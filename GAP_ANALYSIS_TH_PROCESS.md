# การวิเคราะห์ช่องว่าง (Gap Analysis)
## กระบวนการธุรกิจไทย: Trading + Service + Project + Contract เทียบกับระบบ Odoo 19 (OD19)

| รายการ | รายละเอียด |
|---|---|
| เวอร์ชันเอกสาร | R00 |
| วันที่จัดทำ | 2026-11-01 |
| ขอบเขต | ฝั่งขาย / ฝั่งซื้อ / ฝั่งบริการ / บัญชีรับ-จ่าย / เบิกเงินล่วงหน้า / เบิกค่าใช้จ่าย / โครงการ-สัญญา |
| ระบบอ้างอิง | Odoo 19 (custom_addons `od19_*` + OCA `third_party/oca`) |
| เอกสารที่เกี่ยวข้อง | `GAP_ANALYSIS_OD15_to_OD19.md`, `GAP_ANALYSIS_DTR_OD15_to_OD19.md`, `OCA_MODULE_ASSESSMENT_TH.md` |
| เอกสารปลายทาง | `WAVE6_PROCESS_GAP_CLOSURE_PLAN_TH.md` |

---

## 1. วัตถุประสงค์

รวบรวม "กระบวนการดำเนินงานที่แนะนำ" สำหรับบริษัทที่มีรูปแบบธุรกิจผสม (ซื้อมาขายไป, งานบริการ, งานโครงการ, งานสัญญา) ตามข้อกำหนดกฎหมาย/ภาษีไทย แล้วเทียบกับความสามารถที่มีอยู่จริงในระบบ OD19 เพื่อระบุ **สิ่งที่ยังขาด (Gap)** และจัดลำดับความสำคัญก่อนนำไปจัดทำแผนปิดช่องว่าง

---

## 2. วิธีดำเนินการ และข้อจำกัด

**วิธีดำเนินการ**
1. วิจัยจากแหล่งข้อมูลไทยระดับ primary: กรมสรรพากร (rd.go.th), สภาวิชาชีพบัญชี (tfac.or.th), ETDA (etda.or.th), DBD (dbd.go.th) และเอกสาร Odoo/OCA (ดูข้อ 8)
2. ตรวจความสามารถจริงของระบบจากซอร์สโค้ด: `__manifest__.py`, โมเดล (`.py`), มุมมอง, รายงาน และรายการโมดูลที่โคลนไว้ใน `third_party/oca`
3. อ้างอิงขอบเขตธุรกิจเดิมจาก `migration/od15_export/modules.txt` (โมดูล `dtr_*` / `autoinfo_*` ที่ใช้งานจริงใน Odoo 15)

**ข้อจำกัดที่ต้องทราบ**
- เอกสารนี้ยืนยัน "ของที่มี" จากซอร์สโค้ดเป็นหลัก **ยังไม่ได้ตรวจสอบสถานะติดตั้งจริงในฐานข้อมูล `odoo19_pdev`** (เครื่อง terminal มีปัญหาชั่วคราว) รายการที่กำกับ "(ตรวจสอบ)" จึงต้องยืนยันกับ DB ก่อนดำเนินการ
- ข้อกฎหมายอ้างอิงจากเอกสารเผยแพร่ของหน่วยงาน ณ วันที่จัดทำ ควรตรวจทานซ้ำก่อนใช้ในเอกสารราชการ

---

## 3. สถานะรายด้าน (มีอยู่แล้ว / ยังขาด)

### A. ฝั่งขาย (Sales)

