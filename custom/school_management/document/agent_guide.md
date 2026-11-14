# Agent Guide — Odoo 19.0

This document helps AI agents understand and navigate this codebase.

---

## Project Overview

**Odoo 19.0** is a full-licensed ERP/CRM suite — Python backend, OWL (Odoo Web Library) frontend, PostgreSQL-only database. Version `19.0.0 FINAL`. License: LGPL-3.

Entry point: `odoo-bin` → `odoo.cli.main()`.

---

## Directory Structure

```
C:\Odoo\odoo\
├── odoo/                  # Core library (ORM, HTTP, CLI, services, tools)
│   ├── orm/               # ORM: models, fields, domains, environments, registry
│   ├── cli/               # CLI commands (server, shell, scaffold, db, module, etc.)
│   ├── http.py            # HTTP/WSGI layer, Controller base, @route decorator
│   ├── sql_db.py          # PostgreSQL connector (psycopg2 wrapper)
│   ├── tests/             # Core test framework (TransactionCase, HttpCase, Form)
│   ├── tools/             # Utilities (config, translate, sql, image, safe_eval, etc.)
│   ├── modules/           # Module loading, registry, migration, manifest parsing
│   ├── service/           # RPC service layer, server implementation
│   ├── release.py         # Version: (19, 0, 0, FINAL, 0)
│   └── exceptions.py      # UserError, AccessError, ValidationError, etc.
├── addons/                # ~632 standard addons (sale, account, stock, crm, web, etc.)
│   └── <module>/
│       ├── __manifest__.py
│       ├── __init__.py
│       ├── models/        # ORM model definitions
│       ├── views/         # XML view definitions
│       ├── security/      # ir.model.access.csv, record rules
│       ├── data/          # Data files loaded on install
│       ├── demo/          # Demo data
│       ├── controllers/   # HTTP routes
│       ├── wizard/        # Transient models
│       ├── static/        # Frontend assets (JS, SCSS, XML templates)
│       ├── tests/         # Python tests
│       └── i18n/          # Translations (.po/.pot)
├── odoo/addons/           # Core addons (base + ~24 test modules)
├── custom/                # Custom addons (user-defined, currently school_management/)
├── setup/                 # Packaging (deb, rpm, win32, wsgi example)
├── debian/                # Debian/Ubuntu packaging
├── doc/                   # Documentation
├── venv/                  # Python 3.12.8 virtual environment
├── odoo-bin               # Main entry point
├── odoo.conf              # Runtime configuration
├── requirements.txt       # Pinned Python dependencies
├── ruff.toml              # Ruff linter config
├── setup.py               # Package setup
├── setup.cfg              # Flake8 config
├── start_odoo.ps1         # Windows launcher (adds wkhtmltopdf to PATH, starts server)
├── CONTRIBUTING.md        # Contribution guidelines
└── LICENSE                # LGPL-3
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10–3.14 (venv: 3.12.8) |
| Database | PostgreSQL ≥ 13 (psycopg2) |
| Web/WSGI | Werkzeug + gevent/greenlet |
| Templating | Jinja2 |
| ORM | Custom (`../../../odoo/orm`) |
| Frontend | OWL (Odoo Web Library), SCSS, custom asset bundling |
| XML/HTML | lxml |
| Image | Pillow |
| PDF | reportlab, PyPDF2 |
| i18n | Babel, polib, num2words |
| Excel | openpyxl, xlrd, xlwt, xlsxwriter |
| Testing | unittest + freezegun + custom Odoo test framework |
| Linting | Ruff (primary), Flake8 (secondary) |

---

## ORM Architecture (`../../../odoo/orm`)

This is the heart of Odoo. All business objects extend `BaseModel`.

### Key files

| File | Lines | Purpose |
|------|-------|---------|
| `models.py` | ~7130 | BaseModel: CRUD, search, compute, constraints, caching, recordsets |
| `fields.py` | ~1938 | Field base class with storage, computation, defaults, constraints |
| `fields_relational.py` | ~1779 | Many2one, One2many, Many2many |
| `domains.py` | ~2043 | Domain expression AST (AND, OR, NOT, conditions) |
| `environments.py` | ~964 | Environment (cr, uid, context, su, transaction/cache) |
| `registry.py` | ~1296 | Per-database model registry, cache layers, schema ops |
| `commands.py` | — | Command enum: CREATE(0), UPDATE(1), DELETE(2), UNLINK(3), LINK(4), CLEAR(5), SET(6) |
| `decorators.py` | — | @api.depends, @api.constrains, @api.onchange, @api.ondelete, @api.model |

### Core concepts

- **Models** — define `_name` (table), `_description`, `_inherit` (inheritance), CRUD methods
- **Fields** — Char, Text, Html, Integer, Float, Monetary, Boolean, Date, Datetime, Selection, Binary, Image, Json, Many2one, One2many, Many2many
- **Domains** — first-order logical expressions for filtering records
- **Environments** — each request runs in an Environment with cursor, user ID, context, and superuser flag
- **Registry** — singleton per database holding all model classes and cache layers
- **Recordsets** — set-like objects returned by search/browse, support record manipulation

### Field options (common)

`compute`, `store`, `default`, `required`, `readonly`, `copy`, `groups`, `company_dependent`, `tracking` (chatter), `index`, `unique`, `ondelete`

---

## Module Structure

Every addon follows this pattern:

```
module_name/
├── __manifest__.py      # Metadata: name, version, depends, data, demo, assets, hooks
├── __init__.py          # Python package init (imports models/, controllers/, etc.)
├── models/              # ORM model files (imported from __init__.py)
├── views/               # XML view definitions (form, tree, kanban, search, etc.)
├── security/            # ir.model.access.csv + record rule XML
├── data/                # Default data loaded on install (XML, CSV)
├── demo/                # Demo data (loaded with --without-demo=False)
├── controllers/         # HTTP routes (Python, inherits web.controllers)
├── wizard/              # Transient models (wizard forms)
├── static/              # Frontend assets
│   └── src/             # JS, SCSS, XML templates, images
├── tests/               # Python tests (test_*.py)
│   └── __init__.py
├── i18n/                # Translations (.po, .pot)
└── README.md
```

### Manifest (`__manifest__.py`) key fields

```python
{
    'name': 'Module Name',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Short description',
    'description': 'Long description',
    'depends': ['sale', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_views.xml',
        'data/sequence_data.xml',
    ],
    'demo': ['demo/sale_demo.xml'],
    'assets': {
        'web.assets_backend': [
            'module_name/static/src/**/*.js',
            'module_name/static/src/**/*.scss',
        ],
    },
    'installable': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
    'external_dependencies': {'python': ['openpyxl']},
    'license': 'LGPL-3',
}
```

---

## Configuration

### `odoo.conf` (runtime)

```ini
db_name = odoo
db_host = localhost
db_port = 5432
db_user = odoo
addons_path = addons,custom,odoo/addons
http_port = 8070
gevent_port = 8072
```

### `../../../requirements.txt`

106 lines of pinned dependencies. Supports Python 3.10–3.14 with version-conditional pins.

### `../../../ruff.toml`

- Target: Python 3.10
- Preview mode enabled
- Rule sets: E, F, W, I (isort), UP, SIM, TRY, PLC/PLE/PLW, and many more
- `F401` (unused import) suppressed in all `__init__.py` files
- isort: `odoo` = first-party, `odoo.addons` = local-folder

---

## Development Commands

### Start server

```powershell
python odoo-bin -c odoo.conf
```

### Initialize database

```powershell
python odoo-bin -c odoo.conf -d <dbname> -i base --stop-after-init
```

### Install/upgrade a module

```powershell
python odoo-bin -c odoo.conf -d <dbname> -i <module> --stop-after-init   # install
python odoo-bin -c odoo.conf -d <dbname> -u <module> --stop-after-init   # upgrade
```

### Interactive shell

```powershell
python odoo-bin shell -c odoo.conf -d <dbname> --no-http
```

### Scaffold a new module

```powershell
python odoo-bin scaffold <module_name> custom/
```

### Run tests

```powershell
# All tests for a module
python odoo-bin -c odoo.conf -d <dbname> --test-enable -i <module> --stop-after-init

