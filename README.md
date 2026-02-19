# Request Plugins Marketplace

Claude Code plugin marketplace by [Request Labs](https://request.pt).

## Installation

### 1. Add the marketplace

```bash
claude plugin marketplace add https://github.com/request-labs/request-plugins-marketplace
```

### 2. Install a plugin

```bash
claude plugin install supplier-invoice-service
```

### 3. Restart Claude Code

```bash
# Exit the current session and start a new one
claude
```

## Available Plugins

### supplier-invoice-service

Parse PDF invoices and extract structured data (supplier, NIF, amounts, dates, VAT) using a remote MCP server with a Supabase-backed parser registry.

**Skills included:**

| Skill | Trigger | Description |
|---|---|---|
| `/process-document` | `process document`, `parse invoice`, `list parsers` | Run the parsing pipeline, batch process PDFs, manage parsers (list/toggle/disable) |
| `/learn-document <file.pdf>` | `learn document`, `teach document`, `new supplier`, `fix parser`, `finetune` | Create or finetune a supplier-specific parser from a PDF |

**Agent included:**

| Agent | Description |
|---|---|
| `process-invoices` | Autonomous batch processor — receives a directory, uploads and parses all PDFs, classifies by confidence, and produces a markdown + Excel report |

**First-time setup:** When you invoke a skill for the first time, it will ask for your authentication token and save it to `~/.claude/settings.json` as `env.REQUEST_MCP_TOKEN`. The token is stored permanently — you only need to provide it once.

**Output fields:**

| Field | Type | Description |
|---|---|---|
| `fornecedor` | str | Supplier name |
| `nif_fornecedor` | str | NIF / VAT number |
| `numero` | str | Invoice number |
| `data_emissao` | str | Date (DD-MM-YYYY) |
| `periodo` | str/null | Billing period |
| `subtotal` | float | Before taxes |
| `iva` | float | VAT amount |
| `imposto_selo` | float/null | Stamp tax if applicable |
| `outros_encargos` | float/null | Other charges |
| `total` | float | Final amount |
| `moeda` | str | Currency (ISO-4217) |
| `ficheiro` | str | Original PDF filename |
| `confidence` | float | 0.0–1.0 extraction confidence |
| `warnings` | list[str] | Any extraction issues |
| `nota_iva` | str/null | VAT exemption note |

## For developers

### Project structure

```
.claude-plugin/
  marketplace.json       # Marketplace manifest — lists all plugins
plugins/
  supplier-invoice-service/
    .claude-plugin/
      plugin.json        # Plugin manifest (name, version, author, MCP server)
    skills/
      process-document/SKILL.md   # Parsing & batch processing skill
      learn-document/SKILL.md     # Parser creation & finetuning skill
    agents/
      process-invoices.md         # Autonomous batch processor agent
.githooks/
  pre-commit             # Auto-bumps plugin patch version on commit
```

### Adding a new plugin

1. Create a folder under `plugins/<plugin-name>/`
2. Add `.claude-plugin/plugin.json` with name, description, version, author
3. Add skills under `skills/<skill-name>/SKILL.md`
4. Optionally add agents under `agents/<agent-name>.md`
5. Register the plugin in `.claude-plugin/marketplace.json`:
   ```json
   {
     "name": "your-plugin-name",
     "source": "./plugins/your-plugin-name"
   }
   ```

### Version auto-bump

A pre-commit hook automatically increments the patch version of any plugin with staged changes. To activate it after cloning:

```bash
git config core.hooksPath .githooks
```

If you bump the version manually in `plugin.json`, the hook skips that plugin.
