# Legacy Odoo 15 → Odoo 19 Data Profiling Checklist

## Document Metadata

| Field | Value |
| --- | --- |
| Program | Odoo 19 Enterprise (Greenfield + ETL) |
| Artifact path | `docs/superpowers/programs/odoo19-enterprise/discovery/legacy-od15-data-profiling-checklist.md` |
| Artifact owner | Migration / Data engineering lead |
| Artifact status | **Profiled (กรอกผลแล้ว 2026-11-02)** — รันบน `od15_stage` แบบ read-only |
| Source system | Odoo 15 CE (legacy) |
| Target system | Odoo 19 (fresh database) |
| SQL ที่ใช้คู่กัน | `migration/extract/01_profiling_queries.sql` |
| ไฟล์หลักฐาน | `migration/od15_export/profiling_result.txt` (รันด้วย `psql -e`, 4.1 MB) |
| Cut-off date ที่ใช้ | `2025-12-31` (ค่าตัวอย่างใน SQL — ยังต้องยืนยันวันตัดยอดจริงกับฝ่ายบัญชี) |
| Last updated | 2026-11-02 |

## บริบทและขอบเขต (Context)

กลยุทธ์การย้ายข้อมูลคือ **Greenfield + ETL**: ฐานข้อมูล Odoo 19 ใหม่จะรับเฉพาะ
**ข้อมูลหลัก (master data)** และ **ยอดยกมา (opening balances)** เท่านั้น
ไม่ยกประวัติธุรกรรมทั้งก้อน ดังนั้นการ Profiling จึงโฟกัส 3 เรื่อง:

1. **ปริมาณข้อมูล (data volume)** — เพื่อประเมินเวลาและขอบเขตของ ETL
2. **ช่องว่างคุณภาพข้อมูล (data quality gaps)** — สิ่งที่จะทำให้การ import ล้มเหลว
3. **ตัวเลข opening balance ที่ต้อง tie หลัง import (reconciliation baseline)**

> **ข้อบังคับสำคัญ:** การ Profiling ต้องรันบน **สำเนาที่ restore แล้ว** (ชื่อฐานข้อมูล `od15_stage`)
> **ห้ามรันบนฐานข้อมูล production ของระบบเดิมเด็ดขาด** และต้องตั้งการเชื่อมต่อเป็น **read-only**

ไฟล์ SQL ที่ใช้คู่กับเอกสารนี้: `c:\odoo-dev\odoo19\migration\extract\01_profiling_queries.sql`
วิธีรัน:
```
psql -h <host> -U <user> -d od15_stage -f 01_profiling_queries.sql > profiling_result.txt
```

---

## Section 0 : ขั้นตอนเตรียมการ

| # | ขั้นตอน | รายละเอียด | Query | ผลลัพธ์ที่คาดหวัง | สถานะ |
| --- | --- | --- | --- | --- | --- |
| 0.1 | Restore dump เป็นสำเนา | Restore backup ของ Odoo 15 เป็นฐานข้อมูลใหม่ชื่อ `od15_stage` (ห้ามใช้ DB production) | — | ได้ DB `od15_stage` ที่เปิดใช้งานได้ | ☑ |
| 0.2 | ตั้ง read-only | ใช้ role ที่มีสิทธิ์อ่านเท่านั้น หรือรันใน transaction เดียวแล้ว ROLLBACK; ตรวจด้วย query ยืนยัน | `[0.3]` | `transaction_read_only = on` | ☑ |
| 0.3 | ตรวจเวอร์ชัน Odoo 15 | อ่านค่า `base_version` จาก `ir_config_parameter` | `[0.1]` | ค่าขึ้นต้นด้วย `15.` | ☑ (ดูหมายเหตุ) |
| 0.4 | ตรวจเวอร์ชันโมดูลหลัก | อ่าน `latest_version` ของ `base`, `account`, `stock`, `sale`, `purchase`, `hr`, `project` จาก `ir_module_module` | `[0.2]` | `base` = `15.0.x.x.x` | ☑ |
| 0.5 | ยืนยันชื่อฐานข้อมูล | ยืนยันว่ากำลังต่อกับ `od15_stage` | `[0.3]` | `database_name = od15_stage` | ☑ |
| 0.6 | เตรียมที่เก็บหลักฐาน | redirect ผลลัพธ์ทุก query เป็นไฟล์ `profiling_result.txt` และแนบเก็บ | — | มีไฟล์หลักฐานครบ | ☑ |

ผลการตรวจเวอร์ชัน (บันทึก):

| รายการ | ค่าที่อ่านได้ |
| --- | --- |
| `base_version` | **ไม่พบแถว** (query `[0.1]` คืน 0 rows) — ฐานข้อมูลนี้ไม่มี parameter `base_version` ใน `ir_config_parameter` |
| `ir.module.module` base `latest_version` | `15.0.1.3` (ยืนยันว่าเป็น Odoo 15) |
| database name ที่เชื่อมต่อ | `od15_stage` |
| connected role | `odoo` |
| transaction_read_only | `on` |

> **หมายเหตุ [0.1]:** Odoo 15 ไม่ได้เก็บ `base_version` เป็น `ir_config_parameter` เสมอไป
> (พบ 0 rows ในสำเนานี้) จึงใช้ `ir_module_module.latest_version` ของ `base` = `15.0.1.3`
> เป็นหลักฐานยืนยันเวอร์ชันแทน และผ่านเกณฑ์ G2 ได้
>
> **หมายเหตุ [0.2]:** ตั้ง read-only ด้วย `PGOPTIONS='-c default_transaction_read_only=on'`
> ตอนรัน psql เพื่อบังคับทั้ง session (ยืนยันจาก `[0.3]` = `on`)

---

## Section 1 : ทะเบียนโมดูลที่ติดตั้งจริง (Installed Module Inventory)

แหล่งข้อมูล: `ir_module_module` ที่ `state = 'installed'` (query `[1.2]`, `[1.3]`, `[1.5]`)

