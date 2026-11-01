# Odoo 19 CE Wave 2: Custom Finance Controls

## Control Metadata
- Child spec ID: W2-FINANCE-CONTROLS
- Wave: Wave 2 (Custom finance controls)
- Status: Implemented — core finance control modules (Advance, Cheque, Money In, WHT, Petty Cash, Fixed Assets, Jasper foundation) are present on disk; Payment Preparation (Payment Voucher/Receipt + PV/RV sequence) built as `od19_accounting_payment_voucher_reports`; WHT Certificate PDF (มาตรา 50 ทวิ) built in `od19_thai_tax_reports` printed from OCA `withholding.tax.cert` (advisory payment-based certs retired 2026-10-23); Year-End Closing decided as manual no-code on core lock dates (no custom module)
- Owner: Finance controls lead
- Reviewer: Technical supervisor
- Approvers: Business owner; Technical supervisor
- Target edition: Odoo 19 Community Edition (CE)
- Canonical path: `docs/superpowers/specs/2026-10-21-odoo19-enterprise-wave-2-custom-finance-controls.md`
- Source backlog row: `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md`
- Date: 2026-10-21
- Primary readers: ฝ่ายบัญชี, ฝ่ายการเงิน, ผู้อนุมัติ (Finance Director), ฝ่ายจัดซื้อ, ทีมเทคนิค

## Approval Traceability
- Scope baseline (Advance, Cheque, Money In Analysis, WHT, Petty Cash, Fiscal Year & Year-End Closing, Fixed Assets, Jasper Reports Foundation) approved in the Wave Control Register on 2026-10-12.
- Scope expanded 2026-10-13 to include Dual Report Format (printable reports), Thai Localization modules, and Payment Preparation (วิธีที่ 3).
- 2026-10-21: ผู้ใช้อนุมัติแนวทางเขียนสเปกตามสภาพจริงบนดิสก์ (ไม่ใช่ forward-looking "Not started") และให้อัปเดตเอกสารกำกับให้สอดคล้องพร้อมกัน
- 2026-10-21: ผู้ใช้สั่งให้เริ่มพัฒนาส่วนที่ยังขาดให้ครบตามแผน หลังจัดทำสเปกครบทั้งสาม wave
- 2026-10-21: ผู้ใช้ตัดสินใจ **Year-End Closing = Manual no-code** บน core lock dates (`fiscalyear_lock_date` / `hard_lock_date` / `tax_lock_date` / `sale_lock_date` + `account.lock_exception`) — ไม่สร้างโมดูล `od19_accounting_year_end_closing`
- 2026-10-21: พัฒนา `od19_accounting_payment_voucher_reports` (Payment Voucher PV / Payment Receipt RV reports + sequence assignment on `account.payment`) เสร็จบนดิสก์ ปิด GAP Payment Preparation (วิธีที่ 3)

## Discovery Evidence
- Current-state references:
  - `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md` (Wave 2 scope and focus)
  - `docs/superpowers/programs/odoo19-enterprise/reporting/kpi-reporting-baseline.md` (Dual Report Format Requirement; Payment Preparation Strategy วิธีที่ 3)
  - `docs/superpowers/specs/2026-10-07-odoo19-enterprise-wave-1-accounting-operational-closure-design.md` (Wave 1 accounting baseline)
  - `Odoo15Backup/` legacy landscape (module names only — the legacy source of the finance addons is not on disk, so discovery relies on the governance documents)
