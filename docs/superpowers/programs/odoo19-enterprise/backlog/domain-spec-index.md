# Domain Spec Index

## Document Control

| Field | Value |
| --- | --- |
| Program | Odoo 19 CE Program |
| Artifact | Child-spec control index |
| Artifact status | Active baseline |
| Baseline source | [2026-10-04-odoo19-ce-enterprise-blueprint-design.md](../../../specs/2026-10-04-odoo19-ce-enterprise-blueprint-design.md) |
| Owner | Program lead |
| Reviewer | Technical supervisor |
| Approvers | Business owner; Technical supervisor |
| Last updated | 2026-11-01 |
| Review cadence | Update whenever a child spec is created, approved, or resequenced |
| Validator expectation | Keep this file present at the manifest path |

## Required Child Specs

- [x] Wave 0 - Foundation platform, governance, and KPI/reporting baseline
- [ ] Wave 1 - Commercial and financial core
- [ ] Wave 2 - Custom finance controls
- [ ] Wave 3 - Sales Services and after-sales
- [ ] Wave 4 - Logistics extensions
- [ ] Wave 5 - HR and operational enablement

## Wave 1 Baseline Snapshot

| Domain | Current baseline status | Primary evidence | Remaining gap before Wave 1 closure |
| --- | --- | --- | --- |
| Contacts | Approved and implemented | `custom_addons/od19_contacts_partner_roles/` | No major design gap; keep regression-free while closing Accounting |
| Sales | Approved and implemented; customer risk gate implemented and verified on `odoo19_pdev` (24/24 tests pass, 2026-10-11); owner KPI menu actions added and verified (2026-10-12) | `custom_addons/od19_sales_project_context/`, `custom_addons/od19_sales_contract_core/`, `custom_addons/od19_sales_billing_evidence/`, `custom_addons/od19_sales_reporting/`, `custom_addons/od19_sales_oca_bridge_workflow/`, `custom_addons/od19_sales_customer_risk_gate/`, [2026-10-07-odoo19-enterprise-wave-1-customer-risk-credit-gate-design.md](../../../specs/2026-10-07-odoo19-enterprise-wave-1-customer-risk-credit-gate-design.md) | No major design gap; keep regression-free while closing Wave 1 |
| Project &amp; Analytic Accounting | **Implemented 2026-10-20** (W1-PROJECT-ANALYTIC, D1–D7); Project P&amp;L now reads `account.analytic.line` + `analytic_profitability`; 65 domain tests pass (`0 failed, 0 error(s)`) | Odoo 15 legacy: `autoinfo_project`, `autoinfo_project_form`, `autoinfo_project_risk_report`, `dtr_project`, `project_type`; Odoo 19 current: `custom_addons/od19_project_analytic/`, `custom_addons/od19_project_document_sequence/`, `custom_addons/od19_project_enhanced/`, `custom_addons/od19_sales_project_context/`, [2026-10-20-odoo19-enterprise-wave-1-project-analytic-accounting-design.md](../../../specs/2026-10-20-odoo19-enterprise-wave-1-project-analytic-accounting-design.md) | No major design gap; keep regression-free while closing Wave 1 |
| Purchase | Approved and implemented | `custom_addons/od19_purchase_procurement_core/` | Keep stable and verify handoff into Inventory and Accounting |
| Inventory | Approved and implemented | `custom_addons/od19_inventory_execution_control/`, `custom_addons/od19_inventory_audit_count/`, `custom_addons/od19_inventory_reporting/` | Keep stable and harden lot/serial plus adjustment governance without reopening Wave 1 scope |
| Accounting | Approved and implemented; merged to 19.0 mainline and verified on `odoo19_pdev` (35/35 tests pass, 2026-10-11) | `custom_addons/od19_accounting_operational_closure/`, `custom_addons/od19_accounting_reporting/`, [2026-10-07-odoo19-enterprise-wave-1-accounting-operational-closure-design.md](../../../specs/2026-10-07-odoo19-enterprise-wave-1-accounting-operational-closure-design.md), [2026-10-07-odoo19-enterprise-wave-1-accounting-operational-closure-implementation-plan.md](../../../plans/2026-10-07-odoo19-enterprise-wave-1-accounting-operational-closure-implementation-plan.md), master-plan backlog decisions, and the split defined in [2026-10-07-odoo19-enterprise-wave-1-customer-risk-credit-gate-design.md](../../../specs/2026-10-07-odoo19-enterprise-wave-1-customer-risk-credit-gate-design.md) | Keep regression-free; deep finance controls, credit limits, overdue holds, and approval tiers stay in Wave 2 |

