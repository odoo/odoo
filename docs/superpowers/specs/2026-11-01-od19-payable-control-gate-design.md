# เอกสารออกแบบ: ประตูควบคุมฝั่งจ่าย (Payable Control Gate) — บังคับ Prepare→Approve + Three-Way Match

- **วันที่:** 2026-11-01
- **Child spec ID:** W2-PAYABLE-CONTROL-GATE (ภายใต้ W2-FINANCE-CONTROLS)
- **โมดูลที่แตะ:** `od19_accounting_payment_voucher_reports` (แก้), `od19_accounting_features` (แก้ config/สิทธิ์), data/config มาตรฐาน Odoo (`purchase`, `account`) — **ไม่แตะ Odoo core**
- **สถานะ:** รอตรวจสอบ (Draft for review)
- **ผู้เกี่ยวข้อง:** ฝ่ายบัญชีเจ้าหนี้ / ผู้จัดการบัญชี / ผู้จัดทำจ่าย / ผู้อนุมัติ / ไอที–แอดมิน
- **Canonical path:** `docs/superpowers/specs/2026-11-01-od19-payable-control-gate-design.md`

---

## 1. บทสรุป (Summary)

ปัจจุบันกลไก **Prepare Payment** ของ OD19 ถูกสร้างไว้แล้ว (ฟิลด์ `od19_prepare_state` = draft → prepared → approved บน `account.payment`) แต่ **ยังไม่ถูกบังคับใช้**: `action_post()` ไม่ตรวจสถานะอนุมัติ ทำให้เตรียมจ่าย/อนุมัติเป็นเพียงขั้นตอน "ของประดับ" และ flows ที่ลง GL ตรง (cheque / petty cash / advance / HR expense) ข้ามประตูนี้ทั้งหมด

งานนี้สร้าง **ประตูควบคุมฝั่งจ่าย (Payable Control Gate)** ตามกรอบควบคุมภายในที่ยอมรับทั่วไป (COSO / SOX / CIMA) โดยระยะ **P1** ทำเฉพาะ *ความเสี่ยงสูงสุดที่ชัดเจนสุด* 3 ข้อ:

1. **บังคับ** ให้ payment จ่ายผู้ขายต้องผ่าน `prepared → approved` ก่อน Post (มี override + log สำหรับกรณีเร่งด่วน) — พร้อมแยกหน้าที่ผู้จัดทำ ≠ ผู้อนุมัติ
2. **เปิด Three-Way Match** (PO + ใบรับของ + ใบแจ้งหนี้) สำหรับสินค้าคงคลัง — "ไม่ตรงไม่จ่าย"
3. **ใช้ Block Payment** ของ Odoo CE เป็นประตูเสริมระดับบิล

> **ข้อค้นพบที่แก้ข้อเสนอก่อนหน้า:** Odoo 19 **CE ไม่มี** โมดูล `account_batch_payment` (เป็น Enterprise) จึง **ตัด "Batch Payment ไฟล์เดียว" ออกจากแผน** และใช้ **Group Payments** ของ CE (`account.payment.register.group_payment` — รวมหลายบิลของเจ้าเดียวกันเป็น 1 payment) แทน

---

## 2. ปัญหาและความต้องการ (Problem)

### 2.1 สภาพปัจจุบัน (ยืนยันจากโค้ดจริง)

| # | ประเด็น | หลักฐาน | สภาพ |
|---|---|---|---|
| 1 | ไม่บังคับอนุมัติก่อนจ่าย | [account_payment.py](../../../custom_addons/od19_accounting_payment_voucher_reports/models/account_payment.py) `action_post()` ไม่ตรวจ `od19_prepare_state` | เตรียมจ่าย = ตัวเลือก |
| 2 | ไม่มี SoD ผู้จัดทำ/ผู้อนุมัติ | `action_od19_approve()` ไม่เทียบ user | คนเดียวจัดทำ+อนุมัติได้ |
| 3 | ไม่มีด่าน PO ระดับบิล | ยังไม่เปิด Bill Control = Received | จ่ายของไม่ครบ/ยังไม่รับได้ |
| 4 | ไม่ใช้ Block Payment | ไม่มีที่เรียก `action_toggle_block_payment` | ไม่มีเบรกไฟล์บิล |
| 5 | flows อื่นข้ามประตู | cheque/petty cash/advance/HR expense ลง GL ตรง | ควบคุมไม่สม่ำเสมอ |

