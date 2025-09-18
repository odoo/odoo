# CLAUDE.md

## Overview
Odoo 19.0 addons repository for Agromarin ERP: 40+ custom modules for accounting, HR, inventory, manufacturing, and Mexican localization (CFDI, EDI, payroll).

## Business Context

### Mexican Localization & Agricultural Domain
- **CFDI/EDI**: Mexican tax receipt generation and compliance
- **Payroll**: Mexican tax calculations and payroll processing
- **Agricultural**: Crop management, harvest tracking, GPS integration, seasonal planning

### Branch Context
**Development Branch (19.0-marin):** Active development, refactoring allowed, no backward compatibility constraints
**Production Branch:** Backward compatibility REQUIRED, only bug fixes, migration scripts for data model changes

## Standard Workflow
1. Think through problem → read relevant files
2. Plan using **TodoWrite tool** (session tracking) + **todo.md** (persistence)
3. Check in for plan verification
4. Work on todos, marking complete in both places
5. High-level explanations at each step
6. **Simplicity first**: minimal code changes, avoid massive complex changes
7. Add review section to todo.md

## Technology Stack
- **Odoo**: 19.0 | **Python**: 3.12+ | **Database**: PostgreSQL 18 + PostGIS 3.7
- **Tools**: pylint, eslint, black, prettier, Odoo testing framework

### Repository Structure
```
agromarin-addons/
├── marin/              # Main meta-module
├── account_*/          # Accounting & Finance
├── hr_*/               # HR & Payroll
├── stock_*/            # Inventory & Manufacturing
├── l10n_mx_*/          # Mexican localization
├── geoengine/          # Geospatial core
└── claude-todo/        # Task planning (not an Odoo module)
```

### Module Structure
```
addon_name/
├── __manifest__.py  # Module definition
├── models/          # Data models
├── views/           # XML views
├── security/        # Access rights
├── tests/           # Unit tests
└── i18n/            # Translations
```

## Development Commands
```bash
# Module operations
./odoo-bin -u module_name -d db_name                    # Install/update
./odoo-bin -u all -d db_name --addons-path=/path        # Update all
./odoo-bin scaffold module_name /path/to/addons         # Create scaffold

# Testing & debugging
./odoo-bin -u module_name -d db_name --test-enable      # Run tests
./odoo-bin -u module_name -d db_name --test-enable --log-level=test  # With coverage
./odoo-bin -d db_name --dev=all                         # Debug mode
./odoo-bin shell -d db_name                             # Shell access

# Maintenance
./odoo-bin -u module_name -d db_name --stop-after-init  # Migrate data
```

## Coding Standards

### Language & Quality
- **English only**: All code, comments, docstrings, variable names
- **Mandatory docstrings**: Every method and class
- **PEP 8 compliance**, meaningful names, type hints, input validation

### Commit Messages (OCA Format)
Format: `[TAG] module: description`
Tags: **IMP** (improvement), **FIX** (bug fix), **ADD** (new feature), **REF** (refactor)
Max 80 chars/line

*Note: Claude Code auto-appends attribution to commits it creates*

### Odoo 19.0 Quick Reference
- **Models**: `_compute_display_name()`, `@api.depends_context`, `_rec_names_search()`
- **XML**: Remove `/** @odoo-module **/` headers, no `owl="1"` attributes
- **Indexes**: Declarative `models.Index()` class attributes, not `_auto_init()`
- **Hooks**: `post_init_hook(env)` signature, not `(cr, registry)`

## ⚠️ DEPRECATED PATTERNS - DO NOT USE

**CRITICAL**: Claude's training data contains deprecated Odoo patterns from v17/18. This section lists what NOT to use.

### XML Views - Odoo 19.0 Patterns

| ❌ Deprecated (Odoo 17/18) | ✅ Modern (Odoo 19.0) |
|---------------------|------------------------|
| `<tree>` | `<list>` |
| `attrs="{'invisible': [('state', '=', 'draft')]}"` | `invisible="state == 'draft'"` |
| `<div class="oe_chatter">...</div>` | `<chatter />` |
| `groups_id` (in menus) | `group_ids` |
| `owl="1"` attribute | No attribute needed |
| `<group expand="0" string="...">` (search views) | `<group>` (no expand/string) |

