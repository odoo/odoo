# Community Addons Readiness Matrix

## Global activation work

- Catalog discovery fixed via [scripts/build-custom-addon-paths.sh](/home/actpm/workfolder/odoo/scripts/build-custom-addon-paths.sh).
- Nested bundle auto-discovery now quarantines the known legacy bundle `l10n_br_fiscal-14.0.28.1.0` from the active catalog so it no longer pollutes Odoo 19 installs.
- Renderers updated to include nested addon bundles automatically:
  - [scripts/render-dev-host-config.sh](/home/actpm/workfolder/odoo/scripts/render-dev-host-config.sh)
  - [scripts/render-prod-config.sh](/home/actpm/workfolder/odoo/scripts/render-prod-config.sh)
- Current local configs aligned with the new nested `addons_path`:
  - [deploy/odoo/kodoo.dev-host.local.conf](/home/actpm/workfolder/odoo/deploy/odoo/kodoo.dev-host.local.conf)
  - [deploy/odoo/kodoo.prod.local.conf](/home/actpm/workfolder/odoo/deploy/odoo/kodoo.prod.local.conf)
- Warning cleanup:
  - Added missing license key in [custom_addons/knowledge/__manifest__.py](/home/actpm/workfolder/odoo/custom_addons/knowledge/__manifest__.py)

## Readiness status

| Module | Status | Notes |
|---|---|---|
| `report_xlsx` | Ready | Install verified in Docker/Python 3.12 on alternate port/database. |
| `hide_menu_user` | Ready | Install verified in Docker/Python 3.12 on alternate port/database. |
| `ai_sql` | Ready with optional runtime dependency | Install verified after removing hard `openai` install block and making the controller degrade gracefully when `openai` is absent. |
| `auto_database_backup` | Patched, serial rerun pending | Catalog fixed and optional Python backends made lazy. Parallel install hit `SerializationFailure` on `ir_cron`, which is environmental, not a module parse/load failure. |
| `base_account_budget` | Pending family validation | Discovery fixed; validated indirectly as part of the `base_accounting_kit` family path. |
| `base_accounting_kit` | Patched, validation running | Removed hard `qifparse` blocker; QIF import now asks for the package only when used. Install run is in progress. |
| `dynamic_accounts_report` | Pending after accounting kit | Depends on `base_accounting_kit`; same `qifparse` operational patch applied to its bundled copy. |
| `hr_payroll_community` | Validation running | Discovery fixed; fresh install is in progress. |
| `hr_payroll_account_community` | Pending after payroll base | Depends on `hr_payroll_community`. |
| `hr_employee_transfer` | Pending | Awaits Open HRMS family validation. |
| `hr_employee_updation` | Pending | Awaits Open HRMS family validation. |
| `hr_leave_request_aliasing` | Pending | Awaits Open HRMS family validation. |
| `hr_multi_company` | Pending | Awaits Open HRMS family validation. |
| `hr_reminder` | Pending | Awaits Open HRMS family validation. |
| `hr_resignation` | Pending | Awaits Open HRMS family validation. |
| `hr_reward_warning` | Pending | Awaits Open HRMS family validation. |
| `hrms_dashboard` | Patched, pending install | Removed hard `pandas` requirement and replaced the two pandas aggregations with pure Python aggregation. |
| `oh_employee_creation_from_user` | Pending | Awaits Open HRMS family validation. |
| `oh_employee_documents_expiry` | Pending | Awaits Open HRMS family validation. |
| `ohrms_loan` | Pending | Awaits Open HRMS family validation. |
| `ohrms_loan_accounting` | Pending | Awaits Open HRMS family validation. |
| `ohrms_salary_advance` | Pending | Awaits Open HRMS family validation. |
| `ohrms_core` | Patched, pending install | Hard `pandas` manifest blocker removed; depends on the rest of the Open HRMS stack. |
| `multicolor_backend_theme` | Patched, serial rerun pending | Discovery fixed. Parallel install twice hit `SerializationFailure` on `ir_cron`, pointing to concurrent install noise rather than theme code incompatibility. |
| `powered_by_odoo_remove` | Pending rerun | Discovery fixed; needs a clean serial rerun for final verdict. |
| `synconics_bi_dashboard` | Patched, pending install | Removed hard `imgkit` manifest blocker and added a user-facing error only when image export is invoked without the package. |
| `industry_real_estate` | Blocked by missing dependencies | Requires `crm_enterprise`, `project_sale_subscription`, and `website_studio`, which are not present in the current addon catalog. |
| `l10n_br_base` | Blocked by incompatible version | Odoo 19 marks it incompatible automatically because the addon is from the 14.0 series. |
| `l10n_br_fiscal` | Blocked by incompatible version | Odoo 19 marks it incompatible automatically because the addon is from the 14.0 series. |