### 2.2 ความต้องการ (Requirements)

- **R1** payment จ่ายผู้ขาย (`outbound` + supplier) ต้อง `od19_prepare_state='approved'` ก่อน Post
- **R2** ผู้จัดทำ (prepared_by) ≠ ผู้อนุมัติ (approved_by) เมื่อเปิดใช้โหมด SoD
- **R3** มี override สำหรับกรณีเร่งด่วน พร้อมเหตุผล + บันทึกผู้สั่งข้าม (audit)
- **R4** สินค้าคงคลังที่ออกบิลได้เฉพาะเมื่อ **รับของแล้ว** (3-way match) ยกเว้นงานบริการ (2-way)
- **R5** ใช้ `payment_state='blocked'` เป็นเบรกก่อนจ่าย ตามที่ฝ่ายบัญชีเปิด
- **R6** ไม่ทำลาย flow เดิม: HR expense / การจ่ายอัตโนมัติ ต้องไม่ถูกบล็อก
- **R7** เปิด/ปิดการบังคับได้ระดับบริษัท (rollout แบบค่อยเป็นค่อยไป)
- **R8** ไม่แตะ Odoo core; เพิ่มเฉพาะใน addons ของโปรเจกต์

### 2.3 นิยามคำสำคัญ

- **Payable Control Gate** = ชุดเงื่อนไขที่ต้องผ่านก่อนที่เงินจะออกจากบริษัท
- **3-way match** = เทียบ PO + ใบรับของ (GRN) + ใบแจ้งหนี้ ก่อนอนุมัติจ่าย (งานบริการใช้ 2-way: สัญญา/ตรวจรับ + ใบแจ้งหนี้)
- **Prepare** = จัดทำข้อเสนอจ่าย (ออกเลข PV, รวมบิล) / **Approve** = อนุมัติ / **Post·Pay** = ปล่อยจ่าย

---

## 3. หลักการอ้างอิงจากแหล่งน่าเชื่อถือ (Standards Basis)

| หัวข้อ | สาระสำคัญ | แหล่ง |
|---|---|---|
| แยกหน้าที่ (SoD) | ห้ามคนเดียวคุม authorization / custody / recording / reconciliation; ระวังสุดคือ "สร้าง-แก้ผู้ขาย" + "สั่งจ่าย" | Corpay, Peakflo, Univ. of Toledo Internal Audit |
| Three-Way Match | เป็น control activity ภายใต้ COSO/SOX; preventive control ที่ถูกอ้างมากสุดใน AP; ใช้ tolerance | Nimblechapps (CPA guide), Tipalti, SOX/AP guide |
| Approval matrix + วงเงิน | อนุมัติตามวงเงิน, escalation, delegation log | CIMA/AccountingBody, Ramp, GetYooz |
| Payment run + exception review | ก่อนปล่อยจ่ายรีวิวของผิดปกติ (ซ้ำ / เปลี่ยนเลขบัญชีผู้ขาย) | Wise (2026), ApprovalMax |
| เงินล่วงหน้าผู้ขาย | ลงเป็น asset ผูก supplier + reference แล้ว net กับบิลอัตโนมัติ | Peakflo, IFRIC 22 |
| Audit trail | เอกสารต้นทาง → สายอนุมัติ → การจ่าย ต้องเชื่อมไม่ขาด | SOX/AP guide (สอดคล้อง ISO 9001) |

---

## 4. Control Matrix (เทียบกับความสามารถ Odoo 19 CE ที่มีจริง)

