# Gap Analysis: Odoo 15 (DTR / odoo15_mods) → Odoo 19 (od19_*)

**วันที่วิเคราะห์:** 2026-10-31
**ขอบเขต:** ตระกูลโมดูล `dtr_*` และโมดูลประกอบใน `odoo15_mods`, `odoo15_mods_accounting`, `odoo15_mods_sales`, `odoo15_mods_purchase`, `odoo15_mods_sales_services`, `odoo15_mods_manufacturing`
**เอกสารคู่กัน:** `GAP_ANALYSIS_OD15_to_OD19.md` (ครอบเฉพาะตระกูล `custom15_autoinfo`) — เอกสารนี้ **ไม่ซ้ำ** กับฉบับนั้น
**วิธีการ:** เทียบ `__manifest__.py` + name/summary ของทุกโมดูล OD15 กับโมดูล `od19_*` (88 โมดูล) และ OCA ใน `third_party/oca` ที่มีอยู่จริงบนดิสก์

> ⚠️ **หมายเหตุ:** เอกสารนี้จัดทำจากการเทียบ manifest และรายการโมดูลบนดิสก์
> **อัปเดต 2026-10-31:** ได้ตรวจ source ระดับ model ของกลุ่มที่เคยระบุ ❓ ครบทั้ง 11 รายการแล้ว — ผลสรุปอยู่ในคอลัมน์ "สถานะ" ของแต่ละตาราง และในหัวข้อ 9
> เซลล์ที่ระบุ **"ต้องตรวจสอบ"** = ยังไม่มีหลักฐานยืนยันการแมป ให้ตรวจก่อนปิด gap

> 🗄️ **ทะเบียนโมดูลจริงต้นทาง (DB `AUTOERP-PRD`, 2026-10-31) — dump `od15_autoerp_prd.dump` 10.07 MB**
> ต้นทางเป็น Odoo 15 CE จริง (ทุกโมดูลหลัก `15.0.1.x`; `base|15.0.1.3`) นับจาก `migration/od15_export/modules.txt` (170 รายการ):
> **installed = 123 · uninstalled = 46 · uninstallable = 1**
> · ⛔ **uninstalled ที่ต้นทาง → ไม่มีข้อมูลให้ย้าย = Retire/Defer ได้ทันที (46 ตัว):** MRP ทั้งตระกูล (`dtr_mrp`, `_project`, `_report`, `_setting`, `_tier_validation`, `_warranty_card`, `dtr_access_right_mrp`, `dtr_stock_fifo_mrp`, `dtr_product_part_history_with_mrp`, `dtr_erp_package_manufacturing`), `dtr_landed_cost`, `dtr_sql_command`, `dtr_project`, `dtr_stock_adjustment`, `dtr_expense_project`, `dtr_invoice_project`, `dtr_purchase_project`, `dtr_petty_cash_project`, `dtr_advance_project`, `dtr_inventory_project`, `dtr_logistics_project`, `dtr_goods_issue_project`, `dtr_sales_services_project`, `dtr_coa_alternative`, `dtr_database_cleanup`, `dtr_m2o_no_create`, `dtr_product_access_rules`, `dtr_account_non_anglo_saxon`, `dtr_upload_product_picture`, `dtr_general_journal_enterprise`, `dtr_taxation_enterprise`, `dtr_payment_combine_vat_lines`, `dtr_invoice_unlock_six_month`, `dtr_purchase_multi_company`, `dtr_document_sequence_group*` (4), `dtr_approval_levels_project/_reject_comment/_step`, `dtr_project_analysis_approval`, `dtr_qc_approval`, `dtr_stock_approval`, `dtr_stock_valuation_adjustment_approval`, `dtr_goods_issue_approval`
> · ✅ **installed ที่ต้นทางและต้องย้าย (ยืนยัน 2026-10-31):** `dtr_stock_backdating` (15.0.1.0), `dtr_account_cash` + `dtr_account_cash_with_purchase` + `dtr_account_cash_with_sales` (ติดตั้งทั้ง 3), `dtr_sales_revision`, `dtr_approval_levels_base` (15.0.1.8)
> · ℹ️ `autoinfo_*` ติดตั้งจริงเพียง 4 ตัว: `autoinfo_account`, `autoinfo_project`, `autoinfo_purchase`, `autoinfo_sale`
> · ℹ️ `dtr_sales_services_qc` = uninstallable (ไม่มีข้อมูล)

> **สถานะการติดตั้งจริง (DB `odoo19_pdev`, 2026-10-31):** โมดูล `od19_*` ทั้งหมด **installed ครบ 100%**
> · OCA ที่ **uninstalled**: `database_cleanup`, `base_global_discount`, `purchase_triple_discount`, `sale_order_general_discount`, `sale_tier_validation`, `purchase_tier_validation`, `stock_picking_tier_validation`, `hr_expense_tier_validation`, `base_substate`, `stock_request_purchase`, `mrp`
> · OCA ที่ **ยังไม่มีใน DB**: `l10n_th_withholding_tax`, `account_statement_import`, `account_statement_import_file`, `stock_no_negative`, `account_move_line_reconcile_manual`, `account_asset`

**คำอธิบายการตัดสินใจ (Migration Decision):**

| สัญลักษณ์ | ความหมาย |
|-----------|----------|
| **Keep** | เก็บตรรกะ/โมดูลเดิม แทบไม่แก้ |
| **Refactor** | ยกตรรกะเดิมมาเขียนใหม่บนมาตรฐาน Odoo 19 |
| **Replace** | แทนด้วยโมดูล `od19_*` หรือ OCA/Standard ที่มีอยู่แล้ว |
| **Retire** | ไม่ยกมา (ซ้ำซ้อน / ไม่มีมูลค่า / ใช้ Standard แทน) |

**สถานะความครอบคลุม:** ✅ ครบถ้วน · 🟡 บางส่วน · ❌ ยังไม่มี

---

## สรุปตัวเลข

