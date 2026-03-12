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
- Reliable install harness for noisy test DBs:
  - On the non-production database `ktest_report_xlsx`, `lock_timeout` was set to `0` and all rows in `ir_cron` were deactivated during install checks. This eliminated false-negative `ir_cron` lock/serialization failures caused by the always-on main server touching the same test database.

## Readiness status

| Module | Status | Notes |
|---|---|---|
| `report_xlsx` | Ready | Install verified in Docker/Python 3.12 on alternate port/database. |
| `hide_menu_user` | Ready | Install verified in Docker/Python 3.12 on alternate port/database. |
| `ai_sql` | Ready with optional runtime dependency | Install verified after removing hard `openai` install block and making the controller degrade gracefully when `openai` is absent. |
| `auto_database_backup` | Ready with optional backend libraries | Install verified in Docker/Python 3.12 on the prepared non-production database. Optional Python backends remain lazy and now fail with user-facing guidance only when their storage backend is used. |
| `base_account_budget` | Pending family validation | Discovery fixed; validated indirectly as part of the `base_accounting_kit` family path. |
| `base_accounting_kit` | Ready with optional QIF dependency | Install verified in Docker/Python 3.12. Removed hard `qifparse` blocker; QIF import now asks for the package only when used. |
| `dynamic_accounts_report` | Ready | Install verified in Docker/Python 3.12 on top of the validated accounting kit. Added missing ACL rows for four report models. |
| `hr_payroll_community` | Ready | Install verified in Docker/Python 3.12 on alternate database. |
| `hr_payroll_account_community` | Pending after payroll base | Depends on `hr_payroll_community`. |
| `hr_employee_transfer` | Pending | Awaits Open HRMS family validation. |
| `hr_employee_updation` | Pending | Awaits Open HRMS family validation. |
| `hr_leave_request_aliasing` | Pending | Awaits Open HRMS family validation. |
| `hr_multi_company` | Pending | Awaits Open HRMS family validation. |
| `hr_reminder` | Pending | Awaits Open HRMS family validation. |
| `hr_resignation` | Pending | Awaits Open HRMS family validation. |
| `hr_reward_warning` | Pending | Awaits Open HRMS family validation. |
| `hrms_dashboard` | Ready with follow-up warning cleanup | Install verified in Docker/Python 3.12 on top of `ktest_hr_payroll_community`. Removed hard `pandas` requirement, replaced the two pandas aggregations with pure Python aggregation, and switched dashboard chart loading from CDN to local Odoo assets. |
| `oh_employee_creation_from_user` | Pending | Awaits Open HRMS family validation. |
| `oh_employee_documents_expiry` | Pending | Awaits Open HRMS family validation. |
| `ohrms_loan` | Pending | Awaits Open HRMS family validation. |
| `ohrms_loan_accounting` | Pending | Awaits Open HRMS family validation. |
| `ohrms_salary_advance` | Pending | Awaits Open HRMS family validation. |
| `ohrms_core` | Ready with legacy-field warnings | Install verified in Docker/Python 3.12 on top of the validated Open HRMS dependency chain. Hard `pandas` manifest blocker removed; several legacy field parameters still emit non-fatal Odoo 19 warnings and are being normalized incrementally. |
| `multicolor_backend_theme` | Ready | Install verified in Docker/Python 3.12 on the prepared non-production database. Added Owl-safe systray inheritance, fixed the color picker property lookup, and migrated the login theme route flow to `jsonrpc`. |
| `powered_by_odoo_remove` | Ready | Install verified in Docker/Python 3.12. XPath expressions updated to `hasclass(...)` for safer Odoo 19 view inheritance. |
| `synconics_bi_dashboard` | Ready with optional export backends | Install verified in Docker/Python 3.12 on the prepared non-production database. `imgkit` and `xlsxwriter` paths now degrade gracefully instead of blocking module load. |
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
- [custom_addons/ohrms_core-19.0.1.0.0/hrms_dashboard/__manifest__.py](/home/actpm/workfolder/odoo/custom_addons/ohrms_core-19.0.1.0.0/hrms_dashboard/__manifest__.py)
- [custom_addons/ohrms_core-19.0.1.0.0/hrms_dashboard/static/src/js/dashboard.js](/home/actpm/workfolder/odoo/custom_addons/ohrms_core-19.0.1.0.0/hrms_dashboard/static/src/js/dashboard.js)
  - Replaced CDN `Chart.js` loading with the local Odoo asset and removed the stray `d3` dependency from percentage math.
