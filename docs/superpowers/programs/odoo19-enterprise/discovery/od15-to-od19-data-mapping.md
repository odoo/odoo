# Data Migration Mapping: Odoo 15 → Odoo 19 (Master Data + ยอดยกมา)

**วันที่จัดทำ:** 2026-10-31
**ขอบเขต:** เฉพาะ **master data + ยอดยกมา (opening balances)** — ไม่ย้ายประวัติธุรกรรม
**ระบบต้นทาง (Source):** Odoo 15 CE — `custom15_autoinfo` (`autoinfo_*`) และ `odoo15_mods*` (ตระกูล `dtr_*`)
**ระบบปลายทาง (Target):** Odoo 19 CE — `custom_addons/od19_*` + OCA (`third_party/oca/*`) + `l10n_th`

**เอกสาร / เครื่องมือที่เกี่ยวข้อง:**

| ประเภท | ไฟล์ |
|---|---|
| แผนงานแม่ | [2026-10-22-odoo15-to-odoo19-data-migration-plan.md](../../plans/2026-10-22-odoo15-to-odoo19-data-migration-plan.md) |
| Gap Analysis (โมดูล OD15 → OD19) | [GAP_ANALYSIS_OD15_to_OD19.md](../../../../GAP_ANALYSIS_OD15_to_OD19.md) (ส่วนที่ 1 autoinfo · ส่วนที่ 2 DTR) |
| Mapping workbook (11 ชีต) | [od15-to-od19-data-mapping.xlsx](od15-to-od19-data-mapping.xlsx) |
| CSV mapping | [migration/mapping/](../../../../migration/mapping) |
| ETL runner | [migration/import/](../../../../migration/import) (`common.py`, `legacy.py`, `run.py`, `steps/s01…s09`) |
| OD15 export (ข้อมูลจริง) | [migration/od15_export/](../../../../migration/od15_export) (`od15_autoerp_prd.dump`, `modules.txt`, `dtr_columns.txt`, `versions.txt`) |
| ทะเบียนตาราง `dtr_*` (192) | [dtr_columns.txt](../../../../migration/od15_export/dtr_columns.txt) |

---

## 1. หลักการที่บังคับ (Invariants)

1. **อ่าน OD15 แบบ read-only** ผ่าน `legacy.py` (`conn.set_session(readonly=True)`) จาก staging DB `od15_stage`
2. **เขียน OD19 ผ่าน ORM เท่านั้น** — ห้าม raw SQL / `cr.commit()` ใน logic ขั้นตอน (commit เฉพาะใน `run.py` ระหว่าง step)
3. **Idempotency ด้วย External ID** รูปแบบ `__import15__.<model_name_with_underscores>.<legacy_id>` ผ่าน `ir.model.data`
   — สร้างโดย `common.upsert(model, legacy_id, vals)` → คืน `(record, action)` โดย `action ∈ {created, updated, skipped}`
4. **รันซ้ำได้ (re-runnable)** — ทุก record ต้องมี External ID เสมอ
5. **Dry-run ก่อนจริง** — `MIG_DRY_RUN=1` จะไม่เขียนข้อมูล (action = `skipped`)
6. **ค่าที่ map ข้ามระบบเก็บเป็น CSV** (ไม่สร้าง Odoo model) ที่ `migration/mapping/` — โหลดด้วย `common.load_map()` (ข้ามแถวที่ขึ้นต้น `EXAMPLE`)
7. **ยอดยกมาต้องกระทบยอดกับงบการเงินเดิมให้ตรงก่อนนำเข้าจริง**

**ลำดับขั้นตอน (ห้ามสลับ):** `s01_reference → s02_master → s03_partners → s04_products → s05_terms → s06_people → s07_projects → s08_opening → s09_sequences`

---

## 2. แหล่งข้อมูลฝั่ง OD15 (Source Families)

| ตระกูล | ตัวอย่างโมดูล | ป้อนเข้าสู่ master data อะไร |
|---|---|---|
| `autoinfo_*` | `autoinfo_employees`, `autoinfo_sale_form`, … | แผนก/พนักงาน, เงื่อนไขซื้อขาย, ผังบัญชีเสริม |
| `dtr_*` (Base/Stock/Product) | `dtr_company`, `dtr_partner_master`, `dtr_product_master`, `dtr_taxes`, `dtr_coa` | บริษัท, คู่ค้า, สินค้า, ภาษี, ผังบัญชี |
| `dtr_*` (Accounting) | `dtr_fixed_assets`, `dtr_cheque`, `dtr_advance`, `dtr_petty_cash`, `dtr_taxation`, `dtr_account_cash` | สินทรัพย์ถาวร, เช็ค, เงินทดรอง, ภาษี, เงินสด |
| `dtr_*` (Sales/Purchase) | `dtr_sales`, `dtr_purchase`, `dtr_sale.*.report` | เงื่อนไขขาย/ซื้อ, ราคา, รายชื่อผู้ขายสินค้า |
| `dtr_*` (Manufacturing) | `dtr_mrp`, `dtr_mrp_report` | **ไม่ต้องย้าย** — ต้นทาง `uninstalled` ทั้งตระกูล (2026-10-31) → Retire |

