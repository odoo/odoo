# ทะเบียนการพอร์ต Jasper Reports : Odoo 15 → Odoo 19

> เอกสารกำกับขอบเขต (scope register) ของงานพอร์ตรายงาน Jasper ทั้งหมด
> จัดทำจาก **หลักฐานการใช้งานจริง** เท่านั้น — ไม่ใช่การเดา

## 1. แหล่งอ้างอิงหลักฐาน (authoritative evidence)

| หลักฐาน | ที่อยู่ | ใช้พิสูจน์ |
|---|---|---|
| ทะเบียนโมดูลที่ติดตั้งจริง | `migration/od15_export/modules.txt` | โมดูลใด "installed" ในฐานข้อมูลต้นทาง `AUTOERP-PRD` |
| ฐานข้อมูลต้นทาง (dump) | `migration/od15_export/od15_autoerp_prd.dump` | สคีมาจริง/ข้อมูลจริง |
| ซอร์ส jrxml ต้นทาง | `c:\odoo-dev\Odoo15Backup\odoo\odoo15_mods_*`, `...\odoo15_mods` | เทมเพลตต้นฉบับที่จะพอร์ต |
| การวิเคราะห์ช่องว่าง | `GAP_ANALYSIS_OD15_to_OD19.md` (ส่วนที่ 2 — DTR) | การตัดสินใจ Keep / Refactor / Replace / Retire ต่อโมดูล |

**เกณฑ์ขอบเขต**: โมดูลต้องมีสถานะ `installed` ใน `modules.txt` **และ** มีไฟล์ `.jrxml` ในซอร์ส

### สรุปผลการคัดกรอง

- โมดูลทั้งหมดในทะเบียน: **170** → `installed` **123** / `uninstalled` 46 / `uninstallable` 1
- โดเมนที่มี Jasper และ installed: **16 โมดูล** (ทั้งหมดเป็นตระกูล `dtr_*`)
- **ตัดออกทั้งกลุ่ม**: ตระกูล `dtr_mrp_report` และ Manufacturing อื่น ๆ (uninstalled), `dtr_project`, `dtr_stock_adjustment`, `dtr_landed_cost`, `dtr_payment_combine_vat_lines` ฯลฯ
- **ตัดออกทั้งกลุ่ม**: `custom15_autoinfo/autoinfo_*_form` (มี `.jrxml` แต่โมดูล **ไม่ installed** ใน `AUTOERP-PRD` — เป็นรุ่นพัฒนาที่ยังไม่ deploy)
- **ตัดออก**: ไฟล์ `*- Copy.jrxml`, `*- original.jrxml`, `*_backup1.jrxml`, `*_old.jrxml` (ไฟล์สำรอง/รุ่นเก่า ไม่ใช่เทมเพลตที่ใช้งาน)

## 2. สถานะรวม

| โดเมน | jrxml ที่ใช้จริง | พอร์ตแล้ว | คงเหลือ | โมดูล OD19 ปลายทาง |
|---|---|---|---|---|
| บัญชี/การเงิน (Accounting) | 46 | 45 | 0 | `od19_reporting_jasper` (เสริม) · 1 Retire (แทนด้วย QWeb) |
| จัดซื้อ (Purchase) | 6 | 6 | 0 | **`od19_purchase_jasper`** (ใหม่) |
| สต็อก (Stock) | 27 | 27 | 0 | **`od19_stock_jasper`** (ใหม่) |
| ขาย (Sales) | 8 | 8 | 0 | `od19_sale_jasper` (เสริม) |
| บริการหลังการขาย (Sales Services) | 7 | 7 | 0 | **`od19_sales_services_jasper`** (ใหม่) |
| **รวม** | **94** | **93** | **0** | 1 Retire (แทนด้วย QWeb) |

## 3. ทะเบียนรายไฟล์

สัญลักษณ์สถานะ: ✅ พอร์ตแล้ว · ⬜ คงเหลือ · ➖ ตัดออก (ไฟล์สำรอง/ซ้ำ)

### 3.1 จัดซื้อ — `dtr_purchase_form` (installed 15.0.1.0) → **`od19_purchase_jasper`** (ใหม่)

