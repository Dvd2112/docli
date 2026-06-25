# docli — CLI Documentadora de Código

Gera arquivos `.md` de documentação a partir do `git diff` do seu projeto. Também funciona como **chat interativo** e, se quiser, usa **IA local via Ollama** pra descrever as alterações automaticamente.

## Índice

- [Instalação](#instalação)
- [Comandos](#comandos)
- [Modo Chat](#modo-chat)
- [IA com Ollama (opcional)](#ia-com-ollama-opcional)
- [Exemplo de Uso](#exemplo-de-uso)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Testes](#testes)

## Instalação

**Pré-requisitos:** Python >= 3.10 e pip

```bash
git clone https://github.com/Dvd2112/docli.git
cd docli
pip install .
```

Verificar:

```bash
docli --help
```

## Comandos

| Comando | Descrição |
|---------|-----------|
| `docli` | Entra no modo chat interativo |
| `docli init <caminho>` | Configura diretório de saída dos `.md` |
| `docli document` | Gera `.md` a partir do git diff |
| `docli document --ai` | Gera `.md` com descrição automática via IA |
| `docli log` | Lista documentos já gerados |
| `docli model` | Lista modelos disponíveis no Ollama |
| `docli model <nome>` | Define o modelo Ollama a ser usado |
| `docli splash` | Mostra animação decorativa |
| `docli --no-splash` | Executa qualquer comando sem animação |

## Modo Chat

Execute `docli` sem subcomandos para entrar no modo chat. Você pode usar tanto comandos quanto linguagem natural:

```bash
$ docli
╭─ docli chat ───────────────────────────────────╮
│ Status: sem IA (instale Ollama pra usar IA)    │
│ Comandos: document, log, init, splash, ...     │
╰────────────────────────────────────────────────╯
docli: gerar documento              → gera .md
docli: mostrar logs                 → lista docs
docli: configurar docs/             → define saída
docli: ajuda                        → mostra ajuda
docli: sair                         → exit
```

## IA com Ollama (opcional)

O Ollama permite rodar modelos de linguagem localmente no seu computador, sem enviar dados pra nuvem. Com ele, o docli pode:

- Gerar descrições automáticas do diff (`docli document --ai`)
- Responder perguntas sobre o código no chat

### Instalação do Ollama

**Linux:**

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**macOS:** Baixe de https://ollama.com

**Windows:** Baixe de https://ollama.com

### Baixar um modelo

Após instalar o Ollama, inicie o servidor e baixe um modelo:

```bash
# Iniciar o servidor (se não iniciar automaticamente)
ollama serve

# Baixar um modelo (recomendado: llama3.2)
ollama pull llama3.2
```

Modelos recomendados:

| Modelo | Tamanho | RAM necessária |
|--------|---------|---------------|
| `llama3.2:1b` | 1.3 GB | 2 GB |
| `llama3.2` | 4.9 GB | 8 GB |
| `gemma3` | 5.5 GB | 8 GB |
| `mistral` | 4.1 GB | 8 GB |

### Usar IA no docli

```bash
# Gerar documento com descrição automática
docli document --ai

# No chat, perguntas em linguagem natural também usam IA
docli
docli: o que mudou no código?
docli: resuma as alterações dos últimos commits
```

### Configurar o modelo

```bash
# Listar modelos disponíveis
docli model

# Definir um modelo específico
docli model llama3.2

# Definir modelo manualmente no .docli/config.json
```

---

> **Nota:** Tudo funciona normalmente sem Ollama. A IA é um adicional opcional. Comandos como `init`, `document` (sem `--ai`) e `log` não dependem de IA.

## Exemplo de Uso

```bash
# 1. Entre no projeto que quer documentar
cd meu-projeto

# 2. Configure o diretório de saída
docli init docs/

# 3. Faça alterações no código

# 4. Gere a documentação
docli document

# 5. Veja o resultado
cat docs/20260624_143000_auth.md
```

## Estrutura do Projeto

```
docli/
├── pyproject.toml          # Configuração do pacote pip
├── src/docli/
│   ├── __init__.py
│   ├── main.py             # CLI completa (~350 linhas)
│   ├── analyzer.py         # Análise de diff
│   ├── docstore.py         # Armazenamento de documentos
│   └── harness.py          # Harness de teste
└── tests/
    └── test_harness.py     # 12 testes automatizados
```

## Testes

```bash
pip install pytest
pytest tests/ -v
```
