# Thai Accounting Compliance Gap — ตารางเทียบข้อบังคับบัญชี/ภาษีไทย

## Document Control

| Field | Value |
| --- | --- |
| Artifact | Thai accounting & tax regulatory compliance gap analysis |
| Program | Odoo 19 CE Program |
| สร้างเมื่อ | 2026-10-27 |
| ปรับปรุงล่าสุด | 2026-10-29 (Wave 3 ปิดสมบูรณ์ · Wave 4: ปิด ส.บช.3 ยื่นงบ DBD, ภ.ธ.40 SBT และทะเบียนอากรแสตมป์แล้ว · เพิ่มทะเบียน ภ.ง.ด.3/53 fallback สำหรับ CE) |
| ตรวจจาก | สภาพจริงบนดิสก์ (`custom_addons/`, `third_party/oca/`, core `addons/l10n_th`), สถานะโมดูลใน DB `odoo19_pdev`, `odoo.conf`, และงานวิจัยกฎหมายไทย (ยืนยันซ้ำด้วยการค้นเว็บ) |
| มุมมอง | **ข้อบังคับ/กฎหมาย** (ต่างจาก `accounting-requirements-coverage.md` ที่เป็นมุม "requirement checklist ของฝ่ายบัญชี") |
| ผู้จัดทำ | ทีมเทคนิค |
| ผู้รับ | ฝ่ายบัญชี / Audit / เจ้าของธุรกิจ |

สัญลักษณ์: ✅ ครอบคลุมแล้ว · 🟡 ครอบคลุมบางส่วน หรือแนวทางต่างแต่ได้ผลเทียบเท่า · 🔴 ยังไม่ครอบคลุม

## 1. สรุปผู้บริหาร

- ระบบบัญชี Odoo 19 ปัจจุบันมี **ฐาน Thai localization ที่แข็งแรง**: core `l10n_th` มีรายงาน ภ.พ.30 / ภ.ง.ด.3 / ภ.ง.ด.53 ในตัว และ OCA `l10n_th_account_tax` จัดการ VAT + WHT + หนังสือรับรอง 50 ทวิ
- เมื่อเทียบกับ **ข้อบังคับ/กฎหมายไทย** พบช่องว่างที่ยังไม่มี (🔴) เหลือ 4 กลุ่ม หลังปิดหมวด VAT ครบใน Wave 2B แล้ว:
  1. **ภาษีเงินได้นิติบุคคล ภ.ง.ด.50 / ภ.ง.ด.51**
  2. **ภาษีเงินได้รอตัดบัญชี TAS 12**
  3. **การยื่นงบการเงิน DBD (ส.บช.3) / retention 5 ปี**
  4. **ภาษีอื่น: ภ.ธ.40 (SBT) และอากรแสตมป์ / e-Stamp**
- พร้อมกันนั้น **Wave 2A ติดตั้งสำเร็จแล้ว (2026-10-27)** — OCA 12 โมดูล state = `installed` บน `odoo19_pdev` แล้ว ซึ่งปิดช่องว่างด้านรายงานการเงิน/การควบคุมภายในได้ทันที — ได้แก่ `account_financial_report`, `account_tax_balance`, `partner_statement`, `account_reconcile_oca` (+`account_statement_base`), `auditlog`, `account_move_tier_validation` (+`base_tier_validation_formula`), `account_check_deposit`, `account_billing`, `account_journal_lock_date`, `date_range`
- **Wave 2B ปิดช่อง VAT ครบแล้ว (2026-10-27)** — custom module `od19_thai_tax_reports` v19.0.1.5.0 ครอบคลุม ม.82/5 ภาษีซื้อต้องห้าม, ม.83/6 Reverse charge ภ.พ.36, ม.86/4 validate 8 รายการ, ม.86/6 ใบกำกับภาษีอย่างย่อ และ ม.86/9-10 ใบเพิ่มหนี้/ใบลดหนี้ (unit tests ของโมดูลผ่าน 39 รายการ, 0 failed)
- **Wave 2C audit + ปิดงานเกือบครบ (2026-10-27 → 2026-10-28)** — ตรวจโมดูล `od19_etax_invoice` แบบ read-only 21 ไฟล์ พบว่า **XML ขมธอ.3-2560 + XSD ETDA + XAdES-BES ทำเสร็จแล้วและได้มาตรฐาน** หลังจากนั้นปิด Phase 0–4 ครบ (**PDF/A-3 ผ่าน veraPDF 1.30.3 flavour 3b**, **ช่องทางยื่น RD** แบบ mock + batch export, **ภ.ง.ด.54**, และ **e-Withholding Tax** แบบ mock-first ใน `od19_thai_tax_reports`) เหลือเพียงการเชื่อมต่อจริงกับธนาคาร (Bank API spec) สำหรับโหมด `live` (ดูรายละเอียดในข้อ 4 Wave 2C)
- **สถานะปัจจุบัน**: Wave 2A ✅ Wave 2B ✅ Wave 2C Phase 0–4 ✅ **Wave 3 ✅ ปิดสมบูรณ์ (2026-10-29)** — ภ.ง.ด.50/51, TAS 12 Deferred Tax และ TFRS for NPAEs · **Wave 4 ✅ ปิดครบ (2026-10-29)** — **ส.บช.3 / ยื่นงบ DBD** (ลำดับที่ 1), **ภ.ธ.40 SBT** (ลำดับที่ 2) และ **ทะเบียนอากรแสตมป์** (ลำดับที่ 3) · เพิ่ม **ทะเบียน ภ.ง.ด.3/53 (CE fallback) ใน Wave 2C** เมื่อ 2026-10-29 · เทสต์ `od19_etax_invoice` 33 tests + `od19_thai_tax_reports` 96 tests, 0 failed ทั้งคู่; เหลือเฉพาะ e-Stamp / โหมด `live` ที่รอ API spec ภายนอก

## 2. สิ่งที่ระบบมีวันนี้ (As-Is)

### 2.1 โมดูลบัญชีที่ติดตั้งใช้งานจริงใน `odoo19_pdev`