- Verified current state on disk (2026-10-21):
  - `custom_addons/od19_accounting_advance/` — model `account.advance` (customer/supplier), JE posting, states `draft → posted → reconciled / cancel`, sequence `account.advance`, post-install tests
  - `custom_addons/od19_accounting_cheque/` — `account.cheque` + `account.cheque.book`, sequence data, cheque print report, tests; depends `account`, `od19_partner_thai_fields`
  - `custom_addons/od19_accounting_money_in_report/` — snapshot report (`od19.money.in.report.run` / `.line` / `.builder`) with project integration, tests
  - `custom_addons/od19_accounting_features/` — WHT advisory fields on `account.payment` (base/rate/type/amount compute), payer/payee, BOT URL, Billing Note report, AP bill-first gate; depends OCA `l10n_th_account_tax` (WHT Certificate PDFs (PND1/PND3/PND53/PND53 Tris) **retired 2026-10-23**)
  - `custom_addons/od19_thai_tax_reports/` — WHT Register + VAT Sales/Purchase Register reports + WHT Certificate (มาตรา 50 ทวิ) พิมพ์จาก OCA `withholding.tax.cert`; depends OCA `l10n_th_account_tax`
  - `custom_addons/od19_accounting_petty_cash/` — `petty.cash.fund` + `petty.cash.transaction`
  - `custom_addons/od19_accounting_payment_fee/` — payment fee (bank charge) field + journal line generation on `account.payment`
  - `custom_addons/od19_reporting_jasper/` — Jasper/QWeb report foundation (`jasper.report.template`, `jasper.report.action`, generic model-agnostic report), tests
  - `custom_addons/od19_asset_disposal/` — asset disposal workflow on OCA `account_asset_management`
  - `custom_addons/od19_asset_loan/` — tool/equipment loan documents, maintenance integration, loan report, tests
  - `custom_addons/od19_thai_font_support/` — Sarabun font for Web UI + QWeb PDF
  - `custom_addons/od19_thai_localization_base/` — Thai localization base (font default, Buddhist year, company config)
  - `custom_addons/od19_accounting_document_sequence/` — pre-configured Thai document sequences (data-only), รวม sequence `account.voucher.vendor.payment` (`PV%(range_y)s%(range_month)s`) และ `account.voucher.customer.payment` (`RV%(range_y)s%(range_month)s-`)
  - `custom_addons/od19_accounting_payment_voucher_reports/` — **Created 2026-10-21** — `account.payment` extension (`od19_voucher_no` + `action_post()` assigns PV/RV from `ir.sequence`), Payment Voucher (PV) + Payment Receipt (RV) QWeb reports bound to `account.payment` with `payment_type` domain, form view field, post-install tests
  - OCA modules present in `third_party/oca/`: `l10n_th_account_tax` (WHT/VAT), `account_asset_management` (Assets), `account_fiscal_year` (Fiscal year periods), `base_tier_validation` (approval), `currency_rate_update`
  - OCA modules **not** present in `third_party/oca/`: `account_payment_order`
  - **Accounting requirement coverage sync (2026-10-26)**: ตรวจข้อกำหนดจากฝ่ายบัญชีกับแผนและดิสก์จริง แล้วเพิ่ม OCA repo เข้า `third_party/oca/` และ `odoo.conf` `addons_path` ตามนี้ —
    - ✅ `account_financial_report` + `account_tax_balance` (repo `account-financial-reporting`, branch 19.0)
    - ✅ `account_reconcile_oca` (repo `account-reconcile`, branch 19.0) — โมดูลชื่อ `account_reconcile_oca` (ข้อกำหนดฝ่ายบัญชีเขียนว่า `account_reconcile_model_oca`); **เชื่อมกับ core ผ่าน bridge `od19_accounting_reconcile_ui` (created 2026-11-01)** — auto_install, LGPL; `od19_accounting_features` ไม่ hard-depend OCA อีกต่อไป
    - ✅ `auditlog` (repo `server-tools`, มีอยู่แล้ว) + `report_xlsx` (repo `reporting-engine`, มีอยู่แล้ว) — **ยังไม่ถูกอ้างในแผน** จึงบันทึก adopt ที่นี่
    - ✅ `account_move_name_sequence` + `account_lock_date_update` (repo `account-financial-tools`, มีอยู่แล้ว) — พร้อมใช้ ต้องตัดสินใจเทียบกับ custom sequence/lock ที่มี
    - ❌ `account_invoice_supplier_ref_unique` — **ยังไม่มีบน OCA branch 19.0** (repo `account-invoicing` clone แล้วแต่ยังไม่มีโมดูลนี้) → ต้องรอ OCA migrate หรือทำ custom ขนาดเล็ก
- Evidence findings:
  - WHT GL is created by OCA `l10n_th_account_tax` (`_handle_withholding_taxes()`); there is **no custom** `od19_accounting_wht` module on disk — the display/advisory fields live in `od19_accounting_features`.
  - Fiscal year periods are provided by OCA `account_fiscal_year`; there is **no** OCA year-end-closing wizard and **no** custom closing module.
  - Payment Preparation วิธีที่ 3 (payment voucher/receipt QWeb reports + PV sequence on `account.payment`) is now **implemented** as `od19_accounting_payment_voucher_reports` (created 2026-10-21). No `account.payment.voucher` model was introduced (วิธีที่ 3 respected); the voucher number is a stored field on `account.payment` sourced from `od19_accounting_document_sequence`.
  - Year-End Closing: **decided** as manual no-code using core lock dates; no custom closing module is introduced.
- Evidence coverage gaps:
  - Legacy Odoo 15 finance addon source (`dtr_advance`, `dtr_cheque`, `dtr_taxation`, `om_fiscal_year`, `dtr_year_end`, `om_account_asset`) is not on disk — field-by-field migration map cannot yet be produced from source.
  - Odoo 15 printable finance report templates (Jasper) are not on disk for 1:1 layout comparison.
  - Payment Voucher/Receipt QWeb layout has no Odoo 15 Jasper twin on disk for 1:1 comparison (uses finance-form conventions instead).

