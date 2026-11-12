# เอกสารออกแบบ: SP2 — Navigation & Information Architecture (Website Refresh)

- **วันที่:** 2026-11-11
- **โครงการแม่:** Website Refresh (Plan C — 8 Sub-projects)
- **Sub-project:** SP2 — Navigation & Information Architecture
- **สถานะ:** อนุมัติแล้ว (Approved)
- **โมดูลเป้าหมาย:** `od19_website`
- **Branch:** `feature/od19_website-refresh-sp1` (ต่อจาก SP1)
- **AGENT_ID:** `trae-od19_uid`

---

## 1. บทสรุป (Summary)

SP2 ปรับ **โครงสร้างการนำทาง (Navigation)** และ **สถาปัตยกรรมสารสนเทศ (Information Architecture)** ของเว็บไซต์ Auto-Info ให้ชัดเจน แยก "ผู้ชมภายนอก (ลูกค้า)" ออกจาก "ผู้ใช้ภายใน (พนักงาน)" และทำให้ผู้ใช้รู้ตำแหน่งของตนบนเว็บได้เสมอผ่าน breadcrumb

SP1 ทำ "แบรนด์" (โลโก้, 404) → SP2 ทำ "โครง" (เมนู, ผังหน้า, breadcrumb)

---

## 2. ปัญหาและเป้าหมาย (Problem and Goal)

### 2.1 ปัญหาปัจจุบัน

1. **"Employee Portal" อยู่ในเมนูหลักสาธารณะ** (sequence 70)
   - หน้า `/employee-portal` เป็น `auth="user"` — ผู้เยี่ยมชมทั่วไปกดแล้วถูกเด้งไปหน้า login
   - ทำให้เมนูลูกค้าสับสน และไม่สอดคล้องหลัก "ลดความซ้ำซ้อนของเมนู / จัดกลุ่มตามฟังก์ชัน"
   - มีทางเข้าอื่นอยู่แล้วคือ systray shortcut (`od19_shortcut_menu.js`) และการ redirect หลัง login

2. **Breadcrumb ไม่สม่ำเสมอ**
   - มีเฉพาะหน้า Careers (detail / apply) 3 จุด
   - หน้าอื่น (Services 3 หน้า, Products, About) ไม่มี breadcrumb
   - CSS `.od19-breadcrumb` และสไตล์พร้อมใช้แล้ว (ขาวบน hero มืด) แต่ไม่ได้ถูกใช้

3. **ไม่มีการระบุผัง IA อย่างเป็นทางการ** — ลำดับเมนูและเหตุผลไม่ถูกบันทึก

### 2.2 เป้าหมาย

- แยกเมนูสาธารณะ (ลูกค้า) ออกจากพื้นที่พนักงานอย่างชัดเจน
- ให้ทุกหน้าเนื้อหาภายในมี breadcrumb สม่ำเสมอ ชี้ทางกลับหน้าแรก
- บันทึกผัง IA กลางไว้ในเอกสารนี้เพื่ออ้างอิงใน SP ถัดไป

---

## 3. ผัง IA เป้าหมาย (Target Information Architecture)

### 3.1 เมนูหลักสาธารณะ (Top Navigation) — 7 รายการ

| ลำดับ | ชื่อเมนู | URL | ประเภท |
|---|---|---|---|
| 10 | Home | `/` | หน้าแรก |
| 20 | Services ▾ | `#` | dropdown |
| 20.10 | — Industrial Automation | `/industrial-automation` | เอกสาร |
| 20.20 | — Building Automation | `/building-automation` | เอกสาร |
| 20.30 | — Terminal Automation | `/terminal-automation` | เอกสาร |
| 30 | Products | `/products` | แคตตาล็อก |
| 40 | About | `/about-us` | บริษัท |
| 45 | Careers | `/careers` | ร่วมงาน |
| 50 | News & Events | `/blog` | ข่าว |
| 60 | Contact | `/contactus` | ติดต่อ |

> **เปลี่ยนจากเดิม:** ตัด `Employee Portal` (70) ออกจากเมนูหลักสาธารณะ

### 3.2 พื้นที่พนักงาน (Staff Access)

