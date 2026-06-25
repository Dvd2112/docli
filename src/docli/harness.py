"""
docli.harness — Test harness para validação de documentação.

Responsabilidades:
    - Verificar se cada arquivo documentado ainda existe
    - Verificar se a task descrita corresponde ao código atual
    - Validar se a descrição não está vazia ou genérica demais
    - Reportar resultados em formato estruturado

Uso:
    docli harness              — Executa todos os testes
    docli harness --verbose   -v  — Modo detalhado
"""

from pathlib import Path
from typing import List
from docli.analyzer import analyze_file, analyze_directory
from docli.docstore import DocStore


def run_tests(store: DocStore, project_root: Path, verbose: bool = False) -> List[dict]:
    """
    Executa o harness de testes sobre a documentação.

    Retorna lista de dicionários com:
        - teste: nome do teste
        - status: "pass" ou "fail"
        - detalhes: mensagem explicativa
    """
    resultados = []
    entries = store.list_all()

    # Teste 1: Cada arquivo documentado ainda existe
    total = len(entries)
    existentes = 0
    for entry in entries:
        if Path(entry.file).exists():
            existentes += 1
        elif verbose:
            print(f"  [dim]Arquivo não encontrado: {entry.file}[/dim]")

    resultados.append({
        "teste": "Arquivos documentados existem",
        "status": "pass" if existentes == total else "fail",
        "detalhes": f"{existentes}/{total} arquivos encontrados",
    })

    # Teste 2: Descrições não estão vazias ou genéricas
    PALAVRAS_GENERICAS = {"arquivo", "file", "module", "classe", "class", "função", "function"}
    with_desc = 0
    for entry in entries:
        desc = entry.description.lower()
        words = set(desc.split())
        if len(desc) > 20 and not words.issubset(PALAVRAS_GENERICAS):
            with_desc += 1

    resultados.append({
        "teste": "Descrições são significativas",
        "status": "pass" if with_desc >= total * 0.8 else "fail",
        "detalhes": f"{with_desc}/{total} com descrições adequadas (mín 80%)",
    })

    # Teste 3: Task identificada não está vazia
    with_task = sum(1 for e in entries if e.task and e.task != "Módulo desconhecido")
    resultados.append({
        "teste": "Tasks identificadas corretamente",
        "status": "pass" if with_task == total else "fail",
        "detalhes": f"{with_task}/{total} com task identificada",
    })

    # Teste 4: Implementação descrita
    with_impl = sum(1 for e in entries if e.implementation and len(e.implementation) > 10)
    resultados.append({
        "teste": "Implementações descritas",
        "status": "pass" if with_impl == total else "fail",
        "detalhes": f"{with_impl}/{total} com descrição de implementação",
    })

    # Teste 5: Consistência (task documented ainda corresponde ao código)
    if total > 0:
        consistentes = 0
        current = analyze_directory(project_root)
        current_tasks = {c["file"]: c["task"] for c in current}
        for entry in entries:
            if entry.file in current_tasks and entry.task == current_tasks[entry.file]:
                consistentes += 1

        resultados.append({
            "teste": "Documentação consistente com código",
            "status": "pass" if consistentes == total else "fail",
            "detalhes": f"{consistentes}/{total} consistentes",
        })

    return resultados
