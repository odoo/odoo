# เอกสารออกแบบ: ศูนย์อนุมัติ (Approval Center) — การมองเห็นรายการอนุมัติและระยะเวลา

- **วันที่:** 2026-11-01
- **โมดูลที่แตะ:** สร้างใหม่ `od19_approval_center` + แก้ `od19_website` (ไม่แตะ Odoo core)
- **สถานะ:** รอตรวจสอบ (Draft for review)
- **ผู้เกี่ยวข้อง:** ผู้อนุมัติ (หัวหน้าแผนก/ผู้บริหาร) / ผู้ขอ (พนักงาน) / ฝ่ายไอที–แอดมิน

---

## 1. บทสรุป (Summary)

ปัจจุบันโปรเจกต์มี **~13 แหล่งที่มีจุดอนุมัติจริง** (ค่าใช้จ่าย, ใบขอซื้อ, ลงนามเอกสาร, เอกสาร ISO, ใบสั่งขาย, ขนส่ง, ใบสำคัญจ่าย, ปรับปรุงสต็อก ฯลฯ) แต่ **รูปแบบการเก็บสถานะ/ผู้อนุมัติไม่เหมือนกัน** ทำให้:

- ผู้อนุมัติ **มองไม่เห็นว่ามีอะไรรอตนอนุมัติ** → รายการค้างเป็นเวลานานโดยไม่มีใครรู้ (ปัญหาหลักของผู้ใช้)
- ผู้ขอ **ไม่รู้ว่าคำขอของตนอยู่ขั้นไหน รอนานแค่ไหน**

งานนี้เพิ่ม **ศูนย์อนุมัติ (Approval Center)** ให้เห็นทุกอย่างในที่เดียว แบบ **อ่านอย่างเดียว (view-only)** โดย:

1. **หน้าใหม่ `/my/approvals`** — 2 แท็บ (ผู้อนุมัติ / คำขอของฉัน) แต่ละแท็บมี 4 กลุ่ม: **คงค้าง · กำลังมาถึง · สำเร็จ · ปฏิเสธ**
2. **การ์ดสรุปบนหน้า Employee Portal** — ตัวเลข "รอฉันอนุมัติ (N)" + อายุค้างนานสุด → คลิกเข้าศูนย์อนุมัติ

หัวใจคือ **โมดูลกลาง `od19_approval_center` ที่ขับด้วยข้อมูลตั้งค่า (config-driven)** — เพิ่มแหล่งอนุมัติใหม่ในอนาคต = เพิ่ม 1 record ไม่ต้องเขียนโค้ดใหม่

---

## 2. ปัญหาและความต้องการ (Problem)

### 2.1 สภาพปัจจุบัน

| # | ประเด็น | สภาพ |
|---|---|---|
| 1 | ผู้อนุมัติไม่เห็นรายการรออนุมัติ | **ไม่มี** ที่รวมรายการข้ามโมดูล; ต้องเปิดแต่ละโมดูลเอง |
| 2 | ผู้ขอไม่เห็นความคืบหน้า | **ไม่มี**; ต้องถาม/เปิดเอกสารเอง |
| 3 | รูปแบบอนุมัติไม่สม่ำเสมอ | แต่ละโมดูลใช้ `state`/ฟิลด์ผู้อนุมัติ/`tier.validation`/`mail.activity` ต่างกัน |
| 4 | ไม่มีตัววัดระยะเวลา | ไม่มีที่แสดงว่าค้างมานานเท่าไร |

### 2.2 ความต้องการ (Requirements)

- **R1** ผู้อนุมัติเห็น "มีอะไรรอฉันอนุมัติ" ได้ในที่เดียว (แก้ปัญหา lead time)
- **R2** ผู้ขอเห็นสถานะคำขอของตัวเองและระยะเวลาที่ใช้/รอ
- **R3** แสดง 4 กลุ่ม: คงค้าง / กำลังมาถึง / สำเร็จ / ปฏิเสธ
- **R4** ครอบคลุมทุกแหล่งที่มีจุดอนุมัติจริงตั้งแต่แรก
- **R5** เป็น **view-only** — คลิกแล้วเปิดเอกสารจริงในหลังบ้าน (deep link)
- **R6** **ไม่แตะ Odoo core** และไม่แก้โมดูลอื่น (additive ล้วน)
- **R7** ขยายแหล่งใหม่ในอนาคตได้โดยไม่ต้องเขียนโค้ด (config-driven)
- **R8** ใช้ภาษาไทย + ธีมบริษัท (Maroon `#9E2424`) สอดคล้อง UI เดิม

