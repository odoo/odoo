# เอกสารออกแบบ: คำขอเปิดบิลกลาง (Unified Billing Request) — AR/AP จาก IN·OUT·SO·PO

- **วันที่:** 2026-11-02
- **Child spec ID:** W6-BILLING-REQUEST (ภายใต้ Billing / Sales–Purchase–Stock gateway)
- **โมดูลที่แตะ:** `od19_billing_request` (**ใหม่**, พึ่งพา `sale`, `purchase`, `stock`, `account`) + ต่อยอด `od19_sales_billing_evidence`, `od19_document_pull` — **ไม่แตะ Odoo core**
- **สถานะ:** Proposed / รอตรวจสเปก (ยังไม่เริ่มโค้ด)
- **ผู้เกี่ยวข้อง:** ฝ่ายคลังสินค้า / ฝ่ายขาย / ฝ่ายจัดซื้อ / ฝ่ายบัญชี (AR–AP) / ไอที–แอดมิน
- **Canonical path:** `docs/superpowers/specs/2026-11-02-od19-billing-request-design.md`

---

## 1. บทสรุป (Summary)

ปัจจุบันพนักงานคลังสินค้าแจ้งบัญชี "เปิดบิล" ด้วยการ **นัด `mail.activity`** แล้ว **พิมพ์ข้อความ + ก๊อปปี้รายการสินค้า** มาวางเอง ทำให้
- ไม่มีโครงสร้าง ตรวจสอบย้อนกลับยาก เสี่ยงตกหล่น/พิมพ์ผิด
- ไม่มีสถานะว่า "บัญชีเปิดบิลให้แล้วหรือยัง"
- ไม่มีการเชื่อมคำขอ ↔ ใบแจ้งหนี้/บิล

งานนี้สร้าง **คำขอเปิดบิลกลาง (Unified Billing Request)** เป็นเอกสาร 1 ชนิดที่ทำหน้าที่ "ซองคำขอ" ทั้ง **AR และ AP** โดยต้นทางขึ้นกับบทบาทผู้แจ้ง:

| ผู้แจ้ง | ต้นทาง (Origin) | ทิศทาง | เอกสารปลายทาง |
|---|---|---|---|
| คลังสินค้า | `stock.picking` OUT (ใบส่งของ) | AR | `out_invoice` |
| คลังสินค้า | `stock.picking` IN (ใบรับของ) | AP | `in_invoice` |
| ฝ่ายขาย | `sale.order` | AR | `out_invoice` |
| ฝ่ายจัดซื้อ | `purchase.order` | AP | `in_invoice` |

**การตัดสินใจที่ยืนยันแล้ว (Freeze):**

1. **1 คำขอ = 1 ต้นทาง = 1 บิล** (ต้นทาง 1 ใบออกได้หลายคำขอ/หลายรอบ แต่ละคำขอ → 1 เอกสารปลายทาง)
2. **โมดูลเดียว** `od19_billing_request` (ไม่แยก AR/AP)
3. โหมด AR 2 ขั้นใช้ **`account.move` เดียว** (ฉบับร่าง = ใบวางบิล → Post = ใบกำกับภาษี) ไม่สร้างโมเดลเอกสารใหม่
4. **แจ้งเตือนอย่างเดียว ไม่มีระบบอนุมัติ** (บัญชีตรวจและออกบิลได้เลย)
5. นโยบาย AR (1 ขั้น/2 ขั้น) **กำหนดได้** ต่อลูกค้า/ประเภทงาน โดยมีค่าปริยายระดับบริษัท

---

## 2. ปัญหาและความต้องการ (Problem)

### 2.1 สภาพปัจจุบัน

| # | ประเด็น | สภาพ |
|---|---|---|
| 1 | แจ้งเปิดบิลทาง activity + พิมพ์ข้อความ | ข้อมูลไม่มีโครงสร้าง |
| 2 | ก๊อปปี้รายการสินค้าเอง | เสี่ยงตกหล่น/พิมพ์ผิด, ไม่ผูกกับบรรทัดต้นทาง |
| 3 | ไม่มีสถานะคำขอ | ไม่รู้ว่าเปิดบิลแล้วหรือยัง / ใครแจ้ง |
| 4 | ไม่มีลิงก์คำขอ ↔ ใบแจ้งหนี้ | ตรวจสอบย้อนกลับขาดตอน |

