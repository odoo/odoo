# SP4 — Products & Services Content (od19_website)

- **Module**: `od19_website`
- **Branch**: `feature/od19_website-refresh-sp1`
- **AGENT_ID**: `trae-od19_uid`
- **Date**: 2026-11-11
- **Roadmap**: Website Refresh Plan C, sub-project 4 of 8

## 1. Summary

ทำให้เนื้อหา **Products (แคตตาล็อกสินค้า)** และ **Services (3 หน้าบริการตามโดเมน)** เชื่อมโยงกันเป็นเนื้อหาเดียว (bidirectional) — จากเดิมที่หน้าสินค้าและหน้าบริการแยกกันโดยไม่มี cross-link และตัวเลขสถิติบน hero เป็นค่าคงที่ที่อาจไม่ตรงกับข้อมูลจริง

ขอบเขตคือ:
1. ย้าย catalog สินค้า 25 รายการจาก inline `t-set` ใน QWeb → **single source of truth** บนโมเดล `website` (`website.od19_products()`)
2. หน้าสินค้า: filter pill แสดง**จำนวนจริงต่อหมวด**, หัวข้อแต่ละแผนกลิงก์ไปหน้าบริการของแผนกนั้น, hero stats คำนวณจากข้อมูลจริง
3. หน้าบริการทั้ง 3: เพิ่ม section **Related Products** (4 สินค้าต่อโดเมน) ดึงจาก catalog เดียวกัน + ลิงก์กลับ `/products`

## 2. Problem / Goal

**ปัญหา**
- ข้อมูลสินค้าอยู่ใน QWeb template เท่านั้น — หน้าบริการอ้างอิงสินค้าไม่ได้ จึงไม่มี cross-link ระหว่าง Products ↔ Services
- Filter pill บอกแค่หมวด ไม่บอกว่ามีสินค้ากี่รายการ
- Hero stat `10+ Global Brands` ไม่ตรงกับข้อมูลจริง (มี 6 แบรนด์ที่ปรากฏ) → ขัดกับหลัก "ความถูกต้องของเนื้อหา"

**เป้าหมาย**
- Catalog เดียวที่ใช้ร่วมกันทั้งหน้าสินค้าและหน้าบริการ (ไม่มีการคัดลอกข้อมูลซ้ำ)
- ผู้เข้าชมไปมาระหว่างสินค้าและบริการได้ใน 1 คลิก
- ตัวเลขบนหน้าเว็บสะท้อนข้อมูลจริงเสมอ

## 3. Implementation Outline

### 3.1 Single source — `models/website.py`
- เพิ่มค่าคงที่ `OD19_PRODUCT_CATALOG` (25 dicts: `dept`, `brand`, `name`, `desc`, `specs`, `img`)
- เพิ่ม method `Website.od19_products()` (`@api.model`) คืน catalog
- QWeb เรียกผ่าน `t-set="products" t-value="website.od19_products()"`

### 3.2 Products page — `views/products_page.xml`
- `t-set="products"` เปลี่ยนเป็นเรียกจากโมเดล
- คำนวณ `dept_counts` (industrial/building/terminal) + `brand_count` ด้วย QWeb expression
- Filter pill: เพิ่ม `<span class="od19-pc-count">` แสดงจำนวน
- Hero stats: ดึง `len(products)` / `len(depts)` / `brand_count`
- หัวข้อแผนก (`.od19-pc-dept-head`) เพิ่มลิงก์ "Explore &lt;domain&gt; services →" ไป `/industrial-automation`, `/building-automation`, `/terminal-automation`

### 3.3 Services pages — `views/services_pages.xml`
- เพิ่ม reusable template `od19_rel_products` (strip สินค้าที่เกี่ยวข้อง)
- แต่ละหน้า (industrial/building/terminal) แทรก section นี้ก่อน CTA โดย `t-set="rel_products"` = สินค้าของโดเมนนั้น 4 รายการแรก
- การ์ดแต่ละใบลิงก์ไป `/products`

### 3.4 Styles — `static/src/css/od19_website.css`
- `.od19-pc-count` — badge ตัวเลขใน pill
- `.od19-pc-dept-link` — ลิงก์ในหัวข้อแผนก
- `.od19-rel-grid` / `.od19-rel-card` / `.od19-rel-media` / `.od19-rel-body` / `.od19-rel-brand` / `.od19-rel-more`
- responsive + เคารพ `prefers-reduced-motion`

## 4. Section Order (Services page หลัง SP4)

Hero → Overview (split) → Key Capabilities (bg-light) → Process (plain) → Stats (dark) → **Related Products (bg-light)** → CTA (maroon)

## 5. Acceptance Criteria

- [ ] `website.od19_products()` คืน 25 รายการ ครอบคลุม 3 โดเมน (industrial 9 / building 8 / terminal 8)
- [ ] `/products` แสดง filter pill 4 ปุ่ม พร้อมตัวเลข 25 / 9 / 8 / 8
- [ ] `/products` มีลิงก์ไป `/industrial-automation`, `/building-automation`, `/terminal-automation`
- [ ] `/products` hero stats ตรงกับข้อมูลจริง (ไม่ hardcode "10+")
- [ ] หน้าบริการทั้ง 3 มี section `od19-rel-card` ≥ 4 ใบ และลิงก์ไป `/products`
- [ ] เทสต์ `TestProductsServicesSP4` ผ่านทั้งหมด, ชุดเทสต์เดิมไม่ regression (0 failed / 0 error)

## 6. Out of Scope

- ฟอร์ม RFQ รายสินค้า / การสร้าง `crm.lead` → อยู่ใน **SP6**
- หน้าสินค้าแบบ detail ต่อรายการ (`/products/<slug>`) — ไม่ต้องมีในรอบนี้
- SEO meta / schema.org ของหน้าสินค้า-บริการ → อยู่ใน **SP7**
- แก้ข้อมูลสินค้าให้เป็น model ที่แก้ผ่าน backend (ยังใช้ค่าคงที่ในโค้ด)

## 7. Standards

- Odoo 19 CE community conventions (`website`, QWeb)
- ไม่แก้ core; เฉพาะ `custom_addons/od19_website`
- Conventional Commit: `feat(website): SP4 products and services content`
- TDD: เขียนเทสต์คู่กับการ implement; รัน `-u od19_website` บน DB ทดสอบส่วนตัว
