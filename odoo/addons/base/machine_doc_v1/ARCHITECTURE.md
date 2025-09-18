# Base Module Architecture

High-level structure, data flow, and component organization for `core/odoo/addons/base/`.

## Module Identity

- **Name:** Base
- **Technical name:** `base`
- **Category:** Hidden (auto-installed, the kernel of Odoo)
- **Role:** Core framework — ORM infrastructure, model registry, access control, user management, partner data, localization, scheduling, templating

## Layer Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│  ORM Framework (odoo/orm/)                                           │
│  fields, models, api, commands, environments                         │
└───────────────────────────┬──────────────────────────────────────────┘
                            │ defines/extends
                            v
┌──────────────────────────────────────────────────────────────────────┐
│  Base Module (odoo/addons/base/)                                     │
│                                                                      │
│  ┌─────────────────┐  ┌───────────────────┐  ┌────────────────────┐  │
│  │ Model Registry  │  │ Access Control    │  │ Partner/User       │  │
│  │ ir.model        │  │ ir.model.access   │  │ res.partner        │  │
│  │ ir.model.fields │  │ ir.rule           │  │ res.users          │  │
│  │ ir.model.data   │  │ res.groups        │  │ res.company        │  │
│  └────────┬────────┘  └────────┬──────────┘  └────────┬───────────┘  │
│           │                    │                      │              │
│  ┌────────┴────────┐  ┌────────┴──────────┐  ┌─────────┴──────────┐  │
│  │ UI Framework    │  │ Actions           │  │ Infrastructure     │  │
│  │ ir.ui.view      │  │ ir.actions.*      │  │ ir.cron            │  │
│  │ ir.ui.menu      │  │ ir.actions.server │  │ ir.mail.server     │  │
│  │ ir.asset        │  │ ir.actions.report │  │ ir.sequence        │  │
│  │ ir.qweb         │  │ ir.embedded.*     │  │ ir.attachment      │  │
│  └─────────────────┘  └───────────────────┘  └────────────────────┘  │
│                                                                      │
│  ┌─────────────────┐  ┌───────────────────┐  ┌────────────────────┐  │
│  │ Localization    │  │ Module System     │  │ Mixins             │  │
│  │ res.country     │  │ ir.module.module  │  │ image.mixin        │  │
│  │ res.currency    │  │ ir.module.cat.    │  │ avatar.mixin       │  │
│  │ res.lang        │  │ ir.config.param.  │  │ format.address.*   │  │
│  │ res.bank        │  │                   │  │ properties.base.*  │  │
│  └─────────────────┘  └───────────────────┘  └────────────────────┘  │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ Wizards (TransientModel)                                       │  │
│  │ partner merge, language install/export/import, module          │  │
│  │ update/upgrade/uninstall, password change, view reset          │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
                            │
                            v
