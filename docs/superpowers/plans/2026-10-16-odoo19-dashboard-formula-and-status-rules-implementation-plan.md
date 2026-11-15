# Dashboard Formula Engine and Status Rule Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** เพิ่ม Formula engine (14 สูตรสำเร็จรูป + พิมพ์ expression เอง + ประเมินต่อกลุ่มบนกราฟ + อ้างค่าข้าม widget) และ Status rule engine (ตารางกฎ first-match-wins เทียบค่าคงที่ / goal / % ของ goal / widget อื่น / previous / YtY / MtM / QtQ) พร้อม Live Preview ให้โมดูล `od19_dashboard` โดยไม่แก้ Odoo core

**Architecture:** ขยายโมดูลเดิม `custom_addons/od19_dashboard` แบบ additive — เพิ่มโมเดลกฎ `od19.dashboard.widget.rule`, เพิ่มฟิลด์สูตรบน `od19.dashboard.widget`, และแยกตรรกะบริสุทธิ์ (AST validation, preset builder, date shift, compare, safe_eval wrapper) ไปไว้ในโมดูลย่อย `models/dashboard_formula.py` เพื่อทดสอบได้โดยไม่ต้องมีฐานข้อมูล ส่วน `models/dashboard.py` ทำหน้าที่เป็นผู้ประสาน (orchestration) เท่านั้น ทั้งหมดยังทำงานใต้ whitelist เดิม `od19.dashboard.source` และใช้ `safe_eval` ของ Odoo (ห้าม `eval`)

**Tech Stack:** Odoo 19 CE, Python 3, `odoo.tools.safe_eval`, `ast`, OWL 2 (JavaScript), XML views/templates, SCSS, PostgreSQL, Odoo `TransactionCase` tests, Git

**Spec:** `docs/superpowers/specs/2026-10-16-odoo19-dashboard-formula-and-status-rules-design.md`

---

## Design Decisions (ตัดสินใจระหว่างทำ plan — ต้องรับรู้ตอน review)

1. **เพิ่มไฟล์ `models/dashboard_formula.py`** เป็นโมดูลฟังก์ชันบริสุทธิ์ (constants, `build_preset_expression`, `validate_expression`, `evaluate_expression`, `apply_shift`, `compare_values`) — สเปกไม่ได้ระบุไฟล์นี้ แต่จำเป็นเพื่อให้ตรรกะสูตรทดสอบได้แบบ unit test โดยไม่ต้องพึ่ง registry และทำให้ `dashboard.py` ไม่บวมเกินไป (สเปก §4/§7 ยังคงเป็นข้อกำหนดที่ผูกพัน)
2. **`formula_slots` เก็บได้ทั้ง string (measure key) และ number (น้ำหนัก `w1`/`w2`)** — สเปก §3.1 ระบุว่ารองรับ "slot น้ำหนัก w1, w2" ใน `formula_slots` เดียวกัน จึงตีความว่า JSON value ชนิด number = ค่าคงที่น้ำหนัก, ชนิด string = measure key
3. **ไม่บังคับ `compare_value != 0`** เมื่อ `compare_type = constant` (สเปก §3.2 เขียนว่า "ต้องระบุ") — เพราะ `Floor`/`Float` ไม่สามารถแยก "ไม่ได้กรอก" จาก "กรอก 0" ได้ และ 0 เป็นค่าคงที่ที่ถูกต้องในทางธุรกิจ
4. **`total_a` ของสูตร `share` ใน KPI** = ผลรวมของ measure a ทั้งโดเมน (เท่ากับ `a` เอง จึงได้ 100%) ส่วนในกราฟ = ผลรวมของ `a` ทุก bucket (สเปก §4.2 ระบุความหมายของ `total_a` ไว้แล้ว)
5. **ไม่ใช้ git worktree** — โมดูลนี้รันอยู่ใน main workspace และผู้ใช้ทดสอบที่ `http://localhost:8070` โดยตรง (ต่างจาก plan ของ Wave 1 ที่ใช้ worktree)
6. **Known intermediate state:** ระหว่าง Task 5 (rule engine เริ่มอ่าน `rule_ids`) ถึง Task 10 (migration + seed data) widget ที่ seed ไว้จะยังไม่มี rule จึงแสดงสีเขียว/เทา — สถานะนี้หายไปเองเมื่อ Task 10 เสร็จ

---

## Precondition

- โมดูล `od19_dashboard` ติดตั้งอยู่แล้วในฐานข้อมูล `odoo19` (พอร์ต 8070)
- หยุดเซิร์ฟเวอร์ Odoo ก่อนรัน test ทุกครั้ง (ตาม convention ของโครงการ: รันผ่าน main script เดียวและ kill service เก่าก่อน)
- รัน test ด้วยคำสั่งนี้ (จาก `c:\odoo-dev\odoo19`):

```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 -u od19_dashboard --test-enable --test-tags /od19_dashboard --stop-after-init --log-level=test
```

- หมายเหตุ: `-u` ใช้ได้เพราะโมดูลติดตั้งแล้ว (บทเรียนเดิม: ถ้ายังไม่ติดตั้งต้องใช้ `-i`)
- ทำงานบน branch `feature/dashboard-formula-status-rules`; commit แรก (baseline ของโมดูล) = `d582e4e861d` ใช้เป็น BASE_SHA ของ Task แรกได้
- ไฟล์ `security/ir.model.access.csv` และ `data/*.xml` ถูก `.gitignore` บล็อก (`*.csv`, `data/`) — commit baseline บังคับ track ไว้แล้ว (`git add -f`) ดังนั้น `git add` ปกติใน Task ถัด ๆ ไปใช้งานได้ และ `git grep` ใช้ตรวจสอบได้จริง

- **ลำดับการทำงาน (สำคัญ):** ให้ทำ **Task 2 ก่อน Task 1** — Task 1 อ้าง `formula_tools.FORMULA_TYPES` และ import `models/dashboard_formula.py` ซึ่ง Task 2 เป็นผู้สร้าง ถ้าทำ Task 1 ก่อน โมดูลจะ import ไม่ผ่าน (plan ฉบับก่อนหน้าตั้งลำดับสลับกัน; แก้ที่หัวข้อนี้) จากนั้น Task 3–11 ทำตามลำดับปกติ

---

## File Structure

**Create**
- `custom_addons/od19_dashboard/models/dashboard_formula.py` — ฟังก์ชันบริสุทธิ์ของสูตร (constants, preset builder, AST whitelist, safe_eval wrapper, date shift, compare)
- `custom_addons/od19_dashboard/models/dashboard_rule.py` — โมเดล `od19.dashboard.widget.rule`
- `custom_addons/od19_dashboard/tests/__init__.py`
- `custom_addons/od19_dashboard/tests/test_dashboard_rules.py`
- `custom_addons/od19_dashboard/tests/test_dashboard_formula.py`
- `custom_addons/od19_dashboard/tests/test_dashboard_engine.py`
- `custom_addons/od19_dashboard/tests/test_dashboard_migration.py`
- `custom_addons/od19_dashboard/migrations/19.0.2.0.0/pre-migrate.py`
- `custom_addons/od19_dashboard/migrations/19.0.2.0.0/post-migrate.py`

**Modify**
- `custom_addons/od19_dashboard/models/__init__.py`
- `custom_addons/od19_dashboard/models/dashboard.py`
- `custom_addons/od19_dashboard/models/dashboard_source.py`
- `custom_addons/od19_dashboard/__manifest__.py`
- `custom_addons/od19_dashboard/security/ir.model.access.csv`
- `custom_addons/od19_dashboard/security/dashboard_security.xml`
- `custom_addons/od19_dashboard/data/dashboard_data.xml`
- `custom_addons/od19_dashboard/views/dashboard_views.xml`
- `custom_addons/od19_dashboard/static/src/dashboard/builder_dialog.js`
- `custom_addons/od19_dashboard/static/src/dashboard/builder_dialog.xml`
- `custom_addons/od19_dashboard/static/src/dashboard/dashboard_action.js`
- `custom_addons/od19_dashboard/static/src/dashboard/dashboard_action.xml`
- `custom_addons/od19_dashboard/static/src/dashboard/dashboard_action.scss`

**Reuse without changes**
- `odoo/tools/safe_eval.py` (ห้ามแก้)
- `custom_addons/od19_dashboard/models/dashboard_source.py` เดิม (เพิ่ม 1 method เท่านั้น)

---

### Task 1: Status rule model, widget formula fields and security

**Files:**
- Create: `custom_addons/od19_dashboard/models/dashboard_rule.py`
- Create: `custom_addons/od19_dashboard/tests/__init__.py`
- Create: `custom_addons/od19_dashboard/tests/test_dashboard_rules.py`
- Modify: `custom_addons/od19_dashboard/models/__init__.py`
- Modify: `custom_addons/od19_dashboard/models/dashboard.py` (เพิ่มฟิลด์บน `Od19DashboardWidget`, ต่อท้าย `critical_value` ที่บรรทัด 357)
- Modify: `custom_addons/od19_dashboard/security/ir.model.access.csv` (ต่อท้ายบรรทัด 11)
- Modify: `custom_addons/od19_dashboard/security/dashboard_security.xml` (ต่อท้ายก่อน `</odoo>` บรรทัด 101)

- [ ] **Step 1: Write the failing test**

ต่อท้าย `custom_addons/od19_dashboard/tests/__init__.py` (ไฟล์นี้ถูกสร้างไว้แล้วใน Task 2 — ต้อง **เพิ่มบรรทัด** ไม่ใช่เขียนทับ):

```python
from . import test_dashboard_rules
```

สร้าง `custom_addons/od19_dashboard/tests/test_dashboard_rules.py`:

```python
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestDashboardRules(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dashboard = cls.env["od19.dashboard"].create({"name": "Rule test dashboard"})
        cls.source = cls.env.ref("od19_dashboard.source_sale_order")
        cls.widget_a = cls.env["od19.dashboard.widget"].create(
            {
                "dashboard_id": cls.dashboard.id,
                "name": "Widget A",
                "widget_type": "kpi",
                "source_id": cls.source.id,
                "measure_key": "__count",
            }
        )
        cls.widget_b = cls.env["od19.dashboard.widget"].create(
            {
                "dashboard_id": cls.dashboard.id,
                "name": "Widget B",
                "widget_type": "kpi",
                "source_id": cls.source.id,
                "measure_key": "__count",
            }
        )

    def test_widget_has_formula_fields(self):
        for name in (
            "formula_mode",
            "formula_type",
            "formula_slots",
            "formula_expression",
            "formula_basis",
            "delta_basis",
            "default_status",
            "rule_ids",
        ):
            self.assertIn(name, self.env["od19.dashboard.widget"]._fields)

    def test_widget_formula_defaults(self):
        self.assertEqual(self.widget_a.formula_mode, "measure")
        self.assertEqual(self.widget_a.formula_basis, "previous")
        self.assertEqual(self.widget_a.delta_basis, "previous")
        self.assertEqual(self.widget_a.default_status, "green")
        self.assertEqual(self.widget_a.formula_slots, "{}")

    def test_rule_defaults(self):
        rule = self.env["od19.dashboard.widget.rule"].create(
            {"widget_id": self.widget_a.id, "status": "red"}
        )
        self.assertEqual(rule.operator, "<=")
        self.assertEqual(rule.compare_type, "constant")
        self.assertEqual(rule.sequence, 10)
        self.assertTrue(rule.active)

    def test_rule_rejects_self_reference(self):
        with self.assertRaises(ValidationError):
            self.env["od19.dashboard.widget.rule"].create(
                {
                    "widget_id": self.widget_a.id,
                    "compare_type": "widget",
                    "compare_widget_id": self.widget_a.id,
                    "status": "red",
                }
            )

    def test_rule_rejects_cross_dashboard_widget(self):
        other = self.env["od19.dashboard"].create({"name": "Other dashboard"})
        other_widget = self.env["od19.dashboard.widget"].create(
            {
                "dashboard_id": other.id,
                "name": "Other widget",
                "widget_type": "kpi",
                "source_id": self.source.id,
                "measure_key": "__count",
            }
        )
        with self.assertRaises(ValidationError):
            self.env["od19.dashboard.widget.rule"].create(
                {
                    "widget_id": self.widget_a.id,
                    "compare_type": "widget",
                    "compare_widget_id": other_widget.id,
                    "status": "red",
                }
            )

    def test_rule_requires_widget_target(self):
        with self.assertRaises(ValidationError):
            self.env["od19.dashboard.widget.rule"].create(
                {"widget_id": self.widget_a.id, "compare_type": "widget", "status": "red"}
            )

    def test_rule_requires_percent_for_percent_of_goal(self):
        with self.assertRaises(ValidationError):
            self.env["od19.dashboard.widget.rule"].create(
                {
                    "widget_id": self.widget_a.id,
                    "compare_type": "percent_of_goal",
                    "compare_percent": 0,
                    "status": "red",
                }
            )

    def test_rule_ordering_is_sequence_then_id(self):
        first = self.env["od19.dashboard.widget.rule"].create(
            {"widget_id": self.widget_a.id, "sequence": 20, "status": "green"}
        )
        second = self.env["od19.dashboard.widget.rule"].create(
            {"widget_id": self.widget_a.id, "sequence": 10, "status": "red"}
        )
        self.assertEqual(self.widget_a.rule_ids[0], second)
        self.assertEqual(self.widget_a.rule_ids[1], first)
```

- [ ] **Step 2: Run the test to verify it fails**

```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 -u od19_dashboard --test-enable --test-tags /od19_dashboard --stop-after-init --log-level=test
```

Expected: FAIL — `KeyError`/`AttributeError` เพราะ `od19.dashboard.widget.rule` ไม่มีในระบบ และ `formula_mode` ยังไม่มีบน widget

- [ ] **Step 3: Create the rule model**

สร้าง `custom_addons/od19_dashboard/models/dashboard_rule.py`:

```python
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

#: Operators allowed in the left-hand comparison of a status rule.
OPERATORS = [
    (">", "Greater than"),
    (">=", "Greater than or equal"),
    ("<", "Less than"),
    ("<=", "Less than or equal"),
    ("==", "Equal to"),
    ("!=", "Not equal to"),
]

#: Right-hand operand of a status rule.
COMPARE_TYPES = [
    ("constant", "Constant value"),
    ("goal", "Goal"),
    ("percent_of_goal", "Percent of goal"),
    ("widget", "Another widget"),
    ("prev", "Previous period"),
    ("yty", "Same period last year"),
    ("mtm", "Previous month"),
    ("qtq", "Previous quarter"),
]

#: Status colours shared with the KPI baseline.
STATUSES = [
    ("red", "Red"),
    ("yellow", "Yellow"),
    ("green", "Green"),
    ("grey", "Grey"),
]

#: Compare types that need the widget value of a shifted period.
PERIOD_COMPARE_TYPES = ("prev", "yty", "mtm", "qtq")


class Od19DashboardWidgetRule(models.Model):
    """One row of a widget status table.

    The left-hand side of every comparison is always the value of the widget
    that owns the rule; the right-hand side is selected through
    ``compare_type``. Rules are evaluated top to bottom and the first match
    wins, which is why the model is ordered by ``sequence`` then ``id``.
    """

    _name = "od19.dashboard.widget.rule"
    _description = "Dashboard Widget Status Rule"
    _order = "sequence, id"

    widget_id = fields.Many2one(
        "od19.dashboard.widget",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(help="Short label shown in the rule table, e.g. 'Below 20% of goal'.")
    active = fields.Boolean(default=True)

    operator = fields.Selection(selection=OPERATORS, required=True, default="<=")
    compare_type = fields.Selection(
        selection=COMPARE_TYPES,
        required=True,
        default="constant",
    )
    compare_value = fields.Float(help="Used when the compare type is a constant value.")
    compare_percent = fields.Float(
        help="Used with 'Percent of goal': 80 means 80% of the widget goal.",
    )
    compare_widget_id = fields.Many2one(
        "od19.dashboard.widget",
        ondelete="cascade",
        string="Compare with",
    )
    status = fields.Selection(selection=STATUSES, required=True, default="red")

    @api.constrains("widget_id", "compare_widget_id")
    def _check_compare_widget(self):
        for rule in self:
            if not rule.compare_widget_id or not rule.widget_id:
                continue
            if rule.compare_widget_id == rule.widget_id:
                raise ValidationError(
                    _("A status rule cannot compare a widget with itself (rule: %s).")
                    % (rule.name or rule.id)
                )
            if rule.compare_widget_id.dashboard_id != rule.widget_id.dashboard_id:
                raise ValidationError(
                    _("A status rule can only compare widgets of the same dashboard (rule: %s).")
                    % (rule.name or rule.id)
                )

    @api.constrains("compare_type", "compare_widget_id", "compare_percent")
    def _check_compare_target(self):
        for rule in self:
            label = rule.name or rule.id
            if rule.compare_type == "widget" and not rule.compare_widget_id:
                raise ValidationError(
                    _("Choose the widget to compare with (rule: %s).") % label
                )
            if rule.compare_type == "percent_of_goal" and not rule.compare_percent:
                raise ValidationError(
                    _("Set the percentage of the goal to compare with (rule: %s).") % label
                )
```

- [ ] **Step 4: Register the model**

แทนที่ `custom_addons/od19_dashboard/models/__init__.py` ทั้งไฟล์ด้วย:

```python
from . import dashboard_source
from . import dashboard_formula
from . import dashboard
from . import dashboard_rule
```

> หมายเหตุ: การ import `dashboard_formula` ที่นี่ใช้ได้ทันที เพราะ Task 2 (ผู้สร้างไฟล์นั้น) ถูกจัดให้ทำก่อน Task 1 แล้ว — ดู "ลำดับการทำงาน" ในหัวข้อ Precondition ไม่ต้อง comment บรรทัดใดไว้ชั่วคราว

- [ ] **Step 5: Add the formula fields to the widget model**

ใน `custom_addons/od19_dashboard/models/dashboard.py` แก้ส่วน import (บรรทัด 1–9) เป็น:

```python
import json
import logging
from datetime import date, datetime, timedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import format_date, format_datetime
from odoo.tools.safe_eval import safe_eval

from . import dashboard_formula as formula_tools

_logger = logging.getLogger(__name__)
```

> หมายเหตุ: `json` จำเป็นเพราะ `_formula_slot_map` ใช้ `json.loads`; ส่วน `ast` และ `calendar` ไม่ต้อง import ที่นี่ เพราะตรรกะ AST/date shift อยู่ใน `dashboard_formula.py` ทั้งหมด (`formatLang` ก็ไม่ถูกใช้ในไฟล์นี้ — import เกินจะทำให้เกิด lint warning)

จากนั้นเพิ่มค่าคงที่ต่อจาก `DATE_RANGES` (หลังบรรทัด 50):

```python
FORMULA_MODES = [
    ("measure", "Single measure"),
    ("preset", "Preset formula"),
    ("custom", "Custom expression"),
]

FORMULA_BASIS = [
    ("previous", "Previous period"),
    ("yty", "Same period last year"),
    ("mtm", "Previous month"),
    ("qtq", "Previous quarter"),
]

STATUS_SELECTION = [
    ("red", "Red"),
    ("yellow", "Yellow"),
    ("green", "Green"),
    ("grey", "Grey"),
]
```

และแทรกฟิลด์ใหม่ในคลาส `Od19DashboardWidget` ต่อจาก `show_delta` (บรรทัด 358):

```python
    formula_mode = fields.Selection(
        selection=FORMULA_MODES,
        default="measure",
        required=True,
        help="Single measure keeps the historical behaviour; preset and custom "
        "let the user combine several measures.",
    )
    formula_type = fields.Selection(
        selection=formula_tools.FORMULA_TYPES,
        help="Used when the formula mode is 'Preset formula'.",
    )
    formula_slots = fields.Text(
        default="{}",
        help="JSON mapping of slot to measure, e.g. "
        '{"a": "amount_total", "b": "__count"}. Weight slots w1 / w2 hold numbers.',
    )
    formula_expression = fields.Char(
        help="Expression evaluated with safe_eval, used when the formula mode is 'Custom expression'.",
    )
    formula_basis = fields.Selection(
        selection=FORMULA_BASIS,
        default="previous",
        required=True,
        help="Reference period of the growth and cumulative change formulas.",
    )
    delta_basis = fields.Selection(
        selection=FORMULA_BASIS,
        default="previous",
        required=True,
        help="Reference period of the period comparison shown on a KPI.",
    )
    default_status = fields.Selection(
        selection=STATUS_SELECTION,
        default="green",
        required=True,
        help="Status used when no status rule matches.",
    )
    rule_ids = fields.One2many(
        "od19.dashboard.widget.rule",
        "widget_id",
        string="Status Rules",
    )
```

- [ ] **Step 6: Add the ACL rows**

ต่อท้าย `custom_addons/od19_dashboard/security/ir.model.access.csv` (หลังบรรทัด 11):

```csv
access_od19_dashboard_widget_rule_user,access.od19.dashboard.widget.rule.user,model_od19_dashboard_widget_rule,group_od19_dashboard_user,1,1,1,1
access_od19_dashboard_widget_rule_viewer,access.od19.dashboard.widget.rule.viewer,model_od19_dashboard_widget_rule,base.group_user,1,0,0,0
access_od19_dashboard_widget_rule_manager,access.od19.dashboard.widget.rule.manager,model_od19_dashboard_widget_rule,group_od19_dashboard_manager,1,1,1,1
```

- [ ] **Step 7: Add the record rules**

แทรกก่อน `</odoo>` ใน `custom_addons/od19_dashboard/security/dashboard_security.xml`:

```xml
    <!-- ===================== Record rules: widget status rule ===================== -->
    <record id="rule_od19_dashboard_widget_rule_read" model="ir.rule">
        <field name="name">Dashboard widget rule: read from visible dashboard</field>
        <field name="model_id" ref="model_od19_dashboard_widget_rule"/>
        <field name="domain_force">['|', ('widget_id.dashboard_id.shared', '=', True), ('widget_id.dashboard_id.owner_id', '=', user.id)]</field>
        <field name="groups" eval="[Command.link(ref('base.group_user'))]"/>
        <field name="perm_read" eval="True"/>
        <field name="perm_write" eval="False"/>
        <field name="perm_create" eval="False"/>
        <field name="perm_unlink" eval="False"/>
    </record>

    <record id="rule_od19_dashboard_widget_rule_write" model="ir.rule">
        <field name="name">Dashboard widget rule: edit on own dashboard</field>
        <field name="model_id" ref="model_od19_dashboard_widget_rule"/>
        <field name="domain_force">[('widget_id.dashboard_id.owner_id', '=', user.id)]</field>
        <field name="groups" eval="[Command.link(ref('group_od19_dashboard_user'))]"/>
        <field name="perm_read" eval="False"/>
        <field name="perm_write" eval="True"/>
        <field name="perm_create" eval="True"/>
        <field name="perm_unlink" eval="True"/>
    </record>

    <record id="rule_od19_dashboard_widget_rule_manager" model="ir.rule">
        <field name="name">Dashboard widget rule: manager full access</field>
        <field name="model_id" ref="model_od19_dashboard_widget_rule"/>
        <field name="domain_force">[(1, '=', 1)]</field>
        <field name="groups" eval="[Command.link(ref('group_od19_dashboard_manager'))]"/>
        <field name="perm_read" eval="True"/>
        <field name="perm_write" eval="True"/>
        <field name="perm_create" eval="True"/>
        <field name="perm_unlink" eval="True"/>
    </record>
```

- [ ] **Step 8: Run the tests to verify they pass**

```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 -u od19_dashboard --test-enable --test-tags /od19_dashboard --stop-after-init --log-level=test
```

Expected: PASS ทุก test ใน `TestDashboardRules`, EXITCODE 0, ไม่มี warning ใหม่ใน `odoo_server.log`

- [ ] **Step 9: Commit**

```powershell
git add custom_addons/od19_dashboard/models/__init__.py custom_addons/od19_dashboard/models/dashboard.py custom_addons/od19_dashboard/models/dashboard_rule.py custom_addons/od19_dashboard/security/ir.model.access.csv custom_addons/od19_dashboard/security/dashboard_security.xml custom_addons/od19_dashboard/tests/__init__.py custom_addons/od19_dashboard/tests/test_dashboard_rules.py
git commit -m "feat(od19_dashboard): add widget status rule model and formula fields"
```

---

### Task 2: Formula helper module (pure functions)

**Files:**
- Create: `custom_addons/od19_dashboard/models/dashboard_formula.py`
- Create: `custom_addons/od19_dashboard/tests/test_dashboard_formula.py`
- Modify: `custom_addons/od19_dashboard/tests/__init__.py`

- [ ] **Step 1: Write the failing test**

สร้าง `custom_addons/od19_dashboard/tests/test_dashboard_formula.py`:

```python
from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase

from ..models import dashboard_formula as fx


class TestDashboardFormula(TransactionCase):
    def test_preset_expressions(self):
        cases = {
            "ratio": {"a": "x", "b": "y"},
            "difference": {"a": "x", "b": "y"},
            "growth": {"a": "x", "b": "y"},
            "share": {"a": "x"},
            "percent_of_goal": {"a": "x"},
            "min": {"a": "x", "b": "y"},
            "max": {"a": "x", "b": "y"},
            "conversion_rate": {"a": "x", "b": "y"},
            "variance": {"a": "x", "b": "y"},
            "weighted_average": {"a": "x", "b": "y", "w1": 2, "w2": 1},
            "run_rate": {"a": "x"},
            "cumulative_change": {"a": "x"},
        }
        for formula_type, slots in cases.items():
            expression = fx.build_preset_expression(formula_type, slots)
            self.assertTrue(expression.strip(), formula_type)

    def test_preset_sum_and_average_follow_bound_slots(self):
        self.assertEqual(fx.build_preset_expression("sum", {"a": "x", "b": "y", "c": "z"}), "a + b + c")
        self.assertEqual(fx.build_preset_expression("average", {"a": "x", "b": "y"}), "(a + b) / 2")
        self.assertEqual(fx.build_preset_expression("average", {"a": "x"}), "(a) / 1")

    def test_preset_unknown_type_is_rejected(self):
        with self.assertRaises(ValidationError):
            fx.build_preset_expression("does_not_exist", {"a": "x"})

    def test_validate_accepts_allowed_names(self):
        fx.validate_expression(
            "(a - b) / b * 100",
            {"a", "b", "count_records", "goal"},
        )
        fx.validate_expression("min(a, b) + max(goal, 0)", {"a", "b", "goal"})

    def test_validate_rejects_unknown_name(self):
        with self.assertRaises(ValidationError):
            fx.validate_expression("a / secret", {"a"})

    def test_validate_rejects_dunder_count(self):
        with self.assertRaises(ValidationError):
            fx.validate_expression("__count / a", {"a", "count_records"})

    def test_validate_rejects_attribute_access(self):
        with self.assertRaises(ValidationError):
            fx.validate_expression("a.real", {"a"})

    def test_validate_rejects_disallowed_call(self):
        with self.assertRaises(ValidationError):
            fx.validate_expression("open(a)", {"a"})

    def test_validate_rejects_import(self):
        with self.assertRaises(ValidationError):
            fx.validate_expression("__import__('os').getcwd()", {"a"})

    def test_validate_rejects_syntax_error(self):
        with self.assertRaises(ValidationError):
            fx.validate_expression("a /", {"a"})

    def test_evaluate_expression(self):
        context = {"a": 10.0, "b": 4.0, "goal": 100.0, "count_records": 3.0}
        self.assertAlmostEqual(fx.evaluate_expression("a / b", context), 2.5)
        self.assertAlmostEqual(fx.evaluate_expression("(a - b) / b * 100", context), 150.0)
        self.assertAlmostEqual(fx.evaluate_expression("min(a, b)", context), 4.0)

    def test_evaluate_expression_raises_on_zero_division(self):
        with self.assertRaises(ZeroDivisionError):
            fx.evaluate_expression("a / b", {"a": 1.0, "b": 0.0})

    def test_compare_values(self):
        self.assertTrue(fx.compare_values(1.0, "<=", 1.0))
        self.assertTrue(fx.compare_values(2.0, ">", 1.0))
        self.assertTrue(fx.compare_values(1.0, "==", 1.0))
        self.assertTrue(fx.compare_values(1.0, "!=", 2.0))
        self.assertFalse(fx.compare_values(2.0, "<", 1.0))

    def test_shift_previous_keeps_period_length(self):
        start, end = fx.apply_shift(date(2026, 3, 5), date(2026, 3, 16), "previous")
        self.assertEqual((start, end), (date(2026, 2, 21), date(2026, 3, 4)))

    def test_shift_yty_handles_leap_day(self):
        start, end = fx.apply_shift(date(2024, 2, 29), date(2024, 3, 5), "yty")
        self.assertEqual((start, end), (date(2023, 2, 28), date(2023, 3, 5)))

    def test_shift_mtm_snaps_month_end(self):
        start, end = fx.apply_shift(date(2026, 3, 1), date(2026, 3, 31), "mtm")
        self.assertEqual((start, end), (date(2026, 2, 1), date(2026, 2, 28)))

    def test_shift_qtq_uses_previous_quarter(self):
        start, end = fx.apply_shift(date(2026, 4, 1), date(2026, 6, 30), "qtq")
        self.assertEqual((start, end), (date(2026, 1, 1), date(2026, 3, 31)))

    def test_operand_names_helper(self):
        names = fx.expression_names("a + count_records / goal")
        self.assertEqual(names, {"a", "count_records", "goal"})
        self.assertEqual(fx.expression_names("a /"), set())

    def test_operand_names_skip_function_names(self):
        self.assertEqual(fx.expression_names("min(a, b)"), {"a", "b"})
        self.assertEqual(fx.expression_names("abs(a - b) * round(goal)"), {"a", "b", "goal"})

    def test_preset_catalogue_is_complete(self):
        self.assertEqual(len(fx.FORMULA_TYPES), 14)
        self.assertEqual(
            {key for key, _label in fx.FORMULA_TYPES},
            set(fx.PRESET_REQUIRED_SLOTS),
        )

    def test_every_preset_type_builds_an_expression(self):
        for formula_type, _label in fx.FORMULA_TYPES:
            required = fx.PRESET_REQUIRED_SLOTS[formula_type]
            slots = {key: "x" for key in required if key in fx.SLOT_KEYS}
            slots.update({key: 1 for key in required if key in fx.WEIGHT_KEYS})
            self.assertTrue(
                fx.build_preset_expression(formula_type, slots).strip(),
                formula_type,
            )

    def test_preset_sum_and_average_without_slots_return_zero(self):
        self.assertEqual(fx.build_preset_expression("sum", {}), "0")
        self.assertEqual(fx.build_preset_expression("average", {}), "0")
        self.assertEqual(fx.build_preset_expression("cumulative_change", {}), "0")

    def test_validate_rejects_subscript_comprehension_and_lambda(self):
        for expression in ("a[0]", "[x for x in a]", "lambda: 1"):
            with self.assertRaises(ValidationError, msg=expression):
                fx.validate_expression(expression, {"a", "x"})

    def test_validate_rejects_power(self):
        with self.assertRaises(ValidationError):
            fx.validate_expression("a ** b", {"a", "b"})

    def test_compare_values_returns_false_on_none(self):
        self.assertFalse(fx.compare_values(None, "<", 1.0))
        self.assertFalse(fx.compare_values(1.0, "<", None))
```

