# Odoo 19 CE: Purchase Revision (Purchase Order)

## Control Metadata
- Child spec ID: W1-PURCHASE-REVISION
- Wave: Wave 1 (Commercial and financial core)
- Status: Approved / Implemented (2026-11-02) — `od19_purchase_revision` installed on `odoo19_pdev`; 13 tests pass (`0 failed, 0 error(s)`)
- Owner: Procurement domain lead
- Reviewer: Technical supervisor
- Approvers: Business owner; Technical supervisor
- Canonical path: `docs/superpowers/specs/2026-10-16-odoo19-purchase-revision-design.md`
- Source backlog row: `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md`
- Date: 2026-10-16
- Primary readers: ฝ่ายจัดซื้อ, ผู้อนุมัติ (Purchase Director), ฝ่ายบัญชี, ทีมเทคนิค

## Approval Traceability
- 2026-10-16: ผู้ใช้อนุมัติ design ผ่านการ brainstorm (เลือกแนวทาง B = สร้างระเบียนใหม่เชื่อมฉบับเดิม)
- 2026-10-16: ผู้ใช้ยืนยัน — ฉบับตั้งต้นไม่มี suffix, การแก้ไขครั้งแรกคือ `/R00`
- 2026-10-16: ผู้ใช้ยืนยัน — ขอบเขตเฟสนี้เฉพาะ Purchase Order
- 2026-10-16: ผู้ใช้ยืนยัน — กลุ่มสิทธิ์ที่ใช้คือ `Purchase Director` (`od19_purchase_procurement_core.group_purchase_director`)
- 2026-10-16: ผู้ใช้ยืนยัน — ต้องการพิมพ์เลข Revision ในใบ PO (ทำแยกจาก ISO footer)
- 2026-11-02: Implementation verified — module `od19_purchase_revision` = `installed` on `odoo19_pdev`; `--test-enable` reports 13 tests, `0 failed, 0 error(s)` (Revision chain, `/R00` suffix, director-only access, superseded read-only guard, and printed revision)

## Discovery Evidence
- Current-state references:
  - `addons/purchase/models/purchase_order.py` (`copy()`, field `state`/`locked`/`name`)
  - `custom_addons/od19_purchase_document_sequence/` (เลขเอกสารต่อแผนก)
  - `custom_addons/od19_purchase_procurement_core/security/purchase_director_security.xml` (กลุ่ม Purchase Director)
  - `addons/purchase/report/purchase_order_templates.xml` (`report_purchaseorder_document`)
  - `custom_addons/od19_iso_document_control/report/iso_footer_templates.xml` (ISO footer — คนละความหมาย)
- Evidence findings:
  - `purchase.order.name` เป็น `copy=False` → copy จะไม่พกเลขเดิม (ต้องกำหนดเอง)
  - `purchase.order.state` และ `locked` เป็น `copy=False` → ฉบับใหม่กลับเป็น Draft/RFQ อัตโนมัติ
  - ไม่มีแนวคิด Revision ใน Odoo 19 และ Odoo 15 legacy purchase → เป็นของใหม่ทั้งหมด
  - ISO footer เดิมแสดง "Rev." ของ **แม่แบบรายงาน** (จาก `report_action.od19_iso_document_id`) ไม่ใช่ Rev. ของเอกสาร PO

## Delivery Controls
- Dependencies:
  - โมดูล `purchase` (core)
  - โมดูล `od19_purchase_procurement_core` (กลุ่ม Purchase Director)
- Gate readiness:
  - Spec-ready: กติกาการตั้งชื่อ, สถานะ, flow, และ report ถูกนิยามชัด
  - Plan-ready: ขอบเขต addon ชัด, ไม่แตะ core, ไม่กระทบ ISO footer เดิม

---

## 1. สรุปสั้น ๆ

เพิ่มความสามารถ **Revision Control** ให้เอกสาร Purchase Order ตามแนวทาง ISO 9001:
เมื่อ PO ที่ยืนยันแล้วต้องแก้ไข ระบบจะ **สร้างเอกสารฉบับใหม่** ที่เชื่อมโยงกับฉบับเดิม
โดยฉบับใหม่ได้เลขเดิมต่อท้ายด้วย `/R00`, `/R01`, … และ **ฉบับเดิมถูกล็อกเป็น read-only**

- ฉบับตั้งต้น: `PB2501-0001` (ไม่มี suffix)
- แก้ไขครั้งที่ 1: `PB2501-0001/R00`
- แก้ไขครั้งที่ 2: `PB2501-0001/R01`