| กระบวนการมาตรฐาน | สถานะใน OD19 | ช่องว่าง |
|---|---|---|
| ใบเสนอราคา → SO → ส่งของ → ใบกำกับภาษี → ใบเสร็จ | **มี** `sale_management` + `od19_quotation_document_sequence` (QB/QT/QI/QD + revision) + `od19_sale_report_native` + `od19_sales_confirm_stamp` | — |
| ใบกำกับภาษี / e-Tax Invoice & e-Receipt (ขมธอ.3-2560 + XAdES) | **มี** `od19_etax_invoice` | — |
| ใบลดหนี้ / ใบเพิ่มหนี้ (ม.86/9–10) | **มี** `od19_accounting_dncn` | — |
| ใบสำคัญจ่าย / ใบสำคัญรับเงิน | **มี** `od19_accounting_payment_voucher_reports` | — |
| เช็ค (ลูกค้า/ผู้ขาย + พิมพ์เช็ค) | **มี** `od19_accounting_cheque` | — |
| ใบกำกับอย่างย่อ (เฉพาะค้าปลีก) | (ตรวจสอบ) | อาจไม่แยก template |
| Credit limit / ระงับการขาย | **มีบางส่วน** `od19_sales_customer_risk_gate` (blacklist + credit approval) | ยังไม่มีวงเงินเครดิตแบบ rolling + hold อัตโนมัติจาก aging |
| **เงินมัดจำรับ / ล่วงหน้ารับ + VAT** | **มีบางส่วน** `od19_accounting_advance` (ตัดบัญชีล่วงหน้าเท่านั้น) | **ไม่ผูก VAT/ใบกำกับภาษี + ไม่แยก "มัดจำ" กับ "เงินประกันที่ต้องคืน"** |
| **Progress / Milestone Billing** | **มีบางส่วน** `od19_sales_contract_core` + `od19_sales_billing_evidence` | **ไม่มีตารางงวดเรียกเก็บ + สร้างใบแจ้งหนี้อัตโนมัติตามงวด** |
| **เงินประกันผลงาน (Retention)** | **ไม่มี** | ต้องเพิ่มทั้งการหักงวด + บัญชีลูกหนี้ + ติดตามกำหนดคืน |

### B. ฝั่งซื้อ (Purchase)

| กระบวนการมาตรฐาน | สถานะใน OD19 | ช่องว่าง |
|---|---|---|
| PR → PO → รับของ → ตั้งหนี้ → จ่าย (3-way matching) | **มี** `od19_purchase_procurement_core` + OCA `purchase_request` + `od19_purchase_request_extend` | — |
| Revision control / Terms / Document sequence | **มี** `od19_purchase_revision`, `od19_purchase_terms`, `od19_purchase_document_sequence` | — |
| WHT ภ.ง.ด.3 / 53 / 54 + **หนังสือรับรอง 50 ทวิ** | **มี** `od19_thai_tax_reports` (wht_register + wht_certificate + pnd3/pnd53/pnd54) | — |
| ภาษีซื้อต้องห้าม / Reverse charge | **มี** tax data `od19_vat_non_deductible_data.xml`, `od19_reverse_charge_data.xml` | — |
| **เงินมัดจำจ่าย / ล่วงหน้าจ่ายผู้ขาย + VAT/WHT** | **มีบางส่วน** `od19_accounting_advance` (supplier) | ไม่มี VAT + จังหวะหัก WHT ตอนจ่ายล่วงหน้า |
| **สัญญาซื้อระยะยาว / Blanket Order / ผู้รับเหมาช่วง** | OCA `sale-blanket`, `purchase-workflow` โคลนไว้ | ยังไม่ผูกสัญญาซื้อกับ PO/ทยอยส่ง |
| รับ e-Tax Invoice จากผู้ขาย (XML) | **ไม่มี** | รับ/แปลง XML เป็น Vendor Bill + ภาษีซื้อ |

### C. ฝั่งบริการ (Service)