| กลุ่มโมดูล OD15 | จำนวนโมดูล | Keep | Refactor | Replace | Retire | ต้องตรวจสอบ |
|-----------------|-----------|------|----------|---------|--------|-------------|
| `odoo15_mods` (Base/Core/Stock/Product) | 49 | 2 | 14 | 14 | 14 | 5 |
| `odoo15_mods_accounting` | 55 | 0 | 15 | 20 | 17 | 3 |
| `odoo15_mods_sales` | 20 | 0 | 8 | 6 | 5 | 1 |
| `odoo15_mods_purchase` | 14 | 0 | 5 | 3 | 5 | 1 |
| `odoo15_mods_sales_services` | 11 | 0 | 3 | 4 | 4 | 0 |
| `odoo15_mods_manufacturing` | 10 | 0 | 1 | 2 | 6 | 1 |
| **รวม (โดยประมาณ)** | **159** | **2** | **46** | **49** | **51** | **0** |

> ตัวเลขเป็นการจับกลุ่มเชิงแผน (planning-level) — คอลัมน์ "ต้องตรวจสอบ" เป็น **0** แล้ว เพราะได้ตรวจ source ระดับ model ของกลุ่ม ❓ ครบทั้ง 11 รายการเมื่อ 2026-10-31 (ดูหัวข้อ 9)
> ผลตรวจ: ✅ ปิดได้ 3 · 🟡 รอติดตั้ง/ยืนยันขอบเขต 2 · ❌ ต้อง develop ใหม่ 5

---

## 1. Base / Core / Stock / Product (`odoo15_mods`)

| # | โมดูล OD15 | ชื่อ | การตัดสินใจ | โมดูล OD19 / แทนที่ | สถานะ |
|---|-----------|------|-----------|---------------------|-------|
| 1 | `dtr_common` | Common code sharing | Retire | ใช้ Python mixin / abstract model ใน `od19_*` แทน | ✅ |
| 2 | `dtr_settings` | Custom Settings | Refactor | Odoo 19 Settings + `od19_ui_defaults` | 🟡 |
| 3 | `dtr_company` | Company extension | Refactor | `od19_partner_thai_fields` (สาขา/เลขภาษี) | 🟡 |
| 4 | `dtr_coa` | Chart of Accounts (Thailand) | Replace | Odoo `l10n_th` + `od19_thai_localization_base` | ✅ |
| 5 | `dtr_access_right_base` | Access Right Base | Replace | `od19_security_roles` (RBAC + `base_user_role`) | ✅ |
| 6 | `dtr_access_right_base_partner_rules` | Partner record rules | Replace | `od19_security_roles` / `od19_contacts_partner_roles` | ✅ |
| 7 | `dtr_partner_master` | Partner Master | Refactor | `od19_contacts_partner_roles` + `od19_partner_thai_fields` | 🟡 |
| 8 | `dtr_employee_master` | Employee Master | Replace | Odoo `hr` + `od19_hr_attendance_zkteco` | 🟡 |
| 9 | `dtr_database_cleanup` | Database Cleanup | Replace | OCA `database_cleanup` (server-tools) | ✅ |
| 10 | `dtr_sql_command` | Execute SQL Command | Retire | ไม่ยกมา — ความเสี่ยงด้านความปลอดภัย | ✅ |
| 11 | `dtr_m2o_no_create` | Many2one no_create | Refactor | Odoo 19 `options` บน field / OCA `base_optional_quick_create` | 🟡 |
| 12 | `dtr_report_base` | Report Configurations | Replace | `od19_reporting_jasper` | ✅ |
| 13 | `dtr_jasper` | Jasper integration | Replace | `od19_reporting_jasper` + `od19_sale_jasper` | ✅ |
| 14 | `dtr_jasper_auto_active` | Jasper Auto Active | Refactor | `od19_reporting_jasper` | 🟡 |
| 15 | `dtr_document_sequence_group` | Document Sequence Group | Replace | `od19_document_sequence` | ✅ |
| 16 | `dtr_exchange_rate` | Multi Currencies | Replace | OCA `currency_rate_update` + `od19_currency_rate_bot` | ✅ |
| 17 | `dtr_product_master` | Product Master | Refactor | Odoo `product` + `od19_misc_features` | 🟡 |
| 18 | `dtr_product_category` | Product Category | Refactor | Odoo `product` (standard categories) | 🟡 |
| 19 | `dtr_product_access_rules` | Product Access Rules | Replace | `od19_security_roles` | 🟡 |
| 20 | `dtr_product_part_history` | Product Part History | ยังไม่มีปลายทาง | ตรวจ source แล้ว: ไม่พบโมเดล/ตรรกะเทียบเท่าใน OD19 — ต้อง develop ใหม่ หรือ Retire ถ้าไม่มี use case | ❌ |
| 21 | `dtr_upload_product_picture` | Product Image Upload | Retire | Odoo 19 standard image import | ✅ |
| 22 | `dtr_taxes` | Taxes Master | Replace | OCA `l10n_th_account_tax` | ✅ |
| 23 | `dtr_taxes_with_coa` | Taxes with COA | Replace | OCA `l10n_th_account_tax` | ✅ |
| 24 | `dtr_project` | Project Task Management | Replace | `od19_project_enhanced` | ✅ |
| 25 | `dtr_stock` | Stock | Refactor | Odoo `stock` + `od19_stock_picking_features` | 🟡 |
| 26 | `dtr_stock_form` | Stock Form Documents | Replace | `od19_stock_picking_features` | ✅ |
| 27 | `dtr_stock_report` | Stock Documents | Replace | `od19_inventory_reporting` | ✅ |
| 28 | `dtr_stock_adjustment` | Stock Adjustment | Replace | Odoo 19 standard inventory adjustment | ✅ |
| 29 | `dtr_stock_valuation_adjustment` | Stock Valuation Adjustment | Replace | `od19_stock_valuation_adjustment` | ✅ |
| 30 | `dtr_stock_valuation_adjustment_tier_validation` | Tier Validation | Retire | OCA `base_tier_validation` (configure rule) | ✅ |
| 31 | `dtr_stock_tier_validation` | Stock Tier Validation | Retire | OCA `stock_picking_tier_validation` | ✅ |
| 32 | `dtr_stock_fifo` | Stock FIFO | Replace | `od19_stock_fifo` | ✅ |
| 33 | `dtr_stock_backdating` | Stock Backdating | Replace | `od19_inventory_execution_control` (**installed 2026-10-31**) — ตรวจ source แล้วครอบ use case back-dating; **ต้นทางติดตั้งจริง 15.0.1.0 (2026-10-31)** | ✅ |
| 34 | `dtr_inventory_overview` | Inventory Overview | Refactor | `od19_inventory_reporting` | 🟡 |
| 35 | `dtr_inventory_project` | Inventory Project | Refactor | `od19_inventory_execution_control` | 🟡 |
| 36 | `dtr_inventory_department` | Inventory Department | Refactor | `od19_inventory_execution_control` | 🟡 |
| 37 | `dtr_inventory_filter` | Inventory Filters | Retire | รวมเข้า Odoo standard search filters (หลักการ 2) | ✅ |
| 38 | `dtr_landed_cost` | Landed Cost | Replace | core `stock_landed_costs` | 🟡 |
| 39 | `dtr_goods_issue` | Goods Issue (ใบเบิก/ใบหยิบ) | Keep | `od19_goods_issue` (ชั้นเอกสารไทยบน OCA `stock_request`) | ✅ |
| 40 | `dtr_goods_issue_project` | Goods Issue Project | Refactor | `od19_goods_issue` | ✅ |
| 41 | `dtr_goods_issue_tier_validation` | GI Tier Validation | Retire | OCA `base_tier_validation` | ✅ |
| 42 | `dtr_vendor_bills` | Vendor Bills fields | Refactor | Odoo standard + `od19_accounting_features` | 🟡 |
| 43 | `dtr_customer_invoices` | Customer Invoices fields | Refactor | Odoo standard `account.move` | 🟡 |
| 44 | `dtr_invoicing_report` | Invoicing Report | Replace | `od19_accounting_reporting` | ✅ |
| 45 | `dtr_invoicing_discount` | Accounting Discount | Refactor | OCA `base_global_discount` / `od19_accounting_features` | 🟡 |
| 46 | `dtr_warranty` | Warranty Card | Replace | `od19_service_warranty` | ✅ |
| 47 | `dtr_erp_package_core` | ERP Package Core | Retire | Odoo 19 resolve dependency เอง | ✅ |
| 48 | `stock_no_negative` | Stock Disallow Negative | Keep | OCA `stock_no_negative` — ✅ มีใน OCA v19 แต่ **ยังไม่ติดตั้งใน DB** (ดู R09) | ✅ |
| 49 | `internal_transfers_product_filter` | Internal Transfer Filter | Retire | Odoo 19 standard | ✅ |

