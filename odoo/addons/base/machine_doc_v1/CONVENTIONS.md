# Base Module Conventions

Module-specific patterns, rules, and gotchas for working in `core/odoo/addons/base/`.

## No Controllers

The base module has **zero HTTP controllers**. All endpoints live in `web`, `website`,
or other frontend modules. Base is pure infrastructure: ORM models, access control,
data management, and framework extensions.

## Model Naming Conventions

### `ir.*` — Internal Registry

Framework-level models that implement the ORM infrastructure. Users never interact
with these directly; they power the framework.

| Prefix | Purpose | Examples |
|--------|---------|---------|
| `ir.model` | Schema introspection | ir.model, ir.model.fields, ir.model.data |
| `ir.actions` | Navigation actions | ir.actions.act_window, ir.actions.server |
| `ir.ui` | UI definitions | ir.ui.view, ir.ui.menu |
| `ir.cron` | Scheduling | ir.cron, ir.cron.trigger |
| `ir.rule` | Access control | ir.rule, ir.model.access |
| `ir.config_parameter` | Configuration | Key-value system parameters |

### `res.*` — Resource

Business entities that users interact with directly.

| Prefix | Purpose | Examples |
|--------|---------|---------|
| `res.partner` | Contacts/companies | res.partner, res.partner.category |
| `res.users` | User accounts | res.users, res.users.apikeys |
| `res.company` | Multi-company | res.company |
| `res.country` | Geography | res.country, res.country.state |
| `res.currency` | Finance | res.currency, res.currency.rate |
| `res.lang` | Localization | res.lang |
| `res.groups` | Security | res.groups, res.groups.privilege |

## Inheritance Patterns

### Extension Inheritance (`_inherit` without `_name`)

Most models in base use extension inheritance — adding fields/methods to existing
models without creating new database tables.

```python
# Extends the existing base model (adds method to ALL models)
class Base(models.AbstractModel):
    _inherit = 'base'
    def get_empty_list_help(self, help_message): ...
```

### Delegation Inheritance (`_inherits`)

Used sparingly — creates a "has-a" relationship with automatic field delegation.

```python
# res.users delegates to res.partner (shares partner fields)
class ResUsers(models.Model):
    _name = 'res.users'
    _inherits = {'res.partner': 'partner_id'}
    partner_id = fields.Many2one('res.partner', required=True)
    # All partner fields are accessible directly on res.users

# ir.cron delegates to ir.actions.server
class IrCron(models.Model):
    _name = 'ir.cron'
    _inherits = {'ir.actions.server': 'ir_actions_server_id'}
```

### Parent Store (`_parent_store = True`)

Used for hierarchical models that need efficient ancestor/descendant queries.

```python
# These models use _parent_store:
# - res.company (company tree)
# - res.partner.category (tag hierarchy)
# - ir.ui.menu (menu tree)
```

## Caching Patterns

### `@tools.ormcache()`

Heavy use throughout base for expensive queries that rarely change:

```python
# Cached by model name — cleared on ACL changes
@tools.ormcache("model_name", "access_mode", cache="stable")
def _get_access_groups(self, model_name, access_mode="read"): ...

# Cached by XML ID — cleared on data changes
@tools.ormcache('xmlid')
def _xmlid_lookup(self, xmlid): ...

# Cached by model name — cleared on rule changes
@tools.ormcache('self.env.uid', 'self.env.su', 'model_name', 'mode')
def _compute_domain(self, model_name, mode='read'): ...
```

**Cache invalidation**: Most cached methods are invalidated via `clear_caches()` in
`write()` and `unlink()` methods. Missing cache invalidation is a common source of bugs.

### `@tools.ormcache_context()`

Cache varies by context keys (e.g., `lang`, `company_id`).

## Access Control Architecture

### Three Layers

1. **Model ACL** (`ir.model.access`) — CRUD permissions per model per group
2. **Record Rules** (`ir.rule`) — Domain-based record filtering per group per operation
3. **Field Groups** (`groups=` on fields) — Field visibility per group

### Group Implications

Groups form an implication graph:
- `base.group_system` implies `base.group_erp_manager` implies `base.group_user`
- `base.group_portal` and `base.group_public` are **disjoint** with `base.group_user`
- Adding a user to a group automatically adds them to all implied groups

### Superuser (`SUPERUSER_ID = 1`)

Bypasses all access control (ACL + record rules). Used internally for cron jobs,
system operations, and bootstrap. Check with `self.env.su`.

## Settings Framework

### `res.config.settings` Field Naming Convention

```python
class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Prefix: default_ → sets ir.default for the field
    default_invoice_policy = fields.Selection(
        default_model='sale.order'  # target model for the default
    )

    # Prefix: group_ → toggles group membership
    group_multi_currency = fields.Boolean(
        implied_group='base.group_multi_currency'
    )

    # Prefix: module_ → installs/uninstalls module
    module_sale = fields.Boolean()

    # Attribute: config_parameter → reads/writes ir.config_parameter
    auth_signup_uninvited = fields.Selection(
        config_parameter='auth_signup.invitation_scope'
    )
```

## XML ID Conventions

### Format: `module.identifier`

```python
# Lookup
self.env.ref('base.main_company')  # → res.company record
self.env['ir.model.data']._xmlid_to_res_id('base.user_admin')  # → integer ID

# Common base XML IDs:
# base.main_company     — Primary company
# base.user_admin       — Admin user (uid=2)
# base.user_root        — OdooBot/Superuser (uid=1)
# base.group_user       — Internal User group
# base.group_system     — Settings group (admin)
# base.group_erp_manager — Access Rights group
# base.group_portal     — Portal User group
# base.group_public     — Public User group
# base.main_partner     — Main company partner
# base.EUR, base.USD    — Currencies
```