## Delivery Controls
- Dependencies:
  - Wave 1 accounting operational-closure baseline (AR, AP, payment, reconciliation, posting/tax mapping)
  - Wave 0 governance baseline (Thai font, engineering standards)
  - OCA availability: `l10n_th_account_tax`, `account_asset_management`, `account_fiscal_year`, `base_tier_validation`, `auditlog`, `report_xlsx`, `account_financial_report`, `account_tax_balance`, `account_reconcile_oca`, `account_move_name_sequence`, `account_lock_date_update`
- Gate readiness:
  - Spec-ready: ✅ scope, boundary, dual-report rule, and Payment Preparation (วิธีที่ 3) are defined
  - Plan-ready: ✅ addon boundary for Payment Voucher/Receipt (`od19_accounting_payment_voucher_reports`) fixed; Year-End Closing decided as manual no-code on core lock dates
  - Build-ready: ✅ Payment Voucher/Receipt reports + PV/RV sequence implemented and syntax/XML verified on disk; Year-End Closing approach documented (no-code)
  - Verify-ready: ⏳ post-install tests must be run on `odoo19_pdev` by the user via terminal (Agent Runtime limitation)

---

## 1. สรุปสั้น ๆ

Child spec นี้ออกแบบแกน `Custom Finance Controls` ของ Wave 2 ซึ่งต่อยอดจาก Wave 1 accounting operational-closure baseline ให้ครอบคลุม:

- `Advance` (เงินรับ/จ่ายล่วงหน้า)
- `Cheque` (เช็ครับ–จ่าย และสมุดเช็ค)
- `Money In Analysis` (วิเคราะห์เงินรับเข้า)
- `Withholding Tax (WHT)` (ภาษีหัก ณ ที่จ่าย)
- `Petty Cash` (เงินสดย่อย)
- `Fiscal Year & Year-End Closing` (ปีบัญชีและการปิดบัญชี)
- `Fixed Assets` (สินทรัพย์ถาวร)
- `Jasper Reports Foundation` (ฐานรายงาน Jasper/QWeb)
- `Dual Report Format` (ทุกรายงานพิมพ์ต้องมีทั้ง QWeb และ Jasper)
- `Thai Localization modules` (โมดูลภาษาไทย)
- `Payment Preparation (วิธีที่ 3)` (ใบสำคัญจ่าย/รับ + เลขที่เอกสาร payment)

หัวใจของ Wave นี้คือทำให้ระบบตอบได้ว่า:

- เงินที่รับ/จ่ายล่วงหน้า ถูกใช้และกระทบยอดครบหรือไม่
- เช็คทุกใบมีสถานะและตรวจสอบย้อนหลังได้หรือไม่
- ภาษีหัก ณ ที่จ่ายถูกคำนวณและออกรายงานส่งสรรพากรได้หรือไม่
- สินทรัพย์ถาวรคิดค่าเสื่อมและจำหน่ายออกได้ถูกต้องหรือไม่
- รายงานพิมพ์ทุกรูปแบบมีทั้งเวอร์ชัน Odoo 19 Native และ Odoo 15 Legacy Compatible หรือไม่

โดเมนนี้ต้องเป็นแหล่งความจริงของ `finance control` โดยไม่ดึง logic ของ Sales, Inventory หรือ HR เข้ามาปะปนเกินจำเป็น

## 2. เป้าหมายของ Child Spec นี้

- ปิดช่องว่าง finance control ที่ Wave 1 ยังไม่ครอบคลุม โดยยังยึดหลัก **No core modification** และ **OCA-First**
- ใช้ OCA และ Odoo standard เป็นฐานให้มากที่สุด ลดจำนวนโมดูล custom และลดความซ้ำซ้อน
- ให้ทุก addon ติดตั้ง/ถอนได้โดยไม่กระทบ core
- บังคับใช้ **Dual Report Format** กับทุกรายงานที่พิมพ์ออกมา (เฉพาะ printable reports)
- เตรียมความพร้อมสำหรับการตรวจสอบย้อนหลัง (audit trail) ของรายการทางการเงินทุกประเภท

## 3. ขอบเขตของ Child Spec

### 3.1 อยู่ใน scope (ในก้อนนี้)
- Advance: เงินรับ/จ่ายล่วงหน้า + การตัดใช้ + JE posting
- Cheque: lifecycle เช็ค + สมุดเช็ค + รายงานพิมพ์เช็ค
- Money In Analysis: snapshot report ของเงินรับเข้า
- WHT: GL จาก OCA `l10n_th_account_tax` + ฟิลด์ advisory + WHT Certificate (มาตรา 50 ทวิ จาก `withholding.tax.cert`) + WHT/VAT Register
- Petty Cash: เงินสดย่อย + การเบิกใช้/เติมเงิน
- Fiscal Year: ช่วงปีบัญชีผ่าน OCA `account_fiscal_year`
- Year-End Closing: แนวทางปิดบัญชีปลายปี = **Manual no-code** บน core lock dates (ตัดสินใจแล้ว 2026-10-21) — ไม่สร้างโมดูลอัตโนมัติ
- Fixed Assets: ทะเบียนสินทรัพย์ + ค่าเสื่อม (OCA `account_asset_management`) + การจำหน่ายออก (`od19_asset_disposal`) + การยืมเครื่องมือ (`od19_asset_loan`)
- Jasper Reports Foundation: ฐานการพิมพ์ Jasper/QWeb
- Dual Report Format: ทุกรายงานพิมพ์ต้องมีทั้ง QWeb + Jasper
- Thai Localization modules: `od19_thai_font_support`, `od19_thai_localization_base`
- Payment Preparation (วิธีที่ 3): ใบสำคัญจ่าย/ใบสำคัญรับ (QWeb) + เลขที่เอกสารไทยบน `account.payment`
- Deep credit controls (credit limits, overdue holds, exception approvals) ที่ส่งต่อจาก Wave 1 customer risk gate