---

## 2. Accounting (`odoo15_mods_accounting`)

| # | โมดูล OD15 | ชื่อ | การตัดสินใจ | โมดูล OD19 / แทนที่ | สถานะ |
|---|-----------|------|-----------|---------------------|-------|
| 1 | `dtr_advance` | Advance (เงินทดรอง) | Replace | `od19_accounting_advance` | ✅ |
| 2 | `dtr_advance_project` | Advance Project | Refactor | `od19_accounting_advance` | ✅ |
| 3 | `dtr_advance_tier_validation` | Advance Tier Validation | Retire | OCA `base_tier_validation` | ✅ |
| 4 | `dtr_cheque` | Cheque | Replace | `od19_accounting_cheque` | ✅ |
| 5 | `dtr_petty_cash` | Petty Cash | Replace | `od19_accounting_petty_cash` | ✅ |
| 6 | `dtr_petty_cash_project` | Petty Cash Project | Refactor | `od19_accounting_petty_cash` | ✅ |
| 7 | `dtr_petty_cash_tier_validation` | PC Tier Validation | Retire | OCA `base_tier_validation` | ✅ |
| 8 | `dtr_payment_fee` | Payment Fees | Replace | `od19_accounting_payment_fee` | ✅ |
| 9 | `dtr_payment_filter` | Payments Filters | Retire | รวมเข้า Odoo standard (หลักการ 2) | ✅ |
| 10 | `dtr_payment_invoice` | Payment Invoices | Refactor | Odoo standard Register Payment + `od19_accounting_features` | 🟡 |
| 11 | `dtr_payment_method` | Payment Method | Refactor | Odoo standard payment method | 🟡 |
| 12 | `dtr_payment_combine_vat_lines` | Combine VAT lines | Retire | Odoo standard (ไม่มี use case) | ✅ |
| 13 | `dtr_account_filter` | Accounting Filters | Retire | รวมเข้า Odoo standard (หลักการ 2) | ✅ |
| 14 | `dtr_account_cash` | Account Cash | ยังไม่มีปลายทาง | ตรวจ source แล้ว: family `dtr_account_cash` + `_with_purchase` + `_with_sales` ไม่มีคู่ใน OD19 — ต้อง develop ใหม่ หรือรวมเข้า cheque/advance; **ต้นทางติดตั้งจริงทั้ง 3 โมดูล (2026-10-31) → ห้าม Retire ต้องมีปลายทาง** | ❌ |
| 15 | `dtr_account_cash_with_purchase` | Cash with Purchase | ยังไม่มีปลายทาง | **แก้จากเดิม (Retire → ต้องมีปลายทาง):** ต้นทางติดตั้งจริง 15.0.1.0 และมีตาราง `dtr_account_cash_po_wizard` — ต้อง develop หรือรวมเข้า cash core | ❌ |
| 16 | `dtr_account_cash_with_sales` | Cash with Sales | ยังไม่มีปลายทาง | **แก้จากเดิม (Retire → ต้องมีปลายทาง):** ต้นทางติดตั้งจริง 15.0.1.0 และมีตาราง `dtr_account_cash_so_wizard` — ต้อง develop หรือรวมเข้า cash core | ❌ |
| 17 | `dtr_account_control_level` | Account Control Levels | ยังไม่มีปลายทาง | ตรวจ source แล้ว: ไม่มี `account.control.level` ใน core/OCA — ต้อง develop ใหม่ หรือใช้ account group/hierarchy มาตรฐานแทน | ❌ |
| 18 | `dtr_account_invoice_report` | Account Invoice Report | Replace | `od19_accounting_reporting` | ✅ |
| 19 | `dtr_account_tier_validation` | Account Tier Validation | Retire | OCA `account_move_tier_validation` | ✅ |
| 20 | `dtr_accounting_report` | Accounting Report | Replace | `od19_accounting_reporting` (หลักการ 7) | ✅ |
| 21 | `dtr_accounting_form` | Accounting Form Documents | Replace | `od19_accounting_features` | ✅ |
| 22 | `dtr_account_non_anglo_saxon` | Non Anglo Saxon | Refactor | Odoo 19 accounting config (perpetual/periodic) | 🟡 |
| 23 | `dtr_analytic_require` | Require Analytic Account | Replace | `od19_accounting_analytic_require` | ✅ |
| 24 | `dtr_billing` | Billing (ใบวางบิล) | Replace | `od19_accounting_features` | ✅ |
| 25 | `dtr_bring_forward` | Bring Forward | ยังไม่มีปลายทาง | ตรวจ source แล้ว: `od19_accounting_operational_closure` ไม่มีตรรกะ bring-forward — ยังไม่มีเทียบเท่า | ❌ |
| 26 | `dtr_deposit_payment` | Deposit Payment | Refactor | Odoo standard + `od19_accounting_features` | 🟡 |
| 27 | `dtr_down_payment` | Down Payment | Replace | `od19_sale_wizards` (downpayment invoice) | ✅ |
| 28 | `dtr_dncn` | Debit/Credit Note | Replace | `od19_accounting_dncn` | ✅ |
| 29 | `dtr_exchange_diff_partial` | Exchange diff (partial reconcile) | Refactor | Odoo 19 standard exchange diff | 🟡 |
| 30 | `dtr_exchange_rate_specific` | Multi Currencies Specific | Refactor | `od19_currency_rate_bot` + Odoo standard | 🟡 |
| 31 | `dtr_expense_project` | Expense Project | Refactor | `od19_hr_expense_enhanced` | ✅ |
| 32 | `dtr_expense_tier_validation` | Expense Tier Validation | Retire | OCA `hr_expense_tier_validation` | ✅ |
| 33 | `dtr_fixed_assets` | Fixed Assets Management | Replace | OCA `account_asset_management` | ✅ |
| 34 | `dtr_fixed_assets_report` | Fixed Asset Report | Replace | OCA `account_asset_management` + `od19_reporting_jasper` | 🟡 |
| 35 | `dtr_general_journal` | General Journal | Refactor | Odoo standard Miscellaneous journal | 🟡 |
| 36 | `dtr_general_journal_enterprise` | General Journal (Enterprise) | Retire | Odoo 19 standard menu (หลักการ 5) | ✅ |
| 37 | `dtr_invoice_project` | Invoice Project | Refactor | `od19_project_analytic` | ✅ |
| 38 | `dtr_invoice_unlock_six_month` | Unlock Invoice 6 Months | Refactor | Odoo 19 lock exception (`account.lock_exception`) | 🟡 |
| 39 | `dtr_journal_entry` | Journal Entry | Refactor | Odoo standard journal entry | 🟡 |
| 40 | `dtr_journal_entry_set_voucher_running` | Voucher Running | Refactor | `od19_accounting_document_sequence` (`od19_voucher_no`) | ✅ |
| 41 | `dtr_tax_adr` | Thai Tax Address | Replace | `od19_partner_thai_fields` | ✅ |
| 42 | `dtr_tax_txt` | Taxation For RD | Replace | `od19_thai_tax_reports` (PND/VAT export) | ✅ |
| 43 | `dtr_taxation` | Taxation (Thailand) | Replace | OCA `l10n_th_account_tax` | ✅ |
| 44 | `dtr_taxation_enterprise` | Taxation (Enterprise) | Retire | Odoo 19 standard menu (หลักการ 5) | ✅ |
| 45 | `dtr_taxation_with_coa` | Taxation with COA | Replace | OCA `l10n_th_account_tax` | ✅ |
| 46 | `dtr_year_end` | Year End | Retire | Manual no-code บน Odoo 19 lock dates (ตัดสินใจ 2026-10-21) | ✅ |
| 47 | `dtr_vendor_bills_with_purchase` | Vendor Bills with Purchase | Refactor | `od19_purchase_wizards` (create VB from PO) | ✅ |
| 48 | `dtr_customer_invoices_with_sales` | Customer Invoices with Sales | Refactor | `od19_sale_wizards` | ✅ |
| 49 | `dtr_document_sequence_group_accounting` | Document Sequence Accounting | Replace | `od19_accounting_document_sequence` | ✅ |
| 50 | `dtr_erp_package_accounting` | ERP Package Accounting | Retire | Odoo 19 resolve dependency เอง | ✅ |
| 51 | `dtr_erp_package_accounting_enterprise` | ERP Package Accounting (EE) | Retire | Odoo 19 resolve dependency เอง | ✅ |
| 52 | `dtr_access_right_accounting` | Access Right Accounting | Replace | `od19_security_roles` | ✅ |
| 53 | `dtr_bank_statement_import_base` | Bank Statement Import Base | Replace | core `account` + OCA `account_statement_import` — ✅ มีใน OCA v19 แต่ **ยังไม่ติดตั้งใน DB** (ดู R09) | 🟡 |
| 54 | `dtr_coa_alternative` | Chart of Accounts Alternative | Replace | Odoo `l10n_th` (ชุดมาตรฐานเดียว) | ✅ |
| 55 | `accounting_pdf_reports` | Odoo 15 Accounting PDF Reports | Replace | `od19_accounting_reporting` (QWeb) + `od19_reporting_jasper` | ✅ |