## 2. เป้าหมาย
- เก็บประวัติการแก้ไขเอกสาร PO อย่างตรวจสอบย้อนหลังได้ (audit trail)
- ป้องกันการแก้ไขเอกสารที่ถูกแทนที่แล้ว
- ระบุ revision บนเอกสารที่พิมพ์ออกมา ให้สอดคล้อง ISO
- ทำเป็นโมดูลแยก ติดตั้ง/ถอนได้โดยไม่กระทบ core และไม่กระทบ ISO document control เดิม

## 3. ขอบเขต
### 3.1 อยู่ในก้อนนี้
- Purchase Order revision (สร้างฉบับใหม่ + ล็อกฉบับเดิม + chain)
- UI: ปุ่ม Create Revision, smart button, banner, filters
- Report: แสดง Rev. ของเอกสารบนใบ PO
- กลุ่มสิทธิ์: ใช้ `Purchase Director`

### 3.2 ไม่อยู่ในก้อนนี้ (Out of scope)
- Purchase Request revision
- Approval workflow เฉพาะของ revision
- Dual report / Jasper report
- การแก้ Rev. ของ ISO footer (คนละความหมาย)

## 4. สถาปัตยกรรม & โมดูล
- โมดูลใหม่: **`od19_purchase_revision`**
- `depends`: `["purchase", "od19_purchase_procurement_core"]`
- Deploy: ติดตั้งหลัง purchase และ procurement core (Dependency Level ตามมาตรฐานโปรเจกต์)
- ไม่แก้ไขไฟล์ core ใด ๆ ทั้งสิ้น

โครงสร้างไฟล์:
```
od19_purchase_revision/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── purchase_order.py
├── security/
│   └── purchase_revision_security.xml
├── views/
│   ├── purchase_order_views.xml
│   └── purchase_order_report.xml
└── tests/
    ├── __init__.py
    └── test_purchase_revision.py
```

## 5. Data Model (inherit `purchase.order`)

| Field | Type | รายละเอียด |
|---|---|---|
| `od19_revision_of_id` | Many2one `purchase.order` | ฉบับก่อนหน้า (predecessor) — `ondelete='restrict'`, `index=True`, `copy=False` |
| `od19_revision_ids` | One2many `purchase.order` (`od19_revision_of_id`) | ฉบับที่ต่อจากระเบียนนี้ตรง ๆ — `copy=False` (กัน `copy()` สร้างลูกซ้ำ) |
| `od19_base_name` | Char, compute + store, `index=True` | เลขฐาน (ไม่มี suffix) ใช้เป็นคีย์ของสาย revision |
| `od19_revision_no` | Integer, compute + store | ดัชนี revision; `-1` = ฉบับตั้งต้น, `0` = `/R00`, `1` = `/R01` |
| `od19_is_revision` | Boolean, compute + store | `True` เมื่อมี `od19_revision_of_id` |
| `od19_revision_status` | Selection `current` / `superseded`, default `current`, `copy=False`, `tracking=True`, required | สถานะเวอร์ชันของเอกสาร |
| `od19_revision_count` | Integer, compute (non-stored) | จำนวนเอกสารอื่นในสายเดียวกัน (สำหรับ smart button) |

**Computed stored fields** (`od19_base_name`, `od19_revision_no`, `od19_is_revision`) คำนวณจาก `name`:
- ถ้าชื่อลงท้ายด้วย pattern `/R<digits>` → ถือเป็น revision
  - `od19_base_name` = ส่วนหน้า suffix
  - `od19_revision_no` = ค่าตัวเลขหลัง `R`
  - `od19_is_revision` = `True`
- ถ้าไม่ใช่ → ฉบับตั้งต้น
  - `od19_base_name` = `name`
  - `od19_revision_no` = `-1`
  - `od19_is_revision` = `False`
- `od19_revision_of_id` เป็นตัวชี้ลูกโซ่ (chain link) โดยตรง และถูกใช้ร่วมกับ `od19_base_name` ในการค้นทั้งสาย

หมายเหตุ: ใช้ `od19_base_name` เป็นคีย์จัดกลุ่มสาย revision จึงไม่ต้องมี field `root_id` แยก (ลดความซับซ้อน)

## 6. Numbering Rules
- ฉบับตั้งต้น: `name` มาจาก sequence เดิมของ `od19_purchase_document_sequence` (ไม่มี suffix)
- ฉบับแก้ไขครั้งที่ `n` (โดย `n` เริ่มที่ 0): `name = f"{od19_base_name}/R{n:02d}"`
  - `n = 0` → `/R00`, `n = 1` → `/R01`, …