| กลุ่ม | โมดูล | บทบาท |
| --- | --- | --- |
| Core Odoo 19 | `account`, `account_payment`, `account_asset_management`, `account_fiscal_year` | บัญชีแกนหลัก + สินทรัพย์ถาวร + ปีบัญชี |
| Core Thai | `l10n_th` | ผังบัญชีไทย + ภาษีไทย + รายงาน ภ.พ.30 / ภ.ง.ด.3 / ภ.ง.ด.53 (account.report engine — **ภ.ง.ด.3/53 บน CE ต้องใช้ทะเบียน fallback ใน `od19_thai_tax_reports`** เพราะ viewer อยู่ใน Enterprise `account_reports`) |
| OCA Thai | `l10n_th_account_tax` | VAT + WHT บนบรรทัดใบแจ้งหนี้ + `withholding.tax.cert` (50 ทวิ) + `account.move.tax.invoice` (`tax_invoice_number`/`tax_invoice_date`) |
| OCA Finance Tools | `account_lock_date_update`, `account_move_name_sequence` | ล็อกงวดบัญชี + รันเลขที่เอกสารไม่มีช่องว่าง |
| OCA (Wave 2A, 2026-10-27) | `account_financial_report`(+`date_range`), `account_tax_balance`, `partner_statement`, `account_reconcile_oca`(+`account_statement_base`), `auditlog`, `account_move_tier_validation`(+`base_tier_validation_formula`), `account_check_deposit`, `account_billing`, `account_journal_lock_date` | รายงานการเงิน + กระทบยอด VAT/ธนาคาร + AR/AP statement + Audit Trail + อนุมัติหลายชั้น + เช็ครับ + จัดกลุ่มใบแจ้งหนี้ + ล็อกงวดสมุดรายวัน |
| OCA | `base_tier_validation`, `currency_rate_update`, `report_xlsx` | อนุมัติหลายชั้น + เรต + Excel export |
| Custom od19 | `od19_thai_localization_base`, `od19_partner_thai_fields`, `od19_thai_font_support` | ฐานไทย + ที่อยู่ไทย (อำเภอ/ตำบล/รหัสไปรษณีย์) + ฟอนต์ |
| Custom od19 | `od19_accounting_features`, `od19_thai_tax_reports`, `od19_etax_invoice` | ฟีเจอร์บัญชี + ทะเบียน VAT/WHT + e-Tax Invoice |
| Custom od19 | `od19_asset_disposal`, `od19_asset_loan` | จำหน่าย/ให้ยืมสินทรัพย์ |

### 2.2 จุดแข็งที่ยืนยันจากโค้ด

- **ใบกำกับภาษีขาย**: core `l10n_th` override หัวเอกสารเป็น "Tax Invoice" + แสดง `l10n_th_branch_name` (สาขา)
- **รายงาน ภ.พ.30**: มีโครงครบ (ภาษีขายข้อ 1-5, ภาษีซื้อข้อ 6-7, VAT ข้อ 8-12 + ยกยอด) เป็น `account.report`
- **WHT**: มี `withholding.tax.cert` + `account.move.tax.invoice` + PIT rate data
- **ล็อกงวด + รันเลขที่**: ติดตั้งแล้วทั้งคู่

## 3. Gap Analysis — ข้อบังคับไทย vs ความครอบคลุม

### หมวด A: กฎหมายแม่บท / DBD / การเก็บรักษาเอกสาร

| ข้อบังคับ | สิ่งที่กฎหมายกำหนด | สถานะ | ช่องว่าง |
| --- | --- | --- | --- |
| พ.ร.บ.การบัญชี 2543 ม.14 | เก็บรักษาสมุดบัญชี/เอกสาร **5 ปี** | 🟡 | มี DB เก็บถาวร + รายงาน ส.บช.3 ระบุนโยบายจัดเก็บ 5 ปี แต่ยังไม่มีกลไกห้ามลบ/retention enforcement ชัดเจน |
| พ.ร.บ.การบัญชี 2543 ม.11 | งบการเงินรายปี + ยื่น DBD **150 วัน** | ✅ | รายงาน `od19_thai_tax_reports.sbc3_register` (แบบ ส.บช.3) ต่อยอดยอดจากงบ TFRS for NPAEs + แสดงเลขทะเบียนนิติบุคคล/เลขผู้เสียภาษี/ที่อยู่ และคำนวณกำหนดยื่น 150 วัน |
| พ.ร.บ.การบัญชี 2543 ม.17 | งบการเงินต้องมีผู้สอบบัญชีรับรอง (บางประเภท) | 🔴 | ไม่รองรับสายงานผู้สอบบัญชี |

### หมวด B: ภาษีมูลค่าเพิ่ม (VAT)

| ข้อบังคับ | สิ่งที่กฎหมายกำหนด | สถานะ | ช่องว่าง |
| --- | --- | --- | --- |
| ม.86/4 | ใบกำกับภาษีเต็มรูป **8 รายการ** | ✅ | validation 8 รายการก่อน post เมื่อผู้ซื้อมีเลขภาษี (บังคับ/ปิดได้ผ่าน `res.company.od19_enforce_86_4_validation`) + ฟิลด์ `od19_tax_invoice_doc_type` |
| ม.86/6 | ใบกำกับอย่างย่อ | ✅ | รายงาน `od19_thai_tax_reports.abbreviated_tax_invoice_document` สำหรับขายปลีก (ผู้ซื้อไม่มีเลขภาษี) |
| ม.86/9-10 | ใบเพิ่มหนี้ / ใบลดหนี้ | ✅ | ผูกประเภทเอกสาร (ใบเพิ่มหนี้/ใบลดหนี้) + อ้างอิงเลขที่/วันที่ใบกำกับภาษีเดิม + เหตุผล บนรายงานใบกำกับภาษี |
| ภ.พ.30 | ยื่น VAT รายเดือน (15 ของเดือนถัดไป) | ✅ | core `l10n_th` tax_report + od19 register |
| ม.82/5 | **ภาษีซื้อต้องห้าม** (หักไม่ได้) | ✅ | ฟิลด์ `od19_vat_deductible` บน `account.move.line` + ภาษีซื้อต้องห้าม + แยกยอดในทะเบียนภาษีซื้อ |
| ม.83/6 | **Reverse charge ภ.พ.36** (ซื้อบริการต่างประเทศ) | ✅ | ภาษี reverse charge (self-assess ขาย+ซื้อ) + รายงาน ภ.พ.36 |
| ม.83/5 | ขายยกเว้น VAT | ✅ | core จัดการ exempt |