| Control Objective | มาตรฐาน | Odoo 19 CE feature | สถานะ OD19 | ข้อเสนอ |
|---|---|---|---|---|
| อนุมัติก่อนจ่าย (authorization) | COSO/CIMA | — (สร้างเองบน `account.payment`) | มีฟิลด์ แต่ไม่บังคับ | **P1 — บังคับ** |
| แยกหน้าที่ (SoD) | Corpay/Peakflo | Access groups / OCA `base_user_role` | มี RBAC, ยังไม่บังคับคู่จัดทำ≠อนุมัติ | **P1 — บังคับ** |
| Three-Way Match | COSO/SOX | `product.purchase_method='receive'` (Bill Control = On received quantities) | ยังไม่เปิด | **P1 — เปิด** |
| เบรกบิลก่อนจ่าย | SOX | `account.move.action_toggle_block_payment` (`payment_state='blocked'`) | ไม่ใช้ | **P1 — ใช้** |
| รวมบิลของเจ้าเดียว | — | `account.payment.register.group_payment` | มีใน CE | **P1 — ใช้** |
| Approval matrix ตามวงเงิน | CIMA/Ramp | OCA `base_tier_validation` | ยังไม่ติดตั้ง | P2 |
| ตรวจใบซ้ำ / เปลี่ยนเลขบัญชี | SOX/Wise | — (custom) | ไม่มี | P3 |
| เงินล่วงหน้าผูก PO | Peakflo | OCA `purchase_advance_payment` | advance ลง move ตรง | P4 |
| Batch payment ไฟล์เดียว | — | ❌ ไม่มีใน CE (Enterprise) | — | **ตัดออก** |
| Audit trail ครบ | SOX/ISO | chatter tracking | มี tracking | P1 — รวมเป็นหลักฐาน PV |

---

## 5. ดีไซน์ (Design) — ขอบเขต P1

### 5.1 บังคับ Prepare→Approve ก่อน Post

- เพิ่ม **company setting** `od19_enforce_prepare_approval` (default `False` เพื่อ rollout ปลอดภัย) + สวิตช์ใน `res.config.settings`
- เพิ่ม hook **`_od19_requires_prepare_approval()`** บน `account.payment` — คืน `True` เฉพาะ:
  - `payment_type == 'outbound'` และ `partner_type == 'supplier'`
  - **และไม่ใช่** payment ที่สร้างจาก flow ยกเว้น (ดู 5.2)
- แก้ `action_post()`:
  - ถ้า `company.od19_enforce_prepare_approval` และ `_od19_requires_prepare_approval()` และ `od19_prepare_state != 'approved'` และไม่มี override → `UserError`
  - ให้ผู้ใช้กด **"อนุมัติ"** (`action_od19_approve`) หรือ **"ข้ามการอนุมัติ (Override)"** ก่อน
- เก็บพฤติกรรมเดิม: `action_post()` ยังคงออกเลข PV (fallback) และ reconcile staged lines

### 5.2 ข้อยกเว้น (ต้องมีเพื่อไม่ทำลาย flow เดิม)

| Flow | เงื่อนไขยกเว้น | เหตุผล |
|---|---|---|
| HR Expense Reimbursement | `od19_is_expense_payment == True` | สร้าง payment + post ทันทีตามดีไซน์เดิม ([hr_expense.py](../../../custom_addons/od19_hr_expense_thai/models/hr_expense.py)) |
| การจ่ายจาก cross-module / auto | ตั้ง context `od19_skip_prepare_gate` | กันระบบอัตโนมัติพัง |
| การจ่ายที่ไม่ใช่ผู้ขาย (inbound/อื่น) | `_od19_requires_prepare_approval()` = False | ไม่ใช่ฝั่งจ่ายผู้ขาย |

> แนวคิด: **allow-list ของ flow ยกเว้น** ประกาศรวมที่เดียวใน hook เพื่อให้ตรวจสอบได้ ไม่กระจายเงื่อนไข