### 1.1 สรุปจำนวนโมดูล

| หมวด | จำนวน (จาก query `[1.4]`) | หมายเหตุ |
| --- | --- | --- |
| core/other | 206 | Odoo CE + โมดูลที่ `author`/`maintainer` ไม่ใช่ OCA |
| OCA | 59 | ตรวจจาก `author`/`maintainer` มีคำว่า OCA |
| custom (`autoinfo_*` / `dtr_*` / `account_invoice_get_sale`) | 167 | ดูรายละเอียดในหัวข้อ 1.2 |
| **รวมทั้งหมด (installed)** | **432** | เทียบกับ `[1.1]` = 432 ✅ ตรงกัน |

> **ผลยืนยัน:** `[1.4]` (206 + 59 + 167) = 432 = `[1.1]` ✅
> และ `[1.5]` (รายชื่อ custom ที่ติดตั้งจริง) = 167 rows ตรงกับหมวด custom ใน `[1.4]`

> หมายเหตุ: การแยก core / OCA / custom ใน SQL อ้างอิงจาก prefix ของชื่อโมดูลและคอลัมน์
> `author`/`maintainer` (ตรวจสอบกับ source Odoo 15 CE แล้วว่าคอลัมน์เหล่านี้มีจริงที่
> `odoo/addons/base/models/ir_module.py`) ให้ทบทวนผลลัพธ์จริงอีกรอบ

### 1.2 รายชื่อโมดูล custom ที่พบในระบบเดิม (จากโครงสร้างโฟลเดอร์จริง)

โฟลเดอร์ `c:\odoo-dev\Odoo15Backup\odoo\custom15_autoinfo` (prefix `autoinfo_*` และ 1 โมดูลชื่ออื่น):

| # | โมดูลเดิม (Odoo 15) | ติดตั้งจริง? (ยืนยันจาก `[1.5]`) | mapping ไปยังโมดูล od19_* ปลายทาง | สถานะ mapping |
| --- | --- | --- | --- | --- |
| 1 | `account_invoice_get_sale` | ✅ ติดตั้ง | — (ยังไม่มี mapping ระบุ) | ⚠ ต้องกำหนด |
| 2 | `autoinfo_account` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 3 | `autoinfo_account_move_link_payment_number` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 4 | `autoinfo_accounting_form` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 5 | `autoinfo_accounting_form_wht_fix` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 6 | `autoinfo_asset_sale_fix` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 7 | `autoinfo_currency_rate_bot` | ✅ ติดตั้ง | `od19_currency_rate_bot` | ☑ |
| 8 | `autoinfo_data_link_base` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 9 | `autoinfo_data_link_project` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 10 | `autoinfo_employees` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 11 | `autoinfo_fixes_accounting_runtime_guard` | ❌ ไม่ติดตั้ง | — | — |
| 12 | `autoinfo_fleet` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 13 | `autoinfo_hr_expense` | ✅ ติดตั้ง | `od19_hr_expense_enhanced` / `od19_hr_expense_thai` | ☑ |
| 14 | `autoinfo_hr_expense_cash_tracking` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 15 | `autoinfo_logo` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 16 | `autoinfo_money_in_report` | ✅ ติดตั้ง | `od19_accounting_money_in_report` | ☑ |
| 17 | `autoinfo_payment_wht` | ✅ ติดตั้ง | `od19_thai_tax_reports` | ☑ |
| 18 | `autoinfo_project` | ✅ ติดตั้ง | `od19_project_enhanced` | ☑ |
| 19 | `autoinfo_project_form` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 20 | `autoinfo_project_risk_report` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 21 | `autoinfo_purchase` | ✅ ติดตั้ง | `od19_purchase_procurement_core` | ☑ |
| 22 | `autoinfo_purchase_form` | ✅ ติดตั้ง | `od19_purchase_terms` | ☑ |
| 23 | `autoinfo_repeat_customer_dashboard` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 24 | `autoinfo_sale` | ✅ ติดตั้ง | `od19_sale_terms` / `od19_sales_contract_core` | ☑ |
| 25 | `autoinfo_sale_form` | ✅ ติดตั้ง | `od19_sale_terms` | ☑ |
| 26 | `autoinfo_sale_order_invoice_amount` | ✅ ติดตั้ง | `od19_sales_currency_amount` | ☑ |
| 27 | `autoinfo_sign_oca` | ✅ ติดตั้ง | `od19_document_sign` | ☑ |
| 28 | `autoinfo_skip_check_sequence` | ❌ ไม่ติดตั้ง | `od19_document_sequence` | — |
| 29 | `autoinfo_stock_monthly_report` | ✅ ติดตั้ง | `od19_stock_fifo` / `od19_inventory_reporting` | ☑ |

โฟลเดอร์ `c:\odoo-dev\Odoo15Backup\odoo\odoo15_mods` (prefix `dtr_*`):

