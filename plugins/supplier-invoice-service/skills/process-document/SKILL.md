---
name: process-document
description: "Process supplier invoice PDFs — upload, extract structured data (supplier, NIF, amounts, dates, VAT), and return normalized JSON. Supports single and batch processing. Also manages registered parsers (list, view source, toggle, disable). To create or finetune a parser for a new supplier, use the learn-document skill instead."
---

## Execution mode (MANDATORY)

This skill MUST be executed via the Task tool as an autonomous agent. Do NOT execute inline.

After loading this skill, spawn an agent with the FULL skill instructions included in the prompt:

1. Read this entire SKILL.md file content (everything below this section)
2. Spawn the agent:
```
Task(
  subagent_type: "general-purpose",
  mode: "bypassPermissions",
  prompt: "## User request\n<the user's original request + path/arguments>\n\n## Instructions\n<full content of this SKILL.md from '# Invoice Parser' onwards>"
)
```

Do NOT attempt to execute the instructions yourself. ONLY spawn the agent.

---

# Invoice Parser — Supabase Registry

Plugins live in a **Supabase database**. All operations go through the `request` MCP server tools.

## Pre-flight check (REQUIRED)

Before calling ANY MCP tool, verify the server is reachable by checking if `parse_invoice` exists as an available tool.

**If the tool is NOT available**, the MCP server is configured by the plugin via `plugin.json` but needs the `REQUEST_MCP_TOKEN` environment variable set in `~/.claude/settings.json`.

Run the **automatic token setup**:

1. Check if the token already exists: read `~/.claude/settings.json` and look for `env.REQUEST_MCP_TOKEN`
2. If it exists → the issue is something else (server down, plugin not enabled). Tell the user to check `/mcp`.
3. If it does NOT exist → ask the user using AskUserQuestion: "Para usar o MCP server request, preciso do teu token de autenticação. Qual é o token?"
4. Once the user provides the token, save it to `~/.claude/settings.json`:
   - Read the existing file (or start with `{}` if it doesn't exist)
   - Merge `{"env": {"REQUEST_MCP_TOKEN": "<TOKEN>"}}` into the existing JSON (preserve all other settings)
   - Write the file back using the Write tool

5. Tell the user: "Token guardado! Reinicia o Claude Code para ativar (`claude` de novo neste terminal)."
6. **Stop immediately** — do NOT attempt any MCP operations until the user restarts.

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

## Auth token (REQUIRED)

The token lives in **`~/.claude/settings.json`** → `env.REQUEST_MCP_TOKEN` (used by the plugin MCP server automatically and for HTTP uploads).

Before any upload, read the token:

```bash
TOKEN=$(python3 -c "import json,os; print(json.load(open(os.path.expanduser('~/.claude/settings.json')))['env']['REQUEST_MCP_TOKEN'])")
```

If the key does NOT exist, run the token setup from the Pre-flight check section above.

**Never hardcode the token.**

## How to parse a PDF (2-step flow)

The MCP server runs **remotely**. PDFs must be uploaded first via HTTP, then parsed via MCP tool. This keeps the PDF binary out of the Claude context window.

### Step 1: Upload the PDF via HTTP

```bash
TOKEN=$(python3 -c "import json,os; print(json.load(open(os.path.expanduser('~/.claude/settings.json')))['env']['REQUEST_MCP_TOKEN'])")
curl -s -X POST https://mcp.request.pt/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/fatura.pdf"
```

Response: `{"file_id": "abc123"}`

### Step 2: Parse via MCP tool

```
parse_invoice(file_id="abc123")
```

The `file_id` is a short string — no base64, no large payloads, minimal tokens.

**NEVER use `pdf_path` or `pdf_base64`** — `pdf_path` fails because the server can't access local files. `pdf_base64` wastes tokens. Always use the upload → file_id flow.

### Batch processing

For multiple PDFs, use a Bash loop:

```bash
TOKEN=$(python3 -c "import json,os; print(json.load(open(os.path.expanduser('~/.claude/settings.json')))['env']['REQUEST_MCP_TOKEN'])")
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

If yes, invoke the **learn-document** skill (`/learn-document <file.pdf>`).

In batch processing, collect all no_match files and ask once at the end.

## Plugin rules

See the **learn-document** skill for detailed plugin rules (regex patterns, number formats, OCR safety, confidence calculation).