---

## 3. Sales (`odoo15_mods_sales`)

| # | โมดูล OD15 | ชื่อ | การตัดสินใจ | โมดูล OD19 / แทนที่ | สถานะ |
|---|-----------|------|-----------|---------------------|-------|
| 1 | `dtr_sales` | Sales | Refactor | Odoo `sale` + `od19_sales_contract_core` | 🟡 |
| 2 | `dtr_sales_form` | Sales Form Documents | Replace | `od19_sales_billing_evidence` | ✅ |
| 3 | `dtr_sales_report` | Sales Report | Replace | `od19_sales_reporting` | ✅ |
| 4 | `dtr_sales_filter` | Quotation/SO Filters | Retire | รวมเข้า Odoo standard (หลักการ 2) | ✅ |
| 5 | `dtr_sales_revision` | Sales Revision | Replace | OCA `sale_order_revision` + `od19_quotation_document_sequence` (**installed**) — ตรวจ source แล้วมีฝั่ง Sale ครบ | ✅ |
| 6 | `dtr_sales_discount` | Sales Discount | Refactor | OCA `sale_order_general_discount` / `od19_sale_terms` | 🟡 |
| 7 | `dtr_sales_warranty` | Sales Warranty Card | Replace | `od19_service_warranty` | ✅ |
| 8 | `dtr_pricelists` | Pricelists | Refactor | Odoo standard product pricelist | 🟡 |
| 9 | `dtr_project_analysis` | Sales Project Analysis | Replace | `od19_project_analytic` | ✅ |
| 10 | `dtr_project_analysis_tier_validation` | Tier Validation | Retire | OCA `base_tier_validation` | ✅ |
| 11 | `dtr_product_premium` | Product Premium | ยังไม่มีปลายทาง | ตรวจ source แล้ว: `od19_sale_terms` ไม่มีฟิลด์/ตรรกะ premium — ยังไม่มีเทียบเท่า | ❌ |
| 12 | `dtr_crm_filter` | CRM Pipeline Filters | Retire | รวมเข้า Odoo standard (หลักการ 2) | ✅ |
| 13 | `dtr_sale_tier_validation` | Sale Tier Validation | Retire | OCA `sale_tier_validation` | ✅ |
| 14 | `dtr_sales_department` | Sales Department | Refactor | `od19_sales_project_context` | ✅ |
| 15 | `dtr_sales_exchange_rate` | Multi Currencies for Sales | Refactor | `od19_sales_currency_amount` | ✅ |
| 16 | `dtr_sales_exchange_rate_specific` | Multi Currencies Specific | Refactor | `od19_sales_currency_amount` | ✅ |
| 17 | `dtr_delivery_status` | Delivery Status | Replace | OCA `sale_stock_delivery_state` / `od19_delivery_label` | 🟡 |
| 18 | `dtr_document_sequence_group_sales` | Document Sequence Sales | Replace | `od19_quotation_document_sequence` | ✅ |
| 19 | `dtr_access_right_sales` | Access Right Sales | Replace | `od19_security_roles` | ✅ |
| 20 | `dtr_erp_package_sales` | ERP Package Sales | Retire | Odoo 19 resolve dependency เอง | ✅ |

