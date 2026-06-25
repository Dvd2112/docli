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
from pathlib import Path
from datetime import datetime
import subprocess
import json
import time
import shutil

app = typer.Typer(no_args_is_help=True)
console = Console()

CONFIG_FILE = ".docli/config.json"


def _load_config(path: Path) -> dict:
    cfg = path / CONFIG_FILE
    if cfg.exists():
        return json.loads(cfg.read_text())
    return {"output_dir": "docs"}


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


def _splash(segundos: float = 1.5):
    """Mostra animação do Buddha em loop com alternância de cores."""
    cols = shutil.get_terminal_size().columns
    frames = []
    for i, line in enumerate(_BUDDHA):
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


def _git_diff(path: Path) -> str:
    """Executa git diff no diretório do projeto."""
    result = subprocess.run(
        ["git", "diff"],
        capture_output=True, text=True, cwd=path, timeout=30
    )
    if result.returncode != 0:
        return f"(erro git: {result.stderr.strip()})"
    return result.stdout


def _git_diff_name_only(path: Path) -> list[str]:
    """Lista arquivos modificados."""
    result = subprocess.run(
        ["git", "diff", "--name-only"],
        capture_output=True, text=True, cwd=path, timeout=30
    )
    if result.returncode != 0:
        return []
    return [f for f in result.stdout.strip().split("\n") if f]


def _git_log_recent(path: Path, n: int = 5) -> str:
    """Pega os últimos commits para contexto."""
    result = subprocess.run(
        ["git", "log", f"-{n}", "--oneline"],
        capture_output=True, text=True, cwd=path, timeout=15
    )
    return result.stdout.strip() if result.returncode == 0 else ""


@app.command()
def splash(
    segundos: float = typer.Option(3.0, "--time", "-t", help="Duração da animação"),
):
    """Mostra a animação do Buddha em loop."""
    _splash(segundos)


@app.command()
def init(
    output: str = typer.Argument(
        ..., help="Caminho onde os .md serão salvos (ex: docs/ ou documentacao/)"
    ),
):
    """Configura o caminho de saída para os arquivos .md."""
    cfg = _load_config(Path.cwd())
    cfg["output_dir"] = output
    _save_config(Path.cwd(), cfg)

    out_path = Path.cwd() / output
    out_path.mkdir(parents=True, exist_ok=True)

    console.print(f"[green]OK[/] Configurado! Documentos serao salvos em: [bold]{out_path}[/]")


@app.command()
def document(
    name: str = typer.Option(None, "--name", "-n", help="Nome do arquivo .md (sem extensão)"),
    descricao: str = typer.Option(None, "--desc", "-d", help="Descrição inline (pula prompt)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Mostra diff completo no terminal"),
):
    """
    Gera um arquivo .md a partir do git diff.
    Mostra as diferenças, pede uma descrição e cria o documento.
    """
    path = Path.cwd()

    _splash(1.2)

    # 1. Carrega config
    cfg = _load_config(path)
    output_dir = path / cfg["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)

    # 2. Executa git diff
    with console.status("[bold green]Executando git diff..."):
        diff = _git_diff(path)
        files = _git_diff_name_only(path)
        recent = _git_log_recent(path)

    if not diff.strip():
        console.print("[yellow]!! Nenhuma alteracao detectada. Faca alteracoes no codigo e tente novamente.[/]")
        raise typer.Exit()

    # 3. Mostra resumo
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

    # 4. Pede descrição
    console.print("\n[bold yellow]Descreva brevemente o que foi feito:[/]")
    if descricao:
        user_desc = descricao
    else:
        user_desc = typer.prompt("Descrição", default="")

    # 5. Gera nome do arquivo
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if name:
        filename = f"{name}.md"
    else:
        # Pega o primeiro arquivo modificado como sugestão
        prefix = Path(files[0]).stem if files else "alteracao"
        filename = f"{ts}_{prefix}.md"

    filepath = output_dir / filename

    # 6. Monta conteúdo .md
    conteudo = _gerar_md(ts, user_desc, files, diff, stats)

    # 7. Salva
    filepath.write_text(conteudo, encoding="utf-8")
    console.print(f"\n[green]OK[/] Documento gerado: [bold]{filepath}[/]")
    console.print(f"  Tamanho: {len(conteudo)} caracteres, {len(conteudo.splitlines())} linhas")

    return str(filepath)


@app.command()
def log():
    """Lista todos os documentos .md gerados."""
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


def _diff_stats(diff: str) -> dict:
    """Extrai estatísticas básicas do diff."""
    ins = sum(1 for line in diff.split("\n") if line.startswith("+") and not line.startswith("+++"))
    dels = sum(1 for line in diff.split("\n") if line.startswith("-") and not line.startswith("---"))
    return {"insertions": ins, "deletions": dels}


def _gerar_md(timestamp: str, descricao: str, files: list[str], diff: str, stats: dict) -> str:
    """Monta o conteúdo do arquivo .md."""
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
    lines.append(f"")
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
