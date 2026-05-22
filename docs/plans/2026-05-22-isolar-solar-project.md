# iSolar Solar Project Module — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build `solar_project` (core) and `solar_ai` (AI-first layer) custom Odoo 19.0 Community modules that manage solar energy installation projects with 5-10 incoming documents per project, plus an AI pipeline for auto-classification, chat-orchestration, and consistency checking.

**Architecture:** Edition-agnostic core module (`solar_project`) depends only on Community modules; thin bridge modules (`solar_project_documents`, `solar_project_fsm`) auto-activate when Enterprise modules are present. AI layer (`solar_ai`) is provider-agnostic via OpenRouter and intercepts Odoo's built-in "Translate with AI" / "ChatGPT" buttons via a configurable OLG proxy endpoint.

**Tech Stack:** Python 3.10+, Odoo 19.0 ORM, `httpx` (async HTTP for LLM calls), OpenRouter API (provider-agnostic: Claude / GPT-4o / Mistral), `odoo.tests.TransactionCase`, ruff (lint), XML views in OWL-ready format.

---

## Prerequisite: Environment Verification

Before any coding task, verify the sandbox can actually run.

**Step 1: Check PostgreSQL**
```bash
psql -U odoo -c "SELECT 1;" 2>/dev/null && echo "PG OK" || echo "Need: createuser -s odoo"
```
Expected: `PG OK`. If not: `createuser -s odoo && createdb -O odoo isolar_test`

**Step 2: Check Python venv**
```bash
cd /Users/akoziar/dev/tx10/tx10-odoo
python3 --version  # expect 3.10.x or 3.11.x
python3 -c "import odoo" 2>/dev/null && echo "ODOO OK" || echo "Need: pip install -e ."
```
If `ODOO OK` fails: `pip install -r requirements.txt`

**Step 3: Verify Odoo starts**
```bash
./odoo-bin --stop-after-init --log-level=warn \
  -d isolar_test \
  -i base \
  2>&1 | tail -5
```
Expected last lines: `Modules loaded.` (no ERROR or CRITICAL).

**Step 4: Create `custom_addons/` directory**
```bash
mkdir -p /Users/akoziar/dev/tx10/tx10-odoo/custom_addons
echo "# Custom iSolar modules" > /Users/akoziar/dev/tx10/tx10-odoo/custom_addons/README.md
```

---

## Task 1: Install Core Business Stack

**Purpose:** Install the Community modules that our modules depend on so that `solar_project` can run.

**Step 1: Install modules**
```bash
cd /Users/akoziar/dev/tx10/tx10-odoo
./odoo-bin --stop-after-init --log-level=warn \
  -d isolar_test \
  -i project,crm,sale_management,sale_project,project_purchase,project_mrp,project_account,stock,purchase \
  2>&1 | grep -E "^(INFO|WARNING|ERROR|CRITICAL)" | tail -20
```
Expected: no ERROR or CRITICAL lines, ends with `Modules loaded.`

**Step 2: Verify in shell (optional quick check)**
```bash
./odoo-bin shell -d isolar_test --no-http 2>/dev/null <<'EOF'
mods = env['ir.module.module'].search([('state','=','installed'),('name','in',['project','sale_project','project_purchase'])])
print([m.name for m in mods])
EOF
```
Expected: `['project', 'sale_project', 'project_purchase']` (any order).

**Step 3: Commit the docs/plans directory**
```bash
git add docs/plans/2026-05-22-isolar-solar-project.md docs/plans/
git commit -m "[ADD] docs: add iSolar solar_project implementation plan"
```

---

## Task 2: Scaffold `solar_project` Module

**Files to create:**
- `custom_addons/solar_project/__manifest__.py`
- `custom_addons/solar_project/__init__.py`
- `custom_addons/solar_project/models/__init__.py`
- `custom_addons/solar_project/tests/__init__.py`

**Step 1: Create `__manifest__.py`**

File: `custom_addons/solar_project/__manifest__.py`
```python
{
    'name': 'Solar Project',
    'version': '19.0.1.0.0',
    'summary': 'Solar energy installation project management',
    'category': 'Project',
    'depends': [
        'project',
        'sale_project',
        'project_purchase',
        'project_account',
        'crm',
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/solar_document_type_data.xml',
        'views/project_project_views.xml',
        'views/solar_document_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
```

**Step 2: Create `__init__.py`**

File: `custom_addons/solar_project/__init__.py`
```python
from . import models
```

**Step 3: Create `models/__init__.py`**

File: `custom_addons/solar_project/models/__init__.py`
```python
from . import project_project
from . import solar_document_type
from . import solar_document
from . import solar_checklist
```

**Step 4: Create `tests/__init__.py`**

File: `custom_addons/solar_project/tests/__init__.py`
```python
from . import test_solar_project
```

**Step 5: Create placeholder model files (so module installs)**

File: `custom_addons/solar_project/models/project_project.py`
```python
from odoo import models, fields
```

File: `custom_addons/solar_project/models/solar_document_type.py`
```python
from odoo import models, fields
```

File: `custom_addons/solar_project/models/solar_document.py`
```python
from odoo import models, fields
```

File: `custom_addons/solar_project/models/solar_checklist.py`
```python
from odoo import models, fields
```

**Step 6: Create minimal security file (required by manifest)**

File: `custom_addons/solar_project/security/ir.model.access.csv`
```
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
```
_(empty header only — will be filled in Task 8)_

**Step 7: Create minimal data file (required by manifest)**

File: `custom_addons/solar_project/data/solar_document_type_data.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
</odoo>
```

**Step 8: Create minimal view files (required by manifest)**

File: `custom_addons/solar_project/views/project_project_views.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
</odoo>
```

File: `custom_addons/solar_project/views/solar_document_views.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
</odoo>
```

File: `custom_addons/solar_project/views/menus.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
</odoo>
```

**Step 9: Create minimal test file**

File: `custom_addons/solar_project/tests/test_solar_project.py`
```python
from odoo.tests import TransactionCase, tagged

@tagged('solar_project', 'post_install', '-at_install')
class TestSolarProjectBase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env['project.project'].create({'name': 'Test Solar Project'})

    def test_project_created(self):
        self.assertEqual(self.project.name, 'Test Solar Project')
```

**Step 10: Install module with test**
```bash
cd /Users/akoziar/dev/tx10/tx10-odoo
./odoo-bin --stop-after-init --log-level=warn \
  -d isolar_test \
  --addons-path=addons,odoo/addons,custom_addons \
  -i solar_project \
  --test-enable --test-tags solar_project \
  2>&1 | grep -E "(FAIL|ERROR|PASS|OK|solar_project)"
```
Expected: `test_project_created ... ok`

**Step 11: Lint**
```bash
ruff check custom_addons/solar_project/
ruff format --check custom_addons/solar_project/
```
Expected: no output (no issues).

**Step 12: Commit**
```bash
git add custom_addons/solar_project/
git commit -m "[ADD] solar_project: scaffold module with empty models and tests"
```

---

## Task 3: `solar.document.type` Model

**Purpose:** Simple lookup table for document types (электросчёт / план БТИ / замер / etc.).

**File to modify:** `custom_addons/solar_project/models/solar_document_type.py`

**Step 1: Write the failing test first**