- การหา `n` ครั้งถัดไป: `n = max(od19_revision_no ของ revision ทุกตัวในสายเดียวกัน, default=-1) + 1`
- กำหนด `name` ตรง ๆ ตอน `create` → create-override ของ `od19_purchase_document_sequence` จะข้ามการสร้างเลขใหม่ (เพราะ `name != 'New'`) ตามพฤติกรรมเดิม

## 7. Flow — สร้าง Revision

ปุ่ม **Create Revision** (`action_create_revision`) บน form view ของ PO

**เงื่อนไขการแสดง/ทำงาน (guard ทั้ง UI และ server-side):**
- `od19_revision_status == 'current'` (ฉบับที่ถูกแทนที่แล้วสร้างซ้ำไม่ได้)
- `state == 'purchase'` (ยืนยันแล้ว) — ไม่ขึ้นกับ `locked`
- ผู้ใช้ต้องอยู่ในกลุ่ม `Purchase Director`

**ขั้นตอน:**
1. ตรวจ guard ทั้งหมด; ถ้าไม่ผ่าน raise `UserError` / `AccessError`
2. คำนวณ `new_name` ตามข้อ 6
3. `new = self.copy(default)` โดย `default` ประกอบด้วย
   - `name` = `new_name`
   - `od19_revision_of_id` = `self.id`
   - `od19_revision_status` = `'current'`
   - `date_approve` = `False` (ล้างวันที่อนุมัติเดิม)
   - (`state`, `locked`, `invoice_ids` กลับค่าเริ่มต้นเองอยู่แล้ว เนื่องจาก `copy=False`)
   - order lines ถูก copy ตามพฤติกรรมมาตรฐานของ `purchase.order.copy()`
4. ตั้ง `self.od19_revision_status = 'superseded'`
5. `message_post` ที่ฉบับเดิม (แจ้งเลขฉบับใหม่) และที่ฉบับใหม่ (แจ้งว่ามาจากฉบับใด)
6. คืน action เปิด form ของฉบับใหม่

**ข้อกำหนดเพิ่มเติม:**
- การสร้าง revision ทำได้เฉพาะจาก **ฉบับล่าสุด** ของสายเท่านั้น
- ฉบับตั้งต้นที่มี revision แล้ว จะไม่สามารถสร้าง revision ซ้ำได้จนกว่าจะถูก supersede ไปแล้ว (ซึ่งเป็นค่าเสมอเมื่อสร้าง revision)

## 8. Locking ฉบับที่ถูกแทนที่

- ฉบับที่ถูกสร้าง revision ใหม่ → `od19_revision_status = 'superseded'`
- Override `write()`:
  - ถ้ามีระเบียนใน `self` ที่ `od19_revision_status == 'superseded'`
  - และ `vals` มีคีย์ที่ไม่ใช่ "safe keys"
  - → raise `UserError("เอกสารฉบับนี้ถูกแทนที่แล้ว กรุณาใช้ฉบับล่าสุด")`
- **Safe keys** (อนุญาตให้เขียนได้เสมอ): `od19_revision_status` และคีย์ที่ขึ้นต้นด้วย `message_`, `activity_` (เพื่อไม่ให้ chatter/attachment ของ mail.thread ทำงานผิดพลาด)
- ใช้ `self.env.context.get('od19_allow_superseded_write')` เป็น bypass สำหรับกรณีระบบภายใน (ถ้าจำเป็น)

**UI:** เมื่อ superseded
- แสดง banner เตือน "ฉบับนี้ถูกแทนที่แล้ว (view only)"
- ตั้ง field ต่าง ๆ เป็น `readonly="od19_revision_status == 'superseded'"`
- ซ่อนปุ่ม Create Revision

## 9. UI

**Form view** (inherit `purchase.purchase_order_form`)
- ปุ่ม `Create Revision` ใน header (`groups="od19_purchase_procurement_core.group_purchase_director"`), แสดงเมื่อ `state == 'purchase'` และ `od19_revision_status == 'current'`
- บล็อกข้อมูล Revision: `od19_revision_of_id`, `od19_revision_no` (แสดงเฉพาะเมื่อ `od19_is_revision`), `od19_revision_status`
- Banner (`alert-warning` + `role="alert"`): แสดงเมื่อ `od19_revision_status == 'superseded'`
- Smart button **Revisions** (`od19_revision_count`) เปิด list ของทุกฉบับในสาย เรียงตาม `od19_revision_no`

**List view** (inherit `purchase.purchase_order_tree`)
- เพิ่มคอลัมน์ `od19_revision_no`, `od19_revision_status` แบบ `optional="hide"`

**Search view** (inherit `purchase.view_purchase_order_filter`)
- Filter: `Latest Only` (`od19_revision_status = 'current'`), `Superseded`, `Has Revision` (`od19_is_revision = True`)

