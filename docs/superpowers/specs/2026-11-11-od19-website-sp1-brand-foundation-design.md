# เอกสารออกแบบ: SP1 — Foundation & Brand (Website Refresh)

- **วันที่:** 2026-11-11
- **โครงการแม่:** Website Refresh (Plan C — 8 Sub-projects)
- **Sub-project:** SP1 — Foundation & Brand
- **สถานะ:** รอตรวจสอบ (Draft for review)
- **โมดูลเป้าหมาย:** `od19_website`

---

## 1. บทสรุป (Summary)

SP1 เป็นการจัดวางพื้นฐานแบรนด์ของเว็บไซต์ AUTO-INFO ให้สอดคล้องกันเป็นระบบ:
- ยืนยัน `autoinfo_logo.svg` เป็นโลโก้ฉบับจริงทั้งระบบ
- เก็บกวาดไฟล์ทดลองออกแบบโลโก้ที่ค้างอยู่ 17 ไฟล์
- สร้างหน้า 404 แบบมีแบรนด์
- **ไม่** เปลี่ยนสี (`#9E2424`) และฟอนต์ (Sarabun) เพราะมีมาตรฐานใช้งานอยู่แล้ว

---

## 2. ปัญหาและเป้าหมาย (Problem and Goal)

### 2.1 ปัญหาปัจจุบัน

1. โฟลเดอร์ `static/src/img/` มีไฟล์ทดลองโลโก้ค้างอยู่ 17 ไฟล์ (concept / harmony / orbit / soul variants) ทำให้ assets ไม่สะอาดและอาจถูกอ้างอิงโดยไม่ได้ตั้งใจ
2. ไม่มีหน้า 404 แบบมีแบรนด์ — ผู้ใช้ที่พิมพ์ URL ผิดจะเห็นหน้า default ของ Odoo ที่ไม่สอดคล้องกับเอกลักษณ์แบรนด์
3. โลโก้หลักยังไม่ถูกอ้างอิงโดยตรงในเทมเพลต (ดึงจากค่า Website/Company ตามดีฟอลต์)

### 2.2 เป้าหมาย

- ให้มีโลโก้ฉบับเดียวที่ชัดเจนและถูกอ้างอิงทุกที่
- ลบไฟล์ทดลองทั้งหมดออกจาก production assets
- เพิ่มหน้า 404 ที่มีแบรนด์และชี้ทางกลับหน้าแรก

---

## 3. ข้อกำหนดที่ยืนยันแล้ว (Confirmed Requirements)

| หัวข้อ | ข้อกำหนด |
|---|---|
| โลโก้หลัก | `autoinfo_logo.svg` (ตัว A แดง + วงโคจร + ลูกบอล) |
| Favicon | `favicon.svg` (ใช้คงเดิม) |
| การเก็บกวาด | ลบไฟล์ทดลอง 17 ไฟล์ทั้งหมด |
| 404 | หน้า 404 แบบมีแบรนด์ พร้อมลิงก์กลับหน้าแรก |
| สี | คง `#9E2424` (เลือดหมู) ไม่เปลี่ยน |
| ฟอนต์ | คง Sarabun / Noto Sans Thai (จาก `od19_thai_font_support`) ไม่เปลี่ยน |

---

## 4. รายการไฟล์ที่เก็บกวาด

### 4.1 ไฟล์ที่จะลบ (17 ไฟล์)

```
static/src/img/autoinfo_logo_concept_1.jpg
static/src/img/autoinfo_logo_concept_2.jpg
static/src/img/autoinfo_logo_concept_3.jpg
static/src/img/autoinfo_harmony_variant_1.jpg
static/src/img/autoinfo_harmony_variant_2.jpg
static/src/img/autoinfo_harmony_variant_3.jpg
static/src/img/autoinfo_logo_orbit_a.jpg
static/src/img/autoinfo_logo_orbit_b.jpg
static/src/img/autoinfo_logo_orbit_c.jpg
static/src/img/autoinfo_logo_orbit_d.jpg
static/src/img/autoinfo_orbit_variant_1.jpg
static/src/img/autoinfo_orbit_variant_2.jpg
static/src/img/autoinfo_orbit_variant_3.jpg
static/src/img/autoinfo_orbit_variant_4.jpg
static/src/img/autoinfo_soul_variant_1.jpg
static/src/img/autoinfo_soul_variant_2.jpg
static/src/img/autoinfo_soul_variant_3.jpg
```

### 4.2 ไฟล์ที่คงไว้

```
static/src/img/autoinfo_logo.svg      # โลโก้หลัก
static/src/img/autoinfo_logo.jpg      # เวอร์ชัน JPG
static/src/img/favicon.svg            # favicon
static/src/img/about/, content/, hero/, home/, misc/, products/   # รูปที่ใช้จริง
```

---

## 5. สิ่งที่จะดำเนินการ (Implementation Outline)

1. **ลบไฟล์ทดลอง** 17 ไฟล์จาก `static/src/img/`
2. **ตรวจสอบการอ้างอิงโลโก้**: ยืนยันว่า `autoinfo_logo.svg` ถูกใช้เป็นโลโก้หลักใน header/footer ของเว็บสาธารณะและพอร์ทัลพนักงาน (ถ้ายังดึงจากค่า Website ให้เพิ่มการอ้างอิงโดยตรงในเทมเพลตเพื่อความแน่นอน)
3. **สร้างหน้า 404**: เพิ่มเทมเพลต `website_404.xml` ที่ override `website.404` ของ Odoo ด้วยโลโก้ + ข้อความ + ปุ่มกลับหน้าแรก
4. **อัปเดต `__manifest__.py`**: เพิ่มไฟล์ 404 เข้า data list
5. **Unit Test**: เพิ่มเทสต์ตรวจสอบ 404 response และโลโก้ถูกอ้างอิง

---

## 6. เกณฑ์ยอมรับ (Acceptance Criteria)

- [ ] `autoinfo_logo.svg` เป็นโลโก้ที่แสดงผลบน header ของทุกหน้าเว็บสาธารณะ
- [ ] ไฟล์ทดลอง 17 ไฟล์หายจาก `static/src/img/`
- [ ] เข้า URL ที่ไม่มีอยู่ (เช่น `/this-page-does-not-exist`) → เห็นหน้า 404 แบบมีแบรนด์ พร้อมโลโก้และปุ่มกลับหน้าแรก
- [ ] favicon ยังแสดงผลถูกต้องเป็นตัว A แดง
- [ ] ฟอนต์ยังเป็น Sarabun ตามเดิม
- [ ] รัน unit test `od19_website` ผ่าน 0 failed / 0 error

---

## 7. สิ่งที่ไม่ทำใน SP1 (Out of Scope)

- ไม่ปรับสีธีม
- ไม่เพิ่มฟอนต์ใหม่
- ไม่แตะใบรับรอง ISO/SGS/UKAS (ไว้ทำใน SP5 — Trust & References)
- ไม่เพิ่มเนื้อหา/หน้าใหม่ (ไว้ SP4/SP5)
- ไม่แก้ไขเมนู navigation
- ไม่แตะ core Odoo (`odoo/`, `addons/`)

---

## 8. ความสอดคล้องกับมาตรฐานโปรเจกต์

- เปลี่ยนแปลงเฉพาะใน `custom_addons/od19_website/`
- Branch: `feature/od19_website-refresh-sp1`
- Worktree: แยกตาม branch
- ก่อน push: รัน `run-tests.ps1 -Module od19_website` บน DB ส่วนตัวให้ผ่าน
- Conventional commit: `feat(website): SP1 foundation & brand cleanup`