### หมวด C: ภาษีหัก ณ ที่จ่าย (WHT)

| ข้อบังคับ | สิ่งที่กฎหมายกำหนด | สถานะ | ช่องว่าง |
| --- | --- | --- | --- |
| ภ.ง.ด.1 / 2 / 3 | หักจากเงินเดือน/บุคคล/นิติบุคคล | ✅ | OCA `l10n_th_account_tax` (PIT) + ทะเบียน `od19_thai_tax_reports.pnd3_register` รวบรวม ภ.ง.ด.3/3a จาก `account.withholding.move` (core `tax_report_pnd3` ใช้ไม่ได้บน CE เพราะ viewer อยู่ใน Enterprise `account_reports`) |
| ภ.ง.ด.53 | ยื่น **7 วัน** (e-Filing +8 = 15 วัน) | ✅ | ทะเบียน `od19_thai_tax_reports.pnd53_register` (กรอง `income_tax_form = pnd53` จาก `account.withholding.move`; core `tax_report_pnd53` ใช้ไม่ได้บน CE เพราะ viewer อยู่ใน Enterprise `account_reports`) |
| ภ.ง.ด.54 | นำส่งภาษีให้ราชการ/องค์กร | ✅ | report เฉพาะใน `od19_thai_tax_reports` (flag `pnd54` บน `account.withholding.tax.income_tax_form`) |
| ม.50 ทวิ | หนังสือรับรองการหักภาษี **2 ฉบับ** (ม.40(1)(2) ภายใน 15 ก.พ. ปีถัดไป) | ✅ | OCA `withholding.tax.cert` |
| e-Withholding Tax | นำส่งอิเล็กทรอนิกส์ผ่านธนาคาร | 🟡 | mock-first พร้อม (Live รอ Bank API spec) |

### หมวด D: ภาษีเงินได้นิติบุคคล

| ข้อบังคับ | สิ่งที่กฎหมายกำหนด | สถานะ | ช่องว่าง |
| --- | --- | --- | --- |
| ภ.ง.ด.50 | ยื่นประจำปีภายใน 150 วัน | 🔴 | ไม่มี |
| ภ.ง.ด.51 | ยื่นครึ่งปี (ประมาณการ) ภายใน 2 เดือน | 🔴 | ไม่มี |
| TAS 12 | ภาษีเงินได้รอตัดบัญชี (deferred tax) | 🔴 | ไม่มีทั้งการคำนวณและรายงาน |

### หมวด E: e-Tax Invoice

| ข้อบังคับ | สิ่งที่กฎหมายกำหนด | สถานะ | ช่องว่าง |
| --- | --- | --- | --- |
| ระเบียบกรมสรรพากร พ.ศ. 2560 | e-Tax Invoice / e-Receipt | ✅ | `od19_etax_invoice` ทำ XML + XAdES-BES (RSA-SHA512) + แนบ XML ใน **PDF/A-3 level B** (XMP `pdfaid:part=3`/`conformance=B` + `pdfaExtension:schemas`, `/OutputIntents` sRGB ICC, `AFRelationship=/Data`) เสร็จแล้ว |
| ขมธอ.3-2560 (ETDA) | มาตรฐาน XML + ลายมือชื่อดิจิทัล | 🟡 | XML ครบ 6 Document Families + XSD ETDA จริงผูกในโมดูล + validate **ก่อน** ลงนาม · แก้ TypeCode ใบเพิ่มหนี้/ใบลดหนี้เป็น 80/81 ตาม `dncn` แล้ว — แต่ **ตระกูล `invoice` (380) ยังใช้ XSD generic 2015** ต้องได้ไฟล์ ขมธอ.3-2560 ตัวจริงจาก ETDA |
| การนำส่งให้สรรพากร | Upload ผ่านระบบ RD | 🟡 | มี model `od19.etax.submission` + adapter (`lib/rd_gateway.py`, Mock เป็นค่าเริ่มต้น) + batch export ZIP fallback — **แต่ยังไม่เชื่อม RD จริง** (รอ Provider ID + API spec) |

### หมวด F: ภาษีอื่น

| ข้อบังคับ | สิ่งที่กฎหมายกำหนด | สถานะ | ช่องว่าง |
| --- | --- | --- | --- |
| ภ.ธ.40 | ภาษีธุรกิจเฉพาะ (SBT) | ✅ | กลุ่มภาษี `tax_group_sbt` + ภาษี SBT 3% และส่วนท้องถิ่น 0.3% (`data/od19_sbt_data.xml`) + รายงาน `od19_thai_tax_reports.sbt_pp40_register` (รายรับ/ภาษี 3%/ท้องถิ่น/รวม) |
| อากรแสตมป์ / e-Stamp | อากรแสตมป์ + นำส่งอิเล็กทรอนิกส์ | 🟡 | **ทะเบียนอากรแสตมป์ + รายงาน** (2026-10-29): โมเดล `od19.stamp.duty.rate` (บัญชีอัตราอากร 6 ลักษณะ ใน `data/od19_stamp_duty_data.xml`) + `od19.stamp.duty` (คำนวณอากรจากอัตรา ปัดขึ้นตามกติกา "ทุก X บาทหรือเศษของ X บาท" + เพดานอากร) + รายงาน `od19_thai_tax_reports.stamp_duty_register` — **ยังไม่มี e-Stamp ยื่นอิเล็กทรอนิกส์ต่อ RD** (รอ API spec) |

### หมวด G: รายงานการเงิน / การปิดงบ

| ข้อบังคับ | สิ่งที่กฎหมายกำหนด | สถานะ | ช่องว่าง |
| --- | --- | --- | --- |
| TFRS for NPAEs | งบการเงินตามมาตรฐาน | ✅ | template งบการเงินตามแบบ NPAE ใน `od19_thai_tax_reports` (งบแสดงฐานะการเงิน + งบกำไรขาดทุน) **เสร็จ 2026-10-29** (Wave 3) |
| งบทดลอง / กำไรขาดทุน / งบดุล / กระแสเงินสด | รายงานมาตรฐาน | ✅ | `account_financial_report` (OCA) **ติดตั้งแล้ว 2026-10-27** (Wave 2A) |
| กระทบยอดธนาคาร | Monthly recon | ✅ | `account_reconcile_oca` + `account_statement_base` **ติดตั้งแล้ว 2026-10-27** (Wave 2A); เชื่อมกับ core ผ่าน bridge `od19_accounting_reconcile_ui` (2026-11-01) |
| ปิดงวดบัญชี | ล็อกงวด | ✅ | `account_lock_date_update` ติดตั้งแล้ว + `account_journal_lock_date` **ติดตั้งแล้ว 2026-10-27** (Wave 2A) |

