---
name: parser
description: "Invoice parser — run the parsing pipeline on PDFs using the Supabase registry. Use for batch processing, managing existing parsers (toggle/list/delete), and running the extraction pipeline. For creating NEW parsers, use the new-parser skill instead."
---

# Invoice Parser — Supabase Registry

Plugins live in a **Supabase database**. All operations go through the `invoice-parser` MCP server tools.

## Pre-flight check (REQUIRED)

Before calling ANY MCP tool, verify the server is reachable by checking if `parse_invoice` exists as an available tool. If the tool is not available, **stop immediately** and show this error:

> **Erro:** O MCP server `invoice-parser` não está disponível. Verifica que o MCP remoto está configurado:
> ```bash
> claude mcp add --transport streamable-http invoice-parser https://mcp.request.pt/mcp \
>   --header "Authorization: Bearer <token>"
> ```
> Se já está configurado, reinicia o Claude Code para carregar o MCP.

Do NOT attempt to parse, list, or perform any operation without the MCP server running.

## MCP Tools

| Operation | MCP Tool |
|---|---|
| Parse a PDF | `parse_invoice(file_id)` |
| List all parsers | `list_parsers()` |
| View parser source | `get_parser_source(name)` |
| Create a parser | `create_parser(name, source)` |
| Update a parser | `update_parser(name, source)` |
| Disable a parser | `disable_parser(name)` |
| Re-enable a parser | `enable_parser(name)` |

There is no delete operation — use `disable_parser` instead (soft delete).

## How to parse a PDF (2-step flow)

The MCP server runs **remotely**. PDFs must be uploaded first via HTTP, then parsed via MCP tool. This keeps the PDF binary out of the Claude context window.

### Step 1: Upload the PDF via HTTP

```bash
curl -s -X POST https://mcp.request.pt/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@/path/to/fatura.pdf"
```

Response: `{"file_id": "abc123"}`

Read the auth token from `~/.claude/mcp_servers.json` → `invoice-parser.headers.Authorization` (strip the "Bearer " prefix if needed).

### Step 2: Parse via MCP tool

```
parse_invoice(file_id="abc123")
```

The `file_id` is a short string — no base64, no large payloads, minimal tokens.

**NEVER use `pdf_path` or `pdf_base64`** — `pdf_path` fails because the server can't access local files. `pdf_base64` wastes tokens. Always use the upload → file_id flow.

### Batch processing

For multiple PDFs, use a Bash loop:

```bash
for pdf in /path/to/folder/*.pdf; do
  FILE_ID=$(curl -s -X POST https://mcp.request.pt/upload \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@$pdf" | python3 -c "import sys,json; print(json.load(sys.stdin)['file_id'])")
  echo "$pdf → $FILE_ID"
done
```

Then call `parse_invoice(file_id=...)` for each file_id via MCP tool. Results are small JSON — no context issues.

For large batches (20+ files), write a Python script that uploads all files and calls the MCP tools/call endpoint directly via SSE/HTTP to avoid round-trips through Claude. See `process_invoices.py` for reference.

## Normalized fields (output schema)

| Field | Type | Notes |
|---|---|---|
| `fornecedor` | str | Supplier name |
| `nif_fornecedor` | str | NIF / VAT number |
| `numero` | str | Invoice number |
| `data_emissao` | str | DD-MM-YYYY |
| `periodo` | str | "DD-MM-YYYY a DD-MM-YYYY" or null |
| `subtotal` | float | Before taxes |
| `iva` | float | VAT amount (0.0 if exempt) |
| `imposto_selo` | float/null | Stamp tax if applicable |
| `outros_encargos` | float/null | Other charges |
| `total` | float | Final amount paid |
| `moeda` | str | ISO-4217 (EUR/USD/GBP) |
| `ficheiro` | str | Original PDF filename |
| `confidence` | float | 0.0–1.0 based on fields found |
| `warnings` | list[str] | Any extraction issues |
| `nota_iva` | str/null | VAT exemption note |

When LLM OCR is used, output also includes `ocr_cost` with token/cost details. Absent when `pdftotext` was sufficient.

## When no parser matches

When `parse_invoice()` returns `"status": "no_match"`, **always ask the user** if they want to create a new parser:

- "Não existe parser para este ficheiro. Queres que crie um novo parser?" with options "Sim, criar parser" / "Não, ignorar"

If yes, invoke the **new-parser** skill (`/new-parser <file.pdf>`).

In batch processing, collect all no_match files and ask once at the end.

## Plugin rules

See the **new-parser** skill for detailed plugin rules (regex patterns, number formats, OCR safety, confidence calculation).
