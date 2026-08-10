# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Repository overview

This is the Odoo source tree (branch `19.0`) — the open source ERP framework plus the full suite of
official business apps. This particular checkout is a **personal local dev/learning environment**, not
a fork being prepared for upstream contribution:

- `odoo/` — the framework itself (ORM, HTTP layer, module loader, CLI).
- `odoo/addons/` — modules bundled with the framework (`base`, and `test_*` modules used by the
  framework's own test suite).
- `addons/` — the ~620 official first-party application modules (`account`, `sale`, `stock`, `mrp`,
  `hr`, `website`, `point_of_sale`, `l10n_*` localizations, etc.).
- `custom_addons/` — modules under active development here (untracked in git — not part of upstream
  Odoo):
  - `l10n_sa_zatca_compliance` — ZATCA (Saudi e-invoicing) compliance dashboard; extends `l10n_sa_edi`
    (`account.move`, `account.journal`) rather than owning its own core models.
  - `library` — a learning module (`depends: ["base"]`).

## Local dev environment (Windows)

- Python 3.12 virtualenv at `venv/` (gitignored). Run everything through it, e.g. from PowerShell or
  the Bash tool: `./venv/Scripts/python.exe odoo-bin ...`.
- Config file at `config/odoo.conf` (gitignored): `addons_path = D:\odoo\odoo\addons,D:\odoo\odoo\custom_addons`,
  PostgreSQL on `localhost:5432` with user/password `odoo`/`odoo`, HTTP port `8069`. `odoo/addons/`
  does not need to be listed explicitly — it's always implicitly on the path.
- A Docker setup also exists (`Dockerfile`, `docker-compose.yml`, Postgres 16 + `--dev=reload,qweb,werkzeug,xml`)
  but the primary workflow on this machine is the local venv against a local Postgres install.

## Common commands

Run from the repo root using the venv interpreter.

**Start the server** (autoreload + qweb/werkzeug/xml dev helpers):
```
./venv/Scripts/python.exe odoo-bin -c config/odoo.conf --dev=reload,qweb,werkzeug,xml
```

**Install / update a module** against a database:
```
./venv/Scripts/python.exe odoo-bin -c config/odoo.conf -d <db> -i <module> --stop-after-init   # install
./venv/Scripts/python.exe odoo-bin -c config/odoo.conf -d <db> -u <module> --stop-after-init   # update
```

**Run tests** (module tests only run when explicitly enabled):
```
./venv/Scripts/python.exe odoo-bin -c config/odoo.conf -d <db> -i <module> --test-enable --stop-after-init
# or scope to specific tests via tags:
./venv/Scripts/python.exe odoo-bin -c config/odoo.conf -d <db> --test-tags /<module> --stop-after-init
./venv/Scripts/python.exe odoo-bin -c config/odoo.conf -d <db> --test-tags .TestClassName.test_method --stop-after-init
```

**Interactive ORM shell** against a database:
```
./venv/Scripts/python.exe odoo-bin shell -c config/odoo.conf -d <db>
```

**Scaffold a new module** (built-in — prefer this over `create_module.sh`, see below):
```
./venv/Scripts/python.exe odoo-bin scaffold <module_name> custom_addons
```

**Lint** (ruff config in `ruff.toml`, mirrors runbot CI checks):
```
ruff check .
```

### `create_module.sh`
A bash helper at the repo root scaffolds an addon skeleton, but it hardcodes `~/odoo/custom_addons` as
the destination and writes `version: 18.0.1.0.0` into the manifest. On this checkout (19.0, Windows,
addons under `D:\odoo\odoo\custom_addons`), prefer `odoo-bin scaffold` or fix the destination/version
by hand if using this script.

## Architecture

### Addon module structure
Every module is a Python package with a `__manifest__.py` declaring metadata, dependencies, and data
load order:
- `models/` — ORM model definitions (subclass `models.Model`, using `_name` for new models or
  `_inherit` to extend an existing one).
- `views/` — QWeb/XML view definitions, listed in the manifest's `data`, loaded in that order.
- `security/ir.model.access.csv` (+ optional `security/*.xml` record rules) — required for any new model.
- `data/`, `demo/` — XML/CSV records loaded at install time vs. only when demo data is enabled.
- `wizard/` — transient models backing multi-step user actions.
- `report/` — QWeb report templates and report actions.
- `static/src/` — frontend assets (JS/SCSS/XML), organized by bundle.

Odoo loads modules in dependency order (`depends` in the manifest) and merges model definitions across
modules via `_inherit` — extending core apps in place, rather than duplicating models, is the idiomatic
pattern (see `l10n_sa_zatca_compliance` above).

### Framework internals (`odoo/`)
- `odoo/orm/` — the actual ORM engine: `models.py`, `fields*.py`, `decorators.py` (`@api.depends`,
  `@api.model`, ...), `domains.py`, `environments.py`. `odoo/fields/` and `odoo/api/` are thin
  re-export packages over `odoo/orm/` (kept as packages specifically to avoid merge conflicts on a
  single `fields.py`/`api.py` file).
- `odoo/http.py` — the web framework: routing, sessions, request/response.
- `odoo/modules/` — module discovery, loading, and the module registry.
- `odoo/cli/` — `odoo-bin` subcommands: `server` (default), `shell`, `scaffold`, `deploy`, `i18n`,
  `populate`, `neutralize`, `cloc`, etc.
- `odoo/tools/config.py` — the full set of CLI flags / config file options.
- `odoo/addons/base/` — the `base` module (users, companies, `ir.model`, access control, ...) that
  every other module ultimately depends on; also hosts framework-level tests (`base/tests/`).

## Code style
- Lint rules are pinned in `ruff.toml` and mirror what runbot CI enforces. Target Python 3.10 syntax
  even though the local venv runs 3.12 — production Odoo needs to support older Pythons.
- Import order (isort via ruff): future → stdlib → third-party → `odoo` (first-party) → `odoo.addons`
  (local-folder).
- Follow the official coding guidelines:
  https://www.odoo.com/documentation/latest/contributing/development/coding_guidelines.html
