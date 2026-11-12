# od19_document_hub Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** สร้างโมดูล `od19_document_hub` — ชั้น metadata หมวดหมู่ ระดับความลับ และการค้นหาข้อความบน `ir.attachment` ของ Odoo 19 โดยไม่แตะไฟล์ core

**Architecture:** ขยาย `ir.attachment` ผ่าน `_inherit` แล้วเพิ่มโมเดลอ้างอิงใหม่ 3 ตัว (`od19.document.category` แบบ tree, `od19.document.retention.policy`, `od19.document.extract`) พร้อม mixin สำหรับเก็บรายงานที่สร้างภายใน ค้นหาภาษาไทยด้วยดัชนี GIN `pg_trgm` ที่สร้างผ่าน `pre_init_hook` + `models.Index`

**Tech Stack:** Odoo 19 (Python 3), PostgreSQL 16 + `pg_trgm`, `pdfminer.six` (เฟสถัดไป), PowerShell `run-tests.ps1`

**อ้างอิงสเปก:** [2026-11-11-od19-document-hub-design.md](../specs/2026-11-11-od19-document-hub-design.md)

---

## ขอบเขตของแผนนี้

แผนนี้ครอบคลุม **P0 (baseline) + P1 (`od19_document_hub`)** เท่านั้น ตาม §11 ของสเปก

- ออกของแผนนี้: `od19_document_intake` (P2 = เป้า 4) และ `od19_document_governance` (P4/P5 = เป้า 3, 1) → เขียนแผนแยก
- การค้นหาแบบ facet ใน UI (P3 = เป้า 2) รวมอยู่ใน Task 8 ของแผนนี้ เพราะอยู่ในโมดูล hub
- Record rule กรองตาม `od19_confidentiality` / `od19_department_id` → ย้ายไปแผน governance (P4) เพราะ Odoo รวม record rule ของกลุ่มด้วย OR การเพิ่ม rule บน `ir.attachment` ใน P1 เสี่ยงขยายสิทธิ์ของ core

## ขั้นเตรียมการ (ทำครั้งเดียวก่อนเริ่ม)

- [ ] **เตรียม 1: สร้าง worktree + branch**

> ต้องถือ lease `git:worktree` ก่อน (Tier 2). ถ้าไม่ว่าง ให้รอจนหมดอายุ ห้าม break

```powershell
pwsh -File .\agent-lock.ps1 -Action Acquire -Resource git:worktree -AgentId trae-od19_document_hub -Purpose "create worktree feature/od19_document_hub" -Ttl 600
git worktree add ..\od19_doc_hub -b feature/od19_document_hub 19.0
```

- [ ] **เตรียม 2: ตรวจ `pg_trgm` (เงื่อนไขตั้งต้นของ P0)**

Run:
```powershell
psql -U odoo -d odoo19_pdev -c "SELECT extname FROM pg_extension WHERE extname='pg_trgm';"
```
Expected: มีแถว `pg_trgm` หรือว่าง (ถ้าว่าง ต้องมีสิทธิ์สร้าง extension — ตรวจใน Task 1)

---

## โครงสร้างไฟล์

```
custom_addons/od19_document_hub/
├── __init__.py
├── __manifest__.py
├── hooks.py                              # pre_init_hook: CREATE EXTENSION pg_trgm
├── models/
│   ├── __init__.py
│   ├── od19_document_retention_policy.py
│   ├── od19_document_category.py
│   ├── od19_document_extract.py
│   ├── ir_attachment.py
│   └── report_archive_mixin.py
├── views/
│   ├── od19_document_category_views.xml
│   ├── od19_document_retention_policy_views.xml
│   ├── ir_attachment_views.xml
│   └── od19_document_hub_menus.xml
├── security/
│   ├── od19_document_hub_security.xml
│   └── ir.model.access.csv
├── data/
│   └── od19_document_category_data.xml
├── tests/
│   ├── __init__.py
│   ├── test_document_hub_module.py
│   ├── test_document_hub_category.py
│   ├── test_document_hub_extract.py
│   └── test_document_archive_report.py
└── i18n/
    └── th.po
```

**คำสั่งทดสอบที่ใช้ทั้งแผน** (DB ทดสอบส่วนตัวตาม AGENTS.md §6):
```powershell
pwsh -File .\run-tests.ps1 -Module od19_document_hub -Database odoo19_t_doc_hub -HttpPort 8081
```

---

### Task 1: Module skeleton + pg_trgm hook

**Files:**
- Create: `custom_addons/od19_document_hub/__init__.py`
- Create: `custom_addons/od19_document_hub/hooks.py`
- Create: `custom_addons/od19_document_hub/__manifest__.py`
- Create: `custom_addons/od19_document_hub/models/__init__.py`
- Create: `custom_addons/od19_document_hub/tests/__init__.py`
- Create: `custom_addons/od19_document_hub/tests/test_document_hub_module.py`

- [ ] **Step 1: เขียนไฟล์ package และ hook**

`custom_addons/od19_document_hub/__init__.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from .hooks import pre_init_hook
from . import models
```

`custom_addons/od19_document_hub/hooks.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
import logging

_logger = logging.getLogger(__name__)


def pre_init_hook(env):
    """สร้าง extension pg_trgm ก่อนติดตั้ง เพื่อให้ดัชนี GIN trigram สร้างได้"""
    env.cr.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    _logger.info("od19_document_hub: pg_trgm extension พร้อมใช้งาน")
```

`custom_addons/od19_document_hub/models/__init__.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
```

`custom_addons/od19_document_hub/tests/__init__.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from . import test_document_hub_module
```

- [ ] **Step 2: เขียน manifest**

`custom_addons/od19_document_hub/__manifest__.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "OD19 Document Hub",
    "version": "19.0.1.0.0",
    "category": "Document Management",
    "summary": "ศูนย์กลาง metadata หมวด และการค้นหาเอกสารแนบ (ir.attachment)",
    "author": "TRAE",
    "license": "LGPL-3",
    "depends": ["base", "mail", "hr", "od19_thai_font_support"],
    "pre_init_hook": "pre_init_hook",
    "data": [
        "security/od19_document_hub_security.xml",
        "security/ir.model.access.csv",
        "data/od19_document_category_data.xml",
        "views/od19_document_category_views.xml",
        "views/od19_document_retention_policy_views.xml",
        "views/ir_attachment_views.xml",
        "views/od19_document_hub_menus.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
```