### 2.3 นิยามคำสำคัญ

- **"คงค้าง"** = ถึงขั้นของฉันแล้ว ยังไม่ได้ตัดสิน → ต้องลงมือ (actionable)
- **"กำลังมาถึง"** = ฉันเป็นผู้อนุมัติในขั้นถัดไป **แต่เอกสารยังอยู่ขั้นก่อนหน้า** → ยังไม่ถึงมือฉัน
- **"นับเป็นอนุมัติ"** = มีจุดตัดสินใจจริง (มีผู้อนุมัติ/ปฏิเสธ/ยืนยัน) — โมดูลที่เป็นวงจรชีวิตล้วน (asset_loan, cheque, advance, training, service_card, QC) **ไม่นับ**

---

## 3. ขอบเขต (Scope)

### 3.1 ในขอบเขต (In scope)

| # | รายการ | พื้นผิว |
|---|---|---|
| 1 | โมดูลใหม่ `od19_approval_center` (config + บริการกลาง + security + เทสต์) | Backend |
| 2 | Route + QWeb template หน้า `/my/approvals` (2 แท็บ × 4 กลุ่ม) | Employee Portal |
| 3 | การ์ดสรุป "รายการอนุมัติ" บนหน้า `/employee-portal` | Employee Portal |
| 4 | Seed config ตั้งต้นของทุกแหล่งอนุมัติ (ผูกกับโมเดลที่ติดตั้งจริง) | Backend |
| 5 | เทสต์ TDD (TransactionCase + HttpCase) | Tests |

### 3.2 นอกขอบเขต (Out of scope)

- ไม่ทำปุ่มอนุมัติ/ปฏิเสธบน portal (view-only เท่านั้น — ตามการตัดสินใจ)
- ไม่แก้ logic การอนุมัติของโมดูลอื่นแม้แต่โมดูลเดียว
- ไม่ทำ SLA/escalation อัตโนมัติ (มีการแสดง "เกินกำหนด" แต่ไม่ส่งเตือน/ไม่ escalate)
- ไม่ทำ "เวลาที่อยู่ในขั้นปัจจุบัน" (ใช้ `submitted_date` เป็นฐาน; ฟิลด์วันที่เข้าขั้นเป็นงานอนาคต)
- ไม่แตะ Odoo core

---

## 4. ดีไซน์ (Design)

### 4.1 ที่ตั้งและความรับผิดชอบของโมดูล

| โมดูล | รับผิดชอบ |
|---|---|
| **`od19_approval_center`** (ใหม่) | โมเดล config (`od19.approval.source`, `od19.approval.step`), บริการกลางคำนวณ bucket/อายุ, security, เทสต์ |
| **`od19_website`** (แก้) | Route `/my/approvals`, QWeb template (reuse CSS ของ portal), การ์ดสรุปบนหน้า portal — depends เพิ่มบน `od19_approval_center` |

> เหตุผล: `od19_website` เป็นเจ้าของ Employee Portal และธีม (Sarabun / liquid glass) อยู่ที่นั่น; ส่วน "สมอง" แยกไว้ที่โมดูลกลางเพื่อให้ทดสอบและขยายได้อิสระ

### 4.2 หน้า `/my/approvals` (Approval Center)

- Route: `auth="user"`, `website=True`, `sitemap=False` (พนักงานภายในเท่านั้น เหมือน `/employee-portal`)
- โครง: 2 แท็บ บนหน้าจอเดียว โดยแต่ละแท็บมี 4 กลุ่ม

| | แท็บ "รอฉันอนุมัติ" (ผู้อนุมัติ) | แท็บ "คำขอของฉัน" (ผู้ขอ) |
|---|---|---|
| **คงค้าง** | เอกสารถึงขั้นของฉัน → ต้องทำ | คำขอที่ฉันส่ง รอผู้อื่นอนุมัติ |
| **กำลังมาถึง** | ฉันเป็นผู้อนุมัติขั้นถัดไป แต่เอกสารยังอยู่ขั้นก่อนหน้า | คำขอผ่านขั้นแรกแล้ว กำลังเข้าขั้นถัดไป |
| **สำเร็จ** | ฉันอนุมัติแล้ว | อนุมัติครบแล้ว |
| **ปฏิเสธ** | ที่ฉันปฏิเสธ | ที่ถูกปฏิเสธ |

