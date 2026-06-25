"""
docli — Documentador Git.

Uso:
    docli init              — Configura caminho de saída dos .md
    docli document [--name] — Gera .md a partir do git diff
    docli log               — Lista documentos gerados
"""

from docli.main import app