### 3.2 ไม่อยู่ใน scope (Out of scope)
- การแก้ไขไฟล์ core ของ Odoo
- การสร้างโมเดล `account.payment.voucher` ใหม่ (ใช้วิธีที่ 3)
- การสร้างโมดูล custom `od19_accounting_wht` หรือ `od19_accounting_fiscal_year` (ใช้ OCA + core แทน)
- การสร้างโมดูล `od19_accounting_year_end_closing` แบบ automation (ตัดสินใจใช้ Manual no-code + core lock dates แทน)
- KPI Dashboard / on-screen reports (ไม่อยู่ในข้อบังคับ Dual Report Format)
- Payroll engine และการคำนวณเงินเดือน (อยู่ Wave 5 / CE ไม่มี payroll)
- การ re-implement รายงานทางการเงินพื้นฐานที่ Odoo standard มีอยู่แล้ว

## 4. Current-State Summary

Wave 2 มีการพัฒนาไปแล้วบางส่วนบนดิสก์ (2026-10-21):

| โดเมน | โมดูล/แหล่ง | สถานะบนดิสก์ |
| --- | --- | --- |
| Advance | `od19_accounting_advance` | Implemented — model + JE posting + sequence + tests |
| Cheque | `od19_accounting_cheque` | Implemented — cheque + cheque book + sequence + report + tests |
| Money In Analysis | `od19_accounting_money_in_report` | Implemented — snapshot report + project integration + tests |
| WHT | OCA `l10n_th_account_tax` (GL) + `od19_accounting_features` (advisory + PND) + `od19_thai_tax_reports` (register) | Implemented |
| Petty Cash | `od19_accounting_petty_cash` | Implemented — fund + transaction |
| Fiscal Year | OCA `account_fiscal_year` | Available (periods) |
| Year-End Closing | Core lock dates (`fiscalyear_lock_date` / `hard_lock_date` / `tax_lock_date` / `sale_lock_date` + `account.lock_exception`) | **Decided: Manual no-code** — ปิดปีผ่าน GL manual entry + core lock dates (ไม่สร้างโมดูล) |
| Fixed Assets | OCA `account_asset_management` + `od19_asset_disposal` + `od19_asset_loan` | Implemented |
| Jasper Reports Foundation | `od19_reporting_jasper` | Foundation implemented (template/action + generic report + tests) |
| Thai font | `od19_thai_font_support` | Implemented |
| Thai localization base | `od19_thai_localization_base` | Implemented |
| Payment Preparation (วิธีที่ 3) | `od19_accounting_payment_voucher_reports` + `od19_accounting_document_sequence` | Implemented — `od19_voucher_no` + PV/RV sequences on `account.payment`; Payment Voucher (PV) + Payment Receipt (RV) QWeb reports; form view; tests |

## 5. Keep / Refactor / Replace / Retire

- Keep
  - OCA `l10n_th_account_tax`, `account_fiscal_year`, `account_asset_management`, `base_tier_validation`
  - OCA ที่พร้อมใช้เพิ่มตามข้อกำหนดฝ่ายบัญชี (2026-10-26): `auditlog` (ISO/Internal-External Audit), `report_xlsx` (ภ.พ.30 / ภ.ง.ด.3 / ภ.ง.ด.53 / ทะเบียนภาษีซื้อ-ขาย Excel), `account_financial_report` (TB/GL/BS/P&L), `account_tax_balance` (กระทบยอด VAT), `account_reconcile_oca` (auto bank reconciliation — เชื่อมผ่าน bridge `od19_accounting_reconcile_ui`), `account_move_name_sequence`, `account_lock_date_update`
  - Odoo standard `account` (`account.payment.register`, PND CSV ผ่าน `l10n_th`)
  - โมดูล custom ที่ผ่านการตรวจสอบแล้ว: `od19_accounting_cheque`, `od19_accounting_money_in_report`, `od19_accounting_features`, `od19_thai_tax_reports`, `od19_asset_disposal`, `od19_asset_loan`, `od19_thai_font_support`, `od19_accounting_document_sequence`