- แต่ละแถวแสดง: ไอคอนแหล่ง · เลขที่/ชื่อ · ผู้ขอ · **อายุ (ค้าง X วัน)** · ป้ายสถานะ
- เรียงจากค้างนานสุดก่อน; ไฮไลต์สีเมื่อ `age ≥ sla_days` (เหลือง) และเกินมาก (แดง)
- คลิกแถว → `doAction`/deep link เปิดเอกสารจริงในหลังบ้าน (**อ่านอย่างเดียว**)

### 4.3 การ์ดสรุปบน Employee Portal

เพิ่มการ์ด "รายการอนุมัติ" ในกริด "เมนูด่วน (Quick Access)" ของ [employee_portal.xml](../../../custom_addons/od19_website/views/employee_portal.xml):

- แสดง **รอฉันอนุมัติ (N)** เด่น (แดงเมื่อ N > 0)
- แสดง **ค้างนานสุด X วัน** และ **เกินกำหนด N รายการ**
- ลิงก์ไป `/my/approvals`

บริบทที่ส่งเข้า template เพิ่มจาก controller [main.py](../../../custom_addons/od19_website/controllers/main.py): `approval_summary = {...}`

### 4.4 โมเดล `od19.approval.source` (config ระดับแหล่ง)

1 record = 1 แหล่งอนุมัติ

| ฟิลด์ | ชนิด | หน้าที่ |
|---|---|---|
| `name` | Char | ป้ายที่แสดง |
| `model_id` | Many2one `ir.model` | โมเดลของแหล่ง |
| `icon` | Char | คลาสไอคอน (fa) |
| `action_xmlid` | Char | XML id ของ action ปลายทาง (deep link) |
| `sequence` | Integer | ลำดับการแสดง |
| `requester_field` | Char | ฟิลด์ผู้ขอ (เช่น `employee_id`, `create_uid`, `user_id`) |
| `requester_kind` | Selection | `user` / `employee` |
| `submitted_date_field` | Char | วันที่ส่ง (ค่าเริ่มต้น `create_date`) |
| `decided_date_field` | Char | วันที่ตัดสิน (ใช้คิด lead time ของ "สำเร็จ") |
| `rejected_states` | Char (CSV) | ค่า state ที่ถือว่า "ปฏิเสธ" |
| `strategy` | Selection | `field` / `tier_validation` / `activity_assignee` |
| `sla_days` | Integer | เกณฑ์เตือนเกินกำหนด (0 = ไม่เตือน) |
| `active` | Boolean | เปิด/ปิดแหล่ง |

### 4.5 โมเดล `od19.approval.step` (config ระดับขั้นอนุมัติ)

One2many ของ `od19.approval.source` — รองรับหลายชั้น (2 ชั้นค่าใช้จ่าย / 3 ชั้น ISO)

| ฟิลด์ | ชนิด | หน้าที่ |
|---|---|---|
| `source_id` | Many2one | แหล่งแม่ |
| `sequence` | Integer | ลำดับขั้น |
| `label` | Char | ป้ายขั้น (เช่น "อนุมัติชั้น 1", "ตรวจทาน") |
| `state_field` | Char | ชื่อฟิลด์ state ของขั้นนี้ (ว่าง = ใช้ `state`) — เผื่อกรณีหลายฟิลด์ |
| `state_value` | Char | ค่า state ที่เอกสารอยู่ **ตอนรอขั้นนี้** |
| `approver_field` | Char | ฟิลด์ที่เก็บผู้อนุมัติของขั้นนี้ |
| `approver_kind` | Selection | `user` / `employee` |

### 4.6 กลยุทธ์หาผู้อนุมัติ (strategy)

