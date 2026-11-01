# Approval Center (ศูนย์อนุมัติ) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** สร้างศูนย์อนุมัติ (view-only) ที่ให้ผู้อนุมัติเห็นรายการ "รอฉันอนุมัติ" และผู้ขอเห็นความคืบหน้าของคำขอตนเอง รวมทั้งอายุคงค้าง — ครอบคลุมทุกโมดูลที่มีจุดอนุมัติจริงในที่เดียว

**Architecture:** โมดูลกลางใหม่ `od19_approval_center` ขับด้วยข้อมูลตั้งค่า (config-driven) ผ่านโมเดล `od19.approval.source` + `od19.approval.step` ให้บริการคำนวณ 4 กลุ่ม (คงค้าง/กำลังมาถึง/สำเร็จ/ปฏิเสธ) และอายุ/SLA จากนั้น `od19_website` เพิ่ม route `/my/approvals` + QWeb template และการ์ดสรุปบน Employee Portal

**Tech Stack:** Odoo 19 (Python 3.12), QWeb, Bootstrap 5 (website frontend), OCA `base_tier_validation` (`tier.review`)

**Spec:** [2026-11-01-od19-approval-visibility-design.md](../specs/2026-11-01-od19-approval-visibility-design.md)

---

## Decisions (locked — อย่าเปลี่ยนระหว่างลงมือ)

| # | การตัดสินใจ | เหตุผล |
|---|---|---|
| D1 | ครอบคลุม **ครบ 13 แหล่ง** ตั้งแต่แรก | ผู้ใช้ยืนยัน "รวมครบ 13 แหล่ง" |
| D2 | `od19.iso.calibration.record` **นับเป็นอนุมัติ** | ผู้ใช้ยืนยัน "นับ" |
| D3 | เพิ่มฟิลด์ config `success_states` (CSV) ที่ระดับ source | `state_value` ของ step คือสถานะ **ตอนรอ** ไม่ใช่ตอนสำเร็จ ต้องแยก |
| D4 | `approver_kind` ของ step มีค่า `user`/`employee`/`partner` | `od19.document.signer` เก็บผู้ลงนามที่ `partner_id` |
| D5 | `strategy` มี 2 ค่า: `field`, `tier_validation` | ไม่มีแหล่งใดใช้ `activity_assignee` (YAGNI) — ดู Known limitations |
| D6 | seed ทำใน `post_init_hook` (รันเฉพาะตอน **ติดตั้ง**) + ข้ามถ้ามีอยู่แล้ว | ไม่ depend ทั้ง 13 โมดูล; แอดมินแก้ config แล้วไม่ถูกทับ |
| D7 | deep link ใช้ `/web#id={res_id}&model={model}&view_type=form` | ไม่ต้องพึ่ง id ของ action ตอน render; ทน action เปลี่ยน |
| D8 | ทุก query ใช้ `sudo()` + **กรองเจ้าของเอง** (ไม่พึ่ง record rule) | พนักงานเห็นเฉพาะของตน/ที่ตนอนุมัติ |
| D9 | ไม่แตะ Odoo core, ไม่ใช้ `cr.commit()`, additive-only | หลักการโปรเจกต์ |
| D10 | step ที่ **ไม่มี** `approver_field` = "กองกลาง" (shared pool) → ผู้ใช้ภายในทุกคนเห็นเป็น *คงค้าง* | 4 แหล่งไม่มีฟิลด์ผู้อนุมัติที่ถูกเซ็ต *ก่อน* อนุมัติ (audit program, payment voucher, stock valuation, stock count) ถ้าไม่ทำ จะไม่ปรากฏแก่ผู้อนุมัติเลย = แก้ไม่ตรงปัญหา — ดู Task 7 |

### นิยาม (ใช้ตลอดแผน)

- **คงค้าง (pending)** = เอกสารถึงขั้นของฉัน และฉันคือผู้อนุมัติของขั้นนั้น → ต้องลงมือ
- **กำลังมาถึง (incoming)** = ฉันเป็นผู้อนุมัติของขั้น `j` แต่เอกสารยังอยู่ขั้น `i` โดย `i < j`
- **สำเร็จ (done)** = `state ∈ success_states` และฉันเป็นผู้อนุมัติของขั้นใดก็ได้
- **ปฏิเสธ (rejected)** = `state ∈ rejected_states` และฉันเป็นผู้อนุมัติของขั้นใดก็ได้
- **main_state** ของ source = ค่า `state_field` ของ step แรก (หรือ `state` ถ้าไม่มี step)
- **ผู้ขอ (requester tab)**: `pending` = ยังไม่ถึงขั้นที่ 2 (index 0 / ไม่มี step); `incoming` = ผ่านขั้นแรกแล้ว (index > 0); `done`/`rejected` ตาม state

### Mapping ของ tier.review → กลุ่ม

| `tier.review.status` | กลุ่ม |
|---|---|
| `waiting` | กำลังมาถึง (incoming) |
| `pending` | คงค้าง (pending) |
| `approved` | สำเร็จ (done) |
| `rejected` | ปฏิเสธ (rejected) |
| `cancel` | ข้าม |

---

## Test-Run Convention

รันบน Windows PowerShell ที่รากโปรเจกต์ `c:\odoo-dev\odoo19` ใช้ DB พัฒนาเดิม (`odoo19_pdev`) แต่ **พอร์ตแยก 8075** และ `--stop-after-init` เพื่อไม่ชน dev server (8070)

ติดตั้งครั้งแรก:

```powershell
python odoo-bin -c odoo.conf -d odoo19_pdev -i od19_approval_center `
  --test-enable --test-tags /od19_approval_center --stop-after-init --http-port=8075
```

หลังติดตั้งแล้ว (แก้โค้ดซ้ำ) เปลี่ยน `-i` เป็น `-u`:

```powershell
python odoo-bin -c odoo.conf -d odoo19_pdev -u od19_approval_center `
  --test-enable --test-tags /od19_approval_center --stop-after-init --http-port=8075
```

เทสต์ของ `od19_website` (Task 12):

```powershell
python odoo-bin -c odoo.conf -d odoo19_pdev -u od19_website `
  --test-enable --test-tags /od19_website --stop-after-init --http-port=8075
