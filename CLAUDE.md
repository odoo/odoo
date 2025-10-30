# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is **Odoo 19.0** (forked and customized as Sage-ERP), an open-source ERP system built in Python. The codebase follows a modular, plugin-based architecture where functionality is organized into addons/modules. The core framework (`odoo/`) provides the ORM, HTTP server, and infrastructure, while addons in `addons/` implement specific business features.

## Common Commands

### Running Odoo

```bash
# Start Odoo server
./odoo-bin -d database_name --addons-path=addons

# Start with development mode (auto-reload on file changes)
./odoo-bin -d database_name --addons-path=addons --dev=all

# Start with demo data
./odoo-bin -d database_name --addons-path=addons --without-demo=False
```

### Installing/Updating Modules

```bash
# Install a specific module
./odoo-bin -d database_name -i module_name --stop-after-init

# Update a specific module
./odoo-bin -d database_name -u module_name --stop-after-init

# Update all modules
./odoo-bin -d database_name -u all --stop-after-init
```

### Running Tests

```bash
# Run all tests for a module
./odoo-bin -d test_database --test-tags=module_name --stop-after-init

# Run specific test file
./odoo-bin -d test_database --test-tags=/module_name/path/to/test_file --stop-after-init

# Run tests at install
./odoo-bin -d test_database -i module_name --test-enable --stop-after-init

# Run tests post-install only
./odoo-bin -d test_database --test-tags=post_install --stop-after-init
```

### Database Management

```bash
# Create new database
./odoo-bin -d new_database --db_user=postgres --db_password=password --stop-after-init

# Drop database
./odoo-bin --db_name=database_name --db-filter=database_name --stop-after-init --no-database-list
```

### Scaffolding New Modules

```bash
# Create new addon scaffold
./odoo-bin scaffold my_addon addons/

# This creates:
# addons/my_addon/__manifest__.py
# addons/my_addon/__init__.py
# addons/my_addon/models/
# addons/my_addon/views/
# addons/my_addon/security/
# addons/my_addon/controllers/
```

### Code Quality

```bash
# Run ruff linter (configured in ruff.toml)
ruff check .

# Auto-fix linting issues
ruff check --fix .

# Format code
ruff format .
```

### Interactive Shell

```bash
# Start Python shell with Odoo environment
./odoo-bin shell -d database_name

# In shell:
# env['model.name'].search([])
# env['model.name'].browse(1)
```

## High-Level Architecture

### Module-Based Plugin System

Odoo uses a **model-driven architecture** where:
- **Models** define both data structure and business logic (central component)
- **Views** are XML-defined UI layouts auto-generated from models
- **Controllers** handle HTTP routing for web endpoints
- **Data files** (XML/CSV) initialize records and configuration

### Core vs Addons Relationship

**Core (`odoo/`)**: Provides infrastructure
- ORM system (`odoo/orm/`) - BaseModel, Model, TransientModel, field system, registry
- HTTP server (`odoo/http.py`) - Werkzeug-based web server
- CLI tools (`odoo/cli/`) - scaffolding, module management, database operations
- Module loading pipeline (`odoo/modules/`) - discovery, dependency resolution, loading

**Addons (`addons/`)**: Consume core capabilities
- Each addon is a Python package with `__manifest__.py` declaring dependencies
- Addons extend core models via inheritance (`_inherit = 'model.name'`)
- Views extend existing views via XML inheritance with `inherit_id`
- Addons load in dependency order (topologically sorted)

### Module Loading Pipeline

1. Framework initialization - Core ORM classes loaded
2. Module discovery - Scan directories, read `__manifest__.py` files
3. Dependency resolution - Topological sort based on `depends` key
4. Sequential loading per module:
   - Import Python models/controllers from `__init__.py`
   - Register models in the registry
   - Load XML/CSV data files in order from `data` key
   - Execute `post_init_hook` if defined
5. Model registry maintains per-database model instances

### Model Inheritance Patterns

**Classic Inheritance** (`_inherit`):
```python
# Extends existing model - modifies same database table
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    custom_field = fields.Char()  # Adds column to sale_order table
```

**Delegation Inheritance** (`_inherits`):
```python
# Links to parent model - creates separate table
class Company(models.Model):
    _name = 'res.company'
    _inherits = {'res.partner': 'partner_id'}  # Separate tables, linked via partner_id

    partner_id = fields.Many2one('res.partner', required=True)
```