## Operational patches applied

- [custom_addons/ai_sql-19.0.1.0.0/ai_sql/controllers/main.py](/home/actpm/workfolder/odoo/custom_addons/ai_sql-19.0.1.0.0/ai_sql/controllers/main.py)
  - `openai` import is now optional at bootstrap.
  - Route updated to `jsonrpc`.
- [custom_addons/ai_sql-19.0.1.0.0/ai_sql/models/res_config_settings.py](/home/actpm/workfolder/odoo/custom_addons/ai_sql-19.0.1.0.0/ai_sql/models/res_config_settings.py)
  - Removed invalid field parameter warning on Odoo 19.
- [custom_addons/auto_database_backup-19.0.1.0.0/auto_database_backup/models/db_backup_configure.py](/home/actpm/workfolder/odoo/custom_addons/auto_database_backup-19.0.1.0.0/auto_database_backup/models/db_backup_configure.py)
  - Optional imports for `boto3`, `dropbox`, `paramiko`, `nextcloud`.
  - Clear `UserError` messages when optional backend libraries are missing.
- [custom_addons/ohrms_core-19.0.1.0.0/hrms_dashboard/models/hr_employee.py](/home/actpm/workfolder/odoo/custom_addons/ohrms_core-19.0.1.0.0/hrms_dashboard/models/hr_employee.py)
  - Replaced pandas aggregations with Python `defaultdict` sums.
- [custom_addons/synconics_bi_dashboard-19.0.1.0.3/synconics_bi_dashboard/models/dashboard_chart.py](/home/actpm/workfolder/odoo/custom_addons/synconics_bi_dashboard-19.0.1.0.3/synconics_bi_dashboard/models/dashboard_chart.py)
  - `imgkit` import is optional; export now raises a clear validation error if the package is absent.
- [custom_addons/base_accounting_kit-19.0.2.2.0/base_accounting_kit/wizard/import_bank_statement.py](/home/actpm/workfolder/odoo/custom_addons/base_accounting_kit-19.0.2.2.0/base_accounting_kit/wizard/import_bank_statement.py)
- [custom_addons/dynamic_accounts_report-19.0.1.0.0/base_accounting_kit/wizard/import_bank_statement.py](/home/actpm/workfolder/odoo/custom_addons/dynamic_accounts_report-19.0.1.0.0/base_accounting_kit/wizard/import_bank_statement.py)
  - QIF import now requests `qifparse` only when needed.

## Duplicate technical modules detected

- `base_account_budget`
  - [custom_addons/base_accounting_kit-19.0.2.2.0/base_account_budget](/home/actpm/workfolder/odoo/custom_addons/base_accounting_kit-19.0.2.2.0/base_account_budget)
  - [custom_addons/dynamic_accounts_report-19.0.1.0.0/base_account_budget](/home/actpm/workfolder/odoo/custom_addons/dynamic_accounts_report-19.0.1.0.0/base_account_budget)
- `base_accounting_kit`
  - [custom_addons/base_accounting_kit-19.0.2.2.0/base_accounting_kit](/home/actpm/workfolder/odoo/custom_addons/base_accounting_kit-19.0.2.2.0/base_accounting_kit)
  - [custom_addons/dynamic_accounts_report-19.0.1.0.0/base_accounting_kit](/home/actpm/workfolder/odoo/custom_addons/dynamic_accounts_report-19.0.1.0.0/base_accounting_kit)
- `hr_payroll_community`
  - [custom_addons/hr_payroll_community-19.0.1.0.1/hr_payroll_community](/home/actpm/workfolder/odoo/custom_addons/hr_payroll_community-19.0.1.0.1/hr_payroll_community)
  - [custom_addons/ohrms_core-19.0.1.0.0/hr_payroll_community](/home/actpm/workfolder/odoo/custom_addons/ohrms_core-19.0.1.0.0/hr_payroll_community)

The duplicate directories are byte-for-byte identical in the current checkout, so they are not an immediate runtime incompatibility, but they should be normalized later to reduce catalog ambiguity.
