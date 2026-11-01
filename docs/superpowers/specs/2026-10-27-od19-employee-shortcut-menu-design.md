# เอกสารออกแบบ: เมนูลัดพนักงานบน Systray + การ์ดคู่มือบน Employee Portal

- **วันที่:** 2026-10-27
- **โมดูลที่แก้:** `od19_website` (ไม่สร้างโมดูลใหม่)
- **สถานะ:** อนุมัติแล้ว (Approved)
- **ผู้เกี่ยวข้อง:** พนักงานทุกคน (ผู้ใช้ภายใน) / ฝ่ายไอที–แอดมิน

---

## 1. บทสรุป (Summary)

ปัจจุบันพนักงานเข้าถึง Employee Portal ได้ทางเดียวคือ **คีย์ลัด `Alt+P`** ([od19_portal_hotkey.js](../../../custom_addons/od19_website/static/src/js/od19_portal_hotkey.js)) ซึ่งต้องจดจำปุ่ม ไม่สามารถกดด้วยเมาส์/ทัชสกรีนได้ และไม่บอกใบ้ว่ามีทางลัดอยู่

งานนี้เพิ่ม **จุดเข้าใช้งานที่กดคลิกได้** 2 จุด:

1. **ไอคอนลัดบน systray** (มุมขวาบนของหลังบ้าน) กดแล้วเปิด dropdown รวมลิงก์พนักงาน 4 รายการ
2. **การ์ด "คู่มือการใช้งาน"** เพิ่มเข้ากริด "เมนูด่วน (Quick Access)" บนหน้า Employee Portal ที่ยังขาดรายการนี้

โดย **คงคีย์ลัด `Alt+P` เดิมไว้** (ไม่ลบ) เพื่อให้ผู้ที่ชินกับคีย์ลัดใช้งานต่อได้

---

## 2. ปัญหาและความต้องการ (Problem)

### 2.1 สภาพปัจจุบัน

| # | ช่องทางเข้าถึง | สถานะ | ข้อจำกัด |
|---|---|---|---|
| 1 | คีย์ลัด `Alt+P` → `/employee-portal` | มีแล้ว | ต้องจดจำปุ่ม, ไม่มีใบ้บนหน้าจอ |
| 2 | กริด "เมนูด่วน (Quick Access)" บนหน้า Portal (9 การ์ด) | มีแล้ว | **ไม่มี** การ์ด "คู่มือการใช้งาน" และมองเห็นได้เฉพาะเมื่ออยู่ในหน้า Portal แล้วเท่านั้น |
| 3 | ปุ่มลัดจากหน้าอื่นของหลังบ้าน (เช่น ขณะทำเอกสาร) | **ไม่มี** | ต้องกลับหน้าแรก/เปิดแอป Portal ก่อน |

### 2.2 ความต้องการของผู้ใช้

- **R1** ต้องมีปุ่ม/เมนูลัดที่ **กดคลิกได้จาก UI โดยตรง** ไม่ต้องพึ่งคีย์ลัด
- **R2** ต้องเห็นได้ **ทุกหน้าของหลังบ้าน** และเข้าถึงได้ด้วย **คลิกเดียว**
- **R3** ครอบคลุมลิงก์พนักงาน 4 รายการ: Employee Portal, จองห้องประชุม, ประกาศ, คู่มือการใช้งาน
- **R4** **ไม่แตะ Odoo core** — ทั้งหมดเป็นส่วนขยายใน custom module
- **R5** ข้อความ/label เป็นภาษาไทย สอดคล้องกับ UI เดิม และใช้ธีม (Maroon `#9E2424`) ของบริษัท
- **R6** ไม่ทำให้ฟังก์ชันเดิม (คีย์ลัด `Alt+P`) เสียหาย

---

## 3. ขอบเขต (Scope)

### 3.1 ในขอบเขต (In scope)

| # | รายการ | พื้นผิว |
|---|---|---|
| 1 | ไอคอน systray + dropdown 4 ลิงก์ | หลังบ้าน (`web.assets_backend`) |
| 2 | การ์ด "คู่มือการใช้งาน" ในกริด Quick Access | หน้าเว็บ Employee Portal |
| 3 | เทสต์ Python (HttpCase) ตรวจการผูก asset ใน bundle และการ์ดบน Portal | `tests/` |

### 3.2 นอกขอบเขต (Out of scope)

- ไม่ทำแอป/เมนู "Shortcuts" แยกต่างหาก
- ไม่ทำระบบให้แอดมินตั้งค่ารายการลัดได้เอง (hardcode ตามชุดที่ตกลง)
- ไม่แตะ Quick Access เดิม 9 การ์ด (เพิ่มอย่างเดียว)
- ไม่ลบหรือเปลี่ยนพฤติกรรมคีย์ลัด `Alt+P`
- ไม่แก้ไฟล์ Odoo core

---

## 4. ดีไซน์ (Design)

### 4.1 องค์ประกอบที่ 1 — ไอคอน systray

- ไฟล์ใหม่: `custom_addons/od19_website/static/src/js/od19_shortcut_menu.js`
- ขึ้นทะเบียนผ่าน `registry.category("systray").add(...)` (pattern มาตรฐาน Odoo 19)
- UI ใช้ component `Dropdown` / `DropdownItem` จาก `@web/core/dropdown`
- ไอคอน: `fa-bolt` (สื่อความหมาย "ลัด/ด่วน") พร้อม `title` เป็นภาษาไทย
- การนำทางใช้ service `action.doAction()` เพื่อเลี่ยงปัญหา URL scheme (`/web#action=` แบบเดิมเทียบ `/odoo/action-` แบบใหม่)

**รายการลิงก์ (4 รายการ):**