- [ ] **Step 3: เขียน smoke test (ยังต้องล้มเหลว)**

`custom_addons/od19_document_hub/tests/test_document_hub_module.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDocumentHubModule(TransactionCase):
    """ตรวจว่า extension pg_trgm พร้อม และ module ติดตั้งได้"""

    def test_pg_trgm_extension_installed(self):
        self.env.cr.execute(
            "SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'"
        )
        self.assertTrue(self.env.cr.fetchone(), "ต้องมี extension pg_trgm")
```

- [ ] **Step 4: รันเทสต์เพื่อยืนยันว่า FAIL (module ยังไม่มี data files)**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_hub -Database odoo19_t_doc_hub -HttpPort 8081`
Expected: FAIL — parse error เพราะ `data` อ้างไฟล์ `security/...` ที่ยังไม่มี

- [ ] **Step 5: สร้างไฟล์ปลายทางว่างชั่วคราวเพื่อให้ติดตั้งผ่าน**

สร้างไฟล์ XML เปล่า (จะเติมใน Task ถัดไป):

`custom_addons/od19_document_hub/security/od19_document_hub_security.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo/>
```
`custom_addons/od19_document_hub/security/ir.model.access.csv`
```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
```
`custom_addons/od19_document_hub/data/od19_document_category_data.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo/>
```
`custom_addons/od19_document_hub/views/od19_document_category_views.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo/>
```
`custom_addons/od19_document_hub/views/od19_document_retention_policy_views.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo/>
```
`custom_addons/od19_document_hub/views/ir_attachment_views.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo/>
```
`custom_addons/od19_document_hub/views/od19_document_hub_menus.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo/>
```

- [ ] **Step 6: รันเทสต์เพื่อยืนยันว่า PASS**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_hub -Database odoo19_t_doc_hub -HttpPort 8081`
Expected: PASS — 1 test, 0 failed, 0 error

- [ ] **Step 7: Commit**

```powershell
git add custom_addons/od19_document_hub
git commit -m "feat(od19_document_hub): scaffold module with pg_trgm pre-init hook"
```

---

### Task 2: โมเดล `od19.document.retention.policy`

**Files:**
- Create: `custom_addons/od19_document_hub/models/od19_document_retention_policy.py`
- Modify: `custom_addons/od19_document_hub/models/__init__.py`
- Test: `custom_addons/od19_document_hub/tests/test_document_hub_category.py`

- [ ] **Step 1: เขียนเทสต์ที่ล้มเหลว**

`custom_addons/od19_document_hub/tests/test_document_hub_category.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestRetentionPolicy(TransactionCase):

    def test_create_policy(self):
        policy = self.env["od19.document.retention.policy"].create({
            "name": "บัญชี 5 ปี",
            "duration_month": 60,
            "action": "delete",
        })
        self.assertEqual(policy.duration_month, 60)

    def test_duration_must_be_positive(self):
        with self.assertRaises(Exception):
            with self.cr.savepoint():
                self.env["od19.document.retention.policy"].create({
                    "name": "ผิด", "duration_month": 0, "action": "review",
                })
```

- [ ] **Step 2: รันเทสต์เพื่อยืนยันว่า FAIL**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_hub -Database odoo19_t_doc_hub -HttpPort 8081`
Expected: FAIL — `KeyError`/`ValueError` เพราะโมเดลยังไม่มี

- [ ] **Step 3: เขียนโมเดล**

`custom_addons/od19_document_hub/models/od19_document_retention_policy.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


RETENTION_ACTION = [
    ("review", "ทบทวนก่อนตัดสินใจ"),
    ("archive", "เก็บถาวร (Archive)"),
    ("delete", "ทำลาย (Delete)"),
]


class Od19DocumentRetentionPolicy(models.Model):
    _name = "od19.document.retention.policy"
    _description = "นโยบายการเก็บรักษาเอกสาร"
    _order = "duration_month, name"

    name = fields.Char("ชื่อนโยบาย", required=True, translate=True)
    duration_month = fields.Integer("อายุ (เดือน)", required=True, default=60)
    action = fields.Selection(
        RETENTION_ACTION, "การจัดการเมื่อครบกำหนด", required=True, default="review",
    )
    basis = fields.Char(
        "อ้างอิงกฎหมาย/เหตุผล",
        help="เช่น พระราชบัญญัติการบัญชี พ.ศ. 2543 มาตรา 14",
    )
    category_ids = fields.One2many(
        "od19.document.category", "default_retention_policy_id", "หมวดที่ใช้",
    )
    active = fields.Boolean(default=True)

    _duration_positive = models.Constraint(
        "CHECK(duration_month > 0)",
        "อายุการเก็บรักษาต้องมากกว่า 0 เดือน",
    )
```

- [ ] **Step 4: เพิ่ม import**

`custom_addons/od19_document_hub/models/__init__.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from . import od19_document_retention_policy
```

- [ ] **Step 5: รันเทสต์เพื่อยืนยันว่า PASS**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_hub -Database odoo19_t_doc_hub -HttpPort 8081`
Expected: PASS

- [ ] **Step 6: Commit**

```powershell
git add custom_addons/od19_document_hub/models/od19_document_retention_policy.py custom_addons/od19_document_hub/models/__init__.py custom_addons/od19_document_hub/tests/test_document_hub_category.py
git commit -m "feat(od19_document_hub): add retention policy model"
```

---

### Task 3: โมเดล `od19.document.category` (tree)

**Files:**
- Create: `custom_addons/od19_document_hub/models/od19_document_category.py`
- Modify: `custom_addons/od19_document_hub/models/__init__.py`
- Test: `custom_addons/od19_document_hub/tests/test_document_hub_category.py`

- [ ] **Step 1: เขียนเทสต์ที่ล้มเหลว (ต่อท้ายไฟล์เดิม)**

