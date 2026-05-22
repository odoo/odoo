# Module / Addon Structure Pattern

**Purpose:** Every Odoo feature is packaged as a self-contained addon directory. The structure is a convention enforced by the module loader: specific subdirectory names, mandatory files, and a manifest dictionary that declares metadata and load order.

**Source:** `addons/account/__manifest__.py`, `addons/account/__init__.py`, `addons/cloud_storage_google/__manifest__.py`, `addons/hr_recruitment_survey/__manifest__.py`, `odoo/modules/loading.py`

---

## When to Use

- Creating any new Odoo feature, extension, or localization
- Packaging business logic, views, security rules, and static assets together
- Declaring dependencies on other addons

---

## Directory Layout

```
addons/my_addon/
├── __manifest__.py          # REQUIRED: module metadata and file load list
├── __init__.py              # REQUIRED: Python package root; imports sub-packages
│
├── models/                  # ORM model definitions
│   ├── __init__.py
│   ├── my_model.py
│   └── another_model.py
│
├── views/                   # XML view definitions (ir.ui.view records)
│   ├── my_model_views.xml
│   └── menu_items.xml
│
├── controllers/             # HTTP route handlers
│   ├── __init__.py
│   └── main.py
│
├── wizard/                  # TransientModel + view for modal dialogs
│   ├── __init__.py
│   ├── my_wizard.py
│   └── my_wizard_views.xml
│
├── security/                # Access control
│   ├── ir.model.access.csv  # CRUD permission matrix
│   └── ir_rules.xml         # Row-level record rules
│
├── data/                    # Initial / demo data loaded at install
│   ├── my_data.xml
│   └── ir_sequence.xml
│
├── demo/                    # Demo data (only loaded in demo mode)
│   └── demo_data.xml
│
├── report/                  # QWeb PDF/HTML report templates
│   ├── my_report.xml
│   └── my_report_template.xml
│
├── static/                  # Frontend assets (never Python-served directly)
│   └── src/
│       ├── components/      # OWL components (.js + .xml templates)
│       ├── scss/            # SCSS stylesheets
│       └── img/             # Images / icons
│
└── tests/                   # Automated tests
    ├── __init__.py
    ├── common.py            # Shared test fixtures
    └── test_my_feature.py
```

---

## __manifest__.py

```python
# addons/account/__manifest__.py (condensed)
{
    'name': 'Invoicing',              # Display name in Apps list
    'version': '1.4',                 # Module version (semver convention)
    'summary': 'Invoices & Payments', # One-line description
    'description': """...""",         # Long description (RST)
    'category': 'Accounting/Accounting',  # App store category path
    'sequence': 10,                   # Sort order in app list
    'website': 'https://www.odoo.com/app/invoicing',

    'depends': [                      # Addons that must be installed first
        'base_setup',
        'product',
        'analytic',
        'portal',
    ],

    'data': [                         # Files loaded in order at install/upgrade
        'security/account_security.xml',
        'security/ir.model.access.csv',
        'data/account_data.xml',
        'views/account_move_views.xml',
        'views/account_journal_views.xml',
        'wizard/account_payment_register_views.xml',
        'report/account_invoice_report_view.xml',
    ],

    'demo': [                         # Only loaded when demo mode is active
        'demo/demo_data.xml',
    ],

    'assets': {                       # Frontend asset bundles
        'web.assets_backend': [
            'account/static/src/components/**/*',
            'account/static/src/scss/account.scss',
        ],
        'web.assets_tests': [
            'account/static/tests/tours/**/*',
        ],
    },

    'external_dependencies': {        # Optional: system/pip packages required
        'python': ['pdfminer'],
        'apt': {'pdfminer': 'python3-pdfminer'},
    },

    'installable': True,              # Visible in Apps list
    'auto_install': False,            # Auto-install when all depends are present
    'application': True,              # Top-level App (shows icon on home screen)

    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'uninstall_hook': 'uninstall_hook',  # Optional: Python function called on uninstall
}
```

---

## __init__.py (addon root)

```python
# addons/account/__init__.py
def _account_post_init(env):
    """Called once after the module is first installed."""
    env['res.company'].search([]).compute_account_tax_fiscal_country()

# Import sub-packages in dependency order
from . import controllers
from . import models
from . import demo
from . import wizard
from . import report
from . import tools
```

```python
# addons/account/models/__init__.py — imports each model file
from . import account_move
from . import account_move_line
from . import account_journal
from . import account_tax
from . import account_account
from . import partner
from . import company
```

---

## Minimal Addon (smallest valid structure)

```
addons/my_minimal/
├── __manifest__.py    # {'name': 'My Minimal', 'depends': ['base'], 'installable': True}
└── __init__.py        # (empty)
```

---

## Data Load Order Rules

The `data` list in `__manifest__.py` is **ordered and sequential**. Key rules:

1. Security files (`ir.model.access.csv`) must come **before** any view or data file that references the model
2. Menu items must come **after** the actions they reference
3. `noupdate="1"` blocks in XML are skipped on module upgrade (use for reference/config data)
4. `.csv` files are loaded as `ir.model.access` records (columns: `id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink`)

---

## Auto-Install Pattern

```python
# addons/l10n_gw/__manifest__.py
{
    'name': "Guinea-Bissau - Accounting",
    'depends': ['l10n_syscohada', 'account'],
    'auto_install': ['account'],   # Install automatically when 'account' is installed
}
```

---

## Common Pitfalls

- **Missing `__init__.py` in subdirectory** — Python will silently skip the directory; models will not be loaded and no error appears until runtime.
- **Wrong `data` file order** — referencing an XML ID before its record is created causes `ValueError: External ID not found`. Always put `security/` before `views/`.
- **`version` field format** — Odoo uses `major.minor` (e.g. `'1.4'`), not semver. The version is not auto-incremented; update manually to trigger migration scripts.
- **`assets` key replaces old `web.assets_backend` pattern** — in Odoo 17+, all asset registration goes through the `assets` dict in the manifest, not through `ir.asset` XML records.
- **`application: True` vs `installable: True`** — `application` controls whether the module gets a home-screen icon. All installable modules appear in Apps; only `application=True` ones get top-level visibility.

---

## Related Patterns

- [orm-model-pattern.md](./orm-model-pattern.md) — model files in `models/`
- [view-definition-pattern.md](./view-definition-pattern.md) — view files in `views/`
- [security-model-pattern.md](./security-model-pattern.md) — `security/` directory contents
- [http-controller-pattern.md](./http-controller-pattern.md) — `controllers/` directory
- [test-case-pattern.md](./test-case-pattern.md) — `tests/` directory structure
