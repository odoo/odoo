# KSW Odoo Project — AI Agent Instructions

## Project Overview
Odoo 19 Community Edition customised for **Al-Kawthar Software (KSW)**.
All custom development lives in `custom_addons/KSW/`. Everything else is
read-only Odoo core or third-party modules — do not modify them.

## Scope of Work
```
custom_addons/KSW/
├── KSW_base_security/        # HR/Attendance security groups & record rules
├── KSW_working_schedule/     # Work schedule fields on hr.employee
├── KSW_attendance_leave/     # Attendance-based leave tracking
├── KSW_attendance_sheet/     # Monthly attendance sheet (non-biometric)
├── KSW_attendance_report/    # Monthly PDF attendance report
├── KSW_annual_leave/         # Saudi-law annual leave allocation & balance
├── KSW_unpaid_leave/         # Unpaid leave with 2-step approval
├── KSW_leave_approval/       # Direct Manager → HR Manager approval flow
├── KSW_deduction/            # Loans, penalties, advance deductions
├── KSW_commissions/          # Monthly commissions & allowances
└── KSW_payroll/              # Full payroll extending om_hr_payroll
```

## Off-Limits Directories
- `addons/` — Odoo core (read reference only)
- `odoo/` — Odoo framework (read reference only)
- `custom_addons/cybrosys/` — third-party, do not modify
- `custom_addons/Odoo Mates - hr_payroll_community-19.0.1.0.1/` — base payroll dependency, do not modify
- `.venv/` — virtual environment

## Key Domain Rules
- Saudi Labour Law annual leave: 21 days/year (years 1–5), 30 days/year (year 6+)
- Leave duration uses **calendar days** (weekends included)
- Payroll blocked if employee has unconfirmed annual leave return
- Attendance deduction: `ATTDED` salary rule reads from worked-day lines

## Coding Standards
- Extend models with `_inherit`, never replace them wholesale
- Follow Odoo ORM: `@api.depends`, `@api.constrains`, stored computed fields where search is needed
- XML ids must use the module's technical name as prefix
- All new models need entries in `security/ir.model.access.csv`
- Tests use `TransactionCase` in `tests/` with `__init__.py`
- Commit format: `[ADD]`, `[FIX]`, `[IMP]`, `[REF]`, `[REM]`

## Environment
- Odoo config: `KSW.conf`
- Database: `KSWCO`
- Port: 8069
- Python venv: `.venv/`
- Branch: `KSWDev` → `19.0`

## Useful Commands
```bash
# Upgrade and stop
python odoo-bin -c KSW.conf -u <module> --stop-after-init

# Run module tests
python odoo-bin -c KSW.conf --test-enable -u <module> --stop-after-init

# Lint
.venv/bin/ruff check custom_addons/KSW/
```

## Response Preferences
- Show targeted diffs, not full file rewrites
- Reference Odoo core by model/method name rather than copying source
- One focused fix at a time; avoid restructuring unrelated code