Append to `custom_addons/solar_project/tests/test_solar_project.py`:
```python
@tagged('solar_project', 'post_install', '-at_install')
class TestSolarDocumentType(TransactionCase):

    def test_document_type_created(self):
        doc_type = self.env['solar.document.type'].create({
            'name': 'Electricity Bill',
            'code': 'bill_electricity',
        })
        self.assertEqual(doc_type.code, 'bill_electricity')

    def test_document_type_code_unique(self):
        from odoo.exceptions import ValidationError
        self.env['solar.document.type'].create({'name': 'T1', 'code': 'unique_code'})
        with self.assertRaises(ValidationError):
            self.env['solar.document.type'].create({'name': 'T2', 'code': 'unique_code'})
```

**Step 2: Run — expect FAIL (model doesn't exist yet)**
```bash
./odoo-bin --stop-after-init --log-level=warn \
  -d isolar_test \
  --addons-path=addons,odoo/addons,custom_addons \
  -u solar_project \
  --test-enable --test-tags solar_project \
  2>&1 | grep -E "(FAIL|ERROR|test_document)"
```
Expected: `ERROR` or `FAIL` with `KeyError: solar.document.type`.

**Step 3: Implement the model**

File: `custom_addons/solar_project/models/solar_document_type.py`
```python
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SolarDocumentType(models.Model):
    _name = 'solar.document.type'
    _description = 'Solar Document Type'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    description = fields.Text(translate=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Document type code must be unique.'),
    ]

    @api.constrains('code')
    def _check_code_unique(self):
        for rec in self:
            if self.search_count([('code', '=', rec.code), ('id', '!=', rec.id)]) > 0:
                raise ValidationError(f'Document type code "{rec.code}" already exists.')
```

> **Note:** We define both a SQL UNIQUE constraint (enforced at DB level) AND a Python `@api.constrains` check. The Python one is what tests can catch via `ValidationError`; the SQL one is the real guard in production.

**Step 4: Add to security file** (`custom_addons/solar_project/security/ir.model.access.csv`)
```
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_solar_document_type_user,solar.document.type user,model_solar_document_type,base.group_user,1,0,0,0
access_solar_document_type_manager,solar.document.type manager,model_solar_document_type,project.group_project_manager,1,1,1,1
```

**Step 5: Run tests — expect PASS**
```bash
./odoo-bin --stop-after-init --log-level=warn \
  -d isolar_test \
  --addons-path=addons,odoo/addons,custom_addons \
  -u solar_project \
  --test-enable --test-tags solar_project \
  2>&1 | grep -E "(FAIL|ERROR|PASS|ok|test_document_type)"
```
Expected: `test_document_type_created ... ok`, `test_document_type_code_unique ... ok`

**Step 6: Commit**
```bash
git add custom_addons/solar_project/
git commit -m "[ADD] solar_project: add solar.document.type model with uniqueness constraint"
```

---

## Task 4: Extend `project.project` with Solar Fields

**Purpose:** Add solar-specific metadata (kW capacity, battery, roof type, coordinates) to existing `project.project`.

**File to modify:** `custom_addons/solar_project/models/project_project.py`

**Step 1: Write failing test**

Append to `tests/test_solar_project.py`:
```python
@tagged('solar_project', 'post_install', '-at_install')
class TestProjectSolarExtension(TransactionCase):

    def test_solar_fields_exist(self):
        project = self.env['project.project'].create({
            'name': 'Solar Farm Ivanov',
            'solar_kw_capacity': 15.0,
            'solar_battery_kwh': 10.0,
            'solar_roof_type': 'metal',
            'solar_grid_type': 'on_grid',
        })
        self.assertEqual(project.solar_kw_capacity, 15.0)
        self.assertEqual(project.solar_roof_type, 'metal')

    def test_solar_stage_default(self):
        project = self.env['project.project'].create({'name': 'Test'})
        self.assertEqual(project.solar_stage, 'survey')

    def test_solar_coordinates(self):
        project = self.env['project.project'].create({
            'name': 'Geo Project',
            'solar_latitude': 50.4501,
            'solar_longitude': 30.5234,
        })
        self.assertAlmostEqual(project.solar_latitude, 50.4501, places=3)
```

**Step 2: Run — expect FAIL**
```bash
./odoo-bin --stop-after-init --log-level=warn \
  -d isolar_test \
  --addons-path=addons,odoo/addons,custom_addons \
  -u solar_project \
  --test-enable --test-tags solar_project \
  2>&1 | grep -E "(FAIL|ERROR|test_solar_fields|test_solar_stage)"
```

**Step 3: Implement the extension**

File: `custom_addons/solar_project/models/project_project.py`
```python
from odoo import models, fields


SOLAR_STAGE_SELECTION = [
    ('survey', 'Survey'),
    ('design', 'Design'),
    ('procurement', 'Procurement'),
    ('installation', 'Installation'),
    ('handover', 'Handover'),
    ('maintenance', 'Maintenance'),
]

ROOF_TYPE_SELECTION = [
    ('metal', 'Metal / Profiled Sheet'),
    ('tile', 'Tile'),
    ('flat', 'Flat / Soft Roof'),
    ('ground', 'Ground Mount'),
    ('other', 'Other'),
]

GRID_TYPE_SELECTION = [
    ('on_grid', 'On-Grid'),
    ('off_grid', 'Off-Grid'),
    ('hybrid', 'Hybrid'),
]


class ProjectProjectSolar(models.Model):
    _inherit = 'project.project'

    # Technical parameters
    solar_kw_capacity = fields.Float(
        string='System Capacity (kWp)',
        digits=(10, 2),
        help='Peak power capacity of the solar array in kilowatts-peak.',
    )
    solar_battery_kwh = fields.Float(
        string='Battery Storage (kWh)',
        digits=(10, 2),
        help='Total energy storage capacity of battery bank.',
    )
    solar_roof_type = fields.Selection(
        selection=ROOF_TYPE_SELECTION,
        string='Roof / Mount Type',
    )
    solar_grid_type = fields.Selection(
        selection=GRID_TYPE_SELECTION,
        string='Grid Connection',
    )

    # Location
    solar_latitude = fields.Float(string='Latitude', digits=(9, 6))
    solar_longitude = fields.Float(string='Longitude', digits=(9, 6))
    solar_address = fields.Char(string='Site Address')

    # Project lifecycle stage (separate from task kanban stages)
    solar_stage = fields.Selection(
        selection=SOLAR_STAGE_SELECTION,
        string='Project Stage',
        default='survey',
        required=True,
        tracking=True,
    )

    # Financial estimates
    solar_budget_usd = fields.Monetary(
        string='Estimated Budget (USD)',
        currency_field='currency_id',
    )
    solar_estimated_roi_years = fields.Float(
        string='Estimated ROI (years)',
        digits=(5, 1),
        compute='_compute_roi',
        store=True,
    )

    solar_document_ids = fields.One2many(
        comodel_name='solar.document',
        inverse_name='project_id',
        string='Project Documents',
    )
    solar_document_count = fields.Integer(
        compute='_compute_document_count',
        string='Documents',
    )

    def _compute_roi(self):
        # Placeholder: real computation based on kWp, irradiation, budget
        for rec in self:
            if rec.solar_kw_capacity and rec.solar_budget_usd:
                annual_yield_usd = rec.solar_kw_capacity * 1200 * 0.05  # rough: 1200 kWh/kWp/yr at 5c/kWh
                rec.solar_estimated_roi_years = rec.solar_budget_usd / annual_yield_usd if annual_yield_usd else 0
            else:
                rec.solar_estimated_roi_years = 0

    def _compute_document_count(self):
        for rec in self:
            rec.solar_document_count = len(rec.solar_document_ids)
```

**Step 4: Run tests — expect PASS**
```bash
./odoo-bin --stop-after-init --log-level=warn \
  -d isolar_test \
  --addons-path=addons,odoo/addons,custom_addons \
  -u solar_project \
  --test-enable --test-tags solar_project \
  2>&1 | grep -E "(FAIL|ERROR|ok|test_solar)"
```

**Step 5: Commit**
```bash
git add custom_addons/solar_project/
git commit -m "[ADD] solar_project: extend project.project with solar fields and stage"
```

---

## Task 5: `solar.document` Model

**Purpose:** First-class document entity with type, lifecycle state, validity period, and link to `ir.attachment`.

**File to modify:** `custom_addons/solar_project/models/solar_document.py`

**Step 1: Write failing tests**

Append to `tests/test_solar_project.py`:
```python
@tagged('solar_project', 'post_install', '-at_install')
class TestSolarDocument(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env['project.project'].create({'name': 'Doc Test Project'})
        cls.doc_type = cls.env['solar.document.type'].create({
            'name': 'Electricity Bill', 'code': 'bill_electricity'
        })

    def test_document_creation(self):
        doc = self.env['solar.document'].create({
            'name': 'Q1 2026 Bill',
            'project_id': self.project.id,
            'document_type_id': self.doc_type.id,
        })
        self.assertEqual(doc.state, 'draft')
        self.assertEqual(doc.project_id, self.project)

    def test_document_approve(self):
        doc = self.env['solar.document'].create({
            'name': 'Site Plan',
            'project_id': self.project.id,
            'document_type_id': self.doc_type.id,
        })
        doc.action_approve()
        self.assertEqual(doc.state, 'approved')

    def test_document_supersede(self):
        doc_v1 = self.env['solar.document'].create({
            'name': 'Measurement v1',
            'project_id': self.project.id,
            'document_type_id': self.doc_type.id,
        })
        doc_v2 = self.env['solar.document'].create({
            'name': 'Measurement v2',
            'project_id': self.project.id,
            'document_type_id': self.doc_type.id,
            'replaces_id': doc_v1.id,
        })
        doc_v2.action_approve()
        # Approving v2 should supersede v1 automatically
        self.assertEqual(doc_v1.state, 'superseded')
        self.assertEqual(doc_v2.state, 'approved')

    def test_project_document_count(self):
        for i in range(3):
            self.env['solar.document'].create({
                'name': f'Doc {i}',
                'project_id': self.project.id,
                'document_type_id': self.doc_type.id,
            })
        self.assertEqual(self.project.solar_document_count, 3)
```

**Step 2: Run — expect FAIL**
```bash
./odoo-bin --stop-after-init --log-level=warn \
  -d isolar_test \
  --addons-path=addons,odoo/addons,custom_addons \
  -u solar_project \
  --test-enable --test-tags solar_project \
  2>&1 | grep -E "(FAIL|ERROR|test_document_)"
```

**Step 3: Implement the model**

File: `custom_addons/solar_project/models/solar_document.py`
```python
from odoo import models, fields, api


class SolarDocument(models.Model):
    _name = 'solar.document'
    _description = 'Solar Project Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'document_type_id, name'

    name = fields.Char(required=True, tracking=True)
    project_id = fields.Many2one(
        comodel_name='project.project',
        string='Project',
        required=True,
        ondelete='cascade',
        index=True,
    )
    task_id = fields.Many2one(
        comodel_name='project.task',
        string='Task',
        domain="[('project_id', '=', project_id)]",
        ondelete='set null',
    )
    document_type_id = fields.Many2one(
        comodel_name='solar.document.type',
        string='Document Type',
        required=True,
        ondelete='restrict',
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('review', 'In Review'),
            ('approved', 'Approved'),
            ('expired', 'Expired'),
            ('superseded', 'Superseded'),
        ],
        default='draft',
        required=True,
        tracking=True,
        string='Status',
    )
    attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string='File',
        ondelete='set null',
    )
    valid_from = fields.Date(string='Valid From')
    valid_to = fields.Date(string='Valid Until')
    replaces_id = fields.Many2one(
        comodel_name='solar.document',
        string='Supersedes',
        help='Previous version of this document.',
        ondelete='set null',
    )
    notes = fields.Text(string='Notes')

    # AI fields — populated by solar_ai module
    ai_extracted_data = fields.Json(
        string='AI Extracted Data',
        help='Structured data extracted by AI from the document.',
    )
    ai_classified = fields.Boolean(
        string='AI Classified',
        default=False,
    )

    def action_submit_review(self):
        self.write({'state': 'review'})

    def action_approve(self):
        for rec in self:
            rec.state = 'approved'
            if rec.replaces_id and rec.replaces_id.state not in ('superseded', 'expired'):
                rec.replaces_id.state = 'superseded'

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_expire(self):
        self.write({'state': 'expired'})
```

**Step 4: Add to security CSV**

Append to `custom_addons/solar_project/security/ir.model.access.csv`:
```
access_solar_document_user,solar.document user,model_solar_document,base.group_user,1,1,1,0
access_solar_document_manager,solar.document manager,model_solar_document,project.group_project_manager,1,1,1,1
```

**Step 5: Run tests — expect PASS**
```bash
./odoo-bin --stop-after-init --log-level=warn \
  -d isolar_test \
  --addons-path=addons,odoo/addons,custom_addons \
  -u solar_project \
  --test-enable --test-tags solar_project \
  2>&1 | grep -E "(FAIL|ERROR|ok|test_document)"
```

**Step 6: Commit**
```bash
git add custom_addons/solar_project/
git commit -m "[ADD] solar_project: add solar.document model with lifecycle states"
```

---

## Task 6: `solar.checklist.item` Model

**Purpose:** Checklist items attached to project tasks (for survey / installation protocols).

**File to modify:** `custom_addons/solar_project/models/solar_checklist.py`

**Step 1: Write failing test**

Append to `tests/test_solar_project.py`:
```python
@tagged('solar_project', 'post_install', '-at_install')
class TestSolarChecklist(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env['project.project'].create({'name': 'Checklist Project'})
        cls.task = cls.env['project.task'].create({
            'name': 'Site Survey',
            'project_id': cls.project.id,
        })

    def test_checklist_item_created(self):
        item = self.env['solar.checklist.item'].create({
            'name': 'Measure roof pitch',
            'task_id': self.task.id,
            'sequence': 1,
        })
        self.assertFalse(item.is_done)
        self.assertEqual(item.task_id, self.task)

    def test_checklist_completion(self):
        item = self.env['solar.checklist.item'].create({
            'name': 'Take photo of meter',
            'task_id': self.task.id,
        })
        item.is_done = True
        self.assertTrue(item.is_done)
```

**Step 2: Implement the model**

File: `custom_addons/solar_project/models/solar_checklist.py`
```python
from odoo import models, fields


class SolarChecklistItem(models.Model):
    _name = 'solar.checklist.item'
    _description = 'Solar Survey / Installation Checklist Item'
    _order = 'sequence, id'

    name = fields.Char(required=True, string='Item')
    task_id = fields.Many2one(
        comodel_name='project.task',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(default=10)
    is_done = fields.Boolean(string='Done', default=False)
    notes = fields.Text(string='Notes')
    photo_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string='Photo Evidence',
        ondelete='set null',
    )
```

**Step 3: Add to security CSV**

Append to `ir.model.access.csv`:
```
access_solar_checklist_user,solar.checklist.item user,model_solar_checklist_item,base.group_user,1,1,1,0
access_solar_checklist_manager,solar.checklist.item manager,model_solar_checklist_item,project.group_project_manager,1,1,1,1
```

**Step 4: Run all tests**
```bash
./odoo-bin --stop-after-init --log-level=warn \
  -d isolar_test \
  --addons-path=addons,odoo/addons,custom_addons \
  -u solar_project \
  --test-enable --test-tags solar_project \
  2>&1 | grep -E "(FAIL|ERROR|ok|solar)"
```
Expected: all tests `ok`, no FAIL or ERROR.

**Step 5: Commit**
```bash
git add custom_addons/solar_project/
git commit -m "[ADD] solar_project: add solar.checklist.item model for survey/install checklists"
```

---

## Task 7: Views and Menus

**Purpose:** XML views — project form tab, document form/list, menus.

**Step 1: Fill `views/project_project_views.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
  <!-- Inherit project form view: add a Solar tab -->
  <record id="view_project_form_solar" model="ir.ui.view">
    <field name="name">project.project.view.form.solar</field>
    <field name="model">project.project</field>
    <field name="inherit_id" ref="project.edit_project"/>
    <field name="arch" type="xml">
      <notebook position="inside">
        <page string="Solar System" name="solar">
          <group string="Technical Parameters">
            <group>
              <field name="solar_stage"/>
              <field name="solar_kw_capacity"/>
              <field name="solar_battery_kwh"/>
              <field name="solar_grid_type"/>
              <field name="solar_roof_type"/>
            </group>
            <group>
              <field name="solar_address"/>
              <field name="solar_latitude"/>
              <field name="solar_longitude"/>
              <field name="solar_budget_usd" widget="monetary"/>
              <field name="solar_estimated_roi_years"/>
            </group>
          </group>
          <group string="Documents">
            <field name="solar_document_ids" nolabel="1">
              <list>
                <field name="name"/>
                <field name="document_type_id"/>
                <field name="state" widget="badge"
                       decoration-success="state == 'approved'"
                       decoration-warning="state == 'review'"
                       decoration-danger="state in ('expired','superseded')"/>
                <field name="valid_to"/>
                <field name="ai_classified" optional="hide"/>
              </list>
            </field>
          </group>
        </page>
      </notebook>
    </field>
  </record>

  <!-- Stat button on project kanban/form showing doc count -->
  <record id="view_project_form_solar_stat" model="ir.ui.view">
    <field name="name">project.project.view.form.solar.stat</field>
    <field name="model">project.project</field>
    <field name="inherit_id" ref="project.edit_project"/>
    <field name="arch" type="xml">
      <div name="button_box" position="inside">
        <button name="%(solar_project.action_solar_document_project)d"
                type="action"
                class="oe_stat_button"
                icon="fa-file-text-o"
                context="{'default_project_id': active_id}">
          <field name="solar_document_count" widget="statinfo" string="Docs"/>
        </button>
      </div>
    </field>
  </record>
</odoo>
```

**Step 2: Fill `views/solar_document_views.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
  <record id="view_solar_document_form" model="ir.ui.view">
    <field name="name">solar.document.view.form</field>
    <field name="model">solar.document</field>
    <field name="arch" type="xml">
      <form>
        <header>
          <button name="action_submit_review" string="Submit for Review"
                  type="object" class="btn-primary"
                  invisible="state != 'draft'"/>
          <button name="action_approve" string="Approve"
                  type="object" class="btn-primary"
                  invisible="state != 'review'"/>
          <button name="action_reset_draft" string="Reset to Draft"
                  type="object"
                  invisible="state not in ('review','approved')"/>
          <button name="action_expire" string="Mark Expired"
                  type="object"
                  invisible="state not in ('approved',)"/>
          <field name="state" widget="statusbar"
                 statusbar_visible="draft,review,approved"/>
        </header>
        <sheet>
          <group>
            <group>
              <field name="name"/>
              <field name="project_id"/>
              <field name="task_id"/>
              <field name="document_type_id"/>
            </group>
            <group>
              <field name="attachment_id" widget="many2one_binary"/>
              <field name="valid_from"/>
              <field name="valid_to"/>
              <field name="replaces_id"/>
            </group>
          </group>
          <group string="AI Metadata" groups="base.group_no_one">
            <field name="ai_classified"/>
            <field name="ai_extracted_data" widget="json"/>
          </group>
          <field name="notes" placeholder="Notes..."/>
        </sheet>
        <chatter/>
      </form>
    </field>
  </record>

  <record id="view_solar_document_list" model="ir.ui.view">
    <field name="name">solar.document.view.list</field>
    <field name="model">solar.document</field>
    <field name="arch" type="xml">
      <list>
        <field name="name"/>
        <field name="project_id"/>
        <field name="document_type_id"/>
        <field name="state" widget="badge"
               decoration-success="state == 'approved'"
               decoration-warning="state == 'review'"
               decoration-danger="state in ('expired','superseded')"/>
        <field name="valid_to"/>
        <field name="ai_classified"/>
      </list>
    </field>
  </record>

  <record id="action_solar_document" model="ir.actions.act_window">
    <field name="name">Solar Documents</field>
    <field name="res_model">solar.document</field>
    <field name="view_mode">list,form</field>
  </record>

  <record id="action_solar_document_project" model="ir.actions.act_window">
    <field name="name">Project Documents</field>
    <field name="res_model">solar.document</field>
    <field name="view_mode">list,form</field>
    <field name="context">{'default_project_id': active_id}</field>
    <field name="domain">[('project_id', '=', active_id)]</field>
  </record>
</odoo>
```

**Step 3: Fill `views/menus.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
  <menuitem id="menu_solar_project_root"
            name="Solar Projects"
            sequence="10"
            groups="project.group_project_user"/>

  <menuitem id="menu_solar_project_projects"
            name="Projects"
            parent="menu_solar_project_root"
            action="project.open_view_project_all_group_stage"
            sequence="10"/>

  <menuitem id="menu_solar_project_documents"
            name="Documents"
            parent="menu_solar_project_root"
            action="solar_project.action_solar_document"
            sequence="20"/>
</odoo>
```

**Step 4: Update module (views don't need tests, verify via install)**
```bash
./odoo-bin --stop-after-init --log-level=warn \
  -d isolar_test \
  --addons-path=addons,odoo/addons,custom_addons \
  -u solar_project \
  2>&1 | grep -E "(ERROR|CRITICAL|WARNING.*view)"
```
Expected: no ERROR or CRITICAL.

**Step 5: Start the server and verify UI manually**
```bash
./odoo-bin -d isolar_test \
  --addons-path=addons,odoo/addons,custom_addons \
  --dev=all 2>&1 | grep -E "(INFO.*http|ERROR)"
```
Open `http://localhost:8069`, login as admin. Verify:
- Menu "Solar Projects" appears in top bar.
- Opening a project shows "Solar System" tab with all fields.
- "Documents" sub-menu shows the empty list with correct columns.

**Step 6: Commit**
```bash
git add custom_addons/solar_project/
git commit -m "[ADD] solar_project: add XML views for project, documents, and menus"
```

---

## Task 8: Demo Data (Document Types)

**Purpose:** Ship 12 system document type records so the type dropdown is pre-filled after install.

**Step 1: Fill `data/solar_document_type_data.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo noupdate="1">
  <record id="solar_dtype_bill_electricity" model="solar.document.type">
    <field name="name">Electricity Bill</field>
    <field name="code">bill_electricity</field>
    <field name="sequence">10</field>
    <field name="description">Monthly or annual electricity consumption bill</field>
  </record>

  <record id="solar_dtype_roof_measurement" model="solar.document.type">
    <field name="name">Roof Measurement Report</field>
    <field name="code">roof_measurement</field>
    <field name="sequence">20</field>
  </record>

  <record id="solar_dtype_site_plan" model="solar.document.type">
    <field name="name">Site Plan / BTI Scheme</field>
    <field name="code">site_plan_bti</field>
    <field name="sequence">30</field>
  </record>

  <record id="solar_dtype_topographic" model="solar.document.type">
    <field name="name">Topographic Survey</field>
    <field name="code">topographic_survey</field>
    <field name="sequence">40</field>
  </record>

  <record id="solar_dtype_client_brief" model="solar.document.type">
    <field name="name">Client Brief / Technical Requirements</field>
    <field name="code">client_brief</field>
    <field name="sequence">50</field>
  </record>

  <record id="solar_dtype_equipment_spec" model="solar.document.type">
    <field name="name">Equipment Specification</field>
    <field name="code">equipment_spec</field>
    <field name="sequence">60</field>
  </record>

  <record id="solar_dtype_single_line_diagram" model="solar.document.type">
    <field name="name">Single-Line Electrical Diagram</field>
    <field name="code">single_line_diagram</field>
    <field name="sequence">70</field>
  </record>

  <record id="solar_dtype_permit" model="solar.document.type">
    <field name="name">Building / Connection Permit</field>
    <field name="code">permit</field>
    <field name="sequence">80</field>
  </record>

  <record id="solar_dtype_handover_act" model="solar.document.type">
    <field name="name">Handover Act</field>
    <field name="code">handover_act</field>
    <field name="sequence">90</field>
  </record>

  <record id="solar_dtype_commissioning_report" model="solar.document.type">
    <field name="name">Commissioning Test Report</field>
    <field name="code">commissioning_report</field>
    <field name="sequence">100</field>
  </record>

  <record id="solar_dtype_structural_calculation" model="solar.document.type">
    <field name="name">Structural Calculation</field>
    <field name="code">structural_calculation</field>
    <field name="sequence">110</field>
  </record>

  <record id="solar_dtype_grid_connection_agreement" model="solar.document.type">
    <field name="name">Grid Connection Agreement (РЕМ/ОСР)</field>
    <field name="code">grid_connection_agreement</field>
    <field name="sequence">120</field>
  </record>
</odoo>
```

> **Note:** `noupdate="1"` means this data is only loaded on INSTALL — not overwritten on `-u`. This is intentional: an admin can rename or add types after install without fearing they'll be reset.

**Step 2: Write a test for demo data presence**

Append to `tests/test_solar_project.py`:
```python
@tagged('solar_project', 'post_install', '-at_install')
class TestSolarDocumentTypeData(TransactionCase):

    def test_demo_types_loaded(self):
        bill_type = self.env.ref('solar_project.solar_dtype_bill_electricity', raise_if_not_found=False)
        self.assertIsNotNone(bill_type, 'Demo document type solar_dtype_bill_electricity not loaded')
        self.assertEqual(bill_type.code, 'bill_electricity')

    def test_at_least_10_types(self):
        types = self.env['solar.document.type'].search([])
        self.assertGreaterEqual(len(types), 10)
```

**Step 3: Update and run tests**
```bash
./odoo-bin --stop-after-init --log-level=warn \
  -d isolar_test \
  --addons-path=addons,odoo/addons,custom_addons \
  -u solar_project \
  --test-enable --test-tags solar_project \
  2>&1 | grep -E "(FAIL|ERROR|ok|demo_types)"
```
Expected: `test_demo_types_loaded ... ok`, `test_at_least_10_types ... ok`

**Step 4: Commit**
```bash
git add custom_addons/solar_project/
git commit -m "[ADD] solar_project: add 12 default document types as demo data"
```

---

## Task 9: Scaffold `solar_ai` Module

**Purpose:** AI-First layer with OpenRouter client and OLG proxy.

**Files to create:**
```
custom_addons/solar_ai/
├── __manifest__.py
├── __init__.py
├── models/__init__.py
├── models/solar_ai_service.py    (empty stub)
├── controllers/__init__.py
├── controllers/olg_proxy.py      (empty stub)
├── data/config_params.xml
└── tests/__init__.py
    tests/test_solar_ai.py
```

**Step 1: Create `__manifest__.py`**

File: `custom_addons/solar_ai/__manifest__.py`
```python
{
    'name': 'Solar AI',
    'version': '19.0.1.0.0',
    'summary': 'AI-first document processing and project orchestration for solar projects',
    'category': 'Project',
    'depends': [
        'solar_project',
        'base_setup',
    ],
    'external_dependencies': {'python': ['httpx']},
    'data': [
        'data/config_params.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
```

**Step 2: Add `httpx` to requirements**

Check if `httpx` is already in `requirements.txt`:
```bash
grep -i httpx /Users/akoziar/dev/tx10/tx10-odoo/requirements.txt
```
If not found, append it:
```bash
echo "httpx>=0.27.0" >> /Users/akoziar/dev/tx10/tx10-odoo/requirements.txt
pip install httpx
```

**Step 3: Create skeleton files**

File: `custom_addons/solar_ai/__init__.py`
```python
from . import models
from . import controllers
```

File: `custom_addons/solar_ai/models/__init__.py`
```python
from . import solar_ai_service
```

File: `custom_addons/solar_ai/controllers/__init__.py`
```python
from . import olg_proxy
```

File: `custom_addons/solar_ai/models/solar_ai_service.py`
```python
from odoo import models, fields
```

File: `custom_addons/solar_ai/controllers/olg_proxy.py`
```python
from odoo import http
```

File: `custom_addons/solar_ai/data/config_params.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo noupdate="1">
  <record id="solar_ai_openrouter_base_url" model="ir.config_parameter">
    <field name="key">solar_ai.openrouter_base_url</field>
    <field name="value">https://openrouter.ai/api/v1</field>
  </record>
  <record id="solar_ai_default_model" model="ir.config_parameter">
    <field name="key">solar_ai.default_model</field>
    <field name="value">anthropic/claude-sonnet-4-5</field>
  </record>
  <record id="solar_ai_vision_model" model="ir.config_parameter">
    <field name="key">solar_ai.vision_model</field>
    <field name="value">anthropic/claude-opus-4-7</field>
  </record>
  <record id="solar_ai_openrouter_api_key" model="ir.config_parameter">
    <field name="key">solar_ai.openrouter_api_key</field>
    <field name="value"></field>
  </record>
  <!-- OLG proxy: set this to activate "Translate with AI" / "Generate" buttons via our LLM -->
  <!-- After setting this, reload the UI. Leave empty to use Odoo SA's OLG service. -->
  <record id="html_editor_olg_endpoint" model="ir.config_parameter">
    <field name="key">html_editor.olg_api_endpoint</field>
    <field name="value"></field>
  </record>
</odoo>
```

File: `custom_addons/solar_ai/tests/__init__.py`
```python
from . import test_solar_ai
```

File: `custom_addons/solar_ai/tests/test_solar_ai.py`
```python
from odoo.tests import TransactionCase, tagged

@tagged('solar_ai', 'post_install', '-at_install')
class TestSolarAiBase(TransactionCase):

    def test_config_params_loaded(self):
        base_url = self.env['ir.config_parameter'].get_param('solar_ai.openrouter_base_url')
        self.assertEqual(base_url, 'https://openrouter.ai/api/v1')

    def test_default_model_configured(self):
        model_name = self.env['ir.config_parameter'].get_param('solar_ai.default_model')
        self.assertIsNotNone(model_name)
        self.assertIn('claude', model_name)
```

**Step 4: Install module**
```bash
./odoo-bin --stop-after-init --log-level=warn \
  -d isolar_test \
  --addons-path=addons,odoo/addons,custom_addons \
  -i solar_ai \
  --test-enable --test-tags solar_ai \
  2>&1 | grep -E "(FAIL|ERROR|ok|solar_ai)"
```
Expected: `test_config_params_loaded ... ok`, `test_default_model_configured ... ok`

**Step 5: Commit**
```bash
git add custom_addons/solar_ai/ requirements.txt
git commit -m "[ADD] solar_ai: scaffold module with OpenRouter config params"
```

---

## Task 10: `solar.ai.service` — OpenRouter HTTP Client

**Purpose:** Shared LLM client with retry, logging, and provider abstraction.

**File to modify:** `custom_addons/solar_ai/models/solar_ai_service.py`

**Step 1: Write tests with mock HTTP**

File: `custom_addons/solar_ai/tests/test_solar_ai.py` — append:
```python
import json
from unittest.mock import patch, MagicMock

@tagged('solar_ai', 'post_install', '-at_install')
class TestSolarAiService(TransactionCase):

    def _mock_openrouter_response(self, content):
        """Returns a mock httpx.Response mimicking OpenRouter chat completion."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'choices': [{'message': {'content': content, 'role': 'assistant'}}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15},
        }
        return mock_resp

    @patch('httpx.post')
    def test_chat_returns_content(self, mock_post):
        mock_post.return_value = self._mock_openrouter_response('Hello, solar world!')
        # Set a fake API key so the service doesn't skip the call
        self.env['ir.config_parameter'].set_param('solar_ai.openrouter_api_key', 'test-key-123')

        service = self.env['solar.ai.service']
        result = service.chat([{'role': 'user', 'content': 'Hello'}])
        self.assertEqual(result['content'], 'Hello, solar world!')

    @patch('httpx.post')
    def test_classify_document_returns_code(self, mock_post):
        mock_post.return_value = self._mock_openrouter_response(
            json.dumps({'document_type_code': 'bill_electricity', 'confidence': 0.95})
        )
        self.env['ir.config_parameter'].set_param('solar_ai.openrouter_api_key', 'test-key')

        service = self.env['solar.ai.service']
        result = service.classify_document_text('Monthly electricity consumption: 850 kWh. Total: 3210 UAH')
        self.assertEqual(result.get('document_type_code'), 'bill_electricity')
```

**Step 2: Implement the service**

File: `custom_addons/solar_ai/models/solar_ai_service.py`
```python
import json
import logging
from datetime import datetime

import httpx

from odoo import models, api

_logger = logging.getLogger(__name__)

CLASSIFICATION_SYSTEM_PROMPT = """You are a document classifier for solar energy installation projects.
Given document text, classify it into one of the following types and return JSON:
{"document_type_code": "<code>", "confidence": <0.0-1.0>, "extracted_summary": "<brief summary>"}

Document type codes:
- bill_electricity: electricity consumption bill
- roof_measurement: roof measurement or survey report
- site_plan_bti: site plan, BTI (Bureau of Technical Inventory) scheme
- topographic_survey: topographic survey map
- client_brief: client requirements or technical brief
- equipment_spec: equipment datasheet or specification
- single_line_diagram: electrical single-line or wiring diagram
- permit: building or grid connection permit
- handover_act: handover or acceptance act
- commissioning_report: commissioning or testing report
- structural_calculation: structural engineering calculation
- grid_connection_agreement: grid connection agreement
- unknown: none of the above

Respond with ONLY the JSON object, no markdown fences."""


class SolarAiService(models.AbstractModel):
    _name = 'solar.ai.service'
    _description = 'Solar AI LLM Service (OpenRouter)'

    def _get_config(self, key, default=None):
        return self.env['ir.config_parameter'].sudo().get_param(f'solar_ai.{key}', default)

    def _build_headers(self):
        api_key = self._get_config('openrouter_api_key')
        if not api_key:
            return None
        return {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://isolar.ua',
            'X-Title': 'iSolar Odoo',
        }

    def chat(self, messages, model=None, tools=None, timeout=30):
        """Send a chat completion request to OpenRouter. Returns {'content': str, 'usage': dict}."""
        headers = self._build_headers()
        if not headers:
            _logger.warning('solar_ai: no OpenRouter API key configured — skipping LLM call')
            return {'content': '', 'usage': {}}

        base_url = self._get_config('openrouter_base_url', 'https://openrouter.ai/api/v1')
        model = model or self._get_config('default_model', 'anthropic/claude-sonnet-4-5')

        payload = {'model': model, 'messages': messages}
        if tools:
            payload['tools'] = tools

        started_at = datetime.now()
        try:
            resp = httpx.post(
                f'{base_url}/chat/completions',
                headers=headers,
                json=payload,
                timeout=timeout,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _logger.error('solar_ai: OpenRouter HTTP error %s: %s', exc.response.status_code, exc.response.text[:300])
            return {'content': '', 'usage': {}, 'error': str(exc)}
        except httpx.RequestError as exc:
            _logger.error('solar_ai: OpenRouter request error: %s', exc)
            return {'content': '', 'usage': {}, 'error': str(exc)}

        data = resp.json()
        elapsed_ms = int((datetime.now() - started_at).total_seconds() * 1000)
        _logger.info('solar_ai: LLM call complete in %dms (model=%s)', elapsed_ms, model)

        return {
            'content': data['choices'][0]['message']['content'],
            'usage': data.get('usage', {}),
            'elapsed_ms': elapsed_ms,
        }

    def classify_document_text(self, text, max_chars=4000):
        """Classify document text, return dict with 'document_type_code' and 'confidence'."""
        truncated = text[:max_chars] if len(text) > max_chars else text
        messages = [
            {'role': 'system', 'content': CLASSIFICATION_SYSTEM_PROMPT},
            {'role': 'user', 'content': truncated},
        ]
        result = self.chat(messages)
        try:
            return json.loads(result['content'])
        except (json.JSONDecodeError, KeyError):
            return {'document_type_code': 'unknown', 'confidence': 0.0}
```

**Step 3: Run tests**
```bash
./odoo-bin --stop-after-init --log-level=warn \
  -d isolar_test \
  --addons-path=addons,odoo/addons,custom_addons \
  -u solar_ai \
  --test-enable --test-tags solar_ai \
  2>&1 | grep -E "(FAIL|ERROR|ok|test_chat|test_classify)"
```
Expected: `test_chat_returns_content ... ok`, `test_classify_document_returns_code ... ok`

**Step 4: Commit**
```bash
git add custom_addons/solar_ai/
git commit -m "[ADD] solar_ai: implement OpenRouter HTTP client with classify_document_text"
```

---

## Task 11: OLG Proxy Controller

**Purpose:** Endpoint that mimics Odoo's `https://olg.api.odoo.com/api/olg/1/chat` contract, routing calls to OpenRouter instead. After activation, the "Translate with AI" and "Generate with ChatGPT" buttons in the HTML editor use our LLM.

**File to modify:** `custom_addons/solar_ai/controllers/olg_proxy.py`

**Step 1: Write the controller**

File: `custom_addons/solar_ai/controllers/olg_proxy.py`
```python
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class SolarAiOlgProxy(http.Controller):
    """Emulates Odoo's OLG API endpoint so the html_editor 'Translate with AI'
    and 'Generate with ChatGPT' buttons route to OpenRouter instead of Odoo SA."""

    @http.route('/solar_ai/olg/api/olg/1/chat', type='json', auth='user', methods=['POST'], csrf=False)
    def olg_chat(self, **kwargs):
        """OLG chat endpoint. Odoo sends: {prompt, conversation_history, database_id}.
        Returns: {status: 'success', content: str} or {status: 'error', error: str}."""
        body = request.get_json_data()
        prompt = body.get('prompt', '')
        history = body.get('conversation_history', [])

        messages = []
        for turn in history:
            role = 'assistant' if turn.get('role') == 'assistant' else 'user'
            messages.append({'role': role, 'content': turn.get('content', '')})
        messages.append({'role': 'user', 'content': prompt})

        service = request.env['solar.ai.service']
        result = service.chat(messages)

        if result.get('error'):
            return {'status': 'error', 'error': result['error']}
        return {'status': 'success', 'content': result['content']}

    @http.route('/solar_ai/olg/api/olg/1/generate_placeholder', type='json', auth='user', methods=['POST'], csrf=False)
    def olg_generate_placeholder(self, **kwargs):
        """Handles website configurator's placeholder text generation."""
        body = request.get_json_data()
        prompt = body.get('prompt', 'Generate a professional website text for a solar energy company.')

        service = request.env['solar.ai.service']
        result = service.chat([{'role': 'user', 'content': prompt}])

        if result.get('error'):
            return {'status': 'error', 'error': result['error']}
        return {'status': 'success', 'content': result['content']}
```

**Step 2: Write a test for the controller route**

Append to `tests/test_solar_ai.py`:
```python
from odoo.tests import HttpCase, tagged
from unittest.mock import patch

@tagged('solar_ai', 'post_install', '-at_install')
class TestOlgProxy(HttpCase):

    @patch('custom_addons.solar_ai.models.solar_ai_service.httpx.post')
    def test_olg_chat_route(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'choices': [{'message': {'content': 'AI response text', 'role': 'assistant'}}],
            'usage': {},
        }
        self.env['ir.config_parameter'].sudo().set_param('solar_ai.openrouter_api_key', 'test-key')

        resp = self.url_open(
            '/solar_ai/olg/api/olg/1/chat',
            data=json.dumps({'jsonrpc': '2.0', 'method': 'call', 'id': 1,
                             'params': {'prompt': 'Translate this', 'conversation_history': []}}),
            headers={'Content-Type': 'application/json'},
        )
        self.assertEqual(resp.status_code, 200)
        result = resp.json()
        self.assertEqual(result.get('result', {}).get('status'), 'success')
```

**Step 3: Run controller test**
```bash
./odoo-bin --stop-after-init --log-level=warn \
  -d isolar_test \
  --addons-path=addons,odoo/addons,custom_addons \
  -u solar_ai \
  --test-enable --test-tags solar_ai \
  2>&1 | grep -E "(FAIL|ERROR|ok|test_olg)"
```

**Step 4: Activate OLG proxy**

In Odoo Settings → Technical → Parameters → System Parameters, find `html_editor.olg_api_endpoint` and set value to `http://localhost:8069/solar_ai/olg`. Or via shell:
```bash
./odoo-bin shell -d isolar_test --no-http 2>/dev/null <<'EOF'
env['ir.config_parameter'].set_param('html_editor.olg_api_endpoint', 'http://localhost:8069/solar_ai/olg')
env.cr.commit()
print('OLG proxy activated')
EOF
```
Reload `http://localhost:8069`, open any project description field, click "Translate with AI" → should call your LLM.

**Step 5: Commit**
```bash
git add custom_addons/solar_ai/
git commit -m "[ADD] solar_ai: OLG proxy controller hijacks Translate/Generate AI buttons"
```

---

## Task 12: Auto-Classify Documents on Upload

**Purpose:** When a file is attached to a `solar.document` record, trigger AI classification automatically.

**Step 1: Write failing test**

Append to `tests/test_solar_ai.py`:
```python
@tagged('solar_ai', 'post_install', '-at_install')
class TestAutoClassify(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('solar_ai.openrouter_api_key', 'test-key')
        cls.project = cls.env['project.project'].create({'name': 'Classify Test Project'})
        cls.doc_type_bill = cls.env.ref('solar_project.solar_dtype_bill_electricity')

    @patch('httpx.post')
    def test_auto_classify_on_attachment(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'choices': [{'message': {'content': '{"document_type_code": "bill_electricity", "confidence": 0.92}',
                                     'role': 'assistant'}}],
            'usage': {},
        }
        doc = self.env['solar.document'].create({
            'name': 'Test bill',
            'project_id': self.project.id,
            'document_type_id': self.env['solar.document.type'].search([], limit=1).id,
        })
        # Simulate attachment with text content
        attachment = self.env['ir.attachment'].create({
            'name': 'electricity_bill_jan.pdf',
            'res_model': 'solar.document',
            'res_id': doc.id,
            'mimetype': 'application/pdf',
            'datas': b'Monthly electricity: 850 kWh'.hex(),  # fake content
        })
        doc._run_ai_classify()
        self.assertTrue(doc.ai_classified)
        self.assertEqual(doc.document_type_id.code, 'bill_electricity')
```

**Step 2: Add `_run_ai_classify` to `solar.document`**

In `custom_addons/solar_project/models/solar_document.py`, import at top:
```python
import logging
_logger = logging.getLogger(__name__)
```

Append to the `SolarDocument` class:
```python
    def _run_ai_classify(self):
        """Classify this document using solar.ai.service if available."""
        if 'solar.ai.service' not in self.env:
            return  # solar_ai module not installed

        for rec in self:
            attachment = rec.attachment_id
            if not attachment:
                continue
            # Extract text from attachment name + any raw text content
            text = attachment.name or ''
            if attachment.mimetype == 'text/plain' and attachment.raw:
                text += '\n' + attachment.raw.decode('utf-8', errors='ignore')[:4000]

            service = self.env['solar.ai.service']
            classification = service.classify_document_text(text)
            code = classification.get('document_type_code', 'unknown')
            if code and code != 'unknown':
                doc_type = self.env['solar.document.type'].search([('code', '=', code)], limit=1)
                if doc_type:
                    rec.document_type_id = doc_type
            rec.ai_classified = True
            rec.ai_extracted_data = classification
```

**Step 3: Run tests**
```bash
./odoo-bin --stop-after-init --log-level=warn \
  -d isolar_test \
  --addons-path=addons,odoo/addons,custom_addons \
  -u solar_project,solar_ai \
  --test-enable --test-tags solar_ai,solar_project \
  2>&1 | grep -E "(FAIL|ERROR|ok|test_auto_classify)"
```
Expected: `test_auto_classify_on_attachment ... ok`

**Step 4: Commit**
```bash
git add custom_addons/solar_project/ custom_addons/solar_ai/
git commit -m "[ADD] solar_ai: auto-classify solar.document on attachment upload via OpenRouter"
```

---

## Task 13: Consistency Check Action

**Purpose:** Button on project that sends all attached documents to LLM and creates `mail.activity` for each inconsistency found.

**Step 1: Write failing test**

Append to `tests/test_solar_ai.py`:
```python
@tagged('solar_ai', 'post_install', '-at_install')
class TestConsistencyCheck(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('solar_ai.openrouter_api_key', 'test-key')
        cls.project = cls.env['project.project'].create({'name': 'Consistency Test'})
        doc_type = cls.env.ref('solar_project.solar_dtype_roof_measurement')
        for i in range(2):
            cls.env['solar.document'].create({
                'name': f'Doc {i}',
                'project_id': cls.project.id,
                'document_type_id': doc_type.id,
            })

    @patch('httpx.post')
    def test_consistency_check_creates_activity(self, mock_post):
        inconsistency_response = json.dumps({
            'inconsistencies': [
                {'severity': 'warning', 'description': 'Roof area in measurement doc (120m²) differs from site plan (95m²)'},
            ]
        })
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'choices': [{'message': {'content': inconsistency_response, 'role': 'assistant'}}],
            'usage': {},
        }

        initial_activity_count = len(self.project.activity_ids)
        self.project.action_run_consistency_check()
        self.assertGreater(len(self.project.activity_ids), initial_activity_count)
```

**Step 2: Add action to `project.project` extension**

Append to `custom_addons/solar_project/models/project_project.py`:
```python
    CONSISTENCY_CHECK_PROMPT = """You are reviewing solar installation project documents for consistency.
Given a list of document summaries (name, type, any extracted data), identify any contradictions or missing critical documents.

Return JSON: {"inconsistencies": [{"severity": "error|warning|info", "description": "..."}]}
Respond with ONLY the JSON, no markdown."""

    def action_run_consistency_check(self):
        """Run AI consistency check on all project documents. Creates mail.activity for each issue found."""
        if 'solar.ai.service' not in self.env:
            return

        for project in self:
            docs = project.solar_document_ids
            if not docs:
                return

            doc_summaries = '\n'.join(
                f'- [{doc.document_type_id.name or "Unknown type"}] {doc.name} '
                f'(state: {doc.state}, extracted: {doc.ai_extracted_data or "N/A"})'
                for doc in docs
            )

            messages = [
                {'role': 'system', 'content': self.CONSISTENCY_CHECK_PROMPT},
                {'role': 'user', 'content': f'Project: {project.name}\n\nDocuments:\n{doc_summaries}'},
            ]

            service = self.env['solar.ai.service']
            result = service.chat(messages)

            import json
            try:
                data = json.loads(result['content'])
            except (json.JSONDecodeError, TypeError):
                return

            activity_type = self.env.ref('mail.mail_activity_data_todo')
            for issue in data.get('inconsistencies', []):
                severity = issue.get('severity', 'info')
                note = f"[{severity.upper()}] {issue.get('description', '')}"
                project.activity_schedule(
                    activity_type_id=activity_type.id,
                    note=note,
                    summary='Document Consistency Issue',
                )
```

**Step 3: Add button to project form view**

In `custom_addons/solar_project/views/project_project_views.xml`, add inside the `<form>` `<header>` inherit:
```xml
<!-- Add to the project_project_views.xml: a second inherit to add the action button -->
<record id="view_project_form_solar_check" model="ir.ui.view">
  <field name="name">project.project.view.form.solar.check</field>
  <field name="model">project.project</field>
  <field name="inherit_id" ref="project.edit_project"/>
  <field name="arch" type="xml">
    <xpath expr="//form//header" position="inside">
      <button name="action_run_consistency_check"
              string="AI: Check Document Consistency"
              type="object"
              class="btn-secondary"
              title="Run AI consistency check across all project documents"/>
    </xpath>
  </field>
</record>
```

**Step 4: Run all tests**
```bash
./odoo-bin --stop-after-init --log-level=warn \
  -d isolar_test \
  --addons-path=addons,odoo/addons,custom_addons \
  -u solar_project,solar_ai \
  --test-enable --test-tags solar_project,solar_ai \
  2>&1 | grep -E "(FAIL|ERROR|ok|test_consistency)"
```
Expected: all `ok`, no FAIL or ERROR.

**Step 5: Final lint check**
```bash
ruff check custom_addons/solar_project/ custom_addons/solar_ai/
ruff format --check custom_addons/solar_project/ custom_addons/solar_ai/
```

**Step 6: Final commit**
```bash
git add custom_addons/solar_project/ custom_addons/solar_ai/
git commit -m "[ADD] solar_ai: consistency check action creates mail.activity per issue"
```

---

## Task 14: Manual Walkthrough (Sandbox Verification)

**Purpose:** Validate the full iSolar scenario manually in the browser before the PR.

**Start the server:**
```bash
./odoo-bin -d isolar_test \
  --addons-path=addons,odoo/addons,custom_addons \
  --dev=all
```

**Scenario checklist:**

| # | Action | Expected |
|---|--------|----------|
| 1 | Settings → General → Companies — verify base config | OK |
| 2 | Open Solar Projects menu → Projects | Empty kanban |
| 3 | Create project "СЭС Іванов 15 кВт", Solar tab: set capacity=15, battery=10, roof=metal, grid=on_grid | Saved |
| 4 | Set stage "Survey" | Stage shown in form |
| 5 | Project → Documents tab: click Add, choose type "Electricity Bill", upload any PDF | Document created, state=draft |
| 6 | On document: click "Submit for Review" → "Approve" | State → approved |
| 7 | Click "AI: Check Document Consistency" (needs API key set) | Activity created (or "no api key" warning in log) |
| 8 | Settings → Technical → Parameters → find `solar_ai.openrouter_api_key`, set real key | Ready for live test |
| 9 | Create second project, test "Docs" stat button counter | Shows correct count |

**Step: If everything passes — create PR**
```bash
git push -u origin feat/isolar-solar-project
gh pr create \
  --title "[ADD] solar_project, solar_ai: iSolar vertical modules with AI-first document flow" \
  --body "$(cat <<'EOF'
## Summary
- Adds `solar_project` module: extends project.project with solar fields, solar.document model with lifecycle, solar.document.type lookup, solar.checklist.item for field checklists
- Adds `solar_ai` module: OpenRouter LLM client, OLG proxy (hijacks Odoo AI buttons), auto-classify on upload, consistency check action
- All modules tested with TransactionCase TDD

## Test plan
- [ ] Install on clean isolar_test DB without errors
- [ ] Run `--test-tags solar_project,solar_ai` — all green
- [ ] Manual walkthrough: create project, add 2 docs, approve one, run consistency check
- [ ] Verify OLG proxy: set `html_editor.olg_api_endpoint` and confirm "Translate with AI" uses OpenRouter

🤖 Generated with Claude Code
EOF
)" \
  --base develop
```

---

## Quick Reference

**Run specific module tests:**
```bash
./odoo-bin --stop-after-init -d isolar_test \
  --addons-path=addons,odoo/addons,custom_addons \
  -u solar_project \
  --test-enable --test-tags solar_project --log-level=warn \
  2>&1 | tail -30
```

**Lint all custom modules:**
```bash
ruff check custom_addons/ && ruff format --check custom_addons/
```

**Odoo shell (quick ORM experiments):**
```bash
./odoo-bin shell -d isolar_test --no-http \
  --addons-path=addons,odoo/addons,custom_addons
```

**Key Odoo 19.0 gotchas:**
- Use `odoo.fields.Domain` — `odoo.osv` is deprecated in 19.0
- `noupdate="1"` in data XML = loaded once at install, not overwritten on `-u`
- `@tagged('solar_project', 'post_install', '-at_install')` = runs after install, not during
- `AbstractModel` has no table — use for service/utility classes like `solar.ai.service`
- `_inherit` to extend existing model; `_name` to create new model
- `tracking=True` on fields = automatic chatter messages on change (requires `mail.thread`)
