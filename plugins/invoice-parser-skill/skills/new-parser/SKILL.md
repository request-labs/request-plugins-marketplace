---
name: new-parser
description: "Create or finetune a supplier-specific invoice parser plugin for a given PDF file. Receives the PDF path as argument (e.g. /new-parser path/to/file.pdf). If no parser exists, creates one from scratch. If a parser exists but has low confidence or wrong values, enters review/finetune mode to fix the regex patterns. Triggers on: new parser, create parser, add parser, fix parser, finetune parser, review parser, corrigir parser, afinar parser, novo parser, criar parser."
---

# New Parser — Plugin Creator & Finetuner

Goal: given a PDF file, **create or finetune a deterministic parser plugin**, test it, get user validation, and register it in Supabase.

## Pre-flight check (REQUIRED)

Before calling ANY MCP tool, verify the server is reachable by checking if `parse_invoice` exists as an available tool.

**If the tool is NOT available**, run the automatic setup:

1. Ask the user for the token using AskUserQuestion: "Para configurar o MCP server invoice-parser, preciso do teu token de autenticação. Qual é o token?"
2. Once the user provides the token, run:
   ```bash
   claude mcp add --transport streamable-http invoice-parser https://mcp.request.pt/mcp \
     --header "Authorization: Bearer <TOKEN>"
   ```
3. Tell the user: "MCP server configurado! Reinicia o Claude Code para ativar (`claude` de novo neste terminal)."
4. **Stop immediately** — do NOT attempt any MCP operations until the user restarts.

Do NOT attempt to parse, create, update, or perform any operation without the MCP server running.

## Usage

```
/new-parser <path/to/file.pdf>
```

The ARGUMENTS passed to this skill contain the PDF file path.

## Routing: create vs finetune

Run `parse_invoice(pdf_path)` first, then decide:

| Result | Action |
|---|---|
| No match | → **Create workflow** |
| Confidence < 1.0 | → **Finetune workflow** |
| Confidence = 1.0 but values wrong | → **Finetune workflow** |
| Confidence = 1.0, values correct | → Nothing to do |

## MCP Tools

| Operation | MCP Tool |
|---|---|
| Parse a PDF | `parse_invoice(pdf_path)` |
| View parser source | `get_parser_source(name)` |
| Create new parser | `create_parser(name, source)` |
| Update existing parser | `update_parser(name, source)` |
| Disable a parser | `disable_parser(name)` |
| Re-enable a parser | `enable_parser(name)` |

## Workflow — creating a new parser

### Step 1: Parse and get raw text

Run `parse_invoice(pdf_path)`. If no match, the raw extracted text is returned. Capture it.

### Step 2: Analyze the extracted text

Identify: supplier name, NIF/VAT, invoice number pattern, date format, period (if applicable), monetary values, currency, VAT exemption notes.

### Step 3: Write the plugin

```python
import re
from .base import InvoiceParser


class SupplierParser(InvoiceParser):
    """Parser determinístico para faturas de Supplier."""

    NIF = "123456789"

    def can_parse(self, text: str, filename: str = "") -> bool:
        t = text.lower()
        return "supplier keyword" in t or self.NIF in text.replace(" ", "")

    def parse(self, text: str, filename: str = "") -> dict:
        result = self.empty_result()
        result["fornecedor"] = "Supplier"
        result["nif_fornecedor"] = self.NIF
        result["ficheiro"] = filename
        result["moeda"] = "EUR"
        warnings = []

        # Invoice number
        m = re.search(r"Fatura\s+n[.ºo°]\s*(\S+)", text)
        if m:
            result["numero"] = m.group(1)
        else:
            warnings.append("numero não encontrado")

        # Date
        m = re.search(r"Data[:\s]+(\d{2})[/.-](\d{2})[/.-](\d{4})", text)
        if m:
            result["data_emissao"] = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        else:
            warnings.append("data_emissao não encontrada")

        # Subtotal, IVA, Total — adapt regex to supplier layout
        # ...

        # Confidence
        campos_chave = ["numero", "data_emissao", "subtotal", "total"]
        preenchidos = sum(1 for c in campos_chave if result[c] is not None)
        result["confidence"] = round(preenchidos / len(campos_chave), 2)

        result["warnings"] = warnings
        return result
```

