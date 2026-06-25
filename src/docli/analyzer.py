"""
docli.analyzer — Camada de análise de código.

Responsabilidades:
    - Ler arquivos do sistema
    - Identificar a task/main de cada arquivo
    - Gerar descrição da implementação

Pipeline:
    [Arquivo] → [Detectar task] → [Extrair assinaturas] → [Descrição]
"""

import ast
import re
from pathlib import Path
from typing import List, Optional


def _detect_task(content: str, filename: str) -> str:
    """Detecta qual a task/função principal do arquivo."""
    # Tenta detectar via comentário # task:
    task_match = re.search(r"#\s*task:\s*(.+)", content, re.IGNORECASE)
    if task_match:
        return task_match.group(1).strip()

    # Tenta detectar via docstring do módulo
    try:
        tree = ast.parse(content)
        if isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant):
            return tree.body[0].value.value.split("\n")[0].strip()
    except SyntaxError:
        pass

    # Tenta detectar via nome do arquivo
    stem = Path(filename).stem
    if stem == "__init__":
        return "Inicialização do pacote"
    return f"Módulo {stem}"


def _describe_implementation(content: str, filename: str) -> str:
    """Gera uma descrição textual da implementação."""
    ext = Path(filename).suffix
    lines = []
    tree = None

    if ext == ".py":
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return "Arquivo com erro de sintaxe."
    else:
        # Para outras linguagens, conta linhas e identifica funções
        func_patterns = {
            ".js": r"(function\s+\w+|const\s+\w+\s*=\s*\(|async\s+function)",
            ".ts": r"(function\s+\w+|const\s+\w+\s*=\s*\(|async\s+function)",
            ".go": r"(func\s+\w+)",
            ".rs": r"(fn\s+\w+)",
            ".java": r"(public|private|protected)\s+\w+\s+\w+\s*\(",
        }
        pattern = func_patterns.get(ext, r"(def\s+\w+|function\s+\w+)")
        funcs = re.findall(pattern, content)
        lines.append(f"{len(funcs)} função(ões) definida(s)")
        lines.append(f"{content.count('\\n') + 1} linhas")
        lines.append(f"{len(content)} caracteres")
        return "\n".join(lines)

    if tree:
        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        funcs = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        imports = [
            f"{node.names[0].name}" if isinstance(node, ast.Import)
            else f"{node.module}"
            for node in ast.iter_child_nodes(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]

        if classes:
            lines.append(f"Classes: {', '.join(classes[:5])}")
            if len(classes) > 5:
                lines[-1] += f" (+{len(classes) - 5} outras)")
        if funcs:
            lines.append(f"Funções: {', '.join(funcs[:8])}")
            if len(funcs) > 8:
                lines[-1] += f" (+{len(funcs) - 8} outras)")
        if imports:
            lines.append(f"Dependências: {', '.join(imports[:6])}")
            if len(imports) > 6:
                lines[-1] += f" (+{len(imports) - 6} outras)")

        lines.append(f"Total: {len(content.splitlines())} linhas")

    return "\n".join(lines) if lines else "Implementação não analisada."


def analyze_file(path: Path) -> dict:
    """Analisa um único arquivo e retorna task + descrição + implementação."""
    if not path.exists():
        return {"file": str(path), "task": "Arquivo não encontrado", "description": "", "impl": ""}

    content = path.read_text(encoding="utf-8", errors="replace")
    task = _detect_task(content, path.name)
    impl = _describe_implementation(content, path.name)

    return {
        "file": str(path),
        "task": task,
        "description": f"Arquivo: {path.name}",
        "impl": impl,
    }


def analyze_directory(path: Path) -> List[dict]:
    """Analisa todos os arquivos relevantes de um diretório."""
    config_file = path / ".docli" / "config.toml"
    extensions = [".py", ".js", ".ts", ".go", ".rs", ".java"]
    ignore_dirs = {"venv", "__pycache__", ".git", ".docli", "node_modules", ".nox"}

    if config_file.exists():
        import tomllib
        config = tomllib.loads(config_file.read_text())
        extensions = config.get("extensions", extensions)
        ignore_dirs = set(config.get("ignore", list(ignore_dirs)))

    results = []
    for f in sorted(path.rglob("*")):
        if not f.is_file():
            continue
        if any(part.startswith(".") or part in ignore_dirs for part in f.relative_to(path).parts):
            continue
        if f.suffix in extensions:
            results.append(analyze_file(f))

    return results


def describe_implementation(content: str, filename: str) -> str:
    """Função pública para descrever implementação."""
    return _describe_implementation(content, filename)
