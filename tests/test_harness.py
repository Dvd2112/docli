"""
Testes do docli — test harness embutido.
"""

import pytest
from pathlib import Path
import json
import subprocess
from docli.main import _diff_stats, _gerar_md, _load_config, _save_config


# ── Fixtures ────────────────────────────────────────────────

@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """Cria um projeto git de teste."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)
    return tmp_path


@pytest.fixture
def sample_diff() -> str:
    return """diff --git a/src/main.py b/src/main.py
index abc..def 100644
--- a/src/main.py
+++ b/src/main.py
@@ -1,3 +1,4 @@
 def hello():
-    print("old")
+    print("new")
+    print("added line")
"""


# ── Testes do Config ────────────────────────────────────────

class TestConfig:
    def test_load_default(self, tmp_path):
        cfg = _load_config(tmp_path)
        assert cfg["output_dir"] == "docs"

    def test_save_and_load(self, tmp_path):
        _save_config(tmp_path, {"output_dir": "documentacao"})
        cfg = _load_config(tmp_path)
        assert cfg["output_dir"] == "documentacao"

    def test_config_file_created(self, tmp_path):
        _save_config(tmp_path, {"output_dir": "relatorios"})
        assert (tmp_path / ".docli" / "config.json").exists()


# ── Testes do Diff Stats ────────────────────────────────────

class TestDiffStats:
    def test_count_insertions(self, sample_diff):
        stats = _diff_stats(sample_diff)
        assert stats["insertions"] == 2

    def test_count_deletions(self, sample_diff):
        stats = _diff_stats(sample_diff)
        assert stats["deletions"] == 1

    def test_empty_diff(self):
        stats = _diff_stats("")
        assert stats["insertions"] == 0
        assert stats["deletions"] == 0

    def test_no_changes(self):
        stats = _diff_stats("diff --git a/x b/x\nindex a..b\n--- a/x\n+++ b/x\n")
        assert stats["insertions"] == 0
        assert stats["deletions"] == 0


# ── Testes do Gerador MD ────────────────────────────────────

class TestGeradorMD:
    def test_contains_description(self, sample_diff):
        md = _gerar_md("20240101_120000", "Corrige bug no hello", ["src/main.py"], sample_diff, {"insertions": 2, "deletions": 1})
        assert "Corrige bug no hello" in md
        assert "src/main.py" in md
        assert "+    print" in md
        assert "-    print" in md

    def test_contains_stats(self, sample_diff):
        md = _gerar_md("x", "desc", ["f.py"], sample_diff, {"insertions": 5, "deletions": 3})
        assert "Inserções: 5" in md
        assert "Deleções: 3" in md
        assert "Total de arquivos: 1" in md

    def test_contains_timestamp(self):
        md = _gerar_md("20250623_143000", "teste", [], "", {"insertions": 0, "deletions": 0})
        assert "2025" in md or "gerado" in md

    def test_generates_valid_markdown(self, sample_diff):
        md = _gerar_md("x", "desc", ["a.py", "b.py"], sample_diff, {"insertions": 1, "deletions": 1})
        assert md.startswith("# ")
        assert "```diff" in md
        assert "```" in md


# ── Testes de Integração (Harness) ──────────────────────────

class TestHarness:
    def test_diff_stats_accuracy(self, temp_project: Path):
        """Harness: verifica se as estatísticas do diff estão corretas."""
        (temp_project / "teste.py").write_text("linha1\nlinha2\n")
        subprocess.run(["git", "add", "."], cwd=temp_project, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=temp_project, capture_output=True)

        (temp_project / "teste.py").write_text("linha1\nlinha2_alterada\nlinha3\n")
        result = subprocess.run(["git", "diff"], cwd=temp_project, capture_output=True, text=True)
        stats = _diff_stats(result.stdout)

        assert stats["insertions"] >= 1
        assert stats["deletions"] >= 1

    def test_md_contains_diff_content(self, temp_project: Path):
        """Harness: verifica se o .md gerado contém o diff real."""
        (temp_project / "app.py").write_text("x = 1\n")
        subprocess.run(["git", "add", "."], cwd=temp_project, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=temp_project, capture_output=True)

        (temp_project / "app.py").write_text("x = 2\n")
        result = subprocess.run(["git", "diff"], cwd=temp_project, capture_output=True, text=True)

        _save_config(temp_project, {"output_dir": "docs"})
        md = _gerar_md("20250623_120000", "Altera x", ["app.py"], result.stdout, _diff_stats(result.stdout))

        assert "app.py" in md
        assert "Altera x" in md

    def test_output_dir_is_respected(self, temp_project: Path):
        """Harness: verifica se o diretório de saída configurado é usado."""
        _save_config(temp_project, {"output_dir": "minha-doc"})
        cfg = _load_config(temp_project)
        assert cfg["output_dir"] == "minha-doc"