> ✅ **อัปเดต 2026-10-31 — ได้ข้อมูลจริงจากต้นทางแล้ว:** DB dump `AUTOERP-PRD` (`od15_autoerp_prd.dump`, 10.07 MB, PG 12.22, TOC 23,643) โอนมาที่ `migration/od15_export/` เรียบร้อย
> · ทะเบียนโมดูลจริง 170 รายการ (`modules.txt`: installed=123 / uninstalled=46 / uninstallable=1) · เวอร์ชันโมดูลหลัก (`versions.txt`: `base|15.0.1.3`)
> · โครงสร้างคอลัมน์ตาราง `dtr_*` แล้ว **192 ตาราง / 2,390 คอลัมน์** (`dtr_columns.txt`) → ทำ field-level mapping ฝั่ง `dtr_*` ได้ทันที
> ⚠️ คอลัมน์ที่ยังต้องยืนยันคือ **คอลัมน์ที่ `dtr_*`/`autoinfo_*` เติมเข้าไปในตารางมาตรฐาน** (`res_partner`, `product_template`, `account_move`, …) ซึ่งยังไม่ได้ดึง — ต้องอ่าน `information_schema` ของ `od15_stage` หลัง restore (`s03_partners.py` มี helper `_legacy_columns()` เป็นแบบอย่าง)

---

## 3. Mapping ต่อเอนทิตี (ตามขั้นตอน ETL)

คอลัมน์ **Key** = External ID ที่ใช้ (`__import15__.<model>.<legacy_id>`)
สถานะ: ✅ ปลายทางมีจริงและติดตั้ง · 🟡 ปลายทางมีแต่ต้องปรับ · ❌ ยังไม่มีปลายทาง

### 3.1 s01_reference — บริษัท / สกุลเงิน / ผังบัญชี / ภาษี

| เอนทิตี | OD15 (ตาราง) | OD19 (model.field) | การแปลง | CSV ที่ใช้ | สถานะ |
|---|---|---|---|---|---|
| บริษัท (หลัก) | `res_company` | `res.company` (`name`, `vat`, `street`, `city`, `zip`, `currency_id`) | ย้ายตรง; ตั้ง `branch_code`/`tax_name` ถ้า `od19_partner_thai_fields` ติดตั้ง | — | ✅ |
| สกุลเงิน | `res_currency` | `res.currency.active` | เปิดใช้งานรหัสที่ OD15 ใช้ | — | ✅ |
| อัตราแลกเปลี่ยน | `res_currency_rate` | `res.currency.rate` | อิงวันที่ + บริษัท | — | 🟡 |
| ผังบัญชี | `account_account` (company-dependent `code`) | `account.account` (`code`, `name`, `account_type`) | map รหัส OD15→OD19; กำหนด `account_type` ให้ถูก | `account_map.csv` | ✅ |
| ภาษี | `account_tax` | `account.tax` (`type_tax_use`, `amount`, `invoice_repartition_line_ids`) | ตรวจชนิดขาย/ซื้อ + บัญชีใน repartition line | `tax_map.csv` | ✅ |

> แหล่ง OD15: `dtr_coa`, `dtr_coa_alternative`, `dtr_taxes`, `dtr_taxes_with_coa`, `dtr_taxation*` → ปลายทาง `l10n_th` + OCA `l10n_th_account_tax` + `od19_thai_localization_base`

### 3.2 s02_master — สมุดรายวัน / ภาษี / เงื่อนไขชำระ / หน่วยนับ / ราคา

| เอนทิตี | OD15 (ตาราง) | OD19 (model.field) | การแปลง | CSV ที่ใช้ | สถานะ |
|---|---|---|---|---|---|
| สมุดรายวัน | `account_journal` | `account.journal` (`code`, `name`, `type`, `default_account_id`) | map ด้วย `code`; คงชนิด sale/purchase/cash/bank/general | `journal_map.csv` | ✅ |
| เงื่อนไขชำระ | `account_payment_term` | `account.payment.term` + `.line` | map ด้วยชื่อ; สร้าง line (%/วัน) 30/60/90 | `payment_term_map.csv` | ✅ |
| หน่วยนับ | `product_uom` | `uom.uom` (`uom_id`, `uom_po_id`) | map ให้ตรงพร้อม `ratio` (กันสูตรแปลงเพี้ยน) | `uom_map.csv` | ✅ |
| หมวดหมู่สินค้า | `product_category` | `product.category` | map ชื่อ; ตั้งบัญชีสินค้าคงคลัง/รายได้/ต้นทุน | `product_category_map.csv` | 🟡 |
| นโยบายราคา | `product_pricelist` + `.item` | `product.pricelist` + `.item` | ย้ายค่าเริ่มต้น/ช่วงจำนวน/ส่วนลด | — | 🟡 |

### 3.3 s03_partners — คู่ค้า (ลูกค้า/ผู้ขาย)

อ้างอิงซอร์สจริง: [s03_partners.py](../../../../migration/import/steps/s03_partners.py) (`_WANTED_COLUMNS`)

