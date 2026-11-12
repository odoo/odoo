# SP8 — PDPA & Legal + Go-Live (od19_website)

- **Module**: `od19_website`
- **Branch**: `feature/od19_website-refresh-sp1`
- **AGENT_ID**: `trae-od19_uid`
- **Date**: 2026-11-11
- **Roadmap**: Website Refresh Plan C, sub-project 8 of 8 (final)

## 1. Summary

ปิดงาน Website Refresh ด้วยชั้น "กฎหมายและการปฏิบัติตาม PDPA" และงานเตรียม go-live
ทั้งนี้เว็บไซต์เก็บข้อมูลส่วนบุคคลอยู่แล้วใน 3 จุด (ฟอร์ม RFQ → `crm.lead`,
ใบสมัครงาน → `od19.job.application`, และ Google Analytics) จึงต้องมี:

1. **Privacy Policy (`/privacy`)** — ประกาศความเป็นส่วนตัวตาม **พ.ร.บ.คุ้มครองข้อมูลส่วนบุคคล
   พ.ศ. 2562 (PDPA)** ระบุฐานทางกฎหมาย (legal basis), ระยะเวลาเก็บรักษา, สิทธิของเจ้าของข้อมูล
   (rights of the data subject), ช่องทางติดต่อ DPO และมาตรการความปลอดภัย
2. **Terms of Use (`/terms`)** — ข้อกำหนดการใช้เว็บไซต์ ทรัพย์สินทางปัญญา และข้อจำกัดความรับผิด
3. **Cookie Policy** — ใช้หน้า `/cookie-policy` ที่ Odoo สร้างให้อัตโนมัติเมื่อเปิด cookie bar
   แล้ว **override เนื้อหา** ให้เป็นฉบับแบรนด์ Auto-Info (ลิงก์ไป `/privacy`, เพิ่มหมวด Analytics
   และช่องทางถอนความยินยอม)
4. **Cookie consent gate** — เปิด `website.cookies_bar` เพื่อให้ความยินยอมเป็นแบบ opt-in
   จริง (จำเป็นต่อการที่ SP7 ไม่โหลด GA ก่อนได้รับความยินยอม)
5. **Footer legal links** — เพิ่มลิงก์ Privacy / Terms / Cookie Policy ในส่วนท้ายเว็บ
6. **Setup hook `od19_setup_pdpa()`** — idempotent: เปิด cookie bar, publish + ตั้ง metadata
   ของหน้าด้านกฎหมาย, และไม่ทับเนื้อหาที่ผู้ดูแลแก้เอง
7. **Go-live** — ตรวจว่า `/privacy` และ `/terms` อยู่ใน sitemap, ไม่ถูก `robots.txt` ปิดกั้น
   และทุกหน้ามี metadata ครบ

## 2. Problem / Goal

**ปัญหา**
- ฟอร์ม RFQ มีลิงก์ `<a href="/privacy">Privacy Policy</a>` (SP6) แต่ **ไม่มีหน้านั้นจริง** → 404
- ไม่มีประกาศความเป็นส่วนตัว/ข้อกำหนดการใช้ → ไม่สอดคล้อง PDPA และขาดความน่าเชื่อถือ
- ยังไม่เปิด cookie bar → ความยินยอมไม่มีจุดเก็บ และ GA (SP7) ถูกมองว่าได้รับความยินยอมแล้ว
- Footer ไม่มีลิงก์กฎหมายให้ผู้เยี่ยมชมเข้าถึงได้

**เป้าหมาย**
- `/privacy` และ `/terms` เป็นหน้าจริง publish แล้ว มี metadata และอยู่ใน sitemap
- `/cookie-policy` มีเนื้อหาแบรนด์ Auto-Info และเชื่อมกับ `/privacy`
- cookie bar เปิดใช้งาน; ความยินยอมเป็น opt-in (essential / all)
- footer มีลิงก์กฎหมายครบ
- `od19_setup_pdpa()` เป็น idempotent, ไม่ทำลายเนื้อหาที่แก้เอง

## 3. Implementation Outline

### 3.1 Legal pages — `views/legal_pages.xml` (ใหม่)
- `od19_privacy_page` — QWeb template หน้า `/privacy` (ใช้ `website.layout`,
  hero `od19-page-hero`, section `od19-section`) ประกอบด้วยหัวข้อ:
  บทนำ, ข้อมูลที่เก็บ, ฐานทางกฎหมาย, วัตถุประสงค์, การเปิดเผย/ผู้ประมวลผลช่วง,
  การโอนข้อมูลข้ามพรมแดน, ระยะเวลาเก็บรักษา, สิทธิของเจ้าของข้อมูล (PDPA มาตรา 30–36),
  ความปลอดภัย, ช่องทางติดต่อ DPO, วันที่มีผล
- `od19_terms_page` — QWeb template หน้า `/terms`: การยอมรับข้อกำหนด, การใช้ที่อนุญาต,
  ทรัพย์สินทางปัญญา, ลิงก์ภายนอก, ข้อจำกัดความรับผิด, กฎหมายที่ใช้บังคับ

