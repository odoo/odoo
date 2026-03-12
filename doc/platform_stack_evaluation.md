# Platform Stack Evaluation

Date: 2026-03-12

Objective:
- choose canonical baseline stacks for Kodoo
- optimize for neutral BR/USA platform evolution
- prefer the option that delivers good coverage with the least leveling cost

## Architectural Frame

- `suite_dashboard_*` remains neutral product surface.
- `br_*` will be our Brazilian business/fiscal family.
- `gov_*` is contextualization for one public-sector segment, not the platform north.
- USA should stay as close as possible to upstream Odoo localization unless a real gap appears.

## 1. Accounting Stack

### Option A

Modules:
- `custom_addons/accountant`
- `custom_addons/om_account_accountant-19.0.1.0.3/accounting_pdf_reports`
- `custom_addons/om_account_accountant-19.0.1.0.3/om_account_accountant`
- `custom_addons/om_account_accountant-19.0.1.0.3/om_account_asset`
- `custom_addons/om_account_accountant-19.0.1.0.3/om_account_budget`
- `custom_addons/om_account_accountant-19.0.1.0.3/om_account_daily_reports`
- `custom_addons/om_account_accountant-19.0.1.0.3/om_account_followup`
- `custom_addons/om_account_accountant-19.0.1.0.3/om_fiscal_year`
- `custom_addons/om_account_accountant-19.0.1.0.3/om_recurring_payments`

Characteristics:
- modular and relatively low-coupling
- depends mostly on `account`, with narrow extra dependencies like `mail`
- already wrapped behind the stable technical module name `accountant`
- clean fit for a neutral platform where BR logic should live above the accounting baseline

Coverage:
- accounting PDF reports
- assets
- budget
- daily cash/day/bank books
- follow-up
- fiscal year and lock date
- recurring payments

Strengths:
- least leveling cost
- no internal duplicated technical modules found
- better fit for BR/USA neutrality
- easier to extend with `br_*` without inheriting unrelated business logic

Weaknesses:
- less feature-rich than the Cybrosys line out of the box
- reporting UX is more traditional than dynamic
- no local test suite identified in this checkout

### Option B

Modules:
- `custom_addons/base_accounting_kit-19.0.2.2.0/base_account_budget`
- `custom_addons/base_accounting_kit-19.0.2.2.0/base_accounting_kit`
- `custom_addons/dynamic_accounts_report-19.0.1.0.0/base_account_budget`
- `custom_addons/dynamic_accounts_report-19.0.1.0.0/base_accounting_kit`
- `custom_addons/dynamic_accounts_report-19.0.1.0.0/dynamic_accounts_report`

Characteristics:
- broader and more monolithic suite
- richer reporting surface, especially with dynamic report screens
- larger dependency surface: `sale`, `contacts`, `analytic`, `account_check_printing`
- extra Python dependencies: `openpyxl`, `ofxparse`

Coverage:
- assets
- budget
- financial reports
- follow-up
- recurring entries/payments
- cash flow
- bank import
- credit limit
- multiple invoice layouts
- dynamic accounting reports

Strengths:
- most complete feature set out of the box
- stronger reporting UX than Option A

Weaknesses:
- duplicated technical modules exist in two package roots:
  - `base_account_budget`
  - `base_accounting_kit`
- more intrusive core accounting overrides
- larger coupling to sales and supporting modules
- no local test suite identified in this checkout

### Accounting Recommendation

Canonical baseline:
- choose Option A as Kodoo core accounting baseline

Reason:
- Option B is more complete, but Option A demands less leveling and is safer for a neutral BR/USA platform

Practical rule:
- keep `accountant` as the stable compatibility entrypoint
- treat Option B strictly as donor material for future optional addons
- never make Option B a direct dependency of `accountant`, `br_base`, or `br_account`
- if we want ideas from Option B later, prefer isolated named ports such as:
  - `br_reports`
  - `br_bank_import`
  - other small `br_*` bridges with explicit scope
- extract value from Option B feature-by-feature instead of adopting the whole stack

## 2. Payroll Stack

### Option A

Modules:
- `custom_addons/hr_payroll_community-19.0.1.0.1/hr_payroll_community`

Characteristics:
- standalone payroll core
- low coupling
- depends only on `hr_holidays`