**Mixin Pattern** (AbstractModel):
```python
# Reusable logic - no database table
class AnalyticMixin(models.AbstractModel):
    _name = 'analytic.mixin'

    analytic_distribution = fields.Json()

# Usage:
class AccountMoveLine(models.Model):
    _name = 'account.move.line'
    _inherit = 'analytic.mixin'  # Adds mixin fields/methods
```

### Extension Mechanisms

1. **Model Extension**: Use `_inherit = 'existing.model'` to add fields/methods
2. **View Extension**: Use `inherit_id` with `<xpath>` to modify existing views
3. **Method Override**: Override methods with `super()` call to preserve base logic
4. **Dependencies**: Declare in `__manifest__.py` 'depends' to ensure load order
5. **Hooks**: Use `post_init_hook`, `pre_init_hook` for programmatic setup

### Standard Addon Structure

```
addon_name/
├── __manifest__.py          # Module metadata (name, version, depends, data files)
├── __init__.py              # Import models, controllers, wizards
├── models/                  # Business logic and data models
│   ├── __init__.py
│   └── *.py
├── views/                   # XML UI definitions
│   └── *.xml
├── controllers/             # HTTP endpoints
│   ├── __init__.py
│   └── main.py
├── security/                # Access control
│   ├── groups.xml           # User groups
│   └── ir.model.access.csv  # CRUD permissions
├── data/                    # Initial/static data
│   └── *.xml
├── demo/                    # Demo data (--with-demo flag)
│   └── *.xml
├── wizard/                  # TransientModel workflows
│   ├── *.py
│   └── *.xml
├── tests/                   # Test suite
│   ├── __init__.py
│   ├── common.py            # Base test classes
│   └── test_*.py
├── migrations/              # Version migration scripts
│   └── version/
│       ├── pre-migrate.py   # Before code update
│       └── post-migrate.py  # After code update
├── static/                  # Frontend assets
│   └── src/
└── i18n/                    # Translations
    └── *.po
```

### Field System

The ORM provides rich field types with automatic UI generation:

**Basic Types**: Char, Text, Html, Integer, Float, Monetary, Boolean, Date, Datetime, Selection
**Relational**: Many2one, One2many, Many2many
**Special**: Json, Binary, Image, Properties

Fields support:
- Computed fields with `@api.depends()` dependency tracking
- Automatic database column creation
- Inverse/search methods for bi-directional computation
- `store=True` for persisting computed values

### View System

Views are XML records of type `ir.ui.view` defining UI layouts:
- **List views**: Tabular data display
- **Form views**: Detailed record editing with groups/notebooks/pages
- **Search views**: Filters, grouping, domain-based searching
- **Kanban/Calendar/Graph/Pivot**: Specialized visualizations

Views support inheritance via `inherit_id` and `<xpath>` expressions.

### Security Layers

1. **Model Access** (`ir.model.access.csv`): CRUD permissions per group
2. **Record Rules** (`ir.rule` XML): Row-level filtering with domain expressions
3. **Field Access**: Field-level visibility controls
4. **Code-level**: `raise AccessError` in Python methods

### Data Organization

- **`data/`**: Static reference data (sequences, templates, groups)
- **`demo/`**: Sample data loaded with `--with-demo` flag
- **`security/`**: Groups (XML) and access rules (CSV)
- **XML format**: Most flexible, supports `eval`, `ref()`, field commands
- **CSV format**: Compact for bulk data imports

### Testing Architecture

Tests inherit from base classes in `odoo.tests`:
- `TransactionCase`: Database transactions with rollback
- `HttpCase`: HTTP controller testing
- `AccountTestInvoicingCommon`: Specialized for accounting modules (used extensively)

Test tags control execution:
- `@tagged('post_install')`: Run after module installation
- `@tagged('-at_install')`: Skip during initial install
- `@tagged('module_name')`: Run for specific module

Common pattern:
```python
from odoo.addons.account.tests.common import AccountTestInvoicingCommon

class TestInvoice(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.invoice = cls.init_invoice('out_invoice')

    def test_invoice_workflow(self):
        self.invoice.action_post()
        self.assertEqual(self.invoice.state, 'posted')
```