- Refactor
  - `od19_accounting_advance` และ `od19_accounting_petty_cash` — ตรวจสอบให้ workflow, security model และ tests ครบตามมาตรฐาน Lean/Secure
  - `od19_reporting_jasper` — ยกระดับจาก foundation เป็นกลไกคู่ QWeb + Jasper สำหรับรายงานพิมพ์ทุกตัว
- Replace
  - Legacy `dtr_advance`, `dtr_cheque`, `dtr_taxation` → โมดูล Wave 2 ปัจจุบัน + OCA `l10n_th_account_tax`
  - Legacy `om_fiscal_year`, `dtr_year_end` → OCA `account_fiscal_year` (periods) + การปิดบัญชีปลายปีแบบ Manual no-code บน core lock dates
  - Legacy `om_account_asset`, `dtr_fixed_assets` → OCA `account_asset_management` + `od19_asset_disposal`
- Retire
  - โมดูล filter ที่แยกย่อยซ้ำซ้อนจากยุค DTR (`dtr_payment_filter`, `dtr_account_filter`) — ใช้ Odoo standard search/menu แทน
  - รายงานเช็คแยกต่อธนาคาร — ใช้ Cheque Template เดียวที่ตั้งค่าธนาคาร/เลย์เอาต์ได้

## 6. Future-State Design

### 6.1 Advance
`account.advance` (customer/supplier) พร้อม JE posting และการตัดใช้ผ่าน reconciliation กับ `account.move.line` เมื่อตัดครบจะเปลี่ยนเป็น `reconciled`

### 6.2 Cheque
`account.cheque` + `account.cheque.book` ครบ lifecycle (draft → confirmed → deposited → cleared → paid / bounced / cancelled) พร้อมพิมพ์เช็คและรายงานรวมธนาคารแบบ configuration-driven

### 6.3 Money In Analysis
Snapshot report (`od19.money.in.report.run` / `.line`) สร้างจาก builder โดยดึงข้อมูล invoice-based และ cash-invoice-based พร้อมเชื่อม project/analytic

### 6.4 WHT
- GL: OCA `l10n_th_account_tax` สร้าง WHT JE ตอน post/จ่าย (`_handle_withholding_taxes()`)
- Advisory: `od19_accounting_features` แสดง WHT base/rate/type/amount (compute-only, ไม่สร้าง JE ซ้ำ)
- Certificate: หนังสือรับรองการหักภาษี ณ ที่จ่าย (มาตรา 50 ทวิ) พิมพ์จากโมเดล OCA **`withholding.tax.cert`** ใน `od19_thai_tax_reports` — ยอดมาจาก `wht_line` (base/wht_percent/amount) ตรง GL 100%
  - โฟลว์การสร้าง: ตั้ง `wht_cert_income_type` บน `wht_move_ids` ของบิล/payment → กด **"⇒ Create withholding tax cert."** (OCA) → ได้ `withholding.tax.cert` (sequence `WHT/%(year)s/`) → พิมพ์ PDF
- รายงานอื่น: WHT Register/VAT Sales/Purchase Register จาก `od19_thai_tax_reports`
- **Retired (2026-10-23)**: รายงาน WHT Certificate 4 ฟอร์มเดิม (`PND1/PND3/PND53/PND53 Tris`) ที่พิมพ์จาก `account.payment` ด้วยยอด advisory — ลบออกจาก `od19_accounting_features` แล้ว เพราะซ้ำซ้อนและอาจไม่ตรง GL

### 6.5 Petty Cash
`petty.cash.fund` (วงเงิน/ยอดคงเหลือ) + `petty.cash.transaction` (เบิก/เติม) พร้อม JE และการกระทบยอดกับเงินสดในมือ

### 6.6 Fiscal Year & Year-End Closing
- Periods: OCA `account_fiscal_year`
- Period Lock: Odoo 19 core `fiscalyear_lock_date` / `hard_lock_date` / `tax_lock_date` / `sale_lock_date` + `account.lock_exception`
- Year-End Closing: **ตัดสินใจแล้ว — Manual no-code**
  1. ✅ **ทางที่เลือก:** ปิดปีผ่าน GL manual entry (Journal Entries) ตามคำแนะนำฝ่ายบัญชี + ล็อกงวดด้วย core lock dates — ไม่สร้างโมดูล
  2. ❌ ไม่สร้าง `od19_accounting_year_end_closing` (automation) — เก็บเป็น out-of-scope
- เอกสารปฏิบัติ: คู่มือขั้นตอนปิดปี (checklist) อยู่ในขอบเขต training/knowledge ไม่ใช่ development

### 6.7 Fixed Assets
- ทะเบียน + ค่าเสื่อม: OCA `account_asset_management` (FIFO/lot ไม่เกี่ยวข้อง; ค่าเสื่อมตาม schedule)
- จำหน่ายออก: `od19_asset_disposal` (ยกเลิก draft depreciation + สร้าง disposal JE + revert)
- ยืมเครื่องมือ: `od19_asset_loan` (double-borrow guard + calibration tracking + multi-channel notification)