| # | โมดูลเดิม (Odoo 15) | ติดตั้งจริง? | mapping ไปยังโมดูล od19_* ปลายทาง | สถานะ mapping |
| --- | --- | --- | --- | --- |
| 1 | `dtr_access_right_base` | ✅ ติดตั้ง | — (ยังไม่มี mapping) | ⚠ ต้องกำหนด |
| 2 | `dtr_access_right_base_partner_rules` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 3 | `dtr_account_control_level` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 4 | `dtr_coa` | ✅ ติดตั้ง | `od19_thai_localization_base` | ☑ |
| 5 | `dtr_common` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 6 | `dtr_company` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 7 | `dtr_customer_invoices` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 8 | `dtr_database_cleanup` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 9 | `dtr_document_sequence_group` | ✅ ติดตั้ง | `od19_document_sequence` | ☑ |
| 10 | `dtr_employee_master` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 11 | `dtr_erp_package_core` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 12 | `dtr_exchange_rate` | ✅ ติดตั้ง | `od19_currency_rate_bot` | ☑ |
| 13 | `dtr_goods_issue` | ✅ ติดตั้ง | `od19_goods_issue` | ☑ |
| 14 | `dtr_goods_issue_project` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 15 | `dtr_goods_issue_tier_validation` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 16 | `dtr_inventory_department` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 17 | `dtr_inventory_filter` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 18 | `dtr_inventory_overview` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 19 | `dtr_inventory_project` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 20 | `dtr_invoicing_discount` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 21 | `dtr_invoicing_report` | ✅ ติดตั้ง | `od19_sales_reporting` | ☑ |
| 22 | `dtr_jasper` | ✅ ติดตั้ง | `od19_reporting_jasper` | ☑ |
| 23 | `dtr_jasper_auto_active` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 24 | `dtr_landed_cost` | ✅ ติดตั้ง | `od19_stock_valuation_adjustment` | ☑ |
| 25 | `dtr_m2o_no_create` | ❌ ไม่ติดตั้ง | — | — |
| 26 | `dtr_partner_master` | ✅ ติดตั้ง | `od19_partner_thai_fields` | ☑ |
| 27 | `dtr_product_access_rules` | ❌ ไม่ติดตั้ง | — | — |
| 28 | `dtr_product_category` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 29 | `dtr_product_master` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 30 | `dtr_product_part_history` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 31 | `dtr_project` | ✅ ติดตั้ง | `od19_project_enhanced` | ☑ |
| 32 | `dtr_report_base` | ✅ ติดตั้ง | `od19_reporting_jasper` | ☑ |
| 33 | `dtr_settings` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 34 | `dtr_sql_command` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 35 | `dtr_stock` | ✅ ติดตั้ง | `od19_stock_picking_features` | ☑ |
| 36 | `dtr_stock_adjustment` | ✅ ติดตั้ง | `od19_stock_valuation_adjustment` | ☑ |
| 37 | `dtr_stock_backdating` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 38 | `dtr_stock_fifo` | ✅ ติดตั้ง | `od19_stock_fifo` | ☑ |
| 39 | `dtr_stock_form` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |

โฟลเดอร์ `c:\odoo-dev\Odoo15Backup\odoo\odoo15_mods_sales` (prefix `dtr_*`):

| # | โมดูลเดิม (Odoo 15) | ติดตั้งจริง? | mapping ไปยังโมดูล od19_* ปลายทาง | สถานะ mapping |
| --- | --- | --- | --- | --- |
| 1 | `dtr_access_right_sales` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 2 | `dtr_crm_filter` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 3 | `dtr_delivery_status` | ✅ ติดตั้ง | `od19_delivery_label` | ☑ |
| 4 | `dtr_document_sequence_group_sales` | ❌ ไม่ติดตั้ง | `od19_document_sequence` | — |
| 5 | `dtr_erp_package_sales` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 6 | `dtr_pricelists` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 7 | `dtr_product_premium` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 8 | `dtr_project_analysis` | ✅ ติดตั้ง | `od19_project_analytic` | ☑ |
| 9 | `dtr_project_analysis_tier_validation` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 10 | `dtr_sale_tier_validation` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 11 | `dtr_sales` | ✅ ติดตั้ง | `od19_sale_wizards` / `od19_sales_project_context` | ☑ |
| 12 | `dtr_sales_department` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 13 | `dtr_sales_discount` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 14 | `dtr_sales_exchange_rate` | ✅ ติดตั้ง | `od19_sales_currency_amount` | ☑ |
| 15 | `dtr_sales_exchange_rate_specific` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 16 | `dtr_sales_filter` | ✅ ติดตั้ง | — | ⚠ ต้องกำหนด |
| 17 | `dtr_sales_form` | ✅ ติดตั้ง | `od19_sale_terms` | ☑ |
| 18 | `dtr_sales_report` | ✅ ติดตั้ง | `od19_sales_reporting` | ☑ |
| 19 | `dtr_sales_revision` | ✅ ติดตั้ง | `od19_purchase_revision` (แนวทางเดียวกัน) | ☑ |
| 20 | `dtr_sales_warranty` | ✅ ติดตั้ง | `od19_service_warranty` | ☑ |

> **ข้อค้นพบสำคัญ (folder inventory ≠ ของที่ติดตั้งจริง):**
> ตาราง 3 ชุดข้างบนสร้างจากการ **สำรวจโฟลเดอร์ซอร์ส** (`custom15_autoinfo` 29,
> `odoo15_mods` 39, `odoo15_mods_sales` 20 = 88 รายการ) แล้วนำมาเทียบกับ
> รายชื่อที่ **ติดตั้งจริง** จาก query `[1.5]` (167 โมดูล) ผลคือโฟลเดอร์เหล่านี้
> เป็นเพียง **มุมมองบางส่วน** — ยังมีโมดูล custom ที่ติดตั้งจริงอีก **84 รายการ**
> ที่ไม่ปรากฏในโฟลเดอร์ที่สำรวจ (ดูหัวข้อ 1.2.4)
> เอกสารที่ถือเป็น **แหล่งอ้างอิงจริง (authoritative)** คือผลของ `[1.5]` ไม่ใช่ตารางโฟลเดอร์

### 1.2.4 โมดูล custom ที่ติดตั้งจริง แต่ไม่อยู่ในโฟลเดอร์ที่สำรวจ (gap 84 รายการ)

สรุปจาก `[1.5]` (167) ลบด้วย 83 รายการที่ปรากฏในโฟลเดอร์และติดตั้งจริง:

- **prefix `autoinfo_*` ที่โฟลเดอร์ไม่ได้เก็บ (3):**
  `autoinfo_stock_picking_additional_print_lines`, `autoinfo_stock_picking_sale_person_tier`,
  `autoinfo_stock_report`
- **prefix `od15_autoinfo_*` (2):**
  `od15_autoinfo_account_cash_with_purchase`, `od15_autoinfo_account_prepayment`