## Autovacuum Pattern

Models that need periodic cleanup implement `@api.autovacuum` methods:

```python
class MyModel(models.Model):
    _name = 'my.model'

    @api.autovacuum
    def _gc_old_records(self):
        """Called by ir.autovacuum cron job."""
        limit_date = fields.Datetime.now() - timedelta(days=30)
        self.search([('create_date', '<', limit_date)]).unlink()
```

**Base models using autovacuum:**
- `ir.attachment` — Filestore garbage collection
- `ir.autovacuum` — Run all `@api.autovacuum` methods
- `ir.cron` — Old trigger cleanup (×2: triggers + progress)
- `ir.http` — Session garbage collection
- `ir.profile` — Profiles older than 30 days
- `ir.actions.server.history` — Keep last 100 code revisions
- `res.users.apikeys` — Expired API keys
- `res.users.log` — Keep latest log per user
- `res.device` — Old device entries (×2: devices + logs)

## Sequence Implementation

Two implementations for auto-incrementing numbers:

| Implementation | Method | Trade-off |
|---------------|--------|-----------|
| `standard` | PostgreSQL `nextval()` | Fast, concurrent, but gaps on rollback |
| `no_gap` | `SELECT FOR UPDATE` + increment | No gaps, but serialized (slower) |

```python
# Sequence with date ranges (e.g., INV/2024/0001, INV/2025/0001)
seq = self.env['ir.sequence'].next_by_code('account.invoice')
```

## QWeb Template Compilation

QWeb templates are compiled to Python functions and cached:

```python
# Template compilation flow:
# 1. XML arch → parse with lxml
# 2. _compile() → walk nodes, generate Python AST
# 3. compile() → Python code object
# 4. Cache with ormcache (keyed by template + options)
# 5. _render() → execute cached function with values dict
```

**Safe eval**: QWeb expressions are evaluated in a restricted sandbox.
The `_SAFE_QWEB_OPCODES` set in `ir_qweb.py` controls which Python bytecodes
are permitted. This must be updated when upgrading Python versions (new opcodes).

## Report Rendering

Reports use WeasyPrint (not wkhtmltopdf):

```
ir.actions.report._render_qweb_pdf(docids, data)
  → QWeb renders HTML template
  → _prepare_weasyprint_html() splits headers/bodies/footers
  → _render_html_to_pdf() via WeasyPrint
  → Returns (PDF bytes, report_type)
```

**OdooURLFetcher**: Custom URL resolver for WeasyPrint that handles:
- `/web/assets/` → Asset bundles
- `/<module>/static/` → Static files
- HTTP fallback for other URLs

## Test Conventions

### Base Classes (from `base/tests/common.py`)

| Class | Parent | Purpose |
|-------|--------|---------|
| `TransactionCaseWithUserDemo` | TransactionCase | Pre-loads demo user + company context |
| `HttpCaseWithUserDemo` | HttpCase | HTTP tests with demo user |
| `SavepointCaseWithUserDemo` | TransactionCase | Savepoint with demo user |
| `TransactionCaseWithUserPortal` | TransactionCase | Portal user context |
| `HttpCaseWithUserPortal` | HttpCase | HTTP tests with portal user |

### Tag Strategy

- **62% of test files have no `@tagged` decorator** — they run in all phases by default
- **38% use `@tagged`** — typically `@tagged('post_install', '-at_install', 'feature_tag')`
- The `post_install` + `-at_install` pattern is always used together (39 classes)

See `machine_doc_v1/TEST_TAGS.md` for full reference.

## Gotchas

1. **`res.users` inherits `res.partner`** — Every user IS a partner. Creating a user
   auto-creates a partner. Deleting requires care (partner may have other references).

2. **Group implications are transitive** — Adding `group_system` automatically adds
   all implied groups down the chain. Removing a group does NOT remove implied groups
   (they may be implied by other groups too).

3. **`ir.model.data` noupdate flag** — Records with `noupdate=True` are NOT updated
   on module upgrade. This is correct for user-modified data but can cause confusion
   when fixing data bugs.

4. **Cache invalidation** — `ir.rule`, `ir.model.access`, `ir.model.data`, `res.groups`
   all use heavy caching. Changes to these models require `clear_caches()` or the
   change won't take effect until server restart.

5. **`_auto = False` models** — `res.device` and `res.users.apikeys` don't use
   standard ORM table creation. `res.device` is a SQL view, `res.users.apikeys`
   has a custom table with encrypted key storage.

6. **Partner commercial hierarchy** — `commercial_partner_id` is the top-level
   company in a parent-child chain. It's computed, stored, and recursive. Many
   business modules (accounting, sales) use it for grouping.

7. **Company-dependent fields** — Fields with `company_dependent=True` store
   different values per company via `ir.property`. Changing company context
   returns different values for the same record.

8. **`res.config.settings` is transient** — Settings records are created fresh
   each time the settings form opens. `default_get()` loads current state,
   `set_values()` saves it. Don't try to browse old settings records.

9. **View inheritance order** — Views are applied by `priority` (lower = first),
   then by `id`. Changing priority can break inheritance chains. Use
   `machine_doc_v1/ARCHITECTURE.md` → "UI Framework" section for view resolution.

10. **`@api.autovacuum` runs as SUPERUSER** — Autovacuum methods bypass all access
    control. They run in the `ir.autovacuum._run_vacuum_cleaner()` cron job.
    Ensure they handle edge cases (deleted records, missing companies) gracefully.