## 10. Report — แสดง Rev. บนใบ PO

- Inherit `purchase.report_purchaseorder_document`
- เพิ่มการแสดงเลข revision ของ **เอกสาร** (ไม่ใช่ของแม่แบบฟอร์ม) ในบล็อก `informations`
- รูปแบบ: `Revision: R00` (แสดงเฉพาะเมื่อ `o.od19_is_revision`)
- **ไม่แก้ไข** ISO footer (`od19_iso_document_control`) เนื่องจาก "Rev." ใน footer นั้นหมายถึง revision ของแม่แบบรายงาน คนละความหมายกัน

## 11. Security

- ไม่มีโมเดลใหม่ → ไม่ต้องเพิ่ม `ir.model.access.csv`
- ใช้ record rules ของ `purchase.order` เดิม
- ปุ่ม Create Revision จำกัดกลุ่ม `od19_purchase_procurement_core.group_purchase_director`
- ตรวจสิทธิ์ซ้ำที่ server-side ใน `action_create_revision` ผ่าน `self.env.user.has_group(...)` → raise `AccessError` ถ้าไม่มีสิทธิ์
- เพิ่ม `base.group_system` ให้สืบทอด (implied) กลุ่ม Purchase Director เพื่อให้ผู้ดูแลระบบใช้งานได้ทันที (ตาม convention ของโปรเจกต์)
  - Decision D3: หากไม่ต้องการให้ผู้ดูแลระบบได้สิทธิ์ Purchase Director โดยปริยาย ให้ตัดส่วนนี้ออก

## 12. Testing (TDD)

1. **Naming & Chain**
   - สร้าง revision จาก PO ยืนยันแล้ว → `name == "<base>/R00"`, `od19_revision_of_id == root`, `od19_is_revision == True`, `od19_revision_no == 0`
   - สร้าง revision ต่อจาก `/R00` → `name == "<base>/R01"`, `od19_revision_of_id == R00`
   - `od19_base_name` ของทั้งสายเท่ากัน
2. **Status**
   - หลังสร้าง revision: ฉบับเดิม = `superseded`, ฉบับใหม่ = `current`
   - `od19_revision_count` ถูกต้อง
3. **Locking**
   - เขียนฟิลด์ธุรกิจบนฉบับ superseded → raise `UserError`
   - เขียน `od19_revision_status` บนฉบับ superseded → ผ่าน
   - เขียนฟิลด์ `message_*` บนฉบับ superseded → ผ่าน
4. **Guard**
   - PO ที่ state = draft → raise `UserError`
   - PO ที่ superseded → raise `UserError`
   - ผู้ใช้ที่ไม่มีกลุ่ม Purchase Director → raise `AccessError`
5. **Report**
   - template inherit โหลดได้ และ render โดยไม่มี error (smoke test ผ่าน `_render_qweb_html`)

## 13. Acceptance Criteria
- [ ] PO ยืนยันแล้วกด Create Revision → ได้ฉบับใหม่เลข `/R00` และฉบับเดิมเป็น superseded
- [ ] สร้าง revision ต่อได้เป็น `/R01`, `/R02` … ต่อเนื่อง
- [ ] ฉบับ superseded แก้ไขไม่ได้ (ทั้ง UI และ server-side)
- [ ] ปุ่ม Create Revision เห็นเฉพาะกลุ่ม Purchase Director และเฉพาะ state ที่กำหนด
- [ ] ใบ PO ที่พิมพ์ แสดง Revision ของเอกสาร
- [ ] ไม่มี warning ใหม่ใน log จากการพัฒนาโมดูล
- [ ] โมดูลติดตั้ง/ถอนได้โดยไม่กระทบ core และ ISO document control

## 14. Risks & Mitigations
- **write guard ชนกับ mail.thread** — แก้ด้วย safe-key prefix (`message_`, `activity_`)
- **ชื่อเอกสารไม่ตรง pattern** — ใช้ regex `/R(\d+)$`; ชื่ออื่นถือเป็นฉบับตั้งต้น
- **report อ้าง custom field** — โมดูล inherit template เอง จึงมี field พร้อมเสมอเมื่อติดตั้ง
- **ผู้ใช้ไม่มีกลุ่ม** — เอกสารนี้ระบุชัดว่าต้องอยู่ในกลุ่ม Purchase Director (ผู้ใช้จัดการสมาชิกเอง)

## 15. Rollout
- ติดตั้ง: `python odoo-bin -d odoo19 -i od19_purchase_revision --stop-after-init`
- ไม่มีข้อมูลต้อง migrate (ของใหม่)
- อัปเดต version เมื่อแก้ไข: `19.0.1.0.0`
