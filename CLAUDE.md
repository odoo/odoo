# Odoo 19.0 Core Framework Fork

## Overview

Odoo 19.0 addons repository for Agromarin ERP: 40+ custom modules for accounting, HR, inventory, manufacturing, and Mexican localization (CFDI, EDI, payroll).

## Business Context

- **CFDI/EDI**: Mexican tax receipt generation and compliance
- **Payroll**: Mexican tax calculations and payroll processing
- **Agricultural**: Crop management, harvest tracking, GPS integration, seasonal planning

## Branch Context

**Development Branch (19.0-marin):** Active development, refactoring allowed, no backward compatibility constraints
**Production Branch (19.0):** Backward compatibility REQUIRED, only bug fixes, migration scripts for data model changes

## Standard Workflow

1. Think through problem → read relevant files
2. Plan using **TodoWrite tool** (session tracking) + **todo.md** (persistence)
3. Check in for plan verification
4. Work on todos, marking complete in both places
5. High-level explanations at each step
6. **Simplicity first**: minimal code changes, avoid massive complex changes
7. Add review section to todo.md

## Development Commands

```bash
./odoo-bin -u module_name -d db_name                    # Install/update
./odoo-bin -u all -d db_name --addons-path=/path        # Update all
./odoo-bin scaffold module_name /path/to/addons         # Create scaffold
./odoo-bin -u module_name -d db_name --test-enable      # Run tests
./odoo-bin -u module_name -d db_name --test-enable --log-level=test  # Tests with coverage
./odoo-bin -d db_name --dev=all                         # Debug mode
./odoo-bin shell -d db_name                             # Shell access
./odoo-bin -u module_name -d db_name --stop-after-init  # Migrate data
```

## Rules Reference

- `core/ruff.toml` — Linter and formatter config (enforces `doc/coding_guidelines.rst`)
- `core/doc/coding_guidelines.rst` — Authoritative coding standards
