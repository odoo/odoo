# Accounting Requirements Coverage — ตารางเทียบข้อกำหนดฝ่ายบัญชี

## Document Control

| Field | Value |
| --- | --- |
| Artifact | Accounting department requirement coverage matrix |
| Program | Odoo 19 CE Program |
| สร้างเมื่อ | 2026-10-26 |
| ปรับปรุงล่าสุด | 2026-10-27 (OCA Wave 2A ติดตั้งสำเร็จ 12 โมดูล · Wave 2B ปิดช่อง VAT สำเร็จ) |
| ตรวจจาก | แผนจริง (`domain-wave-matrix.md`, `2026-10-21-odoo19-enterprise-wave-2-custom-finance-controls.md`) + สภาพดิสก์จริง (`third_party/oca/`, `custom_addons/`, `odoo.conf`) |
| ผู้จัดทำ | ทีมเทคนิค |
| ผู้รับ | ฝ่ายบัญชี / Audit |

สัญลักษณ์: ✅ ครอบคลุมแล้ว · 🟡 ครอบคลุมบางส่วน หรือแนวทางต่างแต่ได้ผลเทียบเท่า · 🔵 มีพร้อมใช้แต่ยังไม่ถูกอ้างในแผน · 🔴 ยังไม่ครอบคลุม

## 1. สรุปผู้บริหาร

- ข้อกำหนดฝ่ายบัญชีทั้งหมด 16 รายการ → **ครอบคลุมแล้ว 14**, **ครอบคลุมบางส่วน/แนวทางต่าง 2**, **มีพร้อมใช้แต่ยังไม่เข้าแผน 0**, **ยังไม่ครอบคลุม 0** (นับหลังปิดการตัดสินใจวันที่ 2026-10-26)
- ในวันที่ 2026-10-26 ทีมเทคนิคได้ **เพิ่ม OCA repo ที่ขาด 3 repo** (account-invoicing, account-financial-reporting, account-reconcile) เข้า `third_party/oca/` และต่อ `addons_path` ใน `odoo.conf` แล้ว
- **ช่องว่างเดิม 1 รายการถูกปิดแล้ว**: `account_invoice_supplier_ref_unique` ยังไม่มีบน OCA branch 19.0 → ปิดด้วย custom unique index ในโมดูล `od19_accounting_features` (Feature 6)
- **การตัดสินใจ 4 เรื่อง ปิดครบแล้ว** — สรุปอยู่ในข้อ 4
- ไม่มีข้อกำหนดใดที่ยังไม่ครอบคลุม (🔴 = 0)

## 2. ตาราง Coverage Matrix

### 2.1 ข้อมูลพื้นฐานประเทศไทย

| รายการที่ขอ | โมดูลที่เกี่ยวข้อง | สถานะ | หมายเหตุ |
| --- | --- | --- | --- |
| จังหวัด / อำเภอ / รหัสไปรษณีย์ | core Odoo + `od19_partner_thai_fields` | ✅ | จังหวัดใช้ `state_id` มาตรฐาน, รหัสไปรษณีย์ใช้ `zip`; **อำเภอ/ตำบล เพิ่มแล้ว** เป็น `od19_amphoe` (อำเภอ/เขต) และ `od19_subdistrict` (ตำบล/แขวง) พร้อม sync ไป `res.company` (2026-10-26) |
| เลขประจำตัวผู้เสียภาษี 13 หลัก | core `l10n_th` (ฟิลด์ `vat`) | ✅ | มาตรฐาน Odoo + validation |
| สาขา (สำนักงานใหญ่/สาขา) | core `l10n_th` + `od19_partner_thai_fields` (`branch_code` 5 หลัก) | ✅ | HQ = `00000` |

### 2.2 Localization ไทย