### 2.2 ความต้องการ (Requirements)

- **R1** ผู้แจ้ง (คลัง/ขาย/จัดซื้อ) สร้าง "คำขอเปิดบิล" จากต้นทางของตนได้ โดยดึงรายการจริงจากต้นทาง (ไม่พิมพ์เอง)
- **R2** ต้นทาง 1 ใบเปิดบิลได้หลายรอบ เปิดได้เฉพาะ "บางรายการ/บางจำนวน" และกันเปิดซ้ำ/เกินยอด
- **R3** คำขอผูกกับเอกสารปลายทาง 1 ใบ (`out_invoice`/`in_invoice`) และต้องตรวจสอบย้อนกลับได้
- **R4** บังคับแนบ **หลักฐานประกอบ** ตามทิศทาง (AR/AP) ก่อนออกบิล
- **R5** ฝั่ง AP ต้องมีสถานะ **"ได้รับต้นฉบับเอกสารจริง"** และบล็อกการออกบิลถ้ายังไม่ได้รับ
- **R6** นโยบาย AR เลือก 1 ขั้น/2 ขั้นได้ ต่อลูกค้า/ประเภทงาน
- **R7** แจ้งเตือนบัญชีเมื่อ Submit (activity) — ไม่มีขั้นอนุมัติ
- **R8** ใช้กลไกเดิมที่มีในโปรเจกต์ให้มากสุด (document pull, evidence, sequence per department)
- **R9** ไม่แตะ Odoo core

### 2.3 นิยามคำสำคัญ

- **Billing Request** = เอกสารคำขอเปิดบิล (ซอง) ที่มีบรรทัดรายการอ้างอิงต้นทาง
- **Origin** = เอกสารต้นทาง (picking / sale.order / purchase.order)
- **Target** = เอกสารปลายทางที่ระบบสร้าง (`account.move`)
- **AR mode** = `direct` (ออกใบแจ้งหนี้/ใบกำกับเลย) หรือ `two_step` (ใบวางบิล → ใบกำกับภาษี)

---

## 3. หลักการอ้างอิงจากของเดิมในโปรเจกต์

| หัวข้อ | ของเดิมที่จะต่อยอด | ไฟล์ |
|---|---|---|
| ดึง/ลบรายการจากต้นทางแบบมีตัวช่วย | Mixin + Wizard (พร้อม deletion logic กันดึงซ้ำ) | [od19_document_pull_mixin.py](../../../custom_addons/od19_document_pull/models/od19_document_pull_mixin.py), [od19_document_pull_wizard.py](../../../custom_addons/od19_document_pull/wizards/od19_document_pull_wizard.py) |
| หลักฐานการวางบิล (บังคับแนบไฟล์เมื่อ verify) | `od19.billing.evidence` + `od19.billing.evidence.type` | [billing_evidence.py](../../../custom_addons/od19_sales_billing_evidence/models/billing_evidence.py) |
| ออกบิลจาก Sale Order ผ่าน gate หลักฐาน | `action_create_invoice` บนบรรทัดงวดบิล | [contract_billing_line.py](../../../custom_addons/od19_sales_contract_core/models/contract_billing_line.py) |
| Sequence แยกตามแผนก (สร้างอัตโนมัติ) | `_od19_get_goods_issue_sequence()` | [stock_request_order.py](../../../custom_addons/od19_goods_issue/models/stock_request_order.py) |
| แจ้งเตือนภายในด้วย activity | `mail.activity` (วิธีเดิมที่ใช้อยู่) | — |

---

## 4. ดีไซน์ (Design)

### 4.1 โครงสร้างข้อมูล

**`od19.billing.request` (เอกสารหลัก)**