| ช่องทาง | ที่อยู่ | หมายเหตุ |
|---|---|---|
| Footer link (ใหม่) | แถบล่างของ footer → `/employee-portal` | มีไอคอนกุญแจ แยกจากเมนูลูกค้า |
| Systray shortcut (เดิม) | ไอคอน ⚡ บน backend | `od19_shortcut_menu.js` |
| Auto-redirect (เดิม) | หลัง login (employee) | `/employee-portal` |

### 3.3 Breadcrumb (ลำดับชั้น)

| หน้า | Breadcrumb |
|---|---|
| Industrial Automation | Home › Services › Industrial Automation |
| Building Automation | Home › Services › Building Automation |
| Terminal Automation | Home › Services › Terminal Automation |
| Products | Home › Products |
| About Us | Home › About |
| Careers / Job detail / Apply | (มีอยู่แล้ว) Home › Careers › … |

---

## 4. การเปลี่ยนแปลงเชิงเทคนิค (Implementation Outline)

1. **`data/website_menus.xml`** — ลบ `<record id="menu_employee_portal">` ออก
2. **`models/website_menu.py`** — เพิ่มขั้นตอนใน `od19_configure_menus()` ลบเมนู `Employee Portal` ระดับบนสุดที่ค้างใน DB (อ้างด้วย XML ID `od19_website.menu_employee_portal`) พร้อม cascade guard (detach จาก `main_menu` ก่อน `unlink`) เพื่อรองรับ DB ที่ upgrade มาจาก SP1 และกันการลบเมนูอื่นที่ใช้ URL เดียวกัน
3. **`views/website_templates.xml`** — เพิ่มลิงก์ `Employee Portal` แบบ discret ในแถบล่าง footer
4. **`static/src/css/od19_website.css`** — เพิ่มสไตล์ `.od19-footer-staff` + `.od19-footer-sep`
5. **`views/services_pages.xml`** — เพิ่ม `<nav class="od19-breadcrumb">` ใน hero ของ industrial / building / terminal
6. **`views/products_page.xml`** — เพิ่ม breadcrumb ใน hero (`.od19-pc-hero`)
7. **`views/about_page.xml`** — เพิ่ม breadcrumb ใน hero
8. **`tests/test_website.py`** — เพิ่มคลาส `TestNavigationIA` (HttpCase)

---

## 5. เกณฑ์ยอมรับ (Acceptance Criteria)

- [ ] เมนูหลักสาธารณะไม่มี "Employee Portal" (`/employee-portal` ไม่ปรากฏเป็นเมนูบน navbar)
- [ ] Footer มีลิงก์ "Employee Portal" ชี้ `/employee-portal`
- [ ] หน้า `/industrial-automation`, `/building-automation`, `/terminal-automation`, `/products`, `/about-us` แสดง `od19-breadcrumb` พร้อมลิงก์กลับ `href="/"`
- [ ] Breadcrumb ใช้สไตล์เดิม `.od19-breadcrumb` (ขาวบน hero มืด) — ไม่มี CSS ใหม่สำหรับ breadcrumb
- [ ] `od19_configure_menus()` เป็น idempotent (รันซ้ำได้ไม่พัง) และไม่ลบเมนูของตัวเอง
- [ ] รัน unit test `od19_website` ผ่าน 0 failed / 0 error

---

## 6. สิ่งที่ไม่ทำใน SP2 (Out of Scope)

- ไม่เพิ่ม/ลบ "หน้าเนื้อหา" ใหม่ (เนื้อหาเป็นของ SP3/SP4/SP5)
- ไม่แตะ meta/OG/sitemap/analytics (SP7 — SEO & Analytics)
- ไม่แตะ privacy policy / cookie consent (SP8 — PDPA & Legal)
- ไม่แตะ Trust & References (SP5)
- ไม่แก้ไข core Odoo (`odoo/`, `addons/`)
- ไม่เปลี่ยนสี/ฟอนต์ (ยึด SP1)

---

## 7. ความสอดคล้องกับมาตรฐานโปรเจกต์

- เปลี่ยนแปลงเฉพาะใน `custom_addons/od19_website/`
- ใช้ PowerShell 7 + `run-tests.ps1 -Module od19_website` บน DB ส่วนตัว `odoo19_t_trae-od19_uid`
- dbfilter ต้องเจาะจงฐานข้อมูลเดียว: `^odoo19_t_trae.od19_uid$`
- Conventional commit: `feat(website): SP2 navigation and information architecture`
