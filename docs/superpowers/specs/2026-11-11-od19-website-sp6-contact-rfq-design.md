# SP6 — Contact & RFQ (od19_website)

- **Module**: `od19_website`
- **Branch**: `feature/od19_website-refresh-sp1`
- **AGENT_ID**: `trae-od19_uid`
- **Date**: 2026-11-11
- **Roadmap**: Website Refresh Plan C, sub-project 6 of 8

## 1. Summary

เปลี่ยนหน้ายื่นคำขอ (`/contactus`) จากฟอร์มกระดาษเปล่าของ Odoo ให้เป็น **ฟอร์ม Request for Quotation (RFQ) ที่มีโครงสร้าง** ซึ่งสร้าง `crm.lead` จริง ผ่านกลไก `website_form` ของ Odoo และ **จัดเส้นทาง (route) ตามประเภทคำขอ** ไปยัง Sales Team / Tag ที่ถูกต้อง พร้อมหน้า thank-you ที่ติดแบรนด์

ขอบเขตคือ:
1. ฟอร์ม RFQ แบบมีโครงสร้างบน `/contactus` (ประเภทคำขอ + สินค้าที่สนใจ + ข้อมูลติดต่อ + ข้อความ + ความยินยอม)
2. การ route อัตโนมัติ: ประเภทคำขอ → `crm.team` (ถ้ามีทีมชื่อตรง) + `crm.tag`
3. หน้า **thank-you** ที่ติดแบรนด์ แทนหน้า default ที่ยังมีที่อยู่ปลอม "3575 Fake Buena Vista Avenue"

## 2. Problem / Goal

**ปัญหา**
- ฟอร์มบน `/contactus` เป็นฟอร์ม default ที่ post ไปที่ `mail.mail` (ส่งอีเมล) ไม่ได้สร้าง opportunity ใน CRM
- ไม่มีโครงสร้างข้อมูล — ฝ่ายขายไม่รู้ว่าผู้ติดต่อต้องการใบเสนอราคา บริการ อะไหล่ หรือขอสำเนาใบรับรอง
- ไม่มีเส้นทาง (routing) ไปยังทีมที่รับผิดชอบ
- หน้า thank-you ของ Odoo ยังแสดงข้อมูลบริษัทปลอม ทำให้เว็บดูไม่น่าเชื่อถือ

**เป้าหมาย**
- ทุกคำขอจากเว็บกลายเป็น `crm.lead` ที่มีข้อมูลครบและจัดเส้นทางแล้ว
- เพิ่มประเภทคำขอ "ขอสำเนาใบรับรอง" และ "RFQ รายสินค้า" (ต่อจาก SP5 Out of Scope)
- หน้า thank-you ที่สะอาด ติดแบรนด์ และไม่มีข้อมูลปลอม

## 3. Implementation Outline

### 3.1 Data single source — `models/website.py`
- `OD19_ENQUIRY_TYPES` — 7 dicts (`key`, `label`, `team`, `tag`)
  - quotation / product / service / spare_part / certificate / career / other
- method `Website.od19_enquiry_types()`

### 3.2 RFQ routing — `models/crm_lead.py` (ใหม่)
- `_inherit = "crm.lead"`
- override `website_form_input_filter(request, values)`:
  - เรียก `super()` ก่อน (ได้ medium/team/user/type ตามปกติ)
  - อ่าน `request.params.get("Enquiry Type")` → map ด้วย `OD19_ENQUIRY_TYPES`
  - ตั้ง `team_id` เมื่อมี `crm.team` ชื่อตรง (ไม่งั้นคงค่า default ของเว็บไซต์)
  - get-or-create `crm.tag` แล้วผูกกับ `tag_ids`
  - ตั้ง `name` (subject) ถ้าผู้ใช้ไม่ได้ให้มา: `"Website RFQ — <label>"`
- `models/__init__.py` — import `crm_lead`

### 3.3 Contact page — `views/contact_page.xml`
- แทน `<form id="contactus_form">` เดิม (ที่ post ไป `mail.mail`) ด้วยฟอร์ม RFQ ที่ติดแบรนด์
  - `data-model_name="crm.lead"`, `data-success-mode="redirect"`, `data-success-page="/contactus-thank-you"`
  - ฟิลด์: Full name, Company, Email, Phone, **Enquiry Type** (select), **Product of Interest** (select), How can we help (textarea), PDPA consent (checkbox)
- ฟิลด์ select ใช้ข้อมูลจาก `od19_enquiry_types()` และ `od19_products()`

### 3.4 Thank-you page — `views/contact_page.xml`
- inherit `website.contactus_thanks` — แทนคอลัมน์ "My Company" ที่เป็นข้อมูลปลอมด้วยข้อมูล Auto-Info จริง + ติดแบรนด์ข้อความ

### 3.5 Styles — `static/src/css/od19_website.css`
- `.od19-rfq-form` / `.od19-rfq-*` — ระยะห่าง, label, select, consent row, ปุ่ม submit
- responsive + ไม่พึ่ง animation

### 3.6 Tests — `tests/test_website.py`
- `TestContactRFQSP6` (HttpCase): 5 เทสต์

## 4. Acceptance Criteria

- [ ] `website.od19_enquiry_types()` คืน 7 รายการ และมี key ครบ (quotation, product, service, spare_part, certificate, career, other)
- [ ] `/contactus` มี `data-model_name="crm.lead"`, `data-success-page="/contactus-thank-you"`, คลาส `od19-rfq-form`, และ `<select name="Enquiry Type">` ที่มี option ครบ 7
- [ ] `/contactus` มี `<select name="Product of Interest">` ที่มี option ครบตาม catalog
- [ ] POST `/website/form/crm.lead` สร้าง `crm.lead` จริง: `contact_name`, `email_from` ตรง, `description` มีข้อความ + ประเภทคำขอ
- [ ] ประเภทคำขอ `service` ที่มี `crm.team` ชื่อ "Service" → lead ถูก route เข้าทีมนั้น และมี tag "Website: Service"
- [ ] `/contactus-thank-you` ไม่มีข้อความ "3575 Fake Buena Vista Avenue" และแสดงข้อมูล Auto-Info
- [ ] เทสต์ `TestContactRFQSP6` ผ่านทั้งหมด, ชุดเทสต์เดิมไม่ regression (0 failed / 0 error)

## 5. Out of Scope

- SEO meta / schema.org ของหน้า contact → **SP7**
- PDPA consent log ฉบับเต็ม / cookie banner → **SP8** (SP6 เก็บเฉพาะ checkbox ยินยอมในฟอร์ม)
- การสร้าง `crm.team` อัตโนมัติ — ใช้ทีมที่มีอยู่ ถ้าไม่มีให้ fallback เป็นทีม default ของเว็บไซต์
- การแนบไฟล์ในฟอร์ม RFQ

## 6. Standards

- Odoo 19 CE community conventions (`website`, `website_crm`, QWeb, `website_form`)
- ไม่แก้ core; เฉพาะ `custom_addons/od19_website`
- Conventional Commit: `feat(website): SP6 contact and rfq`
- TDD: เขียนเทสต์คู่กับการ implement; รัน `-u od19_website` บน DB ทดสอบส่วนตัว
- ใช้ชื่อฟิลด์กำหนดเองนำหน้าด้วย `od19_` (ซ่อนในโหมดปกติ) และคงคลาส `s_website_form_*` เพื่อให้แก้ใน Website Builder ได้
