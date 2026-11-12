# SP7 — SEO & Analytics (od19_website)

- **Module**: `od19_website`
- **Branch**: `feature/od19_website-refresh-sp1`
- **AGENT_ID**: `trae-od19_uid`
- **Date**: 2026-11-11
- **Roadmap**: Website Refresh Plan C, sub-project 7 of 8

## 1. Summary

ทำให้ทุกหน้าของเว็บไซต์ Auto-Info "พร้อมติด index" โดยใช้กลไก SEO ที่ Odoo 19 CE มีอยู่แล้ว
(`website.seo.metadata` mixin, `website.layout` meta rendering, Google Analytics consent gating)
และเพิ่มสิ่งที่ยังขาด:

1. **Per-page meta** — `website_meta_title` / `website_meta_description` / `website_meta_keywords`
   บนหน้าเว็บหลักทั้ง 8 หน้า (Home, 3 service pages, Products, About, Quality, References)
2. **Organization / WebSite JSON-LD (schema.org)** — ฉีดเข้า `<head>` ทุกหน้าเพื่อให้ได้ rich result
3. **OpenGraph / Twitter defaults** — override `_default_website_meta()` ให้เพิ่ม `og:locale`
   และให้คำอธิบายเริ่มต้น (default meta description) แบรนด์ Auto-Info
4. **Analytics** — ฟิลด์ `od19_website_ga_key` บน `res.company` + ตัวช่วย sync เข้า
   `website.google_analytics_key` (ซึ่ง core render พร้อม consent gating ให้แล้ว)
5. **robots.txt** — ตั้งเนื้อหาเริ่มต้นที่ปิด path ภายใน (`/web/`, `/my/`, `/employee-portal`)

## 2. Problem / Goal

**ปัญหา**
- หน้าเว็บที่สร้างเอง (SP2–SP6) ยังไม่มี `website_meta_title` / description / keywords →
  Google เห็นแค่ชื่อ view ดิบ ๆ และไม่มี meta description ทำให้ CTR ต่ำ
- ไม่มี structured data (schema.org) → ไม่ได้ rich result (ชื่อบริษัท, โลโก้, ที่อยู่, เบอร์โทร)
- OpenGraph ไม่มี `og:locale` ทำให้การแชร์บน social แสดงภาษาไม่ถูกต้อง
- ไม่มีที่กรอก Google Analytics ID ที่เข้าถึงง่ายจากหลังบ้าน (มีแต่หน้า Settings ของ core)
- robots.txt ยังชี้ให้ crawler เก็บหน้า `/web/`, `/my/`, `/employee-portal` ที่ไม่ควร index

**เป้าหมาย**
- ทุกหน้าใน sitemap มี meta title/description/keywords ที่มีความหมาย
- ทุกหน้าใน sitemap emits Organization + WebSite JSON-LD ที่ถูกต้อง
- OG/Twitter tags ครบพร้อม locale
- เปิดใช้ Google Analytics ได้ด้วยการกรอก ID ครั้งเดียว และไหลผ่าน consent gating เดิมของ Odoo
- robots.txt เริ่มต้นที่ปลอดภัย

## 3. Implementation Outline

### 3.1 Company fields — `models/res_company.py`
- `od19_website_ga_key` (Char) — Google Analytics 4 measurement ID (`G-XXXXXXX`), มี help ภาษาไทย

### 3.2 Website model — `models/website.py`
- ค่าคงที่: `OD19_ORG_DESCRIPTION`, `OD19_DEFAULT_ROBOTS`
- `od19_organization_jsonld()` (@api.model) — คืน JSON string (scriptsafe) ของ
  `Organization` (name, url, logo, description, address, contactPoint, sameAs จาก social fields)
  และ `WebSite` (name, url, `potentialAction` = SearchAction → `/website/search?search={q}`)
- `od19_setup_seo()` (@api.model) — idempotent:
  - sync `company.od19_website_ga_key` → `website.google_analytics_key` (เขียนเฉพาะเมื่อต่าง)
  - ตั้ง `website.robots_txt` = `OD19_DEFAULT_ROBOTS` เมื่อยังว่าง
