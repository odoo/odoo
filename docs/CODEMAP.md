# Code Map

**Source:** Directory structure analysis (find), odoo/release.py, setup.py

## Directory Structure (3 levels)

```
tx10-odoo/
├── odoo/                          # Core Odoo framework (~3.5K+ Python files across all subdirs)
│   ├── __main__.py                # CLI entry point
│   ├── release.py                 # Version info (19.0 FINAL)
│   ├── http.py                    # HTTP/WSGI server (112KB core)
│   ├── sql_db.py                  # Database abstraction (31KB)
│   ├── exceptions.py              # Custom exception hierarchy
│   ├── loglevels.py               # Logging configuration
│   ├── netsvc.py                  # Network/RPC services
│   ├── init.py                    # Module initialization
│   │
│   ├── _monkeypatches/            # Runtime patches (23 modules)
│   ├── cli/                       # Command-line interface (20 subcommands)
│   │   ├── command.py, scaffold.py, shell.py, migrate.py, ...
│   │
│   ├── orm/                       # Object-relational mapping (25 modules)
│   │   ├── fields.py, models.py, expressions.py, query.py, ...
│   │   └── Advanced: Many2one, One2many, inheritance, field delegation
│   │
│   ├── models/                    # Base model classes
│   │   └── Model, TransientModel, AbstractModel definitions
│   │
│   ├── api/                       # API decorators & utilities
│   │   └── @api.model, @api.depends, @api.constrains, etc.
│   │
│   ├── fields/                    # Field type definitions
│   │   └── Char, Integer, Float, DateTime, Many2one, Html, etc.
│   │
│   ├── service/                   # Background services (8 modules)
│   │   ├── db.py, session.py, model.py, ...
│   │
│   ├── modules/                   # Module loading & management (10 modules)
│   │   ├── loading.py, migration.py, graph.py, ...
│   │
│   ├── tools/                     # Utilities (49 modules)
│   │   ├── sql.py, convert.py, runner.py, image.py, ...
│   │   └── XML parsing, SQL builders, asset compression, geo/barcode tools
│   │
│   ├── tests/                     # Testing framework (15 modules)
│   │   ├── common.py, test_case.py, runner.py, ...
│   │
│   ├── upgrade/                   # Schema migration tools
│   │   └── Migration utilities for database upgrades
│   │
│   ├── upgrade_code/              # Data migration helpers (11 modules)
│   │   └── CodeRunner, XMLReader, SQL helpers for upgrade scripts
│   │
│   ├── osv/                       # Legacy ORM layer (for backwards compatibility)
│   │
│   ├── addons/                    # Built-in addons (27 modules)
│   │   ├── base/                  # Core features: users, companies, settings
│   │   ├── web/                   # Web client backend
│   │   ├── web_editor/            # Rich text editing
│   │   └── ... (accounting, sales, hr, crm, purchase, inventory, mrp, etc.)
│   │
│   └── import_xml.rng             # RelaxNG schema for manifest validation
│
├── addons/                        # Custom/community addons (622 subdirectories)
│   ├── [addon_1, addon_2, ...]    # Each addon is a self-contained module
│   └── Standard structure per addon: models/, views/, data/, static/, security/
│
├── setup/
│   └── odoo                       # CLI entry script
│
├── setup.py                       # Package metadata & dependencies
├── requirements.txt               # Pinned dependency versions (103 entries)
├── ruff.toml                      # Linter configuration (45+ rules)
├── setup.cfg                      # Flake8 & install config
│
├── docs/                          # Project documentation
│   ├── TECHSTACK.md               # This tech stack reference
│   ├── CODEMAP.md                 # This file (code structure)
│   └── DEPENDENCIES.md            # Dependency details
│
├── agents/                        # Init-workspace flow state tracking
│   └── init-workspace-flow-state.md
│
└── debian/                        # Debian packaging metadata
```

## Module Organization

### Core Framework (odoo/)
| Module | Purpose | Key Classes/Functions |
|--------|---------|----------------------|
| **orm/** | ORM engine | Model, BaseModel, RecordSet, Field abstraction |
| **models/** | Base models | Model, TransientModel, AbstractModel |
| **api/** | Decorators | @api.model, @api.depends, @api.constrains, @api.onchange |
| **fields/** | Field types | Char, Integer, Float, Many2one, One2many, Html, etc. |
| **cli/** | Command line | scaffold, shell, migrate, shell, deploy, etc. |
| **tools/** | Utilities | SQL builders, XML parsing, image ops, barcode/QR, GIS |
| **service/** | Background | Database service, session mgmt, model service |
| **modules/** | Loading | Module loading, dependency graph, migration runner |
| **tests/** | Testing | TestCase, Common, Runner, Form testing |

### Built-in Addons (odoo/addons/)
| Addon | Purpose |
|-------|---------|
| **base** | Core: users, roles, companies, ACL, settings |
| **web** | Web client backend (routes, data models, widgets) |
| **web_editor** | Rich text, snippet templates, media |
| **account** | General ledger, invoicing, taxes, reconciliation |
| **sale** | Sales orders, quotations, pricing |
| **purchase** | Purchase orders, RFQ, supplier mgmt |
| **stock** | Inventory, warehouses, picking, tracking |
| **hr** | Employees, payroll, leave, attendance |
| **crm** | Leads, opportunities, activities |
| **mrp** | Manufacturing, BOMs, work orders |
| **repair** | Service repair orders |
| **calendar** | Events, meetings, scheduling |
| **mail** | Email, messages, channels |
| **documents** | Document mgmt, OCR integration |
| **...** | 20+ more modules (accounting, ecom, iot, automation, etc.) |

## File Count Estimate

| Category | Count | Notes |
|----------|-------|-------|
| **Python (.py)** | 14,298+ | ~146 in odoo/core + 27 in odoo/addons + 622 in addons/ + tests |
| **Python (odoo/)** | ~3,500+ | Core framework + built-in addons |
| **Python (addons/)** | ~10,000+ | Community/custom addons (622 directories) |
| **Templates (.xml)** | 5,000+ | View definitions, data files |
| **Static (JS/CSS)** | 2,000+ | OWL components, SCSS (via libsass) |
| **Config/Meta** | 200+ | Manifests (__manifest__.py), setup files |
| **Total Codebase** | 21,000+ | Estimated (Python + XML + JS + static assets) |

## Key Architecture Patterns

1. **Module System:** Addons are self-contained packages with models, views, data, security rules
2. **ORM:** Declarative models with field definitions; automatic migration on model changes
3. **API Decorators:** @api.model, @api.depends, @api.constrains for business logic hooks
4. **View System:** XML-based UI definitions (tree, form, kanban, pivot, graph)
5. **Security:** Access control lists (ACL), row-level security (RLS), field permissions
6. **Data Loading:** XML-driven initial data, CSV import/export
7. **Web Stack:** WSGI + Jinja2 templates + OWL (Web Components) frontend
8. **Testing:** Unittest-based with transaction rollback per test
9. **Localization:** Babel i18n, per-module translation files (PO/POT)
10. **Extensibility:** Monkey patching, method wrapping, inheritance chains

## Performance Considerations

- **Gevent:** Async I/O for database & HTTP (non-Windows)
- **Database Pooling:** psycopg2 connection pooling
- **Asset Compression:** rjsmin, libsass preprocessing
- **Caching:** ORM query optimization, field caching layers
- **SQL Optimization:** Raw SQL helpers, bulk operations in tools/