- **prefix `dtr_*` ที่โฟลเดอร์ไม่ได้เก็บ (79):**
  `dtr_access_right_accounting`, `dtr_access_right_purchase`, `dtr_access_right_sales_services`,
  `dtr_account_cash`, `dtr_account_cash_with_purchase`, `dtr_account_cash_with_sales`,
  `dtr_account_filter`, `dtr_account_invoice_report`, `dtr_account_tier_validation`,
  `dtr_accounting_form`, `dtr_accounting_report`, `dtr_advance`, `dtr_advance_project`,
  `dtr_advance_tier_validation`, `dtr_analytic_require`, `dtr_bank_statement_import_base`,
  `dtr_billing`, `dtr_bring_forward`, `dtr_cheque`, `dtr_coa_alternative`,
  `dtr_customer_invoices_with_sales`, `dtr_deposit_payment`, `dtr_dncn`,
  `dtr_document_sequence_group_accounting`, `dtr_document_sequence_group_purchase`,
  `dtr_down_payment`, `dtr_erp_package_accounting`, `dtr_erp_package_purchase`,
  `dtr_exchange_diff_partial`, `dtr_exchange_rate_specific`, `dtr_expense_project`,
  `dtr_expense_tier_validation`, `dtr_fixed_assets`, `dtr_fixed_assets_report`,
  `dtr_general_journal`, `dtr_invoice_project`, `dtr_invoice_unlock_six_month`,
  `dtr_journal_entry`, `dtr_journal_entry_set_voucher_running`, `dtr_logistics`,
  `dtr_logistics_project`, `dtr_logistics_tier_validation`, `dtr_payment_fee`,
  `dtr_payment_filter`, `dtr_payment_invoice`, `dtr_payment_method`, `dtr_petty_cash`,
  `dtr_petty_cash_project`, `dtr_petty_cash_tier_validation`, `dtr_purchase`,
  `dtr_purchase_department`, `dtr_purchase_discount`, `dtr_purchase_exchange_rate`,
  `dtr_purchase_exchange_rate_specific`, `dtr_purchase_filter`, `dtr_purchase_form`,
  `dtr_purchase_project`, `dtr_purchase_report`, `dtr_purchase_tier_validation`,
  `dtr_sales_services`, `dtr_sales_services_form`, `dtr_sales_services_project`,
  `dtr_sales_services_report`, `dtr_sales_services_setting`, `dtr_stock_report`,
  `dtr_stock_tier_validation`, `dtr_stock_valuation_adjustment`,
  `dtr_stock_valuation_adjustment_tier_validation`, `dtr_tax_adr`, `dtr_tax_txt`,
  `dtr_taxation`, `dtr_taxation_with_coa`, `dtr_taxes`, `dtr_taxes_with_coa`,
  `dtr_upload_product_picture`, `dtr_vendor_bills`, `dtr_vendor_bills_with_purchase`,
  `dtr_warranty`, `dtr_year_end`

> **ผลต่อเกณฑ์ G3:** เมื่อรวมทั้งหมดแล้ว โมดูล custom ที่ติดตั้งจริง = **167** รายการ
> ต้องมี mapping ไป `od19_*` หรือบันทึกเหตุผล "ไม่ยก" ให้ครบทุกตัว
> งาน mapping ฉบับเต็ม (workbook) อยู่ใน Task **D2** ของ
> `docs/superpowers/plans/2026-11-01-backlog-closure-plan.md`
>
> **หมายเหตุ prefix:** พบทั้ง `autoinfo_*` (โฟลเดอร์ `custom15_autoinfo`) และ
> `od15_autoinfo_*` (2 โมดูลที่ติดตั้งจริง) — SQL จึงเผื่อ pattern
> `autoinfo%` + `od15_autoinfo%` ไว้ทั้งคู่เพื่อความครบถ้วน

### 1.3 รายชื่อโมดูลปลายทาง Odoo 19 (อ้างอิงสำหรับ mapping)

โมดูลเป้าหมายภายใต้ `c:\odoo-dev\odoo19\custom_addons` (เรียงตามชื่อ):

`od19_accounting_advance`, `od19_accounting_analytic_require`, `od19_accounting_cheque`,
`od19_accounting_dncn`, `od19_accounting_document_sequence`, `od19_accounting_features`,
`od19_accounting_money_in_report`, `od19_accounting_operational_closure`,
`od19_accounting_payment_fee`, `od19_accounting_petty_cash`, `od19_accounting_reporting`,
`od19_after_sales_reporting`, `od19_announcement`, `od19_apps_filter`, `od19_asset_disposal`,
`od19_asset_loan`, `od19_contacts_partner_roles`, `od19_currency_rate_bot`, `od19_dashboard`,
`od19_delivery_label`, `od19_document_sequence`, `od19_document_sign`, `od19_fleet_accounting`,
`od19_fleet_notification`, `od19_goods_issue`, `od19_helpdesk_extension`,
`od19_hr_attendance_zkteco`, `od19_hr_expense_enhanced`, `od19_hr_expense_thai`,
`od19_internal_issue`, `od19_inventory_audit_count`, `od19_inventory_execution_control`,
`od19_inventory_reporting`, `od19_iso_calibration`, `od19_iso_customer_satisfaction`,
`od19_iso_document_control`, `od19_iso_internal_audit`, `od19_iso_management_review`,
`od19_iso_nonconformity`, `od19_iso_risk`, `od19_iso_supplier_quality`, `od19_iso_training`,
`od19_knowledge_enhanced`, `od19_meeting_room_booking`, `od19_misc_features`,
`od19_notification_multi_channel`, `od19_partner_document_sequence`, `od19_partner_thai_fields`,
`od19_product_return`, `od19_project_analytic`, `od19_project_document_sequence`,
`od19_project_enhanced`, `od19_purchase_document_sequence`, `od19_purchase_procurement_core`,
`od19_purchase_request_extend`, `od19_purchase_revision`, `od19_purchase_terms`,
`od19_purchase_wizards`, `od19_quality_control`, `od19_quotation_document_sequence`,
`od19_reporting_jasper`, `od19_sale_terms`, `od19_sale_wizards`, `od19_sales_billing_evidence`,
`od19_sales_confirm_stamp`, `od19_sales_contract_core`, `od19_sales_currency_amount`,
`od19_sales_customer_risk_gate`, `od19_sales_oca_bridge_workflow`, `od19_sales_project_context`,
`od19_sales_reporting`, `od19_service_card`, `od19_service_warranty`, `od19_stock_fifo`,
`od19_stock_picking_features`, `od19_stock_valuation_adjustment`, `od19_thai_font_support`,
`od19_thai_localization_base`, `od19_thai_tax_reports`, `od19_transportation`,
`od19_user_guide_tours`, `od19_website`

