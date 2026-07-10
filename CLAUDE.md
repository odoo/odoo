# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Runtime Requirements

- Python 3.10–3.14
- PostgreSQL 13+
- Dependencies: `pip install -r requirements.txt`

## Key Commands

```bash
# Start the server
python odoo-bin -d <database> --addons-path=addons,odoo/addons

# Initialize a database with a module
python odoo-bin -d <database> -i <module> --stop-after-init

# Update a module
python odoo-bin -d <database> -u <module> --stop-after-init

# Run all tests for a module
python odoo-bin -d <database> --test-enable --stop-after-init -i <module>

# Run tests filtered by tag
python odoo-bin -d <database> --test-enable --test-tags <tag> --stop-after-init -i <module>

# Interactive shell (with ORM access)
python odoo-bin shell -d <database>

# Scaffold a new addon
python odoo-bin scaffold <module_name> ./addons

# Lint
ruff check .
ruff format .
```

## Architecture

### Module System

Odoo is built around **addons** (modules). Each addon lives in `addons/<name>/` or `odoo/addons/<name>/` and requires:
- `__manifest__.py` — metadata: `name`, `depends`, `data`, `assets`
- `__init__.py` — Python imports

The `base` addon (`odoo/addons/base/`) is the kernel; everything else depends on it.

### ORM Layer (`odoo/orm/`)

The ORM is the core abstraction. Models are Python classes that map to PostgreSQL tables:

- `Model` — persistent records (`_name = 'module.model'`)
- `TransientModel` — temporary records (wizards), auto-deleted
- `AbstractModel` — mixin base, no table

Fields are defined as class attributes using types from `odoo.fields` (or `odoo/orm/fields*.py`):
`Char`, `Integer`, `Float`, `Boolean`, `Date`, `Datetime`, `Many2one`, `One2many`, `Many2many`, `Selection`, `Binary`, `Html`, etc.

The `odoo/orm/` package contains the full ORM split across files: `models.py`, `fields.py`, `fields_relational.py`, `fields_temporal.py`, `environments.py`, `domains.py`, `registry.py`, `decorators.py`, etc.

### HTTP Layer (`odoo/http.py`)

Controllers extend `odoo.http.Controller` and expose routes via `@http.route()`. The request lifecycle flows:

```
WSGI → Application.__call__ → Request._serve_static / _serve_nodb / _serve_db
     → Dispatcher.dispatch → @route decorated endpoint
```

### API Decorators (`odoo/api/`)

Methods on models use decorators from `odoo.api`:
- `@api.model` — no recordset, class-level
- `@api.depends(...)` — computed field dependencies
- `@api.onchange(...)` — UI-only triggers
- `@api.constrains(...)` — validation

### Service Layer (`odoo/service/`)

- `server.py` — process/worker management (prefork, gevent, threading modes)
- `model.py` — XML-RPC dispatch to model methods
- `db.py` — database management (create, drop, backup)

### Test Framework (`odoo/tests/`)

Base classes to import from `odoo.tests`:
- `TransactionCase` — each test gets a transaction rolled back at the end
- `SavepointCase` — uses savepoints for faster isolation
- `HttpCase` — full HTTP stack, supports browser (Chrome headless) tests via `browser_js()`

Tag tests with `@tagged('tag1', 'tag2')`. Use `-at_install` / `+post_install` for timing.

### Import Conventions

```python
# Imports must be ordered: future → stdlib → third-party → odoo (first-party) → odoo.addons (local)
# Enforced by ruff (see ruff.toml isort section)
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
```