| strategy | ใช้เมื่อ | ตัวอย่าง |
|---|---|---|
| `field` | ผู้อนุมัติเก็บในฟิลด์ของเรกคอร์ด | `hr.expense.first_approver_id`, `purchase.request.assigned_to` |
| `tier_validation` | ใช้ OCA `tier.validation` (`review_ids`) | `sale.order`, `od19.transportation` |
| `activity_assignee` | ผู้อนุมัติ = ผู้ถูกมอบหมาย `mail.activity` | แหล่งที่ใช้ activity เป็นกลไก |

> หมายเหตุ: กรณี "หัวหน้าแผนก" ไม่ต้องมี strategy แยก เพราะค่า `department_id.manager_id` ถูกเก็บลงฟิลด์ผู้อนุมัติของเรกคอร์ดอยู่แล้ว (ใช้ `field` + `approver_kind=employee` ได้)

### 4.7 ตรรกะคำนวณ 4 กลุ่ม (ต่อแท็บ)

ให้ `S` = source, `rec` = เรกคอร์ด, `me` = (user/employee ปัจจุบันตาม `approver_kind`)

- **คงค้าง (ผู้อนุมัติ)**: มี step ที่ `rec[step.state_field] == step.state_value` **และ** `rec[step.approver_field] == me`
- **กำลังมาถึง (ผู้อนุมัติ)**: มี step ที่ฉันเป็นผู้อนุมัติ และมี step อื่นที่ `sequence` ต่ำกว่า และ `rec` อยู่ที่ state ของ step ก่อนหน้านั้น (เอกสารยังไม่ถึงฉัน)
- **สำเร็จ (ผู้อนุมัติ)**: `rec` ถึง state สุดท้ายแล้ว และฉันเป็นผู้อนุมัติของ step ใด ๆ
- **ปฏิเสธ (ผู้อนุมัติ)**: `rec[state] ∈ S.rejected_states` และฉันเป็นผู้อนุมัติของ step ใด ๆ
- **คำขอของฉัน**: กรองด้วย `rec[requester_field] == me` แล้วแบ่งกลุ่มตาม (รออนุมัติ = ยังไม่ถึง state สุดท้ายและไม่ถูกปฏิเสธ / กำลังมาถึง = ผ่านขั้นแรกแล้วแต่ยังไม่สุด / สำเร็จ = ถึง state สุดท้าย / ปฏิเสธ = ∈ `rejected_states`)

### 4.8 การคิดระยะเวลา (lead time)

- **อายุคงค้าง** = `now − rec[submitted_date_field]` → แสดงเป็นวัน (น้อยกว่า 1 วัน = ชั่วโมง)
- **lead time รวม (สำเร็จ)** = `rec[decided_date_field] − rec[submitted_date_field]`
- สถานะ SLA: ปกติ / เตือน (`age ≥ sla_days`) / เกินมาก (เช่น `≥ 2×sla_days`)
- การ์ดสรุป: `pending_count`, `max_age_days`, `over_sla_count`

### 4.9 การ seed config ตั้งต้น

- เก็บ mapping ของทุกแหล่งเป็น **Python constant** ในโมดูล (`data`/`hooks`) เพื่อให้ version-controlled และทดสอบได้
- `post_init_hook` วน mapping แล้วสร้าง `od19.approval.source` (+ steps) **เฉพาะโมเดลที่ติดตั้งอยู่จริง** (`env['ir.model']` มีอยู่) → เลี่ยงการ depend ทั้ง 13 โมดูล
- record ที่สร้างใช้ `noupdate=True` (แอดมินปรับได้ภายหลังโดยไม่ถูกทับตอนอัปเดต)

### 4.10 ไฟล์ที่แตะ

