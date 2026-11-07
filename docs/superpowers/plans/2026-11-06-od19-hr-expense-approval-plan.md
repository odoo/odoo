# HR Expense 3-Level Tier Approval (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** เปลี่ยนกลไกอนุมัติค่าใช้จ่ายของ Odoo 19 CE จาก "2 ชั้นแบบ hardcoded" มาเป็น "3 ชั้นตามลำดับ (หัวหน้าแผนก → บัญชี → CEO)" ด้วย OCA `tier.validation` พร้อมรองรับการมอบหมายต่อ (Forward)

**Architecture:**
- ใช้ OCA module ที่มีอยู่แล้วใน addons_path: `hr_expense_tier_validation` (ตั้ง `_state_field = "approval_state"`, `_state_from=["submitted"]`, `_state_to=["approved"]`, `_tier_validation_manual_config=False`), `base_tier_validation` (เครื่องยนต์ tier) และ `base_tier_validation_forward` (ฟีเจอร์ Forward)
- โมดูล `od19_hr_expense_thai` เป็นเจ้าของข้อมูล `tier.definition` 3 รายการ (sequence 30/20/10), กลุ่มผู้อนุมัติ CEO (`group_od19_expense_ceo_approver`) และการถอดกลไกอนุมัติ 2 ชั้นเดิม (ปุ่ม + method) ออก โดย **คงฟิลด์เดิมไว้ในฐานข้อมูล** เพื่อความเข้ากันได้ของข้อมูล (ห้ามลบฟิลด์)
- `od19_approval_center` เปลี่ยน source ของ `hr.expense` จาก `strategy="field"` เป็น `strategy="tier_validation"` (เหมือน `sale.order` และ `od19.transport.order`)
- `od19_role_catalog` เพิ่มบทบาท CEO (`role_expense_ceo_approver`) ที่ imply กลุ่ม CEO ที่สร้างใน `od19_hr_expense_thai`

**Tech Stack:** Odoo 19 CE · Python 3 · OCA `base_tier_validation` v19.0.1.4.6 / `hr_expense_tier_validation` v19.0.1.0.0 / `base_tier_validation_forward` v19.0.1.0.1 · XML data · Odoo `TransactionCase` tests