| ฟิลด์ OD19 | ฟิลด์ OD15 | การแปลง | สถานะ |
|---|---|---|---|
| `ref` | `ref` | กำหนดรหัสใหม่ไม่ซ้ำ (C0001/V0001) | 🟡 |
| `name` | `name` | ย้ายตรง (บังคับ มีค่า) | ✅ |
| `company_type` | `is_company` | `is_company` ? `company` : `person` | ✅ |
| `vat` | `vat` | normalize เลขภาษี 13 หลัก (ตัดอักขระ) | ✅ |
| `customer_rank` / `supplier_rank` | `customer_rank` / `supplier_rank` | >0 → 1 ไม่งั้น 0 | ✅ |
| `email` / `phone` / `mobile` / `website` | คอลัมน์ชื่อเดียวกัน | ย้ายตรง (ว่าง → `False`) | ✅ |
| `street` / `street2` / `city` / `zip` | คอลัมน์ชื่อเดียวกัน | ย้ายตรง | ✅ |
| `country_id` | `country_id` | map ด้วย `res_country.code` | ✅ |
| `property_payment_term_id` | `property_payment_term_id` | map ชื่อผ่าน `payment_term_map.csv` | ✅ |
| `property_supplier_payment_term_id` | `property_supplier_payment_term_id` | map ชื่อผ่าน `payment_term_map.csv` | ✅ |
| `tax_name` | `tax_name` *(ตรวจสอบ)* | ย้ายตรง; fallback = `name` (ต้องมี `od19_partner_thai_fields`) | ✅ |
| `branch_code` | `branch_code` / `tax_branch_code` *(ตรวจสอบ)* | ตัดเป็น 5 หลัก; สำนักงานใหญ่ = `00000` | ✅ |
| `name_en` / `address_en` / `fax` | `name_en` / … / `fax` *(ตรวจสอบ)* | ย้ายตรง (เฉพาะเมื่อฟิลด์มีจริง) | 🟡 |
| `od19_amphoe` / `od19_subdistrict` | ที่อยู่แยกตำบล/อำเภอ OD15 *(ตรวจสอบ)* | ย้ายตรงถ้ามีใน OD15 | 🟡 |

> แหล่ง OD15: `dtr_partner_master`, `dtr_company`, `autoinfo_*` (แผนก/พนักงาน); Tag หมวดลูกค้า/ผู้ขายผ่าน `partner_category_map.csv`
> ⚠️ ห้ามนำเข้าบริษัทภายใน (มี `WHERE p.id NOT IN (SELECT partner_id FROM res_company)`) และเฉพาะ `active=true` ที่มี rank > 0

### 3.4 s04_products — สินค้า/บริการ

| ฟิลด์ OD19 | ฟิลด์ OD15 | การแปลง | สถานะ |
|---|---|---|---|
| `default_code` | `default_code` | ย้ายตรง | ✅ |
| `barcode` | `barcode` | ย้ายตรง | ✅ |
| `name` | `name` | ย้ายตรง | ✅ |
| `type` / `is_storable` | `type` | Odoo 17+ ใช้ `type='consu'` + `is_storable=True` สำหรับสินค้าคงคลัง | ✅ |
| `categ_id` | `categ_id` | map ผ่าน `product_category_map.csv` | 🟡 |
| `uom_id` / `uom_po_id` | `uom_id` / `uom_po_id` | map ผ่าน `uom_map.csv` | ✅ |
| `list_price` | `list_price` | ย้ายตรง | ✅ |
| `standard_price` | `standard_price` | ย้ายตรง (ฐาน FIFO) | ✅ |
| `taxes_id` / `supplier_taxes_id` | `taxes_id` / `supplier_taxes_id` | map ผ่าน `tax_map.csv` | ✅ |
| `route_ids` | (routes OD15) | map ให้ตรง (MTO/Buy/Make) | 🟡 |
| `seller_ids` (supplier info) | `product_supplierinfo` | นำเข้าผู้ขาย+ราคา | 🟡 |
| ฟิลด์เสริมจาก `od19_inventory_execution_control` / `od19_service_card` / `od19_service_warranty` | *(ตรวจสอบซอร์ส OD15)* | ตรวจฟิลด์จริงของโมดูลก่อนเขียน | 🟡 |

> แหล่ง OD15: `dtr_product_master`, `dtr_product_category`, `dtr_stock`, `dtr_stock_fifo`

### 3.5 s05_terms — เงื่อนไขซื้อ/ขาย (master)

ปลายทางที่ยืนยันจากซอร์สแล้ว: `od19.sale.term.template` ([sale_term_template.py](../../../../custom_addons/od19_sale_terms/models/sale_term_template.py)) และ `od19.purchase.term.template` ([purchase_term_template.py](../../../../custom_addons/od19_purchase_terms/models/purchase_term_template.py))