- [ ] **Step 2: Run the test to verify it fails**

```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 -u od19_dashboard --test-enable --test-tags /od19_dashboard --stop-after-init --log-level=test
```

Expected: FAIL — `ModuleNotFoundError: No module named 'odoo.addons.od19_dashboard.models.dashboard_formula'`

- [ ] **Step 3: Write the helper module**

สร้าง `custom_addons/od19_dashboard/models/dashboard_formula.py`:

```python
"""Pure helpers backing the dashboard formula engine.

Nothing in this module touches the ORM: it accepts plain values so the
formula semantics can be unit tested without a database. ``dashboard.py``
owns the orchestration (read groups, cross widget ordering, fail-soft).
"""

import ast
import calendar
from datetime import timedelta

from odoo import _
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval

#: Preset formula labels exposed to the builder.
FORMULA_TYPES = [
    ("ratio", "Ratio (A ÷ B)"),
    ("difference", "Difference (A − B)"),
    ("growth", "Growth %"),
    ("share", "Share %"),
    ("sum", "Sum"),
    ("average", "Average"),
    ("weighted_average", "Weighted Average"),
    ("percent_of_goal", "% of Goal"),
    ("min", "Min"),
    ("max", "Max"),
    ("cumulative_change", "Cumulative Change"),
    ("run_rate", "Run Rate"),
    ("conversion_rate", "Conversion Rate"),
    ("variance", "Variance"),
]

#: Simple slot formulas; ``sum``, ``average`` and ``cumulative_change`` are built dynamically.
PRESET_EXPRESSIONS = {
    "ratio": "a / b",
    "difference": "a - b",
    "growth": "(a - b) / b * 100",
    "share": "a / total_a * 100",
    "weighted_average": "(a * w1 + b * w2) / (w1 + w2)",
    "percent_of_goal": "a / goal * 100",
    "min": "min(a, b)",
    "max": "max(a, b)",
    "run_rate": "a * days_in_period / days_elapsed",
    "conversion_rate": "a / b * 100",
    "variance": "abs(a - b)",
}

#: Slots a preset formula cannot run without.
PRESET_REQUIRED_SLOTS = {
    "ratio": ("a", "b"),
    "difference": ("a", "b"),
    "growth": ("a", "b"),
    "share": ("a",),
    "sum": ("a", "b"),
    "average": ("a", "b"),
    "weighted_average": ("a", "b", "w1", "w2"),
    "percent_of_goal": ("a",),
    "min": ("a", "b"),
    "max": ("a", "b"),
    "cumulative_change": ("a",),
    "run_rate": ("a",),
    "conversion_rate": ("a", "b"),
    "variance": ("a", "b"),
}

#: Measure slots, in the order used to build the sum / average expressions.
SLOT_KEYS = ("a", "b", "c", "d", "e")
WEIGHT_KEYS = ("w1", "w2")
ALL_SLOT_KEYS = SLOT_KEYS + WEIGHT_KEYS

#: Alias of ``__count``: safe_eval forbids any name containing two underscores.
COUNT_ALIAS = "count_records"

#: Builtin functions a formula may call (all present in safe_eval._BUILTINS).
ALLOWED_CALLS = frozenset({"min", "max", "abs", "round"})

#: Builtin names implicitly exposed to every formula.
IMPLICIT_NAMES = frozenset({"goal", "total_a", "days_in_period", "days_elapsed", COUNT_ALIAS})

ALLOWED_NODES = (
    ast.Expression,
    ast.Name,
    ast.Constant,
    ast.BinOp,
    ast.UnaryOp,
    ast.BoolOp,
    ast.Compare,
    ast.Call,
    ast.Load,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Mod,
    ast.FloorDiv,
    ast.USub,
    ast.UAdd,
    ast.Not,
    ast.And,
    ast.Or,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
)


def build_preset_expression(formula_type, slots):
    """Return the expression a preset formula stands for.

    ``slots`` maps a slot key to a measure key (string) or to a weight
    (number). Only the slots actually bound by the user are used, so
    ``sum`` and ``average`` follow what the user filled in.
    """
    bound = [key for key in SLOT_KEYS if key in slots]
    if formula_type == "sum":
        return " + ".join(bound) if bound else "0"
    if formula_type == "average":
        return "(%s) / %s" % (" + ".join(bound), len(bound)) if bound else "0"
    if formula_type == "cumulative_change":
        return bound[0] if bound else "0"
    expression = PRESET_EXPRESSIONS.get(formula_type)
    if expression is None:
        raise ValidationError(_("Unknown preset formula '%s'.") % formula_type)
    return expression


def expression_names(expression):
    """Return the operand names used by ``expression`` (empty on syntax error).

    Names of the whitelisted functions (:data:`ALLOWED_CALLS`) are calls, not
    operands, so they are left out: ``expression_names("min(a, b)")`` returns
    ``{"a", "b"}`` and no caller ever has to treat ``min`` as a value to
    resolve.
    """
    try:
        tree = ast.parse(expression or "", mode="eval")
    except SyntaxError:
        return set()
    return {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and node.id not in ALLOWED_CALLS
    }


def validate_expression(expression, allowed_names):
    """Validate the syntax, the AST shape and the names of a custom expression.

    Only arithmetic, comparisons, boolean logic and the four whitelisted
    builtins are accepted; attribute access, subscripts, comprehensions,
    lambdas and imports are rejected.
    """
    try:
        tree = ast.parse(expression or "", mode="eval")
    except SyntaxError as error:
        raise ValidationError(
            _("The formula is not a valid expression: %s") % error
        ) from error

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in ALLOWED_CALLS:
                raise ValidationError(
                    _("Only the functions %s can be used in a formula.")
                    % ", ".join(sorted(ALLOWED_CALLS))
                )
            continue
        if isinstance(node, ast.Name):
            if node.id in ALLOWED_CALLS:
                continue
            if node.id not in allowed_names:
                raise ValidationError(
                    _("Unknown name '%s' in the formula. Allowed names: %s.")
                    % (node.id, ", ".join(sorted(allowed_names)))
                )
            continue
        if isinstance(node, ALLOWED_NODES):
            continue
        raise ValidationError(
            _("The formula uses an unsupported construct: %s.") % type(node).__name__
        )
    return tree


def evaluate_expression(expression, context):
    """Evaluate ``expression`` with ``safe_eval`` and return ``float``.

    Raises the underlying arithmetic / name error so the caller can fail
    soft and explain the widget instead of breaking the dashboard.
    """
    result = safe_eval(expression, context)
    if isinstance(result, bool):
        return 1.0 if result else 0.0
    return float(result)


def compare_values(left, operator, right):
    """Apply the rule operator. Returns False when an operand is None."""
    if left is None or right is None:
        return False
    if operator == ">":
        return left > right
    if operator == ">=":
        return left >= right
    if operator == "<":
        return left < right
    if operator == "<=":
        return left <= right
    if operator == "==":
        return left == right
    if operator == "!=":
        return left != right
    return False


def shift_months(value, months):
    """Shift ``value`` by ``months``, clamping the day and snapping month ends."""
    total = (value.year * 12 + value.month - 1) + months
    year, month = divmod(total, 12)
    month += 1
    last_target = calendar.monthrange(year, month)[1]
    last_source = calendar.monthrange(value.year, value.month)[1]
    day = last_target if value.day == last_source else min(value.day, last_target)
    return value.replace(year=year, month=month, day=day)


def shift_years(value, years):
    """Shift ``value`` by ``years``; 29 February falls back to 28 February."""
    try:
        return value.replace(year=value.year - years)
    except ValueError:
        return value.replace(year=value.year - years, month=2, day=28)


def apply_shift(start, end, shift):
    """Return the ``(start, end)`` bounds of the reference period ``shift``."""
    if not start or not end:
        return start, end
    if shift == "previous":
        length = (end - start).days + 1
        new_end = start - timedelta(days=1)
        return new_end - timedelta(days=length - 1), new_end
    if shift == "yty":
        return shift_years(start, 1), shift_years(end, 1)
    if shift == "mtm":
        return shift_months(start, -1), shift_months(end, -1)
    if shift == "qtq":
        return shift_months(start, -3), shift_months(end, -3)
    return start, end
```

- [ ] **Step 4: Register the new test module**

สร้าง `custom_addons/od19_dashboard/tests/__init__.py`:

```python
from . import test_dashboard_formula
```

> หมายเหตุ: บรรทัด `from . import test_dashboard_rules` จะถูก **ต่อท้าย** ใน Task 1 (ซึ่งทำถัดไป) — ที่นี่ต้องมีแค่บรรทัดของ Task 2 เพราะ `test_dashboard_rules.py` ยังไม่มี
> ยังไม่ต้องแก้ `models/__init__.py` ในขั้นนี้ — Task 1 Step 4 จะเขียนทับให้ครบทั้ง 4 import ส่วนเทสต์ที่นี่ import ผ่าน `from ..models import dashboard_formula` จึงทำงานได้โดยไม่ต้องมีบรรทัดนั้น

- [ ] **Step 5: Run the tests to verify they pass**

```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 -u od19_dashboard --test-enable --test-tags /od19_dashboard --stop-after-init --log-level=test
```

Expected: PASS ทั้งหมดใน `TestDashboardFormula`

- [ ] **Step 6: Commit**

```powershell
git add custom_addons/od19_dashboard/models/dashboard_formula.py custom_addons/od19_dashboard/models/__init__.py custom_addons/od19_dashboard/tests/__init__.py custom_addons/od19_dashboard/tests/test_dashboard_formula.py
git commit -m "feat(od19_dashboard): add pure formula helpers with AST whitelist"
```

---

### Task 3: Aggregate request and operand resolution

**Files:**
- Modify: `custom_addons/od19_dashboard/models/dashboard_source.py` (เพิ่ม method ต่อท้าย `_aggregate_spec` ที่บรรทัด 124)
- Modify: `custom_addons/od19_dashboard/models/dashboard.py` (เพิ่ม helper ต่อจาก `_groupby_spec` ที่บรรทัด 613)
- Create: `custom_addons/od19_dashboard/tests/test_dashboard_engine.py`
- Modify: `custom_addons/od19_dashboard/tests/__init__.py`

- [ ] **Step 1: Write the failing test**

สร้าง `custom_addons/od19_dashboard/tests/test_dashboard_engine.py`:

```python
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestDashboardFormulaEngine(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dashboard = cls.env["od19.dashboard"].create({"name": "Engine test dashboard"})
        cls.source = cls.env.ref("od19_dashboard.source_sale_order")
        cls.widget = cls.env["od19.dashboard.widget"].create(
            {
                "dashboard_id": cls.dashboard.id,
                "name": "Engine widget",
                "widget_type": "kpi",
                "source_id": cls.source.id,
                "measure_key": "amount_total",
                "date_key": "date_order",
                "date_range": "this_month",
            }
        )

    def test_aggregate_specs_deduplicates(self):
        specs = self.source._aggregate_specs(["amount_total", "__count", "amount_total"])
        self.assertEqual(specs, ["amount_total:sum", "__count"])

    def test_slot_map_parses_json(self):
        self.widget.formula_slots = '{"a": "amount_total", "b": "__count", "w1": 2}'
        self.assertEqual(
            self.widget._formula_slot_map(),
            {"a": "amount_total", "b": "__count", "w1": 2},
        )

    def test_slot_map_is_empty_on_bad_json(self):
        self.widget.formula_slots = "not json"
        self.assertEqual(self.widget._formula_slot_map(), {})

    def test_requests_in_measure_mode(self):
        self.widget.formula_mode = "measure"
        self.assertEqual(
            self.widget._aggregate_requests(),
            [("value", "amount_total", "amount_total:sum")],
        )

    def test_requests_in_preset_mode(self):
        self.widget.formula_mode = "preset"
        self.widget.formula_type = "ratio"
        self.widget.formula_slots = '{"a": "amount_total", "b": "__count"}'
        self.assertEqual(
            self.widget._aggregate_requests(),
            [("a", "amount_total", "amount_total:sum"), ("b", "__count", "__count")],
        )

    def test_requests_in_custom_mode_use_direct_names(self):
        self.widget.formula_mode = "custom"
        self.widget.formula_expression = "amount_total / count_records"
        self.assertEqual(
            self.widget._aggregate_requests(),
            [
                ("amount_total", "amount_total", "amount_total:sum"),
                ("count_records", "__count", "__count"),
            ],
        )

    def test_allowed_names_include_slots_and_goal(self):
        self.widget.formula_mode = "custom"
        self.widget.formula_expression = "a / goal"
        allowed = self.widget._allowed_names()
        for name in ("a", "b", "goal", "total_a", "count_records", "amount_total"):
            self.assertIn(name, allowed)
        self.assertNotIn("__count", allowed)

    def test_validate_formula_config_accepts_preset(self):
        self.widget.formula_mode = "preset"
        self.widget.formula_type = "ratio"
        self.widget.formula_slots = '{"a": "amount_total", "b": "__count"}'
        self.widget._validate_formula_config()

    def test_validate_formula_config_rejects_missing_slot(self):
        self.widget.formula_mode = "preset"
        self.widget.formula_type = "ratio"
        self.widget.formula_slots = '{"a": "amount_total"}'
        with self.assertRaises(ValidationError):
            self.widget._validate_formula_config()

    def test_validate_formula_config_rejects_unknown_name(self):
        self.widget.formula_mode = "custom"
        self.widget.formula_expression = "a / secret"
        with self.assertRaises(ValidationError):
            self.widget._validate_formula_config()

    def test_effective_expression_for_measure_mode(self):
        self.widget.formula_mode = "measure"
        self.assertEqual(self.widget._effective_expression(), "value")

    def test_effective_expression_for_preset_mode(self):
        self.widget.formula_mode = "preset"
        self.widget.formula_type = "growth"
        self.widget.formula_slots = '{"a": "amount_total", "b": "__count"}'
        self.assertEqual(self.widget._effective_expression(), "(a - b) / b * 100")

    def test_validate_formula_config_accepts_literal_weight_slots(self):
        self.widget.formula_mode = "preset"
        self.widget.formula_type = "weighted_average"
        self.widget.formula_slots = (
            '{"a": "amount_total", "b": "amount_untaxed", "w1": 2, "w2": 1}'
        )
        self.widget._validate_formula_config()

    def test_validate_formula_config_rejects_unknown_slot_measure(self):
        self.widget.formula_mode = "preset"
        self.widget.formula_type = "ratio"
        self.widget.formula_slots = '{"a": "amout_total", "b": "__count"}'
        with self.assertRaises(ValidationError):
            self.widget._validate_formula_config()
```

- [ ] **Step 2: Run the test to verify it fails**

```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 -u od19_dashboard --test-enable --test-tags /od19_dashboard --stop-after-init --log-level=test
```

Expected: FAIL — `AttributeError: 'od19.dashboard.source' object has no attribute '_aggregate_specs'`

- [ ] **Step 3: Add the multi-spec helper on the source**

แทรกต่อท้าย `_aggregate_spec` ใน `custom_addons/od19_dashboard/models/dashboard_source.py`:

```python
    def _aggregate_specs(self, measure_keys):
        """Return the de-duplicated ``_read_group`` aggregate specifications.

        The formula engine needs several measures in a single read group, so
        the order of the returned list is the order of the aggregate columns
        returned by ``_read_group``.
        """
        self.ensure_one()
        specs = []
        for measure_key in measure_keys:
            spec = self._aggregate_spec(measure_key)
            if spec and spec not in specs:
                specs.append(spec)
        return specs
```

- [ ] **Step 4: Add the operand resolution helpers on the widget**

แทรกต่อจาก `_groupby_spec` (หลังบรรทัด 613) ใน `custom_addons/od19_dashboard/models/dashboard.py`:

```python
    # ------------------------------------------------------------------
    # Formula helpers
    # ------------------------------------------------------------------
    def _formula_slot_map(self):
        """Return the slot -> measure / weight mapping stored on the widget."""
        self.ensure_one()
        raw = (self.formula_slots or "").strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            return {}
        if not isinstance(parsed, dict):
            return {}
        return {
            str(key): value
            for key, value in parsed.items()
            if key in formula_tools.ALL_SLOT_KEYS and value not in (None, "")
        }

    def _source_measure_keys(self):
        """Return every measure name the whitelist exposes for this source."""
        self.ensure_one()
        keys = {"__count", formula_tools.COUNT_ALIAS}
        keys.update(
            self.source_id.field_ids.filtered(
                lambda field: field.kind == "measure"
            ).mapped("field_name")
        )
        return keys

    def _effective_expression(self):
        """Return the expression actually evaluated for this widget."""
        self.ensure_one()
        if self.formula_mode == "measure":
            return "value"
        if self.formula_mode == "preset":
            if not self.formula_type:
                return "0"
            return formula_tools.build_preset_expression(
                self.formula_type, self._formula_slot_map()
            )
        return (self.formula_expression or "").strip()

    def _allowed_names(self):
        """Return every name a custom expression of this widget may reference."""
        self.ensure_one()
        names = set(formula_tools.ALL_SLOT_KEYS)
        names |= set(formula_tools.IMPLICIT_NAMES)
        names -= {"__count"}
        names |= {key for key in self._source_measure_keys() if key != "__count"}
        names |= {"widget_%s" % widget_id for widget_id in self._dependency_ids()}
        return names

    def _aggregate_requests(self):
        """Return the de-duplicated ``(alias, measure_key, spec)`` triples to read.

        The list is ordered consistently with the aggregate columns returned
        by a single ``_read_group`` call, so index ``i + 1`` of a result row
        belongs to ``requests[i]``.
        """
        self.ensure_one()
        source = self.source_id
        requests = []
        seen = set()

        def add(alias, measure_key):
            if not measure_key:
                return
            spec = source._aggregate_spec(measure_key)
            if not spec:
                return
            key = (alias, spec)
            if key in seen:
                return
            seen.add(key)
            requests.append((alias, measure_key, spec))

        if self.formula_mode == "measure":
            add("value", self.measure_key or "__count")
            return requests

        if self.formula_mode == "preset":
            slots = self._formula_slot_map()
            for slot_key in formula_tools.SLOT_KEYS:
                measure_key = slots.get(slot_key)
                if isinstance(measure_key, str):
                    add(slot_key, measure_key)
            return requests

        # Custom mode: the names actually written in the expression are
        # resolved one by one — a slot name (a-e) maps to the measure bound to
        # it, count_records maps to the record count, any other name is a
        # measure field of the whitelisted source.
        slots = self._formula_slot_map()
        measure_keys = self._source_measure_keys()
        for name in sorted(formula_tools.expression_names(self.formula_expression)):
            if name in formula_tools.WEIGHT_KEYS:
                continue
            if name in formula_tools.SLOT_KEYS:
                measure_key = slots.get(name)
            elif name == formula_tools.COUNT_ALIAS:
                measure_key = "__count"
            elif name in measure_keys:
                measure_key = name
            else:
                continue
            if isinstance(measure_key, str):
                add(name, measure_key)
        return requests

    def _dependency_ids(self):
        """Return the ids of the other widgets this widget reads.

        A dependency comes from a status rule comparing with another widget and
        from a ``widget_<id>`` name written in a custom expression.
        """
        self.ensure_one()
        ids = set(self.rule_ids.filtered("active").mapped("compare_widget_id").ids)
        for name in formula_tools.expression_names(self._effective_expression()):
            if not name.startswith("widget_"):
                continue
            suffix = name[len("widget_") :]
            if suffix.isdigit():
                ids.add(int(suffix))
        ids.discard(self.id)
        return sorted(ids)

    def _unresolved_names(self):
        """Return the expression names that would have no value at read time."""
        self.ensure_one()
        available = set(formula_tools.IMPLICIT_NAMES)
        # A bound slot always carries a value: a string is a measure key read
        # from the source, a number is a literal weight (``w1`` / ``w2`` of the
        # weighted average) taken from the widget itself.
        available |= set(self._formula_slot_map())
        available |= {"widget_%s" % widget_id for widget_id in self._dependency_ids()}
        available |= {key for key in self._source_measure_keys() if key != "__count"}
        used = formula_tools.expression_names(self._effective_expression())
        return sorted(name for name in used if name not in available)

    def _validate_formula_config(self):
        """Validate the whole formula configuration and raise ``ValidationError``.

        Called by ``create_widget`` / ``update_widget`` / ``preview_widget`` so
        a broken formula is refused while the designer saves it instead of
        failing soft later on the dashboard.
        """
        for widget in self:
            expression = widget._effective_expression()
            if widget.formula_mode == "preset":
                if not widget.formula_type:
                    raise ValidationError(_("Choose a preset formula."))
                missing = [
                    slot_key
                    for slot_key in formula_tools.PRESET_REQUIRED_SLOTS.get(
                        widget.formula_type, ()
                    )
                    if slot_key not in widget._formula_slot_map()
                ]
                if missing:
                    raise ValidationError(
                        _("The preset formula '%(formula)s' needs the slot(s): %(slots)s.")
                        % {"formula": widget.formula_type, "slots": ", ".join(missing)}
                    )
            elif widget.formula_mode == "custom":
                if not (widget.formula_expression or "").strip():
                    raise ValidationError(_("Type the formula of this widget."))
            else:
                continue
            available_measures = widget._source_measure_keys()
            unknown_slots = sorted(
                slot_key
                for slot_key, value in widget._formula_slot_map().items()
                if isinstance(value, str) and value not in available_measures
            )
            if unknown_slots:
                raise ValidationError(
                    _("The slot(s) %s are bound to a field the data source does not offer.")
                    % ", ".join(unknown_slots)
                )
            formula_tools.validate_expression(expression, widget._allowed_names())
            unresolved = widget._unresolved_names()
            if unresolved:
                raise ValidationError(
                    _("The formula uses names without value: %s.") % ", ".join(unresolved)
                )
```

- [ ] **Step 5: Run the tests to verify they pass**

```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 -u od19_dashboard --test-enable --test-tags /od19_dashboard --stop-after-init --log-level=test
```

Expected: PASS ทั้ง `TestDashboardRules`, `TestDashboardFormula` และ `TestDashboardFormulaEngine`

- [ ] **Step 6: Commit**

```powershell
git add custom_addons/od19_dashboard/models/dashboard.py custom_addons/od19_dashboard/models/dashboard_source.py custom_addons/od19_dashboard/tests/__init__.py custom_addons/od19_dashboard/tests/test_dashboard_engine.py
git commit -m "feat(od19_dashboard): resolve formula operands and aggregate requests"
```

---

### Task 4: Status rule engine and period shift

**Files:**
- Modify: `custom_addons/od19_dashboard/models/dashboard_rule.py` (เพิ่ม `_compare_operand` ต่อท้าย `_check_compare_target` และลบ `PERIOD_COMPARE_TYPES`)
- Modify: `custom_addons/od19_dashboard/models/dashboard_formula.py` (เพิ่ม `PERIOD_COMPARE_TYPES` ต่อจาก `IMPLICIT_NAMES`) — Step 3b
- Modify: `custom_addons/od19_dashboard/models/dashboard.py` (`_period_bounds` / `_date_bounds` / `_build_domain` และเพิ่ม `_required_shifts`, `_evaluate_rules`, `_is_lower_better`)
- Modify: `custom_addons/od19_dashboard/tests/test_dashboard_engine.py` (เพิ่มคลาส `TestDashboardRuleEngine` — 21 เทสต์)

- [ ] **Step 1: Write the failing test**

ต่อท้าย `custom_addons/od19_dashboard/tests/test_dashboard_engine.py` (และเพิ่ม import 2 บรรทัดบนสุดของไฟล์ — ปัจจุบันมีแค่ `ValidationError` กับ `TransactionCase`):

```python
from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase
```

แล้วต่อท้ายไฟล์ด้วย:

```python
class TestDashboardRuleEngine(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dashboard = cls.env["od19.dashboard"].create({"name": "Rule engine dashboard"})
        cls.source = cls.env.ref("od19_dashboard.source_sale_order")
        cls.widget_a = cls.env["od19.dashboard.widget"].create(
            {
                "dashboard_id": cls.dashboard.id,
                "name": "Widget A",
                "widget_type": "kpi",
                "source_id": cls.source.id,
                "measure_key": "amount_total",
                "date_key": "date_order",
                "date_range": "this_month",
            }
        )
        cls.widget_b = cls.env["od19.dashboard.widget"].create(
            {
                "dashboard_id": cls.dashboard.id,
                "name": "Widget B",
                "widget_type": "kpi",
                "source_id": cls.source.id,
                "measure_key": "__count",
            }
        )

    def _rule(self, **values):
        values.setdefault("widget_id", self.widget_a.id)
        values.setdefault("status", "red")
        return self.env["od19.dashboard.widget.rule"].create(values)

    def test_operand_constant(self):
        rule = self._rule(compare_type="constant", compare_value=12.5)
        self.assertEqual(rule._compare_operand({"value": 3.0}), 12.5)

    def test_operand_goal(self):
        rule = self._rule(compare_type="goal")
        self.assertEqual(rule._compare_operand({"value": 3.0, "goal": 900.0}), 900.0)

    def test_operand_percent_of_goal(self):
        rule = self._rule(compare_type="percent_of_goal", compare_percent=80.0)
        self.assertEqual(rule._compare_operand({"value": 3.0, "goal": 1000.0}), 800.0)

    def test_operand_shifted_period(self):
        rule = self._rule(compare_type="yty")
        self.assertEqual(rule._compare_operand({"shifts": {"yty": 42.0}}), 42.0)
        self.assertIsNone(rule._compare_operand({"shifts": {}}))

    def test_operand_other_widget(self):
        rule = self._rule(compare_type="widget", compare_widget_id=self.widget_b.id)
        context = {"widget_values": {self.widget_b.id: 7.0}}
        self.assertEqual(rule._compare_operand(context), 7.0)

    def test_evaluate_rules_first_match_wins(self):
        self._rule(sequence=10, operator="<=", compare_value=100.0, status="red")
        self._rule(sequence=20, operator="<=", compare_value=500.0, status="yellow")
        status, source = self.widget_a._evaluate_rules({"value": 50.0})
        self.assertEqual(status, "red")
        self.assertEqual(source, "rule")

    def test_evaluate_rules_continues_when_rule_does_not_match(self):
        self._rule(sequence=10, operator="<=", compare_value=10.0, status="red")
        self._rule(sequence=20, operator="<=", compare_value=500.0, status="yellow")
        status, source = self.widget_a._evaluate_rules({"value": 50.0})
        self.assertEqual((status, source), ("yellow", "rule"))

    def test_evaluate_rules_falls_back_to_default_status(self):
        self.widget_a.default_status = "grey"
        self.assertEqual(self.widget_a._evaluate_rules({"value": 50.0}), ("grey", "default"))

    def test_evaluate_rules_skips_inactive_rules(self):
        self._rule(compare_value=100.0, status="red", active=False)
        self.widget_a.default_status = "green"
        self.assertEqual(self.widget_a._evaluate_rules({"value": 50.0}), ("green", "default"))

    def test_evaluate_rules_ignores_none_value(self):
        self._rule(compare_value=100.0, status="red")
        self.widget_a.default_status = "grey"
        self.assertEqual(self.widget_a._evaluate_rules({"value": None}), ("grey", "default"))

    def test_required_shifts_collects_delta_rules_and_formula(self):
        self.widget_a.delta_basis = "mtm"
        self.widget_a.formula_mode = "custom"
        self.widget_a.formula_expression = "amount_total"
        self.widget_a.formula_basis = "qtq"
        self._rule(compare_type="yty", status="red")
        self.assertEqual(self.widget_a._required_shifts(), {"mtm", "qtq", "yty"})

    def test_required_shifts_skips_delta_when_hidden(self):
        self.widget_a.show_delta = False
        self.widget_a.delta_basis = "mtm"
        self.assertEqual(self.widget_a._required_shifts(), set())

    def test_date_bounds_applies_previous_shift(self):
        # ``apply_shift(..., "previous")`` uses inclusive bounds, so a 12 day
        # window (2026-03-05 → 2026-03-16) shifts to 2026-02-21 → 2026-03-04.
        # This mirrors ``test_shift_previous_keeps_period_length`` in
        # ``test_dashboard_formula.py``.
        bounds = self.widget_a._date_bounds("this_year", "2026-03-05", "2026-03-16", shift="previous")
        self.assertEqual(
            bounds,
            [
                ("date_order", ">=", "2026-02-21 00:00:00"),
                ("date_order", "<=", "2026-03-04 23:59:59"),
            ],
        )

    def test_date_bounds_applies_yty_shift(self):
        bounds = self.widget_a._date_bounds("this_year", "2026-03-01", "2026-03-31", shift="yty")
        self.assertEqual(
            bounds,
            [
                ("date_order", ">=", "2025-03-01 00:00:00"),
                ("date_order", "<=", "2025-03-31 23:59:59"),
            ],
        )

    def test_date_bounds_shift_none_keeps_the_period(self):
        bounds = self.widget_a._date_bounds("this_year", "2026-03-01", "2026-03-31")
        self.assertEqual(
            bounds,
            [
                ("date_order", ">=", "2026-03-01 00:00:00"),
                ("date_order", "<=", "2026-03-31 23:59:59"),
            ],
        )

    def test_period_bounds_all_time_has_no_bounds(self):
        start, end, field_type = self.widget_a._period_bounds("all_time")
        self.assertIsNone(start)
        self.assertIsNone(end)
        self.assertEqual(field_type, "datetime")

    def test_period_bounds_without_date_key_has_no_bounds(self):
        start, end, field_type = self.widget_b._period_bounds("this_month")
        self.assertIsNone(start)
        self.assertIsNone(end)
        self.assertEqual(field_type, "date")

    def test_period_bounds_overdue_starts_at_none(self):
        today = fields.Date.context_today(self.widget_a)
        start, end, _field_type = self.widget_a._period_bounds("overdue")
        self.assertIsNone(start)
        self.assertEqual(end, today - timedelta(days=1))

    def test_date_bounds_on_a_date_field_has_no_time_suffix(self):
        widget = self.env["od19.dashboard.widget"].create(
            {
                "dashboard_id": self.dashboard.id,
                "name": "Date field widget",
                "widget_type": "kpi",
                "source_id": self.env.ref("od19_dashboard.source_account_move").id,
                "measure_key": "amount_total",
                "date_key": "invoice_date",
                "date_range": "this_year",
            }
        )
        bounds = widget._date_bounds("this_year", "2026-03-01", "2026-03-31")
        self.assertEqual(
            bounds,
            [
                ("invoice_date", ">=", "2026-03-01"),
                ("invoice_date", "<=", "2026-03-31"),
            ],
        )

    def test_is_lower_better_inferred_from_the_first_red_rule(self):
        self.assertFalse(self.widget_a._is_lower_better())
        self._rule(operator="<=", compare_value=100.0, status="red")
        self.assertFalse(self.widget_a._is_lower_better())
        self.widget_a.rule_ids.unlink()
        self._rule(operator=">=", compare_value=100.0, status="red")
        self.assertTrue(self.widget_a._is_lower_better())

    def test_unresolved_names_detects_unbound_slot(self):
        self.widget_a.formula_mode = "custom"
        self.widget_a.formula_expression = "a + amount_total"
        self.assertEqual(self.widget_a._unresolved_names(), ["a"])
        self.widget_a.formula_slots = '{"a": "amount_total"}'
        self.assertEqual(self.widget_a._unresolved_names(), [])
```

- [ ] **Step 2: Run the test to verify it fails**

```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 -u od19_dashboard --test-enable --test-tags /od19_dashboard --stop-after-init --log-level=test
```

Expected: FAIL — `AttributeError: 'od19.dashboard.widget.rule' object has no attribute '_compare_operand'`

- [ ] **Step 3: Add the rule engine**

ต่อท้าย `_check_compare_target` ใน `custom_addons/od19_dashboard/models/dashboard_rule.py`:

```python
    def _compare_operand(self, context):
        """Return the right-hand value of the comparison.

        ``context`` is the operand dictionary built by the widget:
        ``{"value": float, "goal": float, "shifts": {shift: float},
        "widget_values": {widget_id: float}}``. Returns ``None`` when the
        operand cannot be resolved, in which case the rule does not match.
        """
        self.ensure_one()
        if self.compare_type == "constant":
            return self.compare_value
        if self.compare_type == "goal":
            return context.get("goal")
        if self.compare_type == "percent_of_goal":
            goal = context.get("goal")
            if not goal or not self.compare_percent:
                return None
            return goal * self.compare_percent / 100.0
        if self.compare_type == "widget":
            if not self.compare_widget_id:
                return None
            return context.get("widget_values", {}).get(self.compare_widget_id.id)
        shift = "previous" if self.compare_type == "prev" else self.compare_type
        return context.get("shifts", {}).get(shift)
```

และแทรกในคลาส `Od19DashboardWidget` ต่อจาก `_validate_formula_config` ใน `custom_addons/od19_dashboard/models/dashboard.py`:

```python
    # ------------------------------------------------------------------
    # Status rules
    # ------------------------------------------------------------------
    def _required_shifts(self):
        """Return the shifted periods this widget needs to read.

        Derived from the period comparison of the KPI (``delta_basis``), from
        the reference period of growth / cumulative change formulas
        (``formula_basis``) and from the status rules comparing a period.
        """
        self.ensure_one()
        shifts = set()
        if self.show_delta and self.delta_basis:
            shifts.add(self.delta_basis)
        if self.formula_mode in ("preset", "custom") and self.formula_basis:
            shifts.add(self.formula_basis)
        shifts.update(
            self.rule_ids.filtered(
                lambda rule: rule.active and rule.compare_type in formula_tools.PERIOD_COMPARE_TYPES
            ).mapped("compare_type")
        )
        return {"previous" if shift == "prev" else shift for shift in shifts}

    def _is_lower_better(self):
        """Infer the direction of the KPI so the delta can be coloured.

        A red rule that triggers on a *high* value means a low value is good
        (``lower is better``); a red rule triggering on a low value means the
        opposite. Defaults to ``higher is better`` when no red rule exists.
        """
        self.ensure_one()
        for rule in self.rule_ids.filtered("active"):
            if rule.status == "red":
                return rule.operator in (">", ">=")
        return False

    def _evaluate_rules(self, context):
        """Return ``(status, status_source)`` with a first-match-wins table.

        ``status_source`` is ``"rule"`` when a rule matched and ``"default"``
        when the widget falls back to ``default_status``. The left-hand side of
        every comparison is always the value of this widget.
        """
        self.ensure_one()
        if context.get("value") is not None:
            for rule in self.rule_ids.filtered("active"):
                operand = rule._compare_operand(context)
                if formula_tools.compare_values(context.get("value"), rule.operator, operand):
                    return rule.status, "rule"
        return self.default_status, "default"
```

`PERIOD_COMPARE_TYPES` และ `formula_tools` ต้องเข้าถึงได้จาก `dashboard.py`:

- import block ของ `custom_addons/od19_dashboard/models/dashboard.py` ถูกวางไว้ถูกต้องแล้วใน **Task 1 Step 5** — ใน Task นี้ **ไม่ต้องแก้ import block** เพียงตรวจสอบว่าเป็นเวอร์ชันนี้ (ห้ามมี `ast`, `calendar`, `formatLang` และห้าม `from .dashboard_rule import ...`):

```python
import json
import logging
from datetime import date, datetime, timedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import format_date, format_datetime
from odoo.tools.safe_eval import safe_eval

from . import dashboard_formula as formula_tools

_logger = logging.getLogger(__name__)
```

> เหตุผลที่ Step 3b ย้ายค่าคงที่: `PERIOD_COMPARE_TYPES` เป็นคำศัพท์ที่ **ทั้ง** `dashboard.py` (ผ่าน `_required_shifts`) และ `dashboard_rule.py` (ผ่าน `COMPARE_TYPES` ของ domain เดียวกัน) ต้องใช้ การประกาศไว้ใน `dashboard_formula.py` ซึ่งเป็นโมดูล pure helper (ไม่แตะ ORM) ทำให้ทั้งสองไฟล์อ้างผ่าน `formula_tools.PERIOD_COMPARE_TYPES` ได้โดยไม่ต้องให้ `dashboard.py` import ข้ามไปยังโมเดลไฟล์ `dashboard_rule.py` (ซึ่ง `models/__init__.py` โหลดทีหลัง) — ลำดับโหลดคือ `dashboard_source`, `dashboard_formula`, `dashboard`, `dashboard_rule`
>
> **ห้าม re-export** — `PERIOD_COMPARE_TYPES` ไม่มีผู้เรียกใช้จาก `dashboard_rule` อีกต่อไป และการวาง `import` ไว้กลางไฟล์ (หลังค่าคงที่ module level) จะขัดกฎ `E402` (module level import not at top) ของ `ruff.toml` ที่ repo ใช้บน runbot — `# noqa: F401` ปิดได้เฉพาะ `F401` ไม่ปิด `E402`

- [ ] **Step 3b: Move `PERIOD_COMPARE_TYPES` to the formula module**

ใน `custom_addons/od19_dashboard/models/dashboard_formula.py` เพิ่มต่อจาก `IMPLICIT_NAMES`:

```python
#: Compare types of a status rule that need the widget value of a shifted period.
PERIOD_COMPARE_TYPES = ("prev", "yty", "mtm", "qtq")
```

และใน `custom_addons/od19_dashboard/models/dashboard_rule.py` **ลบบรรทัดค่าคงที่**

```python
#: Compare types that need the widget value of a shifted period.
PERIOD_COMPARE_TYPES = ("prev", "yty", "mtm", "qtq")
```

ออกทั้งหมด — **ห้าม** แทนด้วย `from .dashboard_formula import PERIOD_COMPARE_TYPES` เพราะ (ก) ไม่มีผู้เรียกใช้ค่าคงที่นี้ผ่าน `dashboard_rule` อีกแล้ว (มีแต่ `formula_tools.PERIOD_COMPARE_TYPES` ใน `dashboard.py`) และ (ข) `import` ที่วางกลางไฟล์ (หลัง `OPERATORS` / `COMPARE_TYPES` / `STATUSES`) จะขัดกฎ ruff `E402` ซึ่ง `ruff.toml` ของ repo เปิดไว้

แล้วใน `dashboard.py` ให้ import จาก formula module:

```python
from . import dashboard_formula as formula_tools
```

และใช้ `formula_tools.PERIOD_COMPARE_TYPES` ใน `_required_shifts()` แทนชื่อเปล่า

- [ ] **Step 4: Turn `previous` into a full period shift**

ใน `custom_addons/od19_dashboard/models/dashboard.py` แทน `_build_domain` (บรรทัด 615–635) และ `_date_bounds` (บรรทัด 637–686) ด้วย:

```python
    def _build_domain(self, date_range=None, date_from=None, date_to=None, shift=None):
        self.ensure_one()
        domain = []
        raw_domain = (self.domain or "").strip()
        if raw_domain:
            try:
                parsed = safe_eval(raw_domain)
            except Exception as error:  # noqa: BLE001
                raise ValidationError(
                    _("The filter of widget '%s' is not valid: %s") % (self.name, error)
                ) from error
            if not isinstance(parsed, list):
                raise ValidationError(
                    _("The filter of widget '%s' must be a list (Odoo domain).") % self.name
                )
            domain += parsed

        effective_range = date_range or self.date_range or "all_time"
        if self.date_key and effective_range != "all_time":
            domain += self._date_bounds(effective_range, date_from, date_to, shift)
        return domain

    def _period_bounds(self, date_range=None, date_from=None, date_to=None, shift=None):
        """Return the ``(start, end)`` dates of the period the widget reads.

        ``shift`` moves the window back in time: ``previous`` (same length),
        ``yty`` (same period last year), ``mtm`` (previous month) or ``qtq``
        (previous quarter). ``(None, None, field_type)`` means "no date bound",
        which is the case for ``all_time`` and for a widget without a date
        field. Always returns three values, so the caller can unpack
        ``start, end, field_type`` without a special case.
        """
        self.ensure_one()
        field_type = "date"
        if self.date_key and self.source_id.model_name in self.env:
            field = self.env[self.source_id.model_name]._fields.get(self.date_key)
            field_type = field.type if field else "date"
        if not self.date_key:
            return None, None, field_type
        effective_range = date_range or self.date_range or "all_time"
        if effective_range == "all_time":
            return None, None, field_type

        today = fields.Date.context_today(self)

        start = end = None
        if date_from or date_to:
            start = fields.Date.to_date(date_from) if date_from else None
            end = fields.Date.to_date(date_to) if date_to else None
        elif effective_range == "today":
            start = end = today
        elif effective_range == "yesterday":
            start = end = today - timedelta(days=1)
        elif effective_range == "last_7_days":
            start, end = today - timedelta(days=6), today
        elif effective_range == "last_30_days":
            start, end = today - timedelta(days=29), today
        elif effective_range == "last_90_days":
            start, end = today - timedelta(days=89), today
        elif effective_range == "this_month":
            start, end = today.replace(day=1), today
        elif effective_range == "this_quarter":
            start, end = today.replace(month=3 * ((today.month - 1) // 3) + 1, day=1), today
        elif effective_range == "this_year":
            start, end = today.replace(month=1, day=1), today
        elif effective_range == "next_7_days":
            start, end = today, today + timedelta(days=7)
        elif effective_range == "overdue":
            start, end = None, today - timedelta(days=1)
        else:
            return None, None, field_type

        if shift:
            start, end = formula_tools.apply_shift(start, end, shift)
        return start, end, field_type

    def _date_bounds(self, range_key, date_from, date_to, shift=None):
        self.ensure_one()
        start, end, field_type = self._period_bounds(range_key, date_from, date_to, shift)
        bounds = []
        if field_type == "date":
            if start:
                bounds.append((self.date_key, ">=", start.isoformat()))
            if end:
                bounds.append((self.date_key, "<=", end.isoformat()))
            return bounds
        if start:
            bounds.append((self.date_key, ">=", "%s 00:00:00" % start.isoformat()))
        if end:
            bounds.append((self.date_key, "<=", "%s 23:59:59" % end.isoformat()))
        return bounds
```

> หมายเหตุ: `_period_bounds` คืน 3 ค่า แต่ผู้เรียกที่ต้องการแค่ขอบเขตให้ใช้ `start, end, _field_type = ...` — ใน Task 6 มี helper `_shifted_period()` ห่อไว้อีกชั้นเพื่อให้อ่านง่าย

- [ ] **Step 5: Point the KPI delta to the new shift API**

ใน `_fill_kpi_data` (บรรทัด 520) แทน

```python
            previous_domain = self._build_domain(date_range, date_from, date_to, previous=True)
```

ด้วย

```python
            previous_domain = self._build_domain(date_range, date_from, date_to, shift="previous")
```

- [ ] **Step 6: Run the tests to verify they pass**

```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 -u od19_dashboard --test-enable --test-tags /od19_dashboard --stop-after-init --log-level=test
```

Expected: PASS ทุก test ใน `TestDashboardRuleEngine` และ test เดิมยังผ่านทั้งหมด

- [ ] **Step 7: Commit**

```powershell
git add custom_addons/od19_dashboard/models/dashboard.py custom_addons/od19_dashboard/models/dashboard_rule.py custom_addons/od19_dashboard/models/dashboard_formula.py custom_addons/od19_dashboard/tests/test_dashboard_engine.py
git commit -m "feat(od19_dashboard): evaluate widget status rules and period shifts"
```

---

### Task 5: Cross-widget dependency order

**Files:**
- Modify: `custom_addons/od19_dashboard/models/dashboard.py` (`get_dashboard_data` ที่บรรทัด 188–221, `_get_widget_data` ที่บรรทัด 452 — เพิ่มพารามิเตอร์ `widget_values`)
- Modify: `custom_addons/od19_dashboard/tests/test_dashboard_engine.py` (เพิ่มคลาส `TestDashboardOrdering`)

- [ ] **Step 1: Write the failing test**

ต่อท้าย `custom_addons/od19_dashboard/tests/test_dashboard_engine.py`:

```python
class TestDashboardOrdering(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dashboard = cls.env["od19.dashboard"].create({"name": "Ordering dashboard"})
        cls.source = cls.env.ref("od19_dashboard.source_sale_order")
        cls.widget_a = cls._make_widget(cls, "Widget A")
        cls.widget_b = cls._make_widget(cls, "Widget B")
        cls.widget_c = cls._make_widget(cls, "Widget C")

    def _make_widget(self, name):
        return self.env["od19.dashboard.widget"].create(
            {
                "dashboard_id": self.dashboard.id,
                "name": name,
                "widget_type": "kpi",
                "source_id": self.source.id,
                "measure_key": "__count",
            }
        )

    def test_dependency_ids_from_rule_and_expression(self):
        self.env["od19.dashboard.widget.rule"].create(
            {
                "widget_id": self.widget_a.id,
                "compare_type": "widget",
                "compare_widget_id": self.widget_b.id,
                "status": "green",
            }
        )
        self.widget_c.formula_mode = "custom"
        self.widget_c.formula_expression = "count_records + widget_%s" % self.widget_a.id
        self.assertEqual(self.widget_a._dependency_ids(), [self.widget_b.id])
        self.assertEqual(self.widget_c._dependency_ids(), [self.widget_a.id])

    def test_dependency_ids_never_contains_the_widget_itself(self):
        self.widget_c.formula_mode = "custom"
        self.widget_c.formula_expression = "count_records + widget_%s" % self.widget_c.id
        self.assertEqual(self.widget_c._dependency_ids(), [])

    def test_compute_order_places_dependencies_first(self):
        self.widget_c.formula_mode = "custom"
        self.widget_c.formula_expression = "count_records + widget_%s" % self.widget_a.id
        ordered = self.dashboard._compute_order()
        self.assertLess(ordered.index(self.widget_a), ordered.index(self.widget_c))

    def test_compute_order_survives_a_cycle(self):
        self.widget_a.formula_mode = "custom"
        self.widget_a.formula_expression = "count_records + widget_%s" % self.widget_b.id
        self.widget_b.formula_mode = "custom"
        self.widget_b.formula_expression = "count_records + widget_%s" % self.widget_a.id
        ordered = self.dashboard._compute_order()
        # Widget C has no dependency, so it is emitted first. The A/B pair is a
        # cycle and cannot be ordered: the fallback emits the remaining widgets
        # in (sequence, id) order, which here is A then B. No widget is lost.
        self.assertEqual(ordered, [self.widget_c, self.widget_a, self.widget_b])

    def test_compute_order_skips_inactive_widgets(self):
        self.widget_b.active = False
        self.widget_c.formula_mode = "custom"
        self.widget_c.formula_expression = "count_records + widget_%s" % self.widget_b.id
        ordered = self.dashboard._compute_order()
        # An inactive widget is never emitted, but reading it must not block
        # the widget that refers to it.
        self.assertEqual(ordered, [self.widget_a, self.widget_c])

    def test_compute_order_ignores_a_dependency_outside_the_dashboard(self):
        other = self.env["od19.dashboard"].create({"name": "Other ordering dashboard"})
        foreign = self.env["od19.dashboard.widget"].create(
            {
                "dashboard_id": other.id,
                "name": "Foreign widget",
                "widget_type": "kpi",
                "source_id": self.source.id,
                "measure_key": "__count",
            }
        )
        self.widget_c.formula_mode = "custom"
        self.widget_c.formula_expression = "count_records + widget_%s" % foreign.id
        ordered = self.dashboard._compute_order()
        # A dependency that is not part of this dashboard is already satisfied,
        # so it must neither deadlock the sort nor be emitted.
        self.assertEqual(len(ordered), 3)
        self.assertNotIn(foreign, ordered)

    def test_get_dashboard_data_returns_every_widget_with_a_cross_widget_rule(self):
        self.env["od19.dashboard.widget.rule"].create(
            {
                "widget_id": self.widget_a.id,
                "compare_type": "widget",
                "compare_widget_id": self.widget_b.id,
                "operator": ">",
                "status": "green",
            }
        )
        data = self.env["od19.dashboard"].get_dashboard_data(self.dashboard.id)
        self.assertEqual(len(data["widgets"]), 3)
        self.assertEqual(
            {widget["id"] for widget in data["widgets"]},
            {self.widget_a.id, self.widget_b.id, self.widget_c.id},
        )
        # Widget A reads Widget B, so B must be rendered (and therefore
        # computed) before A: the emitted order proves the dependency wins.
        self.assertEqual(
            [widget["id"] for widget in data["widgets"]],
            [self.widget_b.id, self.widget_c.id, self.widget_a.id],
        )
        self.assertIn("status_source", data["widgets"][0])
```

- [ ] **Step 2: Run the test to verify it fails**

```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 -u od19_dashboard --test-enable --test-tags /od19_dashboard --stop-after-init --log-level=test
```

Expected: FAIL — `AttributeError: 'od19.dashboard' object has no attribute '_compute_order'`

- [ ] **Step 3: Add the topological sort**

แทรกในคลาส `Od19Dashboard` ต่อจาก `get_dashboard_data`:

```python
    def _compute_order(self):
        """Return the active widgets of this dashboard in dependency order.

        A widget is emitted only once every widget it reads has been emitted,
        so a rule can compare with an already computed value. Sequence (then
        id) breaks ties, which keeps the visual order stable. A cycle cannot be
        solved: it is logged and the remaining widgets are emitted in sequence
        order, which keeps the dashboard usable (fail soft).
        """
        self.ensure_one()
        pending = {widget.id: widget for widget in self.widget_ids.filtered("active")}
        ordered = []
        while pending:
            ready = [
                widget
                for widget in pending.values()
                if all(dependency not in pending for dependency in widget._dependency_ids())
            ]
            if not ready:
                _logger.warning(
                    "Dashboard %s has a circular widget dependency, falling back to sequence order: %s",
                    self.id,
                    sorted(pending),
                )
                ready = list(pending.values())
            for widget in sorted(ready, key=lambda item: (item.sequence, item.id)):
                ordered.append(widget)
                pending.pop(widget.id)
        return ordered
```

- [ ] **Step 4: Compute the widgets in dependency order**

แทนลูปใน `get_dashboard_data` (บรรทัด 197–203) ด้วย:

```python
        widgets = []
        widget_values = {}
        for widget in dashboard._compute_order():
            data = widget._get_widget_data(
                date_range, date_from, date_to, widget_values=widget_values
            )
            widget_values[widget.id] = data.get("value")
            data["config"] = widget._to_config()
            widgets.append(data)
```

และเปลี่ยนลายเซ็น `_get_widget_data` (บรรทัด 452) เป็น:

```python
    def _get_widget_data(self, date_range=None, date_from=None, date_to=None, widget_values=None):
```

โดยยังไม่ใช้ `widget_values` ใน Task นี้ (Task 6 จะส่งต่อเข้า `_fill_kpi_data`) พร้อมเพิ่ม key ชั่วคราวใน dict เริ่มต้น:

```python
            "status_source": "default",
```

- [ ] **Step 5: Run the tests to verify they pass**

```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 -u od19_dashboard --test-enable --test-tags /od19_dashboard --stop-after-init --log-level=test
```

Expected: PASS ทุก test ใน `TestDashboardOrdering`

- [ ] **Step 6: Commit**

```powershell
git add custom_addons/od19_dashboard/models/dashboard.py custom_addons/od19_dashboard/tests/test_dashboard_engine.py
git commit -m "feat(od19_dashboard): compute widgets in cross-widget dependency order"
```

---

### Task 6: Formula evaluation and live preview RPC

**Files:**
- Modify: `custom_addons/od19_dashboard/models/dashboard.py`
- Modify: `custom_addons/od19_dashboard/tests/test_dashboard_engine.py` (เพิ่มคลาส `TestDashboardPreview`)

- [ ] **Step 1: Write the failing test**

ต่อท้าย `custom_addons/od19_dashboard/tests/test_dashboard_engine.py`:

```python
class TestDashboardPreview(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dashboard = cls.env["od19.dashboard"].create({"name": "Preview test dashboard"})
        cls.source = cls.env.ref("od19_dashboard.source_sale_order")
        cls.base_values = {
            "dashboard_id": cls.dashboard.id,
            "name": "Preview widget",
            "widget_type": "kpi",
            "source_id": cls.source.id,
            "measure_key": "amount_total",
            "date_key": "date_order",
            "date_range": "all_time",
        }

    def _preview(self, **overrides):
        values = dict(self.base_values)
        values.update(overrides)
        return self.env["od19.dashboard"].preview_widget(values)

    def test_preview_returns_a_value_and_a_count(self):
        result = self._preview()
        self.assertIn("value", result)
        self.assertIsInstance(result["record_count"], int)
        self.assertEqual(result["status"], "green")
        self.assertEqual(result["status_source"], "default")

    def test_preview_evaluates_a_preset_formula(self):
        result = self._preview(
            formula_mode="preset",
            formula_type="ratio",
            formula_slots='{"a": "amount_total", "b": "__count"}',
        )
        self.assertEqual(result["formula_expression"], "a / b")
        self.assertEqual([item["alias"] for item in result["operands"]], ["a", "b"])

    def test_preview_evaluates_a_literal_weight_slot(self):
        result = self._preview(
            formula_mode="preset",
            formula_type="weighted_average",
            formula_slots='{"a": "amount_total", "b": "amount_untaxed", "w1": 2, "w2": 1}',
        )
        operands = {item["alias"]: item["value"] for item in result["operands"]}
        expected = (operands["a"] * 2 + operands["b"] * 1) / 3
        self.assertAlmostEqual(result["value"], expected)

    def test_preview_applies_the_first_matching_rule(self):
        result = self._preview(
            rule_ids=[
                (0, 0, {
                    "operator": "<",
                    "compare_type": "constant",
                    "compare_value": -1,
                    "status": "red",
                }),
                (0, 0, {
                    "operator": ">=",
                    "compare_type": "constant",
                    "compare_value": -1,
                    "status": "yellow",
                }),
            ],
        )
        self.assertEqual(result["status"], "yellow")
        self.assertEqual(result["status_source"], "rule")

    def test_preview_refuses_a_broken_formula(self):
        with self.assertRaises(ValidationError):
            self._preview(formula_mode="custom", formula_expression="__import__('os').system('dir')")
        with self.assertRaises(ValidationError):
            self._preview(formula_mode="preset", formula_type="ratio", formula_slots='{"a": "amount_total"}')

    def test_preview_writes_nothing(self):
        before = self.env["od19.dashboard.widget"].search_count(
            [("dashboard_id", "=", self.dashboard.id)]
        )
        self._preview()
        after = self.env["od19.dashboard.widget"].search_count(
            [("dashboard_id", "=", self.dashboard.id)]
        )
        self.assertEqual(before, after)

    def test_preview_returns_a_series_preview_for_charts(self):
        result = self._preview(widget_type="bar", groupby_key="state", limit=5)
        self.assertLessEqual(len(result["series_preview"]), 5)

    def test_preview_reads_the_aggregate_of_an_ungrouped_row(self):
        """A KPI reads one row without a group value, so alias 0 maps to row[0]."""
        partner = self.env["res.partner"].create({"name": "Preview customer"})
        self.env["sale.order"].create({"partner_id": partner.id})
        expected = float(self.env["sale.order"].search_count([]))
        self.assertGreater(expected, 0)
        result = self._preview(
            measure_key="__count",
            formula_mode="custom",
            formula_expression="count_records",
        )
        self.assertEqual(result["value"], expected)

    def test_preview_reads_the_aggregate_of_a_grouped_row(self):
        """A chart reads grouped rows: the group value precedes the aggregates."""
        rows = self.env["sale.order"]._read_group([], ["state"], ["__count"])
        self.assertLessEqual(len(rows), 5)
        result = self._preview(
            widget_type="bar",
            groupby_key="state",
            limit=50,
            measure_key="__count",
            formula_mode="custom",
            formula_expression="count_records",
        )
        self.assertEqual(
            sum(item["value"] for item in result["series_preview"]),
            float(sum(count for _state, count in rows)),
        )

    def test_number_text_keeps_a_single_minus_sign(self):
        widget = self.env["od19.dashboard.widget"].new({"name": "Number text"})
        self.assertEqual(widget._number_text(-1234.5, 2), "-1,234.5")
        self.assertEqual(widget._number_text(1234.5, 2), "1,234.5")
        self.assertEqual(widget._number_text(0, 0), "0")
```