**ข้อกำหนดอ้างอิง (บังคับ):**
- ตาม [AGENTS.md](file:///c:/odoo-dev/odoo19/AGENTS.md): ห้ามแก้ Odoo core · commit ได้เองใน `custom_addons/` + `docs/` หลังผ่าน Pre-flight · Conventional Commits · **ห้าม `git add -A`** · Single-writer
- ฐานข้อมูลที่ใช้ทดสอบ: `odoo19_pdev`
- **ห้ามรัน Unit Test แทนผู้ใช้** — ในแผนนี้ระบุคำสั่งไว้ให้ผู้ใช้รันเองบน terminal ของเครื่อง

---

## File Structure

| ไฟล์ | บทบาท | การเปลี่ยนแปลง |
|---|---|---|
| `custom_addons/od19_hr_expense_thai/security/hr_expense_security.xml` | กลุ่มผู้อนุมัติ CEO (`res.groups`) | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_thai/data/tier_definition_data.xml` | `tier.definition` 3 ชั้น | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_thai/__manifest__.py` | depends + data + version | แก้ |
| `custom_addons/od19_hr_expense_thai/models/hr_expense.py` | ถอด method อนุมัติ 2 ชั้นเดิม | แก้ |
| `custom_addons/od19_hr_expense_thai/views/hr_expense_views.xml` | ถอดปุ่ม L1/L2 + ฟิลด์อนุมัติเดิม | แก้ |
| `custom_addons/od19_hr_expense_thai/tests/test_hr_expense_tier.py` | เทสต์กลุ่ม CEO + tier.definition + ลำดับอนุมัติ | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_thai/tests/test_hr_expense_thai.py` | ลบเทสต์ที่อ้าง method ที่ถอดออก | แก้ |
| `custom_addons/od19_hr_expense_thai/tests/__init__.py` | เพิ่ม import ไฟล์เทสต์ใหม่ (**ห้ามทับบรรทัดเดิม**) | แก้ |
| `custom_addons/od19_approval_center/data/approval_sources.py` | source `hr.expense` → tier | แก้ |
| `custom_addons/od19_approval_center/hooks.py` | (ไม่แก้ — ใช้ migration แทน) | — |
| `custom_addons/od19_approval_center/migrations/19.0.1.1.0/post-migrate.py` | อัปเดต source ที่ seed ไปแล้ว | **สร้างใหม่** |
| `custom_addons/od19_approval_center/__manifest__.py` | version bump | แก้ |
| `custom_addons/od19_approval_center/tests/test_approval_seed.py` | ปรับเทสต์ source hr.expense | แก้ |
| `custom_addons/od19_role_catalog/data/od19_roles_backoffice.xml` | เพิ่มบทบาท CEO | แก้ |
| `custom_addons/od19_role_catalog/__manifest__.py` | depends `od19_hr_expense_thai` + version | แก้ |
| `custom_addons/od19_role_catalog/tests/test_role_catalog.py` | ROLE_MATRIX + ตัวเลข 43→44 | แก้ |
| `custom_addons/od19_user_guide_tours/static/src/tours/hr_expense_tour.js` | ปรับปุ่มในทัวร์ | แก้ |
| `docs/superpowers/specs/2026-11-06-od19-hr-expense-reimbursement-design.md` | ถ้อยคำ Delegations → Forward | แก้ |

**ลำดับการโหลดข้อมูล (สำคัญ):** `security/hr_expense_security.xml` ต้องโหลด **ก่อน** `data/tier_definition_data.xml` เพราะ tier definition อ้างกลุ่ม CEO ที่ประกาศในไฟล์ security

---

## กลไกที่ยืนยันจากโค้ดจริง (ใช้อ้างอิงตอน implement)

- `tier.validation._compute_need_validation` → `need_validation = (ไม่มี review_ids) and (มี tier.definition ที่เข้าเงื่อนไข) and (_check_state_from_condition())`
- `@api.depends` ของ `need_validation` คือ `review_ids` + state field → ต้องเซ็ต `approval_state='submitted'` ตรง ๆ ได้ (ไม่ trigger tier เพราะก่อนเขียน state ยังไม่อยู่ใน `_state_from`)
- ลำดับชั้น: `request_validation()` ค้น `tier.definition` ด้วย `order="sequence desc"` แล้วแปลงเป็น `tier.review.sequence = 1, 2, 3, ...` → **definition ที่ sequence สูงกว่า จะถูกอนุมัติก่อน** (ชั้น 1 = seq 30)
- `_validate_tier()` อนุมัติเฉพาะ review ที่มีสถานะ `pending` เรียงตาม `sequence` **ติดกัน** ของผู้ใช้ปัจจุบัน และ **หยุดทันทีที่เจอ review แรกที่ไม่ใช่ของผู้ใช้** → ป้องกันการอนุมัติข้ามขั้น
- `hr_expense_tier_validation.write()` จะ raise `ValidationError("The expense is under validation.")` เมื่อ `approval_state=='submitted'` และมี `review_ids` และ `validation_status` ไม่อยู่ใน `("validated","rejected")` (ยกเว้นฟิลด์ใน `hr_expense.tier_exceptions` = `["message_follower_ids","access_token"]`)
- ลำดับ UX จริง: `draft` → **Submit** (`approval_state='submitted'`) → **Request Validation** (`request_validation`) → **Validate ×3** (`validate_tier`) → **Approve** (ปุ่ม core, `action_approve` → `_do_approve` เขียน `approval_state='approved'`)
- ACL ของ `tier.review`: `base.group_user` มี CRUD ครบ → reviewer ที่เป็น internal user อนุมัติได้
- `res.users` ใน Odoo 19 ใช้ฟิลด์ **`group_ids`** (ไม่ใช่ `groups_id`)
- `hr.expense` core มี `_can_be_autovalidated()` → ถ้าไม่มี manager หรือ manager == user ของพนักงาน จะ auto-approve ทันทีตอน submit (เลี่ยงได้ด้วยการตั้ง `approval_state='submitted'` ตรง ๆ ในเทสต์)

---

## Task 0: Pre-flight (บังคับตาม AGENTS.md)

**Files:** ไม่มี (ตรวจสอบสภาพแวดล้อม)

- [x] **Step 1: ตรวจ branch และสถานะ**

Run:
```powershell
git log -1 --oneline
git status -sb
git branch --show-current
```
Expected: อยู่ที่ branch งาน (`feature/od19-billing-request-from-inventory`) · working tree สะอาด หรือมีเฉพาะไฟล์ที่งานนี้จะแตะ · **ไม่มี** ไฟล์ `.git/index.lock`

- [x] **Step 2: บันทึก HEAD ไว้**

จดค่า SHA จาก `git log -1 --oneline` ไว้รายงานตอนจบ

- [x] **Step 3: ยืนยัน HEAD ไม่เปลี่ยนใน 2 นาที**

Run (รอ 120 วินาทีแล้วเทียบ):
```powershell
Start-Sleep -Seconds 120; git log -1 --oneline
```
Expected: SHA เท่าเดิม → ผ่าน Single-writer · ถ้าเปลี่ยน ให้ **หยุด** และรายงานผู้ใช้

---

## Task 1: กลุ่มผู้อนุมัติ CEO (`group_od19_expense_ceo_approver`)

**Files:**
- Create: `custom_addons/od19_hr_expense_thai/security/hr_expense_security.xml`
- Modify: `custom_addons/od19_hr_expense_thai/__manifest__.py`
- Create: `custom_addons/od19_hr_expense_thai/tests/test_hr_expense_tier.py`
- Modify: `custom_addons/od19_hr_expense_thai/tests/__init__.py`

- [x] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน (failing test)**

สร้างไฟล์ `custom_addons/od19_hr_expense_thai/tests/test_hr_expense_tier.py`:

```python
# -*- coding: utf-8 -*-
from odoo import Command
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestHrExpenseTierValidation(TransactionCase):
    """ตรวจกลุ่ม CEO และการตั้งค่า tier.definition ของค่าใช้จ่าย"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.expense_model = cls.env["hr.expense"]
        cls.product = cls.env["product.product"].create({
            "name": "Tier Test Expense",
            "type": "service",
        })
        cls.employee = cls.env["hr.employee"].search([], limit=1)
        if not cls.employee:
            cls.employee = cls.env["hr.employee"].create({"name": "Tier Test Employee"})

    def _make_user(self, login, group_xmlids):
        groups = [self.env.ref(x).id for x in group_xmlids]
        groups.append(self.env.ref("base.group_user").id)
        return self.env["res.users"].create({
            "name": login,
            "login": login,
            "group_ids": [Command.set(sorted(set(groups)))],
        })

    def test_ceo_group_exists(self):
        """ต้องมีกลุ่ม Expense CEO Approver"""
        group = self.env.ref("od19_hr_expense_thai.group_od19_expense_ceo_approver")
        self.assertEqual(group.name, "Expense CEO Approver")
```

- [x] **Step 2: เพิ่ม import ไฟล์เทสต์ใหม่**

> ⚠️ **ห้ามเขียนทับไฟล์** — `tests/__init__.py` ปัจจุบันมี 2 บรรทัด (`test_hr_expense_thai`, `test_hr_expense_reimburse`) ให้ **เพิ่ม** บรรทัดใหม่ต่อท้ายเท่านั้น มิฉะนั้นเทสต์ reimburse 4 รายการจะหายไปจากชุดทดสอบ

แก้ `custom_addons/od19_hr_expense_thai/tests/__init__.py` ให้เป็น:

```python
# -*- coding: utf-8 -*-
from . import test_hr_expense_thai
from . import test_hr_expense_reimburse
from . import test_hr_expense_tier
```

- [x] **Step 3: รันเทสต์เพื่อยืนยันว่า fail**

Run (ผู้ใช้รันเองบน terminal ของเครื่อง):
```powershell
cd c:\odoo-dev\odoo19
.\run-tests.ps1 -Module od19_hr_expense_thai
```
Expected: FAIL — `ValueError: External ID not found ... group_od19_expense_ceo_approver`

- [x] **Step 4: สร้างไฟล์ security XML**

สร้าง `custom_addons/od19_hr_expense_thai/security/hr_expense_security.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>

    <!--
        กลุ่มผู้อนุมัติชั้นที่ 3 (CEO) สำหรับสายอนุมัติค่าใช้จ่าย
        ใช้เป็น reviewer_group_id ของ tier.definition ชั้น CEO
        บทบาท (res.users.role) ที่ผูกกลุ่มนี้ถูกประกาศใน od19_role_catalog
    -->
    <record id="group_od19_expense_ceo_approver" model="res.groups">
        <field name="name">Expense CEO Approver</field>
        <field name="comment">ผู้อนุมัติค่าใช้จ่ายชั้นที่ 3 (CEO)</field>
    </record>

</odoo>
```

- [x] **Step 5: ลงทะเบียนไฟล์ security + bump version ใน manifest**

แก้ `custom_addons/od19_hr_expense_thai/__manifest__.py`:
- `version`: `'19.0.1.1.0'` → `'19.0.1.2.0'`
- `data`: เพิ่ม `'security/hr_expense_security.xml'` **ก่อน** `'views/hr_expense_views.xml'`

ผลลัพธ์:

```python
    'version': '19.0.1.2.0',
    'data': [
        'security/ir.model.access.csv',
        'security/hr_expense_security.xml',
        'views/hr_expense_views.xml',
    ],
```

- [x] **Step 6: รันเทสต์เพื่อยืนยันว่าผ่าน**

Run:
```powershell
.\run-tests.ps1 -Module od19_hr_expense_thai
```
Expected: PASS — `test_ceo_group_exists`

- [x] **Step 7: Commit**

```powershell
git add custom_addons/od19_hr_expense_thai/security/hr_expense_security.xml custom_addons/od19_hr_expense_thai/__manifest__.py custom_addons/od19_hr_expense_thai/tests/test_hr_expense_tier.py custom_addons/od19_hr_expense_thai/tests/__init__.py
git commit -m "feat(od19_hr_expense_thai): add CEO approver group for expense tier" -m "กลุ่ม Expense CEO Approver (res.groups) สำหรับใช้เป็น reviewer_group_id ของชั้นอนุมัติที่ 3"
```

---

## Task 2: ข้อมูล `tier.definition` 3 ชั้น + เพิ่ม dependency

**Files:**
- Create: `custom_addons/od19_hr_expense_thai/data/tier_definition_data.xml`
- Modify: `custom_addons/od19_hr_expense_thai/__manifest__.py`
- Modify: `custom_addons/od19_hr_expense_thai/tests/test_hr_expense_tier.py`

- [x] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

เพิ่ม method ต่อไปนี้ใน `TestHrExpenseTierValidation` (ไฟล์ `tests/test_hr_expense_tier.py`):

```python
    def _expense_tier_definitions(self):
        return self.env["tier.definition"].search([
            ("model_id.model", "=", "hr.expense"),
            ("company_id", "=", False),
        ])

    def test_three_tier_definitions_exist(self):
        """ต้องมี tier.definition 3 รายการสำหรับ hr.expense"""
        defs = self._expense_tier_definitions()
        self.assertEqual(len(defs), 3)

    def test_tier_definitions_reviewer_groups(self):
        """ชั้น 1 = HR Expense Manager, ชั้น 2 = Account Manager, ชั้น 3 = CEO"""
        defs = self._expense_tier_definitions()
        groups = defs.mapped("reviewer_group_id")
        self.assertIn(self.env.ref("hr_expense.group_hr_expense_manager"), groups)
        self.assertIn(self.env.ref("account.group_account_manager"), groups)
        self.assertIn(
            self.env.ref("od19_hr_expense_thai.group_od19_expense_ceo_approver"),
            groups,
        )

    def test_tier_definition_order_and_forward(self):
        """ชั้น 1 มี sequence สูงสุด และทุกชั้นเปิด Forward + approve_sequence"""
        defs = self._expense_tier_definitions().sorted("sequence", reverse=True)
        self.assertEqual(defs.mapped("sequence"), [30, 20, 10])
        self.assertEqual(defs[0].reviewer_group_id,
                         self.env.ref("hr_expense.group_hr_expense_manager"))
        self.assertTrue(all(defs.mapped("approve_sequence")))
        self.assertTrue(all(defs.mapped("has_forward")))
```

- [x] **Step 2: รันเทสต์เพื่อยืนยันว่า fail**

Run:
```powershell
.\run-tests.ps1 -Module od19_hr_expense_thai
```
Expected: FAIL — `test_three_tier_definitions_exist` ได้ 0 รายการ

- [x] **Step 3: สร้างไฟล์ข้อมูล tier.definition**

สร้าง `custom_addons/od19_hr_expense_thai/data/tier_definition_data.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo noupdate="1">
    <!--
    HR Expense Tier Validation — สายอนุมัติ 3 ชั้น (อนุมัติตามลำดับ)
      ชั้นที่ 1  หัวหน้าแผนก        (hr_expense.group_hr_expense_manager)   sequence 30
      ชั้นที่ 2  ฝ่ายบัญชี          (account.group_account_manager)         sequence 20
      ชั้นที่ 3  CEO               (od19_hr_expense_thai.group_od19_expense_ceo_approver) sequence 10

    กลไก OCA ``request_validation`` เรียง ``tier.definition`` ด้วย ``sequence desc``
    แล้วแปลงเป็น ``tier.review.sequence`` 1, 2, 3, ...
    => definition ที่ ``sequence`` สูงกว่า จะถูกอนุมัติก่อน (ชั้น 1 = sequence 30)

    ``has_forward`` มาจากโมดูล base_tier_validation_forward (เปิดให้ผู้ตรวจ
    มอบหมายต่อให้ผู้ใช้อื่นในกลุ่มได้)
    -->
    <record id="tier_definition_hr_expense_manager" model="tier.definition">
        <field name="name">Expense - Department Manager (ชั้นที่ 1 หัวหน้าแผนก)</field>
        <field name="model_id" ref="hr_expense.model_hr_expense"/>
        <field name="review_type">group</field>
        <field name="reviewer_group_id" ref="hr_expense.group_hr_expense_manager"/>
        <field name="definition_type">domain</field>
        <field name="definition_domain">[(1, '=', 1)]</field>
        <field name="sequence">30</field>
        <field name="approve_sequence" eval="True"/>
        <field name="has_forward" eval="True"/>
        <field name="company_id" eval="False"/>
        <field name="notify_on_create" eval="True"/>
        <field name="notify_on_pending" eval="True"/>
    </record>

    <record id="tier_definition_hr_expense_accounting" model="tier.definition">
        <field name="name">Expense - Accounting (ชั้นที่ 2 บัญชี)</field>
        <field name="model_id" ref="hr_expense.model_hr_expense"/>
        <field name="review_type">group</field>
        <field name="reviewer_group_id" ref="account.group_account_manager"/>
        <field name="definition_type">domain</field>
        <field name="definition_domain">[(1, '=', 1)]</field>
        <field name="sequence">20</field>
        <field name="approve_sequence" eval="True"/>
        <field name="has_forward" eval="True"/>
        <field name="company_id" eval="False"/>
        <field name="notify_on_create" eval="True"/>
        <field name="notify_on_pending" eval="True"/>
    </record>

    <record id="tier_definition_hr_expense_ceo" model="tier.definition">
        <field name="name">Expense - CEO (ชั้นที่ 3 CEO)</field>
        <field name="model_id" ref="hr_expense.model_hr_expense"/>
        <field name="review_type">group</field>
        <field name="reviewer_group_id" ref="od19_hr_expense_thai.group_od19_expense_ceo_approver"/>
        <field name="definition_type">domain</field>
        <field name="definition_domain">[(1, '=', 1)]</field>
        <field name="sequence">10</field>
        <field name="approve_sequence" eval="True"/>
        <field name="has_forward" eval="True"/>
        <field name="company_id" eval="False"/>
        <field name="notify_on_create" eval="True"/>
        <field name="notify_on_pending" eval="True"/>
    </record>
</odoo>
```

- [x] **Step 4: เพิ่ม dependency + ลงทะเบียน data ใน manifest**

แก้ `custom_addons/od19_hr_expense_thai/__manifest__.py`:
- `depends`: เพิ่ม `'hr_expense_tier_validation'`, `'base_tier_validation'`, `'base_tier_validation_forward'`
- `data`: เพิ่ม `'data/tier_definition_data.xml'` **หลัง** `'security/hr_expense_security.xml'`

ผลลัพธ์ส่วนหัวไฟล์:

```python
    'depends': [
        'hr_expense',
        'hr_expense_tier_validation',
        'base_tier_validation',
        'base_tier_validation_forward',
        'od19_hr_expense_enhanced',
        'od19_accounting_features',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/hr_expense_security.xml',
        'data/tier_definition_data.xml',
        'views/hr_expense_views.xml',
    ],
```

- [x] **Step 5: รันเทสต์เพื่อยืนยันว่าผ่าน**

Run:
```powershell
.\run-tests.ps1 -Module od19_hr_expense_thai
```
Expected: PASS — `test_three_tier_definitions_exist`, `test_tier_definitions_reviewer_groups`, `test_tier_definition_order_and_forward`

- [x] **Step 6: Commit**

```powershell
git add custom_addons/od19_hr_expense_thai/data/tier_definition_data.xml custom_addons/od19_hr_expense_thai/__manifest__.py custom_addons/od19_hr_expense_thai/tests/test_hr_expense_tier.py
git commit -m "feat(od19_hr_expense_thai): add 3-tier approval definitions" -m "tier.definition sequence 30/20/10 (หัวหน้าแผนก/บัญชี/CEO) + เปิด has_forward ผ่าน base_tier_validation_forward"
```

---

## Task 3: ถอดกลไกอนุมัติ 2 ชั้นเดิม (views + models + เทสต์เก่า)

**Files:**
- Modify: `custom_addons/od19_hr_expense_thai/views/hr_expense_views.xml`
- Modify: `custom_addons/od19_hr_expense_thai/models/hr_expense.py`
- Modify: `custom_addons/od19_hr_expense_thai/tests/test_hr_expense_thai.py`

> **หมายเหตุ:** ห้ามลบฟิลด์ (`first_approval_date`, `second_approver_id`, `second_approval_date`, `second_approval_state`, `require_second_approval`) ออกจากโมเดล — คงไว้เพื่อความเข้ากันได้ของข้อมูล (spec §13 K1/K5) แค่ถอดการใช้งานออกจาก form view

- [x] **Step 1: ถอดปุ่มและฟิลด์อนุมัติเดิมออกจาก form view**

แก้ `custom_addons/od19_hr_expense_thai/views/hr_expense_views.xml` ให้เหลือ:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>

    <!-- Extend hr.expense form view -->
    <record id="view_hr_expense_form_inherit_thai" model="ir.ui.view">
        <field name="name">hr.expense.form.inherit.thai</field>
        <field name="model">hr.expense</field>
        <field name="inherit_id" ref="hr_expense.hr_expense_view_form"/>
        <field name="arch" type="xml">
            <field name="payment_mode" position="after">
                <field name="payment_method"/>
                <field name="thai_expense_type"/>
            </field>
            <field name="employee_id" position="after">
                <field name="reimbursement_date"/>
                <field name="od19_reimbursement_payment_id"
                       invisible="not od19_reimbursement_payment_id"/>
            </field>
            <xpath expr="//header" position="inside">
                <button name="action_mark_reimbursed"
                        string="Reimburse Employee"
                        type="object"
                        class="btn-primary"
                        invisible="payment_mode != 'own_account' or not account_move_id or od19_reimbursement_payment_id"/>
            </xpath>
        </field>
    </record>

</odoo>
```

- [x] **Step 2: ถอด method อนุมัติ 2 ชั้นเดิมออกจากโมเดล**

แก้ `custom_addons/od19_hr_expense_thai/models/hr_expense.py` — ลบ 3 method นี้ทั้งหมด (`action_approve_first`, `action_approve_second`, `action_refuse_second`) **โดยคง** `action_mark_reimbursed` และ helper ที่ใช้จ่ายคืนทั้งหมดไว้

หลังแก้ ส่วนหัวของคลาสต้องไม่มี 3 method นั้น (กระโดดจากฟิลด์ไปที่ `action_mark_reimbursed` โดยตรง)

- [x] **Step 3: ลบเทสต์ที่อ้าง method ที่ถอดออก**

แก้ `custom_addons/od19_hr_expense_thai/tests/test_hr_expense_thai.py` — **ลบ 3 method** ต่อไปนี้ออกทั้งบล็อก:
- `test_first_approval_no_second_required`
- `test_first_approval_second_required`
- `test_second_approval`

**คง** `test_payment_method_default`, `test_thai_expense_type_default`, `test_require_second_approval_below_threshold`, `test_require_second_approval_above_threshold`, `test_mark_reimbursed_requires_posted_expense`, `test_mark_reimbursed_company_account_raises`

- [x] **Step 4: ตรวจไวยากรณ์แบบ static**

Run:
```powershell
python -m py_compile custom_addons/od19_hr_expense_thai/models/hr_expense.py custom_addons/od19_hr_expense_thai/tests/test_hr_expense_thai.py
```
Expected: ไม่มีข้อผิดพลาด (exit 0)

- [x] **Step 5: รันเทสต์**

Run:
```powershell
.\run-tests.ps1 -Module od19_hr_expense_thai
```
Expected: PASS ทั้งหมด (ไม่มีเทสต์ที่อ้าง `action_approve_first/second` เหลืออยู่)

- [x] **Step 6: Commit**

```powershell
git add custom_addons/od19_hr_expense_thai/views/hr_expense_views.xml custom_addons/od19_hr_expense_thai/models/hr_expense.py custom_addons/od19_hr_expense_thai/tests/test_hr_expense_thai.py
git commit -m "refactor(od19_hr_expense_thai): drop legacy 2-level approval UI and methods" -m "แทนที่ด้วย tier.validation 3 ชั้น; คงฟิลด์เดิมใน DB ตาม spec §13 K1/K5"
```

---

## Task 4: ทดสอบพฤติกรรม Tier (ลำดับชั้น + ห้ามข้ามขั้น)

**Files:**
- Modify: `custom_addons/od19_hr_expense_thai/tests/test_hr_expense_tier.py`

- [x] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

เพิ่ม helper และเทสต์ต่อไปนี้ใน `TestHrExpenseTierValidation`:

```python
    def _submitted_expense(self, amount=1500.0):
        expense = self.env["hr.expense"].create({
            "name": "Tier Flow Expense",
            "product_id": self.product.id,
            "total_amount": amount,
            "employee_id": self.employee.id,
            "payment_mode": "own_account",
        })
        # เซ็ตตรง ๆ เพื่อเลี่ยง auto-validation ของ core (_can_be_autovalidated)
        expense.approval_state = "submitted"
        return expense

    def test_request_validation_creates_three_reviews(self):
        """การขออนุมัติต้องสร้าง review 3 รายการ เรียงตามลำดับชั้น"""
        expense = self._submitted_expense()
        expense.request_validation()
        self.assertEqual(len(expense.review_ids), 3)
        self.assertEqual(
            expense.review_ids.sorted("sequence").mapped("sequence"), [1, 2, 3]
        )
        self.assertEqual(expense.validation_status, "waiting")

    def test_cannot_approve_out_of_order(self):
        """CEO อนุมัติก่อนลำดับไม่ได้: ต้องหยุดที่ review แรกที่ไม่ใช่ของตน"""
        ceo = self._make_user(
            "tier_ceo", ["od19_hr_expense_thai.group_od19_expense_ceo_approver"]
        )
        expense = self._submitted_expense()
        expense.request_validation()
        expense.with_user(ceo).validate_tier()
        self.assertEqual(expense.validation_status, "waiting")
        self.assertEqual(expense.approval_state, "submitted")

    def test_full_three_level_approval_flow(self):
        """อนุมัติครบ 3 ชั้นตามลำดับ แล้ว validation_status = validated"""
        manager = self._make_user(
            "tier_manager", ["hr_expense.group_hr_expense_manager"]
        )
        accountant = self._make_user(
            "tier_accountant", ["account.group_account_manager"]
        )
        ceo = self._make_user(
            "tier_ceo2", ["od19_hr_expense_thai.group_od19_expense_ceo_approver"]
        )
        expense = self._submitted_expense()
        expense.request_validation()

        expense.with_user(manager).validate_tier()
        self.assertEqual(expense.validation_status, "waiting")

        expense.with_user(accountant).validate_tier()
        self.assertEqual(expense.validation_status, "waiting")

        expense.with_user(ceo).validate_tier()
        self.assertEqual(expense.validation_status, "validated")

    def test_write_blocked_while_under_validation(self):
        """ห้ามแก้ไขเอกสารระหว่างอยู่ภายใต้การอนุมัติ"""
        expense = self._submitted_expense()
        expense.request_validation()
        with self.assertRaises(Exception):
            expense.write({"name": "Hacked"})
```

- [x] **Step 2: รันเทสต์เพื่อยืนยันว่า fail (ถ้ามี)**

Run:
```powershell
.\run-tests.ps1 -Module od19_hr_expense_thai
```
Expected: ถ้า Task 2 ยังไม่ครบ → FAIL ที่ `test_request_validation_creates_three_reviews` (ไม่มี review) · ถ้า Task 2 ครบแล้ว → ผ่านทั้งหมด

- [x] **Step 3: แก้ไขให้ผ่าน (ถ้าจำเป็น)**

ถ้า `test_cannot_approve_out_of_order` fail ให้ตรวจว่า `base_tier_validation` มี logic "หยุดที่ review แรกที่ไม่ใช่ของผู้ใช้" ใน `_validate_tier` (บรรทัด ~565-573) ตามที่ยืนยันไว้ — ถ้าไม่ตรง ให้ **หยุดและรายงานผู้ใช้** ห้าม patch โมดูลใน `third_party/`

> ⚠️ **ห้ามแก้ไฟล์ใน `third_party/oca/`** — หากพฤติกรรมไม่ตรงตามที่คาด ให้รายงานเป็น blocker

- [x] **Step 4: รันเทสต์เพื่อยืนยันว่าผ่าน**

Run:
```powershell
.\run-tests.ps1 -Module od19_hr_expense_thai
```
Expected: PASS ทั้งหมด

- [x] **Step 5: Commit**

```powershell
git add custom_addons/od19_hr_expense_thai/tests/test_hr_expense_tier.py
git commit -m "test(od19_hr_expense_thai): cover 3-tier approval order and write lock" -m "ตรวจลำดับชั้น (ห้ามข้ามขั้น) ครบ 3 ชั้นจน validated และห้ามแก้ไขระหว่าง validation"
```

---

## Task 5: ปรับ Approval Center source ของ `hr.expense` → tier_validation

**Files:**
- Modify: `custom_addons/od19_approval_center/data/approval_sources.py`
- Create: `custom_addons/od19_approval_center/migrations/19.0.1.1.0/post-migrate.py`
- Modify: `custom_addons/od19_approval_center/__manifest__.py`
- Modify: `custom_addons/od19_approval_center/tests/test_approval_seed.py`

> เหตุผลที่ต้องมี migration: `post_init_hook` ข้ามรายการที่มี `model_id + name` อยู่แล้ว → ฐานข้อมูลที่เคย seed ไปแล้วจะไม่ถูกอัปเดต

- [x] **Step 1: เปลี่ยนเทสต์เดิมให้ตรงกับพฤติกรรมใหม่**

แก้ `custom_addons/od19_approval_center/tests/test_approval_seed.py` — แทนที่ `test_expense_source_has_two_steps` ด้วย:

```python
    def test_expense_source_is_tier_without_steps(self):
        post_init_hook(self.env)
        source = self.env["od19.approval.source"].search(
            [("model_name", "=", "hr.expense")], limit=1
        )
        self.assertTrue(source, "hr.expense source should be seeded")
        self.assertEqual(source.strategy, "tier_validation")
        self.assertEqual(len(source.step_ids), 0)
        self.assertEqual(source.sla_days, 3)
```

- [x] **Step 2: รันเทสต์เพื่อยืนยันว่า fail**

Run:
```powershell
.\run-tests.ps1 -Module od19_approval_center
```
Expected: FAIL — `strategy` ยังเป็น `field`

- [x] **Step 3: เปลี่ยน source spec**

แก้ `custom_addons/od19_approval_center/data/approval_sources.py` — แทน dict ของ `hr.expense` (บรรทัด 9-30) เป็น:

```python
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
        "strategy": "tier_validation",
        "sla_days": 3,
        "steps": [],
    },
```

- [x] **Step 4: เพิ่ม migration script สำหรับฐานข้อมูลที่ seed แล้ว**

แก้ `custom_addons/od19_approval_center/__manifest__.py` — `version`: `'19.0.1.0.0'` → `'19.0.1.1.0'`

สร้าง `custom_addons/od19_approval_center/migrations/19.0.1.1.0/post-migrate.py`:

```python
import logging

_logger = logging.getLogger(__name__)

SOURCE_NAME = "ค่าใช้จ่าย (Expense)"


def migrate(cr, version):
    """สลับ source ของ hr.expense จาก field-based เป็น tier_validation."""
    if not version:
        return
    cr.execute(
        """
        SELECT s.id
          FROM od19_approval_source s
          JOIN ir_model m ON m.id = s.model_id
         WHERE m.model = 'hr.expense' AND s.name = %s
         LIMIT 1
        """,
        (SOURCE_NAME,),
    )
    row = cr.fetchone()
    if not row:
        _logger.info("Approval Center: hr.expense source not found, skip")
        return
    source_id = row[0]
    cr.execute(
        "UPDATE od19_approval_source SET strategy = 'tier_validation' WHERE id = %s",
        (source_id,),
    )
    cr.execute("DELETE FROM od19_approval_step WHERE source_id = %s", (source_id,))
    _logger.info(
        "Approval Center: hr.expense source %s switched to tier_validation",
        source_id,
    )
```

- [x] **Step 5: รันเทสต์เพื่อยืนยันว่าผ่าน**

Run:
```powershell
.\run-tests.ps1 -Module od19_approval_center
```
Expected: PASS — `test_expense_source_is_tier_without_steps`

- [x] **Step 6: Commit**

```powershell
git add custom_addons/od19_approval_center/data/approval_sources.py custom_addons/od19_approval_center/migrations/19.0.1.1.0/post-migrate.py custom_addons/od19_approval_center/__manifest__.py custom_addons/od19_approval_center/tests/test_approval_seed.py
git commit -m "feat(od19_approval_center): switch hr.expense source to tier_validation" -m "เพิ่ม migration 19.0.1.1.0 อัปเดต source ที่ seed ไปแล้วให้เป็น tier_validation"
```

---

## Task 6: เพิ่มบทบาท CEO (`role_expense_ceo_approver`) ใน Role Catalog

**Files:**
- Modify: `custom_addons/od19_role_catalog/data/od19_roles_backoffice.xml`
- Modify: `custom_addons/od19_role_catalog/__manifest__.py`
- Modify: `custom_addons/od19_role_catalog/tests/test_role_catalog.py`

- [x] **Step 1: อัปเดตเทสต์ (matrix + จำนวนบทบาท)**

แก้ `custom_addons/od19_role_catalog/tests/test_role_catalog.py`:
- ใน `ROLE_MATRIX` ใต้ family G (ต่อจาก `role_meeting_room_manager`) เพิ่ม:

```python
    "role_expense_ceo_approver": {
        "od19_hr_expense_thai.group_od19_expense_ceo_approver",
    },
```

- ใน `test_all_roles_are_loaded` เปลี่ยน `43` → `44` (ทั้งในข้อความ docstring และ `assertEqual`):

```python
    def test_all_roles_are_loaded(self):
        """บทบาททุกตัวใน matrix ต้องโหลดได้ (44 บทบาท)"""
        missing = []
        for xml_id in ROLE_MATRIX:
            if not self.env.ref(
                "od19_role_catalog.%s" % xml_id, raise_if_not_found=False
            ):
                missing.append(xml_id)
        self.assertFalse(missing, "บทบาทที่โหลดไม่สำเร็จ: %s" % ", ".join(missing))
        self.assertEqual(len(ROLE_MATRIX), 44, "Role Matrix ต้องมี 44 บทบาท")
```

- [x] **Step 2: รันเทสต์เพื่อยืนยันว่า fail**

Run:
```powershell
.\run-tests.ps1 -Module od19_role_catalog
```
Expected: FAIL — `role_expense_ceo_approver` ไม่พบ

- [x] **Step 3: เพิ่มบทบาท CEO**

แก้ `custom_addons/od19_role_catalog/data/od19_roles_backoffice.xml` — เพิ่ม record ต่อจาก `role_meeting_room_manager` (ก่อนสิ้นสุดส่วน G):

```xml
        <!-- ผู้อนุมัติค่าใช้จ่ายชั้น CEO -->
        <record id="role_expense_ceo_approver" model="res.users.role">
            <field name="name">ผู้อนุมัติค่าใช้จ่าย (CEO)</field>
            <field name="sequence">74</field>
            <field name="group_privilege_id" ref="od19_security_roles.od19_role_privilege"/>
            <field name="implied_ids" eval="[
                Command.link(ref('od19_hr_expense_thai.group_od19_expense_ceo_approver')),
                Command.link(ref('hr_expense.group_hr_expense_user')),
            ]"/>
        </record>
```

> หมายเหตุ: `hr_expense.group_hr_expense_user` ให้สิทธิ์อ่าน/ใช้งานโมดูลค่าใช้จ่ายเพื่อให้ CEO เห็นเอกสารที่ต้องอนุมัติ

- [x] **Step 4: เพิ่ม dependency + bump version**

แก้ `custom_addons/od19_role_catalog/__manifest__.py`:
- `version`: `'19.0.1.0.0'` → `'19.0.1.1.0'`
- `depends`: เพิ่ม `"od19_hr_expense_thai"` ในส่วน "OD19 business modules that own the referenced groups"
- `summary`: ปรับข้อความ "~43 res.users.role" → "~44 res.users.role" ให้ตรงกับจำนวนจริง

```python
        "od19_hr_expense_thai",
        "od19_currency_rate_bot",
```

- [x] **Step 5: รันเทสต์เพื่อยืนยันว่าผ่าน**

Run:
```powershell
.\run-tests.ps1 -Module od19_role_catalog
```
Expected: PASS ทั้งหมด (รวม `test_all_roles_are_loaded` = 44)

- [x] **Step 6: Commit**

```powershell
git add custom_addons/od19_role_catalog/data/od19_roles_backoffice.xml custom_addons/od19_role_catalog/__manifest__.py custom_addons/od19_role_catalog/tests/test_role_catalog.py
git commit -m "feat(od19_role_catalog): add CEO expense approver role" -m "บทบาท role_expense_ceo_approver (seq 74) imply กลุ่ม Expense CEO Approver + hr_expense user"
```

---

## Task 7: อัปเดต User Guide Tour ของ HR Expense

**Files:**
- Modify: `custom_addons/od19_user_guide_tours/static/src/tours/hr_expense_tour.js`

> Tour เป็นฝั่ง frontend และต้องสลับผู้ใช้จึงจะทดสอบได้ครบ · ปรับให้สอดคล้องปุ่มใหม่ (Submit → Request Validation → Validate → Reimburse) และใช้ `isActive` กันค้างเหมือนเดิม

- [x] **Step 1: ปรับบรรยายและขั้นตอน L1/L2 แทนด้วยขั้นตอน tier**

แก้ `custom_addons/od19_user_guide_tours/static/src/tours/hr_expense_tour.js`:
- เปลี่ยนข้อความเปิด: `2-level approval` → `3-level tier approval`
- แทนบล็อก L1/L2 (บรรทัด ~103-130) ด้วย:

```javascript
        // --- Tier Validation ---
        // เอกสารที่ต้องขออนุมัติจะแสดงปุ่ม "Request Validation"
        // (need_validation = True) หลัง Submit
        {
            isActive: ["button[name='request_validation']"],
            trigger: "button[name='request_validation']",
            content: markup(_t(
                "Click <b>Request Validation</b> to start the 3-level approval: " +
                "Department Manager → Accounting → CEO."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            isActive: ["button[name='validate_tier']"],
            trigger: "button[name='validate_tier']",
            content: markup(_t(
                "Each approver clicks <b>Validate</b> in their turn. " +
                "Approval follows the sequence and cannot be skipped."
            )),
            tooltipPosition: "left",
            run: "click",
        },
```

- เปลี่ยนข้อความปิดท้าย (บรรทัด ~157-158):

```javascript
            content: markup(_t(
                "HR Expense workflow complete! The process is: <b>Create → Submit → " +
                "Request Validation → Validate ×3 → Approve → Reimbursed</b>. " +
                "Thai expense types and payment methods support local compliance."
            )),
```

- [x] **Step 2: ตรวจไวยากรณ์ JS**

Run:
```powershell
node --check custom_addons/od19_user_guide_tours/static/src/tours/hr_expense_tour.js
```
Expected: exit 0 (ไม่มี syntax error)

- [x] **Step 3: Commit**

```powershell
git add custom_addons/od19_user_guide_tours/static/src/tours/hr_expense_tour.js
git commit -m "docs(od19_user_guide_tours): align expense tour with tier approval" -m "แทนขั้น L1/L2 เดิมด้วย Request Validation + Validate ของ tier.validation"
```

---

## Task 8: ปรับถ้อยคำสเปก Delegations → Forward

**Files:**
- Modify: `docs/superpowers/specs/2026-11-06-od19-hr-expense-reimbursement-design.md`

- [x] **Step 1: ค้นหาจุดที่ต้องแก้**

Run:
```powershell
Select-String -Path docs\superpowers\specs\2026-11-06-od19-hr-expense-reimbursement-design.md -Pattern "Delegat"
```
Expected: พบทุกจุดที่กล่าวถึง Delegations (คาดว่าอยู่ใน §2.1, §8, §11, §13, §15)

- [x] **Step 2: แก้ถ้อยคำ**

แทนที่ทุกคำว่า `Delegations` / `tier_validation_delegation` ด้วย `Forward` / `base_tier_validation_forward` และระบุว่าการมอบหมายต่อทำผ่านฟิลด์ `tier.definition.has_forward = True`

- [x] **Step 3: ยืนยันไม่มีคำเดิมเหลือ**

Run:
```powershell
Select-String -Path docs\superpowers\specs\2026-11-06-od19-hr-expense-reimbursement-design.md -Pattern "Delegat"
```
Expected: ไม่พบผลลัพธ์

- [x] **Step 4: Commit**

```powershell
git add docs/superpowers/specs/2026-11-06-od19-hr-expense-reimbursement-design.md
git commit -m "docs(spec): align expense approval spec with base_tier_validation_forward" -m "แทนแนวทาง Delegations (ไม่มีใน OCA) ด้วย Forward module ตามที่ผู้ใช้อนุมัติ"
```

---

## Final Verification

- [x] **Step 1: รันเทสต์ทั้งชุดของงาน Phase 1**

Run:
```powershell
.\run-tests.ps1 -Module od19_hr_expense_thai,od19_approval_center,od19_role_catalog,od19_hr_expense_enhanced,od19_hr_expense_portal
```
Expected: PASS ทั้ง 3 โมดูล
Result (2026-11-07): `0 failed, 0 error(s) of 82 tests` · exit code 0

- [x] **Step 2: อัปเกรดโมดูลในฐานข้อมูล `odoo19_pdev`**

Run:
```powershell
.\STEP-3-Start-Odoo19.ps1
```
(หรือรัน `odoo-bin -d odoo19_pdev -u od19_hr_expense_thai,od19_approval_center,od19_role_catalog --stop-after-init` ตามสคริปต์ของโปรเจกต์)
Expected: ไม่มี error ตอนโหลด data/migration
Result (2026-11-07): upgrade ผ่านพร้อม migration —
`od19_hr_expense_thai 19.0.1.3.0 post-migrate: linked CEO reviewer group on 1 tier definition(s)` ·
`od19_role_catalog 19.0.1.2.0 post-migrate: linked CEO expense group to role (group 218 -> 220)`
(error เดียวในล็อกคือ `od19_ai_assistant: not installable, skipped` ซึ่งมีมาก่อนแล้วและไม่เกี่ยวกับงานนี้)

- [ ] **Step 3: ทดสอบด้วยมือผ่านหน้าเว็บ (ผู้ใช้ทำ)**

1. สร้างค่าใช้จ่าย (employee) → **Submit** → เห็นปุ่ม **Request Validation**
2. กด **Request Validation** → เห็นบล็อก Validate
3. ล็อกอินเป็นหัวหน้าแผนก → **Validate** → ยังไม่ผ่าน (ยังมี 2 ชั้น)
4. ล็อกอินเป็นบัญชี → **Validate**
5. ล็อกอินเป็น CEO → **Validate** → `validation_status = Validated` → กด **Approve** ของ core ได้
6. ทดสอบ **Forward**: ที่เมนู Tier Validation ตั้งค่า `has_forward` แล้วกด Forward ส่งต่อให้ผู้ใช้อื่นในกลุ่ม

- [x] **Step 4: รายงานผลตาม AGENTS.md §8**

ระบุ: commit SHA ทุกตัว · ไฟล์ที่แตะ · คำสั่งที่รันจริง · ผลลัพธ์จริง (ห้ามอ้างผลที่ยังไม่ได้รัน)

---

## Out of Scope (เฟสถัดไป)

- Phase 2: wizard ฝั่ง backend, mileage backend, สมุดรถ (`od19.employee.vehicle`)
- Phase 3: portal สำหรับพนักงาน
- Phase 4: UI/UX polish + i18n (`i18n/th.po`)
- การลบฟิลด์เดิม (`first_approval_date`, `second_approval_state`, ฯลฯ) ออกจากโมเดล — **ห้ามทำในเฟสนี้**