เพิ่มคลาสใน `tests/test_document_hub_category.py`
```python
@tagged("post_install", "-at_install")
class TestDocumentCategory(TransactionCase):

    def test_complete_name(self):
        parent = self.env["od19.document.category"].create({"name": "จัดซื้อ", "code": "PUR"})
        child = self.env["od19.document.category"].create({
            "name": "ใบสั่งซื้อ", "code": "PUR_PO", "parent_id": parent.id,
        })
        self.assertEqual(child.complete_name, "จัดซื้อ / ใบสั่งซื้อ")

    def test_code_unique(self):
        self.env["od19.document.category"].create({"name": "A", "code": "DUP"})
        with self.assertRaises(Exception):
            with self.cr.savepoint():
                self.env["od19.document.category"].create({"name": "B", "code": "DUP"})

    def test_no_parent_cycle(self):
        a = self.env["od19.document.category"].create({"name": "A", "code": "CYC_A"})
        b = self.env["od19.document.category"].create({"name": "B", "code": "CYC_B", "parent_id": a.id})
        with self.assertRaises(ValidationError):
            with self.cr.savepoint():
                a.parent_id = b.id
```

- [ ] **Step 2: รันเทสต์เพื่อยืนยันว่า FAIL**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_hub -Database odoo19_t_doc_hub -HttpPort 8081`
Expected: FAIL — โมเดล `od19.document.category` ยังไม่มี

- [ ] **Step 3: เขียนโมเดล**

`custom_addons/od19_document_hub/models/od19_document_category.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class Od19DocumentCategory(models.Model):
    _name = "od19.document.category"
    _description = "หมวดหมู่เอกสาร"
    _parent_name = "parent_id"
    _parent_store = True
    _rec_name = "complete_name"
    _order = "complete_name, id"

    name = fields.Char("ชื่อหมวด", required=True, translate=True)
    code = fields.Char("รหัส", required=True)
    complete_name = fields.Char(
        "ชื่อเต็ม", compute="_compute_complete_name", store=True, recursive=True,
    )
    parent_id = fields.Many2one(
        "od19.document.category", "หมวดแม่", ondelete="restrict", index=True,
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        "od19.document.category", "parent_id", "หมวดย่อย",
    )
    default_retention_policy_id = fields.Many2one(
        "od19.document.retention.policy", "นโยบายอายุเริ่มต้น", ondelete="restrict",
    )
    auto_classify = fields.Boolean("จัดหมวดอัตโนมัติ", default=True)
    allowed_models = fields.Char(
        "โมเดลที่ผูกได้",
        help="รายชื่อ res_model คั่นด้วยจุลภาค ถ้าว่าง = ผูกได้ทุกโมเดล",
    )
    active = fields.Boolean(default=True)

    _code_uniq = models.Constraint("UNIQUE(code)", "รหัสหมวดต้องไม่ซ้ำ")

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = (
                    f"{category.parent_id.complete_name} / {category.name}"
                )
            else:
                category.complete_name = category.name

    @api.constrains("parent_id")
    def _check_parent_recursion(self):
        if self._has_cycle():
            raise ValidationError(
                _("ไม่สามารถตั้งหมวดแม่ให้เป็นหมวดลูกของตัวเองได้")
            )
```

- [ ] **Step 4: เพิ่ม import**

`custom_addons/od19_document_hub/models/__init__.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from . import od19_document_retention_policy
from . import od19_document_category
```

- [ ] **Step 5: รันเทสต์เพื่อยืนยันว่า PASS**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_hub -Database odoo19_t_doc_hub -HttpPort 8081`
Expected: PASS

- [ ] **Step 6: Commit**

```powershell
git add custom_addons/od19_document_hub/models/od19_document_category.py custom_addons/od19_document_hub/models/__init__.py custom_addons/od19_document_hub/tests/test_document_hub_category.py
git commit -m "feat(od19_document_hub): add document category tree model"
```

---

### Task 4: กลุ่มสิทธิ์ + สิทธิ์เข้าถึงโมเดล

**Files:**
- Modify: `custom_addons/od19_document_hub/security/od19_document_hub_security.xml`
- Modify: `custom_addons/od19_document_hub/security/ir.model.access.csv`

- [ ] **Step 1: เขียนกลุ่มสิทธิ์**

`security/od19_document_hub_security.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="module_category_od19_document" model="ir.module.category">
        <field name="name">Document Hub</field>
        <field name="description">การบริหารจัดการเอกสารแนบ</field>
        <field name="sequence">50</field>
    </record>

    <record id="group_document_user" model="res.groups">
        <field name="name">Document User</field>
        <field name="category_id" ref="module_category_od19_document"/>
    </record>

    <record id="group_document_manager" model="res.groups">
        <field name="name">Document Manager</field>
        <field name="category_id" ref="module_category_od19_document"/>
        <field name="implied_ids" eval="[(4, ref('group_document_user'))]"/>
    </record>

    <record id="group_document_auditor" model="res.groups">
        <field name="name">Document Auditor</field>
        <field name="category_id" ref="module_category_od19_document"/>
        <field name="implied_ids" eval="[(4, ref('group_document_user'))]"/>
    </record>
</odoo>
```

- [ ] **Step 2: เขียนสิทธิ์เข้าถึงโมเดล**

`security/ir.model.access.csv`
```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_od19_document_category_user,od19.document.category.user,model_od19_document_category,od19_document_hub.group_document_user,1,0,0,0
access_od19_document_category_manager,od19.document.category.manager,model_od19_document_category,od19_document_hub.group_document_manager,1,1,1,1
access_od19_retention_policy_user,od19.document.retention.policy.user,model_od19_document_retention_policy,od19_document_hub.group_document_user,1,0,0,0
access_od19_retention_policy_manager,od19.document.retention.policy.manager,model_od19_document_retention_policy,od19_document_hub.group_document_manager,1,1,1,1
access_od19_document_extract_manager,od19.document.extract.manager,model_od19_document_extract,od19_document_hub.group_document_manager,1,1,1,1
```