---

## 4. Purchase (`odoo15_mods_purchase`)

| # | โมดูล OD15 | ชื่อ | การตัดสินใจ | โมดูล OD19 / แทนที่ | สถานะ |
|---|-----------|------|-----------|---------------------|-------|
| 1 | `dtr_purchase` | Purchase | Refactor | Odoo `purchase` + `od19_purchase_procurement_core` | 🟡 |
| 2 | `dtr_purchase_form` | Purchase Form Documents | Replace | `od19_purchase_terms` | ✅ |
| 3 | `dtr_purchase_report` | Purchase Report | Replace | `od19_purchase_terms` (QWeb print block) | 🟡 |
| 4 | `dtr_purchase_filter` | Purchase Filters | Retire | รวมเข้า Odoo standard (หลักการ 2) | ✅ |
| 5 | `dtr_purchase_discount` | Purchase Discount | Refactor | OCA `purchase_triple_discount` | 🟡 |
| 6 | `dtr_purchase_department` | Purchase Department | Refactor | `od19_purchase_procurement_core` | ✅ |
| 7 | `dtr_purchase_project` | Purchase Project | Refactor | `od19_project_analytic` | ✅ |
| 8 | `dtr_purchase_multi_company` | Purchase Multi Company | Retire | Odoo standard multi-company | ✅ |
| 9 | `dtr_purchase_exchange_rate` | Multi Currencies for Purchase | Refactor | Odoo standard currency | 🟡 |
| 10 | `dtr_purchase_exchange_rate_specific` | Multi Currencies Specific | Refactor | Odoo standard currency | 🟡 |
| 11 | `dtr_purchase_tier_validation` | Purchase Tier Validation | Retire | OCA `purchase_tier_validation` | ✅ |
| 12 | `dtr_document_sequence_group_purchase` | Document Sequence Purchase | Replace | `od19_purchase_document_sequence` | ✅ |
| 13 | `dtr_access_right_purchase` | Access Right Purchase | Replace | `od19_security_roles` | ✅ |
| 14 | `dtr_erp_package_purchase` | ERP Package Purchase | Retire | Odoo 19 resolve dependency เอง | ✅ |

---

## 5. Sales Services (`odoo15_mods_sales_services`)

| # | โมดูล OD15 | ชื่อ | การตัดสินใจ | โมดูล OD19 / แทนที่ | สถานะ |
|---|-----------|------|-----------|---------------------|-------|
| 1 | `dtr_sales_services` | Sales Services | Replace | `od19_helpdesk_extension` + `od19_service_card` | ✅ |
| 2 | `dtr_sales_services_form` | Sales Services Form Documents | Replace | `od19_helpdesk_extension` | 🟡 |
| 3 | `dtr_sales_services_project` | Sales Services Project | Refactor | `od19_sales_project_context` | ✅ |
| 4 | `dtr_sales_services_report` | Sales Services Report | Replace | `od19_after_sales_reporting` | ✅ |
| 5 | `dtr_sales_services_setting` | Sales Services Setting | Refactor | `od19_helpdesk_extension` | 🟡 |
| 6 | `dtr_sales_services_tier_validation` | Tier Validation | Retire | OCA `base_tier_validation` | ✅ |
| 7 | `dtr_access_right_sales_services` | Access Right Sales Services | Replace | `od19_security_roles` | ✅ |
| 8 | `dtr_erp_package_sales_services` | ERP Package Sales Services | Retire | Odoo 19 resolve dependency เอง | ✅ |
| 9 | `dtr_logistics` | Logistics | Replace | `od19_transportation` | 🟡 |
| 10 | `dtr_logistics_project` | Logistics Project | Refactor | `od19_transportation` | 🟡 |
| 11 | `dtr_logistics_tier_validation` | Logistics Tier Validation | Retire | OCA `base_tier_validation` | ✅ |