- override `_default_website_meta()` — เรียก `super()` แล้วเพิ่ม
  `default_opengraph['og:locale']` และ `default_meta_description`

### 3.3 JSON-LD template — `views/seo.xml` (ใหม่)
- `od19_seo_jsonld` — inherit `website.layout`, `<xpath expr="//head" position="inside">`
  → `<script type="application/ld+json" t-out="website.od19_organization_jsonld()"/>`
- ผูกใน `__manifest__.py` `data`

### 3.4 Per-page meta — `data/website_pages.xml`
- เพิ่ม `website_meta_title` / `website_meta_description` / `website_meta_keywords`
  ให้ทั้ง 8 `website.page` records

### 3.5 Backend UI — `views/res_company_views.xml`
- เพิ่มกลุ่ม "SEO & Analytics" ในหน้า Website tab ของ `res.company` พร้อมฟิลด์
  `od19_website_ga_key`

### 3.6 Setup — `data/setup_functions.xml`
- เพิ่ม `<function model="website" name="od19_setup_seo"/>` (replay ทุก `-u`)

### 3.7 Tests — `tests/test_website.py`
- `TestSeoAnalyticsSP7` (HttpCase, `post_install`) — per-page meta, OG/Twitter, JSON-LD,
  robots.txt, sitemap, GA consent-gated script

## 4. Acceptance Criteria

- [ ] ทั้ง 8 `website.page` มี `website_meta_title`, `website_meta_description`,
      `website_meta_keywords` ไม่ว่าง
- [ ] เรนเดอร์ `/` แล้ว `<title>` มีค่าเท่ากับ meta title ของหน้า และมี
      `<meta name="description">` + `<meta name="keywords">`
- [ ] ทุกหน้าใน sitemap emit `<script type="application/ld+json">` ที่มี
      `"@type": "Organization"` และชื่อบริษัท, และ `"@type": "WebSite"`
- [ ] หัวหน้าเว็บมี `property="og:title"`, `og:site_name`, `og:image`, `og:locale`
      และ `name="twitter:card"`
- [ ] `/robots.txt` มี `Disallow: /employee-portal` และ `Sitemap:`
- [ ] `/sitemap.xml` มี `/products`, `/quality-certifications`, `/contactus` (อย่างน้อย static pages)
- [ ] เมื่อตั้ง `website.google_analytics_key` → หน้าเว็บมี script
      `googletagmanager.com/gtag/js?id=...` พร้อม `gtag('consent','default',{...'denied'...})`
- [ ] `od19_setup_seo()` เป็น idempotent (เรียกซ้ำไม่เพิ่ม/ไม่เปลี่ยนค่าเดิม)
- [ ] เทสต์ `TestSeoAnalyticsSP7` ผ่านทั้งหมด และชุดเทสต์เดิมไม่ regression (0 failed / 0 error)

## 5. Out of Scope

- Google Search Console verification meta tag / Bing Webmaster
- Multi-language SEO ของหน้า Careers/Blog ที่เรนเดอร์ผ่าน controller (ยังใช้ค่า default ของ layout)
- PDPA cookie banner ฉบับเต็ม / consent log → **SP8**
- การ generate `sitemap.xml` เพิ่มเติมนอกเหนือจากที่ Odoo ทำอัตโนมัติ
- หน้า 404 / thank-you (ไม่ควรถูก index อยู่แล้วผ่าน `noindex`)

## 6. Standards

- Odoo 19 CE community conventions (`website.layout`, QWeb, `website.seo.metadata`, `scriptsafe` JSON)
- ไม่แก้ core; เฉพาะ `custom_addons/od19_website`
- Conventional Commit: `feat(website): SP7 seo and analytics`
- TDD: เขียนเทสต์คู่กับการ implement; รัน `-u od19_website` บน DB ทดสอบส่วนตัว
  (`odoo19_t_trae-od19_uid`) ด้วย `--db-filter='^odoo19_t_trae-od19_uid$'`
- ชื่อฟิลด์กำหนดเองนำหน้าด้วย `od19_`