### 6.8 Jasper Reports Foundation + Dual Report Format
- ฐาน: `od19_reporting_jasper` (`jasper.report.template`, `jasper.report.action`, generic report)
- กฎ: รายงานพิมพ์ทุกตัวต้องมีคู่ QWeb (Odoo 19 Native) + Jasper (Odoo 15 Legacy Compatible) ดึงข้อมูลจาก **แหล่งเดียวกัน** และให้ผู้ใช้เลือกฟอร์มได้
- ฟอนต์: QWeb ใช้ Sarabun/Noto Sans Thai (ติดตั้งบน server); Jasper ใช้ฟอนต์เดิม Odoo 15

### 6.9 Thai Localization modules
- `od19_thai_font_support` (Wave 0/ทุก wave) + `od19_thai_localization_base`
- `od19_accounting_reporting` — รายงานทางการเงินที่พิมพ์ออกมา (AR/AP Aging, Trial Balance, P&L, Balance Sheet)
- ใช้ OCA `l10n_th_account_tax` + `l10n_th` เป็นฐาน; **ไม่สร้าง** `od19_accounting_wht`

### 6.10 Payment Preparation (วิธีที่ 3) — **Implemented**
| ส่วน | ใช้/พัฒนา | โมดูล |
| --- | --- | --- |
| ตั้งหนี้ | Odoo standard + **AP bill-first gate** | `account` + `od19_accounting_features` |
| จัดกลุ่มใบแจ้งหนี้ | Odoo standard `account.payment.register` | `account` |
| WHT คำนวณอัตโนมัติ | OCA | `l10n_th_account_tax` |
| Tax Invoice | OCA | `l10n_th_account_tax` |
| PND (PND3/PND53) | Odoo standard `l10n_th` | `l10n_th` |
| ใบสำคัญจ่าย (Payment Voucher) | ✅ **พัฒนาแล้ว (QWeb)** | `od19_accounting_payment_voucher_reports` |
| ใบสำคัญรับเงิน (Payment Receipt) | ✅ **พัฒนาแล้ว (QWeb)** | `od19_accounting_payment_voucher_reports` |
| หนังสือรับรองการหักภาษี ณ ที่จ่าย (WHT Certificate) | ✅ **พัฒนาแล้ว (QWeb, พิมพ์จาก `withholding.tax.cert`)** | `od19_thai_tax_reports` (โมเดลจาก OCA `l10n_th_account_tax`) |
| เลขที่เอกสารไทยบน `account.payment` | ✅ **พัฒนาแล้ว** (`od19_voucher_no` ออกตอน "เตรียมจ่าย" + guard ใน `action_post()` → `ir.sequence`) | `od19_accounting_payment_voucher_reports` ใช้ sequence จาก `od19_accounting_document_sequence` |
| ขั้นเตรียมจ่าย / อนุมัติ (Prepare / Approve) | ✅ **พัฒนาแล้ว (แนวทาง A, 2026-10-23)** — ฟิลด์ + audit fields บน `account.payment` + chatter tracking | `od19_accounting_payment_voucher_reports` |
- Implementation notes:
  - Field `od19_voucher_no` (Char, copy=False, readonly) บน `account.payment`
  - `action_od19_prepare()` (Draft-only) ออกเลขผ่าน `_od19_assign_voucher_number()` — outbound → `account.voucher.vendor.payment` (PV), inbound → `account.voucher.customer.payment` (RV) แล้ว set `od19_prepare_state = 'prepared'` + `od19_prepared_by/date`
  - `action_od19_approve()` ต้องผ่าน `prepared` ก่อน → set `od19_prepare_state = 'approved'` + `od19_approved_by/date`
  - `action_post()` override เรียก `_od19_assign_voucher_number()` เป็น guard (ถ้ามีเลขแล้วจะไม่เปลี่ยน)
  - ทุกฟิลด์ขั้นเตรียมจ่าย/อนุมัติเปิด `tracking=True` → ประวัติตรวจสอบได้ใน chatter ของ `account.payment`
  - รายงานใบสำคัญจ่ายแสดงลายน้ำ "ร่าง / DRAFT" เมื่อยังไม่มีเลขที่; `print_report_name` ใช้ `od19_voucher_no or name`
  - **ตัวเลือกใน Register Payment wizard (2026-10-23)**: checkbox `od19_prepare_payment` ("เตรียมจ่าย (ไม่ Post ทันที)", แสดงเฉพาะฝั่งขายออก/outbound) — override hook `_post_payments()`/`_reconcile_payments()` ของ `account.payment.register` ให้คง payment ไว้สถานะ `draft` และเก็บรายการตั้งหนี้ที่จะตัดจ่ายไว้ที่ `od19_pending_reconcile_line_ids`; เมื่อ `action_post()` จะ replay การ reconcile (คัดลอก domain/reconcile/`matched_payment_ids` จาก core) ให้เสร็จในจังหวะเดียว
  - **บังคับใช้กับเอกสารใหม่เท่านั้น** — ไม่ migration เลข PV/RV ย้อนหลัง
  - `ir.actions.report` 2 ตัว (`report_type=qweb-pdf`) ผูก `binding_model_id = account.model_account_payment` พร้อม `domain` แยก `payment_type`
  - ใช้ `amount_to_text(lang='th_TH')` และฟอนต์ Sarabun/Noto Sans Thai
