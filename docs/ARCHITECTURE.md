# Architecture

**Workspace:** tx10-odoo | **Branch:** 19.0 (FINAL)
**References:** [TECHSTACK.md](./TECHSTACK.md) | [CODEMAP.md](./CODEMAP.md) | [PATTERNS/INDEX.md](./PATTERNS/INDEX.md)

---

## System Boundaries

Odoo is a monolithic Python web application backed by a single PostgreSQL database. There is no microservices split in the core architecture — all business logic runs in a single process (or gevent worker pool on Linux/macOS). The system boundary is:

```
Browser / Mobile / External API
         |
   [Werkzeug WSGI]          <- HTTP entry point
         |
   [odoo.http.Controller]   <- Route dispatch (JSON-RPC + HTTP)
         |
   [Odoo ORM]               <- Business logic + record access
         |
   [PostgreSQL 13+]         <- Persistent state
```

External integrations (EDI, payment providers, shipping, SMS, email) connect through dedicated addon modules that wrap third-party APIs.

---

## Core Architecture Layers

### 1. Framework Core (`odoo/`)

The framework provides the runtime shared by all 622+ modules. It is not a business module — it is the engine.

| Sub-package | Role | Key Files |
|-------------|------|-----------|
| `odoo/orm/` | ORM engine: query building, record sets, field resolution | `models.py`, `fields.py`, `expressions.py`, `query.py`, `domains.py` |
| `odoo/models/` | Base model classes exported to module authors | `Model`, `TransientModel`, `AbstractModel` |
| `odoo/api/` | Decorators and environment plumbing | `@api.depends`, `@api.constrains`, `@api.onchange`, `@api.model_create_multi` |
| `odoo/fields/` | Field type definitions | `Char`, `Integer`, `Float`, `DateTime`, `Many2one`, `One2many`, `Many2many`, `Html` |
| `odoo/http.py` | WSGI server, route registry, session management | 112KB single file |
| `odoo/cli/` | 20 CLI subcommands | `scaffold.py`, `shell.py`, `migrate.py`, `deploy.py` |
| `odoo/modules/` | Module loader, dependency graph, migration runner | `loading.py`, `graph.py`, `migration.py` |
| `odoo/tools/` | 49 utility modules | SQL builders, XML parsing, image ops, barcode/QR, asset compression |
| `odoo/service/` | Background services | `db.py`, `session.py`, `model.py` |
| `odoo/tests/` | Testing framework | `common.py`, `test_case.py`, `runner.py` |
| `odoo/upgrade/` | Schema migration utilities | DB upgrade scripting |

### 2. Built-in Addons (`odoo/addons/`)

24 modules that ship inside the framework package itself. These are always available regardless of which community addons are installed.

| Addon | Purpose |
|-------|---------|
| `base` | Core: users, companies, groups, ACL, settings, sequence, action |
| `web` | Web client backend: routes, data endpoints, widget registry |
| `web_editor` | Rich text (HTML) editing, snippet system |

### 3. Community Addons (`addons/`)

622 business modules, each self-contained. Every addon follows the standard layout:

```
addons/<module_name>/
├── __manifest__.py      # Metadata: name, version, depends, data files, assets
├── __init__.py          # Python package root, imports models/controllers
├── models/              # ORM model definitions (one class per file convention)
├── views/               # XML view definitions (form, list, kanban, search)
├── data/                # Static data loaded on install (ir.actions, sequences)
├── demo/                # Demo data (only loaded in demo databases)
├── security/            # ir.model.access.csv + ir_rules.xml
├── controllers/         # HTTP route handlers (odoo.http.Controller subclasses)
├── static/              # Frontend assets
│   └── src/             # OWL components (.js), templates (.xml), styles (.css/.scss)
├── wizard/              # TransientModel dialogs
├── report/              # QWeb report templates
└── tests/               # Test cases
```

---

## ORM Layer

### Model Types

| Class | Stored | Use case |
|-------|--------|----------|
| `models.Model` | Yes (PostgreSQL table) | Persistent business objects |
| `models.TransientModel` | Yes (auto-cleaned) | Wizards, temporary dialog state |
| `models.AbstractModel` | No table | Mixins, shared behavior |

### Field System

Fields are class-level descriptors that drive both the DB schema and the UI:

- **Scalar:** `Char`, `Text`, `Integer`, `Float`, `Monetary`, `Boolean`, `Date`, `Datetime`, `Html`, `Binary`
- **Relational:** `Many2one` (FK), `One2many` (reverse FK), `Many2many` (join table)
- **Computed:** `compute='_method'` — derived value, optionally `store=True` for persistence
- **Related:** `related='field.subfield'` — traverses relational path

### API Decorators

| Decorator | Trigger | Signature |
|-----------|---------|-----------|
| `@api.depends('f1', 'f2')` | Field recompute when dependencies change | `def _compute_x(self)` |
| `@api.constrains('f1')` | Validation on write | `def _check_x(self)` raises `ValidationError` |
| `@api.onchange('f1')` | UI-only reactivity (not persisted) | `def _onchange_x(self)` |
| `@api.model_create_multi` | Batch create optimization | `def create(self, vals_list)` |

Full pattern examples: [PATTERNS/api-decorator-pattern.md](./PATTERNS/api-decorator-pattern.md)

### Domain / Filter Syntax

Queries use a Lisp-style prefix list syntax:

```python
[('state', '=', 'draft'), ('amount_total', '>', 1000)]
# Compound: ['&', ('state', '=', 'draft'), ('partner_id.country_id', '=', 'BE')]
# OR: ['|', ('type', '=', 'out_invoice'), ('type', '=', 'out_refund')]
```

Full pattern: [PATTERNS/domain-filter-pattern.md](./PATTERNS/domain-filter-pattern.md)

---

## HTTP / Web Layer

### WSGI Stack

```
odoo-bin serve
  -> gevent pywsgi (Linux/macOS) | wsgiref (Windows fallback)
    -> odoo.http.Application (WSGI callable)
      -> werkzeug.routing.Map (URL dispatch)
        -> odoo.http.Controller subclasses
```

### Route Types

| Decorator | Response type | Auth default |
|-----------|--------------|--------------|
| `@http.route('/path', type='http')` | HTML (Werkzeug Response) | `user` |
| `@http.route('/path', type='json')` | JSON-RPC 2.0 | `user` |
| `@http.route('/path', auth='public')` | Public access | none |

Full pattern: [PATTERNS/http-controller-pattern.md](./PATTERNS/http-controller-pattern.md)

### Frontend (OWL)

The JavaScript frontend uses OWL (Odoo Web Library) — a lightweight reactive component framework developed by Odoo S.A. OWL components live in `addons/*/static/src/` and are registered via the Odoo service registry, not imported directly.

Key OWL primitives: `Component`, `useState`, `useRef`, `useService`, `onMounted`, `onWillStart`. Templates are co-located XML files using OWL-specific directives (`t-if`, `t-foreach`, `t-on-click`, `t-component`).

Full pattern: [PATTERNS/owl-component-pattern.md](./PATTERNS/owl-component-pattern.md)

---

## Module System

### Load Order

When Odoo starts or a module is installed, the framework resolves the dependency graph and loads in this order:

```
1. Resolve __manifest__.py `depends` → topological sort
2. Execute __init__.py (Python import, model classes registered)
3. Apply ORM metaclass → DB columns created/altered
4. Load data/ files (XML/CSV) → populate ir.* tables
5. Load views/ XML → ir.ui.view records
6. Run migrations (if upgrading)
7. Run tests (if --test-tags specified)
```

### Namespace

All addons live in the `odoo.addons` Python namespace:

```python
from odoo.addons.account.models.account_move import AccountMove
```

### Manifest Keys

```python
# __manifest__.py
{
    'name': 'Human readable name',
    'version': '19.0.1.0.0',
    'depends': ['base', 'mail'],         # Load order + implicit security
    'data': ['security/ir.model.access.csv', 'views/my_view.xml'],
    'assets': {'web.assets_backend': ['static/src/my_component.js']},
    'installable': True,
    'auto_install': False,
}
```

Full pattern: [PATTERNS/module-addon-structure-pattern.md](./PATTERNS/module-addon-structure-pattern.md)

---

## Security Model

Three-layer access control:

| Layer | Mechanism | Granularity |
|-------|-----------|-------------|
| Model-level CRUD | `ir.model.access.csv` | Per-model, per-group (create/read/write/unlink) |
| Record-level | `ir.rule` XML (domain filters) | Per-record, per-group |
| Field-level | `groups='group_xml_id'` on field | Per-field visibility |

Groups are defined in XML as `res.groups` records and assigned to users. All access checks run automatically through the ORM — bypassing the ORM (raw SQL) bypasses security.

Full pattern: [PATTERNS/security-model-pattern.md](./PATTERNS/security-model-pattern.md)

---

## Testing Architecture

### Test Classes

| Class | Database behavior | Use case |
|-------|------------------|----------|
| `TransactionCase` | Full rollback after each test | Unit tests for model methods |
| `HttpCase` | Rollback + HTTP client | Controller tests, UI flows |
| `SavepointCase` | Savepoint per test (faster) | Large test suites |

### Test Filtering

```bash
# Run all tests in a module
./odoo-bin --test-tags /account

# Run specific test class
./odoo-bin --test-tags /account:TestAccountMove

# Run post-install tests only
./odoo-bin --test-tags post_install
```

### Tags

```python
@tagged('post_install', '-at_install')  # Run after install, not at install time
@tagged('standard', 'at_install')       # Default: run at install
```

Full pattern: [PATTERNS/test-case-pattern.md](./PATTERNS/test-case-pattern.md)

---

## Code Style & Linting

| Tool | Config | Key rules enforced |
|------|--------|--------------------|
| **Ruff** | `ruff.toml` | E (pycodestyle), F (pyflakes), UP (pyupgrade), TRY, RUF — 45+ rules |
| **Flake8** | `setup.cfg [flake8]` | RST docstring validation, exclude patterns |

RST directives recognized in docstrings: `@versionadded`, `@deprecated`, `@param`, `@type`, `@returns`.

---

## Code Organization Patterns

All extracted patterns live in `docs/PATTERNS/`. See [PATTERNS/INDEX.md](./PATTERNS/INDEX.md) for the full index with reading paths by role (new developer, frontend developer, DevOps/architect, full-stack feature developer).

| Layer | Patterns |
|-------|----------|
| ORM / Model | orm-model, field-definition, api-decorator, domain-filter, wizard-transient-model |
| HTTP / Controller | http-controller |
| Frontend | owl-component |
| Module System | module-addon-structure |
| Security | security-model |
| Testing | test-case |