- [ ] **Step 3: รันเทสต์ (ต้องไม่พัง)**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_hub -Database odoo19_t_doc_hub -HttpPort 8081`
Expected: PASS — ไม่มี parse error (ถ้า `model_od19_document_extract` ยังไม่มี จะ error → รอ Task 6 แล้วรันซ้ำก่อน commit)

- [ ] **Step 4: Commit**

```powershell
git add custom_addons/od19_document_hub/security
git commit -m "feat(od19_document_hub): add security groups and model access"
```

---

### Task 5: ขยาย `ir.attachment` ด้วยฟิลด์ metadata

**Files:**
- Create: `custom_addons/od19_document_hub/models/ir_attachment.py`
- Modify: `custom_addons/od19_document_hub/models/__init__.py`

- [ ] **Step 1: เขียนเทสต์ที่ล้มเหลว**

สร้าง `custom_addons/od19_document_hub/tests/test_document_hub_attachment.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64
import datetime

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAttachmentMetadata(TransactionCase):

    def test_defaults(self):
        att = self.env["ir.attachment"].create({
            "name": "a.txt", "datas": base64.b64encode(b"hello"),
        })
        self.assertEqual(att.od19_origin, "external")
        self.assertEqual(att.od19_confidentiality, "internal")
        self.assertEqual(att.od19_index_state, "none")

    def test_retention_until_computed(self):
        policy = self.env["od19.document.retention.policy"].create({
            "name": "5 ปี", "duration_month": 60, "action": "delete",
        })
        att = self.env["ir.attachment"].create({
            "name": "b.txt",
            "datas": base64.b64encode(b"x"),
            "od19_doc_date": datetime.date(2026, 1, 31),
            "od19_retention_policy_id": policy.id,
        })
        self.assertEqual(att.od19_retention_until, datetime.date(2031, 1, 31))

    def test_duplicate_count(self):
        payload = base64.b64encode(b"same-bytes")
        a1 = self.env["ir.attachment"].create({"name": "d1.txt", "datas": payload})
        a2 = self.env["ir.attachment"].create({"name": "d2.txt", "datas": payload})
        self.assertEqual(a1.checksum, a2.checksum)
        self.assertTrue(a1.od19_duplicate_count >= 1)
```

- [ ] **Step 2: รันเทสต์เพื่อยืนยันว่า FAIL**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_hub -Database odoo19_t_doc_hub -HttpPort 8081`
Expected: FAIL — ฟิลด์ `od19_origin` ไม่มี

- [ ] **Step 3: เขียนส่วนขยาย**

`custom_addons/od19_document_hub/models/ir_attachment.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


ORIGIN_SELECTION = [
    ("external", "รับจากภายนอก"),
    ("internal", "สร้างจากระบบ"),
    ("legacy15", "ยกมาจาก Odoo 15"),
]

CONFIDENTIALITY_SELECTION = [
    ("public", "สาธารณะ"),
    ("internal", "ภายใน"),
    ("confidential", "ความลับ"),
    ("secret", "ลับมาก"),
]

INDEX_STATE_SELECTION = [
    ("none", "ยังไม่เข้าคิว"),
    ("pending", "รอสกัด"),
    ("done", "สกัดแล้ว"),
    ("failed", "ล้มเหลว"),
    ("skipped", "ข้าม"),
]


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    od19_category_id = fields.Many2one(
        "od19.document.category", "หมวดเอกสาร", ondelete="restrict", index=True,
    )
    od19_origin = fields.Selection(
        ORIGIN_SELECTION, "ที่มา", default="external", index=True,
    )
    od19_doc_date = fields.Date("วันที่บนเอกสาร", index=True)
    od19_partner_id = fields.Many2one(
        "res.partner", "คู่ค้า", ondelete="set null", index=True,
    )
    od19_department_id = fields.Many2one(
        "hr.department", "แผนก", ondelete="set null", index=True,
    )
    od19_confidentiality = fields.Selection(
        CONFIDENTIALITY_SELECTION, "ระดับความลับ", default="internal", index=True,
    )
    od19_retention_policy_id = fields.Many2one(
        "od19.document.retention.policy", "นโยบายอายุ", ondelete="restrict",
    )
    od19_retention_until = fields.Date(
        "ครบกำหนดเก็บรักษา",
        compute="_compute_od19_retention_until",
        store=True,
        readonly=True,
        index=True,
    )
    od19_legal_hold = fields.Boolean("ห้ามทำลาย", index=True)
    od19_index_state = fields.Selection(
        INDEX_STATE_SELECTION, "สถานะสกัดข้อความ", default="none", index=True,
    )
    od19_indexed_at = fields.Datetime("สกัดเมื่อ", readonly=True)
    od19_source_ref = fields.Char(
        "เลขอ้างอิงต้นทาง", help="เลขที่เอกสารต้นทางที่ระบบสร้าง",
    )
    od19_duplicate_count = fields.Integer(
        "ระเบียนที่ใช้ไฟล์เดียวกัน", compute="_compute_od19_duplicate_count",
    )

    _od19_name_trgm = models.Index("USING gin (name gin_trgm_ops)")

    @api.depends(
        "od19_doc_date",
        "od19_retention_policy_id",
        "od19_retention_policy_id.duration_month",
    )
    def _compute_od19_retention_until(self):
        for attachment in self:
            policy = attachment.od19_retention_policy_id
            base_date = attachment.od19_doc_date
            if policy and policy.duration_month and base_date:
                attachment.od19_retention_until = fields.Date.add(
                    base_date, months=policy.duration_month,
                )
            else:
                attachment.od19_retention_until = False

    @api.depends("checksum")
    def _compute_od19_duplicate_count(self):
        for attachment in self:
            if attachment.checksum:
                attachment.od19_duplicate_count = self.search_count([
                    ("checksum", "=", attachment.checksum),
                    ("id", "!=", attachment.id),
                ])
            else:
                attachment.od19_duplicate_count = 0
```

- [ ] **Step 4: เพิ่ม import**

`custom_addons/od19_document_hub/models/__init__.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from . import od19_document_retention_policy
from . import od19_document_category
from . import od19_document_extract
from . import ir_attachment
```
> หมายเหตุ: `od19_document_extract` จะถูกเพิ่มจริงใน Task 6 — ถ้ายังไม่มี ให้คอมเมนต์บรรทัดนั้นไว้ชั่วคราว

