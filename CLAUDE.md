# KSW Odoo Project — Claude Context

## Project Identity
- **Product**: Odoo 19 Community Edition, customised for Al-Kawthar Software (KSW)
- **Database**: `KSWCO`
- **Server**: `http://localhost:8069` — config in `KSW.conf`
- **Active branch**: `KSWDev` → merges into `19.0`
- **Author**: Mohammed Albadr / Mohammed Sadiq (`m.sadiq@alkawthersw.com`)

## Where the real work lives
```
custom_addons/KSW/          ← ALL custom development happens here
```
Everything else is read-only reference:
- `addons/` — Odoo 19 Community core (605 modules, 1.1 GB — do NOT edit)
- `odoo/` — Odoo framework source (do NOT edit)
- `custom_addons/cybrosys/` — third-party, do NOT edit
- `custom_addons/Odoo Mates - hr_payroll_community-19.0.1.0.1/om_hr_payroll/` — base payroll that KSW_payroll extends

## KSW Module Map
| Module | Purpose |
|--------|---------|
| `KSW_base_security` | Security groups & record rules for HR/Attendance |
| `KSW_working_schedule` | Work schedule fields on `hr.employee` |
| `KSW_attendance_leave` | Attendance-based leave tracking |
| `KSW_attendance_sheet` | Monthly attendance sheet for non-biometric employees |
| `KSW_attendance_report` | PDF monthly attendance report |
| `KSW_annual_leave` | Saudi-law annual leave: 21 days/yr (<5 yrs), 30 days/yr (≥5 yrs), auto-allocated daily |
| `KSW_unpaid_leave` | Unpaid leave with 2-step approval + attendance integration |
| `KSW_leave_approval` | 2-step time-off approval: Direct Manager → HR Manager |
| `KSW_deduction` | Employee deductions (loans, penalties, advances) |
| `KSW_commissions` | Monthly commissions & allowances for non-biometric employees |
| `KSW_payroll` | Full payroll: extends `om_hr_payroll`, biometric attendance deduction, payslip runs, bank export |

## Dependency Chain
```
KSW_base_security
KSW_working_schedule
KSW_attendance_leave  ←  KSW_annual_leave
                      ←  KSW_unpaid_leave
                      ←  KSW_attendance_sheet  ←  KSW_attendance_report
                                               ←  KSW_commissions
KSW_leave_approval
KSW_deduction
om_hr_payroll  ←  KSW_payroll (depends on all above)
```

## Key Domain Rules (Saudi Labour Law)
- Annual leave: **21 days/year** for first 5 years, **30 days/year** after 5 years
- Leave duration counts **calendar days including weekends**
- Payslip computation is **blocked** if an employee has an unconfirmed annual leave return
- Attendance deduction rule: `ATTDED` worked-day line feeds into salary rule

## Coding Conventions
- Use `_inherit` to extend existing Odoo models — never create standalone replacements
- Follow Odoo ORM conventions: `@api.depends`, `@api.constrains`, `store=True` for computed fields that need search
- XML ids: prefix with module technical name, e.g. `KSW_payroll.action_payslip_tree`
- Security: always add model access in `security/ir.model.access.csv` and group rules in `security/security.xml`
- Tests go in `tests/` with `__init__.py` importing them; use `TransactionCase`
- Commit prefix: `[ADD]`, `[FIX]`, `[IMP]`, `[REF]`, `[REM]`

## What NOT to do
- Never edit files outside `custom_addons/KSW/`
- Never suggest `pip install` — use `.venv` already at project root
- Don't rewrite entire files when a targeted `_inherit` override suffices
- Don't add demo data unless explicitly asked

## Running / Testing
```bash
# Start server
python odoo-bin -c KSW.conf

# Run tests for a module
python odoo-bin -c KSW.conf --test-enable -u KSW_payroll --stop-after-init

# Upgrade a module
python odoo-bin -c KSW.conf -u KSW_annual_leave --stop-after-init
```

## Preferences
- Responses should be concise — show diffs, not full file rewrites
- When referencing Odoo core behaviour, cite the model/method name (e.g. `hr.leave._check_approval_update`) rather than copying source
- Prefer one targeted fix over restructuring surrounding code