| รายการที่ขอ | โมดูลที่เกี่ยวข้อง | สถานะ | หมายเหตุ |
| --- | --- | --- | --- |
| `l10n_th_base` / `l10n_th_partner` / `l10n_th_account` | core `l10n_th` | 🟡 | Odoo 19 รวม 3 โมดูลเดิมเป็น core `l10n_th` เดียว (ชื่อเดิมไม่มีแล้ว) — ผังบัญชีไทย, ภาษีไทย, รายงานภาษีพื้นฐานครบ |
| `l10n_th_withholding_tax` (WHT 3% / 5% / 1% / 0.75%) | OCA `l10n_th_account_tax` | ✅ | 19.0 ใช้ชื่อ `l10n_th_account_tax`; คำนวณ WHT อัตโนมัติ, หักตอนจ่าย, ออกรายงาน; หนังสือรับรอง 50 ทวิ พิมพ์จาก `withholding.tax.cert` (custom `od19_thai_tax_reports`) |

### 2.3 ภาษีซื้อ-ภาษีขาย

| รายการที่ขอ | โมดูลที่เกี่ยวข้อง | สถานะ | หมายเหตุ |
| --- | --- | --- | --- |
| `account_move_name_sequence` | OCA `account-financial-tools` | ✅ | **adopt เข้าแผน (2026-10-26)** — ติดตั้งและโหลดเป็น dependency ของ `od19_accounting_features` แล้ว; โครงการคง custom `od19_document_sequence` / `od19_accounting_document_sequence` (เลขไทย INV/PO/SO/PV ตามปี) ไว้ใช้กับเอกสารไทย |
| `account_fiscal_year` | OCA `account-financial-tools` | ✅ | จัดการปีบัญชี (periods) ตามที่ขอ |
| `account_lock_date_update` | OCA `account-financial-tools` | ✅ | **adopt เข้าแผน (2026-10-26)** — ติดตั้งเป็น dependency ของ `od19_accounting_features` แล้ว; ใช้ร่วมกับ `account.lock_exception` (manual no-code) |

### 2.4 ภาษีหัก ณ ที่จ่าย

ดูข้อ 2.2 (`l10n_th_account_tax`) — ครอบคลุม ✅

### 2.5 งานเจ้าหนี้ (AP)

| รายการที่ขอ | โมดูลที่เกี่ยวข้อง | สถานะ | หมายเหตุ |
| --- | --- | --- | --- |
| `account_payment_order` (Payment Batch / Proposal) | — | 🟡 | **ไม่ adopt โดยเจตนา (ตัดสินใจ 2026-10-26)**: ยังไม่มีบน OCA branch 19.0 (ตรวจ `OCA/account-payment` แล้วมี 8 โมดูล ไม่มีตัวนี้) และจะซ้ำซ้อนกับแนวทาง "Prepare Payment วิธีที่ 3" — ใช้ `account.payment` + `account.payment.register` มาตรฐานแทน; **revisit** เมื่อเกิดความต้องการ "ใบสั่งจ่ายเป็นชุด/หลายคู่ค้าในเอกสารเดียว" จริง |
| `account_invoice_supplier_ref_unique` (กันเลข invoice ผู้ขายซ้ำ) | OCA `account-invoicing` (ไม่มีบน 19.0) → ปิดด้วย custom | ✅ | **ปิดช่องว่างแล้ว (2026-10-26)** ด้วย custom partial unique index ใน `od19_accounting_features` (Feature 6): `UNIQUE (company_id, commercial_partner_id, ref)` เฉพาะ `move_type IN ('in_invoice','in_refund')` และเมื่อ `ref` ไม่ว่าง — ค้นหาไว้รอสลับเป็น OCA เมื่อ migrate 19.0 แล้ว |

### 2.6 สินทรัพย์ถาวร

| รายการที่ขอ | โมดูลที่เกี่ยวข้อง | สถานะ | หมายเหตุ |
| --- | --- | --- | --- |
| `account_asset_management` | OCA `account-financial-tools` | ✅ | Asset Group / Depreciation / Disposal / Partial Disposal / Revalue; เสริมด้วย custom `od19_asset_disposal` และ `od19_asset_loan` |

### 2.7 รายงานภาษี