| กลุ่ม | ฟิลด์ |
|---|---|
| เอกสาร | `name` (Char, default `/`), `direction` (Selection `ar`/`ap`), `state`, `date_request`, `note` |
| ผู้แจ้ง | `requested_by_id` (res.users), `requested_employee_id` (hr.employee), `department_id` |
| ต้นทาง | `origin_model` (Selection `stock.picking`/`sale.order`/`purchase.order`), `origin_ref` (Reference), `partner_id`, `company_id`, `currency_id` |
| ปลายทาง | `move_type` (compute จาก `direction`: `ar`→`out_invoice`, `ap`→`in_invoice`), `target_move_id` (`account.move`) |
| นโยบาย AR | `ar_billing_mode` (Selection `direct`/`two_step`) |
| หลักฐาน | `evidence_ids` (One2many `od19.billing.evidence`), `evidence_ok` (compute) |
| ต้นฉบับจริง (AP) | `original_received` (Boolean), `original_received_date`, `original_received_by_id` |
| รายการ | `line_ids` (One2many `od19.billing.request.line`) |
| อื่น ๆ | `reject_reason` (Text), tracking ผ่าน `mail.thread`/`mail.activity.mixin` |

**`od19.billing.request.line`**

| ฟิลด์ | คำอธิบาย |
|---|---|
| `request_id` | ผูกกับเอกสารหลัก |
| `product_id`, `name`, `product_uom_id` | รายการสินค้า/บริการ |
| `quantity` | จำนวนที่เปิดบิล **รอบนี้** (แก้ได้ ไม่เกินยอดที่เหลือ) |
| `price_unit`, `discount`, `tax_ids` | ราคา/ส่วนลด/ภาษี (คัดลอกมาจากต้นทาง แก้ได้ตามสิทธิ์) |
| `sale_line_id` / `purchase_line_id` / `stock_move_id` | ลิงก์บรรทัดต้นทาง (อย่างใดอย่างหนึ่ง) |
| `qty_ordered`, `qty_already_requested`, `qty_invoiced` | ตัวนับ (compute) |
| `remaining_to_bill` | `qty_ordered − qty_already_requested − qty_invoiced` (compute) |
| `target_line_id` | บรรทัดใน `account.move` หลังออกบิล (compute/readonly) |

**ส่วนขยาย (config)**
- `res.company`: `od19_ar_billing_mode_default` (Selection, default `direct`), `od19_ar_require_evidence` (Boolean, default `True`), `od19_ap_require_original` (Boolean, default `True`)
- `res.partner`: `od19_ar_billing_mode` (Selection `default`/`direct`/`two_step`)
- `sale.order`: `od19_ar_billing_mode` (Selection `default`/`direct`/`two_step`) — override ระดับงาน
- `od19.billing.evidence.type`: เพิ่มรหัสประเภท `delivery_note`, `customer_po`, `service_report`, `vendor_tax_invoice`, `vendor_invoice` + `requires_original` (Boolean, ใช้กับ AP)

### 4.2 สถานะและ Flow

```
Draft ──submit──> Submitted ──create invoice/bill──> Invoiced
  │                   │
  │                   └──reject──> Rejected ──reset──> Draft
  └──cancel──> Cancelled
```

- **`action_submit()`** — ตรวจหลักฐานบังคับ (ดู §4.5) → นัด `mail.activity` ให้กลุ่มบัญชี → `state = submitted`
- **`action_create_invoice()`** — สร้าง `account.move` จาก `line_ids` แล้วผูก `target_move_id`, set `target_line_id` ต่อบรรทัด, claim ยอด → `state = invoiced`
  - AR: สร้าง `out_invoice` โดยอ้างอิง `sale.order` ต้นทาง — ถ้ามาจาก picking OUT ให้ resolve ไปยัง SO ที่ผูกอยู่ก่อน แล้วใช้ `sale.order._create_invoices()`; ถ้ามาจาก SO โดยตรงก็สร้างจาก SO นั้น
  - AP: สร้าง `in_invoice` (ฉบับร่าง) อ้างอิง `purchase.order` — ต้องผ่านเงื่อนไขต้นฉบับจริง (§4.5)
- **`action_reject(reason)`** / **`action_cancel()`** / **`action_reset_draft()`**

### 4.3 กลไกดึงรายการจากต้นทาง + เปิดบิลบางรายการ