| กระบวนการมาตรฐาน | สถานะใน OD19 | ช่องว่าง |
|---|---|---|
| ใบสั่งงานบริการ / Helpdesk | **มี** `od19_helpdesk_extension` (บน OCA `helpdesk_mgmt`) + `od19_service_card` (PM plan) | — |
| Warranty / RMA / Claim | **มี** `od19_service_warranty` (บน `repair`) + `od19_product_return` | — |
| KPI หลังการขาย / QC | **มี** `od19_after_sales_reporting`, `od19_quality_control` | — |
| **เรียกเก็บสัญญาบริการรายงวดอัตโนมัติ (Recurring)** | **ไม่มี** (ไม่พบ OCA `contract` / `sale_subscription` ในโปรเจกต์) | ต้องมี billing schedule + auto invoice |
| Timesheet → Invoice | (ตรวจสอบ) มี project/analytic | ยังไม่ยืนยันการเรียกเก็บจาก timesheet |
| ภาษีธุรกิจเฉพาะ (SBT) | **มี** `od19_sbt_data.xml` + PP40 register | — |

### D. ฝั่งบัญชี รับ (AR) / จ่าย (AP)

| กระบวนการมาตรฐาน | สถานะใน OD19 | ช่องว่าง |
|---|---|---|
| Aging AR/AP, GL, Trial Balance | **มี** OCA `account_financial_report`, `partner_statement` | — |
| กระทบยอด / บัญชีพัก / WHT clearing | **มี** `od19_accounting_features` (clearing wizards), `od19_accounting_reconcile_ui` + OCA `account_reconcile_oca` | — |
| ปิดงวด | **มี** `od19_accounting_operational_closure`, period clear wizard | — |
| ภ.พ.30 (แบบยื่น) | **มีบางส่วน** VAT Sales/Purchase Register + PP36 | **ยังไม่พบแบบ ภ.พ.30** (ตรวจสอบ) |
| **ค่าเผื่อหนี้สงสัยจะสูญ + ตัดหนี้สูญ (ฎ.186)** | **ไม่มี** | ต้องเพิ่ม allowance + write-off |
| ภ.ง.ด.50/51, TAS 12, NPAE, ส.บช.3, อากรแสตมป์ | **มี** `od19_thai_tax_reports` | — |

### E. เบิกเงินล่วงหน้า / เงินทดรองจ่าย / เงินสดย่อย

| กระบวนการมาตรฐาน | สถานะใน OD19 | ช่องว่าง |
|---|---|---|
| เงินล่วงหน้า **ลูกค้า/ผู้ขาย** | **มี** `od19_accounting_advance` (Draft→Post→Reconciled) | ไม่มี VAT/ใบกำกับภาษี |
| เงินสดย่อย (imprest) + เติมเงิน | **มี** `od19_accounting_petty_cash` | ต้องยืนยันตรรกะ imprest / ใบรับรองแทนใบเสร็จ |
| **เงินทดรองจ่ายพนักงาน + การเคลียร์** | **มีเฉพาะแบบพิมพ์** `dtr.adv.request.form` (`f_adv_001`) ใน `od19_reporting_jasper` — **โมเดล `dtr.advance` ยังไม่ติดตั้งบน OD19** (ระบุใน docstring ของไฟล์) | **ต้องสร้างโมเดลใบขอเบิก + อนุมัติขั้นบันได + จ่าย + เคลียร์** |
| ใบรับรองแทนใบเสร็จรับเงิน | **ไม่มี** | ต้องเพิ่มเอกสาร/พิมพ์ + ห้ามเครดิตภาษีซื้อ |

### F. เบิกค่าใช้จ่าย (Expense Claim)

| กระบวนการมาตรฐาน | สถานะใน OD19 | ช่องว่าง |
|---|---|---|
| เบิกค่าใช้จ่าย + อนุมัติหลายชั้น + คืนเงินสด + WHT | **มี** `hr_expense` + `od19_hr_expense_thai` + `od19_hr_expense_enhanced` (dept-head auto-approver, XLSX, delegate, สร้าง `account.payment` จริง) | — |
| **นโยบาย/วงเงินเบี้ยเลี้ยง (ม.42(3))** | **ไม่มี** | ต้องเพิ่ม field นโยบาย + วงเงิน + validate |
| ประเภทเอกสารประกอบ (e-Receipt / ใบรับรองแทนใบเสร็จ) | **ไม่มี** | ต้องเพิ่มประเภทเอกสาร |
| อัตรา WHT ค่าโรงแรม 3% | (ตรวจสอบ) enhanced มี WHT | ยืนยันการ map อัตราตามประเภทเงินได้ |