# Specific test tags
python odoo-bin -c odoo.conf -d <dbname> --test-enable --test-tags=<tag> -i <module> --stop-after-init
```

### Linting

```powershell
ruff check .          # lint
ruff format .         # format
```

### List databases

```powershell
python odoo-bin db -c odoo.conf --list
```

---

## Test Framework

Tests live inside each addon in `tests/` subdirectories.

### Base classes (`../../../odoo/tests/common.py`)

- **`TransactionCase`** — each test gets a fresh transaction, rolled back after
- **`HttpCase`** — tests HTTP endpoints (starts a test server)
- **`BaseCase`** — common utilities
- **`tagged('tag1', 'tag2')`** — decorator for selective test execution

### Form test helper (`../../../odoo/tests/form.py`)

Server-side Form view simulator — writes field values, triggers onchange, validates constraints without a browser.

### Test conventions

- Files: `tests/test_<topic>.py`
- Classes: `class TestSomething(TransactionCase):`
- Methods: `def test_<behavior>(self):`
- Tags: `@tagged('standard', 'fast')` or `@tagged('-at_install', 'post_install')`

### Dedicated test addons

- `../../../odoo/addons`: `test_orm/`, `test_rpc/`, `test_http/`, `test_access_rights/`, etc.
- `../../../addons`: `test_crm_full/`, `test_discuss_full/`, `test_mail_full/`, `test_website/`, etc.

---

## Key Exception Types (`../../../odoo/exceptions.py`)

| Exception | Use |
|-----------|-----|
| `UserError` | User-facing error (displayed in UI alert) |
| `ValidationError` | Constraint violation on record values |
| `AccessError` | Insufficient permissions |
| `AccessDenied` | Authentication failure |
| `MissingError` | Record not found |
| `LockError` | Database lock timeout |
| `ConcurrencyError` | Record modified by another user |
| `CacheMiss` | Field value not in cache |

---

## HTTP Layer (`../../../odoo/http.py`)

- **`Controller`** — base class for HTTP controllers
- **`@route('/path', type='http', auth='user', methods=['POST'])`** — route decorator
- **`request`** — thread-local object with `env`, `cr`, `uid`, `context`, `session`, `params`
- Auth types: `none`, `public`, `user`, `internal`
- Static files served from addon `static/` directories

---

## Important Patterns

### Inheritance

```python
class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # mixin inheritance
```

### Computed fields

```python
total = fields.Float(compute='_compute_total')