| ต้นทาง | วิธีได้มาของบรรทัด | Partial |
|---|---|---|
| ใบ IN / OUT (`stock.picking`) | ดึงจาก `stock.move` ของใบนั้น (auto-link picking) | ใช้ **Backorder เดิมของ Odoo**: ติ๊กเฉพาะของที่ส่ง/รับจริง รายการที่ไม่เอา/ยังไม่มา ระบบแยกใบถัดไป |
| SO / PO | Wizard ดึงบรรทัด (ใช้ mixin `od19_document_pull`) แล้วผู้ใช้แก้จำนวนต่อบรรทัด | ใส่จำนวน **บางส่วน** ได้; `remaining_to_bill` ต่อบรรทัดคุมยอดที่เหลือ |

- Wizard ดึงรายการ: เลือกบรรทัดต้นทาง → `quantity` ปริยาย = ยอดที่เหลือ → ผู้ใช้ปรับได้
- รายการที่ไม่ต้องการ: ถอดออกจากคำขอ (ใช้ deletion logic กันดึงซ้ำของ `od19_document_pull`)

### 4.4 นโยบาย AR (1 ขั้น / 2 ขั้น)

- ลำดับการหาค่า: `sale.order.od19_ar_billing_mode` → `res.partner.od19_ar_billing_mode` → `res.company.od19_ar_billing_mode_default`
- `direct`: สร้าง `out_invoice` แล้วให้บัญชีตรวจ/Post ตามปกติ
- `two_step`: สร้าง `out_invoice` **ฉบับร่าง** ซึ่งพิมพ์เป็น "ใบวางบิล" ได้ → เมื่อลูกค้ายืนยัน/ครบกำหนด จึง Post เพื่อเป็น "ใบกำกับภาษี" (ใช้ `account.move` เดียว ลดความซับซ้อน)
- ค่า `ar_billing_mode` ถูกคัดลอกลงคำขอตอนสร้าง เพื่อไม่ให้เปลี่ยนย้อนหลังระหว่างดำเนินการ

### 4.5 หลักฐานประกอบ (Evidence Gate)

ต่อยอดจาก `od19.billing.evidence` (มี `required_for_billing` และ constraint บังคับแนบไฟล์เมื่อ `is_verified`)

| ทิศทาง | หลักฐาน | ที่มา | บังคับ |
|---|---|---|---|
| AR | ใบส่งของ | auto-link `stock.picking` | ตาม `od19_ar_require_evidence` |
| AR | PO ของลูกค้า | แนบไฟล์ (ต้นฉบับลูกค้า) | เลือกเปิด/ปิด |
| AR | Service Report | จากระบบ (`od19.service.card`) หรือแนบสแกนจากหน้างาน | เลือกเปิด/ปิด |
| AP | ใบกำกับภาษี / ใบแจ้งหนี้ | แนบไฟล์ | บังคับ |
| AP | **ต้นฉบับเอกสารจริง** | ฟิลด์ `original_received` + วันที่ + ผู้รับ | บังคับตาม `od19_ap_require_original` |

- **AR**: ต้องมีหลักฐานชนิด "บังคับ" อย่างน้อย 1 รายการที่ `is_verified` ก่อน `action_submit()` ผ่าน
- **AP**: ต้องมีไฟล์ใบกำกับ/ใบแจ้งหนี้ และ `original_received = True` จึง `action_create_invoice()` ได้ (ถ้า `od19_ap_require_original = True`)

### 4.6 Guards (กันผิดพลาด)

1. `quantity > 0` ต่อบรรทัด
2. `qty_already_requested + qty_invoiced + quantity ≤ qty_ordered` (SO/PO) หรือ `≤ qty_done` (picking)
3. ห้ามแก้ `line_ids` เมื่อ `state = invoiced`
4. ห้าม `action_create_invoice()` ซ้ำเมื่อ `target_move_id` มีค่าแล้ว
5. ต้องมี `line_ids` อย่างน้อย 1 บรรทัดก่อน Submit
6. ใบส่งของ (AR) ต้องมีในระบบ (auto-link) หรือมีหลักฐานทดแทนที่ verify แล้ว

