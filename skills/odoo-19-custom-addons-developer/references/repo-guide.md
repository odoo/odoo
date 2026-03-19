# Repo Guide

## Contents

- Version and scope
- Module families
- Preferred local commands
- Direct `odoo-bin` commands
- Files to inspect first
- Example prompts

## Version and Scope

- Use this skill for Odoo 19.0 development in this repository.
- Treat Python 3.10 as the baseline, matching `ruff.toml` and `odoo/release.py`.
- Prefer repo-local work in `custom_addons/` unless the user explicitly targets another area.

## Module Families

- Treat `custom_addons/public_sector/gov_*` as the project-owned public-sector workflow and accounting suite.
- Treat `custom_addons/accountant` and `custom_addons/theme_liquid_glass` as project-owned.
- Treat `custom_addons/knowledge/*` as OCA-style addons. Preserve their existing structure, tests, and lighter-touch modification style.
- Treat `custom_addons/om_account_accountant-19.0.1.0.3/*` as vendored third-party addons unless the user explicitly asks to modify them.
- Treat `addons/` as upstream vendor code unless the user explicitly asks to modify it.

## Preferred Local Commands

- Install Python dependencies with `pip install -r requirements.txt -r requirements-gov-runtime.txt`.
- Prepare local databases with `make dev-host-db-setup`.
- Initialize the main dev database with `make dev-host-db-init`.
- Initialize the test database with `make dev-host-test-init`.
- Generate local config with `make dev-host-config`.
- Start local Odoo with `make dev-host-up`.
- Tail local logs with `make dev-host-logs`.
- Use Docker when needed with `docker compose up -d` and `docker compose logs -f odoo`.
- Run Python linting with `ruff check .`.

## Direct `odoo-bin` Commands

- Use `deploy/odoo/kodoo.dev-host.local.conf` as the preferred local config path.
- Use `kodoo` as the default dev database name.
- Use `ktest` as the default test database name.
- Use this addon path from the dev-host config: `addons,custom_addons,custom_addons/public_sector,custom_addons/knowledge,custom_addons/om_account_accountant-19.0.1.0.3`
- Start Odoo directly with `./odoo-bin -c deploy/odoo/kodoo.dev-host.local.conf -d kodoo`.
- Upgrade one module with `./odoo-bin -c deploy/odoo/kodoo.dev-host.local.conf -d kodoo -u <module_name> --stop-after-init`.
- Install and run module tests with `./odoo-bin -c deploy/odoo/kodoo.dev-host.local.conf -d ktest --test-enable -i <module_name> --stop-after-init`.
- Use `--addons-path=addons,custom_addons` only when the config file is unavailable and the target modules do not need the extra knowledge or OM paths.

## Files to Inspect First

- Read `__manifest__.py` for dependencies, data order, and install intent.
- Read `__init__.py` files at module and package level before adding new Python files.
- Read `models/*.py` and `wizard/*.py` before extending behavior.
- Read `views/*.xml` and `security/*.xml` or `security/ir.model.access.csv` before adding menus, actions, or fields.
- Read existing `tests/test_*.py` files when the module already has tests, especially under `custom_addons/knowledge/*`.

## Example Prompts

- "Use `$odoo-19-custom-addons-developer` to add a computed field and form view update in `gov_empenho`."
- "Use `$odoo-19-custom-addons-developer` to debug an XPath failure in `gov_processos` after an Odoo 19 upgrade."
- "Use `$odoo-19-custom-addons-developer` to add module-scoped tests for a change in `custom_addons/knowledge/document_page`."