### 3.2 Cookie policy overlay — `views/legal_pages.xml`
- `od19_cookie_policy` — inherit `website.cookie_policy`; เพิ่มส่วนท้าย: หมวด Analytics,
  วิธีถอนความยินยอม (ปุ่ม Cookies Preferences) และลิงก์ไป `/privacy`

### 3.3 Footer — `views/website_templates.xml`
- เพิ่มบล็อกลิงก์กฎหมายใน `.od19-footer-bottom` (Privacy Policy · Terms of Use · Cookie Policy)

### 3.4 Pages + metadata — `data/legal_pages.xml` (ใหม่, noupdate="1")
- `website.page` 2 records: `/privacy`, `/terms` (published, indexed) พร้อม
  `website_meta_title/description/keywords`
- ใช้ `noupdate="1"` เพื่อรักษาเนื้อหา/ค่าที่ผู้ดูแลแก้หลังติดตั้ง

### 3.5 Setup hook — `models/website.py`
- `od19_setup_pdpa()` (@api.model) idempotent:
  - เปิด `website.cookies_bar = True` (ทำให้ Odoo สร้าง `/cookie-policy` อัตโนมัติ)
  - publish `/privacy`, `/terms` และตั้ง metadata ให้ `/cookie-policy` (ต้อง index)
  - ไม่เขียนทับ `cookies_bar` ถ้าเปิดอยู่แล้ว
- เพิ่ม `<function model="website" name="od19_setup_pdpa"/>` ใน
  `data/setup_functions.xml`

### 3.6 Manifest — `__manifest__.py`
- เพิ่ม `views/legal_pages.xml` (ก่อน `data/website_pages.xml`) และ
  `data/legal_pages.xml` (หลัง `data/website_pages.xml`)

### 3.7 Tests — `tests/test_website.py`
- `TestPdpaLegalSP8` (HttpCase, `post_install`):
  - `/privacy` และ `/terms` เรนเดอร์ 200 และมีเนื้อหาสาระสำคัญ (PDPA rights, DPO contact)
  - `/privacy` ไม่มีข้อมูลปลอม (`+1 555-555-5556`, `YourCompany`)
  - footer มีลิงก์ `/privacy`, `/terms`, `/cookie-policy`
  - `od19_setup_pdpa()` เปิด cookie bar และสร้าง `/cookie-policy`
  - `/cookie-policy` มีเนื้อหาแบรนด์ + ลิงก์ไป `/privacy`
  - legal pages มี metadata ไม่ว่าง และอยู่ใน `/sitemap.xml`
  - `robots.txt` ไม่ปิดกั้น `/privacy`/`/terms`
  - `od19_setup_pdpa()` idempotent

## 4. Acceptance Criteria

- [ ] `/privacy` และ `/terms` เป็น `website.page` ที่ publish + indexed และ render 200
- [ ] หน้าด้านกฎหมายทั้งสองมี `website_meta_title`/`_description`/`_keywords` ไม่ว่าง
- [ ] `/privacy` มีหัวข้อสิทธิของเจ้าของข้อมูล (PDPA) และช่องทางติดต่อ DPO
- [ ] footer แสดงลิงก์ Privacy Policy, Terms of Use และ Cookie Policy
- [ ] `od19_setup_pdpa()` เปิด `cookies_bar` และมีหน้า `/cookie-policy`
- [ ] `/cookie-policy` มีเนื้อหาแบรนด์ Auto-Info และลิงก์ไป `/privacy`
- [ ] `/sitemap.xml` มี `/privacy` และ `/terms`
- [ ] `/robots.txt` ไม่มี `Disallow: /privacy` หรือ `/terms`
- [ ] `od19_setup_pdpa()` เป็น idempotent (เรียกซ้ำไม่เปลี่ยนค่าเดิม)
- [ ] เทสต์ `TestPdpaLegalSP8` ผ่านทั้งหมด และชุดเทสต์เดิมไม่ regression (0 failed / 0 error)

## 5. Out of Scope

- ระบบเก็บ consent log รายบุคคล / consent versioning (เก็บใน SP8 ถัดไปเมื่อมี requirement)
- การแปลหน้าด้านกฎหมายเป็นภาษาอังกฤษ/ไทยแบบครบถ้วน (ข้อความ EN ก่อน, แปลไทยภายหลัง)
- หน้า Cookie Preferences ขั้นสูง (Odoo ใช้ popup ถอนความยินยอมที่มีอยู่แล้ว)
- DPA (Data Processing Agreement) template สำหรับลูกค้า

## 6. Standards

- Odoo 19 CE community conventions (`website.layout`, QWeb, `website.cookies_bar`)
- ไม่แก้ core; เฉพาะ `custom_addons/od19_website`
- Conventional Commit: `feat(website): SP8 pdpa legal and go-live`
- PDPA (พ.ร.บ.คุ้มครองข้อมูลส่วนบุคคล พ.ศ. 2562) — อ้างอิงสิทธิมาตรา 30–36 และหน้าที่มาตรา 23
- TDD: เขียนเทสต์คู่กับการ implement; รัน `-u od19_website` บน DB ทดสอบส่วนตัว
  (`odoo19_t_trae-od19_uid`) ด้วย `--db-filter='^odoo19_t_trae-od19_uid$'`
- ชื่อฟิลด์/โมเดลกำหนดเองนำหน้าด้วย `od19_`