| jrxml | รายงาน | OD19 | สถานะ |
|---|---|---|---|
| `purchase_order_report.jrxml` | ใบสั่งซื้อ (Purchase Order Form) F-P-003 | `purchase.order.form` | ✅ |
| `requests_for_quotation_report.jrxml` | ใบขอราคา (RFQ) | `requests.for.quotation.form` | ✅ |
| `po_purchase_request_report.jrxml` | ใบสั่งซื้ออ้างอิงใบขอซื้อ | `po.purchase.request.form` | ✅ |

### 3.2 จัดซื้อ — `dtr_purchase_report` (installed 15.0.1.0) → **`od19_purchase_jasper`**

| jrxml | รายงาน | OD19 | สถานะ |
|---|---|---|---|
| `purchase_order_outstanding_report.jrxml` | รายการใบสั่งซื้อค้างรับ | `purchase.order.outstanding.report` | ✅ |
| `purchase_order_period_report.jrxml` | ใบสั่งซื้อตามช่วงเวลา | `purchase.order.period.report` | ✅ |
| `received_purchase_order_period_report.jrxml` | ใบสั่งซื้อที่รับแล้วตามช่วงเวลา | `received.purchase.order.period.report` | ✅ |

### 3.3 สต็อก — `dtr_stock_form` (installed 15.0.1.0) → **`od19_stock_jasper`** (ใหม่)

| jrxml | รายงาน | สถานะ |
|---|---|---|
| `delivery_report.jrxml` | ใบส่งของ | ✅ |
| `receive_report.jrxml` | ใบรับสินค้า | ✅ |
| `return_report.jrxml` | ใบส่งคืนสินค้า | ✅ |
| `internal_transfer_report.jrxml` | ใบโอนย้ายภายใน | ✅ |
| `goods_issue_picking_report.jrxml` | ใบเบิกสินค้า | ✅ |
| `inventory_adjustment_report.jrxml` | ใบปรับปรุงสินค้า | ➖ |
| `qc_inspection_report.jrxml` | ใบตรวจสอบคุณภาพ | ✅ |
| `product_qrcode_report.jrxml` | ป้าย QR สินค้า | ✅ |
| `product_barcode_report.jrxml` | ป้ายบาร์โค้ดสินค้า | ✅ |
| `product_lot_qrcode_report.jrxml` | ป้าย QR ล็อต | ✅ |
| `product_lot_barcode_report.jrxml` | ป้ายบาร์โค้ดล็อต | ✅ |
| `location_qrcode_report.jrxml` | ป้าย QR ตำแหน่ง | ✅ |
| `location_barcode_report.jrxml` | ป้ายบาร์โค้ดตำแหน่ง | ✅ |
| `delivery_report - Copy.jrxml` | (สำรอง) | ➖ |
| `delivery_report - original.jrxml` | (สำรอง) | ➖ |

### 3.4 สต็อก — `dtr_stock_report` (installed 15.0.1.4) → **`od19_stock_jasper`**

| jrxml | รายงาน | สถานะ |
|---|---|---|
| `stock_card_report.jrxml` | บัตรสินค้า (Stock Card) | ✅ |
| `stock_card_po_report.jrxml` | บัตรสินค้า (มุมมองจัดซื้อ) | ✅ |
| `stock_card_so_report.jrxml` | บัตรสินค้า (มุมมองขาย) | ✅ |
| `stock_card_po_return_report.jrxml` | บัตรสินค้า (คืนผู้ขาย) | ✅ |
| `stock_card_so_return_report.jrxml` | บัตรสินค้า (คืนจากลูกค้า) | ✅ |
| `stock_card_stock_moving_report.jrxml` | บัตรสินค้า (ความเคลื่อนไหว) | ✅ |
| `inventory_move_report.jrxml` | ความเคลื่อนไหวสินค้า | ✅ |
| `inventory_move_special_report.jrxml` | ความเคลื่อนไหวสินค้า (พิเศษ) | ✅ |
| `inventory_move_aging_report.jrxml` | ความเคลื่อนไหวสินค้า (Aging) | ✅ |
| `inventory_valuation_report.jrxml` | มูลค่าสินค้าคงเหลือ | ✅ |
| `inventory_valuation_special_report.jrxml` | มูลค่าสินค้าคงเหลือ (พิเศษ) | ✅ |
| `inventory_valuation_aging_report.jrxml` | มูลค่าสินค้าคงเหลือ (Aging) | ✅ |
| `delivery_order_report.jrxml` | ใบส่งของ (รายงาน) | ✅ |
| `picking_list_report.jrxml` | ใบหยิบสินค้า | ✅ |
| `dead_stock_report.jrxml` | สินค้าไม่เคลื่อนไหว | ✅ |
| `inventory_move_report_backup1.jrxml` | (สำรอง) | ➖ |
| `inventory_valuation_report_backup1.jrxml` | (สำรอง) | ➖ |