### Step 4: Register

Use `create_parser(name, source)`. If parser already exists, use `update_parser(name, source)` (auto-archives previous version).

### Step 5: Test

Run `parse_invoice(pdf_path)` again. Verify JSON output.

### Step 6: User validation

**MANDATORY:** Show results and ask with AskUserQuestion:
- "Os valores extraídos estão corretos?" → "Sim, tudo correto" / "Não, preciso corrigir"

If user rejects → ask what's wrong, fix, update, re-test, ask again.

## Workflow — finetuning an existing parser

1. Run `parse_invoice(pdf_path)` — note wrong/missing fields
2. Get source with `get_parser_source(name)`
3. If needed, extract raw text with `pdftotext <file.pdf> -` to debug regex
4. Diagnose and fix regex issues
5. Save with `update_parser(name, source)`
6. Re-test with `parse_invoice(pdf_path)`
7. User validation (same as create workflow)

## Plugin rules

### Regex patterns
- Use **anchored patterns** with explicit labels (e.g. "Total a Pagar", "Invoice Amount")
- Handle PT format `1.234,56` and EN format `1,234.56` correctly
- Dates: always convert to `DD-MM-YYYY`
- Add alternative label patterns for the same field

### Number parsing helpers

```python
@staticmethod
def _parse_pt(val: str) -> float:
    """Parse PT format: 1.234,56 → float"""
    if not val or not any(c.isdigit() for c in val):
        return 0.0
    return float(val.replace(".", "").replace(",", "."))

@staticmethod
def _parse_dot(val: str) -> float:
    """Parse EN format: 1,234.56 → float"""
    return float(val.replace(",", ""))
```

**Mixed format heuristic (OCR):** dot + ≤2 digits after → EN decimal. >2 digits after dot → PT thousands separator.

### OCR safety
- Handle garbled text in `can_parse` — add common OCR variants
- Use `text.replace(" ", "")` when matching NIFs (OCR inserts spaces)
- Use `[\s\S]*?` instead of `.*?` when label and value span multiple lines
- Safety checks in `_parse_pt`/`_parse_dot` for empty/non-digit values

### Special cases
- IVA 0% and subtotal missing → set `subtotal = total`
- Avoid generic `€` patterns on OCR receipts — can match capital social
- Prefer tax line calculation (`subtotal + iva`) over OCR'd total
- Validate VAT rates: only accept `{6, 13, 23}%`
- **Fuel receipts:** total known but IVA/subtotal missing → `subtotal = total / 1.23`
- **Detalhe/extrato documents:** detect "detalhe" in filename or "VALORES DETALHADOS" in text. Set confidence=0.0 and skip monetary extraction.
- **Multi-entity documents (Via Verde):** sum all "Total pago em ..." sections
- **pdftotext column interleaving:** use `-layout` flag or match values by pattern

### can_parse specificity
- **Never use single short substrings** as sole identifier
- Combine keywords or use full name to avoid false positives
- **Amazon Business:** third-party sellers need special handling — layout varies by country

### Gasolina/thermal receipts
- Invoice number = sequential part of ATCUD (after `-`). Ex: `JUB5974F-000012335` → `000012335`
- ATCUD regex: `A.?T?\s*CUD[;:\s]+([A-Za-z0-9]+)\s*-\s*(\d+)`
- Date fallback from filename: `_date_from_filename(filename)` extracts from `xxx-DDMMYYYY.pdf`

### Confidence calculation
```python
campos_chave = ["numero", "data_emissao", "subtotal", "total"]
preenchidos = sum(1 for c in campos_chave if result[c] is not None)
result["confidence"] = round(preenchidos / len(campos_chave), 2)
```