| รายการที่ขอ | โมดูลที่เกี่ยวข้อง | สถานะ | หมายเหตุ |
| --- | --- | --- | --- |
| `account_tax_balance` (VAT ซื้อ/ขาย, Tax Reconciliation) | OCA `account-financial-reporting` | ✅ | clone repo + ต่อ addons_path (2026-10-26) + **ติดตั้งแล้ว 2026-10-27** (Wave 2A) |
| `account_financial_report` (TB / GL / BS / P&L / Cash Flow) | OCA `account-financial-reporting` | ✅ | clone repo + ต่อ addons_path (2026-10-26) + **ติดตั้งแล้ว 2026-10-27** (Wave 2A); ควบคู่กับ custom `od19_accounting_reporting` (QWeb) |

### 2.8 Audit Trail

| รายการที่ขอ | โมดูลที่เกี่ยวข้อง | สถานะ | หมายเหตุ |
| --- | --- | --- | --- |
| `auditlog` (ใครแก้อะไร เมื่อไร ค่าเดิม/ใหม่) | OCA `server-tools` | ✅ | มีบนดิสก์อยู่แล้ว; **adopt เข้าแผน 2026-10-26** (รองรับ ISO 9001 / Internal / External Audit); **ติดตั้งแล้ว 2026-10-27** (Wave 2A) |

### 2.9 เอกสารภาษีไทย (Excel export)

| รายการที่ขอ | โมดูลที่เกี่ยวข้อง | สถานะ | หมายเหตุ |
| --- | --- | --- | --- |
| `report_xlsx` (ภ.พ.30 / ภ.ง.ด.3 / ภ.ง.ด.53 / ทะเบียนภาษีซื้อ-ขาย) | OCA `reporting-engine` | ✅ | มีบนดิสก์อยู่แล้ว; **adopt เข้าแผน 2026-10-26** เพื่อ export Excel |

### 2.10 กระทบยอดบัญชี (Bank Reconciliation)

| รายการที่ขอ | โมดูลที่เกี่ยวข้อง | สถานะ | หมายเหตุ |
| --- | --- | --- | --- |
| `account_reconcile_model_oca` | OCA `account-reconcile` | ✅ | clone repo + ต่อ addons_path (2026-10-26) + **ติดตั้งแล้ว 2026-10-27** (Wave 2A); ชื่อโมดูลจริงบน 19.0 คือ **`account_reconcile_oca`** (พร้อม `account_statement_base` dependency) — **เชื่อมกับ core ผ่าน bridge `od19_accounting_reconcile_ui`** (ดู §3.3) แทนการผูก hard dependency |

## 3. สิ่งที่ดำเนินการแล้ว (2026-10-26)

1. เพิ่ม git submodule 3 repo (branch 19.0) เข้า `third_party/oca/`:
   - `account-invoicing` (สำหรับ `account_invoice_supplier_ref_unique` — โมดูลยังไม่ถูก migrate)
   - `account-financial-reporting` (`account_tax_balance`, `account_financial_report`)
   - `account-reconcile` (`account_reconcile_oca`)
