# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Odoo 19.0 — open-source ERP/business-app suite. Branch: `19.0`. Python 3.10+, PostgreSQL required.

## Commands

### Run the server

```bash
./odoo-bin -d <database> --addons-path=addons,odoo/addons
```

Common flags:
- `-i <module>` — install module on startup
- `-u <module>` — update module on startup
- `--dev=all` — enable developer mode (auto-reload, debug assets)
- `--stop-after-init` — exit after loading/updating modules

### Run tests

```bash
# All tests for a module
./odoo-bin -d <db> --test-enable --stop-after-init -i <module>

# Filter by module (tag syntax)
./odoo-bin -d <db> --test-tags /account

# Filter by class or method
./odoo-bin -d <db> --test-tags :TestAccountAccount
./odoo-bin -d <db> --test-tags :TestAccountAccount.test_shared_accounts

# Run a specific test file directly
./odoo-bin -d <db> --test-file addons/account/tests/test_account_account.py

# Post-install tests only
./odoo-bin -d <db> --test-tags post_install
```

### Linting

```bash
# Python — ruff (configured in ruff.toml)
ruff check .
ruff format .

# Flake8 config is in setup.cfg (extends ruff for CI compatibility)
```

Import order (enforced by ruff/isort):
`future` → `stdlib` → `third-party` → `first-party (odoo)` → `local-folder (odoo.addons)`

### Install dependencies

```bash
pip install -r requirements.txt
```

## Architecture

### Repository layout

```
odoo-bin              # CLI entry point — wraps odoo.cli.main()
odoo/                 # Core framework
  orm/                # ORM engine (models, fields, environments, registry)
  fields/             # Field type re-exports
  http.py             # HTTP routing framework (routes, controllers)
  tools/              # Utility library (config, date_utils, image, i18n, …)
  modules/            # Module loading, installation, migration
  cli/                # CLI sub-commands (server, shell, scaffold, db, …)
  service/            # Worker processes, WSGI, XML-RPC
  upgrade_code/       # Version-migration codemods (used by upgrade CLI)
  _monkeypatches/     # Internal import hooks applied at startup
addons/               # 622 community business modules
odoo/addons/          # 24 base/internal modules (base, test_*)
```

### Core ORM (`odoo/orm/`)

Models are declared by subclassing one of three base classes from `odoo.models`:

| Class | Use |
|-------|-----|
| `Model` | Regular persistent model (database table) |
| `TransientModel` | Wizard/temporary model (auto-cleaned) |
| `AbstractModel` | Mixin/shared behaviour, no table |

Key ORM files: `models.py` (CRUD, search, read_group), `fields.py` + `fields_*.py` (field descriptors), `environments.py` (env/cache), `domains.py`, `registry.py`.

`odoo.osv` is **deprecated since 19.0** — use `odoo.fields.Domain` instead.

### HTTP framework (`odoo/http.py`)

Controllers inherit from `odoo.http.Controller`. Routes are declared with `@http.route(...)`. JSON-RPC endpoints are decorated with `type='json'`.

### Addon structure

Every addon under `addons/<name>/` follows this layout:

```
__manifest__.py       # name, version, depends, data, assets
__init__.py           # imports models/, controllers/, wizards
models/               # Python model files (one model per file convention)
views/                # XML view definitions
controllers/          # HTTP route handlers
tests/                # Python unit/integration tests
static/src/           # JavaScript/OWL components, SCSS
  components/
  views/
security/             # ir.model.access.csv, record rules XML
data/                 # demo/initial data XML
wizard/               # TransientModel forms
i18n/                 # .po translation files
```

### JavaScript frontend (OWL)

The web client lives in `addons/web/static/src/`. Odoo uses **OWL** (Odoo Web Library) — a reactive component framework similar to Vue. Key directories:

- `core/` — services, utilities, hooks, UI primitives
- `views/` — list, form, kanban, graph, pivot, calendar
- `model/` — relational model layer (fetch/cache records)
- `webclient/` — shell, action manager, menus

Modules are declared with `/** @odoo-module */` JSDoc and loaded via the custom module loader in `module_loader.js`.

### Module system

Addons are discovered via `--addons-path`. `__manifest__.py` declares:
- `depends` — module dependencies (loaded first)
- `data` — XML/CSV files loaded on install/update
- `assets` — JS/SCSS bundles grouped by asset bundle name

## Testing patterns

Tests inherit from `odoo.tests.common`:

```python
from odoo.tests import TransactionCase, HttpCase, tagged, Form

@tagged('post_install', '-at_install')
class MyTest(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # shared fixtures

    def test_something(self):
        record = self.env['my.model'].create({...})
        self.assertEqual(record.state, 'draft')
```

Tag conventions:
- `post_install` — run after all modules installed (most tests)
- `-at_install` — skip during module install
- `standard` — default tag applied automatically
- `external` — needs external service (skipped in CI)

`Form` helper simulates UI interaction for wizard/onchange testing.

## Commit conventions

```
[TAG] module_name[, module2]: short description in imperative

[FIX]  Bug fix
[IMP]  Improvement to existing feature
[ADD]  New feature / module
[REM]  Code removal
[REF]  Refactoring (no behaviour change)
[PERF] Performance improvement
[I18N] Translation update
```

Example: `[FIX] account: prevent tax splitting on discount line`

Multi-module: `[FIX] account, base_vat: improve Swiss VAT matching`

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **tx10-odoo** (286928 symbols, 578137 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/tx10-odoo/context` | Codebase overview, check index freshness |
| `gitnexus://repo/tx10-odoo/clusters` | All functional areas |
| `gitnexus://repo/tx10-odoo/processes` | All execution flows |
| `gitnexus://repo/tx10-odoo/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
