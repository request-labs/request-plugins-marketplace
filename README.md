# Request Plugins Marketplace

Claude Code plugin marketplace by [Request Labs](https://request.pt).

## Installation

### 1. Add the marketplace

```bash
claude plugin marketplace add https://github.com/request-labs/request-plugins-marketplace
```

### 2. Install a plugin

```bash
claude plugin install invoice-parser-skill
```

### 3. Restart Claude Code

```bash
# Exit the current session and start a new one
claude
```

## Available Plugins

### invoice-parser-skill

Parse PDF invoices and extract structured data (supplier, NIF, amounts, dates, VAT) using a remote MCP server with a Supabase-backed parser registry.

**Skills included:**

| Skill | Trigger | Description |
|---|---|---|
| `/parser` | `parse invoice`, `list parsers` | Run the parsing pipeline, batch process PDFs, manage parsers (list/toggle/disable) |
| `/new-parser <file.pdf>` | `create parser`, `new parser`, `fix parser` | Create or finetune a supplier-specific parser from a PDF |

**First-time setup:** When you invoke a skill for the first time, it will ask for your authentication token and configure the MCP server automatically via `claude mcp add`. The token is stored permanently — you only need to provide it once.

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
| `total` | float | Final amount |
| `moeda` | str | Currency (ISO-4217) |
| `confidence` | float | 0.0–1.0 extraction confidence |

## For developers

### Project structure

```
.claude-plugin/
  marketplace.json       # Marketplace manifest — lists all plugins
plugins/
  invoice-parser-skill/
    .claude-plugin/
      plugin.json        # Plugin manifest (name, version, author)
    skills/
      parser/SKILL.md    # Parsing & batch processing skill
      new-parser/SKILL.md # Parser creation & finetuning skill
.githooks/
  pre-commit             # Auto-bumps plugin patch version on commit
```

### Adding a new plugin

1. Create a folder under `plugins/<plugin-name>/`
2. Add `.claude-plugin/plugin.json` with name, description, version, author
3. Add skills under `skills/<skill-name>/SKILL.md`
4. Register the plugin in `.claude-plugin/marketplace.json`:
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