| กลุ่ม | โมเดล OD15 (จาก workbook ชีต 05) | OD19 model (`term_type`) | สถานะ |
|---|---|---|---|
| Sale — ราคา | `dtr.sale.price.report` | `od19.sale.term.template` (`price`) | ✅ |
| Sale — จัดส่ง | `dtr.sale.delivery.report` | `od19.sale.term.template` (`delivery`) | ✅ |
| Sale — ชำระ (สินค้า) | `dtr.sale.payment.product.report` | `od19.sale.term.template` (`payment_product`) | ✅ |
| Sale — ชำระ (วิศวกรรม) | `dtr.sale.payment.engineering.report` | `od19.sale.term.template` (`payment_engineering`) | ✅ |
| Sale — อายุใบเสนอราคา | `dtr.sale.validity.report` | `od19.sale.term.template` (`validity`) | ✅ |
| Sale — ประกัน | `dtr.sales_warranty` | `od19.sale.term.template` (`warranty`) | ✅ |
| Sale — เครดิต | (dtr sales credit) | `od19.sale.term.template` (`credit`) | 🟡 |
| Purchase — ประกัน | `dtr.purchase.warranty.report` | `od19.purchase.term.template` (`warranty`) | ✅ |
| Purchase — ส่งถึง | `dtr.purchase.delivery.report` | `od19.purchase.term.template` (`delivery_to`) | ✅ |
| Purchase — ชำระ | `dtr.purchase.payment.report` | `od19.purchase.term.template` (`payment_term`) | ✅ |
| Purchase — การส่งของ | `dtr.purchase.shipment.report` | `od19.purchase.term.template` (`shipment`) | ✅ |
| Purchase — น้ำหนัก | `dtr.purchase.weight.report` | `od19.purchase.term.template` (`weight`) | ✅ |

> unique constraint: `(name, term_type)` — ต้อง dedupe ก่อน upsert
> แหล่ง OD15: `dtr_sales_form`, `dtr_purchase_form`, `autoinfo_sale_form`

### 3.6 s06_people — พนักงาน / แผนก / ผู้ใช้ / กลุ่ม

| เอนทิตี | OD15 | OD19 | การแปลง | สถานะ |
|---|---|---|---|---|
| แผนก | `hr_department` (+ แผนก custom `autoinfo_employees`) | `hr.department` | ย้ายตรง; ตั้ง `parent_id` เป็นโครงองค์กร | ✅ |
| พนักงาน | `hr_employee` | `hr.employee` (`name`, `department_id`, `job_title`, `work_email`) | map แผนกจากขั้นก่อน | ✅ |
| Badge/PIN | `hr_employee.barcode` / PIN | `hr.employee.barcode` | คง Badge/PIN ให้ตรงเครื่องสแกน (`od19_hr_attendance_zkteco`) | ✅ |
| โควต้าลา | ยอดวันลาคงเหลือ | `hr.leave.allocation` / `hr.leave.type` | ตั้งยอดคงเหลือเป็นยอดยกมา | 🟡 |
| ผู้ใช้ | `res_users` | `res.users` (`login`, `group_ids`, `employee_ids`) | สร้างหลังพนักงาน; **ห้ามตั้งรหัสผ่านคงที่** | ✅ |
| กลุ่มสิทธิ์ | `res_groups` (จาก `dtr_access_right_*`) | `res.groups` + OCA `base_user_role` (`od19_security_roles`) | map บทบาทตาม RBAC ศูนย์กลาง (SoD) | ✅ |

### 3.7 s07_projects — โครงการ / Job No. / Analytic

ปลายทางยืนยันจากซอร์ส: `project.project` ต่อเติมด้วย `od19_project_enhanced` → ฟิลด์ `job_no`, `od19_department_id`, `od19_project_type_id`, `od19_responsible_person_ids`, `od19_coordinator_ids`, `od19_scope_of_work`, `od19_document_requirements`

| ฟิลด์ OD19 | ฟิลด์ OD15 | การแปลง | สถานะ |
|---|---|---|---|
| `name` | ชื่อโครงการ | ย้ายตรง | ✅ |
| `partner_id` | ลูกค้า | map จาก `res.partner` | ✅ |
| `job_no` | เลขที่โครงการ/Job No. | คงรูปแบบเดิม (S+Initials+YY-RunningNo) หรือออกใหม่ตามนโยบาย | 🟡 |
| `od19_project_type_id` | Project Type (OD15) | map เข้า `od19.project.type` | 🟡 |
| `od19_department_id` | แผนก | map จาก `hr.department` | ✅ |
| `od19_responsible_person_ids` / `od19_coordinator_ids` | ผู้รับผิดชอบ | map จาก `hr.employee` | ✅ |
| — | Analytic Account (OD15) | `account.analytic.account` + `account.analytic.plan` (v19 แยก plan จาก account) ผูกกับโครงการ | 🟡 |

> แหล่ง OD15: `dtr_project`, `dtr_purchase_project`, `dtr_invoice_project`, `dtr_project_analysis`

### 3.8 s08_opening — ยอดยกมา (ต้องกระทบยอดก่อน)

| หมวด | OD19 วิธีนำเข้า | บัญชีคุม | สถานะ |
|---|---|---|---|
| AR (ลูกหนี้คงค้าง) | `account.move` (`move_type='entry'`) ต่อคู่ค้า 1 ใบ → `action_post()` | `receivable` | 🟡 |
| AP (เจ้าหนี้คงค้าง) | `account.move` (`move_type='entry'`) ต่อคู่ค้า 1 ใบ → `action_post()` | `payable` | 🟡 |
| สินค้าคงเหลือ | `stock.quant` + `_apply_inventory()` → เกิด `stock.valuation.layer` (ต้องติดตั้ง `od19_stock_fifo`) | `Stock Valuation` | 🟡 |
| สินทรัพย์ถาวร | `account.asset` (OCA `account_asset_management` + `od19_asset_disposal`) — นำเข้าเป็นรายทรัพย์สิน | สินทรัพย์/ค่าเสื่อมสะสม | 🟡 |
| WHT ค้างรับ/ค้างจ่าย | `account.move` (`entry`) — บัญชี WHT map ผ่าน `account_map.csv` | บัญชีคุม WHT | 🟡 |
| เงินเบิกล่วงหน้า | `account.advance` (`od19_accounting_advance`) | — | 🟡 |
| เช็คค้าง | `account.cheque` / `account.cheque.book` (`od19_accounting_cheque`) — เฉพาะที่ยังค้าง | — | 🟡 |

