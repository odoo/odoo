# เอกสารออกแบบ: SP3 — Homepage & Hero Refinement (Website Refresh)

- **วันที่:** 2026-11-11
- **โครงการแม่:** Website Refresh (Plan C — 8 Sub-projects)
- **Sub-project:** SP3 — Homepage & Hero Refinement
- **สถานะ:** อนุมัติแล้ว (Approved)
- **โมดูลเป้าหมาย:** `od19_website`
- **Branch:** `feature/od19_website-refresh-sp1` (ต่อจาก SP1/SP2)
- **AGENT_ID:** `trae-od19_uid`

---

## 1. บทสรุป (Summary)

SP3 ยกระดับ **หน้าแรก (Homepage)** จากหน้าโบรชัวร์แบบคงที่เป็นหน้าปิดการขายที่มีลำดับชั้นชัดเจน: hero ที่ทรงพลังขึ้น เล่าเรื่อง "เราทำงานอย่างไร" ครบวงจร และมีตัวเลขผลงานที่ขยับได้จริง (animated counters) — ทั้งหมดทำงานแบบ **offline-first** และเคารพ `prefers-reduced-motion`

SP1 = แบรนด์, SP2 = โครง/เมนู, **SP3 = หน้าแรก (เนื้อหา + ปฏิสัมพันธ์)**

---

## 2. ปัญหาและเป้าหมาย (Problem and Goal)

### 2.1 ปัญหาปัจจุบัน

1. **Hero อยู่กับที่ (static)** — ตัวอักษรและปุ่มลอยบนพื้นหลังทึบ ไม่มีจุดนำสายตาให้เลื่อนลง ไม่มีสัญญาณ "มีอะไรต่อ" ด้านล่าง
2. **CTA รองชี้ผิดบริบท** — ปุ่มรอง "Learn More" พาไป `/about-us` ทั้งที่สิ่งที่ผู้เยี่ยมชมควรเห็นต่อคือ "บริการ" ที่อยู่ถัดลงไปทันที
3. **ไม่มีเรื่องราว "ขั้นตอนการทำงาน"** — หน้าแรกกระโดดจาก "บริการ 3 การ์ด" ไป "ทำไมต้อง Auto-Info" โดยไม่มีคำตอบว่า *เริ่มต้นอย่างไร จบอย่างไร*
4. **ตัวเลขผลงาน (Stats) นิ่ง** — `20+ / 3 / 100% / 1M+` แสดงค่าสุดท้ายทันที ไม่มีจังหวะดึงความสนใจและไม่รู้สึก "มีชีวิต"
5. **ไม่มี anchor สำหรับ deep-link ภายในหน้า** — มีเพียง `#services` ทำให้ปุ่ม/แคมเปญภายนอกอ้างอิง section อื่นไม่ได้

### 2.2 เป้าหมาย

- Hero มีลำดับชั้นชัด (eyebrow → h1 → lead → CTA → proof) + มี cue ให้เลื่อนลง
- เพิ่ม section **"How We Work"** 4 ขั้นตอน ระหว่าง Services และ Why Auto-Info เพื่อปิดช่องว่างของเรื่องราว
- ทำให้ Stats ขยับแบบ count-up เมื่อเลื่อนถึง (และไม่ขยับถ้าผู้ใช้ปิดอนิเมชัน)
- เพิ่ม anchor ID ให้ทุก section หลักของหน้าแรกเพื่อ deep-link ได้
- ไม่เพิ่มไลบรารีภายนอก, ไม่กระทบความเร็ว, ไม่แก้ core Odoo

---

## 3. การเปลี่ยนแปลงเชิงเทคนิค (Implementation Outline)

1. **`views/homepage.xml`**
   - Hero: เพิ่ม `<div class="od19-hero-sheen" aria-hidden="true"/>` (ชั้นแสงเคลื่อนไหว), ปุ่มรองเปลี่ยนเป็น `#services` ("Explore Services"), เพิ่ม `<a class="od19-hero-scroll" href="#services">` (cue เลื่อนลง)
   - เพิ่ม section ใหม่ `id="how-we-work"` ใช้สไตล์เดิม `.od19-steps` / `.od19-step` / `.od19-step-num` (4 ขั้น: Consult & Survey → Design & Engineer → Implement & Commission → Support & Improve) วางระหว่าง Services และ Why Auto-Info
   - Stats: เพิ่ม `data-od19-count` + `data-od19-suffix` ให้ `.od19-stat-number` ทั้ง 4 ตัว (เปิดให้ JS ทำ count-up)
   - เพิ่ม anchor ID: `id="about"` (Why Auto-Info), `id="how-we-work"`, `id="products"` (Featured), `id="partners"`, `id="news"`, `id="careers"`, `id="contact"` (CTA) — `#services` มีอยู่แล้ว