Coverage:
- payroll structures
- salary rules
- payslips
- payslip runs
- payroll reports

Strengths:
- cleanest canonical payroll base
- easiest to position under future `br_hr_payroll`

Weaknesses:
- no payroll-accounting bridge by itself
- no local test suite identified for this standalone root

### Option B

Modules:
- `custom_addons/ohrms_core-19.0.1.0.0/hr_payroll_community`
- `custom_addons/ohrms_core-19.0.1.0.0/hr_payroll_account_community`
- `custom_addons/ohrms_core-19.0.1.0.0/ohrms_core`
- plus related Open HRMS family modules

Characteristics:
- `hr_payroll_community` source is effectively the same as the standalone one
- `hr_payroll_account_community` is a useful optional bridge
- `ohrms_core` itself is strongly suite-coupled and opinionated

Coverage beyond payroll:
- payroll accounting bridge
- HR dashboard
- loans
- salary advance
- HR multi-company helpers
- reminders and other HRMS utilities

Strengths:
- brings optional side modules that may be useful later
- includes payroll-accounting bridge
- `hr_payroll_account_community` has tests in this checkout

Weaknesses:
- duplicate technical module name `hr_payroll_community`
- `ohrms_core` is too coupled to be Kodoo foundation

### Payroll Recommendation

Canonical baseline:
- choose standalone `hr_payroll_community`

Optional companion:
- keep `hr_payroll_account_community`

Do not use as base:
- `ohrms_core`

Reason:
- it preserves a neutral payroll core while allowing selective Open HRMS reuse later

## 3. BR Localization / Fiscal Base

### Current Odoo 19 Native Line

Modules:
- `addons/l10n_br`
- `addons/l10n_br_sales`
- `addons/l10n_br_website_sale`

Characteristics:
- native Odoo 19 line
- low-friction fit with the current platform
- gives BR chart, taxes, document types, CPF/CNPJ, partner/company/journal adjustments, and sales bridges

Strengths:
- compatible baseline for Odoo 19
- best fit for a neutral platform that also needs USA compatibility

Weaknesses:
- not enough to satisfy the full BR fiscal/business plan by itself

### OCA 14 Fiscal Line

Modules:
- `custom_addons/l10n_br_fiscal-14.0.28.1.0/l10n_br_base`
- `custom_addons/l10n_br_fiscal-14.0.28.1.0/l10n_br_fiscal`

Characteristics:
- richer fiscal vocabulary and domain modeling
- much larger functional surface
- currently versioned for Odoo 14, not Odoo 19
- `l10n_br_base` depends on `base_address_city`, which is not present in this checkout

Strengths:
- valuable reference for tax concepts, fiscal documents, CFOP/CST/NCM/CNAE, document series, and operation modeling
- ships tests in this checkout

Weaknesses:
- not safe to treat as Odoo 19-ready baseline
- should not be installed as canonical BR base without a deliberate porting track

### BR Recommendation

Canonical baseline now:
- `l10n_br`
- `l10n_br_sales`
- `l10n_br_website_sale`

Use the OCA 14 line as:
- reference material
- data model inspiration
- tax/fiscal vocabulary source

Do not adopt now as baseline:
- `l10n_br_base`
- `l10n_br_fiscal`

## Final Canonical Stack Decision

Accounting:
- `accountant` + `om_account_accountant-*`

Payroll:
- standalone `hr_payroll_community`
- optional `hr_payroll_account_community`

BR baseline:
- `l10n_br`
- `l10n_br_sales`
- `l10n_br_website_sale`

BR deep fiscal/business layer:
- build in `br_*`

Optional donor stacks:
- `base_accounting_kit`
- `dynamic_accounts_report`
- selected Open HRMS side modules
- selected concepts from `l10n_br_fiscal`

Operational rule for donor stacks:
- donor features must land as optional named `br_*` modules
- donor stacks must not become a hidden second foundation under the canonical baseline
- a USA customer should keep running on the neutral accounting baseline without loading BR donor modules

## Immediate Follow-up

1. Remove duplicate technical modules from the active addons path strategy.
2. Keep a single official source for `hr_payroll_community`.
3. Keep a single official accounting baseline centered on `accountant`.
4. Start scaffolding:
   - `custom_addons/br_base`
   - `custom_addons/br_account`
   - `custom_addons/br_tax_engine`