- [custom_addons/ohrms_core-19.0.1.0.0/hrms_dashboard/report/broadfactor.py](/home/actpm/workfolder/odoo/custom_addons/ohrms_core-19.0.1.0.0/hrms_dashboard/report/broadfactor.py)
  - Added the missing abstract-report description to silence Odoo 19 model warnings.
- [custom_addons/ohrms_core-19.0.1.0.0/hr_resignation/models/hr_resignation.py](/home/actpm/workfolder/odoo/custom_addons/ohrms_core-19.0.1.0.0/hr_resignation/models/hr_resignation.py)
- [custom_addons/ohrms_core-19.0.1.0.0/hr_reward_warning/models/hr_announcement.py](/home/actpm/workfolder/odoo/custom_addons/ohrms_core-19.0.1.0.0/hr_reward_warning/models/hr_announcement.py)
- [custom_addons/ohrms_core-19.0.1.0.0/ohrms_salary_advance/models/salary_advance.py](/home/actpm/workfolder/odoo/custom_addons/ohrms_core-19.0.1.0.0/ohrms_salary_advance/models/salary_advance.py)
- [custom_addons/ohrms_core-19.0.1.0.0/ohrms_loan_accounting/models/hr_loan.py](/home/actpm/workfolder/odoo/custom_addons/ohrms_core-19.0.1.0.0/ohrms_loan_accounting/models/hr_loan.py)
  - Replaced legacy `track_visibility` usage with Odoo 19 `tracking=True`; `hr_resignation` also now stores `notice_period` to avoid mixed compute-field behavior.
- [custom_addons/synconics_bi_dashboard-19.0.1.0.3/synconics_bi_dashboard/models/dashboard_chart.py](/home/actpm/workfolder/odoo/custom_addons/synconics_bi_dashboard-19.0.1.0.3/synconics_bi_dashboard/models/dashboard_chart.py)
  - `imgkit` import is optional; export now raises a clear validation error if the package is absent.
- [custom_addons/synconics_bi_dashboard-19.0.1.0.3/synconics_bi_dashboard/wizard/mail_compose_message.py](/home/actpm/workfolder/odoo/custom_addons/synconics_bi_dashboard-19.0.1.0.3/synconics_bi_dashboard/wizard/mail_compose_message.py)
- [custom_addons/synconics_bi_dashboard-19.0.1.0.3/synconics_bi_dashboard/static/src/js/form_dashboard_preview.js](/home/actpm/workfolder/odoo/custom_addons/synconics_bi_dashboard-19.0.1.0.3/synconics_bi_dashboard/static/src/js/form_dashboard_preview.js)
- [custom_addons/synconics_bi_dashboard-19.0.1.0.3/synconics_bi_dashboard/static/src/js/dashboard_form_view.js](/home/actpm/workfolder/odoo/custom_addons/synconics_bi_dashboard-19.0.1.0.3/synconics_bi_dashboard/static/src/js/dashboard_form_view.js)
  - Added graceful fallback for image-export-dependent email flows, corrected preview payload field names, and guarded the form compiler against missing class attributes.