- [ ] **Step 5: รันเทสต์เพื่อยืนยันว่า PASS**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_hub -Database odoo19_t_doc_hub -HttpPort 8081`
Expected: PASS

- [ ] **Step 6: Commit**

```powershell
git add custom_addons/od19_document_hub/models/ir_attachment.py custom_addons/od19_document_hub/models/__init__.py custom_addons/od19_document_hub/tests/test_document_hub_attachment.py
git commit -m "feat(od19_document_hub): extend ir.attachment with od19 metadata fields"
```

---

### Task 6: `od19.document.extract` + ดัชนี trigram บนเนื้อข้อความ

**Files:**
- Create: `custom_addons/od19_document_hub/models/od19_document_extract.py`
- Modify: `custom_addons/od19_document_hub/models/__init__.py`
- Test: `custom_addons/od19_document_hub/tests/test_document_hub_extract.py`

- [ ] **Step 1: เขียนเทสต์ที่ล้มเหลว**

`custom_addons/od19_document_hub/tests/test_document_hub_extract.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDocumentExtract(TransactionCase):

    def _make_attachment(self):
        return self.env["ir.attachment"].create({
            "name": "inv.txt", "datas": base64.b64encode(b"invoice"),
        })

    def test_create_extract(self):
        att = self._make_attachment()
        extract = self.env["od19.document.extract"].create({
            "attachment_id": att.id,
            "text_content": "ใบกำกับภาษี เลขที่ INV-2569-0001",
            "engine": "pdfminer",
            "lang": "th",
        })
        self.assertEqual(extract.attachment_id, att)

    def test_one_extract_per_attachment(self):
        att = self._make_attachment()
        self.env["od19.document.extract"].create({
            "attachment_id": att.id, "text_content": "x",
        })
        with self.assertRaises(Exception):
            with self.cr.savepoint():
                self.env["od19.document.extract"].create({
                    "attachment_id": att.id, "text_content": "y",
                })

    def test_trigram_search_thai(self):
        att = self._make_attachment()
        self.env["od19.document.extract"].create({
            "attachment_id": att.id, "text_content": "ใบเสร็จรับเงิน ค่าบริการรายเดือน",
        })
        found = self.env["od19.document.extract"].search([
            ("text_content", "ilike", "ค่าบริการ"),
        ])
        self.assertTrue(found)

    def test_cascade_delete(self):
        att = self._make_attachment()
        extract = self.env["od19.document.extract"].create({
            "attachment_id": att.id, "text_content": "z",
        })
        att.unlink()
        self.assertFalse(extract.exists())
```

- [ ] **Step 2: รันเทสต์เพื่อยืนยันว่า FAIL**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_hub -Database odoo19_t_doc_hub -HttpPort 8081`
Expected: FAIL — โมเดล `od19.document.extract` ยังไม่มี

- [ ] **Step 3: เขียนโมเดล**

`custom_addons/od19_document_hub/models/od19_document_extract.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


ENGINE_SELECTION = [
    ("core", "Odoo Core (attachment_indexation)"),
    ("pdfminer", "pdfminer.six"),
    ("manual", "กรอกด้วยมือ"),
]


class Od19DocumentExtract(models.Model):
    _name = "od19.document.extract"
    _description = "ข้อความที่สกัดได้จากเอกสารแนบ"
    _order = "id desc"

    attachment_id = fields.Many2one(
        "ir.attachment", "เอกสารแนบ", required=True, ondelete="cascade", index=True,
    )
    text_content = fields.Text("ข้อความ", prefetch=False)
    engine = fields.Selection(ENGINE_SELECTION, "ตัวสกัด", default="pdfminer")
    quality = fields.Float("คุณภาพ", digits=(3, 2))
    lang = fields.Char("ภาษา")

    _attachment_uniq = models.Constraint(
        "unique(attachment_id)",
        "เอกสารแนบนี้มีข้อความสกัดอยู่แล้ว",
    )
    _content_trgm = models.Index("USING gin (text_content gin_trgm_ops)")
```

- [ ] **Step 4: เปิด import ให้ครบ**

`custom_addons/od19_document_hub/models/__init__.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from . import od19_document_retention_policy
from . import od19_document_category
from . import od19_document_extract
from . import ir_attachment
```

- [ ] **Step 5: รันเทสต์เพื่อยืนยันว่า PASS**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_hub -Database odoo19_t_doc_hub -HttpPort 8081`
Expected: PASS — รวมเทสต์ Task 4 (access csv) ที่เคยค้าง

- [ ] **Step 6: ตรวจว่าดัชนีถูกสร้างจริง**

Run:
```powershell
psql -U odoo -d odoo19_t_doc_hub -c "\di ir_attachment*"
```
Expected: มี index ที่ใช้ `gin (name gin_trgm_ops)` และ `od19_document_extract_content_trgm`

- [ ] **Step 7: Commit**

```powershell
git add custom_addons/od19_document_hub/models/od19_document_extract.py custom_addons/od19_document_hub/models/__init__.py custom_addons/od19_document_hub/tests/test_document_hub_extract.py
git commit -m "feat(od19_document_hub): add text extract model with trigram index"
```

---

### Task 7: Mixin เก็บรายงานที่สร้างภายใน

**Files:**
- Create: `custom_addons/od19_document_hub/models/report_archive_mixin.py`
- Modify: `custom_addons/od19_document_hub/models/__init__.py`
- Test: `custom_addons/od19_document_hub/tests/test_document_archive_report.py`

- [ ] **Step 1: เขียนเทสต์ที่ล้มเหลว**

`custom_addons/od19_document_hub/tests/test_document_archive_report.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestReportArchive(TransactionCase):

    def test_archive_creates_internal_attachment(self):
        category = self.env["od19.document.category"].create({
            "name": "รายงานภาษี", "code": "RPT_TAX",
        })
        attachment = self.env["od19.report.archive.mixin"]._od19_archive_report(
            report_name="l10n_th.tax.report.pdf",
            binary_content=b"%PDF-1.4 fake",
            res_model="res.partner",
            res_id=self.env.user.partner_id.id,
            filename="tax-report.pdf",
            category_code="RPT_TAX",
        )
        self.assertEqual(attachment.od19_origin, "internal")
        self.assertEqual(attachment.od19_source_ref, "l10n_th.tax.report.pdf")
        self.assertEqual(attachment.od19_category_id, category)
        self.assertIn("tax-report", attachment.name)

    def test_archive_unknown_category_is_skipped(self):
        attachment = self.env["od19.report.archive.mixin"]._od19_archive_report(
            report_name="unknown.pdf",
            binary_content=b"x",
            res_model="res.partner",
            res_id=self.env.user.partner_id.id,
            category_code="NOT_EXIST",
        )
        self.assertFalse(attachment.od19_category_id)