**หลักสำคัญ:** ทุกบรรทัดของ Opening JE ต้องตั้ง `partner_id` เพื่อให้รายงาน aging ทำงาน; ทุกใบต้อง `balance = 0` โดยคู่กับบัญชี "ยอดยกมาคู่ปรับ"

### 3.9 s09_sequences — ความต่อเนื่องของเลขรัน

| ประเภทเอกสาร | OD15 | OD19 (`ir.sequence`) | สถานะ |
|---|---|---|---|
| ใบเสนอราคา | เลขล่าสุด Quotation | `od19_quotation_document_sequence` (`number_next_actual = last + 1`) | 🟡 |
| ใบสั่งขาย | เลขล่าสุด SO | `od19_document_sequence` / core `sale.order` | 🟡 |
| ใบขอซื้อ/ใบสั่งซื้อ | เลขล่าสุด PR/PO | `od19_purchase_request_extend`, `od19_purchase_document_sequence` | 🟡 |
| เลขที่โครงการ (Job No.) | รันตามแผนก | `od19_project_document_sequence` (ดูชีต 07 รูปแบบ) | 🟡 |
| ใบเบิก/รับเข้า (WH/{DEPT}/…) | รันต่อแผนก/คลัง | sequence ที่ใช้ `use_date_range` → ปรับ `ir.sequence.date_range.number_next_actual` | 🟡 |
| ใบสำคัญ (Voucher) | Voucher running | `od19_accounting_document_sequence` (`od19_voucher_no`) | 🟡 |

---

## 4. โมเดล custom ของ `dtr_*` ที่ยังไม่มีปลายทาง (ต้องตัดสินใจก่อน migrate)

อ้างอิง [GAP_ANALYSIS_OD15_to_OD19.md](../../../../GAP_ANALYSIS_OD15_to_OD19.md) (ส่วนที่ 2 — DTR, §9)

| โมเดล OD15 | Use case | สถานะปลายทาง OD19 | สิ่งที่ต้องทำ |
|---|---|---|---|
| `dtr.account.cash` (+`_with_purchase`/`_with_sales`) | เงินสดย่อย/รับจ่ายเงินสด | ❌ ไม่มี | **ติดตั้งจริงทั้ง 3 (2026-10-31)** — ต้อง develop หรือรวมเข้า `od19_accounting_cheque`/`advance`/`petty_cash` (ห้าม Retire) |
| `dtr.partner.fee` | ค่าธรรมเนียมคู่ค้า (percent/amount, ผูกบัญชี+analytic) | ❌ ไม่มี | ตัดสินใจ develop หรือ Retire ถ้าไม่มี use case |
| `dtr.general.template` (+line) | เทมเพลตบัญชีสำหรับ JE | 🟡 ไม่มีตรง | ตรวจว่า `od19_accounting_features` ครอบ หรือใช้ Misc journal template |
| `dtr.account.control.level` | ระดับการควบคุมบัญชี | ❌ ไม่มี | เทียบกับ account hierarchy ของ Odoo 19 (verify) |
| `dtr.bring.forward` | ยกยอดไปงวดถัดไป | ❌ ไม่มี | ยืนยันว่า `od19_accounting_operational_closure` ครอบ |
| `dtr.product.premium` | เบี้ยประกัน/พรีเมียมสินค้า | ❌ ไม่มี | ตรวจการแมปกับ `od19_sale_terms` |
| `dtr.product.part.history` (+`_with_mrp`) | ประวัติอะไหล่ | ❌ ไม่มี | `dtr_product_part_history` **installed** (ตาราง `dtr_parts_history`+`_line`) → ต้อง develop; `_with_mrp` uninstalled → Retire |
| `dtr.stock.backdating` | ลงสต็อกย้อนหลัง | 🟡 บางส่วน | `od19_inventory_execution_control` + standard move date |
| `dtr.bank.statement.import.base` | นำเข้า statement ธนาคาร | 🟡 บางส่วน | OCA `account_statement_import_*` — **ยังไม่มีใน DB** |
| `dtr.sales.revision` | แก้ไขใบเสนอราคา | ✅ มี | OCA `sale_order_revision` + `od19_quotation_document_sequence` |
| `stock.no.negative` | ห้ามสต็อกติดลบ | ⚠️ OCA | OCA `stock_no_negative` — **ยังไม่มีใน DB** |

---

## 4.1 ทะเบียนตาราง `dtr_*` จริงจาก `AUTOERP-PRD` (192 ตาราง)

ดึงจาก `migration/od15_export/dtr_columns.txt` (2,390 คอลัมน์, `information_schema.columns`) — ใช้เป็น **source of truth** สำหรับ field-level mapping