- **AP bill-first rule (บังคับ, 2026-10-23)**: ฝั่งทำจ่าย (outbound payment) ต้องตั้งหนี้ (Vendor Bill ที่ post แล้ว) ก่อนเข้าสู่ payment — `od19_accounting_features` override `account.payment.action_post()` เพื่อบล็อก standalone vendor payment ที่ไม่ผูก Vendor Bill (ตั้งค่าได้ที่ `res.company.od19_require_vendor_bill_for_payment`, default True) Register Payment wizard bypass ผ่าน context `od19_skip_vendor_bill_check`; expense reimbursement ยกเว้น
- WHT Certificate PDF (2026-10-23): พิมพ์จากโมเดล OCA `withholding.tax.cert` (ไม่ใช่ advisory จาก payment) — `ir.actions.report` ใน `od19_thai_tax_reports` model `withholding.tax.cert`, binding ไปที่ `l10n_th_account_tax.model_withholding_tax_cert`, `print_report_name` = `WHT-Cert-%s` ตามเลขที่ cert
- Optional (ยังไม่ทำ): อนุมัติก่อนชำระแบบหลายชั้น (OCA `base_tier_validation`); จัดกลุ่มหลาย partner ต่อ payment ครั้งเดียว (OCA `account_payment_order` — upgrade path ของแนวทาง A)

## 7. Boundary กับโดเมนอื่น

- กับ Wave 1 Accounting: Wave 2 เป็นการเพิ่ม control depth บน baseline เดิม ไม่ re-open AR/AP/payment core
- กับ Sales (Wave 1): deep credit control ใช้ customer risk gate เดิมเป็นจุดต่อ ไม่แก้ logic ขาย
- กับ HR (Wave 5): HR Expense และ Fleet cost post ผ่าน standard module ไม่ซ้ำกับ petty cash
- กับ Inventory (Wave 4): Fixed Asset ไม่ผูกกับ stock valuation; การปรับมูลค่าสต็อกอยู่ Wave 4

## 8. Reporting และ KPI Needs

- AR/AP Aging, Trial Balance, P&L, Balance Sheet (พิมพ์ออกมา → ต้องมี Dual Format)
- WHT Register + VAT Sales/Purchase Register + WHT Certificate (หนังสือรับรองการหักภาษี ณ ที่จ่าย)
- Cheque register และรายงานเช็ครวมธนาคาร
- Advance balance report (ยอดคงเหลือเงินล่วงหน้าตาม partner)
- Petty cash reconciliation report (ยอดคงเหลือ vs วงเงิน)
- Fixed asset register + depreciation schedule
- ใบสำคัญจ่าย (Payment Voucher) และใบสำคัญรับเงิน (Payment Receipt)
- KPI: overdue exposure, collection trend, exception count (ตาม `kpi-reporting-baseline.md`)

## 9. Security และ Control Model

- ปุ่มอนุมัติ/จำหน่ายสินทรัพย์ และการยืนยันเช็ค จำกัดเฉพาะกลุ่มการเงินที่กำหนด (`account.group_account_manager` / กลุ่ม Wave 2 ที่นิยาม)
- การ post WHT ให้ OCA `l10n_th_account_tax` เป็นผู้สร้าง (Wave 2 ไม่สร้างซ้ำ)
- ใช้ `base_tier_validation` สำหรับอนุมัติก่อนชำระ (ถ้าเปิดใช้)
- เพิ่มการตรวจ Credit Limit Amount และ Outstanding Balance (deep credit control) ต่อจาก customer risk gate
- Period Lock ป้องกันการแก้ไขย้อนหลังผ่าน core lock dates

## 10. Migration Assumptions

- ข้อมูล master data (partner, product, account) อ้างอิง business flow จาก Odoo 15 เท่านั้น ไม่ยกโครงสร้างตารางเดิม
- ยอดเงินล่วงหน้าคงเหลือ, เช็คค้าง และค่าเสื่อมสะสม จากระบบเดิมยกมาเป็นยอดตั้งต้น (opening) ตามข้อตกลงฝ่ายบัญชี
- รูปแบบรายงาน Jasper ของ Odoo 15 ใช้เป็นต้นฉบับอ้างอิงสำหรับ Legacy Compatible layout
- Legacy source addon ไม่ได้อยู่บนดิสก์ — migration map ต้องทำจากเอกสาร governance และการสัมภาษณ์ผู้ใช้