### 4.7 สิทธิ์ · แจ้งเตือน · Billing Queue

- **กลุ่มสิทธิ์**
  - `od19_billing_request.group_od19_billing_requester` — สร้างคำขอจากต้นทางของตน
  - `od19_billing_request.group_od19_billing_accounting` — ประมวลผล/ออกบิล
  - Record rules: requester เห็นคำขอของตน/แผนก (ตาม `stock.request.order` department rule เดิม); accounting เห็นทั้งหมด
- **แจ้งเตือน**: `mail.activity.type` (`od19_billing_request_submit`) + template ไปกลุ่มบัญชี; deadline เป็น SLA ของฝ่ายบัญชี
- **Billing Queue**: `ir.actions.act_window` กรอง `state = submitted` จัดกลุ่มตาม `direction` แสดงอายุคำขอ (วันที่แจ้ง → วันนี้) — เมนูเดียวสำหรับบัญชี

### 4.8 Sequence

- แยกตามทิศทาง (+ แผนก ถ้ามี): `BRI/AR/00001`, `BRI/AP/00001`
- ใช้รูปแบบ `_od19_get_billing_request_sequence()` ตามแพตเทิร์น [stock_request_order.py](../../../custom_addons/od19_goods_issue/models/stock_request_order.py) (สร้าง sequence อัตโนมัติถ้ายังไม่มี)

### 4.9 ไฟล์ที่แตะ (แผน)

| ไฟล์ | การเปลี่ยนแปลง |
|---|---|
| `custom_addons/od19_billing_request/__manifest__.py` | **ใหม่** — depends: `sale`, `purchase`, `stock`, `account`, `od19_sales_billing_evidence`, `od19_document_pull`, `hr` |
| `custom_addons/od19_billing_request/models/billing_request.py` | **ใหม่** — โมเดลหลัก + flow |
| `custom_addons/od19_billing_request/models/billing_request_line.py` | **ใหม่** — บรรทัด + guards/computes |
| `custom_addons/od19_billing_request/models/{res_company,res_partner,sale_order,billing_evidence}.py` | **ใหม่** — config + ส่วนขยาย |
| `custom_addons/od19_billing_request/wizards/billing_request_pull_wizard.py` | **ใหม่** — ดึงรายการจาก SO/PO/picking |
| `custom_addons/od19_billing_request/views/*.xml` | **ใหม่** — form/tree/kanban + Billing Queue + เมนู |
| `custom_addons/od19_billing_request/data/*.xml` | **ใหม่** — activity type, template, sequence |
| `custom_addons/od19_billing_request/security/*` | **ใหม่** — กลุ่มสิทธิ์ + record rules |
| `custom_addons/od19_billing_request/tests/*` | **ใหม่** — เทสต์ (TDD) |
| `custom_addons/od19_billing_request/i18n/th.po` | **ใหม่** — คำแปลไทย |

---

## 5. ขอบเขต (Scope)

### 5.1 ในขอบเขต (P1)
- โมเดลคำขอ + บรรทัด + flow Draft→Submitted→Invoiced (+Rejected/Cancelled)
- ต้นทาง picking IN/OUT, SO, PO
- เปิดบิลบางรายการได้ + guards
- นโยบาย AR (1 ขั้น/2 ขั้น) แบบ configurable
- Evidence gate (AR/AP) + ต้นฉบับจริงฝั่ง AP
- แจ้งเตือนบัญชี + Billing Queue + sequence แยกทิศทาง
- เทสต์ TDD + คำแปลไทย

### 5.2 นอกขอบเขต (Out of scope)
- รวมหลายต้นทางเป็นบิลเดียว
- ระบบอนุมัติ / วงเงินอนุมัติ
- auto-post
- e-Tax (XML/ลงนาม/ยื่น RD)
- 3-way match อัตโนมัติสำหรับ AP (ใช้ `product.purchase_method` ของเดิมเป็นกรณีศึกษาแยก)
- ไม่แตะ Odoo core

---

## 6. ความปลอดภัยและสิทธิ์ (Security)