## Wave 0

| Item | Status | Primary artifact |
| --- | --- | --- |
| Foundation and governance baseline | Approved | [2026-10-04-odoo19-enterprise-wave-0-foundation-governance-design.md](../../../specs/2026-10-04-odoo19-enterprise-wave-0-foundation-governance-design.md) |
| Implementation pack | Released baseline package | [2026-10-04-odoo19-enterprise-wave-0-foundation-governance-implementation-plan.md](../../../plans/2026-10-04-odoo19-enterprise-wave-0-foundation-governance-implementation-plan.md) |
| Handoff to Wave 1 | Active baseline | [wave-1-handoff-baseline.md](../governance/wave-1-handoff-baseline.md) |

Wave 0 is packaged and citable for Wave 1 planning, but the linked discovery artifacts remain active partial baselines rather than completed evidence packs.

## Child Spec Register

| Wave | Child spec ID | Canonical child spec title | Child spec path placeholder | Status | Owner | Reviewer | Approvers | Dependencies | Discovery evidence | Gate readiness |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Wave 0 | W0-FOUNDATION | Foundation platform, governance, KPI/reporting baseline, and **Thai Font & UI Localization** | [2026-10-04-odoo19-enterprise-wave-0-foundation-governance-design.md](../../../specs/2026-10-04-odoo19-enterprise-wave-0-foundation-governance-design.md) | Approved — Thai Font & UI Localization scope added 2026-10-13 | Program lead | Technical supervisor | Business owner; Technical supervisor | Discovery pack; engineering standards; review gates; **Thai font standard from Odoo 15 legacy** | [current-state-inventory.md](../discovery/current-state-inventory.md); [access-readiness-checklist.md](../discovery/access-readiness-checklist.md); [engineering-standards.md](../foundation/engineering-standards.md); [review-gates.md](../governance/review-gates.md); **Odoo 15 legacy font configuration** | Ready when the foundation child spec is approved, execution order is agreed, **and Thai font standard is confirmed across Web UI, QWeb Reports, JasperReports, and Email Templates** |
| Wave 1 | W1-COMMERCIAL-CORE | Commercial and financial core | No single combined spec — Wave 1 rolls up the per-domain child specs (Contacts, Sales, Project &amp; Analytic, Purchase, Inventory, Accounting) | In execution — customer risk gate merged/verified (2026-10-11); owner KPIs confirmed with menu actions (2026-10-12); Accounting merged to 19.0 mainline and verified (35/35 tests, 2026-10-11); Project &amp; Analytic Accounting implemented 2026-10-20 and awaiting business-owner verification on `odoo19_pdev`; migration assumptions pending business-owner acceptance | Commercial domain lead | Technical supervisor | Business owner; Technical supervisor | Wave 0 baseline package released; Wave 1 Sales baseline approved; Wave 1 Contacts baseline approved; Wave 1 Project &amp; Analytic Accounting baseline implemented 2026-10-20 (W1-PROJECT-ANALYTIC); Wave 1 Purchase baseline approved; Wave 1 Inventory baseline approved and merged on mainline; Wave 1 Accounting child spec approved, merged on mainline, and verified | Discovery baselines remain partial for access, integration, and data-quality evidence, while implementation evidence is active for the commercial core | Ready when the customer risk gate is implemented ✅, Wave 1 owner KPIs are confirmed ✅, Project &amp; Analytic Accounting is implemented ✅ (2026-10-20) and verified on `odoo19_pdev` ⏳, and migration assumptions for the commercial core are accepted ⏳ |
| Wave 1 | W1-PROJECT-ANALYTIC | Project &amp; Analytic Accounting | [2026-10-20-odoo19-enterprise-wave-1-project-analytic-accounting-design.md](../../../specs/2026-10-20-odoo19-enterprise-wave-1-project-analytic-accounting-design.md) | **Implemented 2026-10-20** — D1–D7 delivered in `od19_project_analytic`, `od19_project_document_sequence`, `od19_project_enhanced`; 65 domain tests pass (`0 failed, 0 error(s)`); awaiting business-owner verification on `odoo19_pdev` | Project &amp; Analytic domain lead | Technical supervisor | Business owner; Technical supervisor | Wave 0 baseline package released; Wave 1 Sales baseline approved (`od19_sales_project_context`); Wave 1 Contacts baseline approved; Wave 1 Accounting baseline approved; existing Odoo 19 Project modules (`od19_project_analytic`, `od19_project_document_sequence`, `od19_project_enhanced`) were in an uncommitted refactor at discovery time; they are now committed and implemented as the approved baseline (see status) | Odoo 15 legacy `autoinfo_project`, `autoinfo_project_form`, `autoinfo_project_risk_report`, `dtr_project`, `project_type`; Odoo 19 `custom_addons/od19_project_analytic/`, `custom_addons/od19_project_document_sequence/`, `custom_addons/od19_project_enhanced/`, `custom_addons/od19_sales_project_context/`; `Odoo15Backup/odoo15_oca_mapping.xlsx` | ✅ 2026-10-20 — implemented and regression-tested; next gate is business-owner verification on `odoo19_pdev` |
| Wave 1 | W1-PURCHASE-REVISION | Purchase Revision (Purchase Order) | [2026-10-16-odoo19-purchase-revision-design.md](../../../specs/2026-10-16-odoo19-purchase-revision-design.md) | In review — design approved 2026-10-16; document review pending | Procurement domain lead | Technical supervisor | Business owner; Technical supervisor | Wave 1 Purchase baseline approved (`od19_purchase_procurement_core`); core module `purchase`; `Purchase Director` group (`od19_purchase_procurement_core.group_purchase_director`) | Core `addons/purchase/models/purchase_order.py`, `addons/purchase/report/purchase_order_templates.xml`; `custom_addons/od19_purchase_document_sequence/`; `custom_addons/od19_purchase_procurement_core/security/purchase_director_security.xml`; `custom_addons/od19_iso_document_control/report/iso_footer_templates.xml` | Ready when revision naming, state flow, and printed-revision design are reviewed and approved; scope limited to Purchase Order and must not alter the existing ISO footer |
| Wave 2 | W2-FINANCE-CONTROLS | Custom finance controls | [2026-10-21-odoo19-enterprise-wave-2-custom-finance-controls.md](../../../specs/2026-10-21-odoo19-enterprise-wave-2-custom-finance-controls.md) | **Implemented** — spec synced 2026-10-21 to disk state; core finance controls present (Advance `od19_accounting_advance`, Cheque `od19_accounting_cheque`, Money In `od19_accounting_money_in_report`, WHT advisory `od19_accounting_features`, Petty Cash `od19_accounting_petty_cash`, Payment Fee `od19_accounting_payment_fee`, Fixed Assets via OCA `account_asset_management`, Jasper foundation `od19_reporting_jasper`); scope expanded 2026-10-12 (WHT, Petty Cash, Fiscal Year &amp; Year-End Closing, Fixed Assets, Jasper Reports, **Dual Report Format**) and 2026-10-13 (**Thai Localization**, **Payment Preparation วิธีที่ 3**); **Payment Preparation closed** by `od19_accounting_payment_voucher_reports` (Payment Voucher PV + Payment Receipt RV QWeb reports + `od19_voucher_no` on `account.payment`); **Year-End Closing decided = Manual no-code** on core lock dates (no custom module) | Finance controls lead | Technical supervisor | Business owner; Technical supervisor | Wave 1 approved or explicitly decoupled; Wave 1 accounting operational-closure baseline; OCA `l10n_th_account_tax`, `account_asset_management`, `account_fiscal_year`, `base_tier_validation` present on disk | Verified disk state 2026-10-21: WHT GL comes from OCA `l10n_th_account_tax` (no custom WHT module); fiscal periods come from OCA `account_fiscal_year` (no year-end-closing wizard — closing is manual no-code on core lock dates); Payment Preparation implemented in `od19_accounting_payment_voucher_reports` (`od19_voucher_no` + PV/RV via `od19_accounting_document_sequence`); OCA `account_financial_report`/`account_payment_order` absent; legacy Odoo 15 finance addon source not on disk | Payment Voucher/Receipt + PV/RV sequence pass post-install tests on `odoo19_pdev` ✅ (3/3, 2026-10-21); wider finance controls verified on `odoo19_pdev` ✅ (`0 failed, 0 error(s) of 124 tests`, 2026-10-21); remaining — dual-report/Thai-localization scope confirmation ⏳ |
| Wave 2 | W2-PAYABLE-CONTROL-GATE | Payable Control Gate — enforce Prepare→Approve + Three-Way Match | [2026-11-01-od19-payable-control-gate-design.md](../../../specs/2026-11-01-od19-payable-control-gate-design.md) | P1 in progress — design drafted 2026-11-01; **T1–T8 implemented and verified 2026-11-01** (settings + hook + `action_post` guard; override/audit; SoD; security groups; three-way match config; AP SOP for Block/Group Payments); T9–T10 pending (full P1 TDD sync + UAT) | Finance controls lead | Technical supervisor | Business owner; Technical supervisor | Wave 2 W2-FINANCE-CONTROLS baseline (Payment Preparation in `od19_accounting_payment_voucher_reports`); core `account.payment.register` `group_payment` (CE); core `purchase` Bill Control (On received quantities); Odoo 15 legacy `od15_autoinfo_account_prepayment` (`dtr.account.prepayment`) | Confirmed from code 2026-11-01: `action_post()` did not check `od19_prepare_state`; `action_od19_approve()` had no SoD check; Odoo 19 **CE does not ship** `account_batch_payment` (Enterprise) so Group Payments replace batch payment; `product.purchase_method='receive'` drives `qty_to_invoice = qty_received − qty_invoiced` in `addons/purchase/models/purchase_order_line.py` | Ready when business owner approves P1 scope (enforce gate + 3-way match + block payment) and `od19_enforce_prepare_approval` rollout (default off) is confirmed; T9–T10 (full P1 TDD sync, UAT) pending |
| Wave 3 | W3-AFTER-SALES | Sales Services and after-sales | [2026-10-21-odoo19-enterprise-wave-3-sales-services-after-sales.md](../../../specs/2026-10-21-odoo19-enterprise-wave-3-sales-services-after-sales.md) | **Implemented** — spec drafted 2026-10-21 from disk state; Quality Control (`od19_quality_control`, 2026-10-12), Digital Signature (`od19_document_sign`, 2026-10-19), Service Card (`od19_service_card`), Warranty (`od19_service_warranty`), Product Return (`od19_product_return`), Sales Services via `od19_helpdesk_extension` (OCA `helpdesk_mgmt`), Internal Issue (`od19_internal_issue`), ISO Customer Satisfaction (`od19_iso_customer_satisfaction`), and after-sales KPI aggregation (`od19_after_sales_reporting`, 2026-10-21) plus the consolidated After-Sales Service Dashboard on `od19_dashboard` (same module, 2026-10-21); cross-module flow gaps closed 2026-10-21 (Ticket→Invoice idempotent + company-scoped, Claim→Repair blocked for rejected/cancelled claims, Return→Picking/Credit Note company-scoped + idempotent + invoice-line refund price); verified on `odoo19_pdev` 2026-10-21 (213 tests, `0 failed, 0 error(s)`) | Service operations lead | Technical supervisor | Business owner; Technical supervisor | Wave 1 customer/project/product baseline; OCA `helpdesk_mgmt` present (`third_party/oca/helpdesk/`); core `addons/repair/` present; confirmed separation of service returns from Inventory core | Verified disk state 2026-10-21: all after-sales flows implemented; OCA `quality_control_oca`, `sign_oca`, and OCA `repair` are **not** used — QC and signature are custom modules; Claims are distributed across Warranty/Product Return (no standalone claims module); KPI aggregation delivered as read-only `od19_after_sales_reporting` (6 SQL views) | After-sales flows and KPI views verified on `odoo19_pdev` ✅ (213 tests, `0 failed, 0 error(s)`, 2026-10-21); remaining — training implications approval ⏳ |
| Wave 4 | W4-LOGISTICS-EXT | Logistics extensions | [2026-10-21-odoo19-enterprise-wave-4-logistics-extensions.md](../../../specs/2026-10-21-odoo19-enterprise-wave-4-logistics-extensions.md) | **Partially implemented** — spec drafted 2026-10-21 from disk state; Stock Valuation Adjustment (`od19_stock_valuation_adjustment`), Transportation (`od19_transportation`), FIFO valuation (`od19_stock_fifo`), picking features (`od19_stock_picking_features`), and delivery label (`od19_delivery_label`) present; core `stock_landed_costs` available; OCA `purchase_request` + `purchase_request_type` present; Thai purchase-requisition extension `od19_purchase_request_extend` is **implemented** on disk (not a stub); dedicated internal Stock Request resolved by adopting **OCA `stock_request`** (submodule `third_party/oca/stock-logistics-request`, branch 19.0, added 2026-10-21 and wired into `odoo.conf`; includes `stock_request_purchase` auto-install); legacy `Goods Issue` **decided 2026-10-21 = keep as a Thai document/UX layer `od19_goods_issue` on OCA `stock_request`** (department/job/reason fields, per-department `GI/{DEPT}/` sequence, printable ใบเบิกสินค้า / ใบหยิบสินค้า reports); Landed Cost activation remains open | Logistics lead | Technical supervisor | Business owner; Technical supervisor | Wave 1 inventory baseline; Wave 3 dependencies as applicable; core `stock_landed_costs`; OCA `purchase_request`, `purchase_request_type`, `purchase_request_tier_validation`, `stock_request` + `stock_request_purchase` (present); legacy `Goods Issue` decision resolved 2026-10-21 | Verified disk state 2026-10-21: valuation adjustment creates journal entries and is inventory-manager-gated; Landed Cost is enablement-only (core `stock_landed_costs`); `od19_purchase_request_extend` extends OCA `purchase_request` (Thai fields + tier-validation notifications), so purchase requisition is covered; internal Stock Request covered by OCA `stock_request` (`stock.request`/`stock.request.order`, state `draft → open → done → cancel`); legacy `Goods Issue` covered by `od19_goods_issue` document layer | Ready when OCA `stock_request` and `od19_goods_issue` are installed on `odoo19_pdev`, the internal Stock Request flow is configured, Landed Cost activation and non-standard warehouse flow decisions are approved, and rollout sequencing is confirmed |
| Wave 5 | W5-HR-ENABLEMENT | HR and operational enablement | [2026-10-15-odoo19-enterprise-wave-5-hr-operational-enablement.md](../../../specs/2026-10-15-odoo19-enterprise-wave-5-hr-operational-enablement.md) | In execution — HR Expense and Fleet already live; Attendances + Time Off enabled and ZKTeco device integration delivered 2026-10-15 | HR operations lead | Technical supervisor | Business owner; Technical supervisor | Wave 0 governance baseline; standard hr_expense and fleet modules available | Discovery evidence for employees, attendances, time off, HR expense, fleet | Attendances/Time Off base modules installed and ZKTeco integration verified on `odoo19` and `odoo19_pdev`; awaiting real-device commissioning and confirmed OT policy |