**Expression Syntax Examples:**
```xml
<!-- ❌ OLD: Complex attrs with domain syntax -->
<field name="date" attrs="{'invisible': [('state', 'in', ['draft', 'cancel'])], 'readonly': [('locked', '=', True)]}"/>
<field name="amount" attrs="{'invisible': ['|', ('state', '=', 'draft'), ('amount', '=', 0)]}"/>

<!-- ✅ NEW: Direct Python-like expressions -->
<field name="date" invisible="state in ['draft', 'cancel']" readonly="locked"/>
<field name="amount" invisible="state == 'draft' or amount == 0"/>
```

### Python Models - Odoo 19.0 Patterns

| ❌ Deprecated (Odoo 17/18) | ✅ Modern (Odoo 19.0) |
|---------------------|------------------------|
| `name_get()` | `@api.depends` + `_compute_display_name()` |
| `name_search()` | `_rec_names_search()` |
| `self._cr` | `self.env.cr` |
| `self._uid` | `self.env.uid` |
| `_sql_constraints = [...]` | `models.UniqueIndex()` or `models.Constraint()` |
| `tools.create_index(..., index_type="gist")` | `tools.create_index(..., method="gist")` |
| Manual `_auto_init()` indexes | Declarative `models.Index()` class attributes |
| `post_init_hook(cr, registry)` | `post_init_hook(env)` |

**Display Name Pattern:**
```python
# ✅ Odoo 19.0
@api.depends('name', 'code')
def _compute_display_name(self):
    for record in self:
        record.display_name = f"{record.name} - {record.code}"
```

**Declarative Indexes and Constraints:**
```python
class MyModel(models.Model):
    _name = 'my.model'

    code = fields.Char(required=True)
    state_id = fields.Many2one('res.country.state')
    event_id = fields.Char()  # Nullable

    # Composite index - MUST be a STRING, not a tuple!
    _state_owner_idx = models.Index("(state, request_owner_id)")

    # UNIQUE CONSTRAINT (SQL: ALTER TABLE ADD CONSTRAINT ... UNIQUE)
    # Use for simple unique constraints without partial indexes
    _code_state_uniq = models.Constraint(
        'unique(code, state_id)',
        'Code must be unique per state!'
    )

    # UNIQUE INDEX (SQL: CREATE UNIQUE INDEX)
    # Use for partial unique indexes or when you need index-specific features
    _event_id_uniq = models.UniqueIndex(
        '(state_id, event_id) WHERE event_id IS NOT NULL',
        'Event ID must be unique per state!'
    )
```

**When to use which:**
- **`models.Index('(field1, field2)')`** → Regular composite indexes (string with SQL expression)
- **`models.Constraint('unique(...)')`** → Simple unique constraints (most common)
- **`models.UniqueIndex('...')`** → Partial indexes with WHERE clause or when you need PostgreSQL index features

**⚠️ GeoEngine Fields:** Don't create GIST indexes manually - `GeoField` handles this automatically in `update_db_column()`

### Relational Fields - Command Class (Odoo 19.0)

```xml
<!-- ❌ OLD: Cryptic tuple syntax -->
<field name="groups_id" eval="[(4, ref('base.group_user'))]"/>
<field name="line_ids" eval="[(0, 0, {'name': 'Line 1'})]"/>
<field name="line_ids" eval="[(6, 0, [id1, id2])]"/>

<!-- ✅ NEW: Command class (clear and explicit) -->
<field name="group_ids" eval="[Command.link(ref('base.group_user'))]"/>
<field name="line_ids" eval="[Command.create({'name': 'Line 1'})]"/>
<field name="line_ids" eval="[Command.set([id1, id2])]"/>
```

**Command Reference:**
- `Command.create({values})` - Create new record
- `Command.update(id, {values})` - Update existing
- `Command.delete(id)` - Delete (One2many)
- `Command.link(id)` - Add link (Many2many)
- `Command.unlink(id)` - Remove link (Many2many)
- `Command.clear()` - Remove all
- `Command.set([ids])` - Replace all with IDs