### 3.5 บัญชี — `dtr_accounting_form` (installed 15.0.1.0) → `od19_reporting_jasper`

| jrxml | รายงาน | OD19 | สถานะ |
|---|---|---|---|
| `invoice_form.jrxml` | ใบแจ้งหนี้ | `invoice.form` | ✅ |
| `billing_form.jrxml` | ใบวางบิล | `billing.form` | ✅ |
| `credit_note_form.jrxml` | ใบลดหนี้ | `credit.note.form` | ✅ |
| `debit_note_form.jrxml` | ใบเพิ่มหนี้ | `debit.note.form` | ✅ |
| `prepayment_form.jrxml` | ใบรับชำระล่วงหน้า | `prepayment.form` | ✅ |
| `receipt_form.jrxml` | ใบเสร็จรับเงิน | `receipt.form` | ✅ |
| `receipt_cash_form.jrxml` | ใบเสร็จรับเงินสด | `receipt.cash.form` | ✅ |
| `journal_voucher_form.jrxml` | ใบสำคัญจ่าย | `journal.voucher.form` | ✅ |
| `journal_voucher_tax_form.jrxml` | ใบสำคัญจ่าย (ภาษี) | `journal.voucher.tax.form` | ✅ |
| `journal_voucher_wht_form.jrxml` | ใบสำคัญจ่าย (หัก ณ ที่จ่าย) | `journal.voucher.wht.form` | ✅ |
| `thanachart.jrxml` · `tmb.jrxml` · `krungsri.jrxml` · `uob.jrxml` | เทมเพลตเช็คธนาคาร | แทนที่ด้วย QWeb `od19_accounting_cheque.cheque_print` | ➖ |
| `debit_note_form_old.jrxml` | (รุ่นเก่า) | | ➖ |

### 3.6 บัญชี — `dtr_accounting_report` (installed 15.0.1.0) → `od19_reporting_jasper`

| jrxml | รายงาน | OD19 | สถานะ |
|---|---|---|---|
| `general_ledger.jrxml` | สมุดรายวันทั่วไป | `general.ledger.report` | ✅ |
| `trial_balance_report.jrxml` | งบทดลอง | `trial.balance.report` | ✅ |
| `pl_bs.jrxml` | งบกำไรขาดทุน/งบดุล | `pl.bs.report` | ✅ |
| `ar_ap_aging_report.jrxml` | ลูกหนี้/เจ้าหนี้ (Aging) | `ar.ap.aging.report` | ✅ |
| `pl_bs_lvl3.jrxml` | งบการเงิน (ระดับ 3) | `pl.bs.report` (context `pl_bs_lvl3`) | ✅ |
| `pl_bs_lvl4.jrxml` | งบการเงิน (ระดับ 4) | `pl.bs.report` (context `pl_bs_lvl4`) | ✅ |
| `ar_ap_card_report.jrxml` | บัตรลูกหนี้/เจ้าหนี้ | `ar.ap.card.report` | ✅ |
| `payment_inbound_report.jrxml` | ใบรับชำระ | `payment.inbound.report` | ✅ |
| `payment_outbound_report.jrxml` | ใบจ่ายชำระ | `payment.outbound.report` | ✅ |
| `payment_inbound_cheque_report.jrxml` | รับชำระ (เช็ค) | ซับรายงานของ `payment.inbound.report` | ✅ |
| `payment_down_payment_report.jrxml` | ชำระล่วงหน้า | `payment.down.payment.report` | ✅ |
| `payment_down_payment_cheque_report.jrxml` | ชำระล่วงหน้า (เช็ค) | ซับรายงานของ `payment.down.payment.report` | ✅ |
| `receipt_report.jrxml` | รายงานใบเสร็จ | `receipt.report` | ✅ |
| `sub_receipt_cheque.jrxml` | ใบเสร็จ (เช็ค, ซับรายงาน) | ไม่มีตัวอ้างอิงใน OD15 (คัดลอก+คอมไพล์ไว้ให้ครบ) | ➖ |
| `credit_debit_note_report.jrxml` | รายงานใบลดหนี้/เพิ่มหนี้ | `credit.debit.note.report` | ✅ |
| `invoice_condition_report.jrxml` | เงื่อนไขใบแจ้งหนี้ | `invoice.condition.report` | ✅ |
| `invoice_actual_due_date_report.jrxml` | ใบแจ้งหนี้ (วันครบกำหนดจริง) | `invoice.actual.due.date.report` | ✅ |
| `billing_condition_report.jrxml` | เงื่อนไขใบวางบิล | `billing.condition.report` | ✅ |
| `prepayment_condition_report.jrxml` | เงื่อนไขใบรับล่วงหน้า | `prepayment.condition.report` | ✅ |