## Cross-Cutting Reporting Track

The dashboard/reporting enablement specs are **not** domain waves in the Wave 0–5 roadmap. They build out the Wave 0 KPI and reporting baseline artifacts (`reporting/kpi-reporting-baseline.md`, `reporting/role-based-dashboard-blueprint.md`) and therefore sit outside the Wave 0–5 domain child-spec register. They are tracked here so the specs that label themselves "Wave 6 (Internal Operations)" stay traceable from this index.

| Track | Spec ID | Spec | Status | Notes |
| --- | --- | --- | --- | --- |
| Internal Operations / reporting enablement | W6-DASH-FORMULA-RULES | [2026-10-16-odoo19-dashboard-formula-and-status-rules-design.md](../../../specs/2026-10-16-odoo19-dashboard-formula-and-status-rules-design.md) | Implemented | Extends module `od19_dashboard`; implements the Wave 0 reporting baseline, no domain-wave scope |
| Internal Operations / reporting enablement | W6-DASH-PHASE2 | [2026-10-16-odoo19-dashboard-phase2-presentation-design.md](../../../specs/2026-10-16-odoo19-dashboard-phase2-presentation-design.md) | Implemented — phase 2 continuation of W6-DASH-FORMULA-RULES | Adds visibility/alert rules, conditional formatting, formula library, cross-source widgets |
| Internal Operations / reporting enablement | W6-DASH-PHASE3 | [2026-10-22-odoo19-dashboard-phase3-completion-design.md](../../../specs/2026-10-22-odoo19-dashboard-phase3-completion-design.md) | Draft — phase 3 continuation of W6-DASH-PHASE2 | `check_access()` cleanup, After-Sales verify closure, per-domain boards (Finance/Logistics/HR), blueprint/KPI doc sync |