## 11. Training Impact

- บัญชี: การใช้ Advance, Cheque book, Petty cash fund/transaction และการกระทบยอด
- บัญชี: การอ่าน PND/WHT Register และการยืนยัน Tax Invoice
- บัญชี/IT: การปิดปีบัญชีและ Period Lock
- บัญชี: การบันทึกจำหน่าย/ย้ายสินทรัพย์ถาวร
- ผู้ใช้ทั่วไป: วิธีเลือกรูปแบบพิมพ์ QWeb หรือ Jasper

## 12. Test Strategy

- Unit/Integration tests (post-install): Advance posting + reconciliation, Cheque lifecycle, Money In report generation, Petty Cash fund/transaction, Asset disposal/revert, Loan double-borrow guard, Payment Voucher/Receipt rendering, PV sequence
- Report tests: ตรวจว่า QWeb และ Jasper ดึงข้อมูลจากแหล่งเดียวกันให้ผลสอดคล้อง
- Security tests: ตรวจว่าเฉพาะกลุ่มที่กำหนดอนุมัติ/จำหน่ายได้
- การรัน Unit Test ต้องรันโดยผู้ใช้ผ่าน Terminal บนเครื่องโดยตรง (ข้อจำกัด Agent Runtime)

## 13. Known Unknowns

- ~~แนวทาง Year-End Closing: manual (no-code) หรือ automated module~~ → **ปิดแล้ว (2026-10-21): Manual no-code + core lock dates**
- การเปิดใช้ OCA `account_financial_report` (ยังไม่มีใน `third_party/oca`) สำหรับรายงานทางการเงินมาตรฐาน
- ต้นฉบับ Jasper layout ของ Odoo 15 สำหรับรายงานการเงินแต่ละตัว
- ~~ขอบเขต WHT Certificate PDF และการอนุมัติก่อนชำระ (optional) — ยังไม่ทำในรอบนี้~~ → **WHT Certificate PDF ปิดแล้ว (2026-10-23): พิมพ์จาก OCA `withholding.tax.cert` ใน `od19_thai_tax_reports`**; เหลือเฉพาะการอนุมัติก่อนชำระ (optional)

## 14. Definition of Done ระดับสเปก

- โมดูล Wave 2 ทั้งหมดติดตั้งได้บน `odoo19_pdev` โดย log ไม่มี warning จากโมดูลเอง
- ฟังก์ชันที่ปิดช่องว่างครบ: ✅ Payment Voucher + Payment Receipt (QWeb) และเลขที่เอกสาร PV/RV บน `account.payment` (`od19_accounting_payment_voucher_reports`); ✅ WHT Certificate PDF (มาตรา 50 ทวิ) พิมพ์จาก OCA `withholding.tax.cert` (`od19_thai_tax_reports`); ✅ Year-End Closing ตัดสินใจแล้ว (Manual no-code + core lock dates)
- ทุกรายงานพิมพ์ในขอบเขตมีทั้ง QWeb และ Jasper และผ่านการเทียบ layout กับ Odoo 15
- มีชุดทดสอบผ่านตามเกณฑ์ที่กำหนด (รันโดยผู้ใช้)
- ไม่มีการแก้ไขไฟล์ core ของ Odoo

## 15. Gate Readiness Summary

- Spec-ready: ✅
- Plan-ready: ✅ (Payment Voucher addon boundary fixed; Year-End Closing decision signed)
- Build-ready: ✅ (Payment Voucher/Receipt + PV/RV sequence implemented; syntax/XML verified on disk)
- Verify-ready: ⏳ (post-install tests to be run by the user on `odoo19_pdev`)

## 16. คำตัดสินของ Child Spec นี้

ยึดหลัก **OCA-First + Odoo standard เป็นฐาน** สำหรับ finance control ของ Wave 2: WHT ใช้ OCA `l10n_th_account_tax`, Period Lock และ Year-End Closing ใช้ core lock dates (manual no-code), Fiscal Year ใช้ OCA `account_fiscal_year`, Fixed Assets ใช้ OCA `account_asset_management` เติมด้วย `od19_asset_disposal` / `od19_asset_loan` และ Advance/Cheque/Money In/Petty Cash/Reporting/Jasper ใช้โมดูล custom ที่มีอยู่แล้ว ปิดช่องว่าง Payment Preparation ด้วย `od19_accounting_payment_voucher_reports` (ใบสำคัญจ่าย PV / ใบสำคัญรับเงิน RV + เลขที่เอกสาร PV/RV) โดยไม่เพิ่มความซ้ำซ้อนและรักษาความ lean/stable/secure ระยะยาว — ไม่มี GAP ด้าน finance control ค้างใน Wave 2
