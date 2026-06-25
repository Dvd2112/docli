"""
docli.main — Ponto de entrada.

Pipeline:
    [git diff] → [Parser Typer] → [diff + descrição do usuário] → [arquivo .md]
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.prompt import Prompt
from pathlib import Path
from datetime import datetime
import subprocess
import json
import time
import shutil
import re
import urllib.request
import urllib.error

app = typer.Typer(no_args_is_help=True)
console = Console()

CONFIG_FILE = ".docli/config.json"
_SHOW_SPLASH = True
OLLAMA_HOST = "http://localhost:11434"
_DEFAULT_MODEL = "llama3.2"


def _load_config(path: Path) -> dict:
    cfg = path / CONFIG_FILE
    if cfg.exists():
        return json.loads(cfg.read_text())
    return {"output_dir": "docs", "ollama_model": _DEFAULT_MODEL}


def _save_config(path: Path, cfg: dict):
    cfg_path = path / CONFIG_FILE
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(cfg, indent=2))


_BUDDHA = [
    "⠀⠀⣸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⢀⣾⣿⣿⣿⣿⣿⣿⣿⣶⣦⡀",
    "⠀⢠⣿⣿⡿⠀⠀⠈⢹⣿⣿⡿⣿⣿⣇⠀⣠⣿⣿⠟⣽⣿⣿⠇⠀⠀⢹⣿⣿⣿",
    "⠀⢸⣿⣿⡇⠀⢀⣠⣾⣿⡿⠃⢹⣿⣿⣶⣿⡿⠋⢰⣿⣿⡿⠀⠀⣠⣼⣿⣿⠏",
    "⠀⣿⣿⣿⣿⣿⣿⠿⠟⠋⠁⠀⠀⢿⣿⣿⠏⠀⠀⢸⣿⣿⣿⣿⣿⡿⠟⠋⠁⠀",
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣀⣀⣸⣟⣁⣀⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀",
    "⣠⣴⣶⣾⣿⣿⣻⡟⣻⣿⢻⣿⡟⣛⢻⣿⡟⣛⣿⡿⣛⣛⢻⣿⣿⣶⣦⣄⡀⠀",
    "⠉⠛⠻⠿⠿⠿⠷⣼⣿⣿⣼⣿⣧⣭⣼⣿⣧⣭⣿⣿⣬⡭⠾⠿⠿⠿⠛⠉⠀",
]

_COLORS = ["red", "yellow", "green", "cyan", "blue", "magenta", "white"]


def _splash(segundos: float = 1.2):
    if not _SHOW_SPLASH:
        return
    cols = shutil.get_terminal_size().columns
    frames = []
    for line in _BUDDHA:
        frames.append(line.center(cols))
    n = len(frames)
    with Live(refresh_per_second=10, transient=True) as live:
        for t in range(int(segundos * 10)):
            idx = t % n
            cor = _COLORS[(t // n) % len(_COLORS)]
            rendered = "\n".join(
                f"[{cor}]{line}[/]" if i == idx else f"[dim]{line}[/]"
                for i, line in enumerate(frames)
            )
            live.update(rendered)
            time.sleep(0.1)


def _ollama_available() -> bool:
    try:
        req = urllib.request.Request(f"{OLLAMA_HOST}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3):
            return True
    except (urllib.error.URLError, TimeoutError, ConnectionRefusedError):
        return False


def _ollama_generate(prompt: str, model: str | None = None) -> str:
    cfg = _load_config(Path.cwd())
    m = model or cfg.get("ollama_model", _DEFAULT_MODEL)
    payload = json.dumps({"model": m, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            return data.get("response", "").strip()
    except Exception as e:
        return f"(erro Ollama: {e})"


def _ollama_models() -> list[str]:
    try:
        req = urllib.request.Request(f"{OLLAMA_HOST}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def _git_diff(path: Path) -> str:
    result = subprocess.run(
        ["git", "diff"],
        capture_output=True, text=True, cwd=path, timeout=30
    )
    if result.returncode != 0:
        return f"(erro git: {result.stderr.strip()})"
    return result.stdout


def _git_diff_name_only(path: Path) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only"],
        capture_output=True, text=True, cwd=path, timeout=30
    )
    if result.returncode != 0:
        return []
    return [f for f in result.stdout.strip().split("\n") if f]


def _git_log_recent(path: Path, n: int = 5) -> str:
    result = subprocess.run(
        ["git", "log", f"-{n}", "--oneline"],
        capture_output=True, text=True, cwd=path, timeout=15
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _diff_stats(diff: str) -> dict:
    ins = sum(1 for line in diff.split("\n") if line.startswith("+") and not line.startswith("+++"))
    dels = sum(1 for line in diff.split("\n") if line.startswith("-") and not line.startswith("---"))
    return {"insertions": ins, "deletions": dels}


def _gerar_md(timestamp: str, descricao: str, files: list[str], diff: str, stats: dict) -> str:
    data = datetime.now().strftime("%d/%m/%Y %H:%M")
    lines = [
        f"# Documentação de Alterações",
        f"",
        f"**Data:** {data}",
        f"",
        f"## Descrição",
        f"",
        f"{descricao}",
        f"",
        f"## Arquivos Modificados",
        f"",
    ]
    for f in files:
        lines.append(f"- `{f}`")
    lines.append("")
    lines.append(f"## Estatísticas")
    lines.append("")
    lines.append(f"- Inserções: {stats['insertions']}")
    lines.append(f"- Deleções: {stats['deletions']}")
    lines.append(f"- Total de arquivos: {len(files)}")
    lines.append("")
    lines.append("## Diff")
    lines.append("")
    lines.append("```diff")
    lines.append(diff)
    lines.append("```")
    lines.append("")
    lines.append("---")
    lines.append(f"*Documento gerado automaticamente por docli em {data}*")
    lines.append("")
    return "\n".join(lines)


def _run_document(ai: bool = False, descricao: str | None = None, name: str | None = None, verbose: bool = False):
    """Core logic for generating a document."""
    path = Path.cwd()
    cfg = _load_config(path)
    output_dir = path / cfg["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)

    with console.status("[bold green]Executando git diff..."):
        diff = _git_diff(path)
        files = _git_diff_name_only(path)
        recent = _git_log_recent(path)

    if not diff.strip():
        console.print("[yellow]!! Nenhuma alteracao detectada. Faca alteracoes no codigo e tente novamente.[/]")
        return

    console.rule("[bold]Alterações Detectadas[/]")
    if files:
        console.print("[bold]Arquivos modificados:[/]")
        for f in files:
            console.print(f"  [cyan]>[/] {f}")

    stats = _diff_stats(diff)
    console.print(f"\n[dim]{stats['insertions']} inserções, {stats['deletions']} deleções[/]")

    if verbose:
        console.print(Panel(diff[:2000], title="Diff", border_style="dim"))

    if recent:
        console.print(f"\n[dim]Commits recentes:[/]\n[dim]{recent}[/dim]")

    if ai and _ollama_available():
        with console.status("[bold magenta]Ollama gerando descrição..."):
            prompt = (
                f"Resuma em português as alterações abaixo em um parágrafo curto e objetivo.\n\n"
                f"Arquivos: {', '.join(files)}\n"
                f"Estatísticas: {stats['insertions']} inserções, {stats['deletions']} deleções\n"
                f"Diff:\n{diff[:3000]}"
            )
            user_desc = _ollama_generate(prompt)
        console.print(f"[dim]Descrição gerada: {user_desc}[/dim]")
    elif descricao:
        user_desc = descricao
    else:
        console.print("\n[bold yellow]Descreva brevemente o que foi feito:[/]")
        user_desc = typer.prompt("Descrição", default="")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if name:
        filename = f"{name}.md"
    else:
        prefix = Path(files[0]).stem if files else "alteracao"
        filename = f"{ts}_{prefix}.md"

    filepath = output_dir / filename
    conteudo = _gerar_md(ts, user_desc, files, diff, stats)
    filepath.write_text(conteudo, encoding="utf-8")
    console.print(f"\n[green]OK[/] Documento gerado: [bold]{filepath}[/]")
    console.print(f"  Tamanho: {len(conteudo)} caracteres, {len(conteudo.splitlines())} linhas")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    no_splash: bool = typer.Option(False, "--no-splash", help="Remove a animação de entrada"),
):
    if ctx.invoked_subcommand is None:
        _splash()
        _chat_mode()
        return
    _splash()


@app.command()
def splash(
    segundos: float = typer.Option(3.0, "--time", "-t", help="Duração da animação"),
):
    _splash(segundos)


@app.command()
def init(
    output: str = typer.Argument(..., help="Caminho onde os .md serão salvos (ex: docs/ ou documentacao/)"),
):
    cfg = _load_config(Path.cwd())
    cfg["output_dir"] = output
    _save_config(Path.cwd(), cfg)
    out_path = Path.cwd() / output
    out_path.mkdir(parents=True, exist_ok=True)
    console.print(f"[green]OK[/] Configurado! Documentos serao salvos em: [bold]{out_path}[/]")
    if _ollama_available():
        console.print("[dim]Ollama detectado! Use 'docli model' para ver/configurar o modelo.[/dim]")


@app.command()
def model(
    nome: str = typer.Argument(None, help="Nome do modelo Ollama (ex: llama3.2, gemma3, mistral)"),
):
    if nome:
        cfg = _load_config(Path.cwd())
        cfg["ollama_model"] = nome
        _save_config(Path.cwd(), cfg)
        console.print(f"[green]OK[/] Modelo definido: [bold]{nome}[/]")
        return

    if not _ollama_available():
        console.print("[red]Ollama não está rodando.[/] Inicie com 'ollama serve'")
        return

    models = _ollama_models()
    if not models:
        console.print("[yellow]Nenhum modelo encontrado.[/] Baixe um com 'ollama pull llama3.2'")
        return

    cfg = _load_config(Path.cwd())
    atual = cfg.get("ollama_model", _DEFAULT_MODEL)
    table = Table("Modelo", "Status")
    for m in models:
        status = "[green]ativo[/]" if m == atual else ""
        table.add_row(m, status)
    console.print("[bold]Modelos disponíveis no Ollama:[/]")
    console.print(table)
    console.print(f"\nAtual: [cyan]{atual}[/]")
    console.print("Use [bold]docli model <nome>[/] para trocar.")


@app.command()
def document(
    name: str = typer.Option(None, "--name", "-n", help="Nome do arquivo .md (sem extensão)"),
    descricao: str = typer.Option(None, "--desc", "-d", help="Descrição inline (pula prompt)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Mostra diff completo no terminal"),
    ai: bool = typer.Option(False, "--ai", help="Usa Ollama para gerar descrição automaticamente"),
):
    _run_document(ai=ai, descricao=descricao, name=name, verbose=verbose)


@app.command()
def log():
    cfg = _load_config(Path.cwd())
    output_dir = Path.cwd() / cfg["output_dir"]

    if not output_dir.exists():
        console.print("[yellow]!! Nenhum documento encontrado.[/]")
        return

    files = sorted(output_dir.glob("*.md"))
    if not files:
        console.print("[yellow]!! Nenhum documento .md encontrado.[/]")
        return

    table = Table("Arquivo", "Tamanho", "Modificado")
    for f in files:
        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%d/%m %H:%M")
        table.add_row(f.name, f"{f.stat().st_size} bytes", mtime)

    console.print(f"\n[bold]Documentos em {output_dir}:[/]")
    console.print(table)
    console.print(f"\nTotal: {len(files)} documento(s)")


def _chat_mode():
    tem_ollama = _ollama_available()
    status_ia = "[green]IA disponivel[/]" if tem_ollama else "[dim]sem IA (instale Ollama)[/]"

    console.print(Panel.fit(
        "[bold yellow]docli chat[/] — Digite comandos ou perguntas.\n"
        f"Status: {status_ia}\n"
        "Comandos: [cyan]document[/], [cyan]log[/], [cyan]init[/], "
        "[cyan]splash[/], [cyan]model[/], [cyan]help[/], [cyan]exit[/]",
        border_style="blue"
    ))

    while True:
        entrada = Prompt.ask("[bold]docli[/]").strip()

        if not entrada:
            continue

        entrada_lower = entrada.lower()

        if entrada_lower in ("exit", "quit", "sair", "q"):
            console.print("[dim]Até logo![/]")
            break

        if entrada_lower in ("help", "ajuda", "?"):
            console.print(Panel.fit(
                "[bold]Comandos disponíveis:[/]\n"
                "  [cyan]document[/] ou [cyan]gerar documento[/] — gera .md do git diff\n"
                "  [cyan]document --ai[/] ou [cyan]documentar com ia[/] — gera .md com IA\n"
                "  [cyan]log[/] ou [cyan]listar[/] — lista docs gerados\n"
                "  [cyan]init <caminho>[/] — define diretório de saída\n"
                "  [cyan]model[/] — lista modelos Ollama\n"
                "  [cyan]model <nome>[/] — define modelo Ollama\n"
                "  [cyan]splash[/] — mostra a animação\n"
                "  [cyan]help[/] — esta mensagem\n"
                "  [cyan]exit[/] — sai do chat",
                border_style="green"
            ))
            continue

        if entrada_lower in ("splash", "animação", "animacao"):
            _splash(3.0)
            continue

        if entrada_lower in ("log", "listar", "listar documentos", "mostrar documentos", "logs"):
            log()
            continue

        if entrada_lower.startswith("init ") or entrada_lower.startswith("configurar "):
            caminho = re.sub(r"^(init|configurar)\s+", "", entrada_lower, count=1)
            cfg = _load_config(Path.cwd())
            cfg["output_dir"] = caminho
            _save_config(Path.cwd(), cfg)
            out_path = Path.cwd() / caminho
            out_path.mkdir(parents=True, exist_ok=True)
            console.print(f"[green]OK[/] Documentos serao salvos em: [bold]{out_path}[/]")
            continue

        if entrada_lower in ("document", "documentar", "gerar documento", "gerar doc", "doc"):
            _run_document()
            continue

        if entrada_lower in ("document --ai", "documentar com ia", "documentar com ai", "gerar com ia", "doc --ai"):
            _run_document(ai=True)
            continue

        if entrada_lower == "model":
            model()
            continue

        if entrada_lower.startswith("model "):
            nome = re.sub(r"^model\s+", "", entrada_lower, count=1)
            model(nome=nome)
            continue

        if tem_ollama:
            with console.status("[bold magenta]Pensando..."):
                diff = _git_diff(Path.cwd())
                ctx_preview = diff[:1500] if diff else "sem alterações"
                prompt = (
                    f"Você é um assistente de terminal especializado em git e documentação.\n"
                    f"Contexto do projeto (diff atual):\n{ctx_preview}\n\n"
                    f"Pergunta do usuário: {entrada}\n"
                    f"Responda de forma objetiva e curta em português."
                )
                resposta = _ollama_generate(prompt)
            console.print(Panel(resposta, border_style="magenta"))
        else:
            console.print(f"[red]?![/] Comando não reconhecido: [bold]'{entrada}'[/]. Digite [cyan]help[/] para ver os comandos.")
