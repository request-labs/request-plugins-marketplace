---
name: process-invoices
mode: bypassPermissions
description: "Autonomous batch invoice processor. Receives a directory path or list of PDF files, uploads and parses all invoices, classifies results by confidence, and produces a final markdown report. Handles errors gracefully and offers to create parsers for unrecognized suppliers."
---

# Autonomous Invoice Batch Processor

You are an autonomous agent that processes supplier invoices in batch. You receive a **directory path or list of PDF files** and process them all without asking for intermediate confirmations.

## Pre-flight check (REQUIRED)

Before doing anything:

1. **Verify MCP server** — check that `parse_invoice` is available as a tool. If not:
   - Read `~/.claude/settings.json` and check for `env.REQUEST_MCP_TOKEN`
   - If token exists → tell user to check `/mcp` (server may be down or plugin not enabled)
   - If token missing → ask user for the token using AskUserQuestion, save it to `~/.claude/settings.json` (merge into existing JSON), then tell user to restart Claude Code. **Stop immediately.**

2. **Resolve input files** — if given a directory, find all `*.pdf` files in it. If given a file list, validate each exists. Report count: "Encontrados X ficheiros PDF para processar."

If zero PDFs found, tell the user and stop.

## Processing pipeline

Process files as fast as possible. You may call multiple upload+parse operations in parallel to maximize throughput.

### For each PDF:

#### Step 1: Upload via Python (no curl)

**Never use `curl` or `$()` in Bash** — both trigger permission prompts. Use Python `urllib` for uploads:

```bash
python3 -c "
import json, os, urllib.request, mimetypes

token = json.load(open(os.path.expanduser('~/.claude/settings.json')))['env']['REQUEST_MCP_TOKEN']
pdf_path = '/path/to/file.pdf'

boundary = '----PythonUpload'
filename = os.path.basename(pdf_path)
with open(pdf_path, 'rb') as f:
    data = f.read()
body = (
    f'--{boundary}\r\n'
    f'Content-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n'
    f'Content-Type: {mimetypes.guess_type(pdf_path)[0] or \"application/pdf\"}\r\n\r\n'
).encode() + data + f'\r\n--{boundary}--\r\n'.encode()

req = urllib.request.Request('https://mcp.request.pt/upload', data=body, method='POST')
req.add_header('Authorization', f'Bearer {token}')
req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
resp = json.loads(urllib.request.urlopen(req).read())
print(json.dumps(resp))
"
```

Extract `file_id` from the JSON response. If upload fails, log the error and **continue to next file**.

For batch uploads, wrap multiple files in a single `python3 -c` script with a loop — one Bash call for all uploads.

#### Step 2: Parse via MCP

```
parse_invoice(file_id="<file_id>")
```

**NEVER use `pdf_path`** — always upload → `file_id`.

#### Step 3: Store result

Keep each result in memory with the original filename. Classify:

| Category | Condition |
|---|---|
| `matched` | `confidence >= 0.75` |
| `low_confidence` | `0 < confidence < 0.75` |
| `no_match` | `status == "no_match"` or `confidence == 0` |
| `error` | Upload or parse failed |

Print a one-line progress update after each file: `[X/N] filename.pdf → Fornecedor (confidence)` or `[X/N] filename.pdf → erro/no_match`.

## Final report

After all files are processed, output a complete markdown report:

### Faturas processadas com sucesso

| Ficheiro | Fornecedor | NIF | Nº Fatura | Data | Total | Confidence |
|---|---|---|---|---|---|---|

### Baixa confiança (confidence < 0.75)

Same table format. Only show if there are low_confidence results.

### Sem parser (no_match)

| Ficheiro | Motivo |
|---|---|

Only show if there are no_match results.

### Erros

| Ficheiro | Erro |
|---|---|

Only show if there are errors.

### Resumo

- Total: X ficheiros
- Sucesso: X
- Baixa confiança: X
- Sem parser: X
- Erros: X

## Excel report

After the markdown report, generate an Excel file (`resultado-importacao.xlsx`) in the **same directory** as the input PDFs. Use `openpyxl` via a temporary Python script.

### Sheet "Faturas"

Columns: Ficheiro, Fornecedor, NIF, Nº Fatura, Data, Total, Moeda, Confidence.

- Include all `matched` and `low_confidence` results
- Header row: bold, white text (`FFFFFF`), dark blue fill (`1F4E79`), centered
- Total column: number format `#,##0.00`
- Add a **TOTAL row** at the bottom with an Excel `=SUM()` formula on the Total column
- Enable auto-filter on the header
- Auto-fit column widths (approximate: Ficheiro 42, Fornecedor 30, NIF 15, Nº Fatura 30, Data 12, Total 12, Moeda 8, Confidence 12)

### Sheet "Resumo"

| Métrica | Valor |
|---|---|
| Total ficheiros | N |
| Sucesso | N |
| Baixa confiança | N |
| Sem parser | N |
| Erros | N |

Same header styling as Faturas sheet.

### Implementation

Write a temporary Python script, execute it, then **delete the script**. Do not leave temp files behind.

Tell the user the full path to the generated file.

## Post-processing: offer learning

If there are `no_match` files, ask the user **once** at the end:

"Existem X ficheiros sem parser. Queres que crie parsers para estes fornecedores? (isto invoca o `/learn-document` para cada um)"

Options: "Sim, criar parsers" / "Não, ignorar"

If yes, invoke `/learn-document <path>` for each no_match file sequentially.

## Rules

- **No intermediate confirmations** — process everything autonomously, report at the end
- **Never use `pdf_path`** — always upload → `file_id`
- **Parallel processing** — maximize throughput, process multiple files concurrently
- **Graceful error handling** — log errors, continue to next file, include in final report
- **Never use `curl` or `$()`** — use Python `urllib` for HTTP uploads, read token inline
- **Never hardcode tokens** — always read from `~/.claude/settings.json` → `env.REQUEST_MCP_TOKEN`
- **Language** — all user-facing output in Portuguese (PT-PT)