### 5.3 SoD — ผู้จัดทำ ≠ ผู้อนุมัติ

- เพิ่ม company setting `od19_enforce_prepare_sod` (default `True`)
- ใน `action_od19_approve()`: ถ้าเปิด SoD และ `od19_approved_by == od19_prepared_by` → `UserError`
- ข้อยกเว้นทำได้ผ่านกลุ่มผู้ดูแล (`base.group_system` / กลุ่ม `${module}.group_od19_payment_admin`) และ log ไว้ใน chatter

### 5.4 Override + Audit

- ฟิลด์ใหม่บน `account.payment`:
  - `od19_approval_override` (Boolean, copy=False)
  - `od19_override_reason` (Text, copy=False, tracking=True)
  - `od19_override_by` (Many2one res.users, readonly, tracking=True)
- ปุ่ม **"ข้ามการอนุมัติ"** เปิดเฉพาะกลุ่มผู้อนุมัติ/แอดมิน, บังคับกรอกเหตุผล, เขียน tracking → ปรากฏใน chatter
- ทุก action (`prepare` / `approve` / `override` / `post`) ลง audit ผ่าน `tracking=True` เดิม + `mail.thread`

### 5.5 Three-Way Match (เปิดใน CE)

- ตั้ง **Bill Control = On received quantities** → `product.purchase_method='receive'` บนสินค้าคงคลัง (บริการคงไว้ `='purchase'`)
- เมื่อเปิด: `qty_to_invoice = qty_received − qty_invoiced` (ยืนยันจาก [purchase_order_line.py](../../../addons/purchase/models/purchase_order_line.py)) → ออกบิลได้ไม่เกินของที่รับ
- เอกสารคู่มือ config: ตาราง Product Category / รายการสินค้าที่ใช้ 3-way vs 2-way + tolerance (ถ้าต้องใช้)
- เป็น **data/config** เป็นหลัก ไม่เขียนโค้ดใหม่ (ใช้ความสามารถ core)

### 5.6 Block Payment Gate (ใช้ความสามารถ CE)

- ใช้ `action_toggle_block_payment` (`payment_state='blocked'`) บนใบแจ้งหนี้/บิล
- เพิ่มขั้นตอนในคู่มือ AP: ฝ่ายจัดซื้อ/ตรวจรับ block บิลที่ยังไม่ผ่านการตรวจสอบก่อนจ่าย
- เพิ่มปุ่ม/ป้ายในวิวบิลที่เกี่ยวข้อง (ถ้าจำเป็น) — ใช้ action ของ core

### 5.7 Group Payments (ทดแทน Batch ที่ไม่มีใน CE)

- ใช้ `group_payment` ของ `account.payment.register` รวมบิลหลายใบของเจ้าเดียวกันเป็น 1 payment
- กำหนดเป็นแนวปฏิบัติมาตรฐานในคู่มือ (ลดจำนวนรายการจ่าย, ช่วยกระทบยอดธนาคาร)

### 5.8 ไฟล์ที่แตะ

| ไฟล์ | การเปลี่ยนแปลง |
|---|---|
| `custom_addons/od19_accounting_payment_voucher_reports/models/account_payment.py` | เพิ่ม hook `_od19_requires_prepare_approval()`, guard ใน `action_post()`, SoD ใน `action_od19_approve()`, ฟิลด์ override + action |
| `custom_addons/od19_accounting_payment_voucher_reports/models/res_company.py` | **เพิ่ม** — settings 2 ตัว (`od19_enforce_prepare_approval`, `od19_enforce_prepare_sod`) |
| `custom_addons/od19_accounting_payment_voucher_reports/models/res_config_settings.py` | **เพิ่ม** — สวิตช์ในหน้าตั้งค่า |
| `custom_addons/od19_accounting_payment_voucher_reports/views/account_payment_views.xml` | เพิ่มปุ่ม "ข้ามการอนุมัติ" + ฟิลด์ override (ตามกลุ่มสิทธิ์) |
| `custom_addons/od19_accounting_payment_voucher_reports/security/*` | **เพิ่ม** — กลุ่ม `group_od19_payment_approver`, record rule สำหรับ override |
| `custom_addons/od19_accounting_payment_voucher_reports/tests/*` | **เพิ่ม** — เทสต์ P1 (TDD) |
| `custom_addons/od19_accounting_features/**` | ทบทวน bill-first gate ให้สอดคล้อง (ไม่ double-block) |