---

## 6. Manufacturing (`odoo15_mods_manufacturing`)

> ✅ **ปิดขอบเขตแล้ว (2026-10-31):** ทะเบียนจริง DB `AUTOERP-PRD` ยืนยันว่า **โมดูลตระกูล MRP ทั้งหมด `uninstalled` ที่ต้นทาง**
> (`dtr_mrp`, `dtr_mrp_project`, `dtr_mrp_report`, `dtr_mrp_setting`, `dtr_mrp_tier_validation`, `dtr_mrp_warranty_card`, `dtr_access_right_mrp`, `dtr_stock_fifo_mrp`, `dtr_product_part_history_with_mrp`, `dtr_erp_package_manufacturing`)
> ⇒ **ไม่มีข้อมูลให้ย้าย — ตัดสินใจ Retire ทั้งกลุ่ม** และระบบ Odoo 19 ยังคง **ไม่ต้องมีโมดูล `od19_mrp_*`** (สอดคล้อง roadmap Wave 0–5)
> ⚠️ ข้อยกเว้นเดียว: `dtr_mrp_warranty_card` มี use case ประกันที่ยังได้ผลจาก `od19_service_warranty` — แต่ตาราง `dtr_warranty_card` อยู่ในโมดูล `dtr_warranty` (installed) ไม่ใช่ MRP

| # | โมดูล OD15 | ชื่อ | การตัดสินใจ | โมดูล OD19 / แทนที่ | สถานะ |
|---|-----------|------|-----------|---------------------|-------|
| 1 | `dtr_mrp` | MRP | Retire | ต้นทาง uninstalled (2026-10-31) — ไม่มีข้อมูลย้าย | ✅ |
| 2 | `dtr_mrp_setting` | MRP Setting | Retire | ต้นทาง uninstalled (2026-10-31) | ✅ |
| 3 | `dtr_mrp_report` | MRP Report | Retire | ต้นทาง uninstalled (2026-10-31) | ✅ |
| 4 | `dtr_mrp_project` | MRP Project | Retire | ต้นทาง uninstalled (2026-10-31) | ✅ |
| 5 | `dtr_mrp_warranty_card` | MRP Warranty Card | Retire | ต้นทาง uninstalled; use case ประกันใช้ `od19_service_warranty` | ✅ |
| 6 | `dtr_product_part_history_with_mrp` | Part History + MRP | Retire | ต้นทาง uninstalled (2026-10-31) | ✅ |
| 7 | `dtr_stock_fifo_mrp` | Stock FIFO MRP | Retire | ต้นทาง uninstalled (2026-10-31); FIFO หลักใช้ `od19_stock_fifo` | ✅ |
| 8 | `dtr_mrp_tier_validation` | MRP Tier Validation | Retire | ต้นทาง uninstalled (2026-10-31) | ✅ |
| 9 | `dtr_access_right_mrp` | Access Right MRP | Retire | ต้นทาง uninstalled (2026-10-31) | ✅ |
| 10 | `dtr_erp_package_manufacturing` | ERP Package Manufacturing | Retire | ต้นทาง uninstalled (2026-10-31) | ✅ |

---

## 7. รูปแบบการตัดสินใจที่ใช้ซ้ำ (Cross-Cutting Patterns)

ตารางด้านบนใช้รูปแบบเดียวกันหลายครั้ง สรุปเพื่อให้ตรวจสอบง่าย:

| รูปแบบ OD15 | การตัดสินใจ | ปลายทาง OD19 |
|--------------|-----------|---------------|
| `*_filter` (payment/account/inventory/sales/purchase/crm) | Retire | รวมเข้า Odoo 19 standard search (หลักการ 2) |
| `*_tier_validation` (10+ โมดูล) | Retire | OCA `base_tier_validation` + configure rule (หลักการ 6) |
| `*_erp_package_*` (ทุกตัว) | Retire | Odoo 19 resolve dependency chain อัตโนมัติ |
| `*_form` (documents print) | Replace | QWeb report ในโมดูลโดเมน (หลักการ 3) |
| `*_report` | Replace | รวมเข้า `od19_accounting_reporting` / `od19_*_reporting` (หลักการ 7) |
| `*_document_sequence_group*` | Replace | `od19_document_sequence` + `od19_*_document_sequence` |
| `*_exchange_rate*` | Refactor | Odoo standard currency + `od19_currency_rate_bot` |
| `*_access_right_*` | Replace | `od19_security_roles` (RBAC ศูนย์กลาง) |
| `*_project` (ผูก Project) | Refactor | `od19_project_analytic` (analytic account) |
| `taxation*` / `taxes*` / `tax_*` | Replace | OCA `l10n_th_account_tax` + `od19_thai_tax_reports` |

---

## 8. OCA Modules ที่ใช้เป็นฐาน (มีบนดิสก์ `third_party/oca`)

| OCA Module | Repo | แทน OD15 |
|-----------|------|----------|
| `l10n_th_account_tax` | l10n-thailand | `dtr_taxation`, `dtr_taxes`, `dtr_taxes_with_coa`, `dtr_taxation_with_coa` |
| `base_tier_validation` | tier-validation | โมดูล `*_tier_validation` ทั้งหมด |
| `account_asset_management` | account-financial-tools | `dtr_fixed_assets`, `dtr_fixed_assets_report` |
| `auditlog` | server-tools | (เดิม `deleted_records_info` ใน autoinfo) |
| `report_xlsx` | reporting-engine | รายงาน Excel (ภ.พ.30, ภ.ง.ด., ทะเบียนภาษี) |
| `database_cleanup` | server-tools | `dtr_database_cleanup` |
| `base_user_role` | server-backend | `dtr_access_right_*` (RBAC) |
| `base_global_discount` | server-backend | `dtr_invoicing_discount`, `dtr_sales_discount` |
| `purchase_triple_discount` | purchase-workflow | `dtr_purchase_discount` |
| `sale_order_general_discount` | sale-workflow | `dtr_sales_discount` |
| `stock_request` + `stock_request_purchase` | stock-logistics-request | `dtr_goods_issue` |
| `purchase_request` + `purchase_request_*` | purchase-workflow | `dtr_purchase` (requisition) |
| `account_move_tier_validation` | tier-validation | `dtr_account_tier_validation` |
| `sale_tier_validation` | tier-validation | `dtr_sale_tier_validation` |
| `purchase_tier_validation` | tier-validation | `dtr_purchase_tier_validation` |
| `stock_picking_tier_validation` | tier-validation | `dtr_stock_tier_validation` |
| `hr_expense_tier_validation` | tier-validation | `dtr_expense_tier_validation` |

