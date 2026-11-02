# แผนดำเนินงาน: คำขอเปิดบิลกลาง (Unified Billing Request) — od19_billing_request

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** สร้างโมดูล `od19_billing_request` ให้พนักงานคลัง/ขาย/จัดซื้อ "แจ้งเปิดบิล" (AR/AP) จากเอกสารต้นทางจริง (ใบ IN/OUT, SO, PO) แทนการพิมพ์ข้อความ + ก๊อปปี้รายการผ่าน `mail.activity` โดยออกเอกสารปลายทาง 1 ใบต่อ 1 คำขอ

**Architecture:** โมเดล `od19.billing.request` + `od19.billing.request.line` ทำหน้าที่เป็น "ซองคำขอ" ที่ inherit `od19.document.pull.mixin` เพื่อดึงบรรทัดจริงจากต้นทาง (ผ่าน wizard เดิมของ `od19_document_pull`) และต่อยอดหลักฐานจาก `od19_sales_billing_evidence` โดยไม่สร้างตารางหลักฐานซ้ำ บรรทัดที่ดึงมาเก็บตัวนับ `qty_already_requested` / `remaining_to_bill` เพื่อกันเปิดบิลซ้ำ/เกินยอด เมื่อออกบิลจะสร้าง `account.move` (`out_invoice` / `in_invoice`) และผูก `sale_line_ids` / `purchase_line_id` กลับไปยังบรรทัดต้นทาง

**Tech Stack:** Odoo 19 CE (custom addons `od19_*`), Python (ORM), XML views/data/security, PostgreSQL, unittest (`odoo.tests`), PowerShell `run-tests.ps1`

**Spec อ้างอิง:** [2026-11-02-od19-billing-request-design.md](../specs/2026-11-02-od19-billing-request-design.md)

**ข้อกำหนดสำคัญ (Freeze):** 1 คำขอ = 1 ต้นทาง = 1 บิล · โมดูลเดียว · AR 2 ขั้นใช้ `account.move` เดียว · แจ้งเตือนอย่างเดียว ไม่มีระบบอนุมัติ · นโยบาย AR กำหนดได้ต่อลูกค้า/ประเภทงาน

---

## File Structure

ไฟล์ทั้งหมดอยู่ใต้ `custom_addons/od19_billing_request/` (ยกเว้นไฟล์ที่แก้ในโมดูลเดิม)

| ไฟล์ | หน้าที่ |
|---|---|
| `__manifest__.py` | metadata + depends + data list |
| `__init__.py` | import `models`, `wizards` |
| `models/__init__.py` | import ทุกโมเดล |
| `models/billing_request.py` | โมเดลหลัก + flow + compensation + document pull contract |
| `models/billing_request_line.py` | บรรทัด + ตัวนับ + guards |
| `models/res_company.py` | config นโยบาย AR/AP ระดับบริษัท |
| `models/res_partner.py` | นโยบาย AR ระดับลูกค้า |
| `models/sale_order.py` | นโยบาย AR ระดับงาน (override) |
| `models/billing_evidence.py` | ขยาย `od19.billing.evidence` (+`billing_request_id`) และ `od19.billing.evidence.type` (+`requires_original`) |
| `wizards/__init__.py` | import wizard (ถ้ามี) |
| `security/od19_billing_request_security.xml` | กลุ่มสิทธิ์ + record rules |
| `security/ir.model.access.csv` | สิทธิ์ระดับโมเดล |
| `data/od19_billing_request_data.xml` | ประเภทหลักฐาน + ข้อมูลตั้งต้น |
| `views/billing_request_views.xml` | form/tree/kanban/search + actions |
| `views/billing_request_menus.xml` | เมนู + Billing Queue |
| `i18n/th.po` | คำแปลไทย |
| `tests/__init__.py` + `tests/test_*.py` | ชุดเทสต์ TDD |

> **หมายเหตุการปรับสูตรตัวนับ (จากสเปก §4.1):** `remaining_to_bill = qty_ordered − qty_already_requested` (ไม่หัก `qty_invoiced` ซ้ำ เพราะ `qty_already_requested` นับรวมคำขอที่ `invoiced` แล้ว) ส่วน `qty_invoiced` แสดงเป็นข้อมูลอ้างอิงเท่านั้น — ดู Risks Task 3

---

## Task 1: โครงโมดูล + โมเดลคำขอขั้นต้น + sequence

**Files:**
- Create: `custom_addons/od19_billing_request/__manifest__.py`
- Create: `custom_addons/od19_billing_request/__init__.py`
- Create: `custom_addons/od19_billing_request/models/__init__.py`
- Create: `custom_addons/od19_billing_request/models/billing_request.py`
- Create: `custom_addons/od19_billing_request/security/ir.model.access.csv`
- Create: `custom_addons/od19_billing_request/security/od19_billing_request_security.xml`
- Test: `custom_addons/od19_billing_request/tests/__init__.py`
- Test: `custom_addons/od19_billing_request/tests/test_billing_request_core.py`

- [ ] **Step 1: เขียนเทสต์ที่จะ fail**

สร้าง `tests/__init__.py`:

```python
from . import test_billing_request_core
```

สร้าง `tests/test_billing_request_core.py`:

```python
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBillingRequestCore(TransactionCase):
    def test_create_ar_request_gets_sequence(self):
        request = self.env["od19.billing.request"].create({"direction": "ar"})
        self.assertTrue(request.name.startswith("BRI/AR/"))
        self.assertEqual(request.state, "draft")

    def test_create_ap_request_gets_sequence(self):
        request = self.env["od19.billing.request"].create({"direction": "ap"})
        self.assertTrue(request.name.startswith("BRI/AP/"))

    def test_move_type_follows_direction(self):
        ar = self.env["od19.billing.request"].create({"direction": "ar"})
        ap = self.env["od19.billing.request"].create({"direction": "ap"})
        self.assertEqual(ar.move_type, "out_invoice")
        self.assertEqual(ap.move_type, "in_invoice")
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_billing_request`
Expected: FAIL — โมดูล `od19_billing_request` ยังไม่มี / `KeyError: 'od19.billing.request'`

- [ ] **Step 3: สร้าง manifest + init**

`__manifest__.py`:

```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "OD19 Billing Request (คำขอเปิดบิลกลาง)",
    "version": "19.0.1.0.0",
    "category": "Accounting",
    "summary": "Unified AR/AP billing request from IN/OUT/SO/PO",
    "author": "TRAE",
    "license": "LGPL-3",
    "depends": [
        "sale_management",
        "purchase",
        "stock",
        "account",
        "hr",
        "od19_sales_billing_evidence",
        "od19_document_pull",
    ],
    "data": [
        "security/od19_billing_request_security.xml",
        "security/ir.model.access.csv",
        "data/od19_billing_request_data.xml",
        "views/billing_request_views.xml",
        "views/billing_request_menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "icon": "/od19_billing_request/static/description/icon.svg",
}
```

`__init__.py`:

```python
from . import models
```

`models/__init__.py`:

```python
from . import billing_request
```

- [ ] **Step 4: เขียนโมเดลขั้นต้น (ยังไม่มีบรรทัด)**

`models/billing_request.py`:

```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
from odoo import _, api, fields, models


class Od19BillingRequest(models.Model):
    _name = "od19.billing.request"
    _description = "OD19 Billing Request"
    _inherit = ["mail.thread", "mail.activity.mixin", "od19.document.pull.mixin"]
    _order = "date_request desc, id desc"

    name = fields.Char(
        string="Number / เลขที่คำขอ", default="/", copy=False, readonly=True
    )
    direction = fields.Selection(
        [("ar", "AR - ลูกหนี้ / Customer"), ("ap", "AP - เจ้าหนี้ / Vendor")],
        string="Direction / ทิศทาง",
        required=True,
        default="ar",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("invoiced", "Invoiced"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        string="Status / สถานะ",
        default="draft",
        required=True,
        copy=False,
        tracking=True,
    )
    date_request = fields.Date(
        string="Request Date / วันที่แจ้ง",
        default=fields.Date.context_today,
        required=True,
    )
    note = fields.Text(string="Note / หมายเหตุ")

    # --- ผู้แจ้ง ---
    requested_by_id = fields.Many2one(
        "res.users",
        string="Requested By / ผู้แจ้ง",
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
    )
    requested_employee_id = fields.Many2one(
        "hr.employee",
        string="Requested Employee / พนักงานผู้แจ้ง",
        compute="_compute_requester_info",
        store=True,
        readonly=False,
    )
    department_id = fields.Many2one(
        "hr.department",
        string="Department / แผนก",
        compute="_compute_requester_info",
        store=True,
        readonly=False,
        index=True,
    )

    # --- ต้นทาง/ปลายทาง ---
    origin_ref = fields.Reference(
        selection="_selection_origin_ref",
        string="Origin / เอกสารต้นทาง",
        tracking=True,
    )
    origin_model = fields.Char(
        string="Origin Model",
        compute="_compute_origin_info",
        store=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Partner / คู่ค้า",
        compute="_compute_origin_info",
        store=True,
        readonly=False,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )
    currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id", string="Currency"
    )
    move_type = fields.Selection(
        [("out_invoice", "Customer Invoice"), ("in_invoice", "Vendor Bill")],
        string="Target Document Type",
        compute="_compute_move_type",
    )
    target_move_id = fields.Many2one(
        "account.move",
        string="Target Invoice/Bill / เอกสารปลายทาง",
        readonly=True,
        copy=False,
    )

    # --- นโยบาย AR ---
    ar_billing_mode = fields.Selection(
        [("direct", "Direct / ออกบิลเลย"), ("two_step", "Two Step / วางบิลก่อน")],
        string="AR Billing Mode / โหมดวางบิล AR",
        compute="_compute_ar_billing_mode",
        store=True,
        readonly=False,
    )

    # --- ต้นฉบับจริง (AP) ---
    original_received = fields.Boolean(
        string="Original Document Received / รับต้นฉบับจริงแล้ว", tracking=True
    )
    original_received_date = fields.Date(string="Original Received Date / วันที่รับต้นฉบับ")
    original_received_by_id = fields.Many2one(
        "res.users", string="Original Received By / ผู้รับต้นฉบับ"
    )

    reject_reason = fields.Text(string="Reject Reason / เหตุผลที่ตีกลับ")

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.model
    def _selection_origin_ref(self):
        return [
            ("stock.picking", _("Transfer / ใบรับ-ส่งสินค้า")),
            ("sale.order", _("Sale Order / ใบสั่งขาย")),
            ("purchase.order", _("Purchase Order / ใบสั่งซื้อ")),
        ]

    @api.model
    def _od19_employee_for_user(self, user):
        if not user:
            return self.env["hr.employee"]
        return user.sudo().employee_id

    @api.depends("requested_by_id")
    def _compute_requester_info(self):
        for request in self:
            employee = request._od19_employee_for_user(request.requested_by_id)
            request.requested_employee_id = employee
            request.department_id = employee.department_id if employee else False

    @api.depends("origin_ref")
    def _compute_origin_info(self):
        for request in self:
            origin = request.origin_ref
            request.origin_model = origin._name if origin else False
            if origin and not request.partner_id:
                request.partner_id = getattr(origin, "partner_id", False)

    @api.depends("direction")
    def _compute_move_type(self):
        for request in self:
            request.move_type = (
                "out_invoice" if request.direction == "ar" else "in_invoice"
            )

    @api.depends("direction", "partner_id", "origin_ref", "company_id")
    def _compute_ar_billing_mode(self):
        for request in self:
            mode = False
            origin = request.origin_ref
            if origin and origin._name == "sale.order":
                mode = origin.od19_ar_billing_mode
            if (not mode or mode == "default") and request.partner_id:
                mode = request.partner_id.od19_ar_billing_mode
            if not mode or mode == "default":
                mode = request.company_id.od19_ar_billing_mode_default or "direct"
            request.ar_billing_mode = mode

    # ------------------------------------------------------------------
    # Sequence
    # ------------------------------------------------------------------
    @api.model
    def _od19_get_billing_request_sequence(self, direction):
        """Return (creating on demand) the sequence for the given direction."""
        sequence_model = self.env["ir.sequence"].sudo()
        code = "od19.billing.request.%s" % (direction or "ar")
        prefix = "BRI/%s/" % (direction or "ar").upper()
        sequence = sequence_model.search([("code", "=", code)], limit=1)
        if not sequence:
            sequence = sequence_model.create(
                {
                    "name": "Billing Request %s" % (direction or "ar").upper(),
                    "code": code,
                    "prefix": prefix,
                    "padding": 5,
                    "company_id": False,
                }
            )
        return sequence

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == "/":
                direction = vals.get("direction") or "ar"
                vals["name"] = self._od19_get_billing_request_sequence(
                    direction
                ).next_by_id()
        return super().create(vals_list)
```

- [ ] **Step 5: สร้าง security (กลุ่มสิทธิ์ + access)**

`security/od19_billing_request_security.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="module_category_od19_billing_request" model="ir.module.category">
        <field name="name">Billing Request</field>
        <field name="sequence">92</field>
    </record>

    <record id="privilege_od19_billing_request" model="res.groups.privilege">
        <field name="name">Billing Request</field>
        <field name="category_id" ref="module_category_od19_billing_request"/>
    </record>

    <record id="group_od19_billing_requester" model="res.groups">
        <field name="name">Billing Requester / ผู้แจ้งเปิดบิล</field>
        <field name="privilege_id" ref="privilege_od19_billing_request"/>
        <field name="implied_ids" eval="[(4, ref('base.group_user'))]"/>
    </record>

    <record id="group_od19_billing_accounting" model="res.groups">
        <field name="name">Billing Accounting / บัญชีผู้เปิดบิล</field>
        <field name="privilege_id" ref="privilege_od19_billing_request"/>
        <field name="implied_ids" eval="[(4, ref('account.group_account_invoice'))]"/>
    </record>

    <record id="rule_od19_billing_request_requester" model="ir.rule">
        <field name="name">Billing Request: own / คำขอของตัวเอง</field>
        <field name="model_id" ref="model_od19_billing_request"/>
        <field name="domain_force">[('requested_by_id', '=', user.id)]</field>
        <field name="groups" eval="[(4, ref('group_od19_billing_requester'))]"/>
        <field name="perm_read" eval="True"/>
        <field name="perm_write" eval="True"/>
        <field name="perm_create" eval="True"/>
        <field name="perm_unlink" eval="True"/>
    </record>

    <record id="rule_od19_billing_request_accounting" model="ir.rule">
        <field name="name">Billing Request: all / ทั้งหมด</field>
        <field name="model_id" ref="model_od19_billing_request"/>
        <field name="domain_force">[(1, '=', 1)]</field>
        <field name="groups" eval="[(4, ref('group_od19_billing_accounting'))]"/>
    </record>
</odoo>
```