### Computed Fields vs Onchange - The Golden Rule

**Use Computed Fields (`@api.depends`) when:**
- ✅ Business logic must work everywhere (UI, API, imports, cron jobs)
- ✅ Calculating values that depend on other fields (totals, taxes, derived values)
- ✅ Setting defaults based on related records (fiscal position from partner)
- ✅ Ensuring data consistency across all record creation methods
- ✅ Need to search/filter on computed values (`store=True`)

**Use Onchange (`@api.onchange`) when:**
- ✅ Showing UI warnings or validation messages (`return {'warning': {...}}`)
- ✅ Setting UI state flags (show_update_pricelist, show_name_warning, etc.)
- ✅ Providing real-time feedback before saving
- ✅ The logic is purely UI convenience with no business meaning

**The Golden Rule:**
> **If the logic ensures data integrity or enforces business rules** → Use computed fields with `@api.depends`
>
> **If the logic provides UI convenience without enforcing rules** → Use `@api.onchange`
>
> Think: Would you expect this logic to apply when importing 10,000 records from a CSV? If yes, use computed fields. If no, use onchange.

**Example - Wrong Pattern:**
```python
# ❌ WRONG: @api.onchange for business logic (only works in UI!)
class AccountMove(models.Model):
    partner_id = fields.Many2one('res.partner')
    fiscal_position_id = fields.Many2one('account.fiscal.position')

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """WRONG: Doesn't work for API, imports, or scheduled actions"""
        if self.partner_id:
            self.fiscal_position_id = self.partner_id.fiscal_position_id
```

**Example - Correct Pattern:**
```python
# ✅ CORRECT: Computed field (works everywhere!)
class AccountMove(models.Model):
    partner_id = fields.Many2one('res.partner')
    fiscal_position_id = fields.Many2one(
        'account.fiscal.position',
        compute='_compute_fiscal_position_id',
        store=True,          # Persists to DB, enables search/filter
        readonly=False,      # Allows manual user override
        precompute=True,     # Computes before DB insertion
    )

    @api.depends('partner_id', 'partner_shipping_id', 'company_id')
    def _compute_fiscal_position_id(self):
        """Works everywhere: UI, API, imports, scheduled actions, etc."""
        for move in self:
            # Only update if not manually set by user
            if not move.fiscal_position_id or move._origin.partner_id != move.partner_id:
                move.fiscal_position_id = move.partner_id.fiscal_position_id
```

**Key Computed Field Attributes:**

| Attribute | Purpose | When to Use |
|-----------|---------|-------------|
| `compute='_compute_method'` | Method that calculates value | Always for computed fields |
| `store=True` | Persists value to database | When you need to search/filter |
| `readonly=False` | Allows manual user override | When users can edit computed values |
| `precompute=True` | Computes before DB insertion | When value needed before save |
| `inverse='_inverse_method'` | Bidirectional computation | When field can be both computed and set |

**Common Pitfalls:**

**Pitfall 1: Missing Nested Dependencies**
```python
# ❌ WRONG - Missing nested dependencies
@api.depends('partner_id')
def _compute_tax_rate(self):
    # If partner_id.country_id changes, this won't recompute!
    record.tax_rate = record.partner_id.country_id.tax_rate

# ✅ CORRECT - Include full dependency chain
@api.depends('partner_id', 'partner_id.country_id', 'partner_id.country_id.tax_rate')
def _compute_tax_rate(self):
    record.tax_rate = record.partner_id.country_id.tax_rate
```

**Pitfall 2: Always Overwriting User Input**
```python
# ❌ WRONG - Always overwrites, even if user manually set it
@api.depends('partner_id')
def _compute_fiscal_position(self):
    for record in self:
        record.fiscal_position_id = record.partner_id.fiscal_position_id

# ✅ CORRECT - Check if field was manually set
@api.depends('partner_id')
def _compute_fiscal_position(self):
    for record in self:
        # Only set if not manually overridden or partner changed
        if not record.fiscal_position_id or record._origin.partner_id != record.partner_id:
            record.fiscal_position_id = record.partner_id.fiscal_position_id
```