---

## 6. ขอบเขต (Scope)

### 6.1 ในขอบเขต (P1)
- บังคับ prepare→approve + SoD + override/audit บน `account.payment`
- เปิด Three-Way Match (config) + เอกสารคู่มือ 3-way/2-way
- ใช้ Block Payment + Group Payments ตามคู่มือ
- เทสต์ TDD ครบ + อัปเดตเอกสาร

### 6.2 นอกขอบเขต (Out of scope — P2+)
- Approval matrix ตามวงเงิน / หลายชั้น (P2 — OCA `base_tier_validation`)
- ตรวจใบซ้ำ / ตรวจเปลี่ยนเลขบัญชีผู้ขาย (P3)
- เงินล่วงหน้าผูก PO / net กับบิล (P4 — OCA `purchase_advance_payment`)
- ปรับ flows cheque / petty cash / advance / clearing ให้ผ่าน `account.payment` (พิจารณาแยก)
- Batch payment ไฟล์เดียว (ไม่มีใน CE)
- ไม่แตะ Odoo core

---

## 7. ความปลอดภัยและสิทธิ์ (Security)

- การบังคับเปิด/ปิด = เฉพาะกลุ่มแอดมินบัญชี (`group_od19_payment_admin`)
- ปุ่ม "ข้ามการอนุมัติ" = เฉพาะกลุ่มผู้อนุมัติ (`group_od19_payment_approver`) + แอดมิน; บังคับกรอกเหตุผล
- `action_od19_approve` เคารพ SoD เมื่อเปิด; มี log ผู้ทำ/วันเวลา ทุกครั้ง (`tracking=True`)
- 3-way match เป็น config ระดับสินค้า/บริษัท — เขียนได้เฉพาะผู้จัดการจัดซื้อ/บัญชี
- ยึดหลักเดิม: ข้อมูลสำคัญมี field-level security + UI masking เมื่อจำเป็น

---

## 8. การจัดการข้อผิดพลาด (Error handling)

- Error message ต้องบอก **สิ่งที่ต้องทำต่อ**: เช่น "ต้องกด 'อนุมัติ' ก่อน Post — หรือใช้ 'ข้ามการอนุมัติ' พร้อมเหตุผล"
- ถ้า `od19_enforce_prepare_approval = False` → ระบบไม่บล็อก (พฤติกรรมเดิม)
- ถ้า flow ยกเว้น (HR expense/auto) → ข้ามประตูเงียบ ๆ + `_logger.info`
- ไม่มี call ภายนอก (offline-tolerant ตามค่าเริ่มต้นโปรเจกต์)

---

## 9. การทดสอบ (Testing / TDD)

| ระดับ | เนื้อหา |
|---|---|
| `od19_accounting_payment_voucher_reports` (TransactionCase) | (1) เปิด enforce + outbound/supplier + draft → `action_post()` ต้อง raise; (2) หลัง `prepare`→`approve` → post ผ่าน; (3) SoD: เปิด และ prepared_by == approved_by → raise; (4) override บังคับกรอกเหตุผล + เขียน tracking; (5) **exemption**: HR expense payment (`od19_is_expense_payment=True`) post ผ่านแม้ enforce เปิด; (6) ปิด enforce → พฤติกรรมเดิม |
| Purchase/Account (TransactionCase) | ตั้ง `purchase_method='receive'` → ออกบิลเกิน `qty_received` ไม่ได้; งานบริการ (`='purchase'`) ยังออกบิลได้ตามสั่ง |
| คำสั่งรัน | `--test-tags od19_accounting_payment_voucher_reports` (+ `purchase`,`account` smoke) |