`security/ir.model.access.csv`:

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_od19_billing_request_requester,access.od19.billing.request.requester,model_od19_billing_request,od19_billing_request.group_od19_billing_requester,1,1,1,0
access_od19_billing_request_accounting,access.od19.billing.request.accounting,model_od19_billing_request,od19_billing_request.group_od19_billing_accounting,1,1,1,1
access_od19_billing_request_requester_manager,access.od19.billing.request.manager,model_od19_billing_request,account.group_account_manager,1,1,1,1
```

> หมายเหตุ: ไฟล์ `data/od19_billing_request_data.xml`, `views/*` จะสร้างใน Task 4/10 — **ชั่วคราวให้คอมเมนต์สองบรรทัดนั้นออกจาก `data` ใน manifest** แล้วเปิดคืนใน Task 4 และ Task 10

ปรับ `__manifest__.py` `data` เป็น:

```python
    "data": [
        "security/od19_billing_request_security.xml",
        "security/ir.model.access.csv",
    ],
```

- [ ] **Step 6: ติดตั้ง/รีสตาร์ต และรันเทสต์ให้ผ่าน**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_billing_request`
Expected: PASS — `0 failed, 0 error(s)` (3 tests)

- [ ] **Step 7: Commit**

```bash
git add custom_addons/od19_billing_request
git commit -m "feat(od19_billing_request): scaffold module with request model and sequence"
```

---

## Task 2: โมเดลบรรทัด + ผูกกับคำขอ

**Files:**
- Create: `custom_addons/od19_billing_request/models/billing_request_line.py`
- Modify: `custom_addons/od19_billing_request/models/__init__.py`
- Modify: `custom_addons/od19_billing_request/models/billing_request.py` (เพิ่ม `line_ids`)
- Test: `custom_addons/od19_billing_request/tests/test_billing_request_line.py`
- Modify: `custom_addons/od19_billing_request/tests/__init__.py`

- [ ] **Step 1: เขียนเทสต์ที่จะ fail**

`tests/test_billing_request_line.py`:

```python
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBillingRequestLine(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {"name": "BR Service", "type": "service", "list_price": 100.0}
        )

    def test_add_line_to_request(self):
        request = self.env["od19.billing.request"].create(
            {
                "direction": "ar",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": "BR Service",
                            "quantity": 2.0,
                            "price_unit": 100.0,
                        },
                    )
                ],
            }
        )
        self.assertEqual(len(request.line_ids), 1)
        line = request.line_ids
        self.assertEqual(line.request_id, request)
        self.assertEqual(line.quantity, 2.0)
```

เพิ่มใน `tests/__init__.py`:

```python
from . import test_billing_request_line
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_billing_request`
Expected: FAIL — `Invalid field 'line_ids' on model 'od19.billing.request'`

- [ ] **Step 3: เขียนโมเดลบรรทัด**

`models/billing_request_line.py`:

```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
from odoo import fields, models


class Od19BillingRequestLine(models.Model):
    _name = "od19.billing.request.line"
    _description = "OD19 Billing Request Line"
    _order = "request_id, sequence, id"

    request_id = fields.Many2one(
        "od19.billing.request",
        string="Request / คำขอ",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    product_id = fields.Many2one(
        "product.product", string="Product / สินค้า", required=True
    )
    name = fields.Char(string="Description / รายละเอียด")
    product_uom_id = fields.Many2one("uom.uom", string="UoM / หน่วย")
    quantity = fields.Float(
        string="Quantity / จำนวน",
        default=1.0,
        digits="Product Unit of Measure",
        required=True,
    )
    price_unit = fields.Float(string="Unit Price / ราคาต่อหน่วย", digits="Product Price")
    discount = fields.Float(string="Discount (%)", digits="Discount")
    tax_ids = fields.Many2many("account.tax", string="Taxes / ภาษี")

    # ลิงก์บรรทัดต้นทาง
    sale_line_id = fields.Many2one("sale.order.line", string="Sale Order Line")
    purchase_line_id = fields.Many2one(
        "purchase.order.line", string="Purchase Order Line"
    )
    stock_move_id = fields.Many2one("stock.move", string="Stock Move")
    origin_line_model = fields.Char(string="Origin Line Model", readonly=True)
    origin_line_id = fields.Integer(string="Origin Line ID", readonly=True)

    # ผลลัพธ์หลังออกบิล
    target_line_id = fields.Many2one(
        "account.move.line", string="Target Line / บรรทัดปลายทาง", readonly=True
    )
```

`models/__init__.py`:

```python
from . import billing_request
from . import billing_request_line
```

ใน `models/billing_request.py` เพิ่มฟิลด์หลัง `reject_reason`:

```python
    line_ids = fields.One2many(
        "od19.billing.request.line", "request_id", string="Lines / รายการ"
    )
```

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_billing_request`
Expected: PASS — `0 failed, 0 error(s)`

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_billing_request
git commit -m "feat(od19_billing_request): add billing request line model"
```

---

## Task 3: ตัวนับยอด + guards (กันเกินยอด/เปิดซ้ำ)

**Files:**
- Modify: `custom_addons/od19_billing_request/models/billing_request_line.py`
- Test: `custom_addons/od19_billing_request/tests/test_billing_request_guards.py`
- Modify: `custom_addons/od19_billing_request/tests/__init__.py`

- [ ] **Step 1: เขียนเทสต์ที่จะ fail**

`tests/test_billing_request_guards.py`:

```python
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBillingRequestGuards(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env["res.partner"].create({"name": "BR Customer"})
        cls.product = cls.env["product.product"].create(
            {"name": "BR Widget", "type": "consu", "list_price": 50.0}
        )
        cls.product.invoice_policy = "order"
        cls.so = cls.env["sale.order"].create(
            {
                "partner_id": cls.customer.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product.id,
                            "product_uom_qty": 10.0,
                            "price_unit": 50.0,
                            "name": cls.product.name,
                        },
                    )
                ],
            }
        )
        cls.so.action_confirm()
        cls.sale_line = cls.so.order_line

    def _request_with(self, qty):
        return self.env["od19.billing.request"].create(
            {
                "direction": "ar",
                "partner_id": self.customer.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "sale_line_id": self.sale_line.id,
                            "quantity": qty,
                            "price_unit": 50.0,
                        },
                    )
                ],
            }
        )

    def test_quantity_ordered_and_remaining(self):
        request = self._request_with(4.0)
        line = request.line_ids
        self.assertAlmostEqual(line.qty_ordered, 10.0)
        self.assertAlmostEqual(line.remaining_to_bill, 6.0)

    def test_over_bill_is_blocked(self):
        with self.assertRaises(ValidationError):
            self._request_with(11.0)

    def test_second_request_cannot_exceed_remaining(self):
        self._request_with(6.0)
        with self.assertRaises(ValidationError):
            self._request_with(5.0)

    def test_zero_quantity_is_blocked(self):
        with self.assertRaises(ValidationError):
            self._request_with(0.0)
```

เพิ่มใน `tests/__init__.py`:

```python
from . import test_billing_request_guards
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_billing_request`
Expected: FAIL — `Invalid field 'qty_ordered'` และไม่มี `ValidationError`

- [ ] **Step 3: เพิ่ม compute + constraint**

ใน `models/billing_request_line.py` แก้ import เป็น:

```python
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
```

เพิ่มฟิลด์ (หลัง `target_line_id`) และเมธอด:

```python
    qty_ordered = fields.Float(
        string="Ordered Qty / จำนวนตามต้นทาง",
        compute="_compute_quantities",
        digits="Product Unit of Measure",
    )
    qty_already_requested = fields.Float(
        string="Already Requested / แจ้งแล้ว",
        compute="_compute_quantities",
        digits="Product Unit of Measure",
    )
    qty_invoiced = fields.Float(
        string="Invoiced / ออกบิลแล้ว",
        compute="_compute_quantities",
        digits="Product Unit of Measure",
    )
    remaining_to_bill = fields.Float(
        string="Remaining to Bill / คงเหลือที่เปิดบิลได้",
        compute="_compute_quantities",
        digits="Product Unit of Measure",
    )

    @api.depends(
        "sale_line_id",
        "sale_line_id.product_uom_qty",
        "sale_line_id.qty_invoiced",
        "purchase_line_id",
        "purchase_line_id.product_qty",
        "purchase_line_id.qty_invoiced",
        "stock_move_id",
        "stock_move_id.quantity",
        "quantity",
        "request_id.state",
    )
    def _compute_quantities(self):
        for line in self:
            if line.sale_line_id:
                line.qty_ordered = line.sale_line_id.product_uom_qty
                line.qty_invoiced = line.sale_line_id.qty_invoiced
            elif line.purchase_line_id:
                line.qty_ordered = line.purchase_line_id.product_qty
                line.qty_invoiced = line.purchase_line_id.qty_invoiced
            elif line.stock_move_id:
                line.qty_ordered = line.stock_move_id.quantity
                line.qty_invoiced = 0.0
            else:
                line.qty_ordered = 0.0
                line.qty_invoiced = 0.0
            line.qty_already_requested = line._od19_qty_already_requested()
            line.remaining_to_bill = max(
                line.qty_ordered - line.qty_already_requested, 0.0
            )

    def _od19_qty_already_requested(self):
        """ผลรวม quantity ของบรรทัดอื่นที่อ้างต้นทางบรรทัดเดียวกัน (ไม่นับตัวเอง)."""
        self.ensure_one()
        domain = [
            ("id", "!=", self.id),
            ("request_id.state", "in", ("draft", "submitted", "invoiced")),
        ]
        if self.sale_line_id:
            domain.append(("sale_line_id", "=", self.sale_line_id.id))
        elif self.purchase_line_id:
            domain.append(("purchase_line_id", "=", self.purchase_line_id.id))
        elif self.stock_move_id:
            domain.append(("stock_move_id", "=", self.stock_move_id.id))
        else:
            return 0.0
        others = self.env["od19.billing.request.line"].search(domain)
        return sum(others.mapped("quantity"))

    @api.constrains("quantity")
    def _check_quantity_positive(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(
                    _("Quantity must be greater than zero on every line.")
                )

    @api.constrains("quantity")
    def _check_quantity_within_remaining(self):
        for line in self:
            if not (line.sale_line_id or line.purchase_line_id or line.stock_move_id):
                continue
            if line.quantity > line.remaining_to_bill + 1e-6:
                raise ValidationError(
                    _(
                        "Cannot bill %(qty)s: only %(remaining)s remaining on "
                        "%(product)s."
                    )
                    % {
                        "qty": line.quantity,
                        "remaining": line.remaining_to_bill,
                        "product": line.product_id.display_name,
                    }
                )
```

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_billing_request`
Expected: PASS — `0 failed, 0 error(s)`

> ถ้า `test_over_bill_is_blocked` ไม่ฟ้อง ValidationError ให้ตรวจว่า `remaining_to_bill` ถูกประเมินตอน create หรือยัง (constraint ต้องเรียก compute แบบ non-stored จึงได้ค่า fresh)

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_billing_request
git commit -m "feat(od19_billing_request): add line counters and over-bill guards"
```

> **Implementation notes (actual — Task 3 shipped, commits `dd71751` + `c10c93e`):**
> - Plan formula `remaining_to_bill = qty_ordered − qty_already_requested` ขัดกับเทสต์ของแผนเอง (บรรทัด 656 คาดว่า 6) จึงใช้สูตรจริง `max(qty_ordered − qty_already_requested − quantity, 0.0)` = "คงเหลือ**หลัง**คำขอนี้"
> - guard ใช้ threshold แยก `available = qty_ordered − qty_already_requested − _od19_qty_invoiced_external()` โดย `_od19_qty_invoiced_external() = max(qty_invoiced − module_invoiced, 0.0)` เพื่อกันยอดที่ออกบิล**นอกโมดูล**ซ้ำ (ตามสเปก §4.6 บรรทัด 169)
> - เทสต์เปลี่ยน product type `consu` → `service` เพื่อเลี่ยง validation DEPT code ของ `od19_delivery_label` บนใบส่งของที่ auto-create
> - ผลเทสต์: 13 passed

---

## Task 4: Config นโยบาย AR/AP + ขยายหลักฐาน

**Files:**
- Create: `custom_addons/od19_billing_request/models/res_company.py`
- Create: `custom_addons/od19_billing_request/models/res_partner.py`
- Create: `custom_addons/od19_billing_request/models/sale_order.py`
- Create: `custom_addons/od19_billing_request/models/billing_evidence.py`
- Create: `custom_addons/od19_billing_request/data/od19_billing_request_data.xml`
- Modify: `custom_addons/od19_billing_request/models/__init__.py`
- Modify: `custom_addons/od19_billing_request/__manifest__.py` (เปิด data)
- Test: `custom_addons/od19_billing_request/tests/test_billing_request_config.py`
- Modify: `custom_addons/od19_billing_request/tests/__init__.py`

- [ ] **Step 1: เขียนเทสต์ที่จะ fail**

`tests/test_billing_request_config.py`:

```python
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBillingRequestConfig(TransactionCase):
    def test_evidence_types_seeded(self):
        codes = self.env["od19.billing.evidence.type"].search(
            [("name", "in", ["delivery_note", "vendor_tax_invoice"])]
        )
        self.assertEqual(len(codes), 2)

    def test_ar_mode_resolution_order(self):
        company = self.env.company
        company.od19_ar_billing_mode_default = "direct"
        partner = self.env["res.partner"].create({"name": "Mode Partner"})
        request = self.env["od19.billing.request"].create(
            {"direction": "ar", "partner_id": partner.id}
        )
        self.assertEqual(request.ar_billing_mode, "direct")
        partner.od19_ar_billing_mode = "two_step"
        request._compute_ar_billing_mode()
        self.assertEqual(request.ar_billing_mode, "two_step")

    def test_ap_original_flag_defaults_on(self):
        self.assertTrue(self.env.company.od19_ap_require_original)
```

เพิ่มใน `tests/__init__.py`:

```python
from . import test_billing_request_config
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_billing_request`
Expected: FAIL — `Invalid field 'od19_ar_billing_mode_default'` / ไม่พบ evidence types

- [ ] **Step 3: เขียนส่วนขยาย config + หลักฐาน**

`models/res_company.py`:

```python
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    od19_ar_billing_mode_default = fields.Selection(
        [("direct", "Direct / ออกบิลเลย"), ("two_step", "Two Step / วางบิลก่อน")],
        string="Default AR Billing Mode",
        default="direct",
    )
    od19_ar_require_evidence = fields.Boolean(
        string="Require AR Evidence before Submit", default=True
    )
    od19_ap_require_original = fields.Boolean(
        string="Require Original Vendor Document before Bill", default=True
    )
```

`models/res_partner.py`:

```python
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    od19_ar_billing_mode = fields.Selection(
        [
            ("default", "Use Company Default / ตามบริษัท"),
            ("direct", "Direct / ออกบิลเลย"),
            ("two_step", "Two Step / วางบิลก่อน"),
        ],
        string="AR Billing Mode",
        default="default",
    )
```

`models/sale_order.py`:

```python
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    od19_ar_billing_mode = fields.Selection(
        [
            ("default", "Use Partner/Company Default / ตามค่าปริยาย"),
            ("direct", "Direct / ออกบิลเลย"),
            ("two_step", "Two Step / วางบิลก่อน"),
        ],
        string="AR Billing Mode",
        default="default",
    )
```

`models/billing_evidence.py`:

```python
from odoo import fields, models


class Od19BillingEvidence(models.Model):
    _inherit = "od19.billing.evidence"

    billing_request_id = fields.Many2one(
        "od19.billing.request",
        string="Billing Request",
        ondelete="cascade",
        index=True,
    )


class Od19BillingEvidenceType(models.Model):
    _inherit = "od19.billing.evidence.type"

    requires_original = fields.Boolean(
        string="Requires Original / ต้องมีต้นฉบับจริง"
    )
```

`data/od19_billing_request_data.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo noupdate="1">
    <record id="evidence_type_delivery_note" model="od19.billing.evidence.type">
        <field name="name">delivery_note</field>
        <field name="trigger_kind">delivery</field>
        <field name="required_for_billing" eval="False"/>
    </record>
    <record id="evidence_type_customer_po" model="od19.billing.evidence.type">
        <field name="name">customer_po</field>
        <field name="trigger_kind">other</field>
        <field name="required_for_billing" eval="False"/>
    </record>
    <record id="evidence_type_service_report" model="od19.billing.evidence.type">
        <field name="name">service_report</field>
        <field name="trigger_kind">service</field>
        <field name="required_for_billing" eval="False"/>
    </record>
    <record id="evidence_type_vendor_tax_invoice" model="od19.billing.evidence.type">
        <field name="name">vendor_tax_invoice</field>
        <field name="trigger_kind">other</field>
        <field name="required_for_billing" eval="False"/>
        <field name="requires_original" eval="True"/>
    </record>
    <record id="evidence_type_vendor_invoice" model="od19.billing.evidence.type">
        <field name="name">vendor_invoice</field>
        <field name="trigger_kind">other</field>
        <field name="required_for_billing" eval="False"/>
        <field name="requires_original" eval="True"/>
    </record>
</odoo>
```

`models/__init__.py`:

```python
from . import billing_request
from . import billing_request_line
from . import res_company
from . import res_partner
from . import sale_order
from . import billing_evidence
```

`__manifest__.py` `data` เปิดคืน:

```python
    "data": [
        "security/od19_billing_request_security.xml",
        "security/ir.model.access.csv",
        "data/od19_billing_request_data.xml",
    ],
```

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_billing_request`
Expected: PASS — `0 failed, 0 error(s)`

> หมายเหตุ: `required_for_billing=False` โดยตั้งใจ เพื่อไม่ให้กระทบ `sale.order.od19_billing_readiness_state` ที่มีอยู่เดิม

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_billing_request
git commit -m "feat(od19_billing_request): add AR/AP policy config and evidence extensions"
```

---

## Task 5: ดึงรายการจากต้นทาง (document pull) + partial

**Files:**
- Modify: `custom_addons/od19_billing_request/models/billing_request.py` (implement contract ของ mixin)
- Create: `custom_addons/od19_billing_request/tests/test_billing_request_pull.py`
- Modify: `custom_addons/od19_billing_request/tests/__init__.py`

- [ ] **Step 1: เขียนเทสต์ที่จะ fail**

`tests/test_billing_request_pull.py`:

```python
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBillingRequestPull(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env["res.partner"].create({"name": "Pull Customer"})
        cls.vendor = cls.env["res.partner"].create({"name": "Pull Vendor"})
        cls.product = cls.env["product.product"].create(
            {"name": "Pull Item", "type": "consu", "list_price": 20.0}
        )
        cls.product.invoice_policy = "order"
        cls.product.purchase_method = "purchase"

    def _confirmed_so(self, qty=5.0):
        so = self.env["sale.order"].sudo().create(
            {
                "partner_id": self.customer.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": qty,
                            "price_unit": 20.0,
                            "name": self.product.name,
                        },
                    )
                ],
            }
        )
        so.action_confirm()
        return so

    def test_pull_from_sale_order(self):
        so = self._confirmed_so()
        request = self.env["od19.billing.request"].create({"direction": "ar"})
        request.origin_ref = so
        wizard = self.env["od19.document.pull.wizard"].create(
            {
                "res_model": "od19.billing.request",
                "res_id": request.id,
                "source_ref": "sale.order,%s" % so.id,
            }
        )
        wizard._onchange_source_ref()
        self.assertEqual(len(wizard.line_ids), 1)
        wizard.action_pull()
        self.assertEqual(len(request.line_ids), 1)
        self.assertEqual(request.line_ids.sale_line_id, so.order_line)
        self.assertAlmostEqual(request.line_ids.price_unit, 20.0)

    def test_pull_from_purchase_order(self):
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_qty": 3.0,
                            "price_unit": 15.0,
                            "name": self.product.name,
                            "date_planned": "2026-11-10 00:00:00",
                        },
                    )
                ],
            }
        )
        po.button_confirm()
        request = self.env["od19.billing.request"].create({"direction": "ap"})
        request.origin_ref = po
        wizard = self.env["od19.document.pull.wizard"].create(
            {
                "res_model": "od19.billing.request",
                "res_id": request.id,
                "source_ref": "purchase.order,%s" % po.id,
            }
        )
        wizard._onchange_source_ref()
        self.assertEqual(len(wizard.line_ids), 1)
        wizard.action_pull()
        self.assertEqual(len(request.line_ids), 1)
        self.assertEqual(request.line_ids.purchase_line_id, po.order_line)

    def test_remove_bound_source_lines(self):
        so = self._confirmed_so()
        request = self.env["od19.billing.request"].create({"direction": "ar"})
        request.origin_ref = so
        request._od19_pull_apply(so, so.order_line)
        self.assertEqual(len(request.line_ids), 1)
        removed = request._od19_pull_remove(so)
        self.assertEqual(removed, 1)
        self.assertFalse(request.line_ids)
```

เพิ่มใน `tests/__init__.py`:

```python
from . import test_billing_request_pull
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_billing_request`
Expected: FAIL — `NotImplementedError` จาก `_od19_pull_candidate_lines`

- [ ] **Step 3: implement contract ของ mixin**

เพิ่มในคลาส `Od19BillingRequest` (`models/billing_request.py`) ต่อท้ายเมธอด `create`:

```python
    # ------------------------------------------------------------------
    # Document pull contract (od19.document.pull.mixin)
    # ------------------------------------------------------------------
    def _od19_pull_editable_states(self):
        return ("draft",)

    def _od19_pull_source_specs(self):
        self.ensure_one()
        partner_domain = (
            [("partner_id", "=", self.partner_id.id)] if self.partner_id else []
        )
        if self.direction == "ap":
            return [
                {
                    "model": "purchase.order",
                    "label": _("Purchase Order / ใบสั่งซื้อ"),
                    "domain": partner_domain + [("state", "in", ("purchase", "done"))],
                },
                {
                    "model": "stock.picking",
                    "label": _("Receipt / ใบรับของ"),
                    "domain": partner_domain
                    + [("picking_type_code", "=", "incoming"), ("state", "=", "done")],
                },
            ]
        return [
            {
                "model": "sale.order",
                "label": _("Sale Order / ใบสั่งขาย"),
                "domain": partner_domain + [("state", "=", "sale")],
            },
            {
                "model": "stock.picking",
                "label": _("Delivery / ใบส่งของ"),
                "domain": partner_domain
                + [("picking_type_code", "=", "outgoing"), ("state", "=", "done")],
            },
        ]

    def _od19_pull_candidate_lines(self, source):
        self.ensure_one()
        if source._name in ("sale.order", "purchase.order"):
            return source.order_line.filtered(
                lambda line: line.product_id and line.qty_to_invoice > 0
            )
        if source._name == "stock.picking":
            return source.move_ids.filtered(
                lambda move: move.product_id and move.quantity > 0
            )
        return self.env["od19.billing.request.line"].browse()

    def _od19_pull_line_info(self, source, line):
        self.ensure_one()
        if source._name in ("sale.order", "purchase.order"):
            return {
                "res_model": source._name,
                "res_id": line.id,
                "source_name": source.display_name,
                "product_id": line.product_id.id,
                "name": line.name,
                "qty_to_pull": line.qty_to_invoice,
                "price_unit": line.price_unit,
                "product_uom_id": line.product_uom_id.id,
            }
        sale_line = line.sale_line_id
        price = sale_line.price_unit if sale_line else (line.price_unit or 0.0)
        return {
            "res_model": source._name,
            "res_id": line.id,
            "source_name": source.display_name,
            "product_id": line.product_id.id,
            "name": line.description_picking or line.product_id.display_name,
            "qty_to_pull": line.quantity,
            "price_unit": price,
            "product_uom_id": line.product_uom.id,
        }

    def _od19_pull_apply(self, source, lines):
        self.ensure_one()
        count = 0
        if not self.origin_ref:
            self.origin_ref = source
        for src_line in lines:
            info = self._od19_pull_line_info(source, src_line)
            vals = {
                "request_id": self.id,
                "product_id": info["product_id"],
                "name": info["name"],
                "quantity": info["qty_to_pull"],
                "price_unit": info["price_unit"],
                "product_uom_id": info["product_uom_id"],
                "origin_line_model": src_line._name,
                "origin_line_id": src_line.id,
            }
            if source._name == "sale.order":
                vals["sale_line_id"] = src_line.id
            elif source._name == "purchase.order":
                vals["purchase_line_id"] = src_line.id
            else:  # stock.picking
                vals["stock_move_id"] = src_line.id
                if src_line.sale_line_id:
                    vals["sale_line_id"] = src_line.sale_line_id.id
                if src_line.purchase_line_id:
                    vals["purchase_line_id"] = src_line.purchase_line_id.id
            self.env["od19.billing.request.line"].create(vals)
            count += 1
        return count

    def _od19_pull_origin_line_ids(self, source):
        self.ensure_one()
        if source._name in ("sale.order", "purchase.order"):
            return source.order_line.ids
        return source.move_ids.ids

    def _od19_pull_bound_lines(self, source):
        self.ensure_one()
        ids = self._od19_pull_origin_line_ids(source)
        return self.line_ids.filtered(
            lambda line: line.origin_line_model == source._name
            and line.origin_line_id in ids
        )

    def _od19_pull_remove(self, source):
        self.ensure_one()
        lines = self._od19_pull_bound_lines(source)
        count = len(lines)
        lines.unlink()
        return count

    def _od19_pull_bound_sources(self):
        self.ensure_one()
        result = []
        for model in ("sale.order", "purchase.order", "stock.picking"):
            model_lines = self.line_ids.filtered(
                lambda line: line.origin_line_model == model
            )
            if not model_lines:
                continue
            records = self.env[model].browse(model_lines.mapped("origin_line_id"))
            if model in ("sale.order", "purchase.order"):
                for order in records.mapped("order_id"):
                    result.append((order, len(self._od19_pull_bound_lines(order))))
            else:
                for picking in records.mapped("picking_id"):
                    result.append((picking, len(self._od19_pull_bound_lines(picking))))
        return result

    def _od19_pull_preview_lines(self, source):
        self.ensure_one()
        return [
            {
                "name": line.name,
                "product_id": line.product_id.id,
                "quantity": line.quantity,
            }
            for line in self._od19_pull_bound_lines(source)
        ]
```

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_billing_request`
Expected: PASS — `0 failed, 0 error(s)`

> **Partial billing:** บรรทัดที่ดึงมาจะมี `quantity = qty_to_invoice` (ยอดที่เหลือ) ผู้ใช้แก้จำนวนลงได้ในหน้าจอ ถ้าอยากเปิดบิลเฉพาะบางรายการ ให้ติ๊กเลือกใน wizard (`mode = "select"`) — รายการที่ไม่เลือกจะไม่ถูกสร้าง บรรทัดที่ไม่ต้องการลบได้ผ่าน `od19_action_open_remove_wizard`

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_billing_request
git commit -m "feat(od19_billing_request): integrate document pull from SO/PO/picking"
```

---

## Task 6: Flow (submit/reject/cancel/reset) + แจ้งเตือนบัญชี

**Files:**
- Modify: `custom_addons/od19_billing_request/models/billing_request.py`
- Test: `custom_addons/od19_billing_request/tests/test_billing_request_flow.py`
- Modify: `custom_addons/od19_billing_request/tests/__init__.py`

- [ ] **Step 1: เขียนเทสต์ที่จะ fail**

`tests/test_billing_request_flow.py`:

```python
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBillingRequestFlow(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {"name": "Flow Item", "type": "service", "list_price": 10.0}
        )
        cls.accounting_user = cls.env["res.users"].create(
            {
                "name": "BR Accountant",
                "login": "br_accountant",
                "groups_id": [
                    (4, cls.env.ref("od19_billing_request.group_od19_billing_accounting").id)
                ],
            }
        )

    def _draft_request(self):
        return self.env["od19.billing.request"].create(
            {
                "direction": "ar",
                "line_ids": [
                    (0, 0, {"product_id": self.product.id, "quantity": 1.0})
                ],
            }
        )

    def test_submit_without_lines_is_blocked(self):
        request = self.env["od19.billing.request"].create({"direction": "ar"})
        with self.assertRaises(UserError):
            request.action_submit()

    def test_submit_sets_state_and_notifies_accounting(self):
        request = self._draft_request()
        request.action_submit()
        self.assertEqual(request.state, "submitted")
        activities = self.env["mail.activity"].search(
            [
                ("res_model", "=", "od19.billing.request"),
                ("res_id", "=", request.id),
                ("user_id", "=", self.accounting_user.id),
            ]
        )
        self.assertTrue(activities)

    def test_reject_then_reset(self):
        request = self._draft_request()
        request.action_submit()
        request.action_reject()
        request.reject_reason = "เอกสารไม่ครบ"
        self.assertEqual(request.state, "rejected")
        request.action_reset_draft()
        self.assertEqual(request.state, "draft")

    def test_cancel(self):
        request = self._draft_request()
        request.action_cancel()
        self.assertEqual(request.state, "cancelled")
```

เพิ่มใน `tests/__init__.py`:

```python
from . import test_billing_request_flow
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_billing_request`
Expected: FAIL — `'od19.billing.request' object has no attribute 'action_submit'`

- [ ] **Step 3: implement flow + notification**

เพิ่มในคลาส `Od19BillingRequest`:

```python
    # ------------------------------------------------------------------
    # Flow
    # ------------------------------------------------------------------
    def action_submit(self):
        for request in self:
            if request.state != "draft":
                raise UserError(
                    _("Only a draft request can be submitted (state: %s).")
                    % request.state
                )
            if not request.line_ids:
                raise UserError(_("Add at least one line before submitting."))
            request._od19_check_evidence_before_submit()
            request.state = "submitted"
            request._od19_notify_accounting()
        return True

    def action_reject(self):
        for request in self:
            if request.state != "submitted":
                raise UserError(_("Only a submitted request can be rejected."))
            request.state = "rejected"
        return True

    def action_reset_draft(self):
        for request in self:
            if request.state not in ("rejected", "cancelled"):
                raise UserError(_("Only rejected/cancelled requests can be reset."))
            request.reject_reason = False
            request.state = "draft"
        return True

    def action_cancel(self):
        for request in self:
            if request.state == "invoiced":
                raise UserError(_("An invoiced request cannot be cancelled."))
            request.state = "cancelled"
        return True

    def _od19_check_evidence_before_submit(self):
        self.ensure_one()
        if self.direction == "ar" and self.company_id.od19_ar_require_evidence:
            if not self.evidence_ok:
                raise UserError(
                    _(
                        "AR requires at least one verified evidence "
                        "(delivery note / customer PO / service report) "
                        "before submitting."
                    )
                )
        return True

    def _od19_notify_accounting(self):
        self.ensure_one()
        group = self.env.ref(
            "od19_billing_request.group_od19_billing_accounting", raise_if_not_found=False
        )
        if not group:
            return
        for user in group.users:
            self.activity_schedule(
                "mail.mail_activity_data_todo",
                date_deadline=fields.Date.context_today(self),
                summary=_("Billing Request %s awaiting billing") % self.name,
                note=_(
                    "คำขอเปิดบิล %(name)s (%(direction)s) รอการออกบิลโดยบัญชี"
                )
                % {"name": self.name, "direction": self.direction.upper()},
                user_id=user.id,
            )
```

เพิ่มฟิลด์ `evidence_ok` (ใช้ใน Task 6 และ gate ของ Task 9) ในส่วน compute ของ `billing_request.py`:

```python
    evidence_ids = fields.One2many(
        "od19.billing.evidence", "billing_request_id", string="Evidence / หลักฐาน"
    )
    evidence_ok = fields.Boolean(
        string="Evidence Ready", compute="_compute_evidence_ok"
    )
```

และเมธอด:

```python
    @api.depends("evidence_ids.is_verified")
    def _compute_evidence_ok(self):
        for request in self:
            request.evidence_ok = bool(request.evidence_ids.filtered("is_verified"))
```

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_billing_request`
Expected: PASS — `0 failed, 0 error(s)`

> ในเทสต์อื่น (Task 3/5) ที่ไม่ต้องการ gate หลักฐาน ให้ปิดด้วย `self.env.company.od19_ar_require_evidence = False` ใน `setUpClass` ถ้ามีการเรียก `action_submit` — ยังไม่มีใน Task 3/5 จึงไม่ต้องแก้

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_billing_request
git commit -m "feat(od19_billing_request): add submit/reject/cancel/reset flow with activity"
```

---

## Task 7: ออกเอกสารปลายทาง AR (`out_invoice`)

**Files:**
- Modify: `custom_addons/od19_billing_request/models/billing_request.py`
- Test: `custom_addons/od19_billing_request/tests/test_billing_request_invoice_ar.py`
- Modify: `custom_addons/od19_billing_request/tests/__init__.py`

- [ ] **Step 1: เขียนเทสต์ที่จะ fail**

`tests/test_billing_request_invoice_ar.py`:

```python
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestBillingRequestInvoiceAR(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.partner_a
        cls.product = cls.product_a
        cls.product.invoice_policy = "order"
        cls.company = cls.env.company
        cls.company.od19_ar_require_evidence = False

    def _submitted_request(self, qty=2.0):
        so = self.env["sale.order"].sudo().create(
            {
                "partner_id": self.customer.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 5.0,
                            "price_unit": 100.0,
                            "name": self.product.name,
                        },
                    )
                ],
            }
        )
        so.action_confirm()
        request = self.env["od19.billing.request"].create(
            {
                "direction": "ar",
                "partner_id": self.customer.id,
                "origin_ref": "sale.order,%s" % so.id,
            }
        )
        request._od19_pull_apply(so, so.order_line)
        request.line_ids.write({"quantity": qty})
        request.action_submit()
        return request, so

    def test_create_invoice_links_target_and_line(self):
        request, so = self._submitted_request()
        move = request.action_create_invoice()
        self.assertEqual(move.move_type, "out_invoice")
        self.assertEqual(request.target_move_id, move)
        self.assertEqual(request.state, "invoiced")
        self.assertAlmostEqual(move.invoice_line_ids.quantity, 2.0)
        self.assertEqual(move.invoice_line_ids.sale_line_ids, so.order_line)
        self.assertEqual(request.line_ids.target_line_id, move.invoice_line_ids)

    def test_create_invoice_twice_is_blocked(self):
        request, _so = self._submitted_request()
        request.action_create_invoice()
        with self.assertRaises(UserError):
            request.action_create_invoice()
```

เพิ่มใน `tests/__init__.py`:

```python
from . import test_billing_request_invoice_ar
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_billing_request`
Expected: FAIL — `'od19.billing.request' object has no attribute 'action_create_invoice'`

- [ ] **Step 3: implement การออกบิล**

เพิ่มในคลาส `Od19BillingRequest`:

```python
    # ------------------------------------------------------------------
    # Create target document
    # ------------------------------------------------------------------
    def action_create_invoice(self):
        self.ensure_one()
        if self.state != "submitted":
            raise UserError(
                _("Only a submitted request can be billed (state: %s).") % self.state
            )
        if self.target_move_id:
            raise UserError(_("This request already has a target document."))
        if not self.line_ids:
            raise UserError(_("Add at least one line before creating the document."))
        if not self.partner_id:
            raise UserError(_("Please set the partner before creating the document."))
        self._od19_check_before_create_document()
        move = self._od19_build_move()
        self.write({"target_move_id": move.id, "state": "invoiced"})
        self._od19_link_target_lines(move)
        return move

    def _od19_check_before_create_document(self):
        self.ensure_one()
        return True

    def _od19_build_move(self):
        self.ensure_one()
        line_commands = []
        for line in self.line_ids.sorted("sequence"):
            vals = {
                "product_id": line.product_id.id,
                "name": line.name or line.product_id.display_name,
                "quantity": line.quantity,
                "price_unit": line.price_unit,
                "discount": line.discount,
            }
            if line.product_uom_id:
                vals["product_uom_id"] = line.product_uom_id.id
            if line.tax_ids:
                vals["tax_ids"] = [(6, 0, line.tax_ids.ids)]
            if line.sale_line_id:
                vals["sale_line_ids"] = [(6, 0, [line.sale_line_id.id])]
            if line.purchase_line_id:
                vals["purchase_line_id"] = line.purchase_line_id.id
            line_commands.append((0, 0, vals))
        move_vals = {
            "move_type": self.move_type,
            "partner_id": self.partner_id.id,
            "invoice_date": fields.Date.context_today(self),
            "invoice_origin": self.name,
            "ref": self.name,
            "invoice_line_ids": line_commands,
        }
        return self.env["account.move"].create(move_vals)

    def _od19_link_target_lines(self, move):
        self.ensure_one()
        move_lines = move.invoice_line_ids.sorted(lambda line: line.id)
        request_lines = self.line_ids.sorted("sequence")
        if len(move_lines) != len(request_lines):
            return
        for request_line, move_line in zip(request_lines, move_lines):
            request_line.target_line_id = move_line
```

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_billing_request`
Expected: PASS — `0 failed, 0 error(s)`

> `invoice_date` ใช้ได้ทั้ง `out_invoice` และ `in_invoice` ใน Odoo 19

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_billing_request
git commit -m "feat(od19_billing_request): create AR customer invoice and link target lines"
```

---

## Task 8: ออกเอกสารปลายทาง AP (`in_invoice`) + ประตูต้นฉบับจริง

**Files:**
- Modify: `custom_addons/od19_billing_request/models/billing_request.py`
- Test: `custom_addons/od19_billing_request/tests/test_billing_request_invoice_ap.py`
- Modify: `custom_addons/od19_billing_request/tests/__init__.py`

- [ ] **Step 1: เขียนเทสต์ที่จะ fail**

`tests/test_billing_request_invoice_ap.py`:

```python
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestBillingRequestInvoiceAP(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.partner_a
        cls.product = cls.product_a
        cls.product.purchase_method = "purchase"
        cls.company = cls.env.company
        cls.company.od19_ap_require_original = True

    def _submitted_request(self):
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_qty": 3.0,
                            "price_unit": 40.0,
                            "name": self.product.name,
                            "date_planned": "2026-11-10 00:00:00",
                        },
                    )
                ],
            }
        )
        po.button_confirm()
        request = self.env["od19.billing.request"].create(
            {"direction": "ap", "partner_id": self.vendor.id, "origin_ref": po}
        )
        request._od19_pull_apply(po, po.order_line)
        request.action_submit()
        return request

    def test_ap_blocked_without_original(self):
        request = self._submitted_request()
        with self.assertRaises(UserError):
            request.action_create_invoice()

    def test_ap_requires_verified_evidence(self):
        request = self._submitted_request()
        request.original_received = True
        with self.assertRaises(UserError):
            request.action_create_invoice()

    def test_ap_creates_vendor_bill_when_gates_pass(self):
        request = self._submitted_request()
        request.original_received = True
        request.original_received_date = "2026-11-02"
        request.original_received_by_id = self.env.user.id
        evidence_type = self.env.ref(
            "od19_billing_request.evidence_type_vendor_tax_invoice"
        )
        attachment = self.env["ir.attachment"].create(
            {"name": "tax.pdf", "datas": "bW9jaw=="}
        )
        self.env["od19.billing.evidence"].create(
            {
                "name": "VAT-001",
                "billing_request_id": request.id,
                "evidence_type_id": evidence_type.id,
                "is_verified": True,
                "attachment_ids": [(4, attachment.id)],
            }
        )
        move = request.action_create_invoice()
        self.assertEqual(move.move_type, "in_invoice")
        self.assertEqual(request.state, "invoiced")
```

เพิ่มใน `tests/__init__.py`:

```python
from . import test_billing_request_invoice_ap
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_billing_request`
Expected: FAIL — AP สร้างบิลได้ทั้งที่ยังไม่ผ่านประตู (`test_ap_blocked_without_original` ไม่ฟ้อง)

- [ ] **Step 3: เพิ่มประตู AP**

แก้ `_od19_check_before_create_document` ใน `models/billing_request.py`:

```python
    def _od19_check_before_create_document(self):
        self.ensure_one()
        if self.direction == "ap":
            if self.company_id.od19_ap_require_original and not self.original_received:
                raise UserError(
                    _(
                        "ยังไม่ได้รับต้นฉบับเอกสาร — กรุณาระบุ 'รับต้นฉบับจริงแล้ว' "
                        "ก่อนออกบิล"
                    )
                )
            if not self.evidence_ok:
                raise UserError(
                    _(
                        "AP requires at least one verified evidence "
                        "(vendor tax invoice / invoice) before creating the bill."
                    )
                )
        return True
```

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_billing_request`
Expected: PASS — `0 failed, 0 error(s)`

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_billing_request
git commit -m "feat(od19_billing_request): create AP vendor bill behind original-document gate"
```

---

## Task 9: Views + Billing Queue + เมนู

**Files:**
- Create: `custom_addons/od19_billing_request/views/billing_request_views.xml`
- Create: `custom_addons/od19_billing_request/views/billing_request_menus.xml`
- Modify: `custom_addons/od19_billing_request/__manifest__.py` (เปิด views)
- Test: `custom_addons/od19_billing_request/tests/test_billing_request_views.py`
- Modify: `custom_addons/od19_billing_request/tests/__init__.py`

- [ ] **Step 1: เขียนเทสต์ที่จะ fail**

`tests/test_billing_request_views.py`:

```python
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBillingRequestViews(TransactionCase):
    def test_form_view_loads(self):
        view = self.env.ref("od19_billing_request.view_od19_billing_request_form")
        self.assertTrue(view)

    def test_billing_queue_action_filters_submitted(self):
        action = self.env.ref(
            "od19_billing_request.action_od19_billing_request_queue"
        )
        self.assertIn("submitted", action.domain)

    def test_menus_exist(self):
        self.assertTrue(
            self.env.ref("od19_billing_request.menu_od19_billing_request_root")
        )
        self.assertTrue(
            self.env.ref("od19_billing_request.menu_od19_billing_request_queue")
        )
```

เพิ่มใน `tests/__init__.py`:

```python
from . import test_billing_request_views
```

- [ ] **Step 2: รันเทสต์ให้ fail**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_billing_request`
Expected: FAIL — `External ID not found: od19_billing_request.view_od19_billing_request_form`

- [ ] **Step 3: เขียน views**

`views/billing_request_views.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- ============ FORM ============ -->
    <record id="view_od19_billing_request_form" model="ir.ui.view">
        <field name="name">od19.billing.request.form</field>
        <field name="model">od19.billing.request</field>
        <field name="arch" type="xml">
            <form string="Billing Request">
                <header>
                    <button name="action_submit" type="object" string="Submit / ส่งให้บัญชี"
                            class="btn-primary" invisible="state != 'draft'"/>
                    <button name="action_create_invoice" type="object"
                            string="Create Invoice/Bill / ออกบิล" class="btn-primary"
                            invisible="state != 'submitted'"/>
                    <button name="action_reject" type="object" string="Reject / ตีกลับ"
                            invisible="state != 'submitted'"/>
                    <button name="action_reset_draft" type="object" string="Reset to Draft"
                            invisible="state not in ('rejected', 'cancelled')"/>
                    <button name="action_cancel" type="object" string="Cancel"
                            invisible="state in ('invoiced', 'cancelled')"/>
                    <button name="od19_action_open_pull_wizard" type="object"
                            string="Pull Lines / ดึงรายการ" invisible="state != 'draft'"/>
                    <button name="od19_action_open_remove_wizard" type="object"
                            string="Manage Source / จัดการต้นทาง" invisible="state != 'draft'"/>
                    <field name="state" widget="statusbar" statusbar_visible="draft,submitted,invoiced"/>
                </header>
                <sheet>
                    <div class="oe_title">
                        <h1><field name="name" readonly="1"/></h1>
                    </div>
                    <group>
                        <group>
                            <field name="direction" readonly="state != 'draft'"/>
                            <field name="date_request"/>
                            <field name="requested_by_id" readonly="1"/>
                            <field name="department_id"/>
                            <field name="company_id" groups="base.group_multi_company"/>
                        </group>
                        <group>
                            <field name="origin_ref" readonly="state != 'draft'"
                                   options="{'no_create': True}"/>
                            <field name="partner_id" readonly="state != 'draft'"/>
                            <field name="ar_billing_mode" invisible="direction != 'ar'"/>
                            <field name="move_type" invisible="1"/>
                            <field name="target_move_id" readonly="1"/>
                            <field name="currency_id" invisible="1"/>
                        </group>
                    </group>
                    <notebook>
                        <page string="Lines / รายการ" name="lines">
                            <field name="line_ids" readonly="state == 'invoiced'">
                                <list editable="bottom">
                                    <field name="sequence" widget="handle"/>
                                    <field name="product_id"/>
                                    <field name="name"/>
                                    <field name="quantity"/>
                                    <field name="product_uom_id" groups="uom.group_uom"/>
                                    <field name="price_unit"/>
                                    <field name="discount"/>
                                    <field name="qty_ordered" readonly="1"/>
                                    <field name="qty_already_requested" readonly="1"/>
                                    <field name="remaining_to_bill" readonly="1"/>
                                </list>
                            </field>
                        </page>
                        <page string="Evidence / หลักฐาน" name="evidence">
                            <field name="evidence_ok" invisible="1"/>
                            <field name="evidence_ids">
                                <list editable="bottom">
                                    <field name="name"/>
                                    <field name="evidence_type_id"/>
                                    <field name="is_verified"/>
                                    <field name="attachment_count"/>
                                </list>
                            </field>
                        </page>
                        <page string="AP Original / ต้นฉบับจริง" name="ap_original"
                              invisible="direction != 'ap'">
                            <group>
                                <field name="original_received"/>
                                <field name="original_received_date"/>
                                <field name="original_received_by_id"/>
                            </group>
                        </page>
                        <page string="Other Info / ข้อมูลอื่น" name="other">
                            <field name="reject_reason" invisible="state != 'rejected'"/>
                            <field name="note"/>
                        </page>
                    </notebook>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_follower_ids"/>
                    <field name="activity_ids"/>
                    <field name="message_ids"/>
                </div>
            </form>
        </field>
    </record>

    <!-- ============ LIST ============ -->
    <record id="view_od19_billing_request_list" model="ir.ui.view">
        <field name="name">od19.billing.request.list</field>
        <field name="model">od19.billing.request</field>
        <field name="arch" type="xml">
            <list string="Billing Requests" decoration-muted="state in ('cancelled','rejected')">
                <field name="name"/>
                <field name="direction"/>
                <field name="date_request"/>
                <field name="partner_id"/>
                <field name="requested_by_id"/>
                <field name="origin_ref"/>
                <field name="state"/>
                <field name="target_move_id"/>
            </list>
        </field>
    </record>

    <!-- ============ KANBAN ============ -->
    <record id="view_od19_billing_request_kanban" model="ir.ui.view">
        <field name="name">od19.billing.request.kanban</field>
        <field name="model">od19.billing.request</field>
        <field name="arch" type="xml">
            <kanban default_group_by="state">
                <field name="name"/>
                <field name="direction"/>
                <field name="partner_id"/>
                <field name="date_request"/>
                <templates>
                    <t t-name="card">
                        <div class="o_kanban_record_title"><field name="name"/></div>
                        <div><field name="partner_id"/></div>
                        <div><field name="direction"/></div>
                        <div><field name="date_request"/></div>
                    </t>
                </templates>
            </kanban>
        </field>
    </record>

    <!-- ============ SEARCH ============ -->
    <record id="view_od19_billing_request_search" model="ir.ui.view">
        <field name="name">od19.billing.request.search</field>
        <field name="model">od19.billing.request</field>
        <field name="arch" type="xml">
            <search>
                <field name="name"/>
                <field name="partner_id"/>
                <field name="requested_by_id"/>
                <filter name="filter_ar" string="AR" domain="[('direction','=','ar')]"/>
                <filter name="filter_ap" string="AP" domain="[('direction','=','ap')]"/>
                <filter name="filter_submitted" string="Submitted"
                        domain="[('state','=','submitted')]"/>
                <group expand="0" string="Group By">
                    <filter name="group_direction" string="Direction" context="{'group_by':'direction'}"/>
                    <filter name="group_state" string="Status" context="{'group_by':'state'}"/>
                </group>
            </search>
        </field>
    </record>

    <!-- ============ ACTIONS ============ -->
    <record id="action_od19_billing_request" model="ir.actions.act_window">
        <field name="name">Billing Requests / คำขอเปิดบิล</field>
        <field name="res_model">od19.billing.request</field>
        <field name="view_mode">list,kanban,form</field>
        <field name="search_view_id" ref="view_od19_billing_request_search"/>
    </record>

    <record id="action_od19_billing_request_queue" model="ir.actions.act_window">
        <field name="name">Billing Queue / คิวรอออกบิล</field>
        <field name="res_model">od19.billing.request</field>
        <field name="view_mode">list,kanban,form</field>
        <field name="domain">[('state', '=', 'submitted')]</field>
        <field name="context">{'search_default_group_direction': 1}</field>
        <field name="search_view_id" ref="view_od19_billing_request_search"/>
    </record>
</odoo>
```

`views/billing_request_menus.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <menuitem id="menu_od19_billing_request_root"
              name="Billing Requests / คำขอเปิดบิล"
              web_icon="od19_billing_request,static/description/icon.svg"
              groups="od19_billing_request.group_od19_billing_requester,od19_billing_request.group_od19_billing_accounting"
              sequence="60"/>

    <menuitem id="menu_od19_billing_request_all"
              name="All Requests / คำขอทั้งหมด"
              parent="menu_od19_billing_request_root"
              action="action_od19_billing_request"
              sequence="10"/>

    <menuitem id="menu_od19_billing_request_queue"
              name="Billing Queue / คิวรอออกบิล"
              parent="menu_od19_billing_request_root"
              action="action_od19_billing_request_queue"
              groups="od19_billing_request.group_od19_billing_accounting"
              sequence="20"/>
</odoo>
```

`__manifest__.py` `data` เปิด views:

```python
    "data": [
        "security/od19_billing_request_security.xml",
        "security/ir.model.access.csv",
        "data/od19_billing_request_data.xml",
        "views/billing_request_views.xml",
        "views/billing_request_menus.xml",
    ],
```

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_billing_request`
Expected: PASS — `0 failed, 0 error(s)`

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_billing_request
git commit -m "feat(od19_billing_request): add views, billing queue and menus"
```

---

## Task 10: คำแปลไทย + รันเทสต์ครบชุด

**Files:**
- Create: `custom_addons/od19_billing_request/i18n/th.po`
- Modify: `custom_addons/od19_billing_request/__manifest__.py`

- [ ] **Step 1: สร้างไฟล์คำแปล**

`i18n/th.po`:

```po
# Translation of Odoo Server.
# This file contains the translation of the following modules:
# 	* od19_billing_request
#
msgid ""
msgstr ""
"Project-Id-Version: Odoo Server 19.0\n"
"Report-Msgid-Bugs-To: \n"
"POT-Creation-Date: 2026-11-02 08:00+0000\n"
"PO-Revision-Date: 2026-11-02 08:00+0000\n"
"Last-Translator: The Auto-Info Co., Ltd.\n"
"Language-Team: Thai\n"
"Language: th\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Plural-Forms: nplurals=1; plural=0;\n"

#. module: od19_billing_request
#: model:ir.model,name:od19_billing_request.model_od19_billing_request
msgid "OD19 Billing Request"
msgstr "คำขอเปิดบิล"

#. module: od19_billing_request
#: model:ir.model,name:od19_billing_request.model_od19_billing_request_line
msgid "OD19 Billing Request Line"
msgstr "รายการคำขอเปิดบิล"

#. module: od19_billing_request
#: code:addons/od19_billing_request/models/billing_request.py:0
msgid "Add at least one line before submitting."
msgstr "กรุณาเพิ่มรายการอย่างน้อย 1 รายการก่อนส่งให้บัญชี"

#. module: od19_billing_request
#: code:addons/od19_billing_request/models/billing_request.py:0
msgid "Add at least one line before creating the document."
msgstr "กรุณาเพิ่มรายการอย่างน้อย 1 รายการก่อนออกบิล"

#. module: od19_billing_request
#: code:addons/od19_billing_request/models/billing_request.py:0
msgid "This request already has a target document."
msgstr "คำขอนี้ออกบิลแล้ว"

#. module: od19_billing_request
#: model_terms:ir.ui.view,arch_db:od19_billing_request.view_od19_billing_request_form
msgid "Billing Request"
msgstr "คำขอเปิดบิล"

#. module: od19_billing_request
#: model_terms:ir.ui.view,arch_db:od19_billing_request.view_od19_billing_request_form
msgid "Submit / ส่งให้บัญชี"
msgstr "ส่งให้บัญชี"

#. module: od19_billing_request
#: model_terms:ir.ui.view,arch_db:od19_billing_request.view_od19_billing_request_form
msgid "Create Invoice/Bill / ออกบิล"
msgstr "ออกบิล"

#. module: od19_billing_request
#: model_terms:ir.ui.view,arch_db:od19_billing_request.view_od19_billing_request_form
msgid "Lines / รายการ"
msgstr "รายการ"

#. module: od19_billing_request
#: model_terms:ir.ui.view,arch_db:od19_billing_request.view_od19_billing_request_form
msgid "Evidence / หลักฐาน"
msgstr "หลักฐาน"

#. module: od19_billing_request
#: model:ir.actions.act_window,name:od19_billing_request.action_od19_billing_request_queue
msgid "Billing Queue / คิวรอออกบิล"
msgstr "คิวรอออกบิล"
```

- [ ] **Step 2: ลงทะเบียน i18n ใน manifest (ไม่บังคับ — Odoo โหลดโฟลเดอร์ `i18n` อัตโนมัติ)**

ตรวจว่าไฟล์อยู่ที่ `custom_addons/od19_billing_request/i18n/th.po` (ไม่ต้องใส่ใน `data`)

- [ ] **Step 3: ตั้งภาษาผู้ใช้เป็นไทยและตรวจคำแปลโหลด**

Run:
```powershell
powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_billing_request
```
Expected: PASS — `0 failed, 0 error(s)` และ log ไม่มี `WARNING` เรื่อง PO syntax

- [ ] **Step 4: รันเทสต์โมดูลที่เกี่ยวข้องเพื่อกันผลกระทบ (regression)**

Run:
```powershell
powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_billing_request,od19_document_pull,od19_sales_billing_evidence
```
Expected: PASS — `0 failed, 0 error(s)`

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_billing_request
git commit -m "chore(od19_billing_request): add Thai translations and verify regression suite"
```

---

## Self-Review (ตรวจแผนกับสเปก)

| สเปก | Task ที่รองรับ | สถานะ |
|---|---|---|
| R1 ผู้แจ้งสร้างคำขอจากต้นทางของตน (ไม่พิมพ์เอง) | Task 5 | ครอบคลุม |
| R2 เปิดหลายรอบ/บางรายการ + กันซ้ำ/เกิน | Task 3, Task 5 | ครอบคลุม |
| R3 คำขอ ↔ เอกสารปลายทาง 1:1 + ตรวจย้อนกลับ | Task 7, Task 8 | ครอบคลุม |
| R4 บังคับหลักฐานตามทิศทาง | Task 6 (AR), Task 8 (AP) | ครอบคลุม |
| R5 AP "รับต้นฉบับจริง" block ก่อนออกบิล | Task 8 | ครอบคลุม |
| R6 AR 1 ขั้น/2 ขั้น ต่อลูกค้า/งาน | Task 4 (`ar_billing_mode` resolve) | ครอบคลุม (โหมด `two_step` ทำงานผ่าน draft move แล้ว Post — ใช้ `account.move` เดียว) |
| R7 แจ้งเตือนบัญชีเมื่อ Submit (ไม่มีการอนุมัติ) | Task 6 | ครอบคลุม |
| R8 ต่อยอดของเดิม (document pull, evidence, sequence) | Task 1, 4, 5 | ครอบคลุม |
| R9 ไม่แตะ Odoo core | ทุก Task (เฉพาะ `custom_addons/od19_billing_request`) | ครอบคลุม |
| เกณฑ์ยอมรับ 1–8 (§9) | Task 1–10 + regression Task 10 | ครอบคลุม |
| Views/menus/Billing Queue (§4.7) | Task 9 | ครอบคลุม |
| Sequence แยกทิศทาง (§4.8) | Task 1 | ครอบคลุม |
| คำแปลไทย | Task 10 | ครอบคลุม |

**Placeholder scan:** ไม่มี "TBD/TODO/implement later" — ทุก step มีโค้ด/คำสั่งจริง

**Type consistency:** ชื่อโมเดล `od19.billing.request` / `od19.billing.request.line`, เมธอด `action_submit` / `action_create_invoice` / `_od19_pull_*` / `_od19_check_before_create_document` / `_od19_build_move` / `_od19_link_target_lines` / `_compute_quantities` / `_compute_evidence_ok` ถูกใช้ตรงกันทุก Task; ฟิลด์ `evidence_ok`, `original_received`, `billing_request_id` ตรงกันระหว่าง Task 4/6/8

**ประเด็นที่ต้องตัดสินใจตอน implement:** การ match `target_line_id` ใน Task 7 ใช้ลำดับบรรทัด (zip) — ถ้า Odoo จัดลำดับต่างจากที่ส่ง ให้เปลี่ยนเป็นการค้นด้วย `sale_line_ids` / `purchase_line_id`

---

## Execution Handoff

แผนบันทึกที่ `docs/superpowers/plans/2026-11-02-od19-billing-request-implementation-plan.md` แล้ว — เลือกวิธีดำเนินการ:

1. **Subagent-Driven (แนะนำ)** — dispatch subagent ใหม่ต่อ Task, รีวิวระหว่าง Task, วนเร็ว
2. **Inline Execution** — ทำในเซสชันนี้ด้วย executing-plans แบบมี checkpoint

เลือกวิธีไหนครับ?