## Wave Sequencing Notes

- Wave 1 remains the active closure target. Accounting and the customer risk gate are both merged/verified on the mainline workspace (2026-10-11); owner KPI menu actions were added and verified on 2026-10-12; Project &amp; Analytic Accounting was implemented 2026-10-20. Remaining Wave 1 work is business-owner verification of Project &amp; Analytic Accounting on `odoo19_pdev` and migration-assumption acceptance by the business owner.
- Wave 0 is already released as the planning baseline package for Wave 1, but that does not convert the discovery artifacts into complete evidence; keep open discovery gaps visible until they are actually closed.
- Wave 1 should absorb only the customer risk gate baseline needed to stop blacklist sales and unapproved credit sales; it should not become the home of full finance-led credit control.
- Wave 1 must include **Project &amp; Analytic Accounting** (gap identified 2026-10-12; child spec **W1-PROJECT-ANALYTIC** drafted 2026-10-20): use standard `project.project` with `job_no`, project type (`od19_project_type`), owning department (`od19_department_id`), project owner, contractor links, and auto-created `analytic_account_id`. This is required for Sales (contract context), Purchase (project on PO lines), and Accounting (project P&amp;L). The bridge to the standard project model is already in place — `od19_sales_project_context` links `sale.order.od19_project_id` to `project.project`, so no custom `od19.sales.project` model exists. The 2026-10-12 wording that described `job_type` and a `department` Char field is superseded by the approved field-ownership map. **Implemented 2026-10-20** (W1-PROJECT-ANALYTIC): Job Type is Sale/Service/PM/Job (Job `J`, PM `PM`, Service `S`, Sales `S`); the Sales-type job number is built as `S + initials + YY + running number` (e.g. `SNV26-0001`), where the initials are derived automatically from the salesperson name (overridable with `od19_initials`) and the salesperson sequence supplies only the running counter (its prefix is ignored). Project P&amp;L is read from `account.analytic.line` + the core `analytic_profitability` classification (single P&amp;L contract, no re-implementation), and the risk levels are high ≥ 70 / medium ≥ 40 with the margin rule skipped while revenue is 0.
- Wave 1 Accounting should close AR, AP, payment, reconciliation, and essential posting/tax mapping as an operational baseline without absorbing Wave 2 control depth.
- Wave 2 should absorb finance controls and legacy reports only when they extend owner decision quality without re-opening Wave 1 boundaries.
- Wave 2 should take over deep credit-control behavior such as credit limits, overdue holds, approval tiers, and exception governance after the Wave 1 customer risk gate stabilizes.
- Wave 3 should own service-linked returns, warranty-linked stock behavior, and after-sales process complexity rather than pushing that logic back into Inventory.
- Wave 4 should own logistics extensions, adopt **OCA `stock_request`** for internal stock requests (decided 2026-10-21), and keep legacy `Goods Issue` as a Thai document/UX layer delivered by **`od19_goods_issue`** on top of OCA `stock_request` (decided 2026-10-21) instead of copying the legacy model.
- **Dual Report Format (ทุก Wave)**: ทุกรายงานที่ **พิมพ์ออกมาจากระบบ (printable reports)** ต้องมีทั้งรูปแบบ Odoo 19 CE Native (QWeb) และรูปแบบ Odoo 15 CE Legacy Compatible (JasperReports/JRXML) พร้อมกัน ไม่รวม KPI Dashboard หรือรายงานบนหน้าจอ (on-screen) ดูรายละเอียดใน `reporting/kpi-reporting-baseline.md` ส่วน Dual Report Format Requirement
- **Thai Font & UI Localization (Wave 0, ใช้ได้ทุก Wave)**: ระบบต้องรองรับฟอนต์ภาษาไทยในทุกส่วน โดยใช้ฟอนต์หลักมาตรฐาน (1-2 ชุด) พร้อมสไตล์ Regular, Bold, Italic, Bold Italic — Web UI/QWeb ใช้ Sarabun/Noto Sans Thai; JasperReports (Legacy) ใช้ฟอนต์เดิมจาก Odoo 15; ฟอนต์ต้องติดตั้งบน server สำหรับ PDF; ไม่แนะนำให้ผู้ใช้เปลี่ยนฟอนต์ทุกสไตล์เพื่อรักษาความสอดคล้อง
- **Payment Preparation — วิธีที่ 3 (Wave 2, ตัดสินใจ 2026-10-13)**: ไม่สร้างโมเดล `account.payment.voucher` เอง ใช้ Odoo standard + OCA เป็นหลัก: (1) ตั้งหนี้ใช้ Vendor Bill/Customer Invoice มาตรฐาน, (2) จัดกลุ่มใบแจ้งหนี้ใช้ `account.payment.register` มาตรฐาน, (3) WHT ใช้ OCA `l10n_th_account_tax`, (4) Tax Invoice ใช้ OCA `l10n_th_account_tax`, (5) PND ใช้ Odoo standard `l10n_th`. Custom เพียงอย่างเดียว: รายงานใบสำคัญจ่าย (QWeb), รายงานใบสำคัญรับเงิน (QWeb), และเลขที่เอกสารไทยบน `account.payment` (~300 บรรทัด custom) — **✅ พัฒนาแล้ว 2026-10-21** ใน `od19_accounting_payment_voucher_reports` (`od19_voucher_no` + PV/RV sequence via `od19_accounting_document_sequence`)
- **Thai Localization Modules (ทุก Wave)**: Wave 0 — `od19_thai_font_support`, `od19_thai_localization_base`; Wave 1 — `od19_partner_thai_fields`, `od19_document_sequence`, `od19_thai_tax_reports`, `od19_accounting_dncn`, `od19_accounting_cheque`; Wave 2 — `od19_accounting_reporting`, `od19_accounting_payment_voucher_reports` (reports only). ใช้ OCA เป็นฐาน: `l10n_th`, `l10n_th_account_tax`, `base_tier_validation`, `account_financial_report`