```

- [ ] **Step 2: รันเทสต์เพื่อยืนยันว่า FAIL**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_hub -Database odoo19_t_doc_hub -HttpPort 8081`
Expected: FAIL — โมเดล `od19.report.archive.mixin` ยังไม่มี

- [ ] **Step 3: เขียน mixin**

`custom_addons/od19_document_hub/models/report_archive_mixin.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class Od19ReportArchiveMixin(models.AbstractModel):
    _name = "od19.report.archive.mixin"
    _description = "Mixin เก็บรายงานที่สร้างภายในเข้าแฟ้มเอกสาร"

    @api.model
    def _od19_resolve_category(self, category_code):
        if not category_code:
            return self.env["od19.document.category"]
        return self.env["od19.document.category"].search(
            [("code", "=", category_code)], limit=1,
        )

    @api.model
    def _od19_archive_report(
        self, report_name, binary_content, res_model, res_id,
        filename=None, category_code=None, doc_date=None,
    ):
        """เก็บผลลัพธ์รายงาน (bytes) เป็น ir.attachment พร้อม metadata ครบ"""
        category = self._od19_resolve_category(category_code)
        if category_code and not category:
            _logger.warning(
                "od19_document_hub: ไม่พบหมวด '%s' — เก็บรายงานโดยไม่ระบุหมวด",
                category_code,
            )
        return self.env["ir.attachment"].create({
            "name": filename or f"{report_name}.pdf",
            "datas": base64.b64encode(binary_content),
            "res_model": res_model,
            "res_id": res_id,
            "od19_origin": "internal",
            "od19_source_ref": report_name,
            "od19_doc_date": doc_date or fields.Date.context_today(self),
            "od19_category_id": category.id,
        })
```

- [ ] **Step 4: เพิ่ม import**

`custom_addons/od19_document_hub/models/__init__.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from . import od19_document_retention_policy
from . import od19_document_category
from . import od19_document_extract
from . import ir_attachment
from . import report_archive_mixin
```

- [ ] **Step 5: รันเทสต์เพื่อยืนยันว่า PASS**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_hub -Database odoo19_t_doc_hub -HttpPort 8081`
Expected: PASS

- [ ] **Step 6: Commit**

```powershell
git add custom_addons/od19_document_hub/models/report_archive_mixin.py custom_addons/od19_document_hub/models/__init__.py custom_addons/od19_document_hub/tests/test_document_archive_report.py
git commit -m "feat(od19_document_hub): add report archive mixin"
```

---

### Task 8: Views + เมนู + ค้นหา

**Files:**
- Modify: `custom_addons/od19_document_hub/views/od19_document_category_views.xml`
- Modify: `custom_addons/od19_document_hub/views/od19_document_retention_policy_views.xml`
- Modify: `custom_addons/od19_document_hub/views/ir_attachment_views.xml`
- Modify: `custom_addons/od19_document_hub/views/od19_document_hub_menus.xml`

- [ ] **Step 1: เขียน view หมวดหมู่**

`views/od19_document_category_views.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_od19_document_category_tree" model="ir.ui.view">
        <field name="name">od19.document.category.tree</field>
        <field name="model">od19.document.category</field>
        <field name="arch" type="xml">
            <list string="หมวดหมู่เอกสาร">
                <field name="complete_name"/>
                <field name="code"/>
                <field name="default_retention_policy_id"/>
                <field name="auto_classify"/>
                <field name="active" invisible="1"/>
            </list>
        </field>
    </record>

    <record id="view_od19_document_category_form" model="ir.ui.view">
        <field name="name">od19.document.category.form</field>
        <field name="model">od19.document.category</field>
        <field name="arch" type="xml">
            <form string="หมวดหมู่เอกสาร">
                <sheet>
                    <group>
                        <group>
                            <field name="name"/>
                            <field name="code"/>
                            <field name="parent_id"/>
                        </group>
                        <group>
                            <field name="default_retention_policy_id"/>
                            <field name="auto_classify"/>
                            <field name="allowed_models"/>
                            <field name="active"/>
                        </group>
                    </group>
                </sheet>
            </form>
        </field>
    </record>

    <record id="action_od19_document_category" model="ir.actions.act_window">
        <field name="name">หมวดหมู่เอกสาร</field>
        <field name="res_model">od19.document.category</field>
        <field name="view_mode">list,form</field>
    </record>
</odoo>
```

- [ ] **Step 2: เขียน view นโยบายอายุ**

`views/od19_document_retention_policy_views.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_od19_retention_policy_tree" model="ir.ui.view">
        <field name="name">od19.document.retention.policy.tree</field>
        <field name="model">od19.document.retention.policy</field>
        <field name="arch" type="xml">
            <list string="นโยบายการเก็บรักษา">
                <field name="name"/>
                <field name="duration_month"/>
                <field name="action"/>
                <field name="basis"/>
            </list>
        </field>
    </record>

    <record id="view_od19_retention_policy_form" model="ir.ui.view">
        <field name="name">od19.document.retention.policy.form</field>
        <field name="model">od19.document.retention.policy</field>
        <field name="arch" type="xml">
            <form string="นโยบายการเก็บรักษา">
                <sheet>
                    <group>
                        <field name="name"/>
                        <field name="duration_month"/>
                        <field name="action"/>
                        <field name="basis"/>
                        <field name="active"/>
                    </group>
                </sheet>
            </form>
        </field>
    </record>

    <record id="action_od19_retention_policy" model="ir.actions.act_window">
        <field name="name">นโยบายการเก็บรักษา</field>
        <field name="res_model">od19.document.retention.policy</field>
        <field name="view_mode">list,form</field>
    </record>