### Key Design Patterns

**Computed Fields with Dependency Tracking**:
```python
@api.depends('line_ids.amount')
def _compute_total(self):
    for record in self:
        record.total = sum(record.line_ids.mapped('amount'))
```

**Field Commands for Relational Fields**:
```python
from odoo.fields import Command

values = {
    'line_ids': [
        Command.create({'product_id': 1, 'quantity': 5}),
        Command.update(2, {'quantity': 10}),
        Command.delete(3),
        Command.clear(),
    ]
}
```

**Environment & Context**:
```python
# Access registry, user, company, context
self.env['model.name']  # Get model from registry
self.env.user           # Current user
self.env.company        # Current company
self.env.context        # Context dict
self.env.ref('module.xml_id')  # Resolve external ID

# Modify context
self.with_context(lang='en_US')
self.with_user(admin_user)
```

**Wizard Pattern (TransientModel)**:
```python
class PaymentRegister(models.TransientModel):
    _name = 'account.payment.register'

    invoice_ids = fields.Many2many('account.move')
    amount = fields.Monetary(compute='_compute_amount')

    def action_create_payment(self):
        # Process and return action
        return {'type': 'ir.actions.act_window', ...}
```

**Domain Expressions**:
```python
# Filter records
domain = [('state', '=', 'draft'), ('amount', '>', 100)]
records = self.env['model.name'].search(domain)

# New Domain API
from odoo.fields import Domain
domain = Domain('state', '=', 'draft') & Domain('amount', '>', 100)
```

### Migration Scripts

For schema/data changes between versions:

```python
# migrations/version/pre-migrate.py
def migrate(cr, version):
    """Run before code update - use raw SQL"""
    cr.execute("ALTER TABLE account_move ADD COLUMN new_field VARCHAR")

# migrations/version/post-migrate.py
def migrate(cr, version):
    """Run after code update - can use ORM"""
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['account.move'].search([]).recompute()
```

## Important Architectural Concepts

### Registry Pattern
- Each database has its own model registry (per-database isolation)
- Models register automatically via metaclass
- Dynamic model lookup: `env['model.name']`
- Supports model extension at runtime

### Metadata-Driven Design
- Field definitions generate both database schema AND UI
- Views auto-generated from field metadata
- Minimal code for CRUD operations
- Decorator-based field dependency tracking

### Multi-Tenancy
- One Odoo instance hosts multiple databases
- Request specifies database in URL
- Models have `_check_company_auto = True` for automatic company filtering

### Transactional Integrity
- All model operations wrapped in SQL transactions
- Automatic rollback on exceptions
- Manual control via `env.cr.commit()` and `env.cr.rollback()`

## Performance Considerations

- Use `.search(limit=N)` to avoid loading all records
- Mark computed fields with `store=True` for database persistence
- Batch operations: bulk `create()`, `write()`, `unlink()` instead of loops
- Prefetch: ORM automatically prefetches related records to avoid N+1 queries
- Use `read()` for specific fields instead of loading full records

## Custom Addons in This Repo

This repository includes custom HR-focused addons:
- `history_employee` - Employee history tracking
- `ohrms_*` - HR management suite (salary advance, loan, loan accounting, core)
- `oh_employee_*` - Employee document expiry, creation from user
- `hr_*` - HR extensions (reward/warning, reminder, resignation, payroll, multi-company, leave request aliasing, employee transfer/updation)
- `hrms_dashboard` - HR dashboard
- `auto_database_backup` - Automatic database backup functionality

These follow the same architecture patterns as core Odoo addons.

## The Big Picture

Odoo achieves flexibility through:
1. **Metadata-driven design**: Models define structure, UI, and behavior
2. **Multiple inheritance**: Models, mixins, and views support inheritance
3. **Plugin ecosystem**: Addons extend via dependencies and inheritance
4. **Automatic CRUD**: Models auto-generate forms/lists/searches
5. **Registry pattern**: Dynamic model lookup enables runtime extension
6. **Clear separation**: Models (logic), views (UI), controllers (routing), data (config)

The core-addon relationship is **provider-consumer**: core provides infrastructure (ORM, HTTP, CLI, registry) and addons consume capabilities through standard mechanisms (inheritance, dependencies, decorators).