- [ ] **Step 2: Run the test to verify it fails**

```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 -u od19_dashboard --test-enable --test-tags /od19_dashboard --stop-after-init --log-level=test
```

Expected: FAIL — `AttributeError: 'od19.dashboard' object has no attribute 'preview_widget'`

- [ ] **Step 3: Add the formula evaluation helpers**

แทรกต่อจาก `_validate_formula_config` ใน `custom_addons/od19_dashboard/models/dashboard.py`:

```python
    # ------------------------------------------------------------------
    # Formula evaluation
    # ------------------------------------------------------------------
    def _shifted_period(self, date_range=None, date_from=None, date_to=None, shift=None):
        """Return the ``(start, end)`` dates of a period, or ``(None, None)``."""
        self.ensure_one()
        start, end, _field_type = self._period_bounds(date_range, date_from, date_to, shift)
        return start, end

    def _run_rate_days(self, date_range=None, date_from=None, date_to=None):
        """Return ``(days_in_period, days_elapsed)``, or ``None`` without a bound."""
        self.ensure_one()
        if not self.date_key:
            return None
        start, end = self._shifted_period(date_range, date_from, date_to)
        if not start or not end:
            return None
        days_in_period = (end - start).days + 1
        elapsed_end = min(end, fields.Date.context_today(self))
        days_elapsed = max((elapsed_end - start).days + 1, 0)
        if days_elapsed <= 0:
            return None
        return days_in_period, days_elapsed

    def _needs_bounded_period(self):
        """Return True when the formula needs a bounded period to be computable."""
        self.ensure_one()
        return bool(
            formula_tools.expression_names(self._effective_expression())
            & {"days_in_period", "days_elapsed"}
        )

    def _uses_share(self):
        """Return True when the expression divides a measure by the total of A."""
        self.ensure_one()
        return "total_a" in formula_tools.expression_names(self._effective_expression())

    def _formula_context(self, row, requests, extra=None):
        """Return the ``safe_eval`` context of one ``_read_group`` row.

        A ``_read_group`` row is flat: the group by values come first, then the
        aggregate of every request. The alias of each request becomes a name of
        the context. A KPI, a delta and a period comparison read a single row
        without any grouping, so their row starts directly with the aggregates:
        the offset is derived from the length of the row instead of assuming a
        group value is always present. Every implicit name is pre-set to
        ``0.0`` so an expression can never raise ``KeyError`` at evaluation.
        """
        self.ensure_one()
        offset = max(len(row) - len(requests), 0)
        context = {}
        for index, (alias, _measure_key, _spec) in enumerate(requests):
            value = row[index + offset] if len(row) > index + offset else 0
            context[alias] = self._to_number(value)
        # A slot bound to a literal weight (``w1`` / ``w2`` of the weighted
        # average) is not an aggregate: its value is the number stored on the
        # widget itself.
        for slot_key, slot_value in self._formula_slot_map().items():
            if not isinstance(slot_value, str):
                context.setdefault(slot_key, self._to_number(slot_value))
        for name in formula_tools.IMPLICIT_NAMES:
            context.setdefault(name, 0.0)
        for widget_id in self._dependency_ids():
            context.setdefault("widget_%s" % widget_id, 0.0)
        context["goal"] = self.goal_value or 0.0
        context.update(extra or {})
        return context

    def _formula_extra(self, model, domain, requests, date_range=None, date_from=None, date_to=None, widget_values=None):
        """Return the context values that are not read from a single aggregate row."""
        self.ensure_one()
        extra = {}
        for widget_id in self._dependency_ids():
            extra["widget_%s" % widget_id] = self._to_number((widget_values or {}).get(widget_id))
        if self._uses_share():
            slot_a = self._formula_slot_map().get("a") or self.measure_key
            spec = self.source_id._aggregate_spec(slot_a) if isinstance(slot_a, str) else False
            if spec:
                rows = model._read_group(domain, [], [spec], limit=1)
                extra["total_a"] = self._to_number(rows[0][0]) if rows and rows[0] else 0.0
        if self._needs_bounded_period():
            days = self._run_rate_days(date_range, date_from, date_to)
            if days:
                extra["days_in_period"] = float(days[0])
                extra["days_elapsed"] = float(days[1])
        return extra

    def _evaluate_value(self, context):
        """Evaluate the effective expression on ``context`` (raises ``UserError``)."""
        self.ensure_one()
        expression = self._effective_expression()
        if not expression:
            raise UserError(_("Type the formula of this widget."))
        if expression == "value":
            return context.get("value", 0.0)
        try:
            return formula_tools.evaluate_expression(expression, context)
        except ZeroDivisionError as error:
            raise UserError(
                _("The formula of widget '%s' divides by zero for this period.") % self.name
            ) from error
        except Exception as error:  # noqa: BLE001 - surfaced as a widget message
            raise UserError(
                _("The formula of widget '%s' could not be evaluated: %s") % (self.name, error)
            ) from error

    def _record_count(self, model, domain):
        """Return the number of records the widget would collect on ``domain``."""
        self.ensure_one()
        rows = model._read_group(domain, [], ["__count"], limit=1)
        return int(rows[0][0] or 0) if rows and rows[0] else 0

    def _operand_details(self, requests, context):
        """Return the ``alias`` → label / value list shown by the builder preview."""
        self.ensure_one()
        labels = {
            field.field_name: field.label or field.field_name
            for field in self.source_id.field_ids
        }
        details = []
        for alias, measure_key, _spec in requests:
            if measure_key == "__count":
                label = _("Number of records")
            else:
                label = labels.get(measure_key, measure_key)
            details.append(
                {"alias": alias, "label": label, "value": context.get(alias, 0.0)}
            )
        used = formula_tools.expression_names(self._effective_expression())
        for name in ("total_a", "days_in_period", "days_elapsed"):
            if name in used:
                details.append(
                    {"alias": name, "label": name, "value": context.get(name, 0.0)}
                )
        return details

    def _number_text(self, value, decimals):
        """Format a number the way the dashboard client does (no padding zeros)."""
        text = ("%%.%df" % decimals) % self._to_number(value)
        sign = "-" if text.startswith("-") else ""
        integer, _dot, decimal = (text[1:] if sign else text).partition(".")
        grouped = "{:,}".format(int(integer or 0))
        return "%s%s%s" % (
            sign,
            grouped,
            (".%s" % decimal.rstrip("0")) if decimal.rstrip("0") else "",
        )

    def _value_text(self, value):
        """Return the value formatted with ``value_format``, mirroring the client."""
        self.ensure_one()
        if value is None:
            return ""
        currency = self.env.company.currency_id
        if self.value_format == "percent":
            return "%s%%" % self._number_text(value, 1)
        if self.value_format == "hours":
            return "%s h" % self._number_text(value, 1)
        if self.value_format == "currency":
            text = self._number_text(value, currency.decimal_places or 2)
            symbol = currency.symbol or ""
            if not symbol:
                return text
            if currency.position == "after":
                return "%s %s" % (text, symbol)
            return "%s %s" % (symbol, text)
        return self._number_text(value, 2)

    def _value_for(self, model, domain, requests, date_range=None, date_from=None, date_to=None, widget_values=None):
        """Evaluate the formula of this widget on an arbitrary domain."""
        self.ensure_one()
        aggregates = [request[2] for request in requests]
        rows = model._read_group(domain, [], aggregates, limit=1)
        extra = self._formula_extra(model, domain, requests, date_range, date_from, date_to, widget_values)
        return self._evaluate_value(self._formula_context(rows[0] if rows else (), requests, extra))

    def _shift_values(self, model, requests, date_range=None, date_from=None, date_to=None, widget_values=None):
        """Return ``{shift: value}`` for the shifts the status rules of this widget need."""
        self.ensure_one()
        values = {}
        for shift in sorted(self._required_shifts()):
            domain = self._build_domain(date_range, date_from, date_to, shift=shift)
            try:
                values[shift] = self._value_for(
                    model, domain, requests, date_range, date_from, date_to, widget_values
                )
            except (UserError, ValidationError) as error:
                # A rule comparing with an unreachable period is skipped, not fatal.
                _logger.info("Shift '%s' of widget %s could not be computed: %s", shift, self.id, error)
                values[shift] = None
        return values

    def _cumulative_series(self, series):
        """Turn a series into its cumulative change (bucket − first bucket)."""
        if not series:
            return series
        base = series[0]["value"]
        return [
            {"label": item["label"], "value": round(item["value"] - base, 4)}
            for item in series
        ]

    def _cumulative_change_value(self, model, domain, requests, date_range=None, date_from=None, date_to=None, widget_values=None):
        """Return the change between the first and the last bucket of the period.

        Used when ``cumulative_change`` is applied to a widget without buckets
        (KPI or list): the period of the widget is bucketed by month on its date
        field, each bucket is evaluated with the formula and the difference
        between the last and the first bucket is returned. ``None`` means the
        widget has no date field, so the formula cannot be computed.
        """
        self.ensure_one()
        if not self.date_key:
            return None
        groupby_spec = "%s:month" % self.date_key
        aggregates = [request[2] for request in requests]
        rows = model._read_group(domain, [groupby_spec], aggregates, order="%s asc" % groupby_spec)
        if len(rows) < 2:
            return 0.0
        extra = self._formula_extra(model, domain, requests, date_range, date_from, date_to, widget_values)
        values = [
            self._evaluate_value(self._formula_context(row, requests, extra))
            for row in rows
        ]
        return values[-1] - values[0]
```

- [ ] **Step 4: Rewrite the data fillers on top of the formula engine**

ใน `custom_addons/od19_dashboard/models/dashboard.py` แทน `_get_widget_data` (บรรทัด 550–610), `_fill_kpi_data` (612–627) และ `_fill_chart_data` (629–668):

```python
    def _get_widget_data(self, date_range=None, date_from=None, date_to=None, widget_values=None):
        self.ensure_one()
        data = {
            "id": self.id,
            "name": self.name,
            "subtitle": self.subtitle or "",
            "widget_type": self.widget_type,
            "value_format": self.value_format,
            "color": self.color or "",
            "goal_value": self.goal_value,
            "delta_basis": self.delta_basis,
            "is_lower_better": self._is_lower_better(),
            "grid_w": self.grid_w,
            "grid_h": self.grid_h,
            "sequence": self.sequence,
            "status": "grey",
            "status_source": "default",
            "value": None,
            "value_text": "",
            "record_count": 0,
            "delta": None,
            "series": [],
            "rows": [],
            "operands": [],
            "formula_expression": self._effective_expression(),
            "message": False,
        }

        source = self.source_id
        if not source or not source.model_name or source.model_name not in self.env:
            data["message"] = _("The data source of this widget is not installed in this database.")
            return data

        model = self.env[source.model_name]
        try:
            model.check_access_rights("read")
        except AccessError:
            data["message"] = _("You do not have read access on %s.") % source.name
            return data

        requests = self._aggregate_requests()
        if not requests:
            data["message"] = _("The measure configured on this widget is not available any more.")
            return data

        try:
            domain = self._build_domain(date_range, date_from, date_to)
        except ValidationError as error:
            data["message"] = str(error)
            return data

        try:
            if self.widget_type == "kpi":
                self._fill_kpi_data(data, model, domain, requests, date_range, date_from, date_to, widget_values)
            elif self.widget_type in ("bar", "line", "pie"):
                self._fill_chart_data(data, model, domain, requests, date_range, date_from, date_to, widget_values)
            else:
                self._fill_list_data(data, model, domain)
        except (AccessError, UserError) as error:
            data["message"] = str(error)
            data["status"] = "grey"
            data["status_source"] = "default"
        except Exception as error:  # noqa: BLE001 - never break the whole dashboard
            _logger.exception("Dashboard widget %s could not be computed", self.id)
            data["message"] = _("This widget could not be computed: %s") % error
            data["status"] = "grey"
            data["status_source"] = "default"
        return data

    def _fill_kpi_data(self, data, model, domain, requests, date_range=None, date_from=None, date_to=None, widget_values=None):
        if self._needs_bounded_period() and not self._run_rate_days(date_range, date_from, date_to):
            data["message"] = _("Choose a date field and a bounded period to compute this formula.")
            return

        aggregates = [request[2] for request in requests]
        rows = model._read_group(domain, [], aggregates, limit=1)
        extra = self._formula_extra(model, domain, requests, date_range, date_from, date_to, widget_values)
        context = self._formula_context(rows[0] if rows else (), requests, extra)
        value = self._evaluate_value(context)
        if self.formula_mode == "preset" and self.formula_type == "cumulative_change":
            value = self._cumulative_change_value(
                model, domain, requests, date_range, date_from, date_to, widget_values
            )
        if value is None:
            data["message"] = _("Choose a date field and a bounded period to compute this formula.")
            return

        data["value"] = value
        data["value_text"] = self._value_text(value)
        data["record_count"] = self._record_count(model, domain)
        data["operands"] = self._operand_details(requests, context)

        rule_context = {
            "value": value,
            "goal": self.goal_value or 0.0,
            "widget_values": widget_values or {},
            "shifts": self._shift_values(model, requests, date_range, date_from, date_to, widget_values),
        }
        data["status"], data["status_source"] = self._evaluate_rules(rule_context)

        if self.show_delta:
            self._fill_delta(data, model, requests, value, date_range, date_from, date_to, widget_values)

    def _fill_delta(self, data, model, requests, value, date_range=None, date_from=None, date_to=None, widget_values=None):
        """Fill the KPI delta against the basis period chosen by the designer."""
        self.ensure_one()
        previous_domain = self._build_domain(date_range, date_from, date_to, shift=self.delta_basis)
        try:
            previous_value = self._value_for(
                model, previous_domain, requests, date_range, date_from, date_to, widget_values
            )
        except (UserError, ValidationError) as error:
            _logger.info("Delta of widget %s could not be computed: %s", self.id, error)
            return
        if previous_value is None:
            return
        if previous_value:
            data["delta"] = round((value - previous_value) / previous_value * 100, 1)
        elif value:
            data["delta"] = 100.0
        else:
            data["delta"] = 0.0

    def _fill_chart_data(self, data, model, domain, requests, date_range=None, date_from=None, date_to=None, widget_values=None):
        groupby_spec = self._groupby_spec()
        if not groupby_spec:
            data["message"] = _("Choose a group by field for this chart.")
            return
        if self._needs_bounded_period() and not self._run_rate_days(date_range, date_from, date_to):
            data["message"] = _("Choose a date field and a bounded period to compute this formula.")
            return

        aggregates = [request[2] for request in requests]
        limit = self.limit if self.limit > 0 else None
        if self.widget_type == "line":
            # A line chart is a trend: take the most recent buckets, then
            # present them in chronological order.
            rows = model._read_group(
                domain,
                [groupby_spec],
                aggregates,
                order="%s desc" % groupby_spec,
                limit=limit,
            )
        else:
            rows = model._read_group(
                domain,
                [groupby_spec],
                aggregates,
                order="%s desc" % aggregates[0],
                limit=limit,
            )

        extra = self._formula_extra(model, domain, requests, date_range, date_from, date_to, widget_values)
        if self._uses_share():
            # In a chart the share of a bucket is measured against the total of
            # every displayed bucket, not against the whole domain.
            extra["total_a"] = sum(
                self._formula_context(row, requests).get("a", 0.0) for row in rows
            )

        series = []
        for row in rows:
            context = self._formula_context(row, requests, extra)
            series.append(
                {"label": self._group_label(row[0]), "value": self._evaluate_value(context)}
            )
        if self.widget_type == "line":
            series.reverse()
        if self.formula_mode == "preset" and self.formula_type == "cumulative_change":
            series = self._cumulative_series(series)

        data["series"] = series
        data["status"] = "green" if series else "grey"
        if series:
            data["value"] = series[-1]["value"]
            data["value_text"] = self._value_text(data["value"])
        else:
            data["message"] = _("No data for the selected period.")
```

> หมายเหตุ: `_fill_list_data` ไม่แก้ใน task นี้ — รายการยังอ่าน measure เดิม (สูตรของ list widget จะเปิดในเฟส 2)

- [ ] **Step 5: Add the preview RPC**

แทรกต่อจาก `_compute_order` (คือก่อน `save_layout`) ใน `custom_addons/od19_dashboard/models/dashboard.py`:

```python
    @api.model
    def _normalise_preview_values(self, values):
        """Return builder values usable to build an in-memory widget record.

        ``id`` is dropped (it would bind the new record to a stored one) and
        ``rule_ids`` is rewritten as create commands so a draft always carries
        brand new rules, whether the builder sent an existing rule, a modified
        rule or a deleted one.
        """
        cleaned = dict(values or {})
        cleaned.pop("id", None)
        commands = []
        for rule in cleaned.get("rule_ids") or []:
            if isinstance(rule, (list, tuple)):
                code = rule[0] if rule else 0
                if code in (2, 3, 6):  # delete / unlink / clear
                    continue
                data = dict(rule[2] or {}) if len(rule) > 2 else {}
            else:
                data = dict(rule)
            data.pop("id", None)
            data.pop("widget_id", None)
            commands.append((0, 0, data))
        cleaned["rule_ids"] = commands
        return cleaned

    @api.model
    def preview_widget(self, values, date_range=None):
        """Evaluate a draft widget configuration without writing to the database.

        The builder calls this on every change so the designer immediately sees
        the value, the number of records the widget would collect, the status
        resulting from the rule list, and the operands actually used. The draft
        lives in a new (in-memory) record: nothing is stored.
        """
        cleaned = self._normalise_preview_values(values)
        draft = self.env["od19.dashboard.widget"].new(cleaned)
        draft._validate_formula_config()

        dashboard = draft.dashboard_id
        if dashboard:
            dashboard.check_access_rights("read")

        effective_range = date_range or cleaned.get("date_range")
        widget_values = {}
        for widget in dashboard.widget_ids.filtered("active"):
            other = widget._get_widget_data(
                date_range=effective_range, widget_values=widget_values
            )
            widget_values[widget.id] = other.get("value")

        data = draft._get_widget_data(date_range=effective_range, widget_values=widget_values)
        return {
            "value": data.get("value"),
            "value_text": data.get("value_text") or "",
            "record_count": data.get("record_count") or 0,
            "status": data.get("status"),
            "status_source": data.get("status_source") or "default",
            "operands": data.get("operands") or [],
            "series_preview": (data.get("series") or [])[:5],
            "formula_expression": draft._effective_expression(),
            "message": data.get("message") or "",
        }
```

> หมายเหตุ: การตรวจสิทธิ์ preview ใช้ read access ของ dashboard ปลายทาง (ไม่ใช่ `_check_edit_access()`) เพราะ preview ไม่เขียนข้อมูล ส่วนการเขียนจริงยังถูกตรวจด้วย `_check_edit_access()` ใน `create_widget` / `update_widget` ตามเดิม

- [ ] **Step 6: Run the tests to verify they pass**

```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 -u od19_dashboard --test-enable --test-tags /od19_dashboard --stop-after-init --log-level=test
```

Expected: PASS ทุกคลาส รวม `TestDashboardPreview`

- [ ] **Step 7: Commit**

```powershell
git add custom_addons/od19_dashboard/models/dashboard.py custom_addons/od19_dashboard/tests/test_dashboard_engine.py
git commit -m "feat(od19_dashboard): evaluate widget formulas and expose the live preview RPC"
```

---

### Task 7: Retire the legacy thresholds and publish the new builder catalogues

**Files:**
- Modify: `custom_addons/od19_dashboard/models/dashboard.py`
- Modify: `custom_addons/od19_dashboard/models/dashboard_rule.py`
- Modify: `custom_addons/od19_dashboard/tests/test_dashboard_rules.py`
- Modify: `custom_addons/od19_dashboard/tests/test_dashboard_engine.py` — **เพิ่มเข้ามาระหว่างทำ Task 7** คอนสเตรนต์ `_check_formula_config` ที่เพิ่มใน Step 6a ยิงทุก `write()` ทำให้เทสต์เดิม 17 ตัวที่เซตฟิลด์สูตรทีละฟิลด์ล้ม ต้องแปลงเป็นการเรียก `write({...})` ครั้งเดียว และย้าย 2 เทสต์ที่ต้องใช้สถานะยังไม่ valid ไปสร้างเรกคอร์ดด้วย `Model.new()`

