"""
docli.docstore — Armazenamento local da documentação.

Formato: JSON em .docli/docs/<hash>.json
Cada entrada contém: file, task, description, implementation, timestamp
"""

import json
import hashlib
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class DocEntry:
    file: str
    task: str
    description: str
    implementation: str
    timestamp: str = ""


class DocStore:
    """Armazena e recupera documentação no diretório .docli/docs/."""

    def __init__(self, docs_dir: Optional[Path]):
        self.docs_dir = docs_dir

    def _hash_path(self, filepath: str) -> str:
        return hashlib.md5(filepath.encode()).hexdigest()

    def _entry_path(self, filepath: str) -> Path:
        return self.docs_dir / f"{self._hash_path(filepath)}.json"

    def save(self, entry: DocEntry) -> None:
        """Salva ou atualiza a documentação de um arquivo."""
        if not self.docs_dir:
            return
        entry.timestamp = datetime.now().isoformat()
        path = self._entry_path(entry.file)
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(entry), indent=2, ensure_ascii=False))
        print(f"  [dim]Documentação salva: {path}[/dim]")

    def get(self, filepath: str) -> Optional[DocEntry]:
        """Recupera a documentação de um arquivo."""
        if not self.docs_dir:
            return None
        path = self._entry_path(filepath)
        if path.exists():
            data = json.loads(path.read_text())
            return DocEntry(**data)
        return None

    def list_all(self) -> List[DocEntry]:
        """Lista toda a documentação salva."""
        if not self.docs_dir or not self.docs_dir.exists():
            return []
        entries = []
        for f in self.docs_dir.glob("*.json"):
            data = json.loads(f.read_text())
            entries.append(DocEntry(**data))
        return entries

    def __bool__(self):
        return self.docs_dir is not None