**Pitfall 3: Long Dependency Chains**
```python
# ❌ AVOID - Creates performance issues
field_a = fields.Char(compute='_compute_a', store=True)
field_b = fields.Char(compute='_compute_b', store=True)  # Depends on field_a
field_c = fields.Char(compute='_compute_c', store=True)  # Depends on field_b

# ✅ BETTER - Flatten dependencies when possible
@api.depends('name')
def _compute_fields(self):
    for record in self:
        field_a = record.name.upper()
        record.field_a = field_a
        record.field_b = f"B: {field_a}"
        record.field_c = f"C: B: {field_a}"
```

**Real Examples from Odoo 19.0 Core:**

```python
# From account/models/account_move.py (lines 454-457, 1022-1036)
# Computed Field Pattern
fiscal_position_id = fields.Many2one(
    'account.fiscal.position',
    compute='_compute_fiscal_position_id',
    store=True,
    readonly=False,
    precompute=True,
)

@api.depends('partner_id', 'partner_shipping_id', 'company_id', 'move_type')
def _compute_fiscal_position_id(self):
    for move in self:
        # Business logic here...
        move.fiscal_position_id = self.env['account.fiscal.position']._get_fiscal_position(...)

# From sale/models/sale_order.py (lines 1375-1384)
# Onchange Pattern - UI helper only
@api.onchange('fiscal_position_id')
def _onchange_fpos_id_show_update_fpos(self):
    """UI helper: Shows button to update taxes when fiscal position changes"""
    if self.line_ids and self.fiscal_position_id != self._origin.fiscal_position_id:
        self.show_update_fpos = True  # UI flag, not business data
```

### When Claude Uses Deprecated Code

**If Claude generates deprecated code:**
1. Stop immediately and point to this section
2. Add the specific pattern here if not already listed
3. Request Claude regenerate using Odoo 19.0 syntax
4. This section should GROW over time as you encounter new patterns

## ⚠️ CRITICAL: XPath in View Inheritance

**MANDATORY**: When inheriting XML views, Claude MUST read the actual parent view file first. NEVER assume or guess XPath locations.

### XPath Hallucination Problem
Claude often hallucinates view structure based on training data, creating XPaths to elements that don't exist.

### Required Workflow
1. **READ** parent view file with Read tool
2. **FIND** exact element in actual structure
3. **VERIFY** XPath targets existing element
4. **USE** specific locators (prefer `name` attributes)

```xml
<!-- ✅ GOOD: Specific field name -->
<xpath expr="//field[@name='partner_id']" position="after">
    <field name="custom_field"/>
</xpath>

<!-- ✅ GOOD: Named group -->
<xpath expr="//group[@name='sale_info']" position="inside">
    <field name="custom_field"/>
</xpath>

<!-- ❌ BAD: Generic path (breaks easily) -->
<xpath expr="//sheet/group" position="after">
    <group><field name="custom_field"/></group>
</xpath>
```

### Common XPath Patterns
```xml
<!-- Modify field attributes -->
<xpath expr="//field[@name='existing']" position="attributes">
    <attribute name="required">True</attribute>
    <attribute name="invisible">state == 'draft'</attribute>
</xpath>

<!-- Add to notebook -->
<xpath expr="//notebook" position="inside">
    <page string="Custom" name="custom_page">
        <group><field name="custom_field"/></group>
    </page>
</xpath>

<!-- Add after button -->
<xpath expr="//button[@name='action_confirm']" position="after">
    <button name="action_custom" string="Custom" type="object"/>
</xpath>
```

**Checklist Before Writing View Inheritance:**
- [ ] Read parent view file with Read tool
- [ ] Verified target element exists in actual file
- [ ] XPath references specific attribute (name, string)
- [ ] Using `position="attributes"` where appropriate

**If you skip reading the file first, you WILL create broken XPaths!**

## Task Management & Branching

### Task Planning
- **TodoWrite tool**: Real-time session tracking
- **todo.md file**: Persistent documentation across sessions
- Keep both synchronized