| ไฟล์ | การเปลี่ยนแปลง |
|---|---|
| `custom_addons/od19_approval_center/__manifest__.py` | **เพิ่ม** — โมดูลใหม่ |
| `custom_addons/od19_approval_center/models/od19_approval_source.py` | **เพิ่ม** — โมเดล + บริการคำนวณ |
| `custom_addons/od19_approval_center/models/od19_approval_step.py` | **เพิ่ม** — โมเดลขั้น |
| `custom_addons/od19_approval_center/data/approval_sources.py` | **เพิ่ม** — mapping ตั้งต้น |
| `custom_addons/od19_approval_center/hooks.py` | **เพิ่ม** — `post_init_hook` seed |
| `custom_addons/od19_approval_center/security/*` | **เพิ่ม** — access + กลุ่ม `group_approval_admin` |
| `custom_addons/od19_approval_center/views/*.xml` | **เพิ่ม** — เมนู/วิว config (สำหรับแอดมิน) |
| `custom_addons/od19_approval_center/tests/*` | **เพิ่ม** — เทสต์ |
| `custom_addons/od19_website/controllers/main.py` | **แก้** — เพิ่ม route `/my/approvals` + ส่ง `approval_summary` |
| `custom_addons/od19_website/views/approval_center.xml` | **เพิ่ม** — template หน้า 2 แท็บ |
| `custom_addons/od19_website/views/employee_portal.xml` | **แก้** — เพิ่มการ์ดสรุป |
| `custom_addons/od19_website/__manifest__.py` | **แก้** — depends `od19_approval_center` + โหลด template ใหม่ |
| `custom_addons/od19_website/tests/*` | **เพิ่ม** — เทสต์ HttpCase ของหน้า |

---

## 5. ความปลอดภัยและสิทธิ์ (Security)

- Route `/my/approvals` = `auth="user"` — พนักงานภายในเท่านั้น
- ทุก query ใช้ `sudo()` **แต่กรองเจ้าของชัดเจนทุกครั้ง** (requester = user/employee ปัจจุบัน) หรือ (approver ตรงกับฉัน) — **ไม่พึ่ง record rule**
- View-only: ไม่มีปุ่มอนุมัติ/ปฏิเสธ, ไม่มีการเขียนกลับฐานข้อมูล, ไม่ใช้ `cr.commit()`
- `od19.approval.source` / `od19.approval.step` = ข้อมูลตั้งค่า → เขียนได้เฉพาะกลุ่มใหม่ `od19_approval_center.group_approval_admin`; พนักงานทั่วไปไม่เห็นเมนู/ไม่สามารถเข้าถึง

---

## 6. การจัดการข้อผิดพลาด (Error handling)

- deep link: ถ้า `action_xmlid` ไม่มีอยู่ (โมดูลปลายทางไม่ได้ติดตั้ง) → ข้ามแถวนั้นเงียบ ๆ + `_logger.warning` **ไม่ทำให้หน้าพัง**
- ฟิลด์ config ที่อ้างถึงไม่มีจริง → ตรวจก่อนสร้าง domain/อ่านค่า, ถ้าผิดให้ข้ามแหล่งนั้น + log (fail-soft)
- แหล่งที่อ่านไม่รองรับ (strategy ไม่รู้จัก) → ข้าม
- ไม่มี call ภายนอก (offline-tolerant ตามค่าเริ่มต้นของโปรเจกต์)

---

## 7. การทดสอบ (Testing / TDD)

| ระดับ | เนื้อหา |
|---|---|
| `od19_approval_center` (TransactionCase) | สร้างเรกคอร์ดจริง → assert การแบ่ง 4 กลุ่มถูกต้อง; assert **ผู้อื่นไม่เห็นของฉัน**; assert การคิดอายุจาก `submitted_date`; assert **multi-step**: ตอนอยู่ step1 → โผล่ใน "กำลังมาถึง" ของผู้อนุมัติ step2 และ **ไม่** โผล่ใน "คงค้าง" ของเขา |
| `od19_approval_center` (seed) | assert `post_init_hook` สร้าง source เฉพาะโมเดลที่ติดตั้ง; จำนวน/ความครบตรง mapping |
| `od19_website` (HttpCase) | login เป็นผู้อนุมัติ → GET `/my/approvals` → 200 + แท็บ + จำนวนถูก; ผู้ไม่เกี่ยวข้อง → ไม่เห็นรายการ; ตรวจการ์ดสรุปบน `/employee-portal` |
| คำสั่งรัน | `--test-tags od19_approval_center,od19_website` |

> หมายเหตุ: รันเทสต์ด้วยพอร์ตแยกจาก dev server (บทเรียนเดิม: พอร์ต/DB ชนกัน) หรือปิด dev server ก่อนรัน

---

## 8. เกณฑ์ยอมรับ (Acceptance criteria)