| โดเมน | จำนวน | ตาราง |
|---|---:|---|
| Access / Security | 2 | `dtr_access_rights_template`, `dtr_access_rights_template_res_groups_rel` |
| Billing | 5 | `dtr_account_billing`, `dtr_account_billing_batch_wizard` (+`_res_partner_rel`), `dtr_account_billing_confirm_wizard`, `dtr_billing_date_config` |
| Cash | 9 | `dtr_account_cash`, `_cancel_wizard`, `_do_wizard`, `_line`, `_line_account_tax_rel`, `_mr_wizard`, `_po_wizard`, `_so_wizard`, `_transfer_line` |
| Invoice payment / return | 3 | `dtr_account_invoice_payment_method` (+`_dtr_account_cash_rel`), `dtr_account_move_product_return_rel` |
| Prepayment | 2 | `dtr_account_prepayment`, `dtr_account_prepayment_confirm_wizard` |
| Report (Excel) | 1 | `dtr_accounting_report_excel` |
| Advance (เงินทดรอง) | 17 | `dtr_adv_ac_mapping`, `dtr_adv_clear` (+`_dtr_adv_fund_rel`), `dtr_adv_clear_form` (+`_res_partner_rel`), `dtr_adv_fund`, `dtr_adv_fund_approver` (+`_res_users_rel`), `dtr_adv_fund_line`, `dtr_adv_payment`, `dtr_adv_request`, `dtr_adv_request_at_date_report` (+rel), `dtr_adv_request_condition_report` (+rel), `dtr_adv_request_form` (+rel) |
| Asset | 12 | `dtr_asset_class`, `dtr_asset_brand` (+`_series`), `dtr_asset_keeper`, `dtr_asset_insurance`, `dtr_asset_insurer`, `dtr_asset_repair`, `dtr_asset_transfer`, `dtr_asset_checking`, `dtr_asset_batch_checking`, `dtr_asset_batch_transfer`, `dtr_asset_card_report_wiz`, `dtr_depreciation_report_wiz` |
| Bring Forward | 2 | `dtr_bring_forward`, `dtr_bring_forward_line` |
| Cheque | 11 | `dtr_cheque`, `dtr_cheque_book`, `dtr_cheque_leaf`, `_mark_as_deposited`, `_mark_as_paid`, `_mark_as_to_pay`, `_printing` (+`_res_partner_rel`), `dtr_cheque_posted`, `dtr_cheque_report`, `dtr_cheque_transformation_cash` |
| Claim | 3 | `dtr_claim`, `dtr_claim_line`, `dtr_claim_symptoms` |
| Config / Misc | 4 | `dtr_close_reason`, `dtr_confirm_delivered_status` (+`_rel`), `dtr_declined_causing` |
| Contact branch | 1 | `dtr_contact_branch_info` |
| Goods Issue / Picking | 8 | `dtr_goods_issue`, `_line`, `_line_lot`, `_type`, `dtr_goods_picking`, `_issue_rel`, `_line`, `dtr_create_goods_picking` |
| VAT/WHT wizard | 4 | `dtr_create_vat_wizard` (+`_vat_base_rel`, `_vat_line_rel`), `dtr_create_wht_wizard` |
| Credit | 1 | `dtr_credit_limit` |
| Customer Master | 8 | `dtr_customer_grade`, `dtr_customer_type`, `dtr_customer_master_group`, `dtr_customer_company_group`, `dtr_customer_selling_area`, `dtr_customer_selling_type`, `dtr_customer_image`, `dtr_customer_image_type` |
| Distribute / DTO | 3 | `dtr_distribute_order`, `_line`, `dtr_dto_product_line` |
| Payment date config | 1 | `dtr_except_payment_date_config_line` |
| General amount | 3 | `dtr_general_amount`, `_move`, `_tax` |
| General Ledger | 3 | `dtr_general_ledger_report` (+`_res_partner_rel`), `dtr_general_ledger_wiz` |
| General template | 4 | `dtr_general_template`, `_line`, `_line_amount`, `_line_subtract` |
| Guarantee | 1 | `dtr_guarantee` |
| Jasper | 3 | `dtr_jasper`, `dtr_jasper_report` (+`_res_partner_rel`) |
| Partner | 2 | `dtr_partner_branch`, `dtr_partner_fee` |
| Parts history | 2 | `dtr_parts_history`, `dtr_parts_history_line` |
| Payment | 4 | `dtr_payment_condition`, `dtr_payment_date_config` (+`_line`), `dtr_payment_fee` |
| Petty Cash | 8 | `dtr_pc_ac_mapping`, `dtr_pc_fund`, `_approver` (+`_res_users_rel`), `_line`, `dtr_pc_payment` (+`_dtr_pc_requests_rel`), `dtr_pc_requests` |
| Pending reason | 2 | `dtr_pending_reason` (+`_wizard`) |
| Prefix | 1 | `dtr_prefix_partner` |
| Product | 9 | `dtr_product_brand`, `dtr_product_brand_model`, `dtr_product_tag` (+`_product_template_rel`), `dtr_product_return`, `_line`, `_cn_wiz_domain_rel`, `_cn_wiz_product_return_rel`, `_to_cn_wizard` |
| Profit & Loss | 1 | `dtr_profit_loss_by_monthly_wiz` |
| Project | 4 | `dtr_project_analysis`, `dtr_project_monthly_progress`, `dtr_project_vendor_price` (+`_line`) |
| Quality | 2 | `dtr_quality_controls`, `dtr_quality_controls_list` |
| Report base | 1 | `dtr_report_base` |
| Request limit | 1 | `dtr_request_limit` |
| Sale | 1 | `dtr_sale_scheduled_date` |
| Service / Warranty / SLA | 17 | `dtr_sales_services` (+`_line`), `dtr_service_card`, `_claim_rel`, `_reason`, `_result`, `_technician`, `_time_record`, `_type`, `dtr_service_level_agreement_setting` (+`_line`), `_state`, `_type` (+`_line`), `dtr_service_team` (+`_hr_employee_rel`, `_res_partner_rel`) |
| Stock valuation adj. | 4 | `dtr_stock_valuation_adjustment`, `_line`, `_stock_move_wizard` (+`_stock_move_rel`) |
| Technical team | 2 | `dtr_technical_team_product` (+`_res_partner_rel`) |
| Period | 1 | `dtr_tr_period` |
| Transportation | 6 | `dtr_transportation_request`, `_line`, `_type`, `dtr_transportation_method`, `dtr_truck_size`, `dtr_vehicle_type` |
| Trial balance | 1 | `dtr_trial_balance_wiz` |
| Update PO price | 2 | `dtr_update_po_price`, `dtr_update_po_price_list` |
| VAT / WHT | 5 | `dtr_vat`, `dtr_vat_rel_move`, `dtr_vat_rel_taxed`, `dtr_vat_rel_untaxed`, `dtr_wht` |
| Warranty | 3 | `dtr_warranty_card`, `dtr_warranty_card_line`, `dtr_warranty_list` |
| Year end | 1 | `dtr_year_end` |
| **รวม** | **192** | |