### G. โครงการ / สัญญา

| กระบวนการมาตรฐาน | สถานะใน OD19 | ช่องว่าง |
|---|---|---|
| Job Number / ต้นทุนโครงการ / P&L ต่อโครงการ | **มี** `od19_project_analytic`, `od19_project_enhanced`, `od19_sales_project_context` (มี sale_order_pnl_analysis) | — |
| สัญญาแม่ (วงเงิน/consumption/amendment) | **มี** `od19_sales_contract_core` | ไม่มีแผนเรียกเก็บ/retention |
| **TFRS 15 – ตารางรับรู้รายได้ตามสัญญา/โครงการ** | **ไม่มี** | ต้องมี revenue schedule |
| ต่ออายุสัญญา / แจ้งเตือนหมดอายุ | (ตรวจสอบ) มี `start_date`/`end_date` | ยังไม่มี renewal workflow |

---

## 4. ทะเบียนช่องว่าง (Gap Register)

| รหัส | ช่องว่าง | ด้าน | ระดับ | อ้างอิงกฎหมาย/มาตรฐาน |
|---|---|---|---|---|
| G-01 | เงินมัดจำรับ/ล่วงหน้ารับ ยังไม่ผูก VAT + ใบกำกับภาษี และไม่แยก "มัดจำ" กับ "เงินประกันที่ต้องคืน" | ขาย/ซื้อ | **สูง** | ป.73/2541, ม.79 |
| G-02 | ไม่มีเงินประกันผลงาน (Retention) | ขาย/โครงการ | **สูง** | กค 0706/พ.789 |
| G-03 | ไม่มีแผนเรียกเก็บตามงวด/เหตุการณ์ (Progress/Milestone Billing) | ขาย/โครงการ | **สูง** | TFRS 15 |
| G-04 | ไม่มีสัญญาบริการ/บำรุงรักษาเรียกเก็บรายงวดอัตโนมัติ | บริการ | **สูง** | TFRS 15 |
| G-05 | เงินทดรองจ่ายพนักงาน + การเคลียร์ (มีแต่แบบพิมพ์) | เบิกล่วงหน้า | **สูง** | — |
| G-06 | ไม่มีใบรับรองแทนใบเสร็จรับเงิน | เบิกค่าใช้จ่าย/เงินสดย่อย | กลาง | แนวปฏิบัติสรรพากร |
| G-07 | ไม่มีนโยบาย/วงเงินเบี้ยเลี้ยง | เบิกค่าใช้จ่าย | กลาง | ม.42(3) |
| G-08 | ไม่มีค่าเผื่อหนี้สงสัยจะสูญ + ตัดหนี้สูญ | AR | กลาง | ฎ.186 (2534), TFRS 9 |
| G-09 | ไม่พบแบบ ภ.พ.30 (ตรวจสอบ) | บัญชี | กลาง | ม.83 |
| G-10 | ไม่รับ e-Tax Invoice ฝั่งซื้อ (XML) | ซื้อ/บัญชี | กลาง | ระเบียบ RD e-Tax |
| G-11 | สัญญาซื้อระยะยาว / Blanket / ผู้รับเหมาช่วง | ซื้อ | กลาง | — |
| G-12 | Timesheet → Invoice งานบริการ/โครงการ (ตรวจสอบ) | บริการ/โครงการ | กลาง | — |
| G-13 | วงเงินเครดิตแบบ rolling + hold จาก aging | ขาย | ต่ำ-กลาง | internal control |
| G-14 | TFRS 15 revenue schedule | บัญชี | กลาง | TFRS 15 |
| G-15 | ต่ออายุสัญญา/แจ้งเตือนหมดอายุ | สัญญา | ต่ำ | — |

---

## 5. ประเด็นไทยเฉพาะ — สถานะ (สรุป)