> หมายเหตุบทเรียนเดิม: รันเทสต์ด้วยพอร์ต/DB แยกจาก dev server เพื่อกันชนกัน

---

## 10. เกณฑ์ยอมรับ (Acceptance Criteria)

1. เมื่อเปิด `od19_enforce_prepare_approval`: payment จ่ายผู้ขายที่ยัง `draft` **Post ไม่ได้** จนกว่าจะ `approved`
2. เมื่อเปิด SoD: ผู้จัดทำไม่สามารถอนุมัติรายการของตัวเองได้
3. Override ทำงานได้ เฉพาะกลุ่มที่กำหนด, บังคับเหตุผล, และมีร่องรอยใน chatter ครบ (ใคร/เมื่อไร/ทำไม)
4. HR expense reimbursement และการจ่ายอัตโนมัติ **ยังทำงานได้ปกติ** (ไม่ถูกบล็อก)
5. เปิด 3-way match แล้ว: บิลจาก PO ของสินค้าคงคลังออกบิลได้ไม่เกินจำนวนที่รับ; งานบริการไม่กระทบ
6. Block Payment ใช้ได้จริงบนบิล (`payment_state='blocked'`) และบิลที่ block ไม่ถูกนำไปจ่าย
7. Group Payments รวมบิลของเจ้าเดียวกันได้ตามคู่มือ
8. ไม่มีการแก้ไฟล์ Odoo core; ไม่มี error/warning ใน log จากการใช้งานปกติ
9. เทสต์ P1 ผ่านทั้งหมด (`0 failed, 0 error(s)`)

---

## 11. P1 Task Breakdown

| ID | Task | Owner (role) | สถานะ | Acceptance criteria | ไฟล์ที่แตะ |
|---|---|---|---|---|---|
| P1-T1 | เพิ่ม company settings 2 ตัว + สวิตช์ใน `res.config.settings` | Backend dev | **done + verified (2026-11-01)** | บันทึก/อ่านค่าได้; default `enforce=False`, `sod=True` | `models/res_company.py`, `models/res_config_settings.py`, `views/res_config_settings_views.xml` |
| P1-T2 | เพิ่ม hook `_od19_requires_prepare_approval()` + allow-list flow ยกเว้น | Backend dev | **done + verified (2026-11-01)** | outbound+supplier = True; HR expense/auto = False (มีเทสต์) | `models/account_payment.py` |
| P1-T3 | Guard ใน `action_post()` (บล็อกถ้ายังไม่ approved) | Backend dev | **done + verified (2026-11-01)** | เทสต์ (1),(2),(6) ใน §9 ผ่าน | `models/account_payment.py` |
| P1-T4 | ฟิลด์ override + action "ข้ามการอนุมัติ" + tracking | Backend dev | **done + verified (2026-11-01)** | เทสต์ (4) ผ่าน; เปิดเฉพาะกลุ่ม | `models/account_payment.py`, `views/account_payment_views.xml` |
| P1-T5 | SoD check ใน `action_od19_approve()` | Backend dev | **done + verified (2026-11-01)** | เทสต์ (3) ผ่าน; ข้อยกเว้นแอดมินตามที่ตั้ง | `models/account_payment.py` |
| P1-T6 | กลุ่มสิทธิ์ `group_od19_payment_approver` + `group_od19_payment_admin` (privilege เดียวกัน) | Backend dev | **done + verified (2026-11-01)** | ผู้อนุมัติ/แอดมินเห็นปุ่ม; คนอื่นไม่เห็น (คุมด้วย `groups=` ที่ปุ่ม) | `security/od19_payment_security.xml` |
| P1-T7 | เปิด Three-Way Match (config) + แก้ `purchase_method` สินค้าคงคลัง | บัญชี + จัดซื้อ | todo | เทสต์ §9 (Purchase) ผ่าน; บริการไม่กระทบ | data/config (core `purchase`) |
| P1-T8 | คู่มือ Block Payment + Group Payments ให้ฝ่าย AP | บัญชีเจ้าหนี้ | todo | มี SOP ระบุขั้นตอน; ทดลองใช้จริง 1 รอบ | `docs/...` (คู่มือ) |
| P1-T9 | เทสต์ TDD P1 ครบ + อัปเดต spec wave-2 (sync) | Backend dev | todo | เกณฑ์ยอมรับ 1–9 ครบ | `tests/*`, `2026-10-21-...wave-2...md` |
| P1-T10 | UAT จำลอง business flow (บิลจาก PO → รับของ → จ่าย) | บัญชี + จัดซื้อ | todo | ผ่านเคสจริง 10 รายการต่อส่วน (ข้อมูลตัวอย่าง) | UAT evidence |