### Task ID Requirements
Every task needs a **Task ID** (Odoo ERP project task database record ID, e.g., #9169)

**Workflow:**
1. Request/extract Task ID before starting
2. Check/create `/claude-todo/<TASK_ID>.md`
3. Document scope, assumptions, approach

**Why Task IDs Matter:**
- Traceability between code changes and business requirements
- Project management and progress tracking
- Proper documentation and context
- Future Odoo GitHub API integration

### Branch Naming
Format: `<ODOO_VERSION>-t<TASK_ID>-<GITHUB_USERNAME>`
Example: `19.0-t9169-suniagajose`

## Quick Reference Checklist

Before starting development:
- [ ] Task ID obtained (Odoo project task record ID)
- [ ] Planning document in `/claude-todo/<TASK_ID>.md`
- [ ] Feature branch: `19.0-t<TASK_ID>-<username>`
- [ ] TodoWrite + todo.md plan created
- [ ] English-only code + comprehensive docstrings
- [ ] Tests updated (target >80% coverage)
- [ ] OCA commit format: `[TAG] module: description`
- [ ] Odoo 19.0 conventions verified:
  - Use `<list>` not `<tree>`
  - Use `<chatter />` not verbose chatter
  - Use `invisible="state == 'draft'"` not attrs
  - Use `_compute_display_name()` not name_get()
  - Use `models.Index()` not `_auto_init()`
  - Use `post_init_hook(env)` not `(cr, registry)`

## Code Examples

### Model Example
```python
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class AgriculturalProduct(models.Model):
    """Agricultural product management for farming operations."""

    _name = 'agricultural.product'
    _description = 'Agricultural Product'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Product Name', required=True, tracking=True)
    crop_type = fields.Selection([
        ('grain', 'Grain'),
        ('vegetable', 'Vegetable'),
        ('fruit', 'Fruit'),
    ], string='Crop Type', required=True)
    harvest_date = fields.Date(string='Expected Harvest Date')

    @api.constrains('harvest_date')
    def _check_harvest_date(self):
        """Validate harvest date is not in the past."""
        for record in self:
            if record.harvest_date and record.harvest_date < fields.Date.today():
                raise ValidationError("Harvest date cannot be in the past.")

    @api.depends('name', 'crop_type')
    def _compute_display_name(self):
        """Compute display name combining name and crop type."""
        for record in self:
            record.display_name = f"{record.name} ({record.crop_type})"
```

### Test Example
```python
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

class TestAgriculturalProduct(TransactionCase):
    """Test agricultural product functionality."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.ProductModel = self.env['agricultural.product']

    def test_create_agricultural_product(self):
        """Test creating an agricultural product."""
        product = self.ProductModel.create({
            'name': 'Test Corn',
            'crop_type': 'grain',
            'harvest_date': '2024-09-15',
        })
        self.assertEqual(product.name, 'Test Corn')
        self.assertEqual(product.crop_type, 'grain')

    def test_harvest_date_validation(self):
        """Test harvest date validation."""
        with self.assertRaises(ValidationError):
            self.ProductModel.create({
                'name': 'Test Corn',
                'crop_type': 'grain',
                'harvest_date': '2020-01-01',  # Past date
            })
```

### Testing Coverage Guidelines
- **Unit Tests**: Cover all business logic methods, computed fields, and constraints
- **Integration Tests**: Cover critical workflows spanning multiple models
- **Coverage Target**: Aim for >80% code coverage on custom modules
- **Always Test**: Edge cases, error conditions, and constraint validations
- **Test Data**: Use TransactionCase for database-dependent tests

## Migration Scripts

**Required when:**
- Adding/removing required fields to existing models with data
- Changing field types (Char → Selection, Integer → Float)
- Renaming models or fields
- Moving data between modules
- Complex data transformations or computations

**Not required when:**
- Adding optional fields (Odoo auto-creates columns with NULL)
- New modules being installed fresh
- Changes only to views, menus, or security rules
- Adding/removing Many2many relationships (handled via relation tables)
- Development databases (can drop and recreate)

## External Documentation
- [Odoo 19.0 Developer Docs](https://www.odoo.com/documentation/19.0/developer.html)
- [Claude Code Docs](https://docs.anthropic.com/claude/docs/claude-code)
- [OCA Guidelines](https://github.com/OCA/odoo-community.org/blob/master/website/Contribution/CONTRIBUTING.rst)