### 4.2 Field-level mapping: ตาราง master data หลัก (ยืนยันจาก `dtr_columns.txt`)

| ตาราง OD15 | คอลัมน์จริง (key) | ปลายทาง OD19 | สถานะ |
|---|---|---|---|
| `dtr_customer_grade` / `dtr_customer_type` / `dtr_customer_selling_area` / `dtr_customer_selling_type` | `name` | `res.partner.category` หรือ model เฉพาะใน `od19_contacts_partner_roles` | 🟡 |
| `dtr_customer_master_group` | `code`, `name` | `res.partner.category` | 🟡 |
| `dtr_customer_company_group` | `name`, `remark` | `res.partner.category` | 🟡 |
| `dtr_prefix_partner` | `name`, `prefix_name`, `subfix_name`, `prefix_type` | `res.partner.title` + ฟิลด์คำนำหน้าไทยใน `od19_partner_thai_fields` | 🟡 |
| `dtr_partner_branch` | `partner_id`, `name`, `tax_name`, `vat`, `branch_code`, `street`, `street2`, `city`, `state_id`, `zip`, `country_id` | `res.partner` (child, `type='branch'`) — `branch_code` → `od19_partner_thai_fields.branch_code` | 🟡 |
| `dtr_credit_limit` | `res_partner_id`, `credit_line_no`, `credit_limit`, `credit_remain`, `credit_start_date`, `credit_end_date`, `credit_remark` | `res.partner` credit fields / `od19_accounting_features` (No credit approval → no payment) | 🟡 |
| `dtr_partner_fee` | `name`, `account_id`, `analytic_account_id`, `percent`, `amount`, `is_profit`, `payment_partner_id`, `receipt_partner_id` | ยังไม่มีเทียบเท่า — ดู §4 | ❌ |
| `dtr_product_brand` | `name` | `product.brand` (OCA brand) / ฟิลด์ `od19_misc_features` | 🟡 |
| `dtr_product_brand_model` | `name`, `brand_id` | model ย่อยของ brand | 🟡 |
| `dtr_product_tag` | `name` | `product.tag` (core v19) | ✅ |
| `dtr_parts_history` | `lot_id`, `receive_date`, `product_id`, `company_id`, `is_lock` | ยังไม่มีเทียบเท่า (Product Part History — GAP §9 ข้อ 2) | ❌ |
| `dtr_parts_history_line` | `history_id`, `product_id`, `lot_id`, `receive_date`, `deliver_date`, `origin` | ยังไม่มีเทียบเท่า | ❌ |
| `dtr_bring_forward` | `doc_no`, `name`, `remark`, `date`, `journal_id`, `state`, `company_id`, `move_id` | ยอดยกมา — นำเข้าเป็น Opening JE (§3.8) หรือ develop model | ❌ |
| `dtr_bring_forward_line` | `account_id`, `target_total_debit/credit`, `compute_debit/credit`, `difference_debit/credit`, `is_create_manual` | ยอดยกมาต่อบัญชี | ❌ |
| `dtr_general_template` | `name`, `company_id` | ไม่มีเทียบเท่า — template JE | 🟡 |
| `dtr_general_template_line` | `template_id`, `sequence`, `account_id`, `name`, `debit`, `credit` | ไม่มีเทียบเท่า | 🟡 |
| `dtr_cheque_book` | `state`, `name`, `journal_id`, `first_cheque_no`, `quantity`, `last_cheque_no`, `last_cheque_no_number`, `date` | `od19_accounting_cheque` (`cheque.book`) | ✅ |
| `dtr_cheque_leaf` | `journal_id`, `name`, `date`, `amount`, `state`, `book_id`, `pay_to`, `paid_date`, `clear_date`, `is_internal_transfer` | `od19_accounting_cheque` (`cheque`) | ✅ |
| `dtr_wht` | `name`, `partner_id`, `payee_tax_id`, `branch_code`, `income_type`, `tax_type`, `pay_date`, `tax_rate1..3`, `pay_amount1..3`, `wht_amount1..3`, ที่อยู่แยกส่วน | `od19_accounting_*` (WHT) + `l10n_th_account_tax` | 🟡 |
| `dtr_vat` | `partner_id`, `tax_name`, `tax_code`, `vat_type`, `vat_no`, `vat_date`, `amount`, `amount_nonvat`, `amount_vat`, `amount_total`, `invoice_id`, `is_tax_invoice`, `dncn` | `od19_thai_tax_reports` (VAT register) | 🟡 |
| `dtr_account_prepayment` | `name`, `number`, `partner_id`, `bill_date`, `actual_due_date`, `payment_method_id`, `state` | `od19_accounting_advance` / prepayment | 🟡 |