```

- `--test-tags /<module>` = เลือกเฉพาะเทสต์ของโมดูลนั้น
- ถ้า dev server เปิดอยู่ที่ 8070 การรันเทสต์ที่ 8075 ทำงานพร้อมกันได้
- Odoo `TransactionCase`/`HttpCase` รันใน savepoint และ **rollback** → ไม่ทิ้งข้อมูลใน DB

---

## File Structure

### สร้างใหม่ — `custom_addons/od19_approval_center/`

| ไฟล์ | ความรับผิดชอบ |
|---|---|
| `__init__.py` | import `models`, `hooks` |
| `__manifest__.py` | depends `base`, `mail`; data: security, views |
| `hooks.py` | `post_init_hook(env)` — seed source/step |
| `data/approval_sources.py` | constant `APPROVAL_SOURCES` (13 แหล่ง) |
| `models/__init__.py` | import 2 โมเดล |
| `models/od19_approval_step.py` | โมเดลขั้นอนุมัติ |
| `models/od19_approval_source.py` | โมเดลแหล่ง + บริการคำนวณ bucket/อายุ/SLA/row |
| `security/od19_approval_security.xml` | หมวด + กลุ่ม `group_approval_admin` |
| `security/ir.model.access.csv` | read/write เฉพาะกลุ่ม admin |
| `views/od19_approval_source_views.xml` | วิว list/form + action (แอดมิน) |
| `views/od19_approval_menus.xml` | เมนู Settings → Approval Center |
| `tests/__init__.py` | import เทสต์ |
| `tests/test_approval_buckets.py` | เทสต์การแบ่งกลุ่ม/อายุ (TransactionCase) |
| `tests/test_approval_seed.py` | เทสต์ `post_init_hook` (TransactionCase) |

### แก้ไข — `custom_addons/od19_website/`

| ไฟล์ | การเปลี่ยนแปลง |
|---|---|
| `__manifest__.py` | depends เพิ่ม `od19_approval_center`; data เพิ่ม `views/approval_center.xml` |
| `controllers/main.py` | route `/my/approvals` + ส่ง `approval_summary` เข้า `/employee-portal` |
| `views/approval_center.xml` | **สร้างใหม่** — template 2 แท็บ × 4 กลุ่ม |
| `views/employee_portal.xml` | เพิ่มการ์ด "รายการอนุมัติ" เป็นการ์ดแรกของ Quick Access |
| `tests/test_approval_portal.py` | **สร้างใหม่** — HttpCase |

---

## Verified seed data (ตรวจกับโค้ดจริงแล้ว 2026-11-01)

| # | แหล่ง (name) | `model` | `state_field` | `strategy` | ผู้อนุมัติ (step) | `action_xmlid` | `sla_days` |
|---|---|---|---|---|---|---|---|
| 1 | ค่าใช้จ่าย | `hr.expense` | `state` + `second_approval_state` | field | `first_approver_id`(emp) → `second_approver_id`(emp) | `hr_expense.hr_expense_actions_my_all` | 3 |
| 2 | ใบขอซื้อ | `purchase.request` | `state` | field | `assigned_to`(user) | `purchase_request.purchase_request_form_action` | 3 |
| 3 | ลงนามเอกสาร | `od19.document.signer` | `state` | field | `partner_id`(partner) | `od19_document_sign.action_od19_document` | 5 |
| 4 | เอกสาร ISO | `od19.iso.document` | `status` | field | `reviewer_id` → `approver_id` → `final_approver_id` (user) | `od19_iso_document_control.action_iso_document` | 5 |
| 5 | แผนตรวจสอบ ISO | `od19.iso.audit.program` | `state` | field | — (pool: ไม่มีฟิลด์ผู้อนุมัติ) | `od19_iso_internal_audit.action_iso_audit_program` | 7 |
| 6 | NC/CAPA | `od19.iso.nonconformity` | `state` | field | `verified_by_id`(user) | `od19_iso_nonconformity.action_iso_nc` | 14 |
| 7 | ความเสี่ยง ISO | `od19.iso.risk` | `state` | field | `risk_owner_id`(user, ใกล้สุด) | `od19_iso_risk.action_iso_risk` | 14 |
| 8 | สอบเทียบ ISO | `od19.iso.calibration.record` | `status` | field | `technician_id`(emp) | `od19_iso_calibration.action_iso_calibration_record` | 7 |
| 9 | ใบสั่งขาย | `sale.order` | `state` | tier_validation | `review_ids` | `sale.action_orders` | 3 |
| 10 | ขนส่ง | `od19.transport.order` | `state` | tier_validation | `review_ids` | `od19_transportation.action_od19_transport_order` | 3 |
| 11 | ใบสำคัญจ่าย | `account.payment` | `od19_prepare_state` | field | — (pool: `od19_approved_by` เซ็ตตอนอนุมัติแล้ว) | `account.action_account_payments` | 2 |
| 12 | ปรับมูลค่าสต็อก | `od19.stock.valuation.adjustment` | `state` | field | — (pool: `approved_by` เซ็ตตอนอนุมัติแล้ว) | `od19_stock_valuation_adjustment.stock_valuation_adjustment_action` | 5 |
| 13 | นับสต็อก | `od19.stock.count.session` | `state` | field | — (pool: `approved_by` เซ็ตตอนอนุมัติแล้ว) | `od19_inventory_audit_count.od19_stock_count_session_action` | 5 |

**ค่า state ที่ยืนยันแล้ว (จากโค้ดจริง):**

| โมเดล | state values |
|---|---|
| `hr.expense` | `draft` / `submitted` / `approved` / `posted` / `in_payment` / `paid` / `refused`; `second_approval_state`: `not_required`/`pending`/`approved`/`refused` |
| `purchase.request` | `draft` / `to_approve` / `approved` / `in_progress` / `done` / `rejected` |
| `od19.document.signer` | `draft` / `sent` / `signed` / `refused` |
| `od19.iso.document` (`status`) | `draft` / `review` / `approval` / `final_approval` / `approved` / `rejected` / `obsolete` |
| `od19.iso.audit.program` | `draft` / `approved` / `closed` |
| `od19.iso.nonconformity` | `draft` / `open` / `analysis` / `action` / `verification` / `closed` / `cancel` |
| `od19.iso.risk` | `draft` / `identified` / `analyzed` / `evaluated` / `treated` / `monitored` / `closed` / `cancel` |
| `od19.iso.calibration.record` (`status`) | `draft` / `scheduled` / `in_progress` / `passed` / `failed` / `cancelled` |
| `account.payment` (`od19_prepare_state`) | `draft` / `prepared` / `approved` |
| `od19.stock.valuation.adjustment` | `draft` / `confirmed` / `done` / `cancelled` |
| `od19.stock.count.session` | `scheduled` / `counted` / `pending_approval` / `adjusted` / `reviewed` / `cancelled` |
| `tier.review.status` | `waiting` / `pending` / `rejected` / `approved` / `cancel` |

> `first_approver_id` (hr.employee) มาจาก `od19_hr_expense_enhanced`; `second_approver_id` (hr.employee) มาจาก `od19_hr_expense_thai` — ตรวจ existence แบบ fail-soft ตอนอ่าน
>
> **กองกลาง (shared pool, D10)**: 4 แหล่ง (#5, #11, #12, #13) ไม่มีฟิลด์ผู้อนุมัติที่ถูกเซ็ต *ก่อน* อนุมัติ จึงไม่ตั้ง `approver_field` → ผู้ใช้ภายในทุกคนเห็นเป็น *คงค้าง* (seed จะล้าง `approver_field` ให้อัตโนมัติถ้าฟิลด์ไม่มีจริงบนโมเดล)

---

## PART A — โมดูลใหม่ `od19_approval_center`

### Task 1: Scaffold module + security

**Files:**
- Create: `custom_addons/od19_approval_center/__init__.py`
- Create: `custom_addons/od19_approval_center/__manifest__.py`
- Create: `custom_addons/od19_approval_center/models/__init__.py`
- Create: `custom_addons/od19_approval_center/hooks.py` (stub)
- Create: `custom_addons/od19_approval_center/security/od19_approval_security.xml`
- Create: `custom_addons/od19_approval_center/security/ir.model.access.csv`
- Create: `custom_addons/od19_approval_center/data/approval_sources.py` (stub `APPROVAL_SOURCES = []`)
- Create: `custom_addons/od19_approval_center/tests/__init__.py`

- [ ] **Step 1: สร้าง `__manifest__.py`**

```python
{
    "name": "OD19 Approval Center",
    "summary": "Config-driven, view-only approval visibility across modules",
    "version": "19.0.1.0.0",
    "category": "Productivity",
    "author": "The Auto-Info Co., Ltd.",
    "license": "LGPL-3",
    "depends": ["base", "mail"],
    "data": [
        "security/od19_approval_security.xml",
        "security/ir.model.access.csv",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": True,
    "auto_install": False,
}
```

- [ ] **Step 2: สร้าง `__init__.py` ราก**

```python
from . import models
from .hooks import post_init_hook
```

> **หมายเหตุ (แก้ระหว่าง execute):** manifest `data` มีแค่ 2 ไฟล์ security เท่านั้น — `views/*.xml` ยังไม่มีจนถึง Task 10 (ถ้าใส่ตอนนี้ `-i` จะล้มด้วย missing file)

- [ ] **Step 3: สร้าง `hooks.py` (stub ชั่วคราว)**

```python
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Seeded in Task 9."""
    return True
```

- [ ] **Step 4: สร้าง `models/__init__.py`**

```python
# Uncommented in Task 2 once the model files exist.
# from . import od19_approval_step
# from . import od19_approval_source
```

> **หมายเหตุ (แก้ระหว่าง execute):** คอมเมนต์ import ไว้ เพราะไฟล์โมเดลจริงยังไม่มีจนถึง Task 2 (ถ้าไม่คอมเมนต์ การโหลด package จะล้ม)

- [ ] **Step 5: สร้าง security XML**

`security/od19_approval_security.xml` (Odoo 19 ใช้ `res.groups.privilege` — `res.groups.category_id` ถูกถอดออกแล้ว):

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="module_category_od19_approval_center" model="ir.module.category">
        <field name="name">Approval Center</field>
        <field name="sequence">90</field>
    </record>

    <record id="privilege_od19_approval_center" model="res.groups.privilege">
        <field name="name">Approval Center</field>
        <field name="category_id" ref="module_category_od19_approval_center"/>
    </record>

    <record id="group_approval_admin" model="res.groups">
        <field name="name">Approval Center Administrator</field>
        <field name="privilege_id" ref="privilege_od19_approval_center"/>
    </record>
</odoo>
```

- [ ] **Step 6: สร้าง access CSV (header-only ชั่วคราว)**

`security/ir.model.access.csv`:

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
```

> **หมายเหตุ (แก้ระหว่าง execute):** ยังไม่ใส่ 2 แถว access เพราะ external id `model_od19_approval_source`/`model_od19_approval_step` จะมีก็ต่อเมื่อโมเดลถูก register (Task 2) — ใส่แถวใน Task 2

- [ ] **Step 7: สร้าง `data/approval_sources.py` (stub) + `tests/__init__.py`**

`data/approval_sources.py`:

```python
"""Initial Approval Center sources. Filled with 13 sources in Task 8."""

APPROVAL_SOURCES = []
```

`tests/__init__.py`:

```python
from . import test_approval_buckets
from . import test_approval_seed
```

- [ ] **Step 8: สร้างไฟล์เทสต์ว่างเพื่อให้ import ผ่าน**

สร้าง `tests/test_approval_buckets.py` และ `tests/test_approval_seed.py` มีเนื้อหาเริ่มต้น:

```python
from odoo.tests.common import TransactionCase


class TestApprovalPlaceholder(TransactionCase):
    def test_placeholder(self):
        self.assertTrue(True)
```

> **หมายเหตุ (แก้ระหว่าง execute):** ใช้ชื่อคลาสต่างกันต่อไฟล์ (`TestApprovalPlaceholder` ใน `test_approval_buckets.py`, `TestApprovalSeedPlaceholder` ใน `test_approval_seed.py`) เพื่อเลี่ยง Odoo duplicate-class warning

- [ ] **Step 9: ตรวจว่า Odoo โหลด manifest ได้**

Run: `python odoo-bin -c odoo.conf -d odoo19_pdev --stop-after-init --http-port=8075` (ยังไม่ต้อง `-i`)
Expected: ไม่มี error ตอน parse manifest (module ยังไม่ติดตั้ง แต่ path ต้อง valid)

- [ ] **Step 10: Commit**

```bash
git add custom_addons/od19_approval_center
git commit -m "feat(od19_approval_center): scaffold module skeleton and security"
```

---

### Task 2: Config models — `od19.approval.step` + `od19.approval.source`

**Files:**
- Create: `custom_addons/od19_approval_center/models/od19_approval_step.py`
- Create: `custom_addons/od19_approval_center/models/od19_approval_source.py`
- Test: `custom_addons/od19_approval_center/tests/test_approval_buckets.py`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน (โมเดล + ฟิลด์)**

```python
from odoo.tests.common import TransactionCase


class TestApprovalConfig(TransactionCase):
    def test_models_and_defaults(self):
        source = self.env["od19.approval.source"].create({
            "name": "Unit Source",
            "model_id": self.env["ir.model"]._get("hr.expense").id,
        })
        self.assertEqual(source.strategy, "field")
        self.assertEqual(source.requester_kind, "user")
        self.assertEqual(source.sla_days, 0)
        self.assertTrue(source.active)

        step = self.env["od19.approval.step"].create({
            "source_id": source.id,
            "label": "Step 1",
            "state_value": "submitted",
            "approver_field": "create_uid",
        })
        self.assertEqual(step.state_field, "state")
        self.assertEqual(step.approver_kind, "user")
        self.assertEqual(step.sequence, 10)
        self.assertIn(step, source.step_ids)
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า FAIL**

Run: `python odoo-bin -c odoo.conf -d odoo19_pdev -u od19_approval_center --test-enable --test-tags /od19_approval_center --stop-after-init --http-port=8075`
Expected: FAIL — `KeyError`/`ValueError` เพราะโมเดลยังไม่มี

- [ ] **Step 3: สร้าง `models/od19_approval_step.py`**

```python
from odoo import fields, models


class Od19ApprovalStep(models.Model):
    _name = "od19.approval.step"
    _description = "Approval Center Step"
    _order = "source_id, sequence, id"

    source_id = fields.Many2one(
        "od19.approval.source", string="Source", required=True, ondelete="cascade"
    )
    sequence = fields.Integer(default=10)
    label = fields.Char(required=True)
    state_field = fields.Char(
        default="state", help="Field holding the state this step waits on."
    )
    state_value = fields.Char(
        required=True, help="State value while the record waits at this step."
    )
    approver_field = fields.Char(
        help="Field holding the approver on the record. Leave empty for a "
             "shared pool step (visible to every internal user)."
    )
    approver_kind = fields.Selection(
        [("user", "User"), ("employee", "Employee"), ("partner", "Partner")],
        default="user",
        required=True,
    )
```

- [ ] **Step 4: สร้าง `models/od19_approval_source.py` (เฉพาะฟิลด์)**

```python
from odoo import fields, models


class Od19ApprovalSource(models.Model):
    _name = "od19.approval.source"
    _description = "Approval Center Source"
    _order = "sequence, id"

    OD19_MAX_RECORDS = 500

    name = fields.Char(required=True)
    model_id = fields.Many2one(
        "ir.model", string="Model", required=True, ondelete="cascade"
    )
    model_name = fields.Char(related="model_id.model", store=True, string="Model Name")
    icon = fields.Char(default="fa-inbox")
    action_xmlid = fields.Char(string="Action XML ID")
    sequence = fields.Integer(default=10)
    requester_field = fields.Char(default="create_uid")
    requester_kind = fields.Selection(
        [("user", "User"), ("employee", "Employee")], default="user", required=True
    )
    submitted_date_field = fields.Char(default="create_date")
    decided_date_field = fields.Char()
    rejected_states = fields.Char(help="Comma separated state values meaning rejected.")
    success_states = fields.Char(help="Comma separated state values meaning success.")
    strategy = fields.Selection(
        [("field", "Field"), ("tier_validation", "Tier Validation")],
        default="field",
        required=True,
    )
    sla_days = fields.Integer(default=0, help="0 = no SLA warning.")
    active = fields.Boolean(default=True)
    step_ids = fields.One2many("od19.approval.step", "source_id", string="Steps")
```

- [ ] **Step 4b: เปิด import โมเดล + ใส่ access CSV rows (แก้ระหว่าง execute)**

เปิด import ใน `models/__init__.py`:
```python
from . import od19_approval_step
from . import od19_approval_source
```

เพิ่ม 2 แถวใน `security/ir.model.access.csv` (external id จะมีแล้วหลังโมเดลถูก register):
```csv
access_od19_approval_source_admin,od19.approval.source admin,model_od19_approval_source,group_approval_admin,1,1,1,1
access_od19_approval_step_admin,od19.approval.step admin,model_od19_approval_step,group_approval_admin,1,1,1,1
```

- [ ] **Step 5: รันเทสต์ให้ PASS**

Run: same as Step 2
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add custom_addons/od19_approval_center
git commit -m "feat(od19_approval_center): add config models source and step"
```

---

### Task 3: กลุ่ม "คงค้าง" (strategy=field, ขั้นเดียว)

**Files:**
- Modify: `custom_addons/od19_approval_center/models/od19_approval_source.py`
- Test: `custom_addons/od19_approval_center/tests/test_approval_buckets.py`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

เพิ่มใน `tests/test_approval_buckets.py`:

```python
from odoo import fields
from odoo.tests.common import TransactionCase


class TestPendingBucket(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.approver = cls.env["res.users"].create({
            "name": "Approver A", "login": "approver_a",
        })
        cls.other = cls.env["res.users"].create({
            "name": "Other B", "login": "other_b",
        })
        cls.expense = cls.env["hr.expense"].create({
            "name": "Taxi",
            "employee_id": cls.env.user.employee_id.id or False,
        })
        cls.source = cls.env["od19.approval.source"].create({
            "name": "Expense Test",
            "model_id": cls.env["ir.model"]._get("hr.expense").id,
            "strategy": "field",
            "requester_field": "create_uid",
            "requester_kind": "user",
            "rejected_states": "refused",
            "success_states": "approved,posted,in_payment,paid",
            "step_ids": [(0, 0, {
                "sequence": 10, "label": "Approve",
                "state_field": "state", "state_value": "submitted",
                "approver_field": "create_uid", "approver_kind": "user",
            })],
        })

    def test_pending_only_for_the_approver(self):
        # The record waits at 'submitted'; the approver field is create_uid.
        self.expense.write({"state": "submitted"})
        buckets = self.source.with_user(self.env.user)._od19_classify_for_approver()
        pending_ids = [r.id for r in buckets["pending"]]
        self.assertIn(self.expense.id, pending_ids)

    def test_other_user_sees_nothing(self):
        self.expense.write({"state": "submitted"})
        buckets = self.source.with_user(self.other)._od19_classify_for_approver()
        self.assertEqual(buckets["pending"], [])
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า FAIL**

Run: `python odoo-bin -c odoo.conf -d odoo19_pdev -u od19_approval_center --test-enable --test-tags /od19_approval_center --stop-after-init --http-port=8075`
Expected: FAIL — `AttributeError: 'od19.approval.source' object has no attribute '_od19_classify_for_approver'`

- [ ] **Step 3: เพิ่ม helper + `_od19_classify_for_approver()`**

ต่อท้ายคลาส `Od19ApprovalSource` ใน `models/od19_approval_source.py`:

```python
    # ------------------------------------------------------------------
    # Low level helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _od19_csv(value):
        if not value:
            return []
        return [token.strip() for token in value.split(",") if token.strip()]

    def _od19_me_ids(self, kind):
        """Return the current user/employee/partner id for ``kind`` (0 if none)."""
        user = self.env.user
        if kind == "employee":
            return user.employee_id.id if "employee_id" in user._fields else 0
        if kind == "partner":
            return user.partner_id.id or 0
        return user.id or 0

    def _od19_ready(self):
        self.ensure_one()
        return bool(self.model_name) and self.model_name in self.env

    def _od19_main_state_field(self, steps):
        return steps[0].state_field or "state" if steps else "state"

    def _od19_field_ok(self, record, field_name):
        return bool(field_name) and field_name in record._fields

    def _od19_current_index(self, record, steps):
        """Index of the step the record waits at, or None."""
        for index, step in enumerate(steps):
            field_name = step.state_field or "state"
            if self._od19_field_ok(record, field_name) and record[field_name] == step.state_value:
                return index
        return None

    def _od19_index_of_my_step(self, record, steps):
        """Index of the first step where the current user is the approver, or None."""
        for index, step in enumerate(steps):
            if not self._od19_field_ok(record, step.approver_field):
                continue
            me_id = self._od19_me_ids(step.approver_kind)
            value = record[step.approver_field]
            if me_id and value and value.id == me_id:
                return index
        return None

    def _od19_classify_for_approver(self):
        """Return the 4 approver buckets for the current user (strategy=field)."""
        self.ensure_one()
        buckets = {"pending": [], "incoming": [], "done": [], "rejected": []}
        if not self._od19_ready():
            return buckets
        steps = self.step_ids.sorted("sequence")
        if not steps:
            return buckets
        Model = self.env[self.model_name].sudo()
        rejected = self._od19_csv(self.rejected_states)
        success = self._od19_csv(self.success_states)
        main_field = self._od19_main_state_field(steps)
        records = Model.search([], limit=self.OD19_MAX_RECORDS)
        for record in records:
            my_index = self._od19_index_of_my_step(record, steps)
            if my_index is None:
                continue
            state_value = record[main_field] if self._od19_field_ok(record, main_field) else False
            if state_value in rejected:
                buckets["rejected"].append(record)
                continue
            if state_value in success:
                buckets["done"].append(record)
                continue
            current = self._od19_current_index(record, steps)
            if current is None:
                continue
            if current == my_index:
                buckets["pending"].append(record)
            elif current < my_index:
                buckets["incoming"].append(record)
        return buckets
```

- [ ] **Step 4: รันเทสต์ให้ PASS**

Run: same as Step 2
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_approval_center
git commit -m "feat(od19_approval_center): classify pending records for the approver"
```

---

### Task 4: multi-step → กลุ่ม "กำลังมาถึง"

**Files:**
- Test: `custom_addons/od19_approval_center/tests/test_approval_buckets.py`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

เพิ่มคลาสใหม่:

```python
class TestIncomingBucket(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.expense = cls.env["hr.expense"].create({"name": "Hotel"})
        cls.source = cls.env["od19.approval.source"].create({
            "name": "Two Tier",
            "model_id": cls.env["ir.model"]._get("hr.expense").id,
            "requester_field": "create_uid",
            "success_states": "approved",
            "rejected_states": "refused",
            "step_ids": [
                (0, 0, {
                    "sequence": 10, "label": "L1", "state_field": "state",
                    "state_value": "submitted", "approver_field": "first_approver_id",
                    "approver_kind": "user",
                }),
                (0, 0, {
                    "sequence": 20, "label": "L2", "state_field": "state",
                    "state_value": "approved", "approver_field": "second_approver_id",
                    "approver_kind": "user",
                }),
            ],
        })

    def test_level2_approver_sees_incoming_not_pending(self):
        first = self.env["res.users"].create({"name": "L1", "login": "l1_user"})
        second = self.env["res.users"].create({"name": "L2", "login": "l2_user"})
        self.expense.write({
            "state": "submitted",
            "first_approver_id": first.id,
            "second_approver_id": second.id,
        })
        buckets = self.source.with_user(second)._od19_classify_for_approver()
        self.assertIn(self.expense.id, [r.id for r in buckets["incoming"]])
        self.assertNotIn(self.expense.id, [r.id for r in buckets["pending"]])
        # The level 1 approver is the actionable one.
        l1 = self.source.with_user(first)._od19_classify_for_approver()
        self.assertIn(self.expense.id, [r.id for r in l1["pending"]])
```

> หมายเหตุ: `first_approver_id`/`second_approver_id` เป็น Many2one `hr.employee`. ปรับ test ให้สร้าง `hr.employee` และใช้ `.user_id` แทนถ้า field ไม่รับ `res.users` — เมื่อ implement จริงให้ยึดชนิดฟิลด์จริง (`_od19_me_ids("employee")` เทียบกับ `user.employee_id`)

- [ ] **Step 2: รันเทสต์ให้เห็นว่า FAIL**

Run: `python odoo-bin -c odoo.conf -d odoo19_pdev -u od19_approval_center --test-enable --test-tags /od19_approval_center --stop-after-init --http-port=8075`
Expected: FAIL — กลุ่ม `incoming` ว่าง (ตรรกะยังไม่ครบ / approver_kind ไม่ตรงชนิดฟิลด์)

- [ ] **Step 3: ปรับ `_od19_classify_for_approver()` ให้รองรับ multi-step**

โค้ดใน Task 3 ครอบ multi-step แล้ว (`current < my_index` → incoming) จุดที่ต้องแก้คือ **การเทียบ approver_kind กับชนิดฟิลด์จริง** ให้เทียบแบบ type-safe โดย `_od19_me_ids` คืน id ของ user/employee/partner ตาม `approver_kind` แล้วเทียบกับ `value.id` ซึ่งเป็น id ของโมเดลปลายทาง (res.users หรือ hr.employee) — แก้ `_od19_index_of_my_step` ให้เลือก id ตามชนิดของ comodel ของฟิลด์นั้น:

```python
    def _od19_index_of_my_step(self, record, steps):
        """Index of the first step where the current user is the approver, or None."""
        for index, step in enumerate(steps):
            if not self._od19_field_ok(record, step.approver_field):
                continue
            value = record[step.approver_field]
            if not value:
                continue
            comodel = record._fields[step.approver_field].comodel_name
            me_id = self._od19_me_ids_for_comodel(comodel, step.approver_kind)
            if me_id and value.id == me_id:
                return index
        return None

    def _od19_me_ids_for_comodel(self, comodel, kind):
        """Map the current user onto the comodel stored by the approver field."""
        user = self.env.user
        if comodel == "hr.employee":
            return user.employee_id.id if "employee_id" in user._fields else 0
        if comodel == "res.partner":
            return user.partner_id.id or 0
        if comodel == "res.users":
            return user.id or 0
        return self._od19_me_ids(kind)
```

- [ ] **Step 4: รันเทสต์ให้ PASS**

Run: same as Step 2
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_approval_center
git commit -m "feat(od19_approval_center): support multi-step incoming bucket"
```

---

### Task 5: แท็บผู้ขอ (requester) + อายุ + SLA

**Files:**
- Modify: `custom_addons/od19_approval_center/models/od19_approval_source.py`
- Test: `custom_addons/od19_approval_center/tests/test_approval_buckets.py`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

```python
import datetime

from odoo import fields
from odoo.tests.common import TransactionCase


class TestRequesterAndAge(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.source = cls.env["od19.approval.source"].create({
            "name": "Age Source",
            "model_id": cls.env["ir.model"]._get("hr.expense").id,
            "requester_field": "create_uid",
            "requester_kind": "user",
            "submitted_date_field": "create_date",
            "success_states": "approved",
            "rejected_states": "refused",
            "sla_days": 3,
            "step_ids": [(0, 0, {
                "sequence": 10, "label": "L1", "state_field": "state",
                "state_value": "submitted", "approver_field": "create_uid",
                "approver_kind": "user",
            })],
        })

    def test_requester_sees_own_pending(self):
        expense = self.env["hr.expense"].create({"name": "My Expense"})
        expense.write({"state": "submitted"})
        buckets = self.source.with_user(self.env.user)._od19_classify_for_requester()
        self.assertIn(expense.id, [r.id for r in buckets["pending"]])

    def test_age_days_from_submitted_field(self):
        expense = self.env["hr.expense"].create({"name": "Old"})
        expense.write({
            "state": "submitted",
            "create_date": fields.Datetime.now() - datetime.timedelta(days=5),
        })
        self.assertEqual(self.source._od19_age_days(expense), 5)

    def test_sla_state_thresholds(self):
        self.assertEqual(self.source._od19_sla_state(1), "normal")
        self.assertEqual(self.source._od19_sla_state(3), "warning")
        self.assertEqual(self.source._od19_sla_state(6), "over")
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า FAIL**

Run: `python odoo-bin -c odoo.conf -d odoo19_pdev -u od19_approval_center --test-enable --test-tags /od19_approval_center --stop-after-init --http-port=8075`
Expected: FAIL — `AttributeError` (`_od19_classify_for_requester` / `_od19_age_days` / `_od19_sla_state` ไม่มี)

- [ ] **Step 3: เพิ่มเมธอด**

ต่อท้ายคลาส `Od19ApprovalSource`:

```python
    def _od19_classify_for_requester(self):
        """Return the 4 requester buckets for the current user."""
        self.ensure_one()
        buckets = {"pending": [], "incoming": [], "done": [], "rejected": []}
        if not self._od19_ready():
            return buckets
        if not self._od19_field_ok(self.env[self.model_name], self.requester_field):
            return buckets
        me_id = self._od19_me_ids(self.requester_kind)
        if not me_id:
            return buckets
        steps = self.step_ids.sorted("sequence")
        rejected = self._od19_csv(self.rejected_states)
        success = self._od19_csv(self.success_states)
        main_field = self._od19_main_state_field(steps)
        records = self.env[self.model_name].sudo().search(
            [(self.requester_field, "=", me_id)], limit=self.OD19_MAX_RECORDS
        )
        for record in records:
            state_value = record[main_field] if self._od19_field_ok(record, main_field) else False
            if state_value in rejected:
                buckets["rejected"].append(record)
            elif state_value in success:
                buckets["done"].append(record)
            else:
                current = self._od19_current_index(record, steps)
                if current is not None and current > 0:
                    buckets["incoming"].append(record)
                else:
                    buckets["pending"].append(record)
        return buckets

    def _od19_age_days(self, record):
        """Whole days between the submitted date and now (0 if unknown)."""
        field_name = self.submitted_date_field or "create_date"
        if not self._od19_field_ok(record, field_name):
            field_name = "create_date"
        start = record[field_name]
        if not start:
            return 0
        if isinstance(start, datetime.date) and not isinstance(start, datetime.datetime):
            start = datetime.datetime.combine(start, datetime.time.min)
        delta = fields.Datetime.now() - start
        return max(int(delta.total_seconds() // 86400), 0)

    def _od19_sla_state(self, age_days):
        if not self.sla_days:
            return "normal"
        if age_days >= 2 * self.sla_days:
            return "over"
        if age_days >= self.sla_days:
            return "warning"
        return "normal"
```

เพิ่ม import ที่หัวไฟล์:

```python
import datetime

from odoo import fields, models
```

- [ ] **Step 4: รันเทสต์ให้ PASS**

Run: same as Step 2
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_approval_center
git commit -m "feat(od19_approval_center): requester buckets with age and SLA"
```

---

## PART B — เก็บรายละเอียด config + presentation

### Task 6: Presentation layer (rows + summary) + furthest-step refinement

**Files:**
- Modify: `custom_addons/od19_approval_center/models/od19_approval_source.py`
- Test: `custom_addons/od19_approval_center/tests/test_approval_buckets.py`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

เพิ่มใน `tests/test_approval_buckets.py`:

```python
import datetime

from odoo import fields
from odoo.tests.common import TransactionCase


class TestRowsAndSummary(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.source = cls.env["od19.approval.source"].create({
            "name": "Rows Source",
            "model_id": cls.env["ir.model"]._get("hr.expense").id,
            "requester_field": "create_uid",
            "success_states": "approved",
            "rejected_states": "refused",
            "sla_days": 3,
            "step_ids": [(0, 0, {
                "sequence": 10, "label": "L1", "state_field": "state",
                "state_value": "submitted", "approver_field": "create_uid",
                "approver_kind": "user",
            })],
        })

    def test_row_carries_deep_link_age_and_sla(self):
        expense = self.env["hr.expense"].create({"name": "Paper"})
        expense.write({
            "state": "submitted",
            "create_date": fields.Datetime.now() - datetime.timedelta(days=7),
        })
        rows = self.source._od19_build_rows(expense)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], expense.id)
        self.assertEqual(rows[0]["model"], "hr.expense")
        self.assertIn("/web#id=%s" % expense.id, rows[0]["url"])
        self.assertEqual(rows[0]["age_days"], 7)
        self.assertEqual(rows[0]["sla_state"], "over")
        self.assertEqual(rows[0]["label"], "Paper")

    def test_summary_kpis(self):
        buckets = self.source._od19_classify_for_approver()
        rows = self.source._od19_build_rows(buckets["pending"])
        summary = self.source._od19_summary(rows)
        self.assertEqual(summary["pending_count"], len(rows))
        self.assertIn("max_age_days", summary)
        self.assertIn("over_sla_count", summary)


class TestFurthestStep(TransactionCase):
    """`_od19_current_index` must report the furthest step the record reached."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.source = cls.env["od19.approval.source"].create({
            "name": "Furthest",
            "model_id": cls.env["ir.model"]._get("hr.expense").id,
            "step_ids": [
                (0, 0, {
                    "sequence": 10, "label": "L1", "state_field": "state",
                    "state_value": "submitted", "approver_field": "first_approver_id",
                    "approver_kind": "employee",
                }),
                (0, 0, {
                    "sequence": 20, "label": "L2",
                    "state_field": "second_approval_state", "state_value": "pending",
                    "approver_field": "second_approver_id", "approver_kind": "employee",
                }),
            ],
        })

    def test_highest_matching_step_wins(self):
        if "second_approval_state" not in self.env["hr.expense"]._fields:
            self.skipTest("od19_hr_expense_thai not installed")
        expense = self.env["hr.expense"].create({"name": "Two tier"})
        expense.write({"state": "submitted", "second_approval_state": "pending"})
        steps = self.source.step_ids.sorted("sequence")
        self.assertEqual(self.source._od19_current_index(expense, steps), 1)
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า FAIL**

Run: `python odoo-bin -c odoo.conf -d odoo19_pdev -u od19_approval_center --test-enable --test-tags /od19_approval_center --stop-after-init --http-port=8075`
Expected: FAIL — `AttributeError` (`_od19_build_rows` ไม่มี) และ `test_highest_matching_step_wins` ได้ 0 แทน 1

- [ ] **Step 3: แก้ `_od19_current_index` ให้คืนขั้น "ไกลสุด" + เพิ่ม rows/summary**

แก้ import หัวไฟล์เป็น `from odoo import api, fields, models` แล้ว**แทนที่** `_od19_current_index` เดิม (PART A) ด้วยเวอร์ชันที่คืน index **สูงสุด** ที่ตรง:

```python
    def _od19_current_index(self, record, steps):
        """Index of the furthest step the record has reached, or None.

        A record can match several steps at once (e.g. ``hr.expense`` keeps
        ``state='submitted'`` while ``second_approval_state='pending'``), so we
        return the highest matching index -- the real current step.
        """
        current = None
        for index, step in enumerate(steps):
            field_name = step.state_field or "state"
            if self._od19_field_ok(record, field_name) and record[field_name] == step.state_value:
                current = index
        return current
```

ต่อท้ายคลาส `Od19ApprovalSource`:

```python
    # ------------------------------------------------------------------
    # Presentation layer (dict rows consumed by QWeb)
    # ------------------------------------------------------------------
    def _od19_record_label(self, record):
        for field_name in ("name", "display_name"):
            if self._od19_field_ok(record, field_name) and record[field_name]:
                return str(record[field_name])
        return "ID %s" % record.id

    def _od19_deep_link(self, record):
        return "/web#id=%s&model=%s&view_type=form" % (record.id, self.model_name)

    def _od19_build_rows(self, records):
        """Turn a recordset into plain dicts (safe to pass to QWeb)."""
        rows = []
        for record in records:
            age_days = self._od19_age_days(record)
            rows.append({
                "id": record.id,
                "source_name": self.name,
                "icon": self.icon or "fa-inbox",
                "model": self.model_name,
                "model_label": self.model_id.name,
                "label": self._od19_record_label(record),
                "url": self._od19_deep_link(record),
                "age_days": age_days,
                "sla_state": self._od19_sla_state(age_days),
            })
        return rows

    @api.model
    def _od19_summary(self, rows):
        """Aggregate KPI over a list of row dicts (approver *pending*)."""
        ages = [row["age_days"] for row in rows]
        return {
            "pending_count": len(rows),
            "max_age_days": max(ages) if ages else 0,
            "over_sla_count": len([row for row in rows if row["sla_state"] == "over"]),
        }
```

- [ ] **Step 4: รันเทสต์ให้ PASS**

Run: same as Step 2
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_approval_center
git commit -m "feat(od19_approval_center): row dicts, summary KPIs and furthest-step fix"
```

---

### Task 7: shared pool steps (ขั้นที่ไม่มี `approver_field`)

**Files:**
- Modify: `custom_addons/od19_approval_center/models/od19_approval_source.py`
- Test: `custom_addons/od19_approval_center/tests/test_approval_buckets.py`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

```python
class TestSharedPoolStep(TransactionCase):
    """A step without approver_field is actionable by every internal user."""

    def test_pool_step_is_pending_for_anyone(self):
        source = self.env["od19.approval.source"].create({
            "name": "Pool Source",
            "model_id": self.env["ir.model"]._get("hr.expense").id,
            "success_states": "approved",
            "rejected_states": "refused",
            "step_ids": [(0, 0, {
                "sequence": 10, "label": "Any approver", "state_field": "state",
                "state_value": "submitted",
            })],
        })
        expense = self.env["hr.expense"].create({"name": "Pool doc"})
        expense.write({"state": "submitted"})
        other = self.env["res.users"].create({"name": "Pool Z", "login": "pool_z"})
        buckets = source.with_user(other)._od19_classify_for_approver()
        self.assertIn(expense.id, [r.id for r in buckets["pending"]])
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า FAIL**

Run: `python odoo-bin -c odoo.conf -d odoo19_pdev -u od19_approval_center --test-enable --test-tags /od19_approval_center --stop-after-init --http-port=8075`
Expected: FAIL — กลุ่ม `pending` ว่าง (`_od19_index_of_my_step` ข้าม step ที่ไม่มี approver_field)

- [ ] **Step 3: รองรับ pool step**

แก้ `_od19_index_of_my_step` ให้คืน index ทันทีเมื่อ step ไม่มี `approver_field` (กองกลาง, D10):

```python
    def _od19_index_of_my_step(self, record, steps):
        """Index of the first step this user acts on, or None.

        A step with no ``approver_field`` is a shared pool step: it is the
        current user's step for every internal user.
        """
        for index, step in enumerate(steps):
            if not step.approver_field:
                return index
            if not self._od19_field_ok(record, step.approver_field):
                continue
            value = record[step.approver_field]
            if not value:
                continue
            comodel = record._fields[step.approver_field].comodel_name
            me_id = self._od19_me_ids_for_comodel(comodel, step.approver_kind)
            if me_id and value.id == me_id:
                return index
        return None
```

- [ ] **Step 4: รันเทสต์ให้ PASS**

Run: same as Step 2
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_approval_center
git commit -m "feat(od19_approval_center): shared pool steps without approver_field"
```

---

### Task 8: strategy = `tier_validation`

**Files:**
- Modify: `custom_addons/od19_approval_center/models/od19_approval_source.py`
- Test: `custom_addons/od19_approval_center/tests/test_approval_buckets.py`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

```python
from odoo.tests.common import TransactionCase


class TestTierStrategy(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.source = cls.env["od19.approval.source"].create({
            "name": "Tier Source",
            "model_id": cls.env["ir.model"]._get("sale.order").id,
            "strategy": "tier_validation",
            "requester_field": "create_uid",
            "rejected_states": "cancel",
            "success_states": "sale",
        })
        cls.order = cls.env["sale.order"].create({
            "partner_id": cls.env["res.partner"].create({"name": "SO Partner"}).id,
        })
        cls.definition = cls.env["tier.definition"].create({
            "name": "SO Tier Test",
            "model_id": cls.env["ir.model"]._get("sale.order").id,
            "review_type": "individual",
            "reviewer_id": cls.env.user.id,
        })

    def _make_review(self, status):
        return self.env["tier.review"].create({
            "model": "sale.order",
            "res_id": self.order.id,
            "status": status,
            "sequence": 1,
            "definition_id": self.definition.id,
        })

    def test_pending_review_is_pending_bucket(self):
        self._make_review("pending")
        buckets = self.source._od19_classify_tier_for_approver()
        self.assertIn(self.order.id, [r.id for r in buckets["pending"]])

    def test_waiting_review_is_incoming_bucket(self):
        self._make_review("waiting")
        buckets = self.source._od19_classify_tier_for_approver()
        self.assertIn(self.order.id, [r.id for r in buckets["incoming"]])
        self.assertNotIn(self.order.id, [r.id for r in buckets["pending"]])

    def test_other_reviewer_sees_nothing(self):
        self._make_review("pending")
        other = self.env["res.users"].create({"name": "No Tier", "login": "no_tier"})
        buckets = self.source.with_user(other)._od19_classify_tier_for_approver()
        self.assertEqual(buckets["pending"], [])
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า FAIL**

Run: `python odoo-bin -c odoo.conf -d odoo19_pdev -u od19_approval_center --test-enable --test-tags /od19_approval_center --stop-after-init --http-port=8075`
Expected: FAIL — `AttributeError: _od19_classify_tier_for_approver`

- [ ] **Step 3: เพิ่มกลยุทธ์ tier_validation + dispatch**

ต่อท้ายคลาส `Od19ApprovalSource`:

```python
    # ------------------------------------------------------------------
    # OCA tier_validation strategy
    # ------------------------------------------------------------------
    OD19_TIER_STATUS_BUCKET = {
        "pending": "pending",
        "waiting": "incoming",
        "approved": "done",
        "rejected": "rejected",
    }
    # Lower value = resolved first when a record has several reviews for me.
    OD19_TIER_STATUS_ORDER = {"pending": 0, "waiting": 1, "rejected": 2, "approved": 3}

    def _od19_classify_tier_for_approver(self):
        """Approver buckets for a tier_validation source, read from tier.review."""
        self.ensure_one()
        buckets = {"pending": [], "incoming": [], "done": [], "rejected": []}
        if not self._od19_ready() or "tier.review" not in self.env:
            return buckets
        reviews = self.env["tier.review"].sudo().search([
            ("model", "=", self.model_name),
            ("reviewer_ids", "in", [self.env.user.id]),
        ])
        seen = {}
        for review in sorted(
            reviews, key=lambda r: self.OD19_TIER_STATUS_ORDER.get(r.status, 9)
        ):
            bucket = self.OD19_TIER_STATUS_BUCKET.get(review.status)
            if not bucket or not review.res_id or review.res_id in seen:
                continue
            record = self.env[self.model_name].sudo().browse(review.res_id)
            if not record.exists():
                continue
            seen[review.res_id] = bucket
            buckets[bucket].append(record)
        return buckets

    def _od19_classify_tier_for_requester(self):
        """Requester buckets for a tier_validation source (state + review history)."""
        self.ensure_one()
        buckets = {"pending": [], "incoming": [], "done": [], "rejected": []}
        Model = self.env[self.model_name].sudo() if self._od19_ready() else None
        if Model is None or not self._od19_field_ok(Model, self.requester_field):
            return buckets
        me_id = self._od19_me_ids(self.requester_kind)
        if not me_id:
            return buckets
        steps = self.step_ids.sorted("sequence")
        main_field = self._od19_main_state_field(steps)
        rejected = self._od19_csv(self.rejected_states)
        success = self._od19_csv(self.success_states)
        records = Model.search(
            [(self.requester_field, "=", me_id)], limit=self.OD19_MAX_RECORDS
        )
        for record in records:
            state_value = record[main_field] if self._od19_field_ok(record, main_field) else False
            if state_value in rejected:
                buckets["rejected"].append(record)
            elif state_value in success:
                buckets["done"].append(record)
            elif "review_ids" in record._fields and any(
                rev.status == "approved" for rev in record.review_ids
            ):
                buckets["incoming"].append(record)
            else:
                buckets["pending"].append(record)
        return buckets
```

จากนั้นเติม dispatch ที่ต้นของทั้งสองเมธอด (หลัง `self.ensure_one()`):

ใน `_od19_classify_for_approver`:

```python
        if self.strategy == "tier_validation":
            return self._od19_classify_tier_for_approver()
```

ใน `_od19_classify_for_requester`:

```python
        if self.strategy == "tier_validation":
            return self._od19_classify_tier_for_requester()
```

- [ ] **Step 4: รันเทสต์ให้ PASS**

Run: same as Step 2
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_approval_center
git commit -m "feat(od19_approval_center): tier_validation strategy via tier.review"
```

---

### Task 9: seed 13 แหล่ง (data + post_init_hook)

**Files:**
- Modify: `custom_addons/od19_approval_center/data/approval_sources.py`
- Modify: `custom_addons/od19_approval_center/hooks.py`
- Test: `custom_addons/od19_approval_center/tests/test_approval_seed.py`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

```python
from odoo.tests.common import TransactionCase

from odoo.addons.od19_approval_center.hooks import post_init_hook


class TestApprovalSeed(TransactionCase):
    def test_seed_is_idempotent(self):
        Source = self.env["od19.approval.source"]
        before = Source.search_count([])
        post_init_hook(self.env)
        self.assertEqual(Source.search_count([]), before)

    def test_expense_source_has_two_steps(self):
        source = self.env["od19.approval.source"].search(
            [("model_name", "=", "hr.expense")], limit=1
        )
        self.assertTrue(source, "hr.expense source should be seeded")
        self.assertEqual(len(source.step_ids), 2)
        self.assertEqual(source.sla_days, 3)

    def test_missing_models_are_skipped(self):
        Source = self.env["od19.approval.source"]
        for source in Source.search([]):
            self.assertIn(
                source.model_name, self.env,
                "seeded source points at a model not installed: %s" % source.model_name,
            )
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า FAIL**

Run: `python odoo-bin -c odoo.conf -d odoo19_pdev -u od19_approval_center --test-enable --test-tags /od19_approval_center --stop-after-init --http-port=8075`
Expected: FAIL — ไม่มี source (stub ยังเป็น `[]`)

- [ ] **Step 3: เขียน `data/approval_sources.py`**

```python
"""Seed data for the Approval Center.

Each entry maps one real approval point to the fields that carry its state and
its approver. ``approver_field`` left empty means a shared pool step (D10).
Field names below were verified against the live code on 2026-11-01.
"""

APPROVAL_SOURCES = [
    {
        "name": "ค่าใช้จ่าย (Expense)",
        "model": "hr.expense",
        "icon": "fa-money",
        "action_xmlid": "hr_expense.hr_expense_actions_my_all",
        "sequence": 10,
        "requester_field": "create_uid",
        "requester_kind": "user",
        "submitted_date_field": "create_date",
        "rejected_states": "refused",
        "success_states": "approved,posted,in_payment,paid",
        "strategy": "field",
        "sla_days": 3,
        "steps": [
            {"sequence": 10, "label": "อนุมัติชั้นที่ 1 (First approval)",
             "state_field": "state", "state_value": "submitted",
             "approver_field": "first_approver_id", "approver_kind": "employee"},
            {"sequence": 20, "label": "อนุมัติชั้นที่ 2 (Second approval)",
             "state_field": "second_approval_state", "state_value": "pending",
             "approver_field": "second_approver_id", "approver_kind": "employee"},
        ],
    },
    {
        "name": "ใบขอซื้อ (Purchase Request)",
        "model": "purchase.request",
        "icon": "fa-shopping-cart",
        "action_xmlid": "purchase_request.purchase_request_form_action",
        "sequence": 20,
        "requester_field": "requested_by",
        "requester_kind": "user",
        "submitted_date_field": "create_date",
        "rejected_states": "rejected",
        "success_states": "approved,in_progress,done",
        "strategy": "field",
        "sla_days": 3,
        "steps": [
            {"sequence": 10, "label": "รออนุมัติ (To approve)",
             "state_field": "state", "state_value": "to_approve",
             "approver_field": "assigned_to", "approver_kind": "user"},
        ],
    },
    {
        "name": "ลงนามเอกสาร (Document Sign)",
        "model": "od19.document.signer",
        "icon": "fa-pencil-square-o",
        "action_xmlid": "od19_document_sign.action_od19_document",
        "sequence": 30,
        "requester_field": "create_uid",
        "requester_kind": "user",
        "submitted_date_field": "create_date",
        "rejected_states": "refused",
        "success_states": "signed",
        "strategy": "field",
        "sla_days": 5,
        "steps": [
            {"sequence": 10, "label": "รอลงนาม (To sign)",
             "state_field": "state", "state_value": "sent",
             "approver_field": "partner_id", "approver_kind": "partner"},
        ],
    },
    {
        "name": "เอกสาร ISO (ISO Document)",
        "model": "od19.iso.document",
        "icon": "fa-file-text-o",
        "action_xmlid": "od19_iso_document_control.action_iso_document",
        "sequence": 40,
        "requester_field": "create_uid",
        "requester_kind": "user",
        "submitted_date_field": "create_date",
        "rejected_states": "rejected",
        "success_states": "approved",
        "strategy": "field",
        "sla_days": 5,
        "steps": [
            {"sequence": 10, "label": "ทบทวน (Review)",
             "state_field": "status", "state_value": "review",
             "approver_field": "reviewer_id", "approver_kind": "user"},
            {"sequence": 20, "label": "อนุมัติ (Approval)",
             "state_field": "status", "state_value": "approval",
             "approver_field": "approver_id", "approver_kind": "user"},
            {"sequence": 30, "label": "อนุมัติขั้นสุดท้าย (Final approval)",
             "state_field": "status", "state_value": "final_approval",
             "approver_field": "final_approver_id", "approver_kind": "user"},
        ],
    },
    {
        "name": "แผนตรวจสอบ ISO (Audit Program)",
        "model": "od19.iso.audit.program",
        "icon": "fa-search",
        "action_xmlid": "od19_iso_internal_audit.action_iso_audit_program",
        "sequence": 50,
        "requester_field": "create_uid",
        "requester_kind": "user",
        "submitted_date_field": "create_date",
        "rejected_states": "",
        "success_states": "approved,closed",
        "strategy": "field",
        "sla_days": 7,
        "steps": [
            {"sequence": 10, "label": "รออนุมัติแผน (Approve plan)",
             "state_field": "state", "state_value": "draft"},
        ],
    },
    {
        "name": "NC/CAPA (Nonconformity)",
        "model": "od19.iso.nonconformity",
        "icon": "fa-exclamation-triangle",
        "action_xmlid": "od19_iso_nonconformity.action_iso_nc",
        "sequence": 60,
        "requester_field": "create_uid",
        "requester_kind": "user",
        "submitted_date_field": "create_date",
        "rejected_states": "cancel",
        "success_states": "closed",
        "strategy": "field",
        "sla_days": 14,
        "steps": [
            {"sequence": 10, "label": "รอทวนสอบ (Verification)",
             "state_field": "state", "state_value": "verification",
             "approver_field": "verified_by_id", "approver_kind": "user"},
        ],
    },
    {
        "name": "ความเสี่ยง ISO (Risk)",
        "model": "od19.iso.risk",
        "icon": "fa-shield",
        "action_xmlid": "od19_iso_risk.action_iso_risk",
        "sequence": 70,
        "requester_field": "create_uid",
        "requester_kind": "user",
        "submitted_date_field": "create_date",
        "rejected_states": "cancel",
        "success_states": "closed",
        "strategy": "field",
        "sla_days": 14,
        "steps": [
            {"sequence": 10, "label": "รอประเมินโดยเจ้าของความเสี่ยง (Owner)",
             "state_field": "state", "state_value": "evaluated",
             "approver_field": "risk_owner_id", "approver_kind": "user"},
        ],
    },
    {
        "name": "สอบเทียบ ISO (Calibration)",
        "model": "od19.iso.calibration.record",
        "icon": "fa-wrench",
        "action_xmlid": "od19_iso_calibration.action_iso_calibration_record",
        "sequence": 80,
        "requester_field": "create_uid",
        "requester_kind": "user",
        "submitted_date_field": "create_date",
        "rejected_states": "failed,cancelled",
        "success_states": "passed",
        "strategy": "field",
        "sla_days": 7,
        "steps": [
            {"sequence": 10, "label": "รอดำเนินการสอบเทียบ (Scheduled)",
             "state_field": "status", "state_value": "scheduled",
             "approver_field": "technician_id", "approver_kind": "employee"},
        ],
    },
    {
        "name": "ใบสั่งขาย (Sales Order)",
        "model": "sale.order",
        "icon": "fa-file-text",
        "action_xmlid": "sale.action_orders",
        "sequence": 90,
        "requester_field": "create_uid",
        "requester_kind": "user",
        "submitted_date_field": "create_date",
        "rejected_states": "cancel",
        "success_states": "sale",
        "strategy": "tier_validation",
        "sla_days": 3,
        "steps": [],
    },
    {
        "name": "ขนส่ง (Transport Order)",
        "model": "od19.transport.order",
        "icon": "fa-truck",
        "action_xmlid": "od19_transportation.action_od19_transport_order",
        "sequence": 100,
        "requester_field": "create_uid",
        "requester_kind": "user",
        "submitted_date_field": "create_date",
        "rejected_states": "cancelled",
        "success_states": "confirmed,in_transit,delivered",
        "strategy": "tier_validation",
        "sla_days": 3,
        "steps": [],
    },
    {
        "name": "ใบสำคัญจ่าย (Payment Voucher)",
        "model": "account.payment",
        "icon": "fa-money",
        "action_xmlid": "account.action_account_payments",
        "sequence": 110,
        "requester_field": "create_uid",
        "requester_kind": "user",
        "submitted_date_field": "create_date",
        "rejected_states": "",
        "success_states": "approved",
        "strategy": "field",
        "sla_days": 2,
        "steps": [
            {"sequence": 10, "label": "รออนุมัติใบสำคัญ (Approve voucher)",
             "state_field": "od19_prepare_state", "state_value": "prepared"},
        ],
    },
    {
        "name": "ปรับมูลค่าสต็อก (Stock Valuation Adj.)",
        "model": "od19.stock.valuation.adjustment",
        "icon": "fa-balance-scale",
        "action_xmlid": "od19_stock_valuation_adjustment.stock_valuation_adjustment_action",
        "sequence": 120,
        "requester_field": "user_id",
        "requester_kind": "user",
        "submitted_date_field": "create_date",
        "rejected_states": "cancelled",
        "success_states": "done",
        "strategy": "field",
        "sla_days": 5,
        "steps": [
            {"sequence": 10, "label": "รออนุมัติ (Approve)",
             "state_field": "state", "state_value": "confirmed"},
        ],
    },
    {
        "name": "นับสต็อก (Stock Count)",
        "model": "od19.stock.count.session",
        "icon": "fa-cubes",
        "action_xmlid": "od19_inventory_audit_count.od19_stock_count_session_action",
        "sequence": 130,
        "requester_field": "create_uid",
        "requester_kind": "user",
        "submitted_date_field": "create_date",
        "rejected_states": "cancelled",
        "success_states": "adjusted,reviewed",
        "strategy": "field",
        "sla_days": 5,
        "steps": [
            {"sequence": 10, "label": "รออนุมัติผลนับ (Approve count)",
             "state_field": "state", "state_value": "pending_approval"},
        ],
    },
]
```

- [ ] **Step 4: เขียน `hooks.py`**

```python
import logging

from .data.approval_sources import APPROVAL_SOURCES

_logger = logging.getLogger(__name__)


def _od19_step_values(env, model_name, step):
    approver_field = step.get("approver_field") or ""
    if approver_field and approver_field not in env[model_name]._fields:
        _logger.info(
            "Approval Center: %s.%s missing -> shared pool step",
            model_name, approver_field,
        )
        approver_field = ""
    return {
        "sequence": step.get("sequence", 10),
        "label": step["label"],
        "state_field": step.get("state_field", "state"),
        "state_value": step["state_value"],
        "approver_field": approver_field,
        "approver_kind": step.get("approver_kind", "user"),
    }


def _od19_source_values(env, spec, model_id, model_name):
    model_fields = env[model_name]._fields
    requester_field = spec.get("requester_field") or "create_uid"
    if requester_field not in model_fields:
        requester_field = "create_uid"
    submitted_field = spec.get("submitted_date_field") or "create_date"
    if submitted_field not in model_fields:
        submitted_field = "create_date"
    return {
        "name": spec["name"],
        "model_id": model_id,
        "icon": spec.get("icon", "fa-inbox"),
        "action_xmlid": spec.get("action_xmlid"),
        "sequence": spec.get("sequence", 10),
        "requester_field": requester_field,
        "requester_kind": spec.get("requester_kind", "user"),
        "submitted_date_field": submitted_field,
        "rejected_states": spec.get("rejected_states"),
        "success_states": spec.get("success_states"),
        "strategy": spec.get("strategy", "field"),
        "sla_days": spec.get("sla_days", 0),
        "step_ids": [
            (0, 0, _od19_step_values(env, model_name, step))
            for step in spec.get("steps", [])
        ],
    }


def post_init_hook(env):
    """Seed Approval Center sources (idempotent, install only)."""
    Source = env["od19.approval.source"]
    IrModel = env["ir.model"]
    for spec in APPROVAL_SOURCES:
        model_name = spec.get("model")
        if not model_name or model_name not in env:
            _logger.info("Approval Center: skip %s (not installed)", model_name)
            continue
        model = IrModel._get(model_name)
        if not model:
            continue
        if Source.search([
            ("model_id", "=", model.id),
            ("name", "=", spec["name"]),
        ], limit=1):
            continue
        Source.create(_od19_source_values(env, spec, model.id, model_name))
        _logger.info("Approval Center: seeded %s (%s)", spec["name"], model_name)
```

- [ ] **Step 5: รันเทสต์ให้ PASS**

Run: same as Step 2
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add custom_addons/od19_approval_center
git commit -m "feat(od19_approval_center): seed 13 approval sources on install"
```

---

## PART C — Admin UI + Website

### Task 10: admin views + menus

**Files:**
- Create: `custom_addons/od19_approval_center/views/od19_approval_source_views.xml`
- Create: `custom_addons/od19_approval_center/views/od19_approval_menus.xml`
- Modify: `custom_addons/od19_approval_center/__manifest__.py`

- [ ] **Step 1: สร้าง `views/od19_approval_source_views.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>

    <record id="view_od19_approval_source_list" model="ir.ui.view">
        <field name="name">od19.approval.source.list</field>
        <field name="model">od19.approval.source</field>
        <field name="arch" type="xml">
            <list string="Approval Sources">
                <field name="sequence" widget="handle"/>
                <field name="name"/>
                <field name="model_name"/>
                <field name="strategy"/>
                <field name="sla_days"/>
                <field name="active"/>
            </list>
        </field>
    </record>

    <record id="view_od19_approval_source_form" model="ir.ui.view">
        <field name="name">od19.approval.source.form</field>
        <field name="model">od19.approval.source</field>
        <field name="arch" type="xml">
            <form string="Approval Source">
                <sheet>
                    <widget name="web_ribbon" title="Archived"
                            bg_color="text-bg-danger" invisible="active"/>
                    <group>
                        <group>
                            <field name="name"/>
                            <field name="model_id"/>
                            <field name="model_name"/>
                            <field name="icon"/>
                        </group>
                        <group>
                            <field name="strategy"/>
                            <field name="sequence"/>
                            <field name="sla_days"/>
                            <field name="active"/>
                        </group>
                    </group>
                    <group string="Requester">
                        <field name="requester_field"/>
                        <field name="requester_kind"/>
                        <field name="submitted_date_field"/>
                        <field name="decided_date_field"/>
                    </group>
                    <group string="States">
                        <field name="rejected_states"/>
                        <field name="success_states"/>
                        <field name="action_xmlid"/>
                    </group>
                    <notebook>
                        <page string="Steps" name="steps">
                            <field name="step_ids">
                                <list editable="bottom">
                                    <field name="sequence" widget="handle"/>
                                    <field name="label"/>
                                    <field name="state_field"/>
                                    <field name="state_value"/>
                                    <field name="approver_field"/>
                                    <field name="approver_kind"/>
                                </list>
                            </field>
                        </page>
                    </notebook>
                </sheet>
            </form>
        </field>
    </record>

    <record id="action_od19_approval_source" model="ir.actions.act_window">
        <field name="name">Approval Sources</field>
        <field name="res_model">od19.approval.source</field>
        <field name="view_mode">list,form</field>
    </record>

</odoo>
```

- [ ] **Step 2: สร้าง `views/od19_approval_menus.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>

    <menuitem id="menu_od19_approval_root"
              name="Approval Center"
              parent="base.menu_administration"
              sequence="95"
              groups="od19_approval_center.group_approval_admin"/>

    <menuitem id="menu_od19_approval_source"
              name="Approval Sources"
              parent="menu_od19_approval_root"
              action="action_od19_approval_source"
              sequence="10"/>

</odoo>
```

> ถ้า `base.menu_administration` ไม่มีใน Odoo 19 ให้เปลี่ยน parent เป็น `base.menu_custom` (ตรวจตอนรัน `-u`).

- [ ] **Step 3: เพิ่ม data ใน `__manifest__.py`**

```python
    "data": [
        "security/od19_approval_security.xml",
        "security/ir.model.access.csv",
        "views/od19_approval_source_views.xml",
        "views/od19_approval_menus.xml",
    ],
```

- [ ] **Step 4: รันให้ผ่าน (ไม่มีเทสต์ใหม่ — ตรวจว่าโหลด XML ไม่ error)**

Run: `python odoo-bin -c odoo.conf -d odoo19_pdev -u od19_approval_center --stop-after-init --http-port=8075`
Expected: ไม่มี traceback; menu "Approval Center" ปรากฏใต้ Settings

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_approval_center
git commit -m "feat(od19_approval_center): admin views and settings menu"
```

---

### Task 11: website route `/my/approvals` + summary

**Files:**
- Modify: `custom_addons/od19_website/controllers/main.py`
- Modify: `custom_addons/od19_website/__manifest__.py`

- [ ] **Step 1: เพิ่ม route + aggregator ใน `controllers/main.py`**

เพิ่มเมธอดในคลาส `AutoInfoWebsite` (ต่อจาก `employee_portal`):

```python
    # ------------------------------------------------------------------
    # Approval Center (view-only)
    # ------------------------------------------------------------------
    @http.route(
        ["/my/approvals"],
        type="http",
        auth="user",
        website=True,
        sitemap=False,
    )
    def od19_my_approvals(self, **kwargs):
        """Approval Center page: what I must approve + my own requests."""
        return request.render(
            "od19_website.od19_approval_center", self._od19_approval_data()
        )

    def _od19_approval_data(self):
        """Aggregate every active source into 2 tabs x 4 groups."""
        Source = request.env["od19.approval.source"].sudo()
        approver = {"pending": [], "incoming": [], "done": [], "rejected": []}
        requester = {"pending": [], "incoming": [], "done": [], "rejected": []}
        for source in Source.search([("active", "=", True)]):
            for key, records in source._od19_classify_for_approver().items():
                approver[key].extend(source._od19_build_rows(records))
            for key, records in source._od19_classify_for_requester().items():
                requester[key].extend(source._od19_build_rows(records))
        return {
            "user": request.env.user,
            "datetime": datetime,
            "approver": approver,
            "requester": requester,
            "summary": Source._od19_summary(approver["pending"]),
        }
```

- [ ] **Step 2: ส่ง `approval_summary` เข้า Employee Portal**

ในเมธอด `employee_portal` เพิ่มคีย์ใน dict ของ `request.render`:

```python
                "approval_summary": self._od19_approval_data()["summary"],
```

- [ ] **Step 3: แก้ `__manifest__.py` ของ `od19_website`**

```python
    "depends": [
        "website", "website_blog", "website_crm", "website_hr_recruitment",
        "portal", "mail", "web_tour",
        "od19_announcement", "od19_meeting_room_booking",
        "od19_knowledge_enhanced", "od19_approval_center",
    ],
```

และเพิ่มใน `"data"`:

```python
        "views/approval_center.xml",
```

- [ ] **Step 4: ตรวจว่าโหลดไม่ error** (template ยังไม่สร้าง — รันหลัง Task 12)

Run: `python odoo-bin -c odoo.conf -d odoo19_pdev -u od19_website --stop-after-init --http-port=8075`

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_website
git commit -m "feat(od19_website): /my/approvals route and portal summary"
```

---

### Task 12: QWeb template (2 แท็บ × 4 กลุ่ม)

**Files:**
- Create: `custom_addons/od19_website/views/approval_center.xml`

- [ ] **Step 1: สร้าง `views/approval_center.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>

    <template id="od19_approval_group" name="Approval Group Card">
        <div class="card border-0 shadow-sm mb-3">
            <div class="card-header bg-white d-flex justify-content-between align-items-center">
                <h6 class="mb-0">
                    <span t-attf-class="#{'text-danger' if group_key == 'pending' else 'text-info' if group_key == 'incoming' else 'text-success' if group_key == 'done' else 'text-secondary'}">
                        <i class="fa fa-circle me-1" style="font-size:0.55rem;"/>
                        <t t-esc="group_title"/>
                    </span>
                </h6>
                <span class="badge bg-light text-dark" t-esc="len(rows)"/>
            </div>
            <div class="card-body p-0">
                <div class="table-responsive" t-if="rows">
                    <table class="table table-sm mb-0 align-middle">
                        <thead>
                            <tr>
                                <th>รายการ</th>
                                <th>ประเภท</th>
                                <th class="text-center">อายุ (วัน)</th>
                                <th class="text-end">เปิด</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr t-foreach="rows" t-as="row">
                                <td>
                                    <i t-attf-class="fa #{row['icon']} me-1 text-muted"/>
                                    <span t-esc="row['label']"/>
                                </td>
                                <td><small class="text-muted" t-esc="row['source_name']"/></td>
                                <td class="text-center">
                                    <span t-attf-class="badge #{'bg-danger' if row['sla_state'] == 'over' else 'bg-warning text-dark' if row['sla_state'] == 'warning' else 'bg-light text-dark'}"
                                          t-esc="row['age_days']"/>
                                </td>
                                <td class="text-end">
                                    <a t-att-href="row['url']" target="_blank"
                                       class="btn btn-sm btn-outline-primary">
                                        <i class="fa fa-external-link"/> เปิด
                                    </a>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div class="text-center text-muted py-4" t-else="">
                    <i class="fa fa-inbox me-1"/> ไม่มีรายการ
                </div>
            </div>
        </div>
    </template>

    <template id="od19_approval_center" name="Approval Center">
        <t t-call="website.layout">
            <t t-set="no_footer" t-value="True"/>
            <div id="wrap" class="oe_structure">

                <section class="od19-portal-hero">
                    <div class="container">
                        <h2><i class="fa fa-check-square-o me-2"/>ศูนย์อนุมัติ (Approval Center)</h2>
                        <p class="mb-0" style="opacity:0.85;">
                            รายการที่รอการอนุมัติของคุณ และความคืบหน้าคำขอของคุณ
                        </p>
                    </div>
                </section>

                <div class="container py-4">

                    <div class="row mb-3" t-if="summary['pending_count']">
                        <div class="col-md-4">
                            <div class="card border-0 shadow-sm">
                                <div class="card-body text-center">
                                    <div class="fs-3 fw-bold text-danger" t-esc="summary['pending_count']"/>
                                    <small class="text-muted">รอฉันอนุมัติ (คงค้าง)</small>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="card border-0 shadow-sm">
                                <div class="card-body text-center">
                                    <div class="fs-3 fw-bold" t-esc="summary['max_age_days']"/>
                                    <small class="text-muted">อายุมากที่สุด (วัน)</small>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="card border-0 shadow-sm">
                                <div class="card-body text-center">
                                    <div class="fs-3 fw-bold text-danger" t-esc="summary['over_sla_count']"/>
                                    <small class="text-muted">เกินกำหนด (Over SLA)</small>
                                </div>
                            </div>
                        </div>
                    </div>

                    <ul class="nav nav-tabs mb-3" role="tablist">
                        <li class="nav-item" role="presentation">
                            <button class="nav-link active" type="button" role="tab"
                                    data-bs-toggle="tab" data-bs-target="#od19-tab-approver">
                                <i class="fa fa-gavel me-1"/>รอฉันอนุมัติ
                                <span class="badge bg-danger ms-1" t-esc="len(approver['pending'])"/>
                            </button>
                        </li>
                        <li class="nav-item" role="presentation">
                            <button class="nav-link" type="button" role="tab"
                                    data-bs-toggle="tab" data-bs-target="#od19-tab-requester">
                                <i class="fa fa-paper-plane me-1"/>คำขอของฉัน
                                <span class="badge bg-secondary ms-1"
                                      t-esc="len(requester['pending']) + len(requester['incoming'])"/>
                            </button>
                        </li>
                    </ul>

                    <div class="tab-content">
                        <div class="tab-pane fade show active" id="od19-tab-approver" role="tabpanel">
                            <t t-foreach="[('pending', 'คงค้าง (Pending)', approver['pending']),
                                           ('incoming', 'กำลังมาถึง (Incoming)', approver['incoming']),
                                           ('done', 'สำเร็จ (Done)', approver['done']),
                                           ('rejected', 'ปฏิเสธ (Rejected)', approver['rejected'])]"
                               t-as="grp">
                                <t t-call="od19_website.od19_approval_group">
                                    <t t-set="group_key" t-value="grp[0]"/>
                                    <t t-set="group_title" t-value="grp[1]"/>
                                    <t t-set="rows" t-value="grp[2]"/>
                                </t>
                            </t>
                        </div>

                        <div class="tab-pane fade" id="od19-tab-requester" role="tabpanel">
                            <t t-foreach="[('pending', 'รออนุมัติ (Pending)', requester['pending']),
                                           ('incoming', 'กำลังดำเนินการ (In progress)', requester['incoming']),
                                           ('done', 'สำเร็จ (Done)', requester['done']),
                                           ('rejected', 'ปฏิเสธ (Rejected)', requester['rejected'])]"
                               t-as="grp">
                                <t t-call="od19_website.od19_approval_group">
                                    <t t-set="group_key" t-value="grp[0]"/>
                                    <t t-set="group_title" t-value="grp[1]"/>
                                    <t t-set="rows" t-value="grp[2]"/>
                                </t>
                            </t>
                        </div>
                    </div>

                    <div class="mt-3">
                        <a href="/employee-portal" class="btn btn-sm btn-outline-secondary">
                            <i class="fa fa-arrow-left me-1"/>กลับพอร์ทัลพนักงาน
                        </a>
                    </div>
                </div>
            </div>
        </t>
    </template>

</odoo>
```

- [ ] **Step 2: รันให้ผ่าน**

Run: `python odoo-bin -c odoo.conf -d odoo19_pdev -u od19_website --stop-after-init --http-port=8075`
Expected: ไม่มี traceback

- [ ] **Step 3: ตรวจด้วยตา (smoke)** — เปิด `http://localhost:8070/my/approvals` ในฐานะพนักงาน → เห็น 2 แท็บ 4 กลุ่ม

- [ ] **Step 4: Commit**

```bash
git add custom_addons/od19_website
git commit -m "feat(od19_website): approval center template (2 tabs, 4 groups)"
```

---

### Task 13: การ์ดบน Employee Portal + HttpCase

**Files:**
- Modify: `custom_addons/od19_website/views/employee_portal.xml`
- Create: `custom_addons/od19_website/tests/test_approval_portal.py`
- Modify: `custom_addons/od19_website/tests/__init__.py` (ถ้ามี — เพิ่ม import)

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

```python
from odoo.tests.common import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestApprovalPortal(HttpCase):
    def setUp(self):
        super().setUp()
        self.tester = self.env["res.users"].create({
            "name": "Approval Tester",
            "login": "approval_tester",
            "password": "approval_tester",
            "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
        })

    def test_my_approvals_page_renders(self):
        self.authenticate("approval_tester", "approval_tester")
        response = self.url_open("/my/approvals")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"od19-tab-approver", response.content)
        self.assertIn(b"od19-tab-requester", response.content)

    def test_portal_card_links_to_approvals(self):
        self.authenticate("approval_tester", "approval_tester")
        response = self.url_open("/employee-portal")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"/my/approvals", response.content)
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า FAIL**

Run: `python odoo-bin -c odoo.conf -d odoo19_pdev -u od19_website --test-enable --test-tags /od19_website --stop-after-init --http-port=8075`
Expected: FAIL — การ์ดยังไม่มีในพอร์ทัล (`/my/approvals` ไม่ปรากฏในหน้า `/employee-portal`)

- [ ] **Step 3: เพิ่มการ์ดเป็นรายการแรกของ Quick Access**

ใน `views/employee_portal.xml` แทรก **ก่อน** การ์ด "แจ้งปัญหาภายใน" (หลังบล็อกหัวข้อ "เมนูด่วน (Quick Access)"):

```xml
                        <div class="col-lg-3 col-md-4 col-sm-6 mb-3">
                            <div class="od19-portal-card">
                                <div class="od19-portal-icon"><i class="fa fa-check-square-o"/></div>
                                <h5>รายการอนุมัติ</h5>
                                <p>Approval Center</p>
                                <a href="/my/approvals">เปิดใช้งาน →</a>
                            </div>
                            <t t-if="approval_summary and approval_summary['pending_count']">
                                <small class="text-danger d-block mt-1">
                                    <i class="fa fa-clock-o me-1"/>
                                    รออนุมัติ <t t-esc="approval_summary['pending_count']"/> รายการ
                                    <t t-if="approval_summary['max_age_days']">
                                        (เก่าสุด <t t-esc="approval_summary['max_age_days']"/> วัน)
                                    </t>
                                </small>
                            </t>
                        </div>
```

- [ ] **Step 4: รันเทสต์ให้ PASS**

Run: same as Step 2
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_website
git commit -m "feat(od19_website): approval center quick-access card with badge"
```

---

## PART D — ตรวจรับ

### Task 14: Acceptance verification

**Files:** ไม่มี (ตรวจเท่านั้น)

- [ ] **Step 1: รันเทสต์ทั้งสองโมดูล**

```powershell
python odoo-bin -c odoo.conf -d odoo19_pdev -u od19_approval_center,od19_website `
  --test-enable --test-tags /od19_approval_center,/od19_website --stop-after-init --http-port=8075
```

Expected: 0 failed, 0 error

- [ ] **Step 2: ตรวจ acceptance criteria จาก design doc**

- [ ] ผู้อนุมัติเห็นรายการ *คงค้าง* ของตน (ทุกแหล่งที่ตนเป็นผู้อนุมัติ) — ผ่าน bucket `pending`
- [ ] ผู้อนุมัติเห็นรายการ *กำลังมาถึง* (ขั้นก่อนหน้ายังไม่จบ) แยกจากคงค้าง — ผ่าน bucket `incoming`
- [ ] ผู้ขอเห็นความคืบหน้าคำขอของตน 4 กลุ่ม — ผ่านแท็บ "คำขอของฉัน"
- [ ] ทุกครั้งที่แสดงรายการ มี **อายุ (วัน)** + สถานะ SLA (ปกติ/เตือน/เกินมาก)
- [ ] คลิกรายการ → เปิดหน้าจริงของเอกสาร (`/web#id=..&model=..`) — **view-only** ไม่มีปุ่มอนุมัติใน Approval Center
- [ ] ครอบคลุมครบ 13 แหล่ง (นับเฉพาะที่ติดตั้งจริง — ที่เหลือถูก skip อย่างมี log)
- [ ] ผู้ใช้ที่ไม่เกี่ยวข้องไม่เห็นรายการของผู้อื่น (D8)

- [ ] **Step 3: ตรวจว่าไม่มี side effect ต่อ core**

```bash
git status --porcelain
```

Expected: มีเฉพาะไฟล์ใน `custom_addons/od19_approval_center` และ `custom_addons/od19_website` (ไม่มีไฟล์ใน `addons/` หรือ `odoo/`)

- [ ] **Step 4: Commit (ถ้ามีการแก้ระหว่างตรวจ)**

```bash
git add custom_addons/od19_approval_center custom_addons/od19_website
git commit -m "chore(od19_approval_center): acceptance fixes"
```

---

## Known limitations (ยอมรับไว้)

1. **Overlapping steps** — แหล่งที่ `state` ยังค้างที่ค่าเดิมระหว่างสองขั้น (เช่น `hr.expense` ยังเป็น `submitted` ตอน `second_approval_state='pending'`) อาศัยกติกา "ขั้นไกลสุดชนะ" ของ `_od19_current_index` (Task 6) ถ้าอนาคตเพิ่มขั้นที่ซ้อนกันกว่านี้ ต้องทบทวน
2. **Shared pool (D10)** — 4 แหล่งที่ไม่มีฟิลด์ผู้อนุมัติ จะมองเห็นร่วมกันโดยผู้ใช้ภายในทุกคน; หากต้องการจำกัดรายกลุ่ม ต้องเพิ่มฟิลด์ `approver_group_id` (นอกขอบเขตแผนนี้)
3. **`od19.iso.risk` step** ใช้ `state='evaluated'` เป็นจุดรอของเจ้าของความเสี่ยง — ถ้าไม่ตรงกับกระบวนการจริง แอดมินแก้ `state_value` ได้จากเมนู Settings → Approval Sources
4. **เพดาน 500 แถว/แหล่ง** (`OD19_MAX_RECORDS`) — เกินกว่านั้นจะไม่แสดง (ป้องกันหน่วยความจำ)

---

## Execution choice

แผนพร้อม execute — เลือกวิธีได้ 2 ทาง:

1. **Subagent-Driven (แนะนำ)** — ใช้ `superpowers:subagent-driven-development` dispatch 1 subagent ต่อ 1 task (Task 1→14) มี checkpoint ระหว่าง task; เหมาะกับแผน 14 task ที่เป็นอิสระต่อกัน
2. **Inline Execution** — ใช้ `superpowers:executing-plans` รันตามลำดับในเซสชันนี้ มี review checkpoint ที่ Task 9, 13, 14

ตอบกลับด้วย "เลือก 1" หรือ "เลือก 2" เพื่อเริ่ม implement (หรือแจ้งแก้ไขแผนก่อน)