> เกณฑ์ผ่าน Section 1: โมดูล custom ที่ติดตั้งจริงทั้งหมด (`[1.5]`) ต้องมี mapping ปลายทาง
> หรือมีบันทึกเหตุผลว่า "ไม่ยก" ครบทุกโมดูล

---

## Section 2 : ปริมาณข้อมูล (Row Counts)

รัน query `[2.1]`–`[2.6]` แล้วบันทึกผล (ค่าเป็นจริงที่อ่านได้ ไม่ใช่ตัวเลขคาดเดา)
**วันที่รัน:** 2026-11-02 · **ผู้รัน:** TRAE agent (`od15_stage`, read-only) · **หลักฐาน:** `migration/od15_export/profiling_result.txt`

### 2.1 Master data

| ตาราง | จำนวนแถว | หมายเหตุ |
| --- | --- | --- |
| `res_company` | 1 | |
| `res_users` | 115 | |
| `res_partner` | 2,200 | |
| `hr_department` | 31 | |
| `hr_employee` | 113 | |
| `product_category` | 20 | |
| `product_template` | 6,986 | |
| `product_product` | 7,005 | |
| `product_supplierinfo` | 2,058 | |
| `uom_uom` | 69 | |
| `product_pricelist` | 5 | |
| `product_pricelist_item` | 2 | |

### 2.2 Accounting

| ตาราง | จำนวนแถว | หมายเหตุ |
| --- | --- | --- |
| `account_account` | 317 | |
| `account_journal` | 30 | |
| `account_tax` | 30 | |
| `account_payment_term` | 22 | |
| `account_analytic_account` | 3,273 | |
| `account_move` | 47,304 | |
| `account_move_line` | 170,274 | |

### 2.3 ขาย / ซื้อ

| ตาราง | จำนวนแถว | หมายเหตุ |
| --- | --- | --- |
| `sale_order` | 9,924 | |
| `sale_order_line` | 76,355 | |
| `purchase_order` | 3,197 | |
| `purchase_order_line` | 13,160 | |

### 2.4 account_move แยกตาม move_type และ state (query `[2.4]`)

| move_type | draft | posted | cancel | รวม |
| --- | --- | --- | --- | --- |
| `entry` | 71 | 32,178 | 2,586 | 34,835 |
| `out_invoice` | 3 | 4,056 | 205 | 4,264 |
| `out_refund` | 0 | 27 | 4 | 31 |
| `in_invoice` | 10 | 7,893 | 253 | 8,156 |
| `in_refund` | 1 | 15 | 2 | 18 |
| `out_receipt` | 0 | 0 | 0 | 0 (ไม่พบแถว) |
| `in_receipt` | 0 | 0 | 0 | 0 (ไม่พบแถว) |
| **รวม** | **85** | **44,169** | **3,050** | **47,304** ✅ = [2.2] |

### 2.5 สต็อก / มูลค่าสต็อก

| ตาราง | จำนวนแถว | หมายเหตุ |
| --- | --- | --- |
| `stock_quant` | 25,480 | |
| `stock_move` | 36,724 | |
| `stock_valuation_layer` | 25,616 | |

### 2.6 โปรเจกต์ / ไฟล์แนบ

| ตาราง | จำนวนแถว | หมายเหตุ |
| --- | --- | --- |
| `project_project` | 3,188 | |
| `ir_attachment` | 169,085 | ขนาดรวม ~63 GB (ดูข้อ 3.14) |

> เกณฑ์ผ่าน Section 2: ได้ตัวเลข baseline ครบทุกตารางที่ระบุ และบันทึกวันที่รัน/ผู้รัน — ☑ ครบ (2026-11-02)

---

## Section 3 : คุณภาพข้อมูล (Data Quality) — ต้องแก้ก่อน import

รัน query `[3.1a]`–`[3.11b]` แล้วบันทึกจำนวนที่พบ + รายการที่ต้องแก้