> ⚠️ **ยังต้องดึงเพิ่มหลัง restore:** คอลัมน์ที่ custom module เติมเข้า **ตารางมาตรฐาน** (`res_partner`, `product_template`, `account_move`, `account_move_line`, `stock_move`, `hr_employee`, `project_project`) — คำสั่งตัวอย่าง:
> `SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_name IN ('res_partner','product_template','account_move') ORDER BY table_name, ordinal_position;`

---

## 5. ทะเบียน CSV mapping (`migration/mapping/`)

| ไฟล์ | คอลัมน์ | ใช้ในขั้น | สถานะ |
|---|---|---|---|
| `account_map.csv` | `od15_code, od19_code, note` | s01, s08 | template (EXAMPLE) |
| `tax_map.csv` | `od15_tax_name, od19_tax_name, rate_note` | s01, s02 | template (EXAMPLE) |
| `journal_map.csv` | `od15_journal_code, od19_journal_code, note` | s02 | template (EXAMPLE) |
| `payment_term_map.csv` | `od15_term_name, od19_term_name, note` | s02, s03 | template (EXAMPLE) |
| `uom_map.csv` | `od15_uom, od19_uom, note` | s02, s04 | template (EXAMPLE) |
| `partner_category_map.csv` | `od15_category, od19_tag, note` | s03 | template (EXAMPLE) |
| `product_category_map.csv` | `od15_category, od19_category, note` | s02, s04 | template (EXAMPLE) |
| `sequence_map.csv` | `doc_type, od15_last_number, od19_sequence_code, note` | s09 | template (EXAMPLE) |

> รูปแบบ: แถวข้อมูลจริงต้อง **ไม่ขึ้นต้นด้วย `EXAMPLE`** (เพราะ `common.load_map()` จะข้ามแถวดังกล่าว)

---

## 6. Blockers & ความเสี่ยง

| # | ความเสี่ยง | ผลกระทบ | มาตรการ |
|---|---|---|---|
| B1 | ~~ยังไม่มี DB dump ของ OD15~~ | ~~ดึงค่า/ตรวจคอลัมน์จริงไม่ได้~~ | ✅ **ปิด (2026-10-31):** ได้ `od15_autoerp_prd.dump` (10.07 MB, TOC 23,643) ที่ `migration/od15_export/` แล้ว — รอ restore เข้า `od15_stage` |
| B2 | ~~ไม่มีซอร์ส `dtr_*` บนดิสก์~~ | ~~ยืนยันฟิลด์ OD15 ไม่ได้~~ | 🟡 **บางส่วน (2026-10-31):** ได้คอลัมน์ `dtr_*` 192 ตารางแล้ว (`dtr_columns.txt`); **ยังเหลือคอลัมน์ที่ custom module เติมเข้า table มาตรฐาน** — อ่าน `information_schema` จาก `od15_stage` หลัง restore |
| B3 | OCA บางตัวยังไม่มีใน DB (`stock_no_negative`, `account_statement_import*`, `l10n_th_withholding_tax`) | gap บาง Open Item ยังปิดไม่ได้ | ติดตั้ง/เพิ่ม repo ก่อน หรือวางแผน develop |
| B4 | ยอดยกมาไม่ตรง GL | งบการเงินคลาดเคลื่อน | กระทบยอด AR/AP/สต็อก/สินทรัพย์ ก่อนรันจริง |
| B5 | เลขเอกสารชนของเดิม | สืบค้นย้อนหลังไม่ได้ | ตั้ง `number_next_actual` ตาม `sequence_map.csv` |

---

## 7. Definition of Done (ต่อเอนทิตี)

- [ ] ระบุตาราง/คอลัมน์ OD15 จริงจาก `od15_stage` (แทนที่ทุกช่อง *(ตรวจสอบ)*)
- [ ] เติม CSV mapping ด้วยแถวข้อมูลจริง (ลบแถว `EXAMPLE`)
- [ ] เขียน logic ใน step ที่เกี่ยวข้องด้วย `common.upsert()` + External ID
- [ ] รัน `MIG_DRY_RUN=1` ผ่าน → ตรวจ log ว่าไม่มี error
- [ ] รันจริง → ตรวจ `created/updated/skipped` และรันซ้ำ (idempotent, ไม่สร้างซ้ำ)
- [ ] ยอดยกมากระทบยอดกับงบการเงินเดิมตรง