1. มีหน้า `/my/approvals` เข้าถึงได้เฉพาะพนักงานภายใน แสดง 2 แท็บ × 4 กลุ่ม
2. ผู้อนุมัติเห็นรายการที่ "รอฉันอนุมัติ" ถูกต้องตรงกับเอกสารจริง และ **ไม่เห็น** ของผู้อื่น
3. แสดงอายุค้าง (วัน) และไฮไลต์เกินกำหนดตาม `sla_days` ได้
4. multi-step ถูกต้อง: ขั้นก่อนหน้า → "กำลังมาถึง"; ถึงขั้นฉัน → "คงค้าง"; อนุมัติแล้ว → "สำเร็จ"; ปฏิเสธ → "ปฏิเสธ"
5. หน้า Employee Portal มีการ์ดสรุป "รอฉันอนุมัติ (N)" + ค้างนานสุด → คลิกเข้าศูนย์อนุมัติได้
6. คลิกแถวแล้วเปิดเอกสารจริงในหลังบ้านได้ (view-only)
7. ไม่มีการแก้ไฟล์ Odoo core; ไม่มี error/warning ใน log จากการใช้งานปกติ

---

## 9. ความเสี่ยงและข้อพิจารณา (Risks)

| ความเสี่ยง | ระดับ | การบรรเทา |
|---|---|---|
| ค่า state จริงของแต่ละโมดูลต่างจากที่ระบุในตาราง | กลาง | ยืนยันกับโค้ดจริงตอนลงมือด้วย TDD; แก้ที่ record config ไม่ต้องแก้โค้ด |
| `tier.validation` มี API ต่างเวอร์ชัน | กลาง | จำกัดที่ strategy เดียว + เขียนเทสต์ครอบ; ถ้าติดค่อยทำ provider เฉพาะราย |
| คิวรีรวมหลายโมดูลอาจช้าถ้าเรกคอร์ดเยอะ | ต่ำ–กลาง | จำกัดจำนวนต่อแหล่ง + เรียง/แบ่งหน้า; เริ่มจาก lightweight domain |
| config ผิด (ฟิลด์/state พิมพ์ผิด) | กลาง | fail-soft + log + เทสต์ seed ตรวจความครบ |
| ซ้ำซ้อนกับ `mail.activity` systray ของ Odoo | ต่ำ | เป็นมุมมองเสริม (view-only) ไม่แทนที่ระบบ activity |

---

## 10. ภาคผนวก — แหล่งอนุมัติตั้งต้น (Initial sources)

> ค่า state จริงจะยืนยันกับโค้ดตอนลงมือ (TDD)

| แหล่ง | โมเดล | strategy | ผู้อนุมัติ | ขั้น |
|---|---|---|---|---|
| ค่าใช้จ่าย | `hr.expense` | field (employee) | `first_approver_id` → `second_approver_id` | 2 |
| ใบขอซื้อ | `purchase.request` | field (user) | `assigned_to` | 1 |
| ลงนามเอกสาร | `od19.document.signer` | field (user) | ฟิลด์ผู้เซ็น | 1 |
| เอกสาร ISO | `od19.iso.document` | field (user) | `reviewer_id` → `approver_id` → `final_approver_id` | 3 |
| แผนตรวจสอบ ISO | `od19.iso.audit.program` | field (user) | ผู้อนุมัติแผน | 1 |
| NC/CAPA | `od19.iso.nonconformity` | field (user) | `verified_by_id` (ยืนยัน) | 1 |
| ความเสี่ยง ISO | `od19.iso.risk` | field (user) | ผู้ยืนยัน | 1 |
| สอบเทียบ ISO | `od19.iso.calibration.record` | field (user) | `technician_id` | 1 |
| ใบสั่งขาย | `sale.order` | tier_validation | `review_ids` | ตาม tier |
| ขนส่ง | `od19.transportation` | tier_validation | `review_ids` | ตาม tier |
| ใบสำคัญจ่าย | `account.payment` | field (user) | `od19_approved_by` | 1 |
| ปรับมูลค่าสต็อก | `od19.stock.valuation.adjustment` | field (user) | `approved_by` | 1 |
| นับสต็อก | `od19.stock.count.session` | field (user) | `approved_by` | 1 |

**ไม่นับ (lifecycle ล้วน)**: `od19.asset.loan`, `account.cheque`, `account.advance`, `od19.iso.training.course`, `od19.service.card`, `qc.inspection`