### 3.7 บัญชี — `dtr_fixed_assets_report` (installed) → `od19_reporting_jasper`

| jrxml | รายงาน | OD19 | สถานะ |
|---|---|---|---|
| `asset_card_form.jrxml` | ทะเบียนทรัพย์สิน (ฟอร์ม) | `asset.card.form` | ✅ |
| `asset_card_report.jrxml` | ทะเบียนทรัพย์สิน | `asset.card.report` | ✅ |
| `asset_card_barcode_report.jrxml` | ทะเบียนทรัพย์สิน (บาร์โค้ด) | `asset.card.barcode.report` | ✅ |
| `asset_card_qrcode_report.jrxml` | ทะเบียนทรัพย์สิน (QR) | `asset.card.qrcode.report` | ✅ |
| `asset_depreciation_report.jrxml` | ค่าเสื่อมราคา | `asset.depreciation.report` | ✅ |
| `asset_depreciation_line_report.jrxml` | ค่าเสื่อมราคา (รายบรรทัด) | `asset.depreciation.line.report` | ✅ |
| `book_value_report.jrxml` | มูลค่าตามบัญชี | `book.value.report` | ✅ |
| `asset_depreciation_report_bk.jrxml` | (สำรอง) | | ➖ |

### 3.8 บัญชี — `dtr_cheque` (installed) · `dtr_petty_cash` (installed) · `dtr_taxation` (installed) · `dtr_advance` (installed) · `dtr_invoicing_report` (installed)

| โมดูลต้นทาง | jrxml | รายงาน | OD19 | สถานะ |
|---|---|---|---|---|
| `dtr_cheque` | `cheque_balance_report.jrxml` | ทะเบียนเช็คคงเหลือ | `cheque.balance.report` | ✅ |
| `dtr_cheque` | `thanachart/tmb/krungsri/uob.jrxml` | เทมเพลตพิมพ์เช็คธนาคาร | QWeb `od19_accounting_cheque.cheque_print` | ➖ |
| `dtr_petty_cash` | `petty_cash_request_report.jrxml` | ใบขอเบิกเงินสดย่อย | `petty.cash.request.report` | ✅ |
| `dtr_petty_cash` | `petty_cash_payment_report.jrxml` | ใบจ่ายเงินสดย่อย | `petty.cash.payment.report` | ✅ |
| `dtr_taxation` | `sales_tax_report.jrxml` | รายงานภาษีขาย | `sales.tax.report` | ✅ |
| `dtr_taxation` | `purchase_tax_report.jrxml` | รายงานภาษีซื้อ | `purchase.tax.report` | ✅ |
| `dtr_advance` | `dtr_adv_request_form.jrxml` | ใบขอเบิกเงินทดรอง | `dtr.adv.request.form` | ✅ |
| `dtr_advance` | `dtr_adv_clear_form.jrxml` | ใบเคลียร์เงินทดรอง | `dtr.adv.clear.form` | ✅ |
| `dtr_advance` | `dtr_adv_request_condition_report.jrxml` | เงื่อนไขใบขอเบิกทดรอง | `dtr.adv.request.condition.report` | ✅ |
| `dtr_advance` | `dtr_adv_request_at_date_report.jrxml` | ใบขอเบิกทดรอง (ตามวันที่) | `dtr.adv.request.at.date.report` | ✅ |
| `dtr_invoicing_report` | `tax_invoice_report.jrxml` | รายงานใบกำกับภาษี | `tax.invoice.report` | ✅ |

### 3.9 ขาย — `dtr_sales_form` (installed) → `od19_sale_jasper`

