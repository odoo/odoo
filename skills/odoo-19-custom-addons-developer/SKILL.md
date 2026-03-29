---
name: odoo-19-custom-addons-developer
description: Develop, extend, debug, and test Odoo 19 custom addons in this repository. Use when Codex needs to work in `custom_addons/`, for tasks such as creating modules, updating manifests, models, views, security rules, wizards, data files, and module-scoped tests. Prefer this skill when repo-specific addon paths, local run commands, or vendor-boundary judgment matter, and avoid editing `addons/` or vendored third-party code unless explicitly requested.
---

# Odoo 19 Custom Addons Developer

## Overview

Develop custom Odoo 19 modules for this repository with repo-specific paths, commands, and module boundaries. Stay focused on `custom_addons/`, follow the target module's existing style, and validate changes with the lightest useful upgrade or test step.

## Start Here

1. Read the target module's `__manifest__.py`, `__init__.py`, and nearby models, views, and security files before editing.
2. Confirm whether the module is project-owned (`gov_*`, `accountant`, `theme_liquid_glass`) or upstream-style (`custom_addons/knowledge/*`, `custom_addons/om_account_accountant-19.0.1.0.3`).
3. Read `references/repo-guide.md` when you need repo-specific commands, addon paths, or module-family guidance.
4. Edit the smallest surface that fixes the task. Avoid broad refactors unless asked.
5. Add or update tests when the module already has tests or when behavior changes are risky.

## Respect Boundaries

- Prefer editing `custom_addons/`.
- Treat `addons/` as upstream vendor code. Change it only when the user explicitly asks.
- Treat `custom_addons/om_account_accountant-19.0.1.0.3` as vendored third-party code unless the user explicitly targets it.
- Preserve OCA-style structure and test conventions inside `custom_addons/knowledge/*`.
- Update `__init__.py`, manifests, security CSV/XML, and view or data registrations when adding new files.

## Implement Safely

- Inspect dependencies in `__manifest__.py` before referencing models, actions, or menus from other modules.
- Keep model names, XML IDs, and file names in `snake_case`.
- Put code in the correct layer: `models/`, `wizard/`, `views/`, `security/`, `data/`, `tests/`, or `static/`.
- Extend existing models with `_inherit` when appropriate; avoid copying large upstream implementations into custom files.
- Update access rights and record rules whenever new models, actions, or menus become user-facing.
- Review view inheritance targets carefully and prefer narrow XPath changes over full view replacement.

## Validate

- Run `ruff check .` for Python-heavy changes when feasible.
- For module install or upgrade checks, prefer the repo's local config and a module-scoped command.
- For tests, prefer `./odoo-bin -c deploy/odoo/kodoo.dev-host.local.conf -d ktest --test-enable -i <module_name> --stop-after-init`.
- For upgrade-only verification, use `-u <module_name>` against the relevant dev database.
- If local config or databases are missing, initialize them with the `make` targets in `references/repo-guide.md`.

## Finish

- Summarize changed business behavior, touched module names, and validation performed.
- Call out when you could not run Odoo or tests.
- State assumptions about local config, database names, or whether a module was treated as vendor code.