| # | ประเด็นที่ตรวจ | Query | เกณฑ์ผ่าน (good) | จำนวนที่พบ | ต้องแก้ไข |
| --- | --- | --- | --- | --- | --- |
| 3.1 | partner นิติบุคคลที่ VAT ว่าง | `[3.1a]` | ใกล้ 0 หรือมีรายการยกเว้น | **55** ราย | ☑ ทบทวน/ใส่ VAT หรือกำหนดข้อยกเว้น |
| 3.2 | partner ที่ VAT ไม่ใช่ 13 หลัก | `[3.1b]` | 0 ก่อน import | **88** ราย | ☑ ทำความสะอาดรูปแบบ VAT |
| 3.3 | partner ที่มีชื่อซ้ำ | `[3.2]` | 0 กลุ่ม หรือมี justification | **56** กลุ่ม | ☑ ยุบรวม/แยกแยะก่อน import |
| 3.4 | partner `active=FALSE` ที่มียอดค้าง | `[3.3]` | 0 รายการค้างผูกกับ partner ปิดใช้งาน | **0** | ☐ ไม่ต้องแก้ |
| 3.5 | product ที่ไม่มี `default_code` | `[3.4]` | 0 (เฉพาะ active) | **164** รายการ | ☑ ออกรหัสสินค้าให้ครบ |
| 3.6 | product ที่มี UoM แปลก/ไม่มาตรฐาน | `[3.5]` | ทุก UoM เป็นหน่วยที่ตกลง | **69** หน่วย (UoM ที่ถูกใช้ทั้งหมด) | ☑ ทบทวนรายการ UoM กับฝ่ายที่เกี่ยวข้อง |
| 3.7 | product ที่ราคาต้นทุนเป็น 0 (แต่มีสต็อก) | `[3.6]` | 0 สำหรับสินค้าที่มีสต็อก | **5,404** รายการ | ☑ กำหนดต้นทุนก่อนทำ opening stock |
| 3.8 | สินค้าที่มีสต็อกติดลบ | `[3.7]` | 0 ก่อนทำ opening stock | **0** | ☐ ไม่ต้องแก้ |
| 3.9 | บัญชีที่ `code` ซ้ำในบริษัทเดียว | `[3.8]` | 0 (unique ต่อ company) | **0** | ☐ ไม่ต้องแก้ |
| 3.10 | ภาษีที่ rate ผิด | `[3.9]` | ไม่มี percent นอกเหนือ 0/7 ที่ไม่ได้รับอนุมัติ | **21** ราย (เป็นอัตรา WHT หัก ณ ที่จ่าย 1/2/3/5/10% — ถูกต้องตามกม.) | ☐ ยืนยันว่าเป็น WHT จริง (ไม่ต้องแก้) |
| 3.11 | เอกสารค้างเก่าเกิน 1 ปี (draft) | `[3.10a]` | ยกเลิก/ปิด หรือมีเอกสารอนุมัติ | **0** | ☐ ไม่ต้องแก้ |
| 3.12 | เอกสาร posted ยังไม่ชำระ เกิน 1 ปี | `[3.10b]` | นับรวมในยอด AR/AP opening ครบ | **36** เอกสาร (`in_invoice` 22 เก่าสุด 2022-04-01 · `out_invoice` 14 เก่าสุด 2013-07-19) | ☑ ยืนยันว่ารวมในยอด AR/AP opening |
| 3.13 | attachment ที่ระเบียนไม่สมบูรณ์ | `[3.11b]` | 0 ระเบียนว่าง | **174** ระเบียน (ไม่มีทั้ง `store_fname` และ `db_datas`) | ☑ ตรวจ/ลบระเบียนกำพร้า |
| 3.14 | attachment ที่ไฟล์หายจาก filestore | `[3.11a]` + ตรวจ filesystem | ไม่มีไฟล์หาย (ต้องตรวจที่ filesystem) | total **169,085** · on_filestore **168,911** · in_db **0** ⇒ **174** ไม่มี `store_fname` (=ข้อ 3.13) · ขนาดรวม **63 GB** | ☑ ตรวจไฟล์จริงบน filesystem (`/filestore`) |

> หมายเหตุ 3.14: SQL ตรวจได้เฉพาะ metadata (`store_fname`, `db_datas`, `file_size`)
> การยืนยันว่าไฟล์จริงหายจาก filestore ต้องตรวจที่ระดับ filesystem/`ir_attachment` store path

---

## Section 4 : ตัวเลข baseline ที่ต้อง tie หลัง import (Reconciliation Baseline)

> แก้ `DATE '2025-12-31'` ในไฟล์ SQL เป็นวันตัดยอดจริงก่อนรันทุก query ในส่วนนี้

| # | ตัวเลข baseline | Query ที่ใช้ | ค่าที่ได้ (baseline) | ค่าหลัง import | ผลต่าง | หมายเหตุ |
| --- | --- | --- | --- | --- | --- | --- |
| 4.1 | Trial Balance ณ วันตัดยอด (รายบัญชี) | `[4.1a]` | **199 บัญชี** ที่มีความเคลื่อนไหว | | | ณ `2025-12-31` (ตัวอย่าง) |
| 4.2 | Trial Balance ยอดรวม (debit = credit) | `[4.1b]` | debit **10,011,821,337.61** = credit **10,011,821,337.61** · balance **0.00** ✅ | | | debit = credit ผ่าน |
| 4.3 | AR คงเหลือ แยกตาม partner | `[4.2]` | รวม **32,442,103.01** (60 partner) | | | |
| 4.4 | AR aging (not_due / 0–90 / >90) | `[4.2b]` | not_due **27,194,897.90** · 0–90 **251,450.00** · >90 **4,995,755.11** | | | ผลรวม = 32,442,103.01 ✅ = ข้อ 4.3 |
| 4.5 | AP คงเหลือ แยกตาม partner | `[4.3]` | รวม **-16,081,136.61** (149 partner) | | | ติดลบ = เจ้าหนี้ |
| 4.6 | AP aging (not_due / 0–90 / >90) | `[4.3b]` | not_due **-15,794,019.94** · 0–90 **0.00** · >90 **-287,116.67** | | | ผลรวม = -16,081,136.61 ✅ = ข้อ 4.5 |
| 4.7 | มูลค่าสต็อก + ปริมาณ แยกสินค้า | `[4.4a]` | **634** สินค้าที่มี layer เหลือ | | | จาก valuation layer |
| 4.8 | ปริมาณคงเหลือจาก stock_quant | `[4.4b]` | **588** สินค้า · รวม **13,808.00** หน่วย | | | ต้องสอดคล้องกับ 4.7 |
| 4.9 | มูลค่าสต็อกรวมทั้งบริษัท | `[4.4c]` | ปริมาณ **18,901.00** · มูลค่า **38,744,146.65** | | | จาก `stock_valuation_layer` ทั้งตาราง |
| 4.10 | ทะเบียนสินทรัพย์ + ค่าเสื่อมสะสม | `[5.1]` (optional) | ยังไม่รัน — ต้องยืนยันตาราง asset ก่อน | | | ดู `[5.0]` |
| 4.11 | ยอด WHT ค้าง | `[5.2]` (optional) | ยังไม่รัน — ต้องยืนยันชื่อตาราง/คอลัมน์ก่อน | | | ตาราง custom |
| 4.12 | เงินทดรองค้าง | `[5.3]` (optional) | ยังไม่รัน — ต้องยืนยันชื่อตาราง/คอลัมน์ก่อน | | | ตาราง custom |
| 4.13 | เช็คค้างรับ/ค้างจ่าย | `[5.4]` (optional) | ยังไม่รัน — ต้องยืนยันชื่อตาราง/คอลัมน์ก่อน | | | ตาราง custom |
| 4.14 | จำนวนเอกสารค้างทั้งหมด | `[4.9]` | draft **85** · posted-unpaid **379** · SO confirmed **52** · SO quotation **3,544** · PO confirmed **113** · PO RFQ **159** · project active **3,180** | | | draft/posted-unpaid/SO/PO/project |