---

## 12. ความเสี่ยงและข้อพิจารณา (Risks)

| ความเสี่ยง | ระดับ | การบรรเทา |
|---|---|---|
| Enforcement ไปบล็อก flow อัตโนมัติ/HR expense | สูง | allow-list ยกเว้น + เทสต์ครอบ + default ปิดก่อน rollout |
| บิลจำนวนมากอาจค้างเพราะต้อง approve ทุกใบ | กลาง | ใช้ Group Payments รวมเป็นชุดเดียว; เอกสาร SOP ชัด |
| 3-way match ทำให้ออกบิลก่อนรับของไม่ได้ (ของเร่งด่วน) | กลาง | ใช้ 2-way สำหรับบริการ; พิจารณา tolerance / override ที่มี audit |
| SoD เข้มเกินในทีมเล็ก | กลาง | ตั้ง `od19_enforce_prepare_sod` ปิดได้ระดับบริษัท; log แทน block (ตัวเลือก) |
| fee/value diff จาก exchange rate ทำให้ match ตก | ต่ำ | ตั้ง tolerance ตามนโยบาย |
| ซ้ำซ้อนกับ bill-first gate เดิม (`od19_accounting_features`) | กลาง | ทบทวนรวมครั้งเดียว ไม่ให้ double-block |

---

## 13. Traceability & Update Order (Governance)

- **Design source of truth:** เอกสารนี้ (สำหรับประตูควบคุมฝั่งจ่าย)
- **Work-state:** ยังไม่มี `tasks.md` ในโปรเจกต์ → ใช้ตาราง §11 เป็น task board ชั่วคราว และผูก task-state กับ commit
- **Exec plan:** หากเริ่มลงมือ ควรมีไฟล์ใน `docs/superpowers/plans/` คู่กัน (เช่น `2026-11-01-od19-payable-control-gate-implementation-plan.md`)

**ลำดับการอัปเดตเมื่อตัดสินใจ:**
1. อัปเดต **เอกสารนี้** ก่อน (เมื่อ scope/ดีไซน์เปลี่ยน)
2. ลงทะเบียน child spec ใน [domain-spec-index.md](../programs/odoo19-enterprise/backlog/domain-spec-index.md) (W2-PAYABLE-CONTROL-GATE)
3. sync กับ [wave-2 spec](2026-10-21-odoo19-enterprise-wave-2-custom-finance-controls.md) (สถานะ Payment Preparation)
4. แล้วจึงเริ่มโค้ด P1 (TDD)

**Commit coupling:** ทุกงานที่ปิด task ใน §11 ต้องอัปเดตสถานะ task ใน commit เดียวกับโค้ดที่เกี่ยวข้อง

**Drift checks:**
- หนึ่งข้อสรุป = หนึ่ง source of truth (เอกสารนี้สำหรับ design; wave-2 spec อ้างอิงกลับ)
- สถานะ task ต้องตรงกับโค้ดจริง ณ commit
- ถ้า Odoo core เพิ่มความสามารถใหม่ (เช่น CE ได้ batch payment ในอนาคต) ให้ทบทวน Control Matrix ใหม่