### หมวด H: การควบคุมภายใน / Audit Trail

| ข้อบังคับ | สิ่งที่กฎหมายกำหนด | สถานะ | ช่องว่าง |
| --- | --- | --- | --- |
| Audit Trail | ISO 9001 + การตรวจสอบย้อนกลับ | ✅ | `auditlog` (OCA) **ติดตั้งแล้ว 2026-10-27** (Wave 2A) |
| อนุมัติหลายชั้นบัญชี | Separation of Duties | ✅ | `base_tier_validation` + `account_move_tier_validation` (+`base_tier_validation_formula`) **ติดตั้งแล้ว 2026-10-27** (Wave 2A) |
| เช็ค | ระบบเช็ครับ/จ่าย | ✅ | `account_check_deposit` **ติดตั้งแล้ว 2026-10-27** (Wave 2A) |

## 4. แผนพัฒนา (ปิดช่องว่างตาม Wave)

### Wave 2A — Quick Win: เปิดใช้ OCA ที่มีอยู่แล้ว ✅ (ปิดแล้ว 2026-10-27)
**เป้าหมาย**: ได้รายงานการเงิน + การควบคุมภายใน + เครื่องมือเช็ค/จัดกลุ่ม โดยไม่ต้องเขียนโค้ดใหม่ (ความเสี่ยงต่ำ)

**ผลการติดตั้ง**: 12 โมดูล state = `installed` บน `odoo19_pdev` (ตรวจด้วย psql 2026-10-27) และ Odoo โหลดผ่านทุกโมดูลใน log (`Loading module account_billing (265/274)` → `account_check_deposit (266/274)` → `account_reconcile_oca (274/274)`)

> อัปเดต 2026-11-01: `od19_accounting_features` **ไม่ hard-depend** `account_reconcile_oca` อีกต่อไป — แยกเป็น bridge module `od19_accounting_reconcile_ui` (LGPL, `auto_install=True`) เพื่อให้ core ไม่ถูกล็อกกับ addon AGPL ภายนอก

| # | โมดูล | Repo | ปิดช่องว่าง | สถานะ |
| --- | --- | --- | --- | --- |
| 1 | `account_financial_report` | account-financial-reporting | หมวด G — TB / GL / BS / P&L | ✅ installed |
| 2 | `account_tax_balance` | account-financial-reporting | หมวด B — กระทบยอด VAT | ✅ installed |
| 3 | `partner_statement` | account-financial-reporting | AR/AP statement | ✅ installed |
| 4 | `account_reconcile_oca` (+`account_statement_base`) | account-reconcile | หมวด G — bank reconciliation (bridge: `od19_accounting_reconcile_ui`) | ✅ installed |
| 5 | `auditlog` | server-tools | หมวด H — Audit Trail (ISO 9001) | ✅ installed |
| 6 | `account_move_tier_validation` (+`base_tier_validation_formula`) | tier-validation | หมวด H — อนุมัติหลายชั้น | ✅ installed |
| 7 | `account_check_deposit` | account-financial-tools | หมวด H — เช็ครับ | ✅ installed |
| 8 | `account_billing` | account-invoicing | จัดกลุ่มใบแจ้งหนี้ก่อนจ่าย | ✅ installed |
| 9 | `account_journal_lock_date` | account-financial-tools | ล็อกงวดระดับสมุดรายวัน | ✅ installed |
| — | `date_range` | server-ux | dependency ของ `account_financial_report` | ✅ installed |

### Wave 2B — ปิดช่อง VAT (สรรพากรบังคับ) ✅ (ปิดแล้ว 2026-10-27)
**เป้าหมาย**: ปิดช่องว่างภาษีมูลค่าเพิ่มที่สรรพากรบังคับ ภายในโมดูล custom `od19_thai_tax_reports` v19.0.1.5.0

**ผลการดำเนินการ**: unit tests ของโมดูลผ่าน **39 รายการ (0 failed, 0 error)** บน `odoo19_pdev`

| รายการ | สิ่งที่ทำ | ไฟล์/กลไก |
| --- | --- | --- |
| ม.82/5 ภาษีซื้อต้องห้าม | ฟิลด์ `od19_vat_deductible` บน `account.move.line` + ภาษี "ภาษีซื้อต้องห้าม" + แยกยอดในทะเบียนภาษีซื้อ | `models/account_move_line.py`, `data/od19_vat_non_deductible_data.xml`, `report/vat_purchase_register.*` |
| ม.83/6 Reverse charge ภ.พ.36 | ภาษี reverse charge (repartition factor < 0 = self-assess ภาษีขาย + ภาษีซื้อ) + รายงาน ภ.พ.36 | `models/account_tax.py`, `data/od19_reverse_charge_data.xml`, `report/pp36_register.*` |
| ม.86/4 validate 8 รายการ | ตรวจความครบถ้วน 8 รายการก่อน post (เฉพาะเมื่อผู้ซื้อมีเลขภาษี) — เปิด/ปิดผ่าน `res.company.od19_enforce_86_4_validation` | `models/account_move.py`, `models/res_company.py`, `models/res_config_settings.py` |
| ม.86/6 ใบกำกับอย่างย่อ | รายงาน Abbreviated Tax Invoice สำหรับขายปลีก | `report/tax_invoice_forms.xml` |
| ม.86/9-10 ใบเพิ่มหนี้/ใบลดหนี้ | ฟิลด์ `od19_tax_invoice_doc_type` + block "อ้างอิงใบกำกับภาษีเดิม/เหตุผล" บนรายงานใบกำกับภาษี | `models/account_move.py`, `report/tax_invoice_forms.xml` |

### Wave 2C — WHT + e-Tax ให้สมบูรณ์ ✅ (audit 2026-10-27 · Phase 0–4 ปิดแล้ว 2026-10-28)
**เป้าหมาย**: ปิดช่องว่างหมวด C (ภ.ง.ด.54, e-Withholding Tax) และหมวด E (e-Tax Invoice ให้สมบูรณ์)