> หมายเหตุ [4.4c] ปริมาณจาก `stock_valuation_layer` (18,901) สูงกว่าจาก `stock_quant` (13,808)
> เพราะ valuation layer สะสมตามการรับเข้า/ตัดออก ขณะที่ quant คือยอดนับจริงในคลัง —
> **ต้องกระทบยอดส่วนต่างนี้กับฝ่ายสต็อกก่อนทำ opening stock**

> ข้อควรระวัง: ตัวเลขในส่วน 4.10–4.13 อ้างถึงตารางที่ต้องยืนยันก่อนว่ามีอยู่ในฐานข้อมูลจริง
> (ดูส่วน Optional ในไฟล์ SQL และ `[5.0]`) ห้ามกรอกตัวเลขก่อนยืนยันว่าตารางมีอยู่จริง

---

## Section 5 : เกณฑ์ผ่าน/ไม่ผ่าน (Acceptance Gate) ของการ Profiling

การ Profiling ถือว่า "ผ่าน" เมื่อครบทุกข้อ:

- [x] **G1 — ข้อมูลครบ:** รัน query ครบทุกข้อในส่วนที่ 0–4 และบันทึกผลในเอกสารนี้แล้ว
      (ส่วนที่ 5 เป็น optional — ยังไม่รัน รอเปิดใช้หลังยืนยันตาราง)
- [x] **G2 — ตรวจเวอร์ชัน:** ยืนยันได้ว่าเป็น Odoo 15 (`base` `latest_version` = `15.0.1.3`
      เนื่องจาก `base_version` ไม่มีใน `ir_config_parameter`) และรันบนสำเนา `od15_stage`
      แบบ read-only (`transaction_read_only = on`) เท่านั้น
- [ ] **G3 — Module inventory ครบ:** โมดูล custom ที่ติดตั้งจริง 167 ตัว ยังต้องทำ mapping
      ไปยัง `od19_*` หรือบันทึกเหตุผล "ไม่ยก" ให้ครบ → **ค้าง Task D2**
- [ ] **G4 — ไม่มี blocking data-quality issue:** ประเด็น blocking ใน Section 3 (3.1–3.3, 3.5, 3.7, 3.13)
      ยังต้องแก้ หรือมีแผนแก้ที่อนุมัติ ก่อนเริ่ม ETL/import
- [ ] **G5 — Baseline ถูกบันทึกและ sign-off:** ตัวเลข baseline ใน Section 4 บันทึกครบแล้ว
      แต่ยัง **รอลงนามรับรอง (sign-off) โดยฝ่ายบัญชี**
- [x] **G6 — หลักฐานครบ:** มีไฟล์ `migration/od15_export/profiling_result.txt` และเอกสารนี้ที่กรอกผลครบแล้ว

| รายการ sign-off | ชื่อ | ตำแหน่ง | วันที่ | ลายเซ็น |
| --- | --- | --- | --- | --- |
| ผู้รัน Profiling | TRAE agent (อ่านอย่างเดียว) | Migration / Data engineering | 2026-11-02 | — |
| หัวหน้าฝ่ายบัญชี (baseline) | | | | |
| Migration lead | | | | |

---

## Section 6 : ตารางบันทึกผล (Result Log)

| วันที่รัน | ผู้รัน | Query / ส่วน | ผลลัพธ์ | ความผิดปกติที่พบ | การแก้ไข | สถานะ |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-11-02 | TRAE agent | `[0.1]`–`[0.3]` | read_only=on · db=od15_stage · base=15.0.1.3 | `base_version` = 0 rows | ใช้ `base.latest_version` แทน (ผ่าน G2) | ☑ |
| 2026-11-02 | TRAE agent | `[1.1]`–`[1.5]` | installed=432 · core206/OCA59/custom167 | โฟลเดอร์สำรวจเป็นมุมมองบางส่วน (gap 84) | บันทึกหัวข้อ 1.2.4 + ส่งต่อ Task D2 | ☑ |
| 2026-11-02 | TRAE agent | `[3.6]` (ราคาต้นทุน 0) | 5,404 รายการ | คอลัมน์ `standard_price` ไม่อยู่บน product (company_dependent) | rewrite JOIN `ir_property` แล้วรันซ้ำได้ (EXIT=0) | ☑ |
| 2026-11-02 | TRAE agent | `[2.1]`–`[2.6]`, `[3.1a]`–`[3.11b]` | ดู Section 2–3 | พบ blocking: VAT ว่าง 55 · VAT ผิดรูป 88 · ชื่อซ้ำ 56 · ไม่มีรหัสสินค้า 164 · ต้นทุน 0 5,404 · attachment กำพร้า 174 | ส่งต่อฝ่ายที่เกี่ยวข้องแก้ก่อน import | ⚠ แก้ต่อ |
| 2026-11-02 | TRAE agent | `[4.1a]`–`[4.9]` | TB debit=credit=10,011,821,337.61 · AR 32,442,103.01 · AP -16,081,136.61 · Stock value 38,744,146.65 | SVL qty 18,901 ≠ quant 13,808 | ต้องกระทบยอดกับฝ่ายสต็อก | ⚠ รอ sign-off |