</odoo>
```

- [ ] **Step 3: เขียน view คลังกลาง (สืบทอดจาก core)**

`views/ir_attachment_views.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_attachment_form_od19_hub" model="ir.ui.view">
        <field name="name">ir.attachment.form.od19.hub</field>
        <field name="model">ir.attachment</field>
        <field name="inherit_id" ref="base.view_attachment_form"/>
        <field name="arch" type="xml">
            <xpath expr="//sheet/group" position="after">
                <group string="ศูนย์เอกสาร (OD19)">
                    <group>
                        <field name="od19_category_id"/>
                        <field name="od19_origin"/>
                        <field name="od19_doc_date"/>
                        <field name="od19_partner_id"/>
                    </group>
                    <group>
                        <field name="od19_department_id"/>
                        <field name="od19_confidentiality"/>
                        <field name="od19_source_ref"/>
                        <field name="od19_duplicate_count"/>
                    </group>
                </group>
            </xpath>
        </field>
    </record>

    <record id="view_attachment_tree_od19_hub" model="ir.ui.view">
        <field name="name">ir.attachment.tree.od19.hub</field>
        <field name="model">ir.attachment</field>
        <field name="inherit_id" ref="base.view_attachment_tree"/>
        <field name="arch" type="xml">
            <field name="name" position="after">
                <field name="od19_category_id"/>
                <field name="od19_origin"/>
                <field name="od19_doc_date"/>
                <field name="od19_confidentiality"/>
            </field>
        </field>
    </record>

    <record id="view_attachment_search_od19_hub" model="ir.ui.view">
        <field name="name">ir.attachment.search.od19.hub</field>
        <field name="model">ir.attachment</field>
        <field name="inherit_id" ref="base.view_attachment_search"/>
        <field name="arch" type="xml">
            <field name="name" position="after">
                <field name="od19_category_id"/>
                <field name="od19_partner_id"/>
                <field name="od19_doc_date"/>
            </field>
            <filter name="binary_filter" position="after">
                <filter name="od19_external" string="รับจากภายนอก"
                        domain="[('od19_origin','=','external')]"/>
                <filter name="od19_internal" string="สร้างจากระบบ"
                        domain="[('od19_origin','=','internal')]"/>
                <filter name="od19_index_pending" string="รอสกัดข้อความ"
                        domain="[('od19_index_state','in',['pending','failed'])]"/>
            </filter>
            <group position="inside">
                <filter name="od19_group_category" string="หมวดเอกสาร"
                        domain="[]" context="{'group_by':'od19_category_id'}"/>
                <filter name="od19_group_origin" string="ที่มา"
                        domain="[]" context="{'group_by':'od19_origin'}"/>
                <filter name="od19_group_department" string="แผนก"
                        domain="[]" context="{'group_by':'od19_department_id'}"/>
            </group>
        </field>
    </record>

    <record id="action_od19_document_hub" model="ir.actions.act_window">
        <field name="name">คลังเอกสารกลาง</field>
        <field name="res_model">ir.attachment</field>
        <field name="view_mode">list,form</field>
        <field name="search_view_id" ref="base.view_attachment_search"/>
        <field name="context">{'search_default_od19_index_pending': 0}</field>
    </record>
</odoo>
```

- [ ] **Step 4: เขียนเมนู**

`views/od19_document_hub_menus.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <menuitem id="menu_od19_document_root"
              name="ศูนย์เอกสาร"
              web_icon="od19_document_hub,static/description/icon.png"
              groups="group_document_user"
              sequence="60"/>

    <menuitem id="menu_od19_document_hub"
              name="คลังเอกสารกลาง"
              parent="menu_od19_document_root"
              action="action_od19_document_hub"
              sequence="10"/>

    <menuitem id="menu_od19_document_category"
              name="หมวดหมู่เอกสาร"
              parent="menu_od19_document_root"
              action="action_od19_document_category"
              groups="group_document_manager"
              sequence="20"/>

    <menuitem id="menu_od19_retention_policy"
              name="นโยบายการเก็บรักษา"
              parent="menu_od19_document_root"
              action="action_od19_retention_policy"
              groups="group_document_manager"
              sequence="30"/>
</odoo>
```

- [ ] **Step 5: ตรวจ XML well-formed**

Run:
```powershell
pwsh -Command "Get-ChildItem custom_addons\od19_document_hub\views\*.xml | ForEach-Object { [xml](Get-Content $_.FullName -Raw) | Out-Null; Write-Host ('OK ' + $_.Name) }"
```
Expected: `OK` ทุกไฟล์

- [ ] **Step 6: รันเทสต์ (ต้องไม่พังจากการโหลด view)**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_hub -Database odoo19_t_doc_hub -HttpPort 8081`
Expected: PASS

- [ ] **Step 7: Commit**

```powershell
git add custom_addons/od19_document_hub/views
git commit -m "feat(od19_document_hub): add hub views, facets and menus"
```

---

### Task 9: ข้อมูลตั้งต้น + คำแปลไทย

**Files:**
- Modify: `custom_addons/od19_document_hub/data/od19_document_category_data.xml`
- Create: `custom_addons/od19_document_hub/i18n/th.po`

- [ ] **Step 1: เขียนข้อมูลหมวดตั้งต้น**

`data/od19_document_category_data.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="cat_purchase" model="od19.document.category">
        <field name="name">จัดซื้อ</field>
        <field name="code">PUR</field>
    </record>
    <record id="cat_purchase_po" model="od19.document.category">
        <field name="name">ใบสั่งซื้อ</field>
        <field name="code">PUR_PO</field>
        <field name="parent_id" ref="cat_purchase"/>
    </record>
    <record id="cat_sales" model="od19.document.category">
        <field name="name">ขาย</field>
        <field name="code">SAL</field>
    </record>
    <record id="cat_sales_tax_invoice" model="od19.document.category">
        <field name="name">ใบกำกับภาษี</field>
        <field name="code">SAL_TAX</field>
        <field name="parent_id" ref="cat_sales"/>
    </record>
    <record id="cat_hr" model="od19.document.category">
        <field name="name">ทรัพยากรบุคคล</field>
        <field name="code">HR</field>
    </record>
    <record id="cat_iso" model="od19.document.category">
        <field name="name">ISO</field>
        <field name="code">ISO</field>
    </record>
    <record id="cat_report" model="od19.document.category">
        <field name="name">รายงานที่ระบบสร้าง</field>
        <field name="code">RPT</field>
    </record>
</odoo>
```

- [ ] **Step 2: เขียนคำแปลไทย**