| jrxml | รายงาน | OD19 | สถานะ |
|---|---|---|---|
| `sale_order_form.jrxml` | ใบสั่งขาย F-S-002 | `sale.order.form` | ✅ |
| `sale_quotation_form.jrxml` | ใบเสนอราคา | `sale.quotation.form` | ✅ |
| `sale_order_proforma_form.jrxml` | ใบแจ้งหนี้ชั่วคราว (Proforma) | `sale.order.proforma.form` | ✅ |
| `warranty_card_form.jrxml` | ใบรับประกัน | `warranty.card.form` | ✅ |

### 3.10 ขาย — `dtr_sales_report` (installed) → `od19_sale_jasper`

| jrxml | รายงาน | OD19 | สถานะ |
|---|---|---|---|
| `sale_order_outstanding_report.jrxml` | ใบสั่งขายค้างส่ง | `sale.order.outstanding.report` | ✅ |
| `sale_order_values_report.jrxml` | มูลค่าใบสั่งขาย | `sale.order.values.report` | ✅ |
| `sale_invoice_values_report.jrxml` | มูลค่าใบแจ้งหนี้ขาย | `sale.invoice.values.report` | ✅ |
| `first_sales_incoming_report.jrxml` | รายรับขายครั้งแรก | `first.sales.incoming.report` | ✅ |

### 3.11 บริการ — `dtr_sales_services_form` · `dtr_sales_services_report` (installed) → **`od19_sales_services_jasper`** (ใหม่)

| jrxml | รายงาน | OD19 | สถานะ |
|---|---|---|---|
| `sales_services_form.jrxml` | ใบสั่งงานบริการ | `sales.services.form` | ✅ |
| `claim_form.jrxml` | ใบเคลม | `claim.form` | ✅ |
| `product_return_form.jrxml` | ใบรับคืนสินค้า | `product.return.form` | ✅ |
| `distribute_order_form.jrxml` | ใบสั่งจ่ายสินค้า | `distribute.order.form` | ✅ |
| `sales_services_report.jrxml` | รายงานงานบริการ | `sales.services.report` | ✅ |
| `claim_report.jrxml` | รายงานเคลม | `claim.report` | ✅ |
| `product_return_report.jrxml` | รายงานรับคืนสินค้า | `product.return.report` | ✅ |

## 4. รูปแบบการพอร์ต (pattern บังคับ)

1. **โครงสร้างโมดูล**: `__init__.py` / `__manifest__.py` / `wizard/` / `security/ir.model.access.csv` / `jrxml/` / `tests/` — ยึดตาม `od19_sale_jasper`
2. **Wizard**: `_name = "<model>.form"`, `_inherit = "od19.jasper.report"`, override `get_parameters()` + `show_report()`
3. **View**: `mode="primary"` + `inherit_id = od19_reporting_jasper.view_jasper_report_wizard` + `xpath //group[@name='parameters'] position="replace"`
4. **Action**: `binding_model_id` ของโมเดลต้นทาง + `binding_type = "report"` + ชื่อ **action** และชื่อ **เมนู** ขึ้นต้นด้วย `(J-Report OD15)`
   - รายงานที่ไม่มี `binding_model_id` (standalone wizard) ให้ชื่อ action และ menuitem ขึ้นต้นด้วย `(J-Report OD15)` เช่นกัน ส่วนเมนูกลุ่ม (folder) ใช้ Suffix `(J-Report OD15)` ได้
5. **jrxml**: คัดลอกเทมเพลตเดิมทั้งไฟล์ **แก้เฉพาะ `queryString`** ให้ตรงสคีมา Odoo 19
6. **การแมปสคีมา Odoo 19**: `product_uom` → `product_uom_id`, `po.notes` → `note`, `res_partner.name_en` คงเดิม
7. **ตัดทิ้งได้**: การอ้างตาราง `company_employee_name` / `company_employee_signature` แบบเก่า → ใช้ `hr_employee` + `hr_version` + `ir_attachment(signature)` ตาม `sale_order_form.jrxml`
8. **ห้ามแก้ Odoo Core**; ฟิลด์ที่เพิ่มต้องขึ้นต้น `od19_`

## 5. หมายเหตุ