2. **`static/src/css/od19_website.css`**
   - เพิ่มสไตล์ `.od19-hero-sheen` + `@keyframes od19-sheen`, `.od19-hero-scroll` + `@keyframes od19-bob`
   - เพิ่ม `@media (prefers-reduced-motion: reduce)` ปิดอนิเมชันของ sheen/scroll cue
   - ซ่อน scroll cue บนจอเล็ก (`max-width: 767.98px`)
   - **ไม่แตะ** สี/ฟอนต์ (ยึด SP1) และ**ไม่แตะ** `.od19-breadcrumb`
3. **`static/src/js/od19_home.js`** (ไฟล์ใหม่)
   - Animated counters: เลือก `.od19-stat-number[data-od19-count]` → IntersectionObserver (threshold 0.4) → count-up ด้วย `requestAnimationFrame` + easing
   - `prefers-reduced-motion: reduce` → ตั้งค่าสุดท้ายทันที ไม่มีอนิเมชัน
   - ไม่มี IntersectionObserver → ตั้งค่าสุดท้ายทันที (fallback)
   - กันการเห็นค่า flash: ตั้งข้อความเป็น `0` + suffix ก่อนเริ่ม observe
4. **`__manifest__.py`** — เพิ่ม `od19_website/static/src/js/od19_home.js` ใน `web.assets_frontend`
5. **`tests/test_website.py`** — เพิ่มคลาส `TestHomepageSP3` (HttpCase, 4 เทสต์)

---

## 4. ผังส่วน (Section Order) ของหน้าแรกหลัง SP3

| # | Section | Anchors | พื้นหลัง |
|---|---|---|---|
| 1 | Hero | — | maroon gradient + hero image + sheen |
| 2 | Service & Solutions | `#services` | `bg-light` |
| 3 | **How We Work (ใหม่)** | `#how-we-work` | `bg-light` |
| 4 | Why Auto-Info | `#about` | ขาว |
| 5 | Featured Products | `#products` | ขาว |
| 6 | Technology Partners | `#partners` | ขาว (`pt-0`) |
| 7 | Stats (count-up) | — | ดำ (`od19-stats`) |
| 8 | News & Events | `#news` | `bg-light` |
| 9 | Careers teaser | `#careers` | ขาว |
| 10 | CTA | `#contact` | maroon |

> จังหวะพื้นหลังสลับ ขาว/light/dark เพื่อให้อ่านง่าย (สอดคล้องหลัก UI/UX ของโปรเจกต์)

---

## 5. เกณฑ์ยอมรับ (Acceptance Criteria)

- [ ] หน้าแรกมี `od19-hero-sheen` (ชั้นแสงเคลื่อนไหว) และ `class="od19-hero-scroll"` ที่ชี้ `href="#services"`
- [ ] ปุ่มรองของ hero ชี้ `#services` (ไม่ใช่ `/about-us`)
- [ ] มี section `id="how-we-work"` และมี `.od19-step-num` 4 อัน
- [ ] `.od19-stat-number` ทั้ง 4 ตัวมี attribute `data-od19-count` (≥ 4)
- [ ] หน้าแรกมี anchor ID ครบ: `services, about, how-we-work, products, partners, news, careers, contact`
- [ ] `od19_home.js` ถูกโหลดใน `web.assets_frontend`
- [ ] เคารพ `prefers-reduced-motion` (ทั้ง CSS และ JS)
- [ ] ไม่แก้ core Odoo, ไม่แตะสี/ฟอนต์/ breadcrumb (SP1/SP2)
- [ ] รัน unit test `od19_website` ผ่าน 0 failed / 0 error

---

## 6. สิ่งที่ไม่ทำใน SP3 (Out of Scope)

- ไม่แก้เนื้อหาแคตตาล็อกสินค้า/หน้ารายละเอียดบริการ (SP4)
- ไม่เพิ่ม ISO/SGS/UKAS certificate + portfolio (SP5 — Trust & References)
- ไม่แตะฟอร์ม RFQ / `crm.lead` (SP6 — Contact & RFQ)
- ไม่แตะ meta/OG/sitemap/schema.org/analytics (SP7 — SEO & Analytics)
- ไม่แตะ privacy policy / cookie consent (SP8 — PDPA & Legal)
- ไม่แก้ไข core Odoo (`odoo/`, `addons/`)

---

## 7. ความสอดคล้องกับมาตรฐานโปรเจกต์

- เปลี่ยนแปลงเฉพาะใน `custom_addons/od19_website/`
- ใช้ PowerShell 7 + รันเทสต์บน DB ส่วนตัว `odoo19_t_trae-od19_uid`
- dbfilter ต้องเจาะจงฐานข้อมูลเดียว: `^odoo19_t_trae.od19_uid$`
- ต้อง robocopy sync worktree `od19_uid` → `odoo19/custom_addons` ก่อนรันเทสต์
- Conventional commit: `feat(website): SP3 homepage and hero refinement`