---

## 9. ประเด็นที่ต้องตัดสินใจ / ยืนยัน (Open Items) — ตรวจ source ระดับ model แล้ว 2026-10-31

| # | ประเด็น | โมดูล OD15 ที่เกี่ยว | ผลตรวจระดับ source (2026-10-31) | สถานะ |
|---|---------|----------------------|--------------------------------|-------|
| 1 | ขอบเขต Manufacturing (MRP) | `dtr_mrp`, `dtr_mrp_report` | **ปิดแล้ว (2026-10-31):** ทะเบียนจริง `AUTOERP-PRD` ยืนยัน MRP ทั้งตระกูล **uninstalled** → **Retire ทั้งกลุ่ม** ไม่มีข้อมูลย้าย | ✅ |
| 2 | Product Part History | `dtr_product_part_history`, `dtr_product_part_history_with_mrp` | `dtr_product_part_history` **installed** ที่ต้นทาง (15.0.1.0) และมีตาราง `dtr_parts_history` + `_line` → **ต้องมีปลายทาง**; ส่วน `_with_mrp` uninstalled → Retire | ❌ |
| 3 | Stock Backdating | `dtr_stock_backdating` | **ปิดได้ (2026-10-31):** ต้นทาง **installed 15.0.1.0**; `od19_inventory_execution_control` (**installed**) ครอบ use case | ✅ |
| 4 | Account Cash family | `dtr_account_cash`, `dtr_account_cash_with_*` | **ปรับข้อสรุป (2026-10-31):** ติดตั้งจริงที่ต้นทาง **ทั้ง 3 โมดูล** (มีตาราง `dtr_account_cash`, `_line`, `_transfer_line`, `_po_wizard`, `_so_wizard`, `_mr_wizard`) — เดิมระบุ `_with_*` = Retire **ไม่ถูกต้อง** ⇒ ต้อง develop/รวมเข้า cash core ให้ครบ | ❌ |
| 5 | Account Control Level | `dtr_account_control_level` | ไม่มี `account.control.level` ใน core/OCA — develop ใหม่ หรือใช้ account group/hierarchy มาตรฐานแทน | ❌ |
| 6 | Bring Forward | `dtr_bring_forward` | `od19_accounting_operational_closure` ไม่มีตรรกะ bring-forward — ยังไม่มีเทียบเท่า | ❌ |
| 7 | Bank Statement Import | `dtr_bank_statement_import_base` | core `account` + OCA `account_statement_import` มี v19 แต่ **ยังไม่ติดตั้งใน DB** | 🟡 |
| 8 | Sales Revision | `dtr_sales_revision` | ปิดได้: OCA `sale_order_revision` + `od19_quotation_document_sequence` (**installed**) ครบฝั่ง Sale | ✅ |
| 9 | Product Premium | `dtr_product_premium` | `od19_sale_terms` ไม่มีฟิลด์/ตรรกะ premium — ยังไม่มีเทียบเท่า | ❌ |
| 10 | Stock No Negative | `stock_no_negative` | OCA `stock_no_negative` v19 พร้อมใช้ แต่ **ยังไม่ติดตั้งใน DB** | ✅ (รอติดตั้ง) |
| 11 | `dtr_account_cash` | ดูข้อ 4 | รวมกับข้อ 4 แล้ว | — |

**สรุปผลตรวจ (ปรับ 2026-10-31 ตามทะเบียนจริง `AUTOERP-PRD`):** ✅ ปิดได้ 4 รายการ (ข้อ 1, 3, 8, 10) · 🟡 รอติดตั้ง OCA 1 รายการ (ข้อ 7) · ❌ ยังไม่มีเทียบเท่าต้อง develop ใหม่ 5 รายการ (ข้อ 2, 4, 5, 6, 9)

---

## 10. โมดูล OD19 ที่ไม่มีคู่ใน DTR (สร้างใหม่ / มาจาก autoinfo หรือ compliance)

โมดูล `od19_*` จำนวนมากไม่มีต้นทางในตระกูล DTR โดยตรง แต่รองรับข้อกำหนดใหม่ (ISO, Thai compliance, dashboard):

`od19_iso_*` (8), `od19_etax_invoice`, `od19_dashboard`, `od19_user_guide_tours`, `od19_meeting_room_booking`, `od19_announcement`, `od19_knowledge_enhanced`, `od19_website`, `od19_fleet_accounting`, `od19_hr_expense_thai`, `od19_notification_multi_channel`, `od19_apps_filter`, `od19_dev_field_marker`, `od19_internal_issue`, `od19_quality_control`, `od19_after_sales_reporting`, ฯลฯ

> รายการเต็มของ 88 โมดูล `od19_*` ดูได้จาก `custom_addons/*/__manifest__.py`

---

## 11. สรุปเชิงปฏิบัติ

**ครอบคลุมแล้ว / แทนได้ (Replace + Keep):** ส่วนใหญ่ของ Accounting, Cheque, Advance, Petty Cash, Payment Fee, Goods Issue, Warranty, Stock FIFO, Fixed Assets, Sequences, Access Rights

**ต้อง Refactor (ยกตรรกะมาเขียนใหม่):** โมดูลปรับแต่งมาตรฐาน (sales/purchase/stock/inventory/project/currency) — ประมาณ 46 โมดูล

**ควร Retire (51 โมดูล):** กลุ่ม `*_filter`, `*_tier_validation`, `*_erp_package_*`, เมนูย้าย (general_journal_enterprise, taxation_enterprise), SQL command
> **บวกด้วย (2026-10-31):** โมดูลที่ต้นทาง `uninstalled` ทั้ง 46 ตัว → ไม่มีข้อมูลย้าย เก็บเป็น Retire/Defer ได้ทันที (ดูทะเบียนจริงในหมายเหตุหัวเอกสาร)

