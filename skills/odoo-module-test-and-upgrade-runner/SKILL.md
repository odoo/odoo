---
name: odoo-module-test-and-upgrade-runner
description: Validate Odoo module changes with the lightest reliable checks available in this repository. Use when Codex must run or propose module-scoped tests, upgrade validation, linting, install checks, or explain what could not be validated locally for changes in `custom_addons/` and related Kodoo modules.
---

# Odoo Module Test And Upgrade Runner

## Overview

Provide disciplined validation for Kodoo changes using repo-specific commands and the smallest meaningful test surface. Prevent unproven patches from being treated as verified.

## Quick Start

1. Identify whether the change is mainly Python, XML, data, security, or model evolution.
2. Choose the lightest meaningful validation:
   lint, upgrade, install, or module tests.
3. Prefer module-scoped checks with the repo's local config.
4. Report exactly what was validated and what was not.

## Validation Ladder

1. Static sanity:
   manifest registration, imports, XML references, and `ruff check .` when useful.
2. Module upgrade check:
   `-u <module_name>` on a dev database.
3. Module install or test check:
   `./odoo-bin -c deploy/odoo/kodoo.dev-host.local.conf -d ktest --test-enable -i <module_name> --stop-after-init`
4. Targeted reproduction note:
   state what passed, what was skipped, and why.

## Responsibilities

- Choose the lightest meaningful validation.
- Prefer module-scoped verification.
- Report environment blockers honestly.
- Separate `not tested` from `tested and passed`.

## Guardrails

- Do not pretend validation happened if it did not.
- Do not run broad expensive checks when a narrow check is enough.
- Always state database and config assumptions.
