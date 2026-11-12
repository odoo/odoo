# SP5 — Trust & References (od19_website)

- **Module**: `od19_website`
- **Branch**: `feature/od19_website-refresh-sp1`
- **AGENT_ID**: `trae-od19_uid`
- **Date**: 2026-11-11
- **Roadmap**: Website Refresh Plan C, sub-project 5 of 8

## 1. Summary

รวมเนื้อหา **ความน่าเชื่อถือ (Trust)** และ **ผลงานอ้างอิง (References)** ให้เป็นระบบ — จากเดิมที่มีเพียง chip strip กระจัดกระจายในหน้า Home/About และไม่มีหน้าผลงานให้ลูกค้า B2B ตรวจสอบ

ขอบเขตคือ:
1. หน้าใหม่ **`/quality-certifications`** — ใบรับรอง (ISO 9001:2015 ที่มีจริง, ISO 14001 ที่กำลังเตรียม) + GMP / CSV + รายละเอียด certification body ที่กรอกได้จากหลังบ้าน
2. หน้าใหม่ **`/portfolio`** — โครงการอ้างอิง 9 รายการ 3 โดเมน พร้อม filter ตามโดเมน
3. เชื่อมโยง trust content: homepage trust band, about page standards section, footer links และเมนูบน top-nav

## 2. Problem / Goal

**ปัญหา**
- ข้อมูล ISO / GMP / CSV กระจายเป็น chip ไม่มีหน้าเฉพาะที่ลูกค้าใช้ตรวจสอบได้
- ไม่มีหน้าผลงานอ้างอิง (portfolio) ซึ่งเป็นหลักฐานสำคัญในการตัดสินใจของลูกค้า B2B
- ชื่อ certification body (SGS / UKAS) ไม่มีที่ให้ผู้ดูแลเว็บกรอกจริง และ hardcode ไม่ได้เพราะข้อมูลจริงเปลี่ยนได้

**เป้าหมาย**
- มีหน้า trust ที่ให้ข้อมูลครบ (สถานะใบรับรอง, ขอบเขต, ขั้นตอนคุณภาพ)
- มีหน้าผลงานที่กรองตามโดเมนได้ใน 1 คลิก
- ข้อมูลใบรับรอง (body / เลขที่ / วันหมดอายุ) ตั้งค่าจากหลังบ้านได้ ไม่ฝังในโค้ด

## 3. Implementation Outline

### 3.1 Data single source — `models/website.py`
- `OD19_CERTIFICATIONS` — 4 dicts (`key`, `icon`, `title`, `subtitle`, `status`, `status_label`, `desc`, `points`)
- `OD19_ACCREDITATIONS` — list ของชื่อมาตรฐาน/กรอบที่ทำงานด้วย
- `OD19_PROJECT_REFERENCES` — 9 dicts (`sector`, `year`, `title`, `scope`, `detail`, `img`)
- methods `Website.od19_certifications()`, `Website.od19_accreditations()`, `Website.od19_projects()`

### 3.2 Company fields — `models/res_company.py` + `views/res_company_views.xml`
- `od19_website_cert_body` (Char), `od19_website_cert_no` (Char), `od19_website_cert_valid_until` (Date)
- เพิ่ม group "Certification" ในหน้า Company → Website
- หน้าบ้านแสดงรายละเอียดเฉพาะเมื่อมีค่า; ถ้าไม่มีให้แสดงข้อความ "Contact us for the current certificate"

### 3.3 Quality page — `views/quality_page.xml` (ใหม่)
Hero → Certification cards (4) → Accreditation strip → Quality assurance process (4 steps) → Certification details (configurable) → CTA

### 3.4 Portfolio page — `views/portfolio_page.xml` (ใหม่)
Hero (+ hero stats) → Sector filter pills → Project grid (9) → Stats → CTA

### 3.5 Pages & menus
- `data/website_pages.xml` — 2 `website.page` records (`/quality-certifications`, `/portfolio`)
- `data/website_menus.xml` — `menu_quality` (sequence 35), `menu_portfolio` (sequence 42)

### 3.6 Cross-links
- `views/homepage.xml` — เปลี่ยน partner strip เป็น section "Quality & Certifications" ที่มีลิงก์ไป `/quality-certifications`
- `views/about_page.xml` — "Technology & Standards" เพิ่มปุ่มลิงก์ไป `/quality-certifications` และ `/portfolio`
- `views/website_templates.xml` — footer "Company" เพิ่ม Quality & Certifications, References

### 3.7 Styles — `static/src/css/od19_website.css`
- `.od19-cert-grid` / `.od19-cert-card` / `.od19-cert-status` (badge ตามสถานะ) / `.od19-cert-points`
- `.od19-accred-strip`
- `.od19-proj-grid` / `.od19-proj-card` / `.od19-proj-media` / `.od19-proj-sector` / `.od19-proj-year`
- responsive + เคารพ `prefers-reduced-motion`

### 3.8 Tests — `tests/test_website.py`
- `TestTrustReferencesSP5` (HttpCase): 5 เทสต์

## 4. Acceptance Criteria

- [ ] `website.od19_certifications()` คืน 4 รายการ และ `od19_projects()` คืน 9 รายการ (industrial 3 / building 3 / terminal 3)
- [ ] `/quality-certifications` แสดงการ์ด `.od19-cert-card` ≥ 4 ใบ, มีข้อความ `ISO 9001:2015` และ `ISO 14001`
- [ ] `/quality-certifications` แสดง `.od19-cert-body` / `.od19-cert-no` เมื่อ company field มีค่า
- [ ] `/portfolio` แสดง `.od19-proj-card` 9 ใบ, filter pill 4 ปุ่ม (all/industrial/building/terminal) พร้อมตัวเลข
- [ ] หน้า Home และ About มีลิงก์ไป `/quality-certifications`; footer มีลิงก์ทั้ง 2 หน้าใหม่
- [ ] หน้าใหม่มี breadcrumb (สอดคล้อง `TestNavigationIA.test_inner_pages_have_breadcrumb`)
- [ ] เทสต์ `TestTrustReferencesSP5` ผ่านทั้งหมด, ชุดเทสต์เดิมไม่ regression (0 failed / 0 error)

## 5. Out of Scope

- ฟอร์มขอสำเนาใบรับรอง / RFQ รายสินค้า → **SP6**
- SEO meta / schema.org ของหน้าใหม่ → **SP7**
- PDPA consent / cookie banner → **SP8**
- การอัปโหลดไฟล์ PDF ใบรับรองจริงจากหลังบ้าน (ใช้ company field + คำเชิญติดต่อก่อน)

## 6. Standards

- Odoo 19 CE community conventions (`website`, QWeb)
- ไม่แก้ core; เฉพาะ `custom_addons/od19_website`
- Conventional Commit: `feat(website): SP5 trust and references`
- TDD: เขียนเทสต์คู่กับการ implement; รัน `-u od19_website` บน DB ทดสอบส่วนตัว
- เนื้อหาโครงการอ้างอิงเป็น **illustrative** (ไม่ระบุชื่อลูกค้า) — ต้องแทนที่ด้วยข้อมูลจริงก่อน go-live (SP8)