2. ต่อ `addons_path` ใน `odoo.conf` ให้ครบทั้ง 3 repo
3. อัปเดตเอกสารแผน: `domain-wave-matrix.md` (เพิ่มภาคผนวก Accounting Requirements Coverage) และ `2026-10-21-odoo19-enterprise-wave-2-custom-finance-controls.md` (ปรับรายการ OCA availability + Keep)
4. **adopt OCA (ตัดสินใจ #2)**: ติดตั้ง `account_move_name_sequence` และ `account_lock_date_update` เป็น dependency ของ `od19_accounting_features` (เลขรันเอกสารจาก sequence ตามปี ไม่มีช่องว่าง + wizard ตั้งวันล็อกบัญชีสำหรับผู้สอบบัญชี)
5. **เพิ่มฟิลด์อำเภอ/ตำบล (ตัดสินใจ #4)**: โมดูล `od19_partner_thai_fields` เพิ่ม `od19_amphoe` / `od19_subdistrict` บน `res.partner` พร้อม sync ไป `res.company` (ใช้ทั้งหน้าจอและเอกสารพิมพ์)
6. **ปิดช่องว่างเลขใบกำกับซื้อซ้ำ (ตัดสินใจ #3)**: เพิ่ม unique index `account_move_od19_supplier_ref_uniq` ใน `od19_accounting_features` v19.0.1.5.0 + unit tests 6 เคส (ซ้ำคู่ค้าเดิม/สาขาเดียวกัน บล็อก · ต่างคู่ค้า/เลขว่าง ซ้ำได้)

## 3.1 OCA Wave 2A — ติดตั้งสำเร็จ (2026-10-27)

ติดตั้ง OCA ที่โคลนไว้แล้วแต่ยังไม่ติดตั้ง (Quick Win, ไม่ต้องเขียนโค้ด) — 12 โมดูล state = `installed` บน `odoo19_pdev` (ตรวจด้วย psql) และ Odoo โหลดผ่านทุกโมดูลใน `odoo_server.log` (`account_billing (265/274)` → `account_check_deposit (266/274)` → `account_reconcile_oca (274/274)`):

| โมดูล | Repo | ปิดช่องว่าง |
| --- | --- | --- |
| `account_financial_report` (+`date_range`) | account-financial-reporting | TB / GL / BS / P&L / Cash Flow |
| `account_tax_balance` | account-financial-reporting | กระทบยอด VAT |
| `partner_statement` | account-financial-reporting | AR/AP statement |
| `account_reconcile_oca` (+`account_statement_base`) | account-reconcile | กระทบยอดธนาคาร |
| `auditlog` | server-tools | Audit Trail (ISO 9001) |
| `account_move_tier_validation` (+`base_tier_validation_formula`) | tier-validation | อนุมัติหลายชั้นบัญชี |
| `account_check_deposit` | account-financial-tools | เช็ครับ (นำฝากธนาคาร) |
| `account_billing` | account-invoicing | จัดกลุ่มใบแจ้งหนี้ก่อนจ่าย |
| `account_journal_lock_date` | account-financial-tools | ล็อกงวดระดับสมุดรายวัน |

หมายเหตุ: `account_billing` ไม่มีไฟล์แปลไทย (`no translation for language th_TH`) — ไม่ใช่ปัญหา; เอกสารนี้ครอบคลุมเฉพาะข้อกำหนดฝ่ายบัญชี ส่วนช่องว่างเชิงข้อบังคับกฎหมายไทย (ม.82/5, ภ.พ.36, ภ.ง.ด.50/51, TAS 12, e-Tax, ส.บช.3 ฯลฯ) ดู `thai-accounting-compliance-gap.md`

## 3.2 Custom Wave 2B — ปิดช่อง VAT ตามกฎหมายไทย (2026-10-27)

ปิดช่องว่างภาษีมูลค่าเพิ่มที่สรรพากรบังคับ ด้วยโมดูล custom `od19_thai_tax_reports` v19.0.1.5.0 (unit tests 39 รายการ ผ่านทั้งหมด บน `odoo19_pdev`):

| ข้อบังคับ | สิ่งที่ทำ | ไฟล์/กลไก |
| --- | --- | --- |
| ม.82/5 ภาษีซื้อต้องห้าม | ฟิลด์ `od19_vat_deductible` บน `account.move.line` + ภาษี "ภาษีซื้อต้องห้าม" + แยกยอดในทะเบียนภาษีซื้อ | `models/account_move_line.py`, `data/od19_vat_non_deductible_data.xml`, `report/vat_purchase_register.*` |
| ม.83/6 Reverse charge ภ.พ.36 | ภาษี reverse charge (self-assess ภาษีขาย + ภาษีซื้อ) + รายงาน ภ.พ.36 | `models/account_tax.py`, `data/od19_reverse_charge_data.xml`, `report/pp36_register.*` |
| ม.86/4 ใบกำกับภาษีเต็มรูป | validate 8 รายการก่อน post เฉพาะเมื่อผู้ซื้อมีเลขภาษี (เปิด/ปิดผ่าน `res.company.od19_enforce_86_4_validation`) | `models/account_move.py`, `models/res_company.py`, `models/res_config_settings.py` |
| ม.86/6 ใบกำกับภาษีอย่างย่อ | รายงาน Abbreviated Tax Invoice สำหรับขายปลีก | `report/tax_invoice_forms.xml` |
| ม.86/9-10 ใบเพิ่มหนี้/ใบลดหนี้ | ฟิลด์ `od19_tax_invoice_doc_type` + block อ้างอิงใบกำกับเดิม/เหตุผล บนรายงานใบกำกับภาษี | `models/account_move.py`, `report/tax_invoice_forms.xml` |

## 3.3 Bridge `od19_accounting_reconcile_ui` — ถอด hard dependency ออกจาก core (2026-11-01)

หลัง Wave 2A พบว่า `od19_accounting_features` ผูก `account_reconcile_oca` เป็น hard dependency โดยตรง ทำให้ core (LGPL) ถูกล็อกกับ addon ภายนอก AGPL และขนย้าย/ใช้บน Enterprise ไม่ได้ ตัดสินใจแยกด้วย **bridge module**:

| ประเด็น | รายละเอียด |
| --- | --- |
| โมดูล | `od19_accounting_reconcile_ui` (v19.0.1.0.0, LGPL-3) |
| หน้าที่ | ไม่มี business logic — ทำหน้าที่เชื่อม `od19_accounting_features` ↔ `account_reconcile_oca` เท่านั้น |
| depends | `od19_accounting_features`, `account_reconcile_oca` |
| `auto_install` | `True` — ติดตั้งอัตโนมัติเมื่อทั้งสองฝั่งมีอยู่แล้ว (CE deployment ได้ OCA UI ตามปกติ) |
| ผลต่อ core | `od19_accounting_features` **ไม่ hard-depend** `account_reconcile_oca` อีกต่อไป — ฟีเจอร์ period-clearing/helper ใน core ทำงานได้เองโดยไม่ต้องมี OCA |
| สิ่งที่ OCA UI เสริม | หน้าจอจับคู่ manual (เมนู `Accounting ▸ Accounting ▸ Reconcile`) + contextual action "Reconcile" บนบัญชี/คู่ค้า |

> หมายเหตุ: DB ที่สร้างใหม่ด้วย `-i od19_accounting_features` เพียงอย่างเดียวจะ **ไม่** ดึง OCA UI เข้ามา ต้องติดตั้ง bridge (ซึ่งดึง dependency ทั้งคู่) หรือรัน `STEP-2-Install-Odoo19.ps1 -All`

## 4. บันทึกการตัดสินใจ (ปิดครบ 2026-10-26)

| # | เรื่อง | ผลการตัดสินใจ | ผลกระทบ |
| --- | --- | --- | --- |
| 1 | `account_payment_order` | **ไม่ adopt** — คงแนวทาง Prepare Payment บน `account.payment` เดิม; บันทึกเป็น "รอ OCA 19.0 / revisit เมื่อต้องการใบสั่งจ่ายเป็นชุด" | ไม่มี dependency ใหม่, flow การจ่ายคงเดิม |
| 2 | Sequence / Lock Date | **ใช้ OCA** — `account_move_name_sequence` + `account_lock_date_update` เป็น dependency ของ `od19_accounting_features` | อัปเดตโมดูล `od19_accounting_features` |
| 3 | `account_invoice_supplier_ref_unique` | **ทำ custom ขนาดเล็กในนามโครงการ** — partial unique index บน `ref` ต่อ (company, commercial partner) | ติดตั้ง/อัปเดต `od19_accounting_features` v19.0.1.5.0 |
| 4 | ฟิลด์อำเภอ/ตำบล | **ต้องการ** — เพิ่ม `od19_amphoe` / `od19_subdistrict` | ติดตั้ง/อัปเดต `od19_partner_thai_fields` v19.0.1.1.0 |

## 5. ภาคผนวก — ชื่อโมดูล OCA จริงบน branch 19.0

| ชื่อที่ฝ่ายบัญชีเขียน | ชื่อโมดูลจริงบน 19.0 | Repo |
| --- | --- | --- |
| `l10n_th_withholding_tax` | `l10n_th_account_tax` | OCA `l10n-thailand` |
| `account_reconcile_model_oca` | `account_reconcile_oca` | OCA `account-reconcile` |
| — (bridge ของโครงการ) | `od19_accounting_reconcile_ui` | custom `od19_*` (เชื่อม core ↔ OCA reconcile UI) |
| `l10n_th_base` / `l10n_th_partner` / `l10n_th_account` | core `l10n_th` (รวมเป็นโมดูลเดียว) | Odoo core `addons/` |