---

## ภาคผนวก: ตาราง/คอลัมน์ที่ยืนยันกับ source Odoo 15 CE แล้ว

อ้างอิงจาก source ที่ `c:\odoo-dev\Odoo15Backup\odoo\odoo15`

| ตาราง/คอลัมน์ | ไฟล์:บรรทัด (evidence) | สถานะ |
| --- | --- | --- |
| `ir_module_module` (`name`, `latest_version`, `state`, `author`, `maintainer`) | `odoo/addons/base/models/ir_module.py:154,257,259,263,264,273,286` | ✅ ยืนยัน |
| `ir_config_parameter` (`key`, `value`) | `odoo/addons/base/models/ir_config_parameter.py:30,35,36` | ✅ ยืนยัน |
| `res_partner` (`vat`, `active`, `is_company`, `company_type`) | `odoo/addons/base/models/res_partner.py:134,172,181,209,213` | ✅ ยืนยัน |
| `ir_attachment` (`store_fname`, `db_datas`, `file_size`, `res_model`, `res_id`) | `odoo/addons/base/models/ir_attachment.py:39,384,385,387,403,404,405` | ✅ ยืนยัน |
| `account_account` (`code`, `internal_type`, `internal_group`, `user_type_id`) | `addons/account/models/account_account.py:36,61,64,66,67` | ✅ ยืนยัน |
| `account_account_type.type` ค่าคือ `other/receivable/payable/liquidity` | `addons/account/models/account_account.py:13-18` | ✅ ยืนยัน (Odoo 15 ใช้ค่าเหล่านี้ ไม่ใช่ `asset_receivable`/`liability_payable`) |
| `account_move` (`move_type`, `state`, `date`, `payment_state`, `amount_residual`) | `addons/account/models/account_move.py:160-176,185,239,256` | ✅ ยืนยัน |
| `account_move_line` (`move_id`, `date`, `parent_state`, `account_id`, `balance`, `amount_residual`, `full_reconcile_id`, `date_maturity`, `partner_id`) | `addons/account/models/account_move.py:3525-3646` | ✅ ยืนยัน (ไม่มีคอลัมน์ stored `account_type`/`internal_type` — ต้อง JOIN `account_account`) |
| `account_journal` (`code`, `type`, `company_id`) | `addons/account/models/account_journal.py:27,56,58,98` | ✅ ยืนยัน |
| `account_tax` (`amount`, `amount_type`, `type_tax_use`, `active`) | `addons/account/models/account_tax.py:62,72,75,87,95` | ✅ ยืนยัน |
| `account_payment_term` | `addons/account/models/account_payment_term.py:10` | ✅ ยืนยัน |
| `account_analytic_account` (`code`, `name`, `active`, `partner_id`) | `addons/analytic/models/analytic_account.py:58,126,127,128,137` | ✅ ยืนยัน |
| `product_template` (`type`, `detailed_type`, `categ_id`, `standard_price`, `uom_id`, `active`, `default_code`) | `addons/product/models/product_template.py:16,47,53,62,83,105,122,140` ; `type` ได้ `product` จาก `addons/stock/models/product.py:643` | ✅ ยืนยัน |
| `product_product` (`default_code`, `standard_price`, `product_tmpl_id`) | `addons/product/models/product.py:76,97,104,116` | ✅ ยืนยัน |
| `product_supplierinfo` (`min_qty`, `price`, `product_tmpl_id`) | `addons/product/models/product.py:800,820,823,838` | ✅ ยืนยัน |
| `product_category` | `addons/product/models/product.py:19` | ✅ ยืนยัน |
| `product_pricelist` / `product_pricelist_item` | `addons/product/models/product_pricelist.py:13,354` | ✅ ยืนยัน |
| `hr_department` (`name`, `active`, `company_id`) | `addons/hr/models/hr_department.py:9,15,17,18` | ✅ ยืนยัน |
| `hr_employee` (`active`, `company_id`) | `addons/hr/models/hr_employee.py:28,39,40` | ✅ ยืนยัน |
| `stock_quant` (`product_id`, `location_id`, `quantity`, `company_id`) | `addons/stock/models/stock_quant.py:17,53,63,64,79` | ✅ ยืนยัน |
| `stock_move` (`product_qty`, `location_id`, `state`) | `addons/stock/models/stock_move.py:21,51,73,96` | ✅ ยืนยัน |
| `stock_valuation_layer` (`product_id`, `quantity`, `value`, `remaining_qty`, `remaining_value`) | `addons/stock_account/models/stock_valuation_layer.py:10,17,20,24,25,26` | ✅ ยืนยัน |
| `sale_order.state` = `draft/sent/sale/done/cancel` | `addons/sale/models/sale_order.py:168-174` | ✅ ยืนยัน |
| `purchase_order` (`state` = `draft/sent/to approve/purchase/done/cancel`) | `addons/purchase/models/purchase.py:22,99-106` | ✅ ยืนยัน |
| `project_project` (`name`, `active`, `company_id`, `analytic_account_id`) | `addons/project/models/project.py:177,269,271,282,284` | ✅ ยืนยัน |
| `account_asset` / ตาราง asset | ไม่พบใน source Odoo 15 CE (`addons`, `odoo/addons`) | ⚠️ ต้องยืนยัน (enterprise/OCA) |
| `dtr_wht`, `dtr_account_prepayment`, cheque ฯลฯ | เป็นโมดูล custom — ไม่มีใน core | ⚠️ ต้องยืนยันจาก `ir_module_module` + `information_schema` (`[5.0]`) |