| ประเด็น | สถานะ |
|---|---|
| หนังสือรับรองหักภาษี ณ ที่จ่าย (50 ทวิ) | ครอบคลุม (`wht_certificate.xml`) |
| ภ.ง.ด.3 / 53 / 54 | ครอบคลุม |
| ภ.ง.ด.50 / 51, TAS 12, NPAE, ส.บช.3 | ครอบคลุม |
| ภาษีซื้อต้องห้าม (ม.82/5) / Reverse charge | ครอบคลุม (tax data) |
| ภาษีธุรกิจเฉพาะ (SBT) + ภ.ธ.40 | ครอบคลุม (PP40) |
| อากรแสตมป์ | ครอบคลุม |
| e-Tax Invoice / e-Receipt (ขมธอ.3-2560 + XAdES) | ครอบคลุม (ขาออก) |
| e-Withholding | ครอบคลุม |
| **เงินมัดจำ + VAT** | **ยังขาด** |
| **เงินประกันผลงาน + ใบกำกับเต็มจำนวน** | **ยังขาด** |
| **ใบรับรองแทนใบเสร็จรับเงิน** | **ยังขาด** |
| **ภ.พ.30 (แบบยื่น)** | ยังไม่ยืนยัน |
| **e-Tax Invoice ฝั่งซื้อ** | **ยังขาด** |

---

## 6. แหล่งอ้างอิง (แหล่งไทยที่น่าเชื่อถือ)

**Primary – หน่วยงานรัฐ / สถาบันวิชาชีพ**
- ป.73/2541 เงินจ่ายล่วงหน้า/เงินประกัน/เงินมัดจำ — https://www.rd.go.th/3580.html
- ป.80/2542 ใบเพิ่มหนี้/ใบลดหนี้ — https://rd.go.th/3574.html
- ท.ป.4/2528 อัตราภาษีหัก ณ ที่จ่าย — https://rd.go.th/3479.html
- ระบบงาน WHT + กำหนดนำส่ง — https://www.rd.go.th/62977.html
- คู่มือ 50 ทวิ (ป.อ. ฉบับที่ 186) — https://www.rd.go.th/fileadmin/images/image_law/images/guide100248.pdf
- ใบกำกับภาษี (VAT 360) — https://www.rd.go.th/fileadmin/user_upload/SMEs/infographic/13-1.vat_360.pdf
- ภาษีธุรกิจเฉพาะ ม.91/5 — https://www.rd.go.th/5204.html
- เงินประกันผลงาน (Retention) — https://www.rd.go.th/37665.html
- เงินได้ยกเว้นภาษี ม.42 — https://www.rd.go.th/fileadmin/borkor/taxreturn23072567.pdf
- คู่มือ TFRS 15 (สภาวิชาชีพบัญชี) — https://acpro-std.tfac.or.th/uploads/files/TFRS15-Manual.pdf
- มาตรฐาน e-Tax Invoice ขมธอ.3-2560 (ETDA) — https://standard.etda.or.th/
- e-Tax Invoice สำหรับ SMEs (ETDA) — https://www.etda.or.th/th/Useful-Resource/e-Tax-Invoice_smes.aspx
- DBD e-Filing งบการเงิน — https://www.dbd.go.th/news/17226032569
- Odoo 19 Thailand Localization — https://www.odoo.com/documentation/19.0/applications/finance/fiscal_localizations/thailand.html
- OCA l10n-thailand — https://github.com/OCA/l10n-thailand

**Secondary – ใช้ยืนยันวิธีปฏิบัติ**
- หนี้สูญ/ตัดจำหน่าย ฎ.186 (Forvis Mazars) — https://www.forvismazars.com/th/en/insights/doing-business-in-thailand/tax/write-it-off-as-a-tax-deductible-expense
- ภาษีซื้อต้องห้าม ม.82/5 — https://www.uniginventures.com/articles/non-creditable-input-vat-thailand
- เงินสดย่อยแบบ Imprest — https://wp.peakaccount.com/blog/accounting/gen-acct/petty-cash-advance-payment