@api.depends('line_ids.price')
def _compute_total(self):
    for rec in self:
        rec.total = sum(rec.line_ids.mapped('price'))
```

### Constraints

```python
@api.constrains('date_start', 'date_end')
def _check_dates(self):
    for rec in self:
        if rec.date_start > rec.date_end:
            raise ValidationError("Start must be before end.")
```

### Onchange (client-side only)

```python
@api.onchange('partner_id')
def _onchange_partner_id(self):
    self.email = self.partner_id.email
```

### Relational field commands

```python
# Write to one2many/many2many
order.write({'line_ids': [
    (0, 0, {'name': 'New line', 'price': 100}),   # CREATE
    (1, existing_id, {'price': 200}),               # UPDATE
    (2, existing_id),                                # DELETE (remove + unlink)
    (3, existing_id),                                # UNLINK (remove only)
    (4, existing_id),                                # LINK
    (5, 0, 0),                                      # CLEAR all
    (6, 0, [id1, id2]),                             # SET (replace all)
]})
```

---

## Addon Categories (high-level)

| Category | Key addons |
|----------|-----------|
| Core | `web`, `mail`, `bus`, `http_routing` |
| Business | `sale`, `purchase`, `account`, `stock`, `mrp`, `crm`, `project`, `hr` |
| eCommerce | `website`, `website_sale`, `website_slides` |
| POS | `point_of_sale`, `pos_restaurant`, `pos_*` (~30 modules) |
| Marketing | `mass_mailing`, `marketing_card`, `social_media` |
| Localization | `l10n_*` (~200+ country modules) |
| Payment | `payment_stripe`, `payment_paypal`, `payment_adyen`, `payment_*` (~20+) |
| Integrations | `google_*`, `microsoft_*`, `sms_twilio` |
| Spreadsheets | `spreadsheet`, `spreadsheet_dashboard_*` |
| Testing | `test_*` (~15+ dedicated test modules) |

---

## Git & CI

- **No CI workflows** in repo — Odoo uses internal runbot
- **No `.pre-commit-config.yaml`** — uses custom git hooks via `../../../addons/web/tooling/enable.sh`
- **Pre-commit hook** runs `npm run format-staged` (ESLint --fix on staged JS files)
- **JS tooling**: ESLint 8.x + Prettier 2.x + lint-staged (template in `addons/web/tooling/_package.json`)
- Enable JS tooling: `bash addons/web/tooling/enable.sh`

---

## Custom Addons

Custom addons live in `C:\Odoo\odoo\custom\`. The working module there is `school_management` ("University Management System").

### `school_management` structure

```
school_management/
├── __manifest__.py          # name, category Education, version 19.0.1.2.2,
│                            # depends ['auth_signup','base','mail','portal','web'],
│                            # application: True; data + web.assets_backend assets
├── __init__.py              # (models are imported from models/__init__.py)
├── models/                  # ORM model files imported by models/__init__.py
│   ├── __init__.py          # one import per model file
│   ├── res_users.py         # res.users extension -> teacher_id (record-rule backbone)
│   ├── fee.py               # university.fee, fee.line, fee.structure, fee.structure.line
│   ├── grading.py           # grade.scale(+line), assessment.category/result,
│   │                        #   report.card(+line), transcript(+line)
│   ├── timetable.py         # university.timeslot, university.timetable.slot
│   ├── exam.py              # university.exam and university.exam.score
│   ├── staff_attendance.py  # university.staff.attendance
│   └── ...                  # faculty, department, program, subject, classroom,
│                            # academic_year, semester_subject, teacher, student,
│                            # academic_assignment, enrollment, class_section,
│                            # admission, attendance, capability, lesson_plan,
│                            # assignment, notice_board, service_hour, payment,
│                            # dashboard, document_signature, res_config_settings
├── data/                    # cleanup_legacy_models, dashboard_data, fee_sequence,
│   │                        # academic_defaults, mail_template, capability_data,
│   │                        # fix_user_teacher_links, demo_attendance_links
├── demo/                    # attendance_demo (idempotent _seed_attendance_demo for roles)
├── migrations/
│   ├── 19.0.1.2.0/pre-migrate.py
│   └── 19.0.1.2.1/pre-migrate.py  # data repair before schema reload
├── security/
│   ├── security.xml         # six functional roles plus supporting access groups
│   ├── ir.model.access.csv  # role-based grants (NOT broad base.group_user CRUD)
│   ├── record_rules.xml     # teacher/hod/dean/student/portal record scoping
│   └── fix_demo_staff_links.sql  # reference only; Odoo runs the XML <function> instead
├── wizard/                  # student_enrollment, bulk_enrollment, populate_class,
│                            # timetable_generation, teacher_account (+ related views)
├── reports/                 # payment (receipt), curriculum, academic (report card/transcript)
├── views/                   # model views, timetable wizard form, dashboards, menus,
│                            # attendance sheets, reports/actions, and portal placeholder
├── static/src/school_management/
│   ├── dashboard_shell.{js,xml,scss}
│   ├── student_dashboard_shell.{js,xml,scss}
│   ├── teacher_dashboard_shell.{js,xml,scss}
│   └── layout/              # school_layout (OWL sidebar), webclient_patch, topbar_integration
├── scripts/                  # maintenance scripts
│   ├── audit_semester_subject_duplicates.py
│   ├── cleanup_student_data.py
│   ├── cleanup_teacher_data.py
│   └── fix_empty_assignment_teachers.py # repair missing assignment teacher_id
├── tests/
│   └── test_payment.py      # focused payment tests
├── seed/                    # run_seed.py + seed_data.sql (SQL demo data, not part of install)
└── document/                # project_overview, project_structure, agent_guide,
                             # local_configuration_guide, login_guide, architecture, QNA review