**ค้างตัดสินใจ (ปรับ 2026-10-31 ตามทะเบียนจริง `AUTOERP-PRD`):** ✅ ปิดได้ 4 รายการ (MRP scope→Retire, Stock Backdating, Sales Revision, Stock No Negative) · 🟡 รอติดตั้ง OCA 1 รายการ (Bank Statement Import) · ❌ ต้อง develop ใหม่ 5 รายการ (Product Part History, Account Cash family, Account Control Level, Bring Forward, Product Premium) — รายละเอียดในหัวข้อ 9

**⚠️ สิ่งที่ต้องแก้จากข้อเท็จจริงต้นทาง:** ตาราง §2 ข้อ 15/16 เดิมระบุ `dtr_account_cash_with_purchase`/`_with_sales` = Retire — **ไม่ถูกต้อง** เพราะติดตั้งจริงทั้ง 3 โมดูล จึงต้องมีปลายทาง (ดูหัวข้อ 9 ข้อ 4)

---

## 12. โมดูลจริงใน `AUTOERP-PRD` ที่ยังไม่มีในเอกสาร (พบ 2026-10-31)

ตรวจจาก `migration/od15_export/modules.txt` แล้วพบโมดูลที่เอกสารนี้ยังไม่ครอบคลุม:

| # | โมดูล OD15 | สถานะต้นทาง | หน้าที่ (จากชื่อ/ตาราง) | ข้อเสนอ |
|---|-----------|-------------|------------------------|---------|
| 1 | `dtr_approval_levels_base` | **installed** 15.0.1.8 | ชั้นอนุมัติหลายระดับ (approval levels) | Refactor → OCA `base_tier_validation` หรือ `od19_security_roles` |
| 2 | `dtr_qc` | **installed** 15.0.1.2 | Quality Control (`dtr_quality_controls`, `_list`) | Replace → `od19_quality_control` |
| 3 | `dtr_requests` | **installed** 15.0.1.0 | ใบขออนุมัติ/คำขอภายใน | Refactor → `od19_purchase_request_extend` / `od19_internal_issue` |
| 4 | `dtr_sales_services_qc` | uninstallable | QC สำหรับงานบริการ | Retire (ไม่มีข้อมูล) |
| 5 | `dtr_approval_levels_project` | uninstalled | approval levels ผูก Project | Retire |
| 6 | `dtr_approval_levels_reject_comment` | uninstalled | เหตุผลตีกลับใน approval | Retire |
| 7 | `dtr_approval_levels_step` | uninstalled | ขั้นตอน approval | Retire |
| 8 | `dtr_project_analysis_approval` | uninstalled | อนุมัติ Project Analysis | Retire |
| 9 | `dtr_qc_approval` | uninstalled | อนุมัติ QC | Retire |
| 10 | `dtr_stock_approval` | uninstalled | อนุมัติ Stock | Retire |
| 11 | `dtr_stock_valuation_adjustment_approval` | uninstalled | อนุมัติ Valuation Adj. | Retire |
| 12 | `dtr_goods_issue_approval` | uninstalled | อนุมัติใบเบิก | Retire |

> 📌 **หมายเหตุตาราง (จาก `dtr_columns.txt` — 192 ตาราง `dtr_*`):** ตาราง master data จำนวนมาก **ไม่ใช่โมดูล** แต่เป็น extension ของโมดูลที่ติดตั้งแล้ว เช่น
> Partner (`dtr_customer_grade`, `dtr_customer_type`, `dtr_customer_master_group`, `dtr_customer_company_group`, `dtr_customer_selling_area`, `dtr_customer_selling_type`, `dtr_prefix_partner`, `dtr_partner_branch`, `dtr_partner_fee`, `dtr_credit_limit`),
> Product (`dtr_product_brand`, `dtr_product_brand_model`, `dtr_product_tag`, `dtr_parts_history`, `dtr_parts_history_line`),
> Accounting (`dtr_general_template`, `dtr_general_template_line`, `dtr_wht`, `dtr_vat`, `dtr_cheque_book`, `dtr_cheque_leaf`, `dtr_account_prepayment`, `dtr_bring_forward`, `dtr_bring_forward_line`),
> Asset (`dtr_asset_class`, `dtr_asset_brand`, `dtr_asset_keeper`, `dtr_asset_insurance`, `dtr_asset_repair`, `dtr_asset_transfer`),
> Service (`dtr_service_card*`, `dtr_warranty_card`, `dtr_guarantee`, `dtr_claim*`, `dtr_service_level_agreement_*`),
> Transport (`dtr_transportation_request*`, `dtr_transportation_method`, `dtr_vehicle_type`, `dtr_truck_size`),
> Jasper (`dtr_jasper`, `dtr_jasper_report`)
> ⇒ คอลัมน์ทั้งหมด (2,390 แถว) ใช้ทำ field-level mapping ได้แล้ว — ดู `migration/od15_export/dtr_columns.txt`

---

## เอกสารอ้างอิง

- `GAP_ANALYSIS_OD15_to_OD19.md` — gap analysis ตระกูล `custom15_autoinfo` (ฉบับคู่กัน)
- `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md` — นโยบาย Keep/Replace/Retire + Thailand Localization Strategy 9 หลักการ
- `docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md` — Wave 0–5 child specs
- `docs/superpowers/programs/odoo19-enterprise/discovery/current-state-inventory.md` — legacy namespaces (AUTO-INFO, DTR)
- `migration/od15_export/modules.txt` — ทะเบียนโมดูลจริง 170 รายการจาก `AUTOERP-PRD` (installed=123 / uninstalled=46 / uninstallable=1)
- `migration/od15_export/dtr_columns.txt` — โครงสร้างคอลัมน์ตาราง `dtr_*` 192 ตาราง (2,390 คอลัมน์) สำหรับ field-level mapping
- `migration/od15_export/versions.txt` — เวอร์ชันโมดูลหลัก Odoo 15 (`base|15.0.1.3` ฯลฯ)