- [custom_addons/multicolor_backend_theme-19.0.1.0.0/multicolor_backend_theme/static/src/xml/systray_ext.xml](/home/actpm/workfolder/odoo/custom_addons/multicolor_backend_theme-19.0.1.0.0/multicolor_backend_theme/static/src/xml/systray_ext.xml)
- [custom_addons/multicolor_backend_theme-19.0.1.0.0/multicolor_backend_theme/static/src/js/systray_item.js](/home/actpm/workfolder/odoo/custom_addons/multicolor_backend_theme-19.0.1.0.0/multicolor_backend_theme/static/src/js/systray_item.js)
- [custom_addons/multicolor_backend_theme-19.0.1.0.0/multicolor_backend_theme/controllers/theme_config.py](/home/actpm/workfolder/odoo/custom_addons/multicolor_backend_theme-19.0.1.0.0/multicolor_backend_theme/controllers/theme_config.py)
- [custom_addons/multicolor_backend_theme-19.0.1.0.0/multicolor_backend_theme/static/src/js/login_page.js](/home/actpm/workfolder/odoo/custom_addons/multicolor_backend_theme-19.0.1.0.0/multicolor_backend_theme/static/src/js/login_page.js)
  - Added `owl="1"` and resilient systray XPath targeting, fixed the color-picker property lookup, and migrated the login theme endpoint flow to `jsonrpc`.
- [custom_addons/base_accounting_kit-19.0.2.2.0/base_accounting_kit/wizard/import_bank_statement.py](/home/actpm/workfolder/odoo/custom_addons/base_accounting_kit-19.0.2.2.0/base_accounting_kit/wizard/import_bank_statement.py)
- [custom_addons/dynamic_accounts_report-19.0.1.0.0/base_accounting_kit/wizard/import_bank_statement.py](/home/actpm/workfolder/odoo/custom_addons/dynamic_accounts_report-19.0.1.0.0/base_accounting_kit/wizard/import_bank_statement.py)
  - QIF import now requests `qifparse` only when needed.
- [custom_addons/base_accounting_kit-19.0.2.2.0/base_accounting_kit/models/account_asset_category.py](/home/actpm/workfolder/odoo/custom_addons/base_accounting_kit-19.0.2.2.0/base_accounting_kit/models/account_asset_category.py)
- [custom_addons/dynamic_accounts_report-19.0.1.0.0/base_accounting_kit/models/account_asset_category.py](/home/actpm/workfolder/odoo/custom_addons/dynamic_accounts_report-19.0.1.0.0/base_accounting_kit/models/account_asset_category.py)
  - Removed invalid `hide=True` field parameter that generated Odoo 19 warnings.
- [custom_addons/dynamic_accounts_report-19.0.1.0.0/dynamic_accounts_report/security/ir.model.access.csv](/home/actpm/workfolder/odoo/custom_addons/dynamic_accounts_report-19.0.1.0.0/dynamic_accounts_report/security/ir.model.access.csv)
  - Added missing access rows for aged payable, aged receivable, bank book, and tax report models.
- [custom_addons/powered_by_odoo_remove-saas-19.1.1.0/powered_by_odoo_remove/views/login_layout.xml](/home/actpm/workfolder/odoo/custom_addons/powered_by_odoo_remove-saas-19.1.1.0/powered_by_odoo_remove/views/login_layout.xml)
- [custom_addons/powered_by_odoo_remove-saas-19.1.1.0/powered_by_odoo_remove/views/portal_record_sidebar.xml](/home/actpm/workfolder/odoo/custom_addons/powered_by_odoo_remove-saas-19.1.1.0/powered_by_odoo_remove/views/portal_record_sidebar.xml)
- [custom_addons/powered_by_odoo_remove-saas-19.1.1.0/powered_by_odoo_remove/views/brand_promotion.xml](/home/actpm/workfolder/odoo/custom_addons/powered_by_odoo_remove-saas-19.1.1.0/powered_by_odoo_remove/views/brand_promotion.xml)
  - Replaced fragile `@class` XPath filters with `hasclass(...)` for Odoo 19 compatibility.

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