- จำนวนนับ "พอร์ตแล้ว" 93 รายการ (45 ใน `od19_reporting_jasper` + 6 ใน `od19_purchase_jasper` + 27 ใน `od19_stock_jasper` + 8 ใน `od19_sale_jasper` + **7 ใน `od19_sales_services_jasper`**) จากทั้งหมด 94 เทมเพลตที่ใช้จริง — **คงเหลือ 0** (อีก 1 รายการถูก Retire: เทมเพลตเช็คธนาคาร 4 ไฟล์ แทนที่ด้วย QWeb)
- **โดเมน Accounting ปิดสมบูรณ์** — `od19_reporting_jasper` v19.0.1.4.0 ติดตั้ง/อัปเดตผ่าน + เทสต์ **0 failed / 0 error (244 tests)** ครอบคลุมกลุ่ม 3.6 (13 รายงาน + 2 ซับรายงาน), 3.7 (7 รายงานสินทรัพย์ถาวร) และ 3.8 (10 รายงาน: เช็คคงเหลือ · เงินสดย่อย 2 · ภาษีขาย/ซื้อ · เงินทดรอง 4 · ใบกำกับภาษี)
- `pl_bs_lvl3` / `pl_bs_lvl4` ไม่สร้างโมเดลใหม่ — ใช้ `pl.bs.report` เดิมร่วมกับ `report_template` (Level 3/4/5) และเพิ่มเมนู `(J-Report OD15) งบการเงิน (ระดับ 3)` seq 88 / `(ระดับ 4)` seq 89
- `sub_receipt_cheque.jrxml` ไม่มีตัวอ้างอิงทั้งใน OD15 และ OD19 (ตรวจ `<subreportExpression>` แล้ว) — คัดลอก+คอมไพล์เก็บไว้ให้ครบเท่านั้น
- `payment_inbound_cheque_report` / `payment_down_payment_cheque_report` เป็น**ซับรายงาน**ของ `payment.inbound.report` / `payment.down.payment.report` (ยืนยันจาก `<subreportExpression>`) จึงไม่สร้าง wizard แยก
- **โดเมน Sales Services ปิดสมบูรณ์** — พอร์ตครบ 7 ไฟล์ (`dtr_sales_services_form` 4 + `dtr_sales_services_report` 3) แบบ **Flat mapping** (1 เอกสาร = 1 สินค้า ตามสคีมา Odoo 19) ติดตั้งโมดูลผ่าน + เทสต์ 0 failed / 0 error (45 tests)
- เทมเพลตเช็คธนาคาร (thanachart/tmb/krungsri/uob) นับเป็น 1 งาน (รวมเข้าโมดูล cheque) จึงไม่นับซ้ำในยอดรวมโดเมนบัญชี — **Retire**: แทนที่ด้วย QWeb report `od19_accounting_cheque.cheque_print` (binding `account.cheque`)
- รายงาน Stock Card มี 6 มุมมอง แยกเป็นไฟล์ ต้องคงป้ายกำกับให้ผู้ใช้แยกออก — **พอร์ตครบทั้ง 6 มุมมองแล้ว** (เมนู `Stock Reports (J-Report OD15)` seq 70–190)
- **โดเมน Stock ปิดสมบูรณ์** — ไฟล์จริงในซอร์ส: `dtr_stock_form` 13 + `dtr_stock_report` 15 = 28 (ไม่รวมไฟล์สำรอง 4 ไฟล์) → พอร์ต ✅ 27 / ตัดออก ➖ 1 / คงเหลือ 0 (verify 41/41 tests ผ่าน)
- `inventory_adjustment_report.jrxml` **ตัดออก (➖)**: OD15 คอมเมนต์ไว้ทั้งใน `__manifest__.py` และ `reports/__init__.py` (ไม่ได้ deploy) และ query อ้างตาราง `stock_inventory` / `stock_inventory_line` / `stock_inventory_stock_location_rel` ที่ถูกลบตั้งแต่ Odoo 17
- ⚠️ ปรับยอด Stock ในตารางสรุปจาก **30 → 27**: ยอดเดิมนับเกิน 2 (ไฟล์จริงมี 28) และหักตัวที่ตัดออก 1 → ใช้จริง 27/พอร์ต 27/คงเหลือ 0; ยอดรวมทั้งโครงการจึงปรับจาก 97/38/59 → **94/46/48**
- อัปเดตทะเบียนนี้ทุกครั้งที่จบโดเมน