#### ผล Audit `od19_etax_invoice` (read-only, 2026-10-27 · 21 ไฟล์)

**สิ่งที่ทำเสร็จและได้มาตรฐานแล้ว**

| องค์ประกอบ | สถานะ | หลักฐาน |
| --- | --- | --- |
| XML 6 Document Families | ✅ | `lib/namespaces.py` — TaxInvoice(388) · Receipt(T01) · AbbreviatedTaxInvoice(T05) · Invoice(380) · DebitCreditNote(81) · CancellationNote(T07) |
| XSD ETDA จริงผูกในโมดูล | ✅ | `data/schema/ETDA/**` + `uncefact/**` ครบ · `lib/validator.py` compile + cache ต่อ doc type · ตรวจก่อนลงนาม |
| XAdES-BES | ✅ | `lib/signer.py` — RSA-SHA512 · SHA-512 · c14n 1.0 · enveloped transform · KeyInfo/X509Data |
| Certificate lifecycle | ✅ | `models/etax_certificate.py` — PEM key/cert/chain + passphrase + verify + expiry |
| Lifecycle + immutability | ✅ | draft → generated → signed; เอกสารที่ signed แก้/ยกเลิกไม่ได้ |
| แนบ XML ใน PDF | ✅ | `lib/pdf_embed.py` (pikepdf) แนบ signed XML เข้า `/Names /EmbeddedFiles` เป็น **PDF/A-3 level B** — XMP `pdfaid:part=3`/`conformance=B` + `pdfaExtension:schemas`, `/OutputIntents` sRGB ICC, `AFRelationship=/Data`, PDF 1.7 · เขียน `/W` ของ CIDFont ใหม่จาก embedded font program (fontTools) ให้ตรง ISO 19005-3 §6.2.11.5 |
| QR + รายงานไทย | ✅ | `lib/qr.py` + `report/etax_document_report.xml` (โทน #9E2424, watermark ฉบับร่าง, block ลายเซ็น + digest) |
| เทสต์ | 🟡 | `tests/test_etax_document.py` 18 เทสต์ — ครอบ 2/6 families |

**ตรวจแล้วว่าไม่เป็นปัญหา**: ลำดับ Summation `OriginalInformationAmount → LineTotalAmount → DifferenceInformationAmount` ถูกต้องตามทั้ง XSD ของ DebitCreditNote และ CancellationNote · TypeCode 80/81/380/388/T01/T05/T07 มีจริงใน `ThaiDocumentNameCode_Invoice_1p0.xsd` · log 2026-10-26 โหลดโมดูลผ่านสะอาด

**ช่องว่างที่เหลือ**

| รายการ | สถานะ | สิ่งที่ต้องทำ |
| --- | --- | --- |
| A. PDF/A-3 | ✅ | `lib/pdf_embed.py` (pikepdf) ใส่ XMP (`pdfaid:part=3`, `conformance=B` + `pdfaExtension:schemas`), `/OutputIntents` + sRGB ICC (สร้างจาก Pillow/lcms), `AFRelationship=/Data` บน embedded file, PDF 1.7 — เทสต์ parse XMP/OutputIntent/attachment ผ่าน · **ยืนยันด้วย veraPDF 1.30.3 (flavour 3b) แล้ว: PASS** (`lib/pdf_embed.py` เขียน `/W` ของ CIDFont ใหม่จาก embedded font program ด้วย `fontTools` เพราะ wkhtmltopdf ปัดเศษ glyph width ไม่ตรงตาม ISO 19005-3 §6.2.11.5) |
| B. ช่องทางยื่น RD | ✅ | อยู่ใน `od19_etax_invoice` — model `od19.etax.submission` (state/submitted_at/reference/response_code/response_message/attempt_count) + config ระดับบริษัท (`od19_etax_rd_mode` mock｜live, `od19_etax_rd_endpoint`, `od19_etax_rd_provider_id`) + adapter `lib/rd_gateway.py` (Mock = ค่าเริ่มต้น, Live = จุด implement จริง) · fallback `lib/batch_export.py` (ZIP: signed XML + PDF + `manifest.txt` เป็น audit trail) |
| C. e-Withholding Tax | 🟡 mock พร้อม | อยู่ใน `od19_thai_tax_reports` — model `od19.ewht.submission` (state/submitted_at/reference/response_code/response_message/attempt_count) + config บริษัท (`od19_ewht_mode` mock｜live, `od19_ewht_endpoint`, `od19_ewht_provider_id`) + adapter `lib/ewht_gateway.py` (Mock = ค่าเริ่มต้น, Live = จุด implement จริง) · แหล่งข้อมูล = `account.withholding.move` (OCA) · **โหมด `live` ยังต้อง bank API + mTLS** |
| D. ภ.ง.ด.54 report | ✅ | อยู่ใน `od19_thai_tax_reports` — mirror pattern `report/wht_register.py` + `pnd54` ใน `wizard/tax_report_wizard.py` + `selection_add` `pnd54` บน `account.withholding.tax.income_tax_form` (OCA ไม่มีค่านี้) |

**ประเด็นคุณภาพที่พบ (ยืนยันจากโค้ด)**

| # | เรื่อง | ระดับ | รายละเอียด |
| --- | --- | --- | --- |
| 1 | ใบเพิ่มหนี้ออกเป็น TypeCode 81 (ใบลดหนี้) | ✅ | แก้แล้ว — `lib/namespaces.py` เลือก 80/81 ตาม `move_id.dncn` (`NOTE_TYPE_CODE_BY_DNCN`) + `_compute_type_code` depends `move_id.dncn` · เทสต์ยืนยัน |
| 2 | `validator.ValidationError` เป็น Exception ธรรมดา | ✅ | แก้แล้ว — `_build_unsigned_tree` จับ `ValidationError` → raise `UserError` ข้อความไทย |
| 3 | เทสต์ XSD ครอบเพียง 2/6 families | ✅ | แก้แล้ว — เทสต์ครอบครบ 6 families และผ่านทั้งหมด · XSD ที่ bundle เป็นของจริงจาก ETDA (ตรวจกับ master ทุกไบต์) แต่มี 3 โปรไฟล์ย่อย: **generic 2015** (`invoice` 380 → `listID=1001_Invoice`, `agency=6`, ไม่มี `PurposeCode`/`CreationDateTime`), **Thai full** (tax_invoice/receipt/abbreviated_tax_invoice/debit_credit_note) และ **minimal** (`cancellation_note` → มีแต่ SellerTradeParty + AdditionalReferencedDocument + InvoicerTradeParty) · แก้ที่ `lib/xml_builder.py` + `lib/namespaces.py` ให้ builder รู้จักโปรไฟล์ (`uses_generic_profile` / `uses_minimal_profile`) แทนการแทน XSD |
| 4 | `PyPDF2` เลิกพัฒนาแล้ว | ✅ | แก้แล้ว — ตัด `PyPDF2` ออก ใช้ `pikepdf` ทั้ง embed + extract (`__manifest__` external_dependencies อัปเดตแล้ว) |
| 5 | `od19_etax_enabled` เป็น field ตกแต่ง | ✅ | แก้แล้ว — `res.company._od19_etax_check_enabled()` เป็นสวิตช์เดียวของโมดูล: gate การสร้างเอกสาร (`create`), ทุกขั้น lifecycle (`action_generate_xml`/`action_sign`/`action_generate_pdf`/`action_print`), การนำส่ง (`action_submit_to_rd`, submission `action_submit`/`action_export_batch`) และซ่อนปุ่ม/แท็บใน view ด้วย related field · เทสต์ `test_company_switch_gates_the_feature` |
| 6 | default mapping ไม่ใช้ Receipt/T05/Invoice/T07 | ✅ | แก้แล้ว — `_od19_etax_default_type()` ใช้เกณฑ์เดียวกับ `od19_thai_tax_reports._od19_get_tax_invoice_doc_type()`: `dncn` → debit/credit note · `out_invoice` + buyer VAT → full (388) ไม่มี VAT → abbreviated (T05, ม.86/6) · `out_refund` → debit/credit note · `out_receipt` → receipt (T01) · ส่วน `invoice` (380) และ `cancellation_note` (T07) ออกนอกวงจรการขายปกติจึงคงเป็น manual · `_ALLOWED_MOVE_TYPES` + domain + ValidationError รองรับ `out_receipt` · เทสต์ `test_default_type_follows_the_buyer_tax_status` + `test_default_type_for_sales_receipt` |
| 7 | ทับซ้อนกับ Wave 2B | ✅ | แก้แล้ว — คงความสามารถทั้งสองไว้ (คนละวัตถุประสงค์: paper 86/6 สำหรับขายปลีก vs electronic T05 พร้อมลายมือชื่อดิจิทัล + PDF/A-3) แต่เพิ่ม `<field name="help">` ใน `action_od19_abbreviated_tax_invoice` (`od19_thai_tax_reports/report/tax_invoice_forms.xml`) ระบุขอบเขตและเส้นทางออกเอกสารอิเล็กทรอนิกส์ให้ชัด |

**แผนดำเนินการ Wave 2C**

| Phase | งาน |
| --- | --- |
| Phase 0 — Quick win แก้ของเดิม | ✅ (1) TypeCode 80/81 ตาม `dncn` · ✅ (2) schema error → `UserError` ข้อความไทย · ✅ (3) เทสต์ XSD 6 families ผ่านครบ — builder เป็น profile-aware (generic `invoice` + minimal `cancellation_note` + Thai full) · ✅ (4) ตัด `PyPDF2` ใช้ `pikepdf` · ✅ (5) `od19_etax_enabled` gate ครบทุกเส้นทาง (create/lifecycle/submit + view) v19.0.1.2.1 |
| Phase 1 — PDF/A-3 | ✅ `lib/pdf_embed.py` (pikepdf) — XMP `pdfaid:part=3`/`conformance=B` + `pdfaExtension:schemas`, `/OutputIntents` sRGB ICC, `AFRelationship=/Data`, PDF 1.7 · เขียน `/W` ของ CIDFont ใหม่จาก embedded font program (เพิ่ม `fontTools` ใน `requirements-od19.txt`) · เทสต์ parse XMP/OutputIntent/attachment + `test_glyph_widths_match_the_font_program` · v19.0.1.2.3 · **veraPDF 1.30.3 flavour 3b: PASS** |
| Phase 2 — ช่องทางยื่น RD | ✅ model `od19.etax.submission` + config บริษัท + adapter (mock ได้) · fallback batch export ZIP + audit trail · v19.0.1.1.0 |
| Phase 3 — ภ.ง.ด.54 | ✅ report เฉพาะใน `od19_thai_tax_reports` (mirror `wht_register`) · v19.0.1.6.1 |
| Phase 3.5 — ปิดประเด็นคุณภาพ #6/#7 | ✅ default mapping ครบ families ตาม buyer VAT + receipt · เอกสารแยกขอบเขต paper 86/6 vs electronic T05 ชัดเจน · v19.0.1.2.3 / v19.0.1.6.1 |
| Phase 4 — e-Withholding | ✅ mock-first ใน `od19_thai_tax_reports` — model `od19.ewht.submission` + adapter `lib/ewht_gateway.py` (Mock/Live) + config บริษัท + view/security/เทสต์ · v19.0.1.7.0 (โหมด `live` รอ Bank API spec) |
| Phase 5 — ภ.ง.ด.3 / ภ.ง.ด.53 (CE fallback) | ✅ (2026-10-29) — core `l10n_th` มี ภ.ง.ด.3/53 เป็น `account.report` variant แต่ renderer อยู่ใน Enterprise `account_reports` (ชุดนี้ไม่มี) จึงเปิดจากเมนูไม่ได้ · เพิ่มทะเบียน QWeb PDF ในโมดูลเราเอง: `report/pnd3_register.py`/`.xml` (กรอง `income_tax_form in (pnd3, pnd3a)`) และ `report/pnd53_register.py`/`.xml` (กรอง `= pnd53`) อ่านจาก `account.withholding.move` (OCA) · ผูกเข้า wizard + เมนู `menu_pnd3_register`/`menu_pnd53_register` (seq 55/56) · เทสต์ bound/gathers/render · v19.0.1.14.0 |

**ต้องตัดสินใจ / รอข้อมูล**: (1) ~~PDF/A-3 ใช้ `pikepdf` หรือ `ghostscript`~~ ✅ เลือก `pikepdf` · (2) ~~มี RD Service Provider ID + API spec แล้วหรือยัง~~ 🟡 adapter ทำเป็น mock ได้แล้ว (`od19_etax_rd_mode`); mode `live` ยังต้องมี Provider ID + API spec จริง · (3) ~~ยืนยันการแยก TypeCode 80/81 (กระทบเอกสารที่ออกไปแล้ว)~~ ✅ ยืนยันแล้ว (ดูประเด็นคุณภาพ #1) · (4) ~~ลำดับเริ่ม Phase 0 หรือ Phase 1~~ ✅ เริ่มจาก Phase 0 (ปิดแล้วทั้งสอง) · (5) ~~ธนาคารสำหรับ e-Withholding (Phase 4)~~ 🟡 adapter ทำเป็น mock ได้แล้ว (`od19_ewht_mode`); mode `live` ยังต้องยืนยันธนาคาร + bank API spec · (6) **ยืนยันสมมุติฐาน ภ.ง.ด.54**: ใช้ flag `pnd54` ที่เพิ่มบน `account.withholding.tax.income_tax_form` เป็นเกณฑ์คัดรายการ (OCA ไม่มีค่านี้) — หากต้องการเกณฑ์อื่น (เช่น ตามประเภทผู้จ่าย/หน่วยงานราชการ) ต้องปรับ domain ใน `report/pnd54_register.py`
**ติดตาม**: terminal บน Windows กลับมาใช้งานได้แล้ว (2026-10-28) — Wave 2B/2C commit + **push ขึ้น `origin/feat/od19-wave2b-vat-compliance` แล้ว (HEAD ล่าสุด `d08a3c225b1`)** · Wave 2C Phase 0 (ข้อ 1–5 ครบ) + Phase 1 + Phase 2 + Phase 3 + Phase 3.5 (ปิดประเด็นคุณภาพ #6/#7 ครบทั้ง 7 ข้อ) + Phase 4 (e-Withholding mock-first) ปิดแล้ว · เทสต์ `od19_etax_invoice` 0 failed, 0 error(s) of 33 tests · เทสต์ `od19_thai_tax_reports` 0 failed, 0 error(s) of 63 tests (รวมเทสต์ e-WHT และ TAS 12 Deferred Tax) · คงเหลือเพียงการเชื่อมต่อจริงกับธนาคาร/RD สำหรับโหมด `live`

> หมายเหตุ: ผล audit ข้างต้นมาจากการตรวจแบบ read-only (ขั้นตอน audit ไม่ได้แก้ไขไฟล์ในโมดูล `od19_etax_invoice`) — การแก้ไขเกิดขึ้นภายหลังใน Phase 0–4 ตามแผนด้านบน

### Wave 3 — ภาษีเงินได้นิติบุคคล + มาตรฐานบัญชี

| รายการ | สถานะ | สิ่งที่ต้องทำ |
| --- | --- | --- |
| ภ.ง.ด.50 (รายปี) | ✅ | อยู่ใน `od19_thai_tax_reports` — `report/pnd50_register.py` (`_get_profit_and_loss` รวบยอดบัญชี `internal_group in (income, expense)` ที่ `parent_state='posted'` ผ่าน `_read_group(balance:sum)`) + template/report action `report/pnd50_register.xml` + selection/menu บน wizard · v19.0.1.8.0 |
| ภ.ง.ด.51 (ครึ่งปี/ประมาณการ) | ✅ | อยู่ใน `od19_thai_tax_reports` — `report/pnd51_register.py` ใช้ `_get_profit_and_loss` ร่วมกับ ภ.ง.ด.50, ประมาณการกำไรทั้งปี (`net_profit × 12 ÷ จำนวนเดือน`) และภาษีครึ่งปี = 50% ของประมาณการทั้งปี · v19.0.1.8.0 |
| TAS 12 Deferred Tax | ✅ | อยู่ใน `od19_thai_tax_reports` — Worksheet/Register `od19.deferred.tax.worksheet` + `od19.deferred.tax.line` (มูลค่าตามบัญชี vs ฐานภาษี → ผลต่างชั่วคราว taxable/deductible → ภาษีรอตัดบัญชี) · บันทึกบัญชีอัตโนมัติเฉพาะ **ส่วนเคลื่อนไหว** (ยอดปิดงวด − ยอดยกมาจาก `previous_worksheet_id` ที่ Post แล้ว) ผ่าน `action_post_deferred_tax` · ตั้งค่าบัญชี DTA/DTL/ค่าใช้จ่าย + สมุดรายวัน + อัตราภาษี ที่หน้าตั้งค่าบริษัท · v19.0.1.9.0 |
| TFRS for NPAEs template | ✅ | อยู่ใน `od19_thai_tax_reports` — `report/npae_financial_statement.py` (AbstractModel สรุป **งบแสดงฐานะการเงิน** จากยอดสะสม `parent_state='posted'` จัดกลุ่มตาม `account_type` เป็นหมุนเวียน/ไม่หมุนเวียน + **งบกำไรขาดทุน** เฉพาะรอบระยะเวลา) + template/report action `report/npae_financial_statement.xml` + selection/menu บน wizard · ตรวจสมการบัญชีผ่าน `balance_difference` (สินทรัพย์ − หนี้สิน − ส่วนของผู้ถือหุ้นรวมผลกำไร) · v19.0.1.10.0 |

**ประเด็นคุณภาพที่พบ (แก้แล้วใน Wave 3)**

| # | เรื่อง | ระดับ | รายละเอียด |
| --- | --- | --- | --- |
| 1 | รายงานเดิม 5 ตัว Print ไม่ได้ (`MissingError: Template not found`) | ✅ | แก้แล้ว — `report_name` ของ `ir.actions.report` ไม่ตรงกับ xmlid ของ QWeb template (template เดิมลงท้าย `_document`) ทำให้ `_render_template` หา template ไม่เจอ · rename xmlid ของ vat_sales/vat_purchase/wht/pp36/pnd54 ให้ตรง `report_name` (`od19_thai_tax_reports.<name>`) |
| 2 | เทมเพลตใช้ `t-field` กับค่า dict/ตัวแปร (compile ไม่ผ่าน) | ✅ | แก้แล้ว — `_compile_directive_field` บังคับ `assert "." in t-field` (ใช้กับ record.field เท่านั้น) ทำให้ `t-field="date_from"` และ `t-field="line['date']"` compile ไม่ผ่าน · เปลี่ยนเป็น `t-out` (+ `t-options='{"widget": "date"}'` สำหรับวันที่) ใน pnd50/pnd51/vat_sales/vat_purchase/wht/pp36/pnd54 |
| 3 | Computed field อ้าง computed field ของโมเดลเดียวกัน (TAS 12) | ✅ | แก้แล้ว — `total_dta`/`total_dtl` ถูกใช้เป็น dependency ของ `_compute_totals` ผ่าน `previous_worksheet_id.total_*` (self-reference) ทำให้ Odoo เตือน `should be declared with recursive=True` · ประกาศ `recursive=True` บนสองฟิลด์ |

**แผนดำเนินการ Wave 3**: ✅ ลำดับที่ 1 — ภ.ง.ด.50 + ภ.ง.ด.51 (report + ประมาณการ + เทสต์ render/compute ผ่าน) · ✅ ลำดับที่ 2 — TAS 12 Deferred Tax (worksheet + auto GL + เทสต์ 8 ตัวผ่าน) · ✅ ลำดับที่ 3 — TFRS for NPAEs (งบแสดงฐานะการเงิน + งบกำไรขาดทุน + เทสต์ render/compute/wizard ผ่าน) — **Wave 3 ปิดสมบูรณ์**

### Wave 4 — ภาษีอื่น + การยื่นราชการ
- ✅ **ส.บช.3 / ยื่นงบ DBD 150 วัน** + retention policy 5 ปี (2026-10-29)
  - รายงาน `od19_thai_tax_reports.sbc3_register` (model `report.od19_thai_tax_reports.sbc3_register`) — ต่อยอดยอดจากงบ TFRS for NPAEs ผ่าน `_get_report_values` ในโมดูล `od19_thai_tax_reports`
  - เทมเพลต QWeb `report/sbc3_register.xml` แสดง 5 ส่วน: ข้อมูลทั่วไป, งบแสดงฐานะการเงิน, งบกำไรขาดทุน, สรุปสาระสำคัญ, คำรับรอง + หมายเหตุ 150 วัน/5 ปี
  - คำนวณ `filing_deadline = date_to + 150 วัน` (พ.ร.บ.การบัญชี 2543 ม.11) และแสดง `retention_years = 5` (ม.14)
  - เพิ่มเข้า wizard `thai.tax.report.wizard` (selection `sbc3`) + เมนู `menu_sbc3_register` (seq 65) + เทสต์ 5 ตัว (`test_sbc3_register.py`)
- ✅ **ภ.ธ.40 SBT** (กรณีเข้าข่ายธุรกิจเฉพาะ) (2026-10-29) — กลุ่มภาษี `tax_group_sbt` + ภาษี SBT 3% (`tax_sbt_specific`) และส่วนท้องถิ่น 0.3% (`tax_sbt_local`) ใน `data/od19_sbt_data.xml`; รายงาน `od19_thai_tax_reports.sbt_pp40_register` สรุปรายรับ/ภาษี 3%/ท้องถิ่น/รวม แยกใบกำกับขาย–ใบลดหนี้ (ใบลดหนี้เป็นค่าลบ), เทสต์ 7 ตัว (`test_sbt_pp40_register.py`)
- ✅ **อากรแสตมป์ (Stamp Duty)** — ทะเบียน + รายงาน (2026-10-29)
  - โมเดล `od19.stamp.duty.rate` (บัญชีอัตราอากรแสตมป์ 6 ลักษณะ: 1/2/3/4 = 1 บาท/1,000, 5 = 1 บาท/2,000 เพดาน 10,000, 9 = 3 บาท/ฉบับ) ใน `data/od19_stamp_duty_data.xml`
  - โมเดล `od19.stamp.duty` คำนวณอากรอัตโนมัติ (`_compute_duty_amount`) ตามกติกา "ทุกจำนวนเงิน X บาท หรือเศษของ X บาท" = **ปัดขึ้น (ceil)** + เพดาน `max_amount`; มี sequence `ST/%(year)s/` และสถานะ ร่าง→ปิดอากร
  - รายงาน `od19_thai_tax_reports.stamp_duty_register` (ทะเบียนอากร + สรุปตามลักษณะแห่งตราสาร) + เมนู `menu_stamp_duty` (register/rates/report) + wizard selection `stamp_duty`
  - เทสต์ 13 ตัว (`test_stamp_duty.py`) ผ่านทั้งหมด
- **อากรแสตมป์ / e-Stamp** — เหลือเฉพาะการนำส่งอิเล็กทรอนิกส์ (e-Stamp ต่อ RD API) รอ API spec

## 5. ลำดับความสำคัญเชิงธุรกิจ (Criticality)

| ระดับ | รายการ | เหตุผล |
| --- | --- | --- |
| 🔴 วิกฤต (สรรพากร) | ม.82/5, ภ.พ.36, ภ.ง.ด.50/51, e-Tax | ฝ่าฝืนมีโทษ/เบี้ยปรับ |
| 🟠 สูง (Governance) | auditlog, tier validation, lock date สมบูรณ์ | ISO 9001 + Separation of Duties |
| 🟡 กลาง (มาตรฐาน) | TAS 12, NPAEs, ส.บช.3 | ต้องใช้ตอนปิดงบ/ส่งผู้สอบ |
| 🟢 ต่ำ (เฉพาะกิจ) | SBT, อากรแสตมป์, ภ.ง.ด.54 | ขึ้นกับประเภทธุรกิจ |

## 6. การเชื่อมโยงเอกสาร

| เอกสาร | ความสัมพันธ์ |
| --- | --- |
| `accounting-requirements-coverage.md` | มุม "ข้อกำหนดฝ่ายบัญชี" (requirement checklist) — เอกสารนี้เป็นมุม "ข้อบังคับกฎหมาย" เสริมกัน |
| `domain-wave-matrix.md` | Wave 2 Focus ระบุ finance controls ที่สอดคล้องกับแผนในข้อ 4 |
| `2026-10-21-odoo19-enterprise-wave-2-custom-finance-controls.md` | Wave 2 child spec — งาน Wave 2A/2B/2C ควรอัปเดตในเอกสารนี้ |