`i18n/th.po`
```po
# Thai translation for od19_document_hub
msgid ""
msgstr ""
"Project-Id-Version: od19_document_hub 19.0.1.0.0\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Language: th\n"

#. module: od19_document_hub
#: model:ir.module.category,name:od19_document_hub.module_category_od19_document
msgid "Document Hub"
msgstr "ศูนย์เอกสาร"

#. module: od19_document_hub
#: model:res.groups,name:od19_document_hub.group_document_user
msgid "Document User"
msgstr "ผู้ใช้เอกสาร"

#. module: od19_document_hub
#: model:res.groups,name:od19_document_hub.group_document_manager
msgid "Document Manager"
msgstr "ผู้จัดการเอกสาร"

#. module: od19_document_hub
#: model:res.groups,name:od19_document_hub.group_document_auditor
msgid "Document Auditor"
msgstr "ผู้ตรวจสอบเอกสาร"
```

- [ ] **Step 3: รันเทสต์ทั้งโมดูล**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_hub -Database odoo19_t_doc_hub -HttpPort 8081`
Expected: PASS — ทั้งหมด 0 failed / 0 error

- [ ] **Step 4: Commit**

```powershell
git add custom_addons/od19_document_hub/data custom_addons/od19_document_hub/i18n
git commit -m "feat(od19_document_hub): seed categories and add Thai translation"
```

---

### Task 10: P0 baseline measurement (อ่านเท่านั้น)

**Files:**
- Create: `custom_addons/od19_document_hub/tests/test_document_hub_baseline.py`

- [ ] **Step 1: เขียนเทสต์วัด baseline (read-only, ไม่ assert ค่าตายตัว)**

`tests/test_document_hub_baseline.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBaselineMetrics(TransactionCase):
    """เก็บตัวเลข baseline ของคลังเอกสาร (รันบน DB ทดสอบ ไม่แตะข้อมูลจริง)"""

    def test_report_metrics(self):
        Attachment = self.env["ir.attachment"]
        total = Attachment.search_count([("type", "=", "binary")])
        with_checksum = Attachment.search_count([("checksum", "!=", False)])
        self.env.cr.execute("""
            SELECT COUNT(*) FROM (
                SELECT checksum FROM ir_attachment
                WHERE checksum IS NOT NULL
                GROUP BY checksum HAVING COUNT(*) > 1
            ) dup
        """)
        duplicate_groups = self.env.cr.fetchone()[0]
        self.env.cr.execute("""
            SELECT COALESCE(SUM(file_size), 0) FROM ir_attachment
        """)
        total_bytes = self.env.cr.fetchone()[0]

        # บันทึกเป็น log เพื่อใช้เทียบกับ KPI ในเฟสถัดไป
        self.env.cr.execute("""
            INSERT INTO ir_logging (create_uid, create_date, name, level, type, dbname, message)
            VALUES (%s, NOW(), %s, %s, %s, current_database(), %s)
        """, (
            self.env.uid, "od19_document_hub.baseline", "INFO", "server",
            f"total={total} with_checksum={with_checksum} "
            f"dup_groups={duplicate_groups} total_bytes={total_bytes}",
        ))
        self.assertTrue(total >= 1, "ต้องมีไฟล์แนบอย่างน้อย 1 รายการเพื่อยืนยันว่าอ่านได้")
```

- [ ] **Step 2: รันเทสต์**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_hub -Database odoo19_t_doc_hub -HttpPort 8081`
Expected: PASS — ไม่ล้ม และมี log `od19_document_hub.baseline`

- [ ] **Step 3: Commit**

```powershell
git add custom_addons/od19_document_hub/tests/test_document_hub_baseline.py
git commit -m "test(od19_document_hub): add baseline metrics measurement"
```

---

## Self-Review (ตรวจแผนกับสเปก §6–§10)

**1. Spec coverage:**

| สเปก | Task |
|---|---|
| §6.1 ฟิลด์ `od19_*` บน `ir.attachment` | Task 5 |
| §6.2 `od19.document.category` | Task 3 |
| §6.2 `od19.document.extract` | Task 6 |
| §6.2 `od19.document.retention.policy` (ย้ายมา hub) | Task 2 |
| §6.3 ดัชนี pg_trgm (extract + name) | Task 1 (hook) + Task 5 + Task 6 |
| §6.4 ใช้ `checksum` เดิม / mixin เก็บรายงาน | Task 5 (`od19_duplicate_count`) + Task 7 |
| §7.1–7.4 เมนู/คลังกลาง/เก็บรายงาน | Task 8 + Task 7 |
| §7.6 กลุ่มสิทธิ์ | Task 4 |
| §8 ลำดับการทำงาน (internal archive) | Task 7 |
| §10 แผนการทดสอบ | Task 1,2,3,5,6,7,10 |
| §11 P0 baseline | Task 10 |

**ช่องว่างที่รู้ตัว (อยู่นอกแผนนี้โดยเจตนา):**
- `od19.document.channel`, `od19.document.inbox`, OCR, จัดหมวดด้วย AI → แผน `od19_document_intake` (P2)
- cron ทำลายตามนโยบาย, legal hold workflow, audit read/download, dashboard ตัววัด → แผน `od19_document_governance` (P4/P5)
- Record rule ตาม `od19_confidentiality`/`od19_department_id` → แผน governance (เหตุผลใน §ขอบเขตของแผนนี้)
- การสกัดข้อความ PDF ด้วย `pdfminer.six` จริง (คิว + ตัวสกัด) → P2/P3 (ตาราง extract + index เตรียมไว้แล้วใน Task 6)

**2. Placeholder scan:** ไม่มี `TBD`/`TODO` — ทุก step มีโค้ด/คำสั่งจริง

**3. Type consistency:**
- ชื่อโมเดลตรงกันทุก Task: `od19.document.category`, `od19.document.retention.policy`, `od19.document.extract`, `od19.report.archive.mixin`
- เมธอด: `_compute_complete_name`, `_compute_od19_retention_until`, `_compute_od19_duplicate_count`, `_od19_archive_report`, `_od19_resolve_category` — ใช้ชื่อเดียวกันตลอด
- ฟิลด์ XML `ref` ตรงกับ `id` ที่สร้างจริง (`cat_purchase`, `cat_sales_tax_invoice`, ฯลฯ)

---

## Execution Handoff

**ลบไฟล์ template เปล่า (Step 5 ของ Task 1) ทันทีที่ Task ที่เกี่ยวข้องเขียนจริงเสร็จ** เพื่อไม่ให้เหลือ `<?xml version="1.0"?><odoo/>` ค้างในระบบ