```

### Financial & Analytic Accounting Architecture Notes

- **Fee Model Boundary:** `school_management` maintains standalone fee and payment models (`university.fee`, `university.fee.line`, `university.fee.structure`, `university.payment`) for student fee invoicing and receipts without forcing full General Ledger setup.
- **Integration with Odoo `account.analytic.account`:**
  - Academic units (`university.faculty`, `university.department`, `university.program`) map directly to Odoo 19 `account.analytic.account` cost centers (`addons/account/models/account_analytic_account.py`).
  - Student fee moves tag revenue using Odoo 19's `analytic_distribution` dictionary (e.g. `{"<analytic_account_id>": 100.0}`).
  - Leverages standard computed fields `invoice_count` and `vendor_bill_count` along with smart actions `action_view_invoice()` and `action_view_vendor_bill()` to drill down into student invoices and departmental expenses directly from the analytic account.
  - Complete conceptual specifications are documented in [`university_management_system_architecture.md`](university_management_system_architecture.md#13--fee-architecture).

### Demo Data & Attendance Seeding (`demo/attendance_demo.xml`)

- **Role Demonstration:** Loads deterministic attendance data across four core seeded class sections (`DBMS-A101`, `R2`, `B202`, `GM-Y1-A`) so that Student, Teacher, Head of Department, and Dean roles immediately have attendance statistics and risk metrics to review in their dashboards.
- **Execution Mechanism:** Invoked via `<function model="university.attendance" name="_seed_attendance_demo"/>` in `demo/attendance_demo.xml` when installing with demo data enabled (`--without-demo=False`).
- **Idempotency & Pre-requisites:** `_seed_attendance_demo()` creates only missing records and never overwrites existing attendance data. It depends on `data/demo_attendance_links.xml` running first to establish staff/user relationships.

### Class Section & Assignment Architecture Notes

- `university.class.section`:
  - Contains embedded `assignment_ids` under `views/class_section_views.xml`.
  - Context defaults `default_teacher_id`, `default_section_id`, and `default_subject_id` to guarantee one2many lines inherit class instructor metadata.
- `university.assignment`:
  - Enforces `teacher_id` ("Prepared By", `required=True`).
  - Implements `@api.model_create_multi def create(...)` safety net: if `teacher_id` is not passed, falls back to `section_id.teacher_id`. If the section lacks an instructor, raises `ValidationError("Please set a Teacher on the class before adding assignments.")`.
  - Ensures Class form actions (*View Interactive Schedule*, *SCHEDULE TIMETABLE*, *Populate Class*) never encounter validation blocks during auto-save.

### Security highlights

#### Functional dashboard roles

| Role | Group | Dashboard scope |
|---|---|---|
| Student | `group_school_student` | Own academic record, attendance, and finances |
| Teacher/Advisor | `group_school_teacher` | Assigned classes, advisees, attendance, and follow-up |
| Head of Department | `group_school_hod` | Managed department |
| Head of Faculty | `group_school_dean` | Managed faculty and its departments |
| Registrar | `group_school_registrar` | Student records and transcript-request queues |
| University Administrator | `group_school_admin` | Institution-wide operations, role management, settings, and system administration |

- Functional roles are Student, Teacher/Advisor, Head of Department, Head of Faculty, Registrar, and University Administrator. The academic hierarchy is `group_school_user → teacher → hod → dean → admin`; Registrar is separately assigned through `group_school_registrar`. `group_teacher_dashboard` and `group_student_portal` are supporting access groups, not functional roles.
- Record rules scope through `res.users.teacher_id → teacher → department → faculty`.
- Staff attendance uses `university.teacher` as its staff model. Admin has full access;
  teachers are scoped to their own linked staff record; department and faculty leaders
  are scoped through the department/faculty leadership links.
- The group hierarchy is `teacher → hod → dean → admin`. Because access rights are
  additive for inherited groups, staff-attendance write restrictions for HOD/Dean are
  enforced by both ACL/rule definitions and the model guard in
  `models/staff_attendance.py`.

### Timetable generation workflow

- Wizard model: `university.timetable.generation.wizard` in
  `wizard/timetable_generation_wizard.py`.
- The wizard form and action are defined in `views/timetable_views.xml` as
  `view_university_timetable_generation_wizard_form` and
  `action_university_timetable_generation_wizard`; there is no separate
  `wizard/timetable_generation_wizard_views.xml` file.
- Required inputs are an active academic year, matching active semester, one or more
  active class sections, one or more active timeslots, a week-start date, and 1–20 weeks.
- The wizard normalizes the entered start date to Monday, creates
  `university.timetable.slot` records, assigns the section teacher or the first teacher
  assigned to the subject, and reports missing subjects, missing teachers, and timetable
  conflicts in a notification.
- Generated slots inherit the section's semester and academic year through related fields
  on `university.timetable.slot`. Resource conflicts are validated for teacher, section,
  and classroom overlap.
- Current boundary: the wizard does not explicitly validate that the generated dates stay
  inside the semester date range, and it does not prevent selecting an unrelated active
  timeslot. Treat those as validation improvements before relying on the wizard for a
  production calendar.

### Notes / gotchas (Odoo 19 specifics)

- Kanban templates use `t-name="card"` (renamed from `kanban-box`).
- Kanban images use `<field name="image_1920" widget="image" .../>` — the legacy `kanban_image()` JS helper was removed in Odoo 19.
- `<group>` inside a `<search>` view does **not** accept `expand` or `string` attributes.
- Manifest `data` must list **every** XML file (e.g. `menu_views.xml`), or those views silently won't load.
- The current manifest loads `views/timetable_views.xml`; that file contains both the
  timetable views and the timetable-generation wizard form/action.
- `<i class="fa-...">` icons must have a `title` attribute (accessibility warning otherwise).

---

## External References

- [Odoo Documentation](https://www.odoo.com/documentation/master)
- [Developer Tutorials](https://www.odoo.com/documentation/master/developer/howtos.html)
- [Coding Guidelines](https://www.odoo.com/documentation/latest/contributing/development/coding_guidelines.html)
- [CONTRIBUTING.md](../../../CONTRIBUTING.md)
- [`local_configuration_guide.md`](local_configuration_guide.md) — install/upgrade/verify the addon; use `start_odoo.ps1` to launch Odoo with wkhtmltopdf on `PATH`.


                                 ┌──────────────────────────────────────────────┐
                                 │       University Management System           │
                                 │        (Simplified Scope Illustration)       │
                                 └──────────────────────┬───────────────────────┘
                                                        │
          ┌───────────────────────────┬─────────────────┴─────────────┬───────────────────────────┐
          ▼                           ▼                               ▼                           ▼
┌──────────────────┐        ┌──────────────────┐            ┌──────────────────┐        ┌──────────────────┐
│  Administrator   │        │Head of Department│            │ Teacher/Advisor  │        │     Student      │
│(Global Authority)│        │(Dept Scoped Org) │            │ (Advisees/Teach) │        │ (Personal Scope) │
├──────────────────┤        ├──────────────────┤            ├──────────────────┤        ├──────────────────┤
│• Global KPI view │        │• Managed Dept only│            │• Advisees + class│        │• Own profile &   │
│• All depts/facs  │        │• Assign advisors │            │  sections only   │          metrics (GPA,    │
│• All teachers/   │        │  within dept     │            │• Advising notes &│          attendance %,    │
│  students        │        │• Dept risk/GPA/  │            │  interventions   │          standing)        │
│• Configure risk  │        │  attendance trend│            │• Private notes   │        │• Assigned advisor│
│  thresholds      │        │• No unrelated    │            │  confidential    │        │• Shared follow-up│
│• No sudo() hacks │        │  dept access     │            │• Zero fee access │          actions only     │
└──────────────────┘        └──────────────────┘            └──────────────────┘        └──────────────────┘