- การสร้างคำขอ = กลุ่ม requester; การออกบิล = กลุ่ม accounting (แยกหน้าที่ตาม SoD)
- Record rules จำกัดการมองเห็นตามต้นทาง/แผนก
- แก้ราคา/ส่วนลดได้ตามกลุ่ม (ดีฟอลต์: requester แก้ได้ก่อน Submit; หลัง Submit ล็อกไว้ให้บัญชี)
- ฟิลด์ AP `original_received` + ผู้รับ เป็นร่องรอยการควบคุม (tracking)
- ยึดหลักเดิม: ข้อมูลสำคัญมี field-level security + UI masking เมื่อจำเป็น

---

## 7. การจัดการข้อผิดพลาด (Error handling)

- ข้อความ error ต้องบอกสิ่งที่ต้องทำต่อ เช่น "ยังไม่ได้รับต้นฉบับเอกสาร — กรุณาระบุ 'รับต้นฉบับแล้ว' ก่อนออกบิล"
- Block เกินยอด: แจ้งยอดที่เหลือต่อบรรทัด
- `action_create_invoice()` เมื่อสร้าง `account.move` ไม่สำเร็จ → ไม่เปลี่ยน state, ไม่ set `target_move_id`
- ไม่มี call ภายนอก (offline-tolerant ตามค่าเริ่มต้นโปรเจกต์)

---

## 8. การทดสอบ (Testing / TDD)

| กลุ่ม | เนื้อหา |
|---|---|
| โมเดล | `quantity > 0`; guard เกินยอด (SO/PO/picking); แก้ไม่ได้เมื่อ invoiced |
| Flow | submit→แจ้งเตือน; create invoice/bill ผูก `target_move_id`; reject/cancel/reset |
| AR mode | `direct` สร้างออกบิลได้; `two_step` สร้างฉบับร่างแล้ว Post ได้; override ต่อ partner/SO ถูกต้อง |
| AR sources | จาก `sale.order` และจาก `stock.picking` OUT; partial + backorder |
| AP sources | จาก `purchase.order` และจาก `stock.picking` IN; บังคับต้นฉบับจริง |
| Evidence | AR ขาดหลักฐานบังคับ → submit ไม่ผ่าน; AP ขาดไฟล์/ต้นฉบับ → create bill ไม่ผ่าน |
| ความปลอดภัย | requester สร้างได้แต่ process ไม่ได้; accounting process ได้ |
| คำสั่งรัน | `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_billing_request` |

---

## 9. เกณฑ์ยอมรับ (Acceptance Criteria)

1. คลังฯ สร้างคำขอจากใบ IN/OUT และเซล/จัดซื้อสร้างจาก SO/PO ได้ โดยดึงรายการจริง (ไม่พิมพ์เอง)
2. ต้นทาง 1 ใบเปิดบิลได้หลายรอบ/บางรายการ และระบบกันเกินยอด/เปิดซ้ำ
3. คำขอ 1 ใบ → เอกสารปลายทาง 1 ใบ และตรวจสอบย้อนกลับ (คำขอ ↔ บรรทัด ↔ ใบแจ้งหนี้) ได้
4. AR เลือก 1 ขั้น/2 ขั้นได้ตามลูกค้า/งาน
5. AR/AP บังคับหลักฐานตามที่ตั้ง; AP บังคับ "รับต้นฉบับจริง" ก่อนออกบิล
6. Submit แล้วบัญชีได้รับแจ้งเตือน และเห็นใน Billing Queue
7. ไม่แก้ไฟล์ Odoo core; log ไม่มี error/warning จากการใช้งานปกติ
8. เทสต์ P1 ผ่านทั้งหมด (`0 failed, 0 error(s)`)

---

## 10. Task Breakdown (P1)