## Required Fields Per Child Spec

- Scope
- Current-state summary
- Keep/refactor/replace/retire decisions
- Future-state process
- Reporting and KPI needs
- Security and approval model
- Migration assumptions
- Training impact
- Child spec ID and wave reference
- Canonical child spec path and traceability back to [domain-wave-matrix.md](domain-wave-matrix.md)
- Owner, technical reviewer, approvers, and current status
- Discovery evidence references and source locations
- Dependency map, predecessor waves, and known blockers
- Approvers, approval dates, and approval notes
- Gate readiness summary for spec-ready, plan-ready, and build-ready checkpoints

## Child Spec Header Schema

```markdown
# <Child Spec Title>

## Control Metadata
- Child spec ID: <W0-W5 code>
- Wave: <Wave 0-5>
- Status: <Not started | In discovery | Draft | In review | Approved | Ready for plan>
- Owner: <role or named owner>
- Reviewer: <technical reviewer role or named reviewer>
- Approvers: <business owner>; <technical supervisor>
- Canonical path: <docs/superpowers/specs/...>
- Source backlog row: `backlog/domain-wave-matrix.md`

## Discovery Evidence
- Current-state references: <links to discovery artifacts, screenshots, exports, notes>
- Evidence coverage gaps: <known unknowns that must be closed before approval>

## Delivery Controls
- Dependencies: <waves, specs, systems, or data prerequisites>
- Gate readiness:
  - Spec-ready: <criteria>
  - Plan-ready: <criteria>
  - Build-ready: <criteria>
```

## Control Rules

- Do not mark a child spec ready unless its evidence, reviewer input, and approvers are recorded.
- Keep wave naming, child-spec IDs, and path placeholders synchronized with [domain-wave-matrix.md](domain-wave-matrix.md).
- Promote a child spec to `Ready for plan` only after business and technical review are both complete.
- Keep this index synchronized with the master-plan section `Wave Planning Update After Inventory Baseline` when post-review scope or sequencing changes.

## Review Checkpoints

- Business owner approval required before a child spec is marked ready
- Technical supervisor approval required before an implementation plan is written
- Owner-reporting impact must be confirmed before build starts