| ลำดับ | Label (ไทย) | ไอคอน | กลไกนำทาง | ปลายทาง |
|---|---|---|---|---|
| 1 | Employee Portal | `fa-user-circle` | `act_url` | `/employee-portal` |
| 2 | จองห้องประชุม | `fa-calendar-check-o` | `doAction(xmlid)` | `od19_meeting_room_booking.action_meeting_room_booking` |
| 3 | ประกาศ | `fa-bullhorn` | `doAction(xmlid)` | `od19_announcement.announcement_action` |
| 4 | คู่มือการใช้งาน | `fa-book` | `doAction(xmlid)` | `web_tour.tour_action` |

**การควบคุมการเข้าถึง:** systray อยู่ใน `web.assets_backend` จึงแสดงเฉพาะผู้ใช้ที่เข้าไทม์หลังบ้านอยู่แล้ว (ผู้ใช้ภายใน) — ไม่ต้องมี record rule เพิ่ม

**Dependency:** เพิ่ม `web_tour` เข้า `depends` ของ `od19_website` เพื่อรับประกันว่า `web_tour.tour_action` มีอยู่จริง (เป็นโมดูล core ที่ auto-install อยู่แล้ว การเพิ่มเป็น dependency ชัดเจนจึงมีความเสี่ยงต่ำ)

### 4.2 องค์ประกอบที่ 2 — การ์ด "คู่มือการใช้งาน" บน Portal

- แก้ `custom_addons/od19_website/views/employee_portal.xml` ในกริด "เมนูด่วน (Quick Access)"
- เพิ่มการ์ด 1 ใบ รูปแบบเดียวกับ 9 การ์ดเดิม (`od19-portal-card`) ไอคอน `fa-book`
- ปลายทาง: `/web#action=web_tour.tour_action` (สอดคล้องกับรูปแบบ href เดิมของกริดนี้)

### 4.3 ไฟล์ที่แตะ

| ไฟล์ | การเปลี่ยนแปลง |
|---|---|
| `custom_addons/od19_website/static/src/js/od19_shortcut_menu.js` | **เพิ่ม** — ตัว component + การขึ้นทะเบียน systray |
| `custom_addons/od19_website/views/employee_portal.xml` | **แก้** — เพิ่มการ์ดคู่มือ |
| `custom_addons/od19_website/__manifest__.py` | **แก้** — เพิ่ม asset `web.assets_backend` และ dependency `web_tour` |
| `custom_addons/od19_website/tests/test_employee_shortcut_menu.py` | **เพิ่ม** — เทสต์ Python (HttpCase) |
| `custom_addons/od19_website/tests/__init__.py` | **แก้** — เพิ่ม import เทสต์ใหม่ |

---

## 5. การจัดการข้อผิดพลาด (Error handling)

- การเรียก `doAction(xmlid)` ถูกห่อ `try/catch` — ถ้า action ปลายทางไม่มี (เช่น โมดูลปลายทางยังไม่ติดตั้ง) ให้ `console.warn` เงียบ ๆ **ไม่ทำให้ systray หรือหน้าจอพัง**
- ไม่ใช้ `cr.commit()` / raw cursor (ตามข้อกำหนดโปรเจกต์ — ไม่เกี่ยวข้องเพราะเป็นงาน frontend ล้วน)
- ไม่มี call ภายนอก (offline-tolerant ตามค่าเริ่มต้น)

---

## 6. การทดสอบ (Testing)

| ระดับ | เนื้อหา |
|---|---|
| Python HttpCase | ตรวจว่าไฟล์ `od19_shortcut_menu.js` ถูกผูกเข้า bundle `web.assets_backend` จริง และหน้า `/employee-portal` มีการ์ด "คู่มือการใช้งาน" รวมทั้งสิ้น 10 ใบ |
| Manual | ตรวจว่าไอคอนโผล่ทุกหน้า, กดแต่ละรายการไปถูกปลายทาง, และ `Alt+P` ยังทำงาน |

> หมายเหตุ: เทสต์ต้องรันด้วยพอร์ตแยกจาก dev server (บทเรียน HttpCase/พอร์ตชนกัน) หรือปิด dev server ก่อนรัน

---

## 7. เกณฑ์ยอมรับ (Acceptance criteria)

1. มีไอคอนลัดบน systray มุมขวาบน เห็นได้ทุกหน้าของหลังบ้าน
2. กดแล้วเปิด dropdown แสดง 4 รายการ label ภาษาไทยครบ
3. แต่ละรายการนำทางไปถูกปลายทางจริง
4. หน้า Employee Portal มีการ์ด "คู่มือการใช้งาน" เพิ่มจาก 9 การ์ดเดิม (รวมเป็น 10)
5. คีย์ลัด `Alt+P` ยังทำงานเหมือนเดิม
6. ไม่มีการแก้ไฟล์ Odoo core และไม่มี error/warning ใน log จากการใช้งานปกติ

---

## 8. ความเสี่ยงและข้อพิจารณา (Risks)

| ความเสี่ยง | ระดับ | การบรรเทา |
|---|---|---|
| `web_tour.tour_action` ไม่มีในบางสภาพแวดล้อม | ต่ำ | เพิ่ม dependency `web_tour` + guard `try/catch` |
| รายการ hardcode ทำให้แก้ไขต้องแก้โค้ด | ต่ำ | ยอมรับได้ในเฟสนี้ (ชุดลิงก์พนักงานคงที่); อนาคตสามารถขยายเป็นข้อมูลตั้งค่าได้ |
| ไอคอน systray ชนกับของเดิม | ต่ำ | ใช้ key เฉพาะ `od19_website.shortcut_menu` และกำหนด `sequence` |