| ID | Task | Owner (role) | Acceptance | ไฟล์หลัก |
|---|---|---|---|---|
| P1-T1 | โครงโมดูล + โมเดลคำขอ/บรรทัด + sequence | Backend dev | สร้าง/อ่านคำขอได้; เลขรันแยกทิศทาง | `models/*`, `data/sequence.xml` |
| P1-T2 | Wizard ดึงรายการ (SO/PO/picking) + partial + guards | Backend dev | บรรทัดถูกต้อง; กันเกินยอด/ซ้ำ | `wizards/*`, `models/billing_request_line.py` |
| P1-T3 | Flow submit/reject/cancel/reset + activity แจ้งเตือน | Backend dev | state ถูก; บัญชีได้ activity | `models/billing_request.py`, `data/*` |
| P1-T4 | `action_create_invoice()` AR/AP + ผูก `target_move_id` | Backend dev | ออกเอกสารปลายทาง 1 ใบ; claim ยอด | `models/billing_request.py` |
| P1-T5 | นโยบาย AR configurable (company/partner/SO) | Backend dev | override ถูกต้องตามลำดับ | `models/res_company.py`, `res_partner.py`, `sale_order.py` |
| P1-T6 | Evidence gate AR/AP + ต้นฉบับจริงฝั่ง AP | Backend dev | บล็อกถูกต้องตามที่ตั้ง | `models/billing_request.py`, `models/billing_evidence.py` |
| P1-T7 | Views + Billing Queue + เมนู + สิทธิ์ | Backend dev | requester/accounting เห็นต่างกันถูกต้อง | `views/*`, `security/*` |
| P1-T8 | เทสต์ TDD ครบ + คำแปลไทย | Backend dev | เกณฑ์ยอมรับ 1–8 | `tests/*`, `i18n/th.po` |

---

## 11. ความเสี่ยงและข้อพิจารณา (Risks)

| ความเสี่ยง | ระดับ | การบรรเทา |
|---|---|---|
| AR ออกบิลก่อนส่งของกระทบความรับผิด VAT | สูง | บังคับ/เตือนให้มีใบส่งของ; ทำโหมด `two_step` เป็นทางเลือกหลักของงานที่ยังไม่ส่ง |
| Partial billing ทำให้ยอดไม่ตรงกับ SO/PO | กลาง | `remaining_to_bill` + guard + รายงานสถานะเปิดบิลครบ |
| AP PO ไม่ตรงใบกำกับ (ราคา/จำนวน) | กลาง | ให้บัญชีปรับตอนสร้างบิล + แนบหลักฐาน; พิจารณา 3-way match แยกในเฟสหน้า |
| ต้นฉบับจริงมาช้ากว่าออกบิล | กลาง | เปิด/ปิด `od19_ap_require_original` ระดับบริษัท; มีร่องรอยผู้รับ |
| โมดูลพึ่งพาหลายโมดูล (sale/purchase/stock/account) | ต่ำ | ใช้ bridge pattern + `auto_install` ตามแนวทางเดิมของโปรเจกต์ |
| ซ้ำซ้อนกับ `od19_sales_billing_evidence` | กลาง | ต่อยอด ไม่สร้างตารางหลักฐานซ้ำ; ทบทวนให้ gate เดียว |

---

## 12. Traceability & Update Order (Governance)

- **Design source of truth:** เอกสารนี้
- **Work-state:** ใช้ตาราง §10 เป็น task board ชั่วคราว ผูก task-state กับ commit
- **Exec plan:** หากเริ่มลงมือ ให้มีไฟล์ใน `docs/superpowers/plans/` คู่กัน (`2026-11-02-od19-billing-request-implementation-plan.md`)

**ลำดับการอัปเดตเมื่อตัดสินใจ:**
1. อัปเดตเอกสารนี้ก่อนเมื่อ scope/ดีไซน์เปลี่ยน
2. ลงทะเบียน child spec `W6-BILLING-REQUEST` ใน [domain-spec-index.md](../programs/odoo19-enterprise/backlog/domain-spec-index.md)
3. sync กับสเปก wave ที่เกี่ยวข้อง (sales/purchase/stock) แล้วจึงเริ่มโค้ด (TDD)

**Drift checks:**
- หนึ่งข้อสรุป = หนึ่ง source of truth
- สถานะ task ต้องตรงกับโค้ดจริง ณ commit
- ถ้า Odoo core/OCA เพิ่มความสามารถที่ทดแทนได้ ให้ทบทวนดีไซน์ใหม่