> **ขอบเขตที่ *ไม่* รวมใน Task นี้ (โดยเจตนา):**
>
> - `data/dashboard_data.xml` ยังคงมี `threshold_mode` / `warning_value` / `critical_value` ต่อไปจนถึง **Task 10** ไฟล์นี้ถูกประกาศด้วย `noupdate="1"` การอัปเดตโมดูลบนฐานข้อมูลเดิม (mode `update`) จะข้าม record ที่มีอยู่แล้ว **ก่อน** อ่านฟิลด์ (ดู [convert.py](file:///c:/odoo-dev/odoo19/odoo/tools/convert.py#L360-L380)) จึงไม่ล้ม — ผลข้างเคียงคือ **การติดตั้งใหม่ (mode `init`) จะล้มจนกว่า Task 10 จะแก้ seed** ซึ่งเป็นงานของ Task 10 ตามที่ระบุไว้ที่นั่น
> - `static/src/dashboard/builder_dialog.js` / `builder_dialog.xml` / `dashboard_action.js` ที่ยังอ้าง `threshold_mode` เป็นของ **Task 8** (การลบฟิลด์ใน Task นี้ทำให้ `widget.threshold_mode` กลายเป็น `undefined` ฝั่ง JS ชั่วคราว)
> - เทสต์ `test_dependency_ids_never_contains_the_widget_itself` ต้อง**บังคับ** ค่าตัวเองเข้าไปในหน่วยความจำ (patch `_effective_expression`) เพราะทั้งสองเส้นทางที่ผู้ใช้ทำได้จริงถูกกันไว้แล้ว — `_check_formula_config` ตัด id ของ widget ตัวเองออกจาก allowed names และ `_check_compare_widget` ห้ามกฎเทียบ widget กับตัวเอง — การสร้างด้วย `Model.new()` แบบเดิมทำให้เทสต์ผ่านตลอดกาลโดยไม่แตะบรรทัด `ids.discard(self.id)` เลย
>
> **การรันเทสต์ของ Task นี้** (ใช้กับ Step 2 และ Step 7) — พอร์ต 8070 ถูกเซิร์ฟเวอร์พื้นหลังยึดอยู่ และ `odoo.conf` เขียน log ลงไฟล์ ทำให้ stdout ว่าง ต้องระบุสองแฟลกเพิ่ม:
>
> ```powershell
> venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 -u od19_dashboard --test-enable --test-tags /od19_dashboard --stop-after-init --log-level=test --http-port=8099 --logfile=$env:TEMP\od19_dashboard_task7.log
> ```
>
> อ่านผลจากบรรทัด `odoo.tests.result: N failed, M error(s) of K tests` ใน `$env:TEMP\od19_dashboard_task7.log`

**บริบท:** หลัง Task 6 การตัดสินสถานะย้ายมาอยู่ที่ `_evaluate_rules()` ทั้งหมดแล้ว จึงถอด threshold เดิมออกทั้งชุด — ค่าคงที่ `THRESHOLD_MODES`, ฟิลด์ 3 ตัวบน widget, validation ใน `_check_source_fields()` และเมธอด `_compute_status()` — แล้วให้ builder รับแค็ตตาล็อกใหม่ (โหมดสูตร, ประเภทสูตร, ประเภทการเทียบ, ตัวดำเนินการ, สถานะ) ผ่าน `get_builder_meta()` แทน `threshold_modes`

**การตรวจสูตรผูกเป็น `@api.constrains` ไม่ใช่เรียกมือใน `create_widget()` / `update_widget()`** เพราะ `od19.dashboard.widget` ถูกเขียนผ่าน `create()` / `write()` ได้หลายทาง (builder RPC, form view, seed data) — constrains จะจับทุกทางที่เขียน (Odoo 19 รัน `_validate_fields()` แบบ sudo ให้) ส่วน `preview_widget()` ยังเรียก `_validate_formula_config()` เอง เพราะ record ที่สร้างด้วย `Model.new()` ไม่ผ่าน constrains

> `dashboard.py` import `COMPARE_TYPES` และ `OPERATORS` จาก `dashboard_rule` ได้โดยตรง เพราะทิศทาง import เป็นเส้นเดียว `dashboard` → `dashboard_rule` → `dashboard_formula` — `dashboard_rule.py` ไม่ได้ import `dashboard.py` กลับ จึงไม่มี cycle

- [ ] **Step 1: Write the failing test**

ต่อท้ายไฟล์ `custom_addons/od19_dashboard/tests/test_dashboard_rules.py` (หลังคลาส `TestDashboardRules`):

```python
class TestDashboardBuilderMeta(TransactionCase):
    """The builder reads the formula catalogues; the legacy thresholds are gone."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dashboard = cls.env["od19.dashboard"].create({"name": "Meta test dashboard"})
        cls.source = cls.env.ref("od19_dashboard.source_sale_order")
        cls.widget_model = cls.env["od19.dashboard.widget"]

    def _base_values(self, **overrides):
        values = {
            "dashboard_id": self.dashboard.id,
            "name": "Meta widget",
            "widget_type": "kpi",
            "source_id": self.source.id,
            "measure_key": "amount_total",
        }
        values.update(overrides)
        return values

    def test_widget_no_longer_carries_the_threshold_fields(self):
        for name in ("threshold_mode", "warning_value", "critical_value"):
            self.assertNotIn(name, self.widget_model._fields)

    def test_builder_meta_publishes_the_formula_modes(self):
        meta = self.env["od19.dashboard"].get_builder_meta()
        self.assertNotIn("threshold_modes", meta)
        self.assertEqual(
            [item["key"] for item in meta["formula_modes"]],
            ["measure", "preset", "custom"],
        )
        formula_types = {item["key"]: item for item in meta["formula_types"]}
        self.assertIn("ratio", formula_types)
        # The builder draws the slot table from the catalogue, so every preset
        # must ship its slots, its variadic flag and its expression.
        self.assertEqual(formula_types["ratio"]["slots"], ["a", "b"])
        self.assertEqual(
            formula_types["weighted_average"]["slots"], ["a", "b", "w1", "w2"]
        )
        self.assertEqual(formula_types["ratio"]["expression"], "a / b")
        self.assertFalse(formula_types["ratio"]["variadic"])
        self.assertTrue(formula_types["sum"]["variadic"])
        self.assertTrue(formula_types["average"]["variadic"])
        for item in meta["formula_types"]:
            self.assertTrue(
                item["slots"], "Preset '%s' must declare its slots." % item["key"]
            )

    def test_builder_meta_publishes_the_rule_catalogues(self):
        meta = self.env["od19.dashboard"].get_builder_meta()
        self.assertEqual(
            [item["key"] for item in meta["operators"]],
            [">", ">=", "<", "<=", "==", "!="],
        )
        compare_keys = [item["key"] for item in meta["compare_types"]]
        for key in ("constant", "goal", "percent_of_goal", "widget", "prev", "yty", "mtm", "qtq"):
            self.assertIn(key, compare_keys)
        self.assertEqual(
            [item["key"] for item in meta["statuses"]],
            ["red", "yellow", "green", "grey"],
        )
        self.assertEqual(
            [item["key"] for item in meta["period_bases"]],
            ["previous", "yty", "mtm", "qtq"],
        )

    def test_to_config_serialises_the_formula_and_the_rules(self):
        widget = self.widget_model.create(
            self._base_values(
                formula_mode="preset",
                formula_type="ratio",
                formula_slots='{"a": "amount_total", "b": "__count"}',
                rule_ids=[
                    (0, 0, {"operator": "<", "compare_type": "constant", "compare_value": 10, "status": "red"}),
                    (0, 0, {"operator": ">=", "compare_type": "yty", "status": "green"}),
                ],
            )
        )
        config = widget._to_config()
        for key in (
            "formula_mode",
            "formula_type",
            "formula_slots",
            "formula_expression",
            "formula_basis",
            "delta_basis",
            "default_status",
            "rule_ids",
        ):
            self.assertIn(key, config)
        for name in ("threshold_mode", "warning_value", "critical_value"):
            self.assertNotIn(name, config)
        self.assertEqual(config["formula_expression"], "a / b")
        self.assertEqual(len(config["rule_ids"]), 2)
        self.assertEqual(config["rule_ids"][0]["status"], "red")
        self.assertTrue(config["rule_ids"][0]["id"], "Existing rules keep their id for the builder.")

    def test_creating_a_widget_with_a_broken_formula_is_refused(self):
        with self.assertRaises(ValidationError):
            self.widget_model.create(
                self._base_values(
                    formula_mode="custom",
                    formula_expression="__import__('os').system('dir')",
                )
            )
        with self.assertRaises(ValidationError):
            self.widget_model.create(
                self._base_values(
                    formula_mode="preset",
                    formula_type="ratio",
                    formula_slots='{"a": "amount_total"}',
                )
            )

    def test_updating_a_widget_with_a_broken_formula_is_refused(self):
        widget = self.widget_model.create(self._base_values())
        with self.assertRaises(ValidationError):
            widget.write({"formula_mode": "custom", "formula_expression": "unknown_measure + 1"})

    def test_a_single_measure_widget_is_still_accepted(self):
        widget = self.widget_model.create(self._base_values())
        self.assertEqual(widget.formula_mode, "measure")
        self.assertEqual(widget.default_status, "green")
```

ตรวจว่าไฟล์ import `ValidationError` แล้ว — ถ้ายัง ให้เพิ่มบรรทัด

```python
from odoo.exceptions import ValidationError
```

- [ ] **Step 2: Run the test to verify it fails**

```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 -u od19_dashboard --test-enable --test-tags /od19_dashboard --stop-after-init --log-level=test
```

Expected: FAIL — `test_widget_no_longer_carries_the_threshold_fields` ล้มเพราะฟิลด์ยังอยู่, `test_builder_meta_publishes_the_formula_modes` ล้มเพราะยังไม่มี `formula_modes`, `test_to_config_serialises_the_formula_and_the_rules` ล้มเพราะยังไม่มี `formula_mode` ใน config, และเทสต์ broken-formula ยังไม่ raise (ยังไม่มี constrains)

- [ ] **Step 3: Delete the legacy threshold constant, fields and validation**

**3a.** ใน `custom_addons/od19_dashboard/models/dashboard.py` ลบบล็อกบรรทัด 29–33:

```python
THRESHOLD_MODES = [
    ("none", "No threshold"),
    ("higher_is_better", "Higher is better"),
    ("lower_is_better", "Lower is better"),
]
```

**3b.** ลบฟิลด์ 3 ตัวบน `Od19DashboardWidget` (บรรทัด 502–504) ให้เหลือ:

```python
    goal_value = fields.Float()
    show_delta = fields.Boolean(default=True, string="Show Period Comparison")
```

**3c.** ลบบล็อก threshold validation 2 ท่อนท้าย `_check_source_fields()` (บรรทัด 585–592):

```python
            if widget.threshold_mode == "higher_is_better" and widget.critical_value > widget.warning_value:
                raise ValidationError(
                    _("For 'higher is better' the critical value must be lower than the warning value.")
                )
            if widget.threshold_mode == "lower_is_better" and widget.critical_value < widget.warning_value:
                raise ValidationError(
                    _("For 'lower is better' the critical value must be higher than the warning value.")
                )
```

ให้เมธอดจบที่การตรวจ `date_key` (บรรทัด 580–584) แล้วปิด loop

**3d.** ลบเมธอด `_compute_status()` ทั้งบล็อก (บรรทัด 1450–1464):

```python
    def _compute_status(self, value):
        self.ensure_one()
        if value is None or self.threshold_mode == "none":
            return "green" if value is not None else "grey"
        if self.threshold_mode == "higher_is_better":
            if value <= self.critical_value:
                return "red"
            if value <= self.warning_value:
                return "yellow"
            return "green"
        if value >= self.critical_value:
            return "red"
        if value >= self.warning_value:
            return "yellow"
        return "green"
```

> หลัง Task 6 ไม่มีใครเรียก `_compute_status()` แล้ว (`_fill_kpi_data` ใช้ `_evaluate_rules()` และกราฟ/ลิสต์ตั้งสถานะเองจากจำนวนข้อมูล) — ยืนยันด้วยการ grep `_compute_status` ว่าเหลือศูนย์ผลลัพธ์ก่อนลบ

- [ ] **Step 4: Serialise the formula and the rules**

**4a.** ใน `custom_addons/od19_dashboard/models/dashboard_rule.py` เพิ่มเมธอดนี้ในคลาส `Od19DashboardWidgetRule` (ต่อจาก constrains):

```python
    def _to_values(self):
        """Return the rule as a plain dictionary for the builder and the tests."""
        self.ensure_one()
        return {
            "id": self.id,
            "name": self.name or "",
            "sequence": self.sequence,
            "active": self.active,
            "operator": self.operator,
            "compare_type": self.compare_type,
            "compare_value": self.compare_value,
            "compare_percent": self.compare_percent,
            "compare_widget_id": self.compare_widget_id.id,
            "status": self.status,
        }
```

**4b.** ใน `dashboard.py` แทนบล็อกบรรทัด 629–633 ของ `_to_config()`:

```python
            "goal_value": self.goal_value,
            "threshold_mode": self.threshold_mode,
            "warning_value": self.warning_value,
            "critical_value": self.critical_value,
            "show_delta": self.show_delta,
```

ด้วย:

```python
            "goal_value": self.goal_value,
            "show_delta": self.show_delta,
            "formula_mode": self.formula_mode,
            "formula_type": self.formula_type or "",
            "formula_slots": self.formula_slots or "{}",
            "formula_expression": self.formula_expression or "",
            "formula_basis": self.formula_basis,
            "delta_basis": self.delta_basis,
            "default_status": self.default_status,
            "rule_ids": [rule._to_values() for rule in self.rule_ids],
```

> `rule_ids` ส่ง `id` ไปด้วย เพื่อให้ builder ส่ง `[1, id, {...}]` สำหรับกฎเดิมและ `[2, id]` สำหรับกฎที่ถูกลบ — การเขียน One2many ที่มีแต่ `(0, 0, ...)` จะ *เพิ่ม* กฎใหม่โดยไม่ลบของเดิม

- [ ] **Step 5: Publish the new catalogues in `get_builder_meta()`**

**5a.** แก้ import ของ `dashboard.py` (บล็อกที่ **Task 1 Step 5** วางไว้) ให้เพิ่มบรรทัด:

```python
from .dashboard_rule import COMPARE_TYPES, OPERATORS
```

**5b.** แทนบรรทัด 200 ของ `get_builder_meta()`:

```python
            "threshold_modes": [{"key": key, "label": label} for key, label in THRESHOLD_MODES],
```

ด้วย:

```python
            "formula_modes": [{"key": key, "label": label} for key, label in FORMULA_MODES],
            "formula_types": [
                {
                    "key": key,
                    "label": label,
                    "slots": list(formula_tools.PRESET_REQUIRED_SLOTS.get(key, ())),
                    "variadic": key in VARIADIC_FORMULA_TYPES,
                    "expression": formula_tools.PRESET_EXPRESSIONS.get(key, ""),
                }
                for key, label in formula_tools.FORMULA_TYPES
            ],
            "compare_types": [{"key": key, "label": label} for key, label in COMPARE_TYPES],
            "operators": [{"key": key, "label": label} for key, label in OPERATORS],
            "statuses": [{"key": key, "label": label} for key, label in STATUS_SELECTION],
            "period_bases": [{"key": key, "label": label} for key, label in FORMULA_BASIS],
```

> `FORMULA_MODES` และ `STATUS_SELECTION` ประกาศไว้ที่หัวไฟล์ `dashboard.py` แล้วใน Task 1 Step 5 ส่วน `formula_tools.FORMULA_TYPES` มาจาก `dashboard_formula.py` (Task 2)
>
> แต่ละรายการของ `formula_types` ส่ง `slots` (สล็อตที่สูตรนั้นต้องใช้ เรียงตามลำดับที่แสดงในตาราง), `variadic` (`True` สำหรับ `sum` / `average` — เติมสล็อต c–e ได้เอง) และ `expression` (สูตรที่ระบบจะสร้างให้ แสดงเป็นตัวอย่างในไดอะล็อก) เพื่อให้ builder ไม่ต้องคัดลอกรายการสล็อตซ้ำไว้ฝั่ง JS — ถ้า `dashboard_formula.py` เพิ่มสูตรใหม่ builder จะเห็นทันทีโดยไม่ต้องแก้ front-end
>
> **5c.** เพิ่มค่าคงที่ต่อจาก `FORMULA_MODES` (ปัจจุบันจบที่บรรทัด 59) ที่หัวไฟล์ `dashboard.py`:
>
> ```python
> #: Preset formulas whose slot list is filled by the designer (a, b, c, d, e).
> VARIADIC_FORMULA_TYPES = ("sum", "average")
> ```

- [ ] **Step 6: Make the formula validation automatic on create and write**

**6a.** ใน `dashboard.py` เพิ่ม constrains ต่อจาก `_check_domain()` (จบที่บรรทัด 608):

```python
    @api.constrains(
        "formula_mode",
        "formula_type",
        "formula_slots",
        "formula_expression",
        "formula_basis",
        "delta_basis",
        "source_id",
        "measure_key",
        "rule_ids",
    )
    def _check_formula_config(self):
        self._validate_formula_config()
```

**6b.** ปรับ docstring ของ `_validate_formula_config()` ให้ตรงความจริง — แทนย่อหน้าคำอธิบายเดิมด้วย:

```python
        """Validate the whole formula configuration and raise ``ValidationError``.

        Called automatically by the ``_check_formula_config`` constraint on
        every create / write of a widget, and explicitly by ``preview_widget``
        because a record built with ``Model.new()`` never triggers a constraint.
        """
```

- [ ] **Step 7a: Snapshot the database before the module update**

> ⚠️ **ต้องทำก่อน Step 7** — การอัปเดตโมดูลจะลบคอลัมน์ `threshold_mode` / `warning_value` / `critical_value` ทิ้งทันที (Odoo ลบคอลัมน์ของฟิลด์ที่ถูกถอดออกจากโมเดล) ถ้าสคริปต์ migration ยังไม่มี (Task 9) และ `version` ยังไม่ถูก bump (Task 10) ข้อมูล threshold เดิมจะหายถาวร และ `pre-migrate` จะไม่มีอะไรให้คัดลอกในภายหลัง

```powershell
$env:PGPASSWORD = "<your-db-password>"
createdb -h localhost -p 5432 -U odoo -T odoo19 odoo19_dashboard_baseline
```

สำเนา `odoo19_dashboard_baseline` นี้ **ห้ามอัปเดตโมดูล** จนกว่าจะถึง Task 10 — จะถูกใช้เป็นคู่ทดสอบว่า migration ทำงานจริงบนฐานข้อมูลที่ยังมี threshold เดิม

- [ ] **Step 7: Run the tests to verify they pass**

```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 -u od19_dashboard --test-enable --test-tags /od19_dashboard --stop-after-init --log-level=test
```

Expected: PASS ทุกคลาส รวม `TestDashboardBuilderMeta` — และ log ต้องไม่มี warning เรื่องฟิลด์ที่ถูกลบ

> ถ้า log ขึ้น `WARNING ... unable to set the null value` หรือข้อความเกี่ยวกับคอลัมน์ `threshold_mode` ให้ตรวจว่า Task 9 (migration) จะเป็นตัวจัดการข้อมูลเก่า ไม่ใช่ Task 7 — การลบฟิลด์ใน Odoo ลบคอลัมน์ตอน update แต่ Task 10 (seed) และ Task 9 (migration) เป็นผู้รับผิดชอบข้อมูลในฐานข้อมูลเดิม

- [ ] **Step 8: Commit**

```powershell
git add custom_addons/od19_dashboard/models/dashboard.py custom_addons/od19_dashboard/models/dashboard_rule.py custom_addons/od19_dashboard/tests/test_dashboard_rules.py
git commit -m "refactor(od19_dashboard): retire the per-widget thresholds for formula driven rules"
```

---


### Task 8: Rebuild the widget designer around formulas and status rules

**Goal:** ให้ดีไซเนอร์เลือกโหมดสูตร (measure / preset / custom), กรอกค่าสล็อต, กำหนดกฎสถานะเป็นตารางที่เลื่อนลำดับได้ และเห็น **ผลลัพธ์ + จำนวน record ที่จะเก็บได้** ก่อนกดบันทึก โดยไม่ต้องแก้โค้ด

**Files:**
- Modify: `custom_addons/od19_dashboard/static/src/dashboard/builder_dialog.js`
- Modify: `custom_addons/od19_dashboard/static/src/dashboard/builder_dialog.xml`
- Modify: `custom_addons/od19_dashboard/static/src/dashboard/dashboard_action.js`
- Modify: `custom_addons/od19_dashboard/static/src/dashboard/dashboard_action.xml`
- Modify: `custom_addons/od19_dashboard/static/src/dashboard/dashboard_action.scss`

**Precondition:** Task 7 เสร็จแล้ว — `get_builder_meta()` ส่ง `formula_modes`, `formula_types` (มี `slots` / `variadic` / `expression`), `compare_types`, `operators`, `statuses`, `period_bases` และ Task 6 เสร็จแล้ว — `preview_widget(values, date_range=None)` พร้อมใช้

**Design Decisions ของ task นี้:**

> **1. ไม่เพิ่ม `widget_options` ลงใน `get_builder_meta()`** — สเปก §8.3 ระบุให้ meta ส่งรายชื่อ widget ของแดชบอร์ดปัจจุบันเพื่อทำ cross-reference แต่ `get_builder_meta()` เป็น `@api.model` ที่ไม่มีพารามิเตอร์และถูกเรียกครั้งเดียวตอนเปิดหน้า การเพิ่มพารามิเตอร์จะทำให้ต้องเรียกซ้ำทุกครั้งที่สลับแดชบอร์ดและเพิ่ม round trip โดยไม่จำเป็น ทางเลือกที่ใช้คือ **ส่ง `state.widgets` เป็น props ให้ `BuilderDialog`** จาก `dashboard_action.js` ซึ่งมีข้อมูลนี้อยู่แล้ว ผลที่ผู้ใช้ได้รับเหมือนกันทุกประการ (เลือก widget อื่นในแดชบอร์ดเดียวกันเป็นคู่เทียบได้) โดยไม่ต้องแก้ RPC

> **2. การลบกฎต้องส่งคำสั่ง `[2, id]`** — การเขียน One2many ด้วย `[1, id, {...}]` และ `[0, 0, {...}]` เท่านั้น **ไม่ลบ** กฎที่หายไปจากลิสต์ (ดูหมายเหตุ Task 7 Step 4b) ดังนั้น builder เก็บ id ของกฎที่ถูกลบไว้ใน `state.removedRuleIds` แล้วต่อท้ายคำสั่ง `[2, id]` ตอนสร้าง payload

> **3. `_boundSlots()` ตัดสล็อตว่างออก** — ระหว่างแก้ไข ตารางสล็อตต้องเก็บคีย์ที่ยังว่างไว้เพื่อให้แถวยังแสดงอยู่ แต่ payload ที่ส่งเซิร์ฟเวอร์ต้องมีเฉพาะสล็อตที่ผูกค่าแล้ว มิฉะนั้น `_validate_formula_config()` จะไม่เห็นสล็อตบังคับแล้วรายงานว่า "needs the slot(s): b"

> **4. `dashboard_id` ส่งเฉพาะตอน preview ไม่ส่งตอนบันทึก** — `preview_widget()` ต้องรู้แดชบอร์ดปลายทางเพื่อคำนวณค่าของ widget อื่นที่จะถูกอ้างอิง แต่ `update_widget()` เขียนค่าทุกคีย์ที่ได้รับลงระเบียนจริง การส่ง `dashboard_id` ตอนบันทึกจึงเท่ากับย้าย widget — `_previewValues()` เติมคีย์นี้ ส่วน `_buildValues()` ไม่มีคีย์นี้

> **5. `config.formula_expression` คือ *effective expression* ไม่ใช่ค่าฟิลด์ดิบ** — Task 7 Step 4b ให้ `_to_config()` ส่ง `self._effective_expression()` ภายใต้คีย์นี้ (และ `_get_widget_data()` ก็ส่งค่าเดียวกันมานานแล้ว) ผลคือ widget โหมด measure จะได้ค่า sentinel ภายในคือ `"value"` (alias ที่ `_aggregate_requests()` ใช้ตอนโหมด measure) **ไม่ใช่** นิพจน์ที่ผู้ใช้พิมพ์ ดังนั้น `openEditWidget()` ต้องดู `formula_mode` ก่อนใช้ค่านี้: ถ้าไม่ใช่ `custom` ให้ตั้ง textarea เป็น `""` และ `onFormulaModeChange()` ต้องรีเซ็ต `formula_expression` เป็น `""` เมื่อสลับออก/เข้าโหมด custom มิฉะนั้นผู้ใช้ที่สลับจาก measure ไป custom จะเห็นคำว่า `value` ค้างในช่อง และโดนปฏิเสธด้วย "The formula uses names without value: value."

---

- [ ] **Step 1: Extend the draft state, the constants and the catalogue getters**

ใน `custom_addons/od19_dashboard/static/src/dashboard/builder_dialog.js` แทนส่วนหัวไฟล์ (บรรทัด 1–53) ด้วย:

```js
/** @odoo-module **/

import { Component, onWillDestroy, onWillStart, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

/**
 * Default configuration of a brand new widget. The keys mirror
 * ``od19.dashboard.widget._to_config`` so the very same dictionary can be sent
 * back to ``create_widget`` / ``update_widget``.
 */
const DEFAULT_CONFIG = {
    name: "",
    subtitle: "",
    widget_type: "kpi",
    value_format: "number",
    color: "",
    source_id: null,
    measure_key: "__count",
    groupby_key: "",
    date_key: "",
    date_range: "last_30_days",
    domain: "[]",
    limit: 10,
    goal_value: 0,
    show_delta: true,
    formula_mode: "measure",
    formula_type: null,
    formula_slots: "{}",
    formula_expression: "",
    formula_basis: "previous",
    delta_basis: "previous",
    default_status: "green",
    rule_ids: [],
    grid_w: 4,
    grid_h: 2,
};

const CHART_TYPES = ["bar", "line", "pie"];

//: Measure slots the designer may bind, in the order they are offered.
const SLOT_KEYS = ["a", "b", "c", "d", "e"];
const WEIGHT_KEYS = ["w1", "w2"];

//: Names a custom expression may always use, on top of the source measures.
const IMPLICIT_NAMES = [
    "goal",
    "total_a",
    "days_in_period",
    "days_elapsed",
    "count_records",
];

//: How long the dialog waits before asking the server for a preview.
const PREVIEW_DEBOUNCE = 600;

/**
 * Web based widget designer. It is opened by the dashboard action either empty
 * (create) or pre-filled with an existing widget configuration (edit).
 *
 * Since the formula engine landed, the designer also chooses how the value is
 * computed (single measure, preset formula or custom expression) and how the
 * colour is decided (an ordered table of status rules). A debounced preview
 * shows the resulting value and the number of records the widget would collect.
 */
export class BuilderDialog extends Component {
    static template = "od19_dashboard.BuilderDialog";
    static props = {
        meta: Object,
        config: { optional: true },
        widgets: { optional: true },
        dashboardId: { optional: true },
        onSave: Function,
        onClose: Function,
    };

    setup() {
        this.orm = useService("orm");
        this._ruleKey = 0;
        this._previewTimer = null;

        const config = this.props.config || {};
        this.state = useState({
            draft: {
                ...DEFAULT_CONFIG,
                ...config,
                rule_ids: this._prepareRules(config.rule_ids || []),
            },
            error: "",
            preview: { loading: false, data: null, error: "" },
            // Ids of the stored rules the designer removed: they are sent back
            // as ``[2, id]`` commands, otherwise Odoo would keep them.
            removedRuleIds: [],
            dragRuleIndex: null,
        });

        onWillStart(() => this._refreshPreview());
        onWillDestroy(() => this._clearPreviewTimer());
    }

    _nextRuleKey() {
        this._ruleKey += 1;
        return `new-${this._ruleKey}`;
    }

    _prepareRules(rules) {
        // ``_key`` is client side only: it keeps OWL stable while the rows are
        // reordered. ``_ruleCommands`` rebuilds every dictionary from scratch,
        // so the key never reaches the server.
        return rules.map((rule) => ({
            ...rule,
            _key: rule.id ? `rule-${rule.id}` : this._nextRuleKey(),
        }));
    }
```

- [ ] **Step 2: Replace the threshold getters with the formula and rule getters**

ในไฟล์เดิม แทน getter `thresholdModes` (บรรทัด 70–72) และ `showThreshold` (บรรทัด 98–100) และเพิ่ม getter ชุดใหม่ ต่อจาก `showGoal`:

```js
    get formulaModes() {
        return this.props.meta.formula_modes || [];
    }

    get formulaTypes() {
        return this.props.meta.formula_types || [];
    }

    get compareTypes() {
        return this.props.meta.compare_types || [];
    }

    get operators() {
        return this.props.meta.operators || [];
    }

    get statuses() {
        return this.props.meta.statuses || [];
    }

    get periodBases() {
        return this.props.meta.period_bases || [];
    }

    get isFormula() {
        return this.state.draft.formula_mode !== "measure";
    }

    get isPresetFormula() {
        return this.state.draft.formula_mode === "preset";
    }

    get isCustomFormula() {
        return this.state.draft.formula_mode === "custom";
    }

    get selectedFormula() {
        return (
            this.formulaTypes.find((item) => item.key === this.state.draft.formula_type) || null
        );
    }

    get needsWeight() {
        const formula = this.selectedFormula;
        return Boolean(formula && formula.slots.some((key) => WEIGHT_KEYS.includes(key)));
    }

    /** The slots currently bound, as a plain object (bad JSON reads as empty). */
    get slotMap() {
        try {
            const parsed = JSON.parse(this.state.draft.formula_slots || "{}");
            return parsed && typeof parsed === "object" ? parsed : {};
        } catch (error) {
            return {};
        }
    }

    /**
     * One row per slot of the selected preset. A variadic preset (sum,
     * average) grows as soon as the designer adds a slot, so c to e appear
     * only when wanted.
     */
    get slotRows() {
        const formula = this.selectedFormula;
        if (!formula) {
            return [];
        }
        const map = this.slotMap;
        const keys = [...formula.slots];
        if (formula.variadic) {
            for (const key of SLOT_KEYS) {
                if (!keys.includes(key) && map[key] !== undefined) {
                    keys.push(key);
                }
            }
        }
        return keys.map((key) => ({
            key,
            label: key.toUpperCase(),
            is_weight: WEIGHT_KEYS.includes(key),
            value: map[key] === undefined ? "" : map[key],
        }));
    }

    get canAddSlot() {
        const formula = this.selectedFormula;
        if (!formula || !formula.variadic) {
            return false;
        }
        const map = this.slotMap;
        return SLOT_KEYS.some((key) => map[key] === undefined);
    }

    /** The other widgets of the dashboard: allowed as a comparison operand. */
    get widgetOptions() {
        return (this.props.widgets || []).filter((item) => item.id !== this.state.draft.id);
    }

    get ruleRows() {
        return this.state.draft.rule_ids.map((rule, index) => ({
            ...rule,
            index,
            is_constant: rule.compare_type === "constant",
            is_percent: rule.compare_type === "percent_of_goal",
            is_widget: rule.compare_type === "widget",
        }));
    }

    /** Every name the insert buttons may offer to a custom expression. */
    get insertableNames() {
        const names = [...SLOT_KEYS, ...IMPLICIT_NAMES];
        for (const measure of this.measures) {
            if (!names.includes(measure.key)) {
                names.push(measure.key);
            }
        }
        for (const widget of this.widgetOptions) {
            names.push(`widget_${widget.id}`);
        }
        return names;
    }

    // ------------------------------------------------------------------
    // Preview getters
    // ------------------------------------------------------------------
    get previewExpression() {
        const data = this.state.preview.data;
        return data ? data.formula_expression || "" : "";
    }

    get previewValue() {
        const data = this.state.preview.data;
        if (!data) {
            return "";
        }
        return this._number(data.value);
    }

    get previewRecords() {
        const data = this.state.preview.data;
        return data ? data.record_count : 0;
    }

    get previewStatusLabel() {
        const data = this.state.preview.data;
        if (!data) {
            return "";
        }
        const match = this.statuses.find((item) => item.key === data.status);
        return match ? match.label : data.status;
    }

    get previewOperands() {
        const data = this.state.preview.data;
        if (!data) {
            return [];
        }
        return (data.operands || []).map((operand) => ({
            key: operand.alias,
            label: operand.label,
            text: this._number(operand.value),
        }));
    }

    get previewSeries() {
        const data = this.state.preview.data;
        if (!data) {
            return [];
        }
        return (data.series_preview || []).map((point, index) => ({
            key: `${point.label}-${index}`,
            label: point.label,
            text: this._number(point.value),
        }));
    }

    _number(value) {
        if (value === null || value === undefined) {
            return "—";
        }
        const number = Number(value);
        if (Number.isNaN(number)) {
            return String(value);
        }
        return number.toLocaleString(undefined, { maximumFractionDigits: 2 });
    }
```

> `isChart`, `showGoal`, `sources`, `widgetTypes`, `valueFormats`, `dateRanges`, `currentSource`, `measures`, `groupbys`, `dates`, `dialogTitle`, `sourceHint` ไม่เปลี่ยน

- [ ] **Step 3: Add the slot, rule and preview handlers**

แทน handler `onSourceChange` / `onTypeChange` / `onSave` เดิม (บรรทัด 118–171) ด้วย:

```js
    // ------------------------------------------------------------------
    // Handlers: data
    // ------------------------------------------------------------------
    onSourceChange(ev) {
        const sourceId = parseInt(ev.target.value, 10) || null;
        const draft = this.state.draft;
        draft.source_id = sourceId;
        const source = this.currentSource;
        const measureKeys = (source ? source.measures : []).map((item) => item.key);
        if (!measureKeys.includes(draft.measure_key)) {
            draft.measure_key = "__count";
        }
        const groupbyKeys = (source ? source.groupbys : []).map((item) => item.key);
        if (!groupbyKeys.includes(draft.groupby_key)) {
            draft.groupby_key = "";
        }
        const dateKeys = (source ? source.dates : []).map((item) => item.key);
        if (!dateKeys.includes(draft.date_key)) {
            draft.date_key = "";
        }
        // The slots of the previous source no longer resolve.
        draft.formula_slots = "{}";
        this._schedulePreview();
    }

    onTypeChange(ev) {
        const widgetType = ev.target.value;
        this.state.draft.widget_type = widgetType;
        if (CHART_TYPES.includes(widgetType) && !this.state.draft.groupby_key) {
            const first = this.groupbys[0];
            if (first) {
                this.state.draft.groupby_key = first.key;
            }
        }
        this.state.error = "";
        this._schedulePreview();
    }

    onFormulaChange() {
        this._schedulePreview();
    }

    onFormulaModeChange(ev) {
        const draft = this.state.draft;
        draft.formula_mode = ev.target.value;
        if (draft.formula_mode === "preset" && !draft.formula_type) {
            const first = this.formulaTypes[0];
            if (first) {
                draft.formula_type = first.key;
            }
        }
        this.state.error = "";
        this._schedulePreview();
    }

    onFormulaTypeChange(ev) {
        const draft = this.state.draft;
        draft.formula_type = ev.target.value;
        // The slots of the previous preset no longer apply.
        draft.formula_slots = "{}";
        this._schedulePreview();
    }

    // ------------------------------------------------------------------
    // Handlers: formula slots
    // ------------------------------------------------------------------
    setSlot(key, value) {
        const map = { ...this.slotMap };
        map[key] = WEIGHT_KEYS.includes(key) ? Number(value) || 0 : value;
        this.state.draft.formula_slots = JSON.stringify(map);
        this._schedulePreview();
    }

    addSlot() {
        const map = { ...this.slotMap };
        const next = SLOT_KEYS.find((key) => map[key] === undefined);
        if (!next) {
            return;
        }
        // An empty value keeps the row visible; ``_boundSlots`` drops it again
        // before the payload leaves the browser.
        map[next] = "";
        this.state.draft.formula_slots = JSON.stringify(map);
    }

    insertName(name) {
        const draft = this.state.draft;
        const current = draft.formula_expression || "";
        const spacer = current && !current.endsWith(" ") ? " " : "";
        draft.formula_expression = `${current}${spacer}${name}`;
        this._schedulePreview();
    }

    // ------------------------------------------------------------------
    // Handlers: status rules
    // ------------------------------------------------------------------
    addRule() {
        const draft = this.state.draft;
        draft.rule_ids = [
            ...draft.rule_ids,
            {
                id: 0,
                _key: this._nextRuleKey(),
                name: "",
                sequence: (draft.rule_ids.length + 1) * 10,
                active: true,
                operator: ">=",
                compare_type: "goal",
                compare_value: 0,
                compare_percent: 0,
                compare_widget_id: this.widgetOptions.length ? this.widgetOptions[0].id : false,
                status: this.statuses.length ? this.statuses[0].key : "red",
            },
        ];
        this._schedulePreview();
    }

    updateRule(index, key, value) {
        const rules = [...this.state.draft.rule_ids];
        const rule = { ...rules[index], [key]: value };
        if (key === "compare_type") {
            // Switching the comparison resets the operand it no longer uses.
            rule.compare_value = 0;
            rule.compare_percent = 0;
            rule.compare_widget_id = this.widgetOptions.length ? this.widgetOptions[0].id : false;
        }
        rules[index] = rule;
        this.state.draft.rule_ids = rules;
        this._schedulePreview();
    }

    removeRule(index) {
        const rules = [...this.state.draft.rule_ids];
        const [removed] = rules.splice(index, 1);
        if (removed && removed.id) {
            this.state.removedRuleIds = [...this.state.removedRuleIds, removed.id];
        }
        this.state.draft.rule_ids = rules;
        this._renumberRules();
        this._schedulePreview();
    }

    moveRule(index, delta) {
        const target = index + delta;
        const rules = [...this.state.draft.rule_ids];
        if (target < 0 || target >= rules.length) {
            return;
        }
        const [moved] = rules.splice(index, 1);
        rules.splice(target, 0, moved);
        this.state.draft.rule_ids = rules;
        this._renumberRules();
        this._schedulePreview();
    }

    _renumberRules() {
        this.state.draft.rule_ids = this.state.draft.rule_ids.map((rule, index) => ({
            ...rule,
            sequence: (index + 1) * 10,
        }));
    }

    onRuleDragStart(ev, index) {
        this.state.dragRuleIndex = index;
        if (ev.dataTransfer) {
            ev.dataTransfer.effectAllowed = "move";
            ev.dataTransfer.setData("text/plain", String(index));
        }
    }

    onRuleDragOver(ev) {
        ev.preventDefault();
    }

    onRuleDrop(ev, index) {
        ev.preventDefault();
        const from = this.state.dragRuleIndex;
        this.state.dragRuleIndex = null;
        if (from === null || from === undefined || from === index) {
            return;
        }
        const rules = [...this.state.draft.rule_ids];
        const [moved] = rules.splice(from, 1);
        rules.splice(index, 0, moved);
        this.state.draft.rule_ids = rules;
        this._renumberRules();
        this._schedulePreview();
    }

    // ------------------------------------------------------------------
    // Live preview
    // ------------------------------------------------------------------
    _clearPreviewTimer() {
        if (this._previewTimer) {
            clearTimeout(this._previewTimer);
            this._previewTimer = null;
        }
    }

    _schedulePreview() {
        this._clearPreviewTimer();
        this._previewTimer = setTimeout(() => this._refreshPreview(), PREVIEW_DEBOUNCE);
    }

    async _refreshPreview() {
        this._clearPreviewTimer();
        const values = this._previewValues();
        if (!values.name || !values.source_id) {
            // Not enough to compute anything yet: do not bother the server.
            this.state.preview = { loading: false, data: null, error: "" };
            return;
        }
        this.state.preview = { loading: true, data: this.state.preview.data, error: "" };
        try {
            const data = await this.orm.call("od19.dashboard", "preview_widget", [
                values,
                this.state.draft.date_range,
            ]);
            this.state.preview = { loading: false, data, error: "" };
        } catch (error) {
            this.state.preview = { loading: false, data: null, error: this._errorText(error) };
        }
    }

    _errorText(error) {
        const data = (error && error.data) || {};
        return data.message || (error && error.message) || _t("The preview could not be computed.");
    }

    _previewValues() {
        const values = this._buildValues();
        // The draft must know its dashboard so a reference to another widget can
        // be resolved while designing. ``onSave`` never sends this key.
        if (this.props.dashboardId) {
            values.dashboard_id = this.props.dashboardId;
        }
        return values;
    }

    _buildValues() {
        const draft = this.state.draft;
        return {
            ...(draft.id ? { id: draft.id } : {}),
            name: draft.name,
            subtitle: draft.subtitle,
            widget_type: draft.widget_type,
            value_format: draft.value_format,
            color: draft.color,
            source_id: draft.source_id,
            measure_key: draft.measure_key,
            groupby_key: draft.groupby_key,
            date_key: draft.date_key,
            date_range: draft.date_range,
            domain: draft.domain,
            limit: draft.limit,
            goal_value: draft.goal_value,
            show_delta: draft.show_delta,
            formula_mode: draft.formula_mode,
            formula_type: draft.formula_type || null,
            formula_slots: JSON.stringify(this._boundSlots()),
            formula_expression: draft.formula_expression,
            formula_basis: draft.formula_basis,
            delta_basis: draft.delta_basis,
            default_status: draft.default_status,
            rule_ids: this._ruleCommands(),
            grid_w: draft.grid_w,
            grid_h: draft.grid_h,
        };
    }

    /** Only the slots the designer actually filled in. */
    _boundSlots() {
        const bound = {};
        for (const [key, value] of Object.entries(this.slotMap)) {
            if (value === "" || value === null || value === undefined) {
                continue;
            }
            if (WEIGHT_KEYS.includes(key) && !Number(value)) {
                continue;
            }
            bound[key] = value;
        }
        return bound;
    }

    /**
     * The rule list as One2many commands. ``[1, id, {...}]`` updates a stored
     * rule, ``[0, 0, {...}]`` adds one and ``[2, id]`` deletes the rules the
     * designer removed (a plain rewrite never deletes anything).
     */
    _ruleCommands() {
        const commands = [];
        for (const rule of this.state.draft.rule_ids) {
            const data = {
                name: rule.name || "",
                sequence: rule.sequence,
                active: rule.active !== false,
                operator: rule.operator,
                compare_type: rule.compare_type,
                compare_value: Number(rule.compare_value) || 0,
                compare_percent: Number(rule.compare_percent) || 0,
                compare_widget_id: rule.compare_widget_id || false,
                status: rule.status,
            };
            commands.push(rule.id ? [1, rule.id, data] : [0, 0, data]);
        }
        for (const ruleId of this.state.removedRuleIds) {
            commands.push([2, ruleId]);
        }
        return commands;
    }

    onSave() {
        const draft = this.state.draft;
        if (!draft.name || !draft.name.trim()) {
            this.state.error = _t("Give the widget a name.");
            return;
        }
        if (!draft.source_id) {
            this.state.error = _t("Choose a data source.");
            return;
        }
        if (CHART_TYPES.includes(draft.widget_type) && !draft.groupby_key) {
            this.state.error = _t("Chart widgets need a group by field.");
            return;
        }
        if (this.isPresetFormula && !draft.formula_type) {
            this.state.error = _t("Choose a preset formula.");
            return;
        }
        if (this.isCustomFormula && !(draft.formula_expression || "").trim()) {
            this.state.error = _t("Type the formula of this widget.");
            return;
        }
        this.props.onSave(this._buildValues());
    }
```

> `onSave` ไม่ได้คัดลอก draft ทั้งก้อนอีกต่อไป แต่ประกอบ payload จาก `_buildValues()` เพื่อให้ `_key`, `removedRuleIds` และสล็อตว่างไม่หลุดออกไป และไม่ต้องพึ่งการกรอง `undefined`

- [ ] **Step 4: Rebuild the dialog template**

ใน `custom_addons/od19_dashboard/static/src/dashboard/builder_dialog.xml`:

**4a.** เปลี่ยน `<div class="modal-dialog modal-lg modal-dialog-scrollable">` (บรรทัด 6) เป็น:

```xml
            <div class="modal-dialog modal-xl modal-dialog-scrollable">
```

**4b.** เปิดสองคอลัมน์ใน modal-body — แทนบรรทัด 18–19:

```xml
                    <div class="modal-body">
                        <div class="alert alert-danger" role="alert" t-if="state.error" t-esc="state.error"/>

                        <div class="row g-4">
                            <div class="col-lg-8">
```

และปิดคอลัมน์ซ้าย + เปิดคอลัมน์ขวา preview ก่อน `</div>` ปิด modal-body (เดิมบรรทัด 202) — หลังจากบล็อก Layout (บรรทัด 184–201) ให้ใส่:

```xml
                            </div>

                            <!-- ===================== Preview ===================== -->
                            <div class="col-lg-4">
                                <div class="od19-preview">
                                    <div class="od19-preview__header">
                                        <h6 class="od19-builder__section mb-0">Preview</h6>
                                        <button type="button" class="od19-icon-btn od19-icon-btn--sm"
                                                title="Refresh the preview" t-on-click="_refreshPreview">
                                            <i class="fa fa-refresh"/>
                                        </button>
                                    </div>

                                    <div class="text-muted" t-if="state.preview.loading">
                                        <i class="fa fa-spinner fa-spin me-1"/>Computing…
                                    </div>
                                    <div class="alert alert-warning" role="alert"
                                         t-if="state.preview.error" t-esc="state.preview.error"/>
                                    <div class="text-muted" t-if="!state.preview.data and !state.preview.loading and !state.preview.error">
                                        Fill in the title and the data source to see the result.
                                    </div>

                                    <t t-if="state.preview.data and !state.preview.loading">
                                        <div class="od19-preview__value">
                                            <span t-attf-class="od19-preview__dot od19-status-{{ state.preview.data.status }}"/>
                                            <span t-esc="previewValue"/>
                                        </div>
                                        <ul class="od19-preview__meta">
                                            <li>
                                                Records collected:
                                                <strong t-esc="previewRecords"/>
                                            </li>
                                            <li>
                                                Status:
                                                <strong t-esc="previewStatusLabel"/>
                                                <span class="text-muted"
                                                      t-esc="state.preview.data.status_source === 'rule' ? '(rule)' : '(default)'"/>
                                            </li>
                                        </ul>
                                        <div class="od19-preview__message" t-if="state.preview.data.message"
                                             t-esc="state.preview.data.message"/>
                                        <div class="od19-preview__expression" t-if="previewExpression">
                                            <small class="text-muted">Expression</small>
                                            <code t-esc="previewExpression"/>
                                        </div>
                                        <table class="table table-sm od19-preview__table" t-if="previewOperands.length">
                                            <thead>
                                                <tr><th>Slot</th><th>Value</th></tr>
                                            </thead>
                                            <tbody>
                                                <tr t-foreach="previewOperands" t-as="operand" t-key="operand.key">
                                                    <td t-esc="operand.label"/>
                                                    <td t-esc="operand.text"/>
                                                </tr>
                                            </tbody>
                                        </table>
                                        <table class="table table-sm od19-preview__table" t-if="previewSeries.length">
                                            <thead>
                                                <tr><th>Group</th><th>Value</th></tr>
                                            </thead>
                                            <tbody>
                                                <tr t-foreach="previewSeries" t-as="point" t-key="point.key">
                                                    <td t-esc="point.label"/>
                                                    <td t-esc="point.text"/>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </t>
                                </div>
                            </div>
                        </div>
                    </div>
```

> ตารางสล็อตแสดงได้เฉพาะ 5 bucket แรกตาม `series_preview` ของสเปก §6.1 — ชื่อหัวตารางคือ "Group" เพื่อให้ตรงกับ API

**4c.** แทน select ของ Measure (บรรทัด 83–92) ด้วยแบบที่มีเงื่อนไขโหมด:

```xml
                            <div class="col-md-6" t-if="!isFormula">
                                <label class="form-label" for="od19_widget_measure">Measure</label>
                                <select id="od19_widget_measure" class="form-select"
                                        t-model="state.draft.measure_key"
                                        t-on-change="onFormulaChange">
                                    <option t-foreach="measures" t-as="measure" t-key="measure.key"
                                            t-att-value="measure.key">
                                        <t t-esc="measure.label"/>
                                    </option>
                                </select>
                            </div>
```

**4d.** แทรกบล็อกสูตรต่อจาก select ของ Data source (หลังบรรทัด 82) ก่อน select ของ Measure:

```xml
                            <div class="col-md-6" t-if="isFormula">
                                <label class="form-label" for="od19_widget_formula_mode">Formula</label>
                                <select id="od19_widget_formula_mode" class="form-select"
                                        t-model="state.draft.formula_mode"
                                        t-on-change="onFormulaModeChange">
                                    <option t-foreach="formulaModes" t-as="mode" t-key="mode.key"
                                            t-att-value="mode.key">
                                        <t t-esc="mode.label"/>
                                    </option>
                                </select>
                            </div>
                            <div class="col-md-6" t-if="isFormula">
                                <label class="form-label" for="od19_widget_formula_basis">
                                    Period used by the formula
                                </label>
                                <select id="od19_widget_formula_basis" class="form-select"
                                        t-model="state.draft.formula_basis"
                                        t-on-change="onFormulaChange">
                                    <option t-foreach="periodBases" t-as="basis" t-key="basis.key"
                                            t-att-value="basis.key">
                                        <t t-esc="basis.label"/>
                                    </option>
                                </select>
                            </div>
                            <div class="col-md-6" t-if="isPresetFormula">
                                <label class="form-label" for="od19_widget_formula_type">Preset</label>
                                <select id="od19_widget_formula_type" class="form-select"
                                        t-model="state.draft.formula_type"
                                        t-on-change="onFormulaTypeChange">
                                    <option t-att-value="null">— Select a formula —</option>
                                    <option t-foreach="formulaTypes" t-as="formula" t-key="formula.key"
                                            t-att-value="formula.key">
                                        <t t-esc="formula.label"/>
                                    </option>
                                </select>
                            </div>
                            <div class="col-12" t-if="isPresetFormula and selectedFormula">
                                <div class="od19-slots">
                                    <div class="od19-slots__row" t-foreach="slotRows" t-as="slot" t-key="slot.key">
                                        <label class="od19-slots__label" t-att-for="'od19_slot_' + slot.key">
                                            <t t-esc="slot.label"/>
                                        </label>
                                        <select t-if="!slot.is_weight"
                                                t-att-id="'od19_slot_' + slot.key"
                                                class="form-select form-select-sm"
                                                t-att-value="slot.value"
                                                t-on-change="(ev) => this.setSlot(slot.key, ev.target.value)">
                                            <option t-att-value="">— Select a measure —</option>
                                            <option t-foreach="measures" t-as="measure" t-key="measure.key"
                                                    t-att-value="measure.key">
                                                <t t-esc="measure.label"/>
                                            </option>
                                        </select>
                                        <input t-else="" type="number" step="any" min="0"
                                               t-att-id="'od19_slot_' + slot.key"
                                               class="form-control form-control-sm"
                                               t-att-value="slot.value"
                                               t-on-change="(ev) => this.setSlot(slot.key, ev.target.value)"/>
                                    </div>
                                    <button type="button" class="btn btn-link btn-sm p-0" t-if="canAddSlot"
                                            t-on-click="addSlot">
                                        <i class="fa fa-plus me-1"/>Add a slot
                                    </button>
                                    <small class="text-muted d-block" t-if="selectedFormula.expression">
                                        Expression: <code t-esc="selectedFormula.expression"/>
                                    </small>
                                </div>
                            </div>
                            <div class="col-12" t-if="isCustomFormula">
                                <label class="form-label" for="od19_widget_expression">Expression</label>
                                <textarea id="od19_widget_expression" rows="2" class="form-control"
                                          placeholder="a / b * 100"
                                          t-model="state.draft.formula_expression"
                                          t-on-input="onFormulaChange"/>
                                <div class="od19-slots__names">
                                    <button type="button" class="btn btn-outline-secondary btn-sm"
                                            t-foreach="insertableNames" t-as="name" t-key="name"
                                            t-on-click="() => this.insertName(name)">
                                        <t t-esc="name"/>
                                    </button>
                                </div>
                                <small class="text-muted">
                                    Allowed: <code>+ - * / % **</code>, comparisons,
                                    <code>and</code> / <code>or</code>, <code>min</code>,
                                    <code>max</code>, <code>abs</code>, <code>round</code>.
                                </small>
                            </div>
```

**4e.** แทนหมวด "Target &amp; status" ทั้งหมด (บรรทัด 145–182) ด้วย:

```xml
                        <!-- ===================== Targets ===================== -->
                        <h6 class="od19-builder__section">Target &amp; status</h6>
                        <div class="row g-3">
                            <div class="col-md-4" t-if="showGoal">
                                <label class="form-label" for="od19_widget_goal">Goal value</label>
                                <input id="od19_widget_goal" type="number" step="any"
                                       class="form-control" t-model.number="state.draft.goal_value"
                                       t-on-change="onFormulaChange"/>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label" for="od19_widget_default_status">
                                    When no rule matches
                                </label>
                                <select id="od19_widget_default_status" class="form-select"
                                        t-model="state.draft.default_status"
                                        t-on-change="onFormulaChange">
                                    <option t-foreach="statuses" t-as="status" t-key="status.key"
                                            t-att-value="status.key">
                                        <t t-esc="status.label"/>
                                    </option>
                                </select>
                            </div>
                            <div class="col-md-4" t-if="state.draft.widget_type === 'kpi'">
                                <div class="form-check mt-md-4">
                                    <input id="od19_widget_delta" type="checkbox" class="form-check-input"
                                           t-model="state.draft.show_delta" t-on-change="onFormulaChange"/>
                                    <label class="form-check-label" for="od19_widget_delta">
                                        Show the period comparison
                                    </label>
                                </div>
                            </div>
                            <div class="col-md-4"
                                 t-if="state.draft.widget_type === 'kpi' and state.draft.show_delta">
                                <label class="form-label" for="od19_widget_delta_basis">
                                    Comparison period
                                </label>
                                <select id="od19_widget_delta_basis" class="form-select"
                                        t-model="state.draft.delta_basis"
                                        t-on-change="onFormulaChange">
                                    <option t-foreach="periodBases" t-as="basis" t-key="basis.key"
                                            t-att-value="basis.key">
                                        <t t-esc="basis.label"/>
                                    </option>
                                </select>
                            </div>
                        </div>

                        <!-- ===================== Status rules ===================== -->
                        <h6 class="od19-builder__section">
                            Status rules
                            <button type="button" class="btn btn-outline-secondary btn-sm ms-2"
                                    t-on-click="addRule">
                                <i class="fa fa-plus me-1"/>Add rule
                            </button>
                        </h6>
                        <p class="text-muted od19-rules__hint">
                            The first matching rule, from the top, decides the colour of the widget.
                            Drag the handle or use the arrows to change the order.
                        </p>
                        <div class="table-responsive" t-if="ruleRows.length">
                            <table class="table table-sm align-middle od19-rules">
                                <thead>
                                    <tr>
                                        <th style="width: 2rem"></th>
                                        <th style="width: 22%">Operator</th>
                                        <th style="width: 26%">Compare with</th>
                                        <th>Value</th>
                                        <th style="width: 18%">Colour</th>
                                        <th style="width: 5rem"></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr t-foreach="ruleRows" t-as="rule" t-key="rule._key"
                                        class="od19-rules__row" draggable="true"
                                        t-on-dragstart="(ev) => this.onRuleDragStart(ev, rule.index)"
                                        t-on-dragover="onRuleDragOver"
                                        t-on-drop="(ev) => this.onRuleDrop(ev, rule.index)">
                                        <td class="od19-rules__handle" title="Drag to reorder">
                                            <i class="fa fa-bars"/>
                                        </td>
                                        <td>
                                            <select class="form-select form-select-sm"
                                                    t-att-value="rule.operator"
                                                    t-on-change="(ev) => this.updateRule(rule.index, 'operator', ev.target.value)">
                                                <option t-foreach="operators" t-as="operator" t-key="operator.key"
                                                        t-att-value="operator.key">
                                                    <t t-esc="operator.label"/>
                                                </option>
                                            </select>
                                        </td>
                                        <td>
                                            <select class="form-select form-select-sm"
                                                    t-att-value="rule.compare_type"
                                                    t-on-change="(ev) => this.updateRule(rule.index, 'compare_type', ev.target.value)">
                                                <option t-foreach="compareTypes" t-as="compare" t-key="compare.key"
                                                        t-att-value="compare.key">
                                                    <t t-esc="compare.label"/>
                                                </option>
                                            </select>
                                        </td>
                                        <td>
                                            <input t-if="rule.is_constant" type="number" step="any"
                                                   class="form-control form-control-sm"
                                                   t-att-value="rule.compare_value"
                                                   t-on-change="(ev) => this.updateRule(rule.index, 'compare_value', ev.target.value)"/>
                                            <div t-elif="rule.is_percent" class="input-group input-group-sm">
                                                <input type="number" step="any" min="0"
                                                       class="form-control"
                                                       t-att-value="rule.compare_percent"
                                                       t-on-change="(ev) => this.updateRule(rule.index, 'compare_percent', ev.target.value)"/>
                                                <span class="input-group-text">%</span>
                                            </div>
                                            <select t-elif="rule.is_widget" class="form-select form-select-sm"
                                                    t-att-value="rule.compare_widget_id"
                                                    t-on-change="(ev) => this.updateRule(rule.index, 'compare_widget_id', parseInt(ev.target.value, 10) || false)">
                                                <option t-att-value="false">— Select a widget —</option>
                                                <option t-foreach="widgetOptions" t-as="option" t-key="option.id"
                                                        t-att-value="option.id">
                                                    <t t-esc="option.name"/>
                                                </option>
                                            </select>
                                            <span t-else="" class="text-muted">—</span>
                                        </td>
                                        <td>
                                            <select class="form-select form-select-sm"
                                                    t-att-value="rule.status"
                                                    t-on-change="(ev) => this.updateRule(rule.index, 'status', ev.target.value)">
                                                <option t-foreach="statuses" t-as="status" t-key="status.key"
                                                        t-att-value="status.key">
                                                    <t t-esc="status.label"/>
                                                </option>
                                            </select>
                                        </td>
                                        <td class="od19-rules__actions">
                                            <button type="button" class="od19-icon-btn od19-icon-btn--sm"
                                                    title="Move up" t-on-click="() => this.moveRule(rule.index, -1)">
                                                <i class="fa fa-arrow-up"/>
                                            </button>
                                            <button type="button" class="od19-icon-btn od19-icon-btn--sm"
                                                    title="Move down" t-on-click="() => this.moveRule(rule.index, 1)">
                                                <i class="fa fa-arrow-down"/>
                                            </button>
                                            <button type="button"
                                                    class="od19-icon-btn od19-icon-btn--sm od19-icon-btn--danger"
                                                    title="Remove rule" t-on-click="() => this.removeRule(rule.index)">
                                                <i class="fa fa-trash-o"/>
                                            </button>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                        <p class="text-muted" t-else="">
                            No rule yet: the widget keeps the colour chosen above.
                        </p>
```

> ปุ่ม `fa-arrow-up` / `fa-arrow-down` / `fa-trash-o` / `fa-refresh` ทุกตัวมี `title` ตามข้อกำหนดของโปรเจกต์ (Odoo 19 ออก warning ถ้าปุ่ม icon ไม่มี `title`)

- [ ] **Step 5: Pass the new props and drop the legacy keys in the dashboard action**

ใน `custom_addons/od19_dashboard/static/src/dashboard/dashboard_action.js`:

**5a.** แทน `threshold_modes: []` (บรรทัด 49) ใน `setup()` ด้วย:

```js
                formula_modes: [],
                formula_types: [],
                compare_types: [],
                operators: [],
                statuses: [],
                period_bases: [],
```

**5b.** แทน `_deltaClass` (บรรทัด 371–379) ด้วย:

```js
    _deltaClass(widget) {
        if (!widget.delta) {
            return "od19-delta-flat";
        }
        const positive = widget.delta > 0;
        // The server infers the direction from the first red rule, so a widget
        // whose alert is "below a threshold" is not shown as improving.
        const better = widget.is_lower_better ? !positive : positive;
        return better ? "od19-delta-good" : "od19-delta-bad";
    }
```

**5c.** เพิ่มสองบรรทัดใน `_decorate` (ต่อจาก `widget.delta_icon = this._deltaIcon(widget);` บรรทัด 355):

```js
            widget.delta_note = this._basisLabel(widget.delta_basis).toLowerCase();
            // Shown as a tooltip on the widget card while designing.
            widget.formula_hint = widget.formula_expression || "";
```

และเพิ่ม helper ต่อจาก `_deltaIcon`:

```js
    _basisLabel(basis) {
        const match = (this.state.meta.period_bases || []).find((item) => item.key === basis);
        return match ? match.label : _t("previous period");
    }
```

> `_decorate` อ่าน key ใหม่จาก `_get_widget_data()` (`delta_basis`, `is_lower_better`, `formula_expression`, `status_source`) ที่ Task 6 ส่งมาแล้ว โดยไม่ต้องลบ key เดิมใด ๆ

**5d.** ใน `custom_addons/od19_dashboard/static/src/dashboard/dashboard_action.xml` แทนบรรทัด 153:

```xml
                                        <span class="od19-kpi__delta-note">vs previous</span>
```

ด้วย:

```xml
                                        <span class="od19-kpi__delta-note"
                                              t-if="widget.delta_note"
                                              t-esc="widget.delta_note"/>
```

และเปลี่ยน invocation ของ `BuilderDialog` (บรรทัด 276–280) เป็น:

```xml
            <BuilderDialog t-if="state.builder.open"
                           meta="state.meta"
                           widgets="state.widgets"
                           dashboardId="state.dashboardId"
                           config="state.builder.config"
                           onSave="onBuilderSave"
                           onClose="closeBuilder"/>
```

**5e.** เพิ่ม tooltip ของสูตรบนการ์ด widget — แทน `<span class="od19-widget__name" t-esc="widget.name"/>` (บรรทัด 124) ด้วย:

```xml
                                <span class="od19-widget__name" t-esc="widget.name"
                                      t-att-title="state.editMode ? widget.formula_hint : ''"/>
```

- [ ] **Step 6: Style the slot table, the rule table and the preview panel**

ต่อท้าย `custom_addons/od19_dashboard/static/src/dashboard/dashboard_action.scss` (หลังบล็อก `.od19-builder__section`) เพิ่ม:

```scss
.od19-slots {
    &__row {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.35rem;
    }

    &__label {
        flex: 0 0 2.2rem;
        font-weight: 600;
        font-size: 0.85rem;
    }

    &__names {
        display: flex;
        flex-wrap: wrap;
        gap: 0.25rem;
        margin: 0.35rem 0;
    }
}

.od19-rules {
    font-size: 0.875rem;

    &__hint {
        font-size: 0.8rem;
    }

    &__row[draggable="true"] {
        cursor: grab;
    }

    &__handle {
        color: #8a8a8a;
        cursor: grab;
    }

    &__actions {
        white-space: nowrap;
        text-align: right;
    }
}

.od19-preview {
    position: sticky;
    top: 0;
    padding: 0.75rem;
    border: 1px solid #e3e3e3;
    border-radius: 0.5rem;
    background: #fbfbfb;

    &__header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.5rem;
    }

    &__value {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 1.5rem;
        font-weight: 600;
    }

    &__dot {
        width: 0.7rem;
        height: 0.7rem;
        border-radius: 50%;
        display: inline-block;
    }

    &__meta {
        list-style: none;
        padding: 0;
        margin: 0.5rem 0;
        font-size: 0.85rem;
    }

    &__message {
        color: #9e2424;
        font-size: 0.8rem;
    }

    &__expression {
        display: flex;
        flex-direction: column;
        margin-bottom: 0.5rem;

        code {
            word-break: break-all;
        }
    }

    &__table {
        margin-bottom: 0.5rem;
        font-size: 0.8rem;
    }
}
```

> `.od19-status-red|yellow|green|grey` มีอยู่แล้วในไฟล์นี้ (บรรทัด 349–364) จึงใช้กับจุดสีของ preview ได้ทันที

- [ ] **Step 7: Check the JavaScript syntax**

```powershell
node --check custom_addons/od19_dashboard/static/src/dashboard/builder_dialog.js
node --check custom_addons/od19_dashboard/static/src/dashboard/dashboard_action.js
```

Expected: ทั้งสองคำสั่งไม่มี output และ `$LASTEXITCODE` เป็น `0`

> ตรวจแล้วในเครื่องนี้: `node --check` กับไฟล์ที่มี `/** @odoo-module **/` และ `import` ทำงานได้ปกติ (ทดสอบกับ `builder_dialog.js` ก่อนแก้ ได้ exit code 0)

- [ ] **Step 8: Verify the template names still match**

```powershell
findstr /C:"od19_dashboard.BuilderDialog" custom_addons/od19_dashboard/static/src/dashboard/builder_dialog.js custom_addons/od19_dashboard/static/src/dashboard/builder_dialog.xml
findstr /C:"od19_dashboard.DashboardAction" custom_addons/od19_dashboard/static/src/dashboard/dashboard_action.js custom_addons/od19_dashboard/static/src/dashboard/dashboard_action.xml
```

Expected: อย่างละ 2 บรรทัด — `static template` ใน JS ต้องตรงกับ `t-name` ใน XML เสมอ (OWL จะ throw ตอน runtime ถ้าไม่ตรง)

- [ ] **Step 9: Commit**

```powershell
git add custom_addons/od19_dashboard/static/src/dashboard/builder_dialog.js custom_addons/od19_dashboard/static/src/dashboard/builder_dialog.xml custom_addons/od19_dashboard/static/src/dashboard/dashboard_action.js custom_addons/od19_dashboard/static/src/dashboard/dashboard_action.xml custom_addons/od19_dashboard/static/src/dashboard/dashboard_action.scss
git commit -m "feat(od19_dashboard): design widget formulas and status rules in the builder"
```

**ผลลัพธ์หลัง Task 8 (ตรวจด้วยตาเปล่าได้):** เปิด `http://localhost:8070` → Dashboards → My Dashboards → Customize → Add Widget จะเห็น select "Formula" (Single measure / Preset formula / Custom expression), ตารางสล็อต A–E พร้อมน้ำหนักสำหรับ Weighted Average, ปุ่มแทรกชื่อตัวแปรในโหมด custom, ตาราง Status rules ที่ลากสลับได้ และแผง Preview ทางขวาที่แสดงค่าที่คำนวณได้ จำนวน record สถานะ และตารางสล็อต

> **สถานะกึ่งกลางที่ต้องทราบ:** widget ที่ seed ไว้จะยังไม่มี rule และยังไม่มีการ migrate ข้อมูล threshold เดิม จนกว่า Task 9 (migration) และ Task 10 (seed) จะเสร็จ — ระหว่างนี้ widget เหล่านั้นจะแสดงสีเขียวหรือเทาตาม `default_status` เท่านั้น

---

### Task 9: Migrate the legacy thresholds into the rule table

**Goal:** ย้ายค่า threshold ของ widget ที่มีอยู่ในฐานข้อมูลเดิมไปเป็นแถวของ `od19.dashboard.widget.rule` โดยให้ `_evaluate_rules()` ให้ผลเทียบเท่า `_compute_status()` ที่ถอดออกใน Task 7 ทุกช่วงค่า ผู้ใช้ไม่ต้องตั้งกฎใหม่เองและสีของ KPI ไม่เปลี่ยนหลังอัปเกรด

**Files:**
- Create: `custom_addons/od19_dashboard/migrations/19.0.2.0.0/pre-migrate.py`
- Create: `custom_addons/od19_dashboard/migrations/19.0.2.0.0/post-migrate.py`
- Create: `custom_addons/od19_dashboard/tests/test_dashboard_migration.py`
- Modify: `custom_addons/od19_dashboard/tests/__init__.py`

**Precondition:** Task 1 (โมเดล rule + ACL + record rules) และ Task 7 (ลบฟิลด์เดิม, เพิ่ม `formula_mode` / `formula_slots` / `formula_basis` / `delta_basis` / `default_status`, ลบ `_compute_status()`) เสร็จแล้ว

**บริบทและข้อจำกัดที่ต้องออกแบบรอบรับ:**

Odoo เรียกสคริปต์ migration ตามลำดับนี้

```
migrate_module(pre) → registry.init_models() → load_data('init') → load_data() → migrate_module(post) → post_init_hook → migrate_module(end)
```

- `pre-migrate.py` ทำงาน **ก่อน** ปรับ schema → คอลัมน์ `threshold_mode` / `warning_value` / `critical_value` ยังอยู่
- `post-migrate.py` ทำงาน **หลัง** ปรับ schema → คอลัมน์เหล่านั้นถูกลบไปแล้ว แต่ตาราง `od19_dashboard_widget_rule` และคอลัมน์ใหม่ของ widget (`formula_mode`, `delta_basis`, `default_status`, ...) ถูกสร้างแล้ว
- ลายเซ็นคือ `def migrate(cr, version)` — **ไม่มี `env`** จึงใช้ ORM ไม่ได้ทั้งสองฝั่ง ต้องใช้ raw SQL เท่านั้น
- โฟลเดอร์ migration ไม่ต้องมี `__init__.py` — Odoo หาไฟล์จากชื่อโฟลเดอร์ version แล้วโหลดด้วย `runpy`-style loader
- Odoo เรียกสคริปต์ในโฟลเดอร์ที่ `installed_version < folder_version <= new_version` จึงต้องใช้ชื่อโฟลเดอร์ `19.0.2.0.0` (version ใหม่) ไม่ใช่ `19.0.1.0.0`

**Design Decisions ของ task นี้:**

> **1. ส่งค่าข้ามสคริปต์ผ่านตารางชั่วคราว ไม่ใช้ `post_init_hook`** — `post_init_hook` รันเฉพาะตอน *ติดตั้งใหม่* และต้องประกาศใน `__init__.py` ให้ loader เห็น ส่วนกรณีของเราคือ **อัปเกรด** ซึ่งต้องใช้กลไก `pre-` / `post-migrate` เท่านั้น ตาราง `od19_dashboard_threshold_backup` เป็นที่พักข้อมูลช่วงสั้น ๆ และถูก `DROP` ทิ้งท้าย `post-migrate`

> **2. คัดลอกเฉพาะ widget ที่ `threshold_mode <> 'none'`** — widget ที่ไม่เคยตั้ง threshold ไม่ต้องมี rule และยังคงได้ `default_status = 'green'` เหมือนเดิม (สเปก §5.4)

> **3. ลำดับกฎ red ก่อน yellow และใช้ `<=` / `>=` ตามทิศทาง** — ตรรกะเดิมคือ `higher_is_better`: red เมื่อ `value <= critical`, yellow เมื่อ `value <= warning` (validation เดิมบังคับ `critical <= warning`); `lower_is_better`: red เมื่อ `value >= critical`, yellow เมื่อ `value >= warning` (บังคับ `critical >= warning`) การสร้าง rule ตามลำดับนี้ทำให้ first-match-wins ให้ผลตรงกันทุกช่วงค่า

> **4. KPI ที่ไม่มีค่า (`value is None`) ไม่ต้องใช้กฎเพื่อให้ได้สีเทา** — ตรรกะเดิมคืน `grey` เมื่อ `value is None` ซึ่งยังคงเป็นเช่นนั้นเพราะ `_fill_kpi_data()` คืนค่าก่อนเรียก `_evaluate_rules()` (Task 6 Step 4 — `if value is None: return`) ทำให้ `status` คงค่า `"grey"` จาก dict เริ่มต้นของ `_get_widget_data()` ดังนั้น `default_status = 'green'` จึงไม่ทำให้สีเพี้ยน

> **5. ไม่ตั้ง `compare_percent` / `compare_widget_id`** — ค่าเริ่มต้นของคอลัมน์คือ `0.0` และ `NULL` ตามลำดับ สอดคล้องกับ constraint ที่บังคับเฉพาะเมื่อ `compare_type` เป็น `percent_of_goal` หรือ `widget`

**การทดสอบบนฐานข้อมูล dev:** หลัง Task 7 Step 7 ฐานข้อมูล `odoo19` ไม่มีคอลัมน์ threshold แล้ว จึงทดสอบเส้นทาง `migrate()` ได้ด้วยการสร้างคอลัมน์เดิมกลับชั่วคราวในเทสต์ (DDL ใน transaction ถูก rollback เองเมื่อจบแต่ละเทสต์) ส่วนการอัปเกรดจริงทำกับ `odoo19_dashboard_baseline` ที่สำรองไว้ใน Task 7 Step 7a — จะรันได้จริงเมื่อ bump version ใน Task 10

---

- [ ] **Step 1: Write the failing test**

สร้าง `custom_addons/od19_dashboard/tests/test_dashboard_migration.py`:

```python
# -*- coding: utf-8 -*-
import runpy
from pathlib import Path

from odoo.tests.common import TransactionCase

MIGRATION_VERSION = "19.0.2.0.0"
MIGRATION_DIR = Path(__file__).resolve().parents[1] / "migrations" / MIGRATION_VERSION
BACKUP_TABLE = "od19_dashboard_threshold_backup"


def _load_migration(filename):
    """Return the ``migrate`` function of a migration script.

    ``migrations/19.0.2.0.0`` is not a valid Python package name (Odoo locates
    the folder by version string), so the script is executed straight from its
    path instead of being imported.
    """
    return runpy.run_path(str(MIGRATION_DIR / filename))["migrate"]


class TestDashboardThresholdMigration(TransactionCase):
    """The retired thresholds must come back as equivalent status rules."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dashboard = cls.env["od19.dashboard"].create({"name": "Migration dashboard"})
        cls.source = cls.env.ref("od19_dashboard.source_sale_order")
        cls.widget_model = cls.env["od19.dashboard.widget"]
        cls.pre_migrate = _load_migration("pre-migrate.py")
        cls.post_migrate = _load_migration("post-migrate.py")
        cls.installed_version = "19.0.1.0.0"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _legacy_status(self, value, mode, warning_value, critical_value):
        """Verbatim copy of the ``_compute_status()`` removed in Task 7.

        Kept in the test on purpose: the method no longer exists in the module,
        so this copy is the only reference for the migration equivalence check.
        """
        if value is None or mode == "none":
            return "green" if value is not None else "grey"
        if mode == "higher_is_better":
            if value <= critical_value:
                return "red"
            if value <= warning_value:
                return "yellow"
            return "green"
        if value >= critical_value:
            return "red"
        if value >= warning_value:
            return "yellow"
        return "green"

    def _add_legacy_columns(self):
        """Recreate the columns dropped by the module update (test only).

        The dev database has already been upgraded by Task 7, so the legacy
        columns have to be put back before the backup script can read them.
        """
        self.env.cr.execute(
            """
            ALTER TABLE od19_dashboard_widget
                ADD COLUMN IF NOT EXISTS threshold_mode varchar,
                ADD COLUMN IF NOT EXISTS warning_value double precision,
                ADD COLUMN IF NOT EXISTS critical_value double precision
            """
        )

    def _drop_legacy_columns(self):
        """Do what the module update does: remove the legacy columns."""
        self.env.cr.execute(
            """
            ALTER TABLE od19_dashboard_widget
               DROP COLUMN IF EXISTS threshold_mode,
               DROP COLUMN IF EXISTS warning_value,
               DROP COLUMN IF EXISTS critical_value
            """
        )

    def _legacy_widget(self, mode, warning_value, critical_value):
        """Create a widget and give it threshold values through raw SQL."""
        widget = self.widget_model.create(
            {
                "dashboard_id": self.dashboard.id,
                "name": "Legacy %s widget" % mode,
                "source_id": self.source.id,
                "measure_key": "__count",
            }
        )
        self.env.cr.execute(
            """
            UPDATE od19_dashboard_widget
               SET threshold_mode = %s, warning_value = %s, critical_value = %s
             WHERE id = %s
            """,
            (mode, warning_value, critical_value, widget.id),
        )
        return widget

    def _run_migration(self):
        """Replay the real upgrade order on the current transaction."""
        self.pre_migrate(self.env.cr, self.installed_version)
        # The schema is upgraded between the two scripts: the columns are gone
        # by the time ``post-migrate`` runs, only the backup table survives.
        self._drop_legacy_columns()
        self.post_migrate(self.env.cr, self.installed_version)
        self.env.invalidate_all()

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------
    def test_thresholds_become_equivalent_rules(self):
        cases = {
            "higher_is_better": (80.0, 50.0),
            "lower_is_better": (5.0, 10.0),
        }
        self._add_legacy_columns()
        widgets = {
            mode: self._legacy_widget(mode, warning, critical)
            for mode, (warning, critical) in cases.items()
        }

        self._run_migration()

        for mode, (warning_value, critical_value) in cases.items():
            widget = widgets[mode]
            rules = widget.rule_ids.sorted("sequence")
            expected_operator = "<=" if mode == "higher_is_better" else ">="
            self.assertEqual([rule.status for rule in rules], ["red", "yellow"])
            self.assertEqual([rule.operator for rule in rules], [expected_operator] * 2)
            self.assertEqual([rule.compare_type for rule in rules], ["constant"] * 2)
            self.assertEqual(
                [rule.compare_value for rule in rules], [critical_value, warning_value]
            )
            self.assertTrue(all(rule.active for rule in rules))
            self.assertEqual(widget.default_status, "green")
            self.assertEqual(widget.formula_mode, "measure")
            self.assertEqual(widget.formula_basis, "previous")
            self.assertEqual(widget.delta_basis, "previous")

            for value in (-10.0, 0.0, 49.0, 50.0, 79.0, 80.0, 100.0):
                context = {"value": value, "goal": 0.0, "widget_values": {}, "shifts": {}}
                self.assertEqual(
                    widget._evaluate_rules(context)[0],
                    self._legacy_status(value, mode, warning_value, critical_value),
                    "Status differs for %s at value %s" % (mode, value),
                )

    def test_widgets_without_threshold_get_no_rule(self):
        self._add_legacy_columns()
        widget = self._legacy_widget("none", 0.0, 0.0)

        self._run_migration()

        self.assertFalse(widget.rule_ids)
        self.assertEqual(widget.default_status, "green")
        context = {"value": 42.0, "goal": 0.0, "widget_values": {}, "shifts": {}}
        self.assertEqual(widget._evaluate_rules(context), ("green", "default"))

    def test_backup_table_is_dropped(self):
        self._add_legacy_columns()
        self._legacy_widget("higher_is_better", 80.0, 50.0)

        self._run_migration()

        self.env.cr.execute("SELECT to_regclass(%s)", (BACKUP_TABLE,))
        self.assertIsNone(self.env.cr.fetchone()[0])

    def test_migration_is_idempotent(self):
        self._add_legacy_columns()
        widget = self._legacy_widget("higher_is_better", 80.0, 50.0)

        self._run_migration()
        # A second pass must not duplicate anything: without the backup table
        # the pre script has nothing to copy and the post script only refreshes
        # the new column defaults.
        self.pre_migrate(self.env.cr, self.installed_version)
        self.post_migrate(self.env.cr, self.installed_version)
        widget.invalidate_recordset()

        self.assertEqual(len(widget.rule_ids), 2)
        self.env.cr.execute("SELECT to_regclass(%s)", (BACKUP_TABLE,))
        self.assertIsNone(self.env.cr.fetchone()[0])
```

และเพิ่มบรรทัดท้ายไฟล์ `custom_addons/od19_dashboard/tests/__init__.py`:

```python
from . import test_dashboard_migration
```

- [ ] **Step 2: Run the test to verify it fails**

```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 -u od19_dashboard --test-enable --test-tags /od19_dashboard --stop-after-init --log-level=test
```

Expected: FAIL — `TestDashboardThresholdMigration` ERROR ทุกเทสต์ด้วย `FileNotFoundError` จาก `MIGRATION_DIR / "pre-migrate.py"` เพราะยังไม่มีสคริปต์

- [ ] **Step 3: Create the backup script**

สร้าง `custom_addons/od19_dashboard/migrations/19.0.2.0.0/pre-migrate.py`:

```python
"""Back up the per-widget thresholds before the ORM drops their columns.

The widget model no longer declares ``threshold_mode``, ``warning_value`` and
``critical_value``, so updating the module deletes those columns. This script
runs *before* the schema is touched and copies the values into a temporary
table that ``post-migrate.py`` can still read: ``migrate(cr, version)`` never
receives an ``env``, so the ORM is not available at that point either.
"""

import logging

_logger = logging.getLogger(__name__)

BACKUP_TABLE = "od19_dashboard_threshold_backup"


def migrate(cr, version):
    if not version:
        return
    if not _has_legacy_column(cr):
        _logger.info(
            "od19_dashboard: no legacy threshold column found, nothing to back up"
        )
        return
    cr.execute("SELECT to_regclass(%s)", (BACKUP_TABLE,))
    if cr.fetchone()[0]:
        _logger.info(
            "od19_dashboard: %s already exists, keeping its content", BACKUP_TABLE
        )
        return
    cr.execute(
        """
        CREATE TABLE od19_dashboard_threshold_backup (
            widget_id integer PRIMARY KEY,
            threshold_mode varchar,
            warning_value double precision,
            critical_value double precision
        )
        """
    )
    cr.execute(
        """
        INSERT INTO od19_dashboard_threshold_backup
             (widget_id, threshold_mode, warning_value, critical_value)
        SELECT id, threshold_mode, warning_value, critical_value
          FROM od19_dashboard_widget
         WHERE threshold_mode IS NOT NULL
           AND threshold_mode <> 'none'
        """
    )
    _logger.info("od19_dashboard: backed up %s widget thresholds", cr.rowcount)


def _has_legacy_column(cr):
    """Return True when the widget table still has the threshold column."""
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = 'od19_dashboard_widget'
           AND column_name = 'threshold_mode'
        """
    )
    return bool(cr.fetchone())
```

- [ ] **Step 4: Create the conversion script**

สร้าง `custom_addons/od19_dashboard/migrations/19.0.2.0.0/post-migrate.py`:

```python
"""Turn the backed up thresholds into status rows.

Runs after the schema upgrade: the widget columns are gone, the rule table and
the new widget columns exist, and the temporary table filled by
``pre-migrate.py`` is the only remaining source of truth.
"""

import logging

_logger = logging.getLogger(__name__)

BACKUP_TABLE = "od19_dashboard_threshold_backup"

#: One row per rule to create: ``(threshold_mode, operator, sequence, status,
#: column, label)``. ``higher_is_better`` alerts when the value falls *below*
#: the bound, ``lower_is_better`` when it climbs *above* it; in both cases the
#: critical (red) rule must be evaluated before the warning (yellow) one so the
#: first-match-wins engine reproduces the retired ``_compute_status()``.
RULE_SPECS = [
    ("higher_is_better", "<=", 10, "red", "critical_value", "Migrated critical value"),
    ("higher_is_better", "<=", 20, "yellow", "warning_value", "Migrated warning value"),
    ("lower_is_better", ">=", 10, "red", "critical_value", "Migrated critical value"),
    ("lower_is_better", ">=", 20, "yellow", "warning_value", "Migrated warning value"),
]


def migrate(cr, version):
    if not version:
        return
    _convert_thresholds(cr)
    _set_widget_defaults(cr)


def _convert_thresholds(cr):
    """Insert the status rules of every widget that had a threshold."""
    cr.execute("SELECT to_regclass(%s)", (BACKUP_TABLE,))
    if not cr.fetchone()[0]:
        _logger.info(
            "od19_dashboard: no threshold backup table, nothing to convert"
        )
        return
    for mode, operator, sequence, status, column, label in RULE_SPECS:
        # ``column`` comes from the constant list above, never from user input.
        cr.execute(
            """
            INSERT INTO od19_dashboard_widget_rule
                 (widget_id, sequence, name, active, operator, compare_type,
                  compare_value, compare_percent, compare_widget_id, status)
            SELECT backup.widget_id, %s, %s, true, %s, 'constant',
                   COALESCE(backup.{column}, 0.0), 0.0, NULL, %s
              FROM od19_dashboard_threshold_backup AS backup
             WHERE backup.threshold_mode = %s
            """.format(column=column),
            (sequence, label, operator, status, mode),
        )
        _logger.info(
            "od19_dashboard: created %s '%s' rules for '%s' widgets",
            cr.rowcount,
            status,
            mode,
        )
    cr.execute("DROP TABLE %s" % BACKUP_TABLE)


def _set_widget_defaults(cr):
    """Give the new columns of the existing widgets their documented default.

    The ORM fills them from the field defaults while adding the columns, but
    the update does not run on a database where the fields already existed, so
    the values are set explicitly to keep the result deterministic.
    """
    cr.execute(
        """
        UPDATE od19_dashboard_widget
           SET formula_mode   = COALESCE(formula_mode, 'measure'),
               formula_slots  = COALESCE(formula_slots, '{}'),
               formula_basis  = COALESCE(formula_basis, 'previous'),
               delta_basis    = COALESCE(delta_basis, 'previous'),
               default_status = COALESCE(default_status, 'green')
        """
    )
```

- [ ] **Step 5: Run the tests to verify they pass**

```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 -u od19_dashboard --test-enable --test-tags /od19_dashboard --stop-after-init --log-level=test
```

Expected: PASS ทุกคลาส รวม `TestDashboardThresholdMigration` ทั้ง 4 เทสต์ — และ log ต้องมี `od19_dashboard: backed up N widget thresholds` กับ `created 1 'red' rules for 'higher_is_better' widgets`

> เทสต์นี้เรียก `migrate()` ตรง ๆ จึงไม่ต้องพึ่งกลไก version ของ Odoo การอัปเกรดจริงจะเกิดขึ้นเมื่อ `version` ใน `__manifest__.py` เป็น `19.0.2.0.0` แล้ว (Task 10) — ถ้ารัน `-u` ก่อนหน้านั้น สคริปต์จะไม่ถูกเรียกและจะเห็น log `no legacy threshold column found` ในฐานข้อมูลที่ผ่าน Task 7 ไปแล้วเท่านั้น

- [ ] **Step 6: Commit**

```powershell
git add custom_addons/od19_dashboard/migrations custom_addons/od19_dashboard/tests/__init__.py custom_addons/od19_dashboard/tests/test_dashboard_migration.py
git commit -m "feat(od19_dashboard): migrate the widget thresholds into status rules"
```

---

### Task 10: Re-seed the sample dashboards and publish version 19.0.2.0.0

**Goal:** ให้การติดตั้งใหม่ได้ widget ตัวอย่างที่ใช้ **กฎสถานะ** แทน threshold เดิม พร้อมสาธิตสูตร preset อย่างน้อย 1 widget (สเปก §9, §12) และให้ฐานข้อมูลเดิมที่ยังมี threshold ถูกอัปเกรดจริงผ่านสคริปต์ migration ของ Task 9 โดยไม่เหลือการอ้างถึงฟิลด์ที่ถอดออกแล้วในโค้ด วิว และไฟล์ข้อมูล

**Files:**
- Modify: `custom_addons/od19_dashboard/data/dashboard_data.xml`
- Modify: `custom_addons/od19_dashboard/__manifest__.py`
- Modify: `custom_addons/od19_dashboard/views/dashboard_views.xml`

**Precondition:** Task 9 เสร็จแล้ว (`migrations/19.0.2.0.0/pre-migrate.py` และ `post-migrate.py` มีอยู่จริง) และยังมีสำเนา `odoo19_dashboard_baseline` ที่ **ยังไม่ถูกอัปเดตโมดูล** จาก Task 7 Step 7a

**Design Decisions ของ task นี้:**

> **1. `data/dashboard_data.xml` ถูกประกาศด้วย `noupdate="1"`** — การแก้ seed จึงมีผลกับ **การติดตั้งใหม่เท่านั้น** record ที่มี `ir.model.data` อยู่แล้วจะไม่ถูกเขียนทับ นี่คือเหตุผลที่ต้องมี migration แยกต่างหากใน Task 9 การแก้ seed ยังจำเป็นอยู่ดี เพราะห้ามเหลือฟิลด์ `threshold_mode` / `warning_value` / `critical_value` ในไฟล์ข้อมูล (โมเดลไม่มีฟิลด์เหล่านี้อีกแล้ว) มิฉะนั้นการติดตั้งใหม่จะล้มด้วย `Invalid field ... on model od19.dashboard.widget`

> **2. ใช้ operator และ sequence ชุดเดียวกับ `RULE_SPECS` ใน Task 9** — `higher_is_better` → red `<=` critical (sequence 10) + yellow `<=` warning (sequence 20); `lower_is_better` → red `>=` critical (sequence 10) + yellow `>=` warning (sequence 20) เพื่อให้ผลของ fresh install เหมือนกับผลของ upgraded database เป๊ะ (สเปก §12 ข้อ "widget เดิมยังแสดงสีเดิม")

> **3. สาธิตสูตร preset ด้วย widget ใหม่ ไม่ใช่ widget เดิม** — `percent_of_goal` เปลี่ยนหน่วยของค่าที่แสดง (จากสกุลเงิน/จำนวน เป็นเปอร์เซ็นต์) จึงไม่ควรเขียนทับความหมายของ widget ตัวอย่างเดิมที่ผู้ใช้อาจปรับแต่งไปแล้ว จึงเพิ่ม widget `dashboard_owner_revenue_goal` บนแดชบอร์ด Owner ที่ `value_format = percent`, `formula_mode = preset`, `formula_type = percent_of_goal`, `formula_slots = {"a": "amount_total"}` และมี `goal_value` ของตัวเอง (สเปก §12 ข้อ 1) และให้ `sequence = 45` เพื่อไม่รบกวนแถว KPI เดิม (10 / 20 / 30 / 40)

> **4. กฎของ widget สาธิตสูตรใช้ `compare_type = constant` ไม่ใช่ `percent_of_goal`** — ค่าของ widget นี้เป็น "เปอร์เซ็นต์" อยู่แล้ว (เช่น `105.3`) แต่ `percent_of_goal` ของ rule engine คืน `goal × percent ÷ 100` ซึ่งเป็นหน่วยสกุลเงิน (เช่น `1,200,000`) การเทียบสองหน่วยนี้จะไม่มีความหมาย จึงใช้ค่าคงที่ 80 / 100 บนสเกลเปอร์เซ็นต์แทน **ข้อควรทราบ:** `compare_type = percent_of_goal` ใช้กับ widget ที่ค่าดิบยังเป็นจำนวนเงิน/จำนวน ไม่ใช่กับ widget ที่สูตรคืนค่าเป็นเปอร์เซ็นต์แล้ว

> **5. ไม่มี `post_init_hook`** — การติดตั้งใหม่ได้ค่า default จาก field definition และจาก seed ในไฟล์ข้อมูล ไม่ต้องมี hook (สอดคล้องกับสเปก §9 ข้อ 3)

---

- [ ] **Step 1: Replace the seeded thresholds with status rules**

แก้ `custom_addons/od19_dashboard/data/dashboard_data.xml` ทั้ง 4 record ที่ยังใช้ threshold (`dashboard_owner_revenue` บรรทัด 19–36, `dashboard_owner_receivables` 37–54, `dashboard_owner_late_delivery` 69–86, `dashboard_operational_late` 296–313) โดย**ลบ** `<field name="threshold_mode">`, `<field name="warning_value">`, `<field name="critical_value">` ออก และ**เพิ่ม** `rule_ids` แทน

`dashboard_owner_revenue` — คงฟิลด์อื่นไว้เหมือนเดิม แล้วเพิ่ม `rule_ids` ต่อจาก `sequence`:

```xml
        <field name="rule_ids" eval="[(0, 0, {'sequence': 10, 'name': 'Below the critical value', 'operator': '&lt;=', 'compare_type': 'constant', 'compare_value': 200000.0, 'status': 'red'}), (0, 0, {'sequence': 20, 'name': 'Below the warning value', 'operator': '&lt;=', 'compare_type': 'constant', 'compare_value': 500000.0, 'status': 'yellow'})]"/>
```

`dashboard_owner_receivables`:

```xml
        <field name="rule_ids" eval="[(0, 0, {'sequence': 10, 'name': 'Above the critical value', 'operator': '&gt;=', 'compare_type': 'constant', 'compare_value': 800000.0, 'status': 'red'}), (0, 0, {'sequence': 20, 'name': 'Above the warning value', 'operator': '&gt;=', 'compare_type': 'constant', 'compare_value': 300000.0, 'status': 'yellow'})]"/>
```

`dashboard_owner_late_delivery` และ `dashboard_operational_late` (ค่าเดียวกันทั้งสอง record):

```xml
        <field name="rule_ids" eval="[(0, 0, {'sequence': 10, 'name': 'Above the critical value', 'operator': '&gt;=', 'compare_type': 'constant', 'compare_value': 10.0, 'status': 'red'}), (0, 0, {'sequence': 20, 'name': 'Above the warning value', 'operator': '&gt;=', 'compare_type': 'constant', 'compare_value': 3.0, 'status': 'yellow'})]"/>
```

> ในไฟล์ XML ต้องเลี่ยง `<` ตรง ๆ ในค่า attribute จึงเขียน `&lt;=` (ส่วน `&gt;=` เขียนเป็น `&gt;=` ได้เช่นกันเพื่อความอ่านง่าย) และห้ามใส่ `threshold_mode` แบบ `eval="..."` กลับเข้าไปอีก

- [ ] **Step 2: Add the preset-formula sample widget**

แทรก record ใหม่ใน `custom_addons/od19_dashboard/data/dashboard_data.xml` ต่อจาก `dashboard_owner_late_delivery` (ก่อน `dashboard_owner_revenue_trend`):

```xml
    <record id="dashboard_owner_revenue_goal" model="od19.dashboard.widget">
        <field name="dashboard_id" ref="dashboard_owner"/>
        <field name="name">Revenue vs Goal</field>
        <field name="subtitle">Confirmed sales orders as a percentage of the monthly goal</field>
        <field name="widget_type">kpi</field>
        <field name="value_format">percent</field>
        <field name="source_id" ref="source_sale_order"/>
        <field name="measure_key">amount_total</field>
        <field name="date_key">date_order</field>
        <field name="date_range">this_month</field>
        <field name="goal_value" eval="1500000"/>
        <field name="formula_mode">preset</field>
        <field name="formula_type">percent_of_goal</field>
        <field name="formula_slots">{"a": "amount_total"}</field>
        <field name="show_delta" eval="False"/>
        <field name="grid_w" eval="3"/>
        <field name="grid_h" eval="2"/>
        <field name="sequence" eval="45"/>
        <field name="rule_ids" eval="[(0, 0, {'sequence': 10, 'name': 'Under 80% of the goal', 'operator': '&lt;=', 'compare_type': 'constant', 'compare_value': 80.0, 'status': 'red'}), (0, 0, {'sequence': 20, 'name': 'Under the goal', 'operator': '&lt;=', 'compare_type': 'constant', 'compare_value': 100.0, 'status': 'yellow'})]"/>
    </record>
```

> `formula_slots` เป็น `fields.Text` ที่เก็บ JSON จึงเขียนเป็น **ข้อความตรง** ใน element ไม่ใช่ `eval=` (ถ้าใช้ `eval="{'a': 'amount_total'}"` Odoo จะเก็บเป็น Python repr ที่มี single quote และ `json.loads()` จะล้มเหลว)

- [ ] **Step 3: Bump the module version and refresh the manifest description**

ใน [__manifest__.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_dashboard/__manifest__.py) แก้ `"version"` (บรรทัด 4) เป็น `"19.0.2.0.0"` และแทน bullet เดิม

```
* KPI widgets inherit the red / yellow / green / grey status model from
  ``kpi-reporting-baseline.md`` through per-widget thresholds.
```

ด้วย

```
* KPI status rules are a reorderable first-match-wins table that compares the
  widget value with a constant, a goal, a percentage of the goal, another
  widget of the same dashboard, or a shifted period (previous, YtY, MtM, QtQ).
* Formula engine: 14 preset formulas (ratio, difference, growth, share, sum,
  average, weighted average, percent of goal, min, max, cumulative change, run
  rate, conversion rate, variance), a free-text expression evaluated through
  ``safe_eval``, and per-group evaluation on bar / line / pie charts.
* Live preview in the builder shows the resulting value and the number of
  records the widget would collect before the widget is saved.
```

> `version` ต้องเป็น `19.0.2.0.0` ให้ตรงกับชื่อโฟลเดอร์ `migrations/19.0.2.0.0/` มิฉะนั้น Odoo จะไม่รันสคริปต์ migration

- [ ] **Step 4: Refresh the action help text**

ใน `custom_addons/od19_dashboard/views/dashboard_views.xml` เปลี่ยนข้อความ help ของ `action_od19_dashboard_manage` (บรรทัด 101–105) เป็น:

```xml
            <p>
                Build a dashboard from the pre-defined data sources, then design it
                with the in-browser builder: add widgets, drag to reorder, resize and
                define status rules (red / yellow / green) or a formula combining
                several measures.
            </p>
```

- [ ] **Step 5: Check the edited files**

```powershell
foreach ($file in @("custom_addons\od19_dashboard\data\dashboard_data.xml", "custom_addons\od19_dashboard\views\dashboard_views.xml")) {
    $null = [xml](Get-Content -Raw $file)
    Write-Host "OK $file"
}
```

Expected: `OK custom_addons\od19_dashboard\data\dashboard_data.xml` และ `OK custom_addons\od19_dashboard\views\dashboard_views.xml` (ไม่มี exception จาก XML parser)

จากนั้นตรวจว่าไม่มีโค้ดหรือข้อมูลใดอ้างถึงฟิลด์ที่ถอดออกแล้ว:

```powershell
git grep -n "threshold" -- custom_addons/od19_dashboard/models custom_addons/od19_dashboard/views custom_addons/od19_dashboard/data custom_addons/od19_dashboard/static
```

Expected: **ไม่มีผลลัพธ์เลย** (ที่ยังเหลือเฉพาะคำว่า threshold ใน `migrations/19.0.2.0.0/pre-migrate.py` และ `tests/test_dashboard_migration.py` ซึ่งอยู่นอก scope ของคำสั่งนี้)

- [ ] **Step 6: Upgrade the untouched copy to prove the migration runs**

ก่อนอัปเดต ให้ยืนยันว่าสำเนายังมี threshold เดิมอยู่จริง:

```powershell
$env:PGPASSWORD = "<your-db-password>"
psql -h localhost -p 5432 -U odoo -d odoo19_dashboard_baseline -c "SELECT COUNT(*) AS widgets_with_thresholds FROM od19_dashboard_widget WHERE threshold_mode IS NOT NULL AND threshold_mode <> 'none';"
```

Expected: `4`

```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19_dashboard_baseline -u od19_dashboard --stop-after-init --log-level=info
```

Expected: EXITCODE 0 และ log มีข้อความจากสคริปต์ migration:

```
od19_dashboard: backed up 4 widget thresholds
od19_dashboard: created 1 'red' rules for 'higher_is_better' widgets
od19_dashboard: created 1 'yellow' rules for 'higher_is_better' widgets
od19_dashboard: created 2 'red' rules for 'lower_is_better' widgets
od19_dashboard: created 2 'yellow' rules for 'lower_is_better' widgets
```

> `-d odoo19_dashboard_baseline` ใช้งานได้แม้ `odoo.conf` ตั้ง `dbfilter = ^odoo19$` เพราะตัวกรองนี้ถูกใช้เฉพาะชั้น HTTP (`odoo/http.py:db_filter`) ส่วน CLI ส่งชื่อฐานข้อมูลเข้า `server.start(preload=...)` ตรง ๆ ไม่ผ่านตัวกรอง

ตรวจผลลัพธ์หลังอัปเดต (3 คำสั่ง):

```powershell
psql -h localhost -p 5432 -U odoo -d odoo19_dashboard_baseline -c "SELECT w.name, r.sequence, r.operator, r.compare_value, r.status FROM od19_dashboard_widget_rule r JOIN od19_dashboard_widget w ON w.id = r.widget_id ORDER BY w.name, r.sequence;"
psql -h localhost -p 5432 -U odoo -d odoo19_dashboard_baseline -c "SELECT to_regclass('od19_dashboard_threshold_backup') AS backup_table;"
psql -h localhost -p 5432 -U odoo -d odoo19_dashboard_baseline -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'od19_dashboard_widget' AND column_name IN ('threshold_mode', 'warning_value', 'critical_value');"
```

Expected:
1. **8 แถว** (2 กฎ × 4 widget) โดย `Revenue (This Month)` มี `<= 200000 red` แล้ว `<= 500000 yellow`; `Outstanding Receivables`, `Overdue Deliveries`, `Late Deliveries` มี `>= critical red` แล้ว `>= warning yellow`
2. `backup_table` เป็นค่าว่าง (NULL) — ตารางชั่วคราวถูก `DROP` แล้ว
3. **0 แถว** — คอลัมน์ threshold ถูกลบแล้ว

> ⚠️ หลัง Step นี้ สำเนา `odoo19_dashboard_baseline` ไม่มี threshold เดิมอีกต่อไป ถ้าต้องรันซ้ำให้สร้างสำเนาใหม่จาก Task 7 Step 7a (แต่ต้องทำบนฐานข้อมูลที่ยังมี threshold เท่านั้น)

- [ ] **Step 7: Upgrade the development database**

```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 -u od19_dashboard --stop-after-init --log-level=info
```

Expected: EXITCODE 0 และ log มี

```
od19_dashboard: no legacy threshold column found, nothing to back up
od19_dashboard: no threshold backup table, nothing to convert
```

> ทั้งสองบรรทัดเป็นผลที่ถูกต้องสำหรับฐานข้อมูลพัฒนา เพราะ Task 7 Step 7 รัน `-u` ไปแล้วครั้งหนึ่งและลบคอลัมน์ threshold ทิ้งไปก่อนที่สคริปต์ migration จะมีอยู่ ส่วน `_set_widget_defaults()` ยังทำงานและเติมค่า `formula_mode = 'measure'` / `delta_basis = 'previous'` ให้ widget เดิมทุกแถว ตรวจว่าไม่มี warning ใหม่ใน `odoo_server.log` — โดยเฉพาะ `unable to set the null value` และ `Invalid field`

> **widget ตัวอย่างบนฐานข้อมูลพัฒนาจะไม่มีกฎสถานะ** — record เหล่านั้นถูกสร้างตั้งแต่เวอร์ชันก่อนและมี `noupdate="1"` จึงไม่ถูกเขียนทับด้วย seed ใหม่ และ threshold ของมันหายไปตั้งแต่ Task 7 Step 7 ก่อนที่ Task 9 จะมีสคริปต์ migration ดังนั้น widget เหล่านั้นจะแสดง `default_status` (เขียว) แทนสีเดิม ถ้าต้องการให้ตรงกับ seed ใหม่ ให้ **ลบ widget ตัวอย่างผ่าน UI** (Dashboards → เปิดแดชบอร์ดตัวอย่าง → ลบ widget) แล้วรันคำสั่ง `-u` ข้างบนซ้ำ — Odoo จะสร้าง record ใหม่จาก seed ที่อัปเดตแล้ว เพราะการลบผ่าน UI ล้างแถวใน `ir.model.data` ให้ด้วย

- [ ] **Step 8: Commit**

```powershell
git add custom_addons/od19_dashboard/data/dashboard_data.xml custom_addons/od19_dashboard/__manifest__.py custom_addons/od19_dashboard/views/dashboard_views.xml
git commit -m "feat(od19_dashboard): seed formulas and status rules and release 19.0.2.0.0"
```

---

### Task 11: Close the cycle-validation gap and verify the release end to end

**Goal:** ปิดช่องว่างที่เหลือระหว่างสเปกกับโค้ด — สเปก §10.2 กำหนดว่า "cycle detection → `ValidationError`" และ §11 ระบุให้ "ตรวจ topological ตอนบันทึก" แต่ Task 5 ทำเฉพาะ fail-soft ตอนแสดงผล — จากนั้นพิสูจน์เกณฑ์ความสำเร็จตามสเปก §10.1 / §10.2 / §10.3 และ §12 ด้วยการติดตั้งใหม่บนฐานข้อมูลสะอาด การอัปเกรด และการตรวจ front-end

**Files:**
- Modify: `custom_addons/od19_dashboard/models/dashboard.py` (เพิ่ม `_check_no_cycle()` และ constrain)
- Modify: `custom_addons/od19_dashboard/tests/test_dashboard_engine.py` (เพิ่มคลาส `TestDashboardAcceptance`)

**Precondition:** Task 1–10 เสร็จแล้ว — โดยเฉพาะ Task 6 (`preview_widget`) และ Task 5 (`_dependency_ids`, `_compute_order`)

**Design Decisions ของ task นี้:**

> **1. ตรวจวัฏจักรสองระดับตามที่สเปก §11 ระบุไว้** — ตอน **บันทึก** ต้อง error เพื่อไม่ให้ผู้ใช้ออกแบบแดชบอร์ดที่คำนวณไม่ได้ (ไม่มีทางแก้ทีหลังได้เอง) ส่วนตอน **แสดงผล** ต้อง fail-soft เพื่อไม่ให้แดชบอร์ดที่เสียหายอยู่แล้วล้มทั้งหน้า `_compute_order()` ที่ Task 5 เขียนไว้ทำหน้าที่ฝั่งหลังอยู่แล้ว งานนี้จึงเพิ่มเฉพาะฝั่งบันทึก
> **2. `_check_no_cycle()` อยู่บน `od19.dashboard`** — วัฏจักรเป็นสมบัติของทั้งแดชบอร์ด ไม่ใช่ของ widget เดี่ยว การตรวจบนแดชบอร์ดทำให้ constrain ตัวเดียวครอบทุกเส้นทางที่แก้กราฟได้ (เพิ่ม/ลบ widget, แก้ `formula_expression`, เพิ่ม/ลบ rule) และใช้ `_dependency_ids()` ชุดเดียวกับ `_compute_order()` จึงไม่มีการตีความกราฟสองแบบ
> **3. constrain ประกาศบน `formula_mode`, `formula_expression`, `rule_ids`** — สามฟิลด์นี้คือทุกทางที่ทำให้เกิดเส้นเชื่อมใหม่ (`rule_ids` ครอบ `compare_widget_id` ด้วย เพราะเป็นลูกของ widget) และไม่ต้องพึ่ง `compare_widget_id` ของ rule โดยตรง
> **4. เทสต์ acceptance สร้างข้อมูลจริง 1 รายการ แทนการใช้ข้อมูลที่มีอยู่ในฐานข้อมูล** — เพื่อให้สูตรที่หารด้วยค่าวัด (`ratio`, `growth`, `conversion_rate`, `share`, `weighted_average`, `percent_of_goal`) ไม่ล้มด้วยการหารด้วยศูนย์ และใช้ `sale.order` สถานะ `draft` ที่มี 1 บรรทัดราคา 100 × 2 ชิ้น → `amount_total = amount_untaxed = 200.0`, `count_records = 1` โดยไม่ต้องยืนยันคำสั่งขาย (จึงไม่มี side effect กับสต็อกหรือใบแจ้งหนี้)
> **5. ใช้ `date_range = "this_month"` ไม่ใช่ `all_time`** — สูตร `run_rate` ต้องมีช่วงเวลาที่มีขอบเขต (`_run_rate_days()` คืน `None` เมื่อไม่มีขอบเขต) การทดสอบด้วย `all_time` จะทำให้ `run_rate` ล้มด้วยเหตุผลของช่วงเวลา ไม่ใช่ของสูตร

---

- [ ] **Step 1: Write the failing acceptance tests**

ต่อท้าย `custom_addons/od19_dashboard/tests/test_dashboard_engine.py`:

```python
class TestDashboardAcceptance(TransactionCase):
    """Acceptance checks of spec section 10.2 no earlier task covered."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dashboard = cls.env["od19.dashboard"].create({"name": "Acceptance dashboard"})
        cls.source = cls.env.ref("od19_dashboard.source_sale_order")
        partner = cls.env["res.partner"].create({"name": "Acceptance customer"})
        product = cls.env["product.product"].create(
            {"name": "Acceptance product", "list_price": 100.0}
        )
        cls.order = cls.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "order_line": [
                    (0, 0, {"product_id": product.id, "product_uom_qty": 2.0})
                ],
            }
        )

    def _values(self, **extra):
        values = {
            "dashboard_id": self.dashboard.id,
            "name": "Acceptance widget",
            "widget_type": "kpi",
            "source_id": self.source.id,
            "measure_key": "__count",
            "date_key": "date_order",
            "date_range": "this_month",
            "goal_value": 10.0,
        }
        values.update(extra)
        return values

    def _preview(self, **extra):
        return self.env["od19.dashboard.widget"].preview_widget(
            self._values(**extra), date_range="this_month"
        )

    def test_every_preset_formula_returns_a_number(self):
        slots_by_type = {
            "ratio": {"a": "__count", "b": "amount_total"},
            "difference": {"a": "amount_total", "b": "amount_untaxed"},
            "growth": {"a": "amount_total", "b": "amount_untaxed"},
            "share": {"a": "amount_total"},
            "sum": {"a": "amount_total", "b": "amount_untaxed"},
            "average": {"a": "amount_total", "b": "amount_untaxed"},
            "weighted_average": {"a": "amount_total", "b": "amount_untaxed", "w1": 2, "w2": 1},
            "percent_of_goal": {"a": "amount_total"},
            "min": {"a": "amount_total", "b": "amount_untaxed"},
            "max": {"a": "amount_total", "b": "amount_untaxed"},
            "cumulative_change": {"a": "amount_total"},
            "run_rate": {"a": "amount_total"},
            "conversion_rate": {"a": "__count", "b": "amount_total"},
            "variance": {"a": "amount_total", "b": "amount_untaxed"},
        }
        for formula_type, slots in slots_by_type.items():
            result = self._preview(
                formula_mode="preset",
                formula_type=formula_type,
                formula_slots=json.dumps(slots),
            )
            self.assertIsInstance(result["value"], (int, float), formula_type)
            self.assertGreaterEqual(result["record_count"], 1, formula_type)

    def test_count_records_alias_works(self):
        result = self._preview(formula_mode="custom", formula_expression="count_records")
        self.assertEqual(result["value"], 1)

    def test_simple_slots_match_direct_names(self):
        with_slots = self._preview(
            formula_mode="custom",
            formula_expression="a + b",
            formula_slots=json.dumps({"a": "amount_total", "b": "amount_untaxed"}),
        )
        with_names = self._preview(
            formula_mode="custom",
            formula_expression="amount_total + amount_untaxed",
        )
        self.assertEqual(with_slots["value"], with_names["value"])
        self.assertEqual(with_slots["value"], 400.0)

    def test_cross_widget_value_matches_the_source_widget(self):
        source_widget = self.env["od19.dashboard.widget"].create(
            self._values(name="Source widget", formula_mode="custom", formula_expression="count_records")
        )
        reader_widget = self.env["od19.dashboard.widget"].create(
            self._values(
                name="Reader widget",
                formula_mode="custom",
                formula_expression="widget_%s * 2" % source_widget.id,
            )
        )
        data = self.env["od19.dashboard"].get_dashboard_data(
            self.dashboard.id, date_range="this_month"
        )
        values = {widget["id"]: widget["value"] for widget in data["widgets"]}
        self.assertEqual(values[source_widget.id], 1)
        self.assertEqual(values[reader_widget.id], 2)

    def test_cycle_is_refused_on_save(self):
        widget_a = self.env["od19.dashboard.widget"].create(
            self._values(name="Cycle A", formula_mode="custom", formula_expression="count_records")
        )
        widget_b = self.env["od19.dashboard.widget"].create(
            self._values(name="Cycle B", formula_mode="custom", formula_expression="count_records")
        )
        widget_a.formula_expression = "count_records + widget_%s" % widget_b.id
        with self.assertRaises(ValidationError):
            widget_b.formula_expression = "count_records + widget_%s" % widget_a.id

    def test_builder_rpc_refuses_a_user_without_write_access(self):
        widget = self.env["od19.dashboard.widget"].create(self._values(name="Protected widget"))
        stranger = self.env["res.users"].create(
            {
                "name": "Acceptance stranger",
                "login": "od19_dashboard_acceptance_stranger",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        with self.assertRaises(AccessError):
            self.env["od19.dashboard"].with_user(stranger).update_widget(
                widget.id, {"name": "Hijacked"}
            )

    def test_operands_do_not_add_aggregation_queries(self):
        """Spec 10.2: operands must be batched into one aggregation per domain.

        ``_record_count`` legitimately runs its own aggregation, so the check
        compares two formulas with a different number of slots instead of
        hard-coding a call count.
        """
        model = type(self.env["sale.order"])
        original = model._read_group
        calls = []

        def counting_read_group(recordset, *args, **kwargs):
            calls.append(recordset._name)
            return original(recordset, *args, **kwargs)

        model._read_group = counting_read_group
        try:
            self._preview(formula_mode="custom", formula_expression="amount_total")
            one_slot = len(calls)
            calls.clear()
            self._preview(
                formula_mode="custom",
                formula_expression="a + b + c + d",
                formula_slots=json.dumps(
                    {
                        "a": "amount_total",
                        "b": "amount_untaxed",
                        "c": "amount_total",
                        "d": "amount_untaxed",
                    }
                ),
            )
            four_slots = len(calls)
        finally:
            model._read_group = original
        self.assertEqual(
            four_slots,
            one_slot,
            "Four operand slots must reuse the aggregation of a single slot.",
        )
```

และตรวจว่า `custom_addons/od19_dashboard/tests/test_dashboard_engine.py` มี import ครบ (ถ้ายังไม่มีให้เพิ่มที่หัวไฟล์):

```python
import json

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase
```

> `test_simple_slots_match_direct_names` ยังยืนยันค่าจริง `400.0` = `amount_total (200) + amount_untaxed (200)` ของคำสั่งขาย draft 1 ใบที่สร้างใน `setUpClass` — ถ้าค่าเป็นอย่างอื่นนอกจาก 400.0 แปลว่ามีข้อมูลคำสั่งขายอื่นในเดือนเดียวกันปนเข้ามา ให้แก้ให้เทสต์เทียบกันเองระหว่างสองเส้นทาง (ตัด `assertEqual(..., 400.0)` ออก) แทนการลบข้อมูล

- [ ] **Step 2: Run the tests to verify they fail**

```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 -u od19_dashboard --test-enable --test-tags /od19_dashboard --stop-after-init --log-level=test
```

Expected: FAIL เฉพาะ `TestDashboardAcceptance.test_cycle_is_refused_on_save` ด้วย `AssertionError: ValidationError not raised` — เทสต์อื่นในคลาสนี้ต้องผ่าน (ถ้ามีตัวอื่นล้ม ให้แก้สูตร/ช่วงเวลาในเทสต์ก่อน ไม่ใช่แก้โค้ดโมดูล)

- [ ] **Step 3: Add the cycle validation**

แทรกในคลาส `Od19Dashboard` ต่อจาก `_compute_order` ใน `custom_addons/od19_dashboard/models/dashboard.py`:

```python
    def _check_no_cycle(self):
        """Refuse a widget graph that never settles (spec section 11).

        ``_compute_order()`` resolves the same edges but fails soft at render
        time; saving must fail hard so an unsolvable dashboard is never stored.
        """
        self.ensure_one()
        pending = {widget.id: widget for widget in self.widget_ids.filtered("active")}
        resolved = set()
        while pending:
            ready = [
                widget
                for widget in pending.values()
                if all(dependency not in pending for dependency in widget._dependency_ids())
            ]
            if not ready:
                names = ", ".join(
                    sorted(widget.name or str(widget.id) for widget in pending.values())
                )
                raise ValidationError(
                    _(
                        "These widgets read each other in a loop: %s. "
                        "Remove one of the references so the values can be computed."
                    )
                    % names
                )
            for widget in ready:
                resolved.add(widget.id)
                pending.pop(widget.id)
```

และแทรก constrain ในคลาส `Od19DashboardWidget` ต่อจาก `_evaluate_rules`:

```python
    @api.constrains("formula_mode", "formula_expression", "rule_ids")
    def _check_dependency_cycle(self):
        for widget in self:
            if widget.dashboard_id:
                widget.dashboard_id._check_no_cycle()
```

- [ ] **Step 4: Run the tests to verify they pass**

```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 -u od19_dashboard --test-enable --test-tags /od19_dashboard --stop-after-init --log-level=test
```

Expected: PASS ทุกคลาส รวม `TestDashboardAcceptance` ทั้ง 7 เทสต์ — และ `TestDashboardOrdering.test_compute_order_survives_a_cycle` ต้องยังผ่าน (เทสต์นั้นเขียน `formula_expression` ผ่าน `write()` ซึ่งตอนนี้จะ **raise** แล้ว) **ถ้าล้มด้วย `ValidationError` ให้แก้เทสต์นั้นให้ใช้ `self.env.cr.execute(...)` เขียนคอลัมน์ตรง ๆ หรือห่อด้วย `self.assertRaises(ValidationError)`** เพราะพฤติกรรมที่ถูกต้องตามสเปก §11 คือการปฏิเสธวัฏจักรตอนบันทึก

- [ ] **Step 5: Fresh install on a clean database (spec 10.1)**

```powershell
$env:PGPASSWORD = "<your-db-password>"
dropdb -h localhost -p 5432 -U odoo --if-exists odoo19_dashboard_fresh
createdb -h localhost -p 5432 -U odoo odoo19_dashboard_fresh
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19_dashboard_fresh -i od19_dashboard --without-demo=all --stop-after-init --log-level=info
```

Expected: EXITCODE 0 และ log **ไม่มี** ข้อความจากสคริปต์ migration เลย (การติดตั้งใหม่ไม่มี `installed_version` จึงไม่รัน `migrations/`)

ตรวจว่า seed ใหม่ลงครบ:

```powershell
psql -h localhost -p 5432 -U odoo -d odoo19_dashboard_fresh -c "SELECT COUNT(*) AS rules FROM od19_dashboard_widget_rule;"
psql -h localhost -p 5432 -U odoo -d odoo19_dashboard_fresh -c "SELECT name, formula_mode, formula_type, formula_slots FROM od19_dashboard_widget WHERE formula_mode <> 'measure';"
psql -h localhost -p 5432 -U odoo -d odoo19_dashboard_fresh -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'od19_dashboard_widget' AND column_name LIKE '%threshold%';"
```

Expected: `rules` = **10**; มี 1 แถวชื่อ `Revenue vs Goal` ที่ `formula_mode = preset`, `formula_type = percent_of_goal`, `formula_slots = {"a": "amount_total"}`; 0 แถว (ไม่มีคอลัมน์ threshold ตั้งแต่แรก)

ตรวจว่า log ของการติดตั้งใหม่ไม่มี warning ใหม่ (โดยเฉพาะ `WARNING` ที่เกี่ยวกับ `od19_dashboard`):

```powershell
Select-String -Path odoo_server.log -Pattern "WARNING.*od19_dashboard|ERROR.*od19_dashboard" | Select-Object -Last 20
```

Expected: ไม่มีผลลัพธ์

- [ ] **Step 6: Front-end checks (spec 10.3)**

```powershell
node --check custom_addons/od19_dashboard/static/src/dashboard/builder_dialog.js
node --check custom_addons/od19_dashboard/static/src/dashboard/dashboard_action.js
git grep -n "static template = \"" -- custom_addons/od19_dashboard/static/src/dashboard
git grep -n "t-name=\"" -- custom_addons/od19_dashboard/static/src/dashboard
```

Expected: ทั้งสอง `node --check` ออกด้วย exit code 0 (ไม่มี output) และรายชื่อ template ใน JS ตรงกับ `t-name` ใน XML ทุกชื่อ

จากนั้นเปิดเซิร์ฟเวอร์ด้วย main script ของโครงการ แล้วตรวจว่า static asset ตอบ 200:

```powershell
Invoke-WebRequest -Uri "http://localhost:8070/od19_dashboard/static/src/dashboard/builder_dialog.js" -UseBasicParsing | Select-Object -ExpandProperty StatusCode
```

Expected: `200`

- [ ] **Step 7: Commit**

```powershell
git add custom_addons/od19_dashboard/models/dashboard.py custom_addons/od19_dashboard/tests/test_dashboard_engine.py
git commit -m "test(od19_dashboard): refuse widget dependency cycles and cover the acceptance criteria"
```

- [ ] **Step 8: Hand the manual acceptance checklist to the user**

สเปก §10.4 ต้องให้ผู้ใช้ทดสอบเอง (ไม่ทราบรหัส admin) — แจ้งเช็กลิสต์นี้พร้อมกับ URL `http://localhost:8070`:

1. Dashboards → My Dashboards → เปิดแดชบอร์ด Owner: `Revenue vs Goal` ต้องแสดงเป็นเปอร์เซ็นต์ และมีสีตามกฎที่ seed ไว้
2. กด Customize → Add widget → เลือก **Preset formula** → `Revenue vs Goal (percent_of_goal)` → **Live Preview** ต้องแสดงค่าที่เป็นตัวเลขและจำนวน record ที่จะเก็บได้ ก่อนกด Save
3. เลือก **Custom expression** → พิมพ์ `amount_total / count_records` → Preview ต้องได้ตัวเลข และพิมพ์ `__count` ต้องได้ข้อความ error ที่แนะนำให้ใช้ `count_records`
4. เพิ่ม 2 กฎสถานะที่เข้าเงื่อนไขพร้อมกัน → ผลต้องเป็นสีของกฎที่อยู่บนสุด → ลากสลับลำดับ → สีต้องเปลี่ยนตาม
5. ตั้งกฎที่เทียบกับ **Same period last year** และ **Previous month** → Preview ต้องได้ค่าที่สมเหตุสมผล
6. สร้าง widget ที่ fórmula อ้าง `widget_<id>` ของ widget อื่นในแดชบอร์ดเดียวกัน → ค่าต้องตรงกับ widget ต้นทาง
7. ใส่สูตรที่ผิด (เช่น `a / 0`) → widget นั้นต้องแสดง `—` พร้อมคำอธิบาย ส่วน widget อื่นบนแดชบอร์ดต้องทำงานปกติ
8. บนกราฟ bar / line / pie ที่ใช้ preset formula → ต้องได้ค่าต่อกลุ่ม (per-group) ไม่ใช่ค่าเดียว

- [ ] **Step 9: Stop and review**

หยุดที่ขั้นนี้ — รายงานผลต่อผู้ใช้ (ผ่าน / ไม่ผ่าน / ข้อสังเกต) ก่อนเริ่ม Phase 2 (ซ่อน/แสดง widget, ข้อความเตือนตามเงื่อนไข, conditional formatting) ซึ่งอยู่นอกขอบเขตของ plan นี้

---