┌──────────────────────────────────────────────────────────────────────┐
│  PostgreSQL                                                          │
│  Tables, sequences, constraints, record rules, indexes               │
└──────────────────────────────────────────────────────────────────────┘
```

## No HTTP Controllers

The base module has **no controllers**. It is pure infrastructure/data — all HTTP
endpoints live in other modules (`web`, `website`, etc.). Base provides the models,
access control, and ORM extensions that those controllers depend on.

## Directory Structure

```
core/odoo/addons/base/
├── __manifest__.py              # Module metadata + asset/data file declarations
├── __init__.py                  # Imports models, report, wizard + post_init hook
├── models/                      # 63 Python model files (core ORM infrastructure)
│   ├── ir_actions.py            #   7 action classes: window, url, client, todo, close + views
│   ├── ir_actions_report.py     #   Report actions (WeasyPrint PDF/HTML/image rendering)
│   ├── ir_actions_server.py     #   Server actions (code, CRUD, webhook) + history
│   ├── ir_asset.py              #   Asset bundle management (directives, paths, sorting)
│   ├── ir_attachment.py         #   File storage (DB or filestore), GC, MIME detection
│   ├── ir_autovacuum.py         #   Garbage collection framework (@api.autovacuum)
│   ├── ir_binary.py             #   File streaming helpers (images, downloads)
│   ├── ir_config_parameter.py   #   System parameters (key-value config store)
│   ├── ir_cron.py               #   Scheduled jobs + triggers + progress tracking
│   ├── ir_default.py            #   Default field values (per-user, per-company)
│   ├── ir_demo.py               #   Demo data installation
│   ├── ir_demo_failure.py       #   Demo data failure tracking
│   ├── ir_embedded_actions.py   #   Embedded actions in views
│   ├── ir_exports.py            #   Export presets (saved field lists)
│   ├── ir_fields.py             #   Import field type converters
│   ├── ir_filters.py            #   Saved search filters
│   ├── ir_http.py               #   HTTP routing, auth, dispatch, translations
│   ├── ir_logging.py            #   Server/client log storage
│   ├── ir_mail_server.py        #   SMTP mail server configuration and sending
│   ├── ir_model.py              #   Model registry + ir.model.inherit
│   ├── ir_model_access.py       #   ACL + ir.model.constraint + ir.model.relation
│   ├── ir_model_data.py         #   XML ID registry (external identifiers)
│   ├── ir_model_fields.py       #   Field metadata registry
│   ├── ir_model_fields_selection.py # Selection option management
│   ├── ir_module.py             #   Module system (install, upgrade, dependencies)
│   ├── ir_profile.py            #   Code profiling (speedscope output)
│   ├── ir_qweb.py               #   QWeb template engine (compile + render)
│   ├── ir_qweb_fields.py        #   QWeb field widgets (~20 type formatters)
│   ├── ir_rule.py               #   Record-level access rules (domain-based)
│   ├── ir_sequence.py           #   Auto-incrementing sequences (standard/no-gap)
│   ├── ir_ui_menu.py            #   Menu tree (hierarchy, visibility, icons)
│   ├── ir_ui_view.py            #   View definitions (arch, inheritance, validation)
│   ├── ir_ui_view_base.py       #   Default view generators (form/list/kanban/etc.)
│   ├── ir_ui_view_custom.py     #   User-specific view customizations (COW)
│   ├── ir_ui_view_name_manager.py # View XML structure validator
│   ├── assetsbundle.py          #   Asset compilation (JS/CSS/SCSS minification)
│   ├── avatar_mixin.py          #   SVG avatar generation from initials
│   ├── decimal_precision.py     #   Configurable decimal precision
│   ├── image_mixin.py           #   Multi-resolution image fields
│   ├── properties_base_definition.py      # Properties field definitions
│   ├── properties_base_definition_mixin.py # Properties support mixin
│   ├── report_layout.py         #   Report layout templates
│   ├── report_paperformat.py    #   Paper format configuration
│   ├── res_bank.py              #   Banks + partner bank accounts
│   ├── res_company.py           #   Company hierarchy (parent_store)
│   ├── res_config.py            #   Settings wizard framework
│   ├── res_country.py           #   Countries, states, country groups
│   ├── res_currency.py          #   Currencies + exchange rates
│   ├── res_device.py            #   Device/session tracking + revocation
│   ├── res_groups.py            #   Security groups + implications + privileges
│   ├── res_groups_privilege.py  #   Group privilege categories
│   ├── res_lang.py              #   Language management + formatting
│   ├── res_partner.py           #   Contacts/companies (core business entity)
│   ├── res_partner_category.py  #   Partner tags (hierarchical)
│   ├── res_partner_format_address_mixin.py # Address form customization
│   ├── res_partner_format_vat_mixin.py     # VAT label customization
│   ├── res_partner_industry.py  #   Industry classification
│   ├── res_users.py             #   Users (inherits res.partner)
│   ├── res_users_apikeys.py     #   API key management
│   ├── res_users_deletion.py    #   User deletion queue
│   ├── res_users_identitycheck.py # Password verification wizard
│   ├── res_users_log.py         #   Login tracking
│   └── res_users_settings.py    #   Per-user settings
├── wizard/                      # 10 transient model files
│   ├── base_export_language.py  #   Export translations (PO/CSV/TGZ)
│   ├── base_import_language.py  #   Import translation files
│   ├── base_language_install.py #   Install/activate languages
│   ├── base_module_uninstall.py #   Module uninstall with dependency analysis
│   ├── base_module_update.py    #   Scan for new/updated modules
│   ├── base_module_upgrade.py   #   Upgrade module with dependency validation
│   ├── base_partner_merge.py    #   Deduplicate partners (manual/automatic)
│   ├── change_password.py       #   Password change (admin + self-service)
│   ├── reset_view_arch.py       #   Reset view to original arch (soft/hard)
│   └── wizard_ir_model_menu_create.py # Create menu item for custom model
├── tests/                       # 85 Python test files + test assets
│   ├── common.py                #   Base test classes (demo user, portal user)
│   └── test_*.py                #   ~195 test classes, ~1347 test methods
├── views/                       # 34 XML view definition files
├── data/                        # 21 XML/CSV data files (countries, currencies, params)
├── report/                      # 4 report template files
├── security/                    # 2 files (ir.model.access.csv + security groups XML)
├── rng/                         # 7 RelaxNG schema files (view validation)
├── static/                      # CSS, JS, images, test assets (~348 files)
├── i18n/                        # 63 translation files (.po)
└── machine_doc_v1/              # Machine-consumable documentation (this directory)
```

## Model Categories

### Infrastructure Models (ir.*)

The `ir.*` namespace contains all framework-level models. These implement the ORM
registry, access control, UI framework, scheduling, and module system.

| Category | Models | Purpose |
|----------|--------|---------|
| Model Registry | ir.model, ir.model.inherit, ir.model.fields, ir.model.fields.selection | Schema introspection, custom model/field creation |
| Access Control | ir.model.access, ir.rule, ir.model.constraint, ir.model.relation | ACL rules, record rules, DB constraints |
| Data Registry | ir.model.data | XML ID ↔ record ID mapping |
| UI Framework | ir.ui.view, ir.ui.view.custom, ir.ui.menu, ir.asset | Views, menus, asset bundles |
| Actions | ir.actions.actions, ir.actions.act_window, ir.actions.act_url, ir.actions.client, ir.actions.act_window_close, ir.actions.todo | All action types for navigation |
| Server Actions | ir.actions.server, ir.actions.server.history | Automated actions (code, CRUD, webhook) |
| Reports | ir.actions.report | PDF/HTML report rendering (WeasyPrint) |
| Embedded Actions | ir.embedded.actions | Actions embedded within views |
| Templating | ir.qweb, ir.qweb.field (+ ~20 subclasses) | QWeb compile/render, field formatting |
| Scheduling | ir.cron, ir.cron.trigger, ir.cron.progress | Scheduled jobs with trigger system |
| Storage | ir.attachment | File storage (DB or filestore) |
| Streaming | ir.binary | File/image download helpers |
| Sequences | ir.sequence, ir.sequence.date_range | Auto-incrementing sequences |
| Configuration | ir.config_parameter, ir.default, ir.filters, ir.exports | System params, defaults, saved filters |
| Module System | ir.module.module, ir.module.category | Module lifecycle management |
| Mail | ir.mail.server | SMTP configuration and email sending |
| HTTP | ir.http | Routing, auth dispatch, translations |
| Logging | ir.logging, ir.profile | Server logs, code profiling |
| Import | ir.fields.converter | Data import type conversion |
| Autovacuum | ir.autovacuum | Garbage collection framework |
| Demo | ir.demo, ir.demo_failure, ir.demo_failure.wizard | Demo data management |

### Resource Models (res.*)

The `res.*` namespace contains all business entity models — the core data that
every Odoo module depends on.

| Category | Models | Purpose |
|----------|--------|---------|
| Partners | res.partner, res.partner.category, res.partner.industry | Contacts, companies, tags, industries |
| Users | res.users, res.users.log, res.users.settings, res.users.deletion | User accounts, preferences, audit |
| Auth | res.users.apikeys, res.users.identitycheck | API keys, password verification |
| Security | res.groups, res.groups.privilege | Group hierarchy, privilege categories |
| Companies | res.company | Multi-company hierarchy (parent_store) |
| Localization | res.country, res.country.state, res.country.group, res.lang | Geography, languages |
| Finance | res.currency, res.currency.rate, res.bank, res.partner.bank | Currencies, exchange rates, banking |
| Config | res.config, res.config.settings | Settings wizard framework |
| Devices | res.device, res.device.log | Session/device tracking |

### Mixins and Utilities

| Model | Purpose |
|-------|---------|
| image.mixin | Multi-resolution image fields (1920/1024/512/256/128) |
| avatar.mixin | SVG avatar generation from name initials |
| format.address.mixin | Country-specific address form layout |
| format.vat.label.mixin | Country-specific VAT field labeling |
| properties.base.definition | Properties field definition storage |
| properties.base.definition.mixin | Properties support for models |
| decimal.precision | Configurable decimal precision per usage |
| report.layout | Report layout template registry |
| report.paperformat | Paper format configuration (A4, Letter, etc.) |

### Non-ORM Classes

| Class | File | Purpose |
|-------|------|---------|
| AssetsBundle | assetsbundle.py | Asset compilation engine (JS/CSS/SCSS minification) |
| NameManager | ir_ui_view_name_manager.py | View XML structure validation |
| RecordSnapshot | (in web module) | Form state diffing for onchange |
| AssetPaths | ir_asset.py | Asset path collection and ordering |

## File Counts

| Category | Count |
|----------|-------|
| Python (models) | 63 |
| Python (wizards) | 10 |
| Python (tests) | 85 |
| XML (views) | 34 |
| XML (data) | 21 |
| XML (reports) | 4 |
| XML (wizard views) | 8 |
| CSV (data + security) | 3 |
| RNG (schemas) | 7 |
| i18n (translations) | 63 |
| Static assets | ~348 |
| **Total** | **~650+** |
