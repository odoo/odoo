# Base Module Architecture

High-level structure, data flow, and component organization for `odoo/addons/base/`.

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
│  │ ir.ui.menu      │  │ ir.actions.server │  │ ir.sequence        │  │
│  │ ir.asset        │  │ ir.actions.report │  │ ir.attachment      │  │
│  │ ir.qweb         │  │ ir.embedded.*     │  │ ir.job             │  │
│  └─────────────────┘  └───────────────────┘  └────────────────────┘  │
│                                                                      │
│  ┌─────────────────┐  ┌───────────────────┐  ┌────────────────────┐  │
│  │ Localization    │  │ Module System     │  │ Mixins             │  │
│  │ res.country     │  │ ir.module.module  │  │ mixin.image        │  │
│  │ res.currency    │  │ ir.module.cat.    │  │ mixin.avatar       │  │
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
odoo/addons/base/
├── __manifest__.py              # Module metadata + asset/data file declarations
├── __init__.py                  # Imports models, report, wizard + post_init hook
├── models/                      # 106 Python model files (core ORM infrastructure)
│   ├── assetsbundle/            #   Asset compilation package (bundle, JS/CSS/XML pipelines, store)
│   ├── decimal_precision.py         #   Configurable decimal precision
│   ├── ir_actions_act_url.py        #   URL action
│   ├── ir_actions_act_window.py     #   Window actions (open views on a model)
│   ├── ir_actions_act_window_close.py #   Close-window action
│   ├── ir_actions_act_window_view.py #   View ordering inside a window action
│   ├── ir_actions_actions.py        #   Base action model: bindings, path, type dispatch
│   ├── ir_actions_client.py         #   Client-side (JS component) action
│   ├── ir_actions_embedded.py       #   Actions embedded inside views
│   ├── ir_actions_path.py           #   Side table keeping an action path unique
│   ├── ir_actions_report.py         #   Report actions (action type, HTML/text render; PDF is web's inherit)
│   ├── ir_actions_server.py         #   Server actions (code, CRUD, webhook)
│   ├── ir_actions_server_history.py #   Code history of a server action
│   ├── ir_actions_todo.py           #   Configuration wizard queue
│   ├── ir_asset.py                  #   Asset bundle management (directives, paths, sorting)
│   ├── ir_asset_paths.py            #   Asset directive walk: paths, anchors, insert/remove/replace
│   ├── ir_attachment.py             #   File storage (DB or filestore), GC, MIME detection
│   ├── ir_attachment_assets.py      #   ir.attachment extension: generated-asset GC and regeneration
│   ├── ir_attachment_storage.py     #   Storage backends (DB, filestore, registry of schemes)
│   ├── ir_autovacuum.py             #   Garbage collection framework (@api.autovacuum)
│   ├── ir_binary.py                 #   File streaming helpers (images, downloads)
│   ├── ir_egress.py                 #   Outbound HTTP: address policy, pinned sessions, caps
│   ├── ir_config_parameter.py       #   System parameters (key-value config store)
│   ├── ir_cron.py                   #   Scheduled jobs + triggers + progress tracking
│   ├── ir_default.py                #   Default field values (per-user, per-company)
│   ├── ir_demo.py                   #   Demo data installation
│   ├── ir_demo_failure.py           #   Demo data failure tracking
│   ├── ir_fields.py                 #   Import field type converters
│   ├── ir_filters.py                #   Saved search filters
│   ├── ir_http.py                   #   HTTP routing, auth, dispatch, translations
│   ├── ir_job.py                    #   Background job queue + channels
│   ├── ir_logging.py                #   Server/client log storage
│   ├── ir_model.py                  #   Model registry + ir.model.inherit
│   ├── ir_model_access.py           #   ir.model.access (model-level ACL)
│   ├── ir_model_common.py           #   Shared helpers for the ir.model family (xmlids, upserts, access errors)
│   ├── ir_model_data.py             #   XML ID registry (external identifiers)
│   ├── ir_model_fields.py           #   Field metadata registry
│   ├── ir_model_fields_selection.py #   Selection option management
│   ├── ir_model_reflection.py       #   ir.model.constraint + ir.model.relation (uninstall bookkeeping)
│   ├── ir_module.py                 #   Module system (install, upgrade, dependencies)
│   ├── ir_module_module_dependency.py #   Manifest `depends` entries
│   ├── ir_module_module_exclusion.py #   Manifest `excludes` entries
│   ├── ir_profile.py                #   Code profiling (speedscope output)
│   ├── ir_qweb.py                   #   QWeb template engine (compile + render)
│   ├── ir_qweb_assets.py            #   ir.qweb extension: asset nodes, ESM bundles
│   ├── ir_qweb_assets_esbuild.py    #   ir.qweb extension: esbuild circuit, advisory lock, compile
│   ├── ir_qweb_assets_esbuild_circuit.py #   esbuild failure circuit breaker
│   ├── ir_qweb_assets_import_map.py #   ir.qweb extension: the page's ESM import map
│   ├── ir_qweb_assets_served_libs.py #   ir.qweb extension: vendored libraries served to the page
│   ├── ir_qweb_fields.py            #   QWeb field widgets (~20 type formatters)
│   ├── ir_rule.py                   #   Record-level access rules (domain-based)
│   ├── ir_sequence.py               #   Auto-incrementing sequences (standard/no-gap)
│   ├── ir_ui_menu.py                #   Menu tree (hierarchy, visibility, icons)
│   ├── ir_ui_view.py                #   View definitions (arch, inheritance, validation)
│   ├── ir_ui_view_arch.py           #   Arch element handlers (validation, postprocessing, editability)
│   ├── ir_ui_view_base.py           #   Default view generators (form/list/kanban/etc.)
│   ├── ir_ui_view_custom.py         #   User-specific view customizations (COW)
│   ├── ir_ui_view_name_manager.py   #   View XML structure validator
│   ├── kpi_provider.py              #   KPI aggregation hook (abstract)
│   ├── mixin_avatar.py              #   SVG avatar generation from initials
│   ├── mixin_band.py                #   Numeric band / range mixin
│   ├── mixin_catalog.py             #   Unique translated name, archivable
│   ├── mixin_lifecycle.py           #   Declared state transitions, locking, confirm/cancel checks
│   ├── mixin_color.py               #   Shared defaults, hex validation and palette conversion
│   ├── mixin_favorite.py            #   Per-record favourite flag
│   ├── mixin_format_address.py      #   Address form customization
│   ├── mixin_format_vat_label.py    #   VAT label customization
│   ├── mixin_hierarchy.py           #   Parent/child tree on a materialized path (`parent_path`)
│   ├── mixin_image.py               #   Multi-resolution image fields
│   ├── mixin_merge.py               #   Record merge engine (reference repointing)
│   ├── mixin_module_link.py         #   Manifest-named module link (abstract)
│   ├── mixin_properties_base_definition.py #   Properties support mixin
│   ├── mixin_recurrence_anchored.py #   Fixed points inside a period: weekday, day, month, twice
│   ├── mixin_recurrence_interval.py #   Every N units: repeat_interval, repeat_unit, next occurrence
│   ├── mixin_recurrence_occurrence.py #   Which occurrences an edit applies to
│   ├── mixin_recurrence_rrule.py    #   iCalendar RRULE engine over the rule
│   ├── mixin_recurrence_rule.py     #   Interval plus end policy (forever/until)
│   ├── mixin_table_inheritance_root.py #   PostgreSQL table-inheritance tree: concrete type by tableoid, ondelete, root dispatch
│   ├── mixin_tag.py                 #   Coloured label with a stable code
│   ├── mixin_tag_nested.py          #   Tag with a parent/child hierarchy
│   ├── mixin_user_favorite.py       #   Per-user favourite flag
│   ├── phone_number.py              #   Shared phone number records
│   ├── properties_base_definition.py #   Properties field definitions
│   ├── report_paperformat.py        #   Paper format configuration
│   ├── res_bank.py                  #   Banks + partner bank accounts
│   ├── res_company.py               #   Company hierarchy (parent_store)
│   ├── res_config.py                #   Settings wizard framework
│   ├── res_country.py               #   Countries, states, country groups
│   ├── res_currency.py              #   Currencies + exchange rates
│   ├── res_device.py                #   Device/session tracking + revocation
│   ├── res_groups.py                #   Security groups + implications + privileges
│   ├── res_groups_privilege.py      #   Group privilege categories
│   ├── res_lang.py                  #   Language management + formatting
│   ├── res_partner.py               #   Contacts/companies (core business entity)
│   ├── res_partner_identifier.py    #   One contact's identifier value
│   ├── res_partner_identifier_type.py #   Identifier kinds (RFC, CURP, SIREN...)
│   ├── res_partner_industry.py      #   Industry classification
│   ├── res_partner_tag.py           #   Partner tags (hierarchical)
│   ├── res_users.py                 #   Users (inherits res.partner)
│   ├── res_users_apikeys.py         #   API key management
│   ├── res_users_auth.py            #   Password store: hashing and checks under _get_crypt_context
│   ├── res_users_deletion.py        #   User deletion queue
│   ├── res_users_identitycheck.py   #   Password verification wizard
│   ├── res_users_log.py             #   Login tracking
│   ├── res_users_login_cooldown.py  #   Login-failure cooldown counter
│   ├── res_users_settings.py        #   Per-user settings
│   └── tag_tag.py                   #   Generic tag records
├── wizards/                      # 11 transient model files
│   ├── base_export_language.py      #   Export translations (PO/CSV/TGZ)
│   ├── base_import_language.py      #   Import translation files
│   ├── base_language_install.py     #   Install/activate languages
│   ├── base_module_uninstall.py     #   Module uninstall with dependency analysis
│   ├── base_module_update.py        #   Scan for new/updated modules
│   ├── base_module_upgrade.py       #   Upgrade module with dependency validation
│   ├── base_partner_merge.py        #   Deduplicate partners (manual/automatic)
│   ├── change_password.py           #   Password change (admin + self-service)
│   ├── reset_view_arch.py           #   Reset view to original arch (soft/hard)
│   ├── server_action_history.py     #   Server-action run history (diff + restore)
│   └── wizard_ir_model_menu_create.py #   Create menu item for custom model
├── tests/                       # 140 Python test files + test assets
│   ├── common.py                #   Base test classes (demo user, portal user)
│   └── test_*.py                #   Test modules -- counts in TEST_TAGS.md, derived by factcheck.sh
├── views/                       # 37 XML view definition files
├── data/                        # 20 data files (XML, CSV, SQL, JSON)
├── security/                    # ir.model.access.csv + groups and record-rule XML
├── rng/                         # RelaxNG schemas (view validation)
├── static/                      # CSS, JS, images, test assets
├── i18n/                        # Translations (.po)
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
| Configuration | ir.config_parameter, ir.default, ir.filters | System params, defaults, saved filters |
| Module System | ir.module.module, ir.module.category | Module lifecycle management |
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
| Partners | res.partner, res.partner.tag, res.partner.industry | Contacts, companies, tags, industries |
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
| mixin.image | Multi-resolution image fields (1920/1024/512/256/128) |
| mixin.avatar | SVG avatar generation from name initials |
| mixin.format.address | Country-specific address form layout |
| mixin.format.vat.label | Country-specific VAT field labeling |
| properties.base.definition | Properties field definition storage |
| mixin.properties.base.definition | Properties support for models |
| decimal.precision | Configurable decimal precision per usage |
| report.paperformat | Paper format configuration (A4, Letter, etc.) |

### Non-ORM Classes

| Class | File | Purpose |
|-------|------|---------|
| AssetsBundle | assetsbundle.py | Asset compilation engine (JS/CSS/SCSS minification) |
| NameManager | ir_ui_view_name_manager.py | View XML structure validation |
| RecordSnapshot | (in web module) | Form state diffing for onchange |
| AssetPaths | ir_asset.py | Asset path collection and ordering |

## File Counts

Derived by `factcheck.sh`, which re-measures every row against the tree.

| Category | Count |
|----------|-------|
| Python (models) | 106 |
| Python (wizards) | 11 |
| Python (tests) | 140 |
| XML (views) | 37 |
| Data files | 20 |
| XML (reports) | 0 |
| XML (wizard views) | 8 |
| Security files | 3 |
| RNG (schemas) | 7 |
| i18n (translations) | 64 |
| Static assets | 348 |
