# Security Model Pattern

**Purpose:** Control who can read, write, create, or delete records using two complementary mechanisms: model-level ACL (coarse-grained, per group) and record rules (fine-grained, per row via domain filters). Both are declared as XML/CSV data records, not Python code.

**Source:** `addons/website_event_track/security/ir.model.access.csv`, `addons/sale/security/ir_rules.xml`, `addons/hr_attendance/security/hr_attendance_overtime_ruleset_security.xml`, `addons/account/models/account_journal.py` (groups= attribute)

---

## When to Use

- Granting a user group access to a new model (`ir.model.access.csv`)
- Restricting record visibility per company, user, or team (`ir.rule`)
- Hiding UI fields or buttons from groups without permission (`groups=` in views)
- Defining custom user groups (`res.groups` records)

---

## Layer 1 — Model-Level ACL (ir.model.access.csv)

One row per group/model combination. All four CRUD permissions are independent.

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink

# Public and portal: read-only
access_event_track_public,event.track,model_event_track,base.group_public,1,0,0,0
access_event_track_portal,event.track,model_event_track,base.group_portal,1,0,0,0

# Internal users: read-only
access_event_track_employee,event.track,model_event_track,base.group_user,1,0,0,0

# Event users: read + write + create (no delete)
access_event_track_user,event.track.user,model_event_track,event.group_event_user,1,1,1,0

# Event managers: full CRUD
access_event_track_manager,event.track.manager,model_event_track,event.group_event_manager,1,1,1,1
```

Column reference:

| Column | Value | Meaning |
|--------|-------|---------|
| `id` | XML ID string | Unique identifier for this access rule |
| `name` | human label | Displayed in Settings > Technical > ACL |
| `model_id:id` | `model_<model_name_underscored>` | Auto-generated XML ID for the model |
| `group_id:id` | `addon.group_xmlid` | Group that receives this permission |
| `perm_read` | 0 / 1 | SELECT |
| `perm_write` | 0 / 1 | UPDATE |
| `perm_create` | 0 / 1 | INSERT |
| `perm_unlink` | 0 / 1 | DELETE |

---

## Layer 2 — Record Rules (ir.rule)

Domain-based row-level filters applied after ACL. A user only sees records that match at least one applicable rule.

### Multi-Company Rule (most common pattern)

```xml
<!-- addons/sale/security/ir_rules.xml -->
<odoo noupdate="1">
    <record id="sale_order_comp_rule" model="ir.rule">
        <field name="name">Sales Order multi-company</field>
        <field name="model_id" ref="model_sale_order"/>
        <!-- company_ids is a magic variable: set of companies the user belongs to -->
        <field name="domain_force">[('company_id', 'in', company_ids)]</field>
        <!-- No <groups>: applies globally to all users -->
    </record>
</odoo>
```

### Portal Access Rule (filter by partner)

```xml
<record id="sale_order_rule_portal" model="ir.rule">
    <field name="name">Portal Personal Quotations/Sales Orders</field>
    <field name="model_id" ref="sale.model_sale_order"/>
    <!-- user is a magic variable: the current res.users record -->
    <field name="domain_force">[('partner_id','child_of',[user.commercial_partner_id.id])]</field>
    <field name="groups" eval="[(4, ref('base.group_portal'))]"/>
    <field name="perm_read" eval="True"/>
    <field name="perm_write" eval="True"/>
    <field name="perm_unlink" eval="True"/>
</record>
```

### Read-Only Global Rule

```xml
<!-- addons/hr_attendance/security/hr_attendance_overtime_ruleset_security.xml -->
<record id="hr_attendance_overtime_ruleset_rule" model="ir.rule">
    <field name="name">Attendance Overtime Ruleset</field>
    <field name="model_id" ref="model_hr_attendance_overtime_ruleset"/>
    <field name="global" eval="True"/>   <!-- applies to all groups -->
    <field name="domain_force">[('company_id', 'in', company_ids + [False])]</field>
    <field name="perm_read" eval="True"/>
    <field name="perm_create" eval="False"/>
    <field name="perm_write" eval="False"/>
    <field name="perm_unlink" eval="False"/>
</record>

<!-- Managers get full CRUD via a separate rule -->
<record id="hr_attendance_overtime_ruleset_rule_manager" model="ir.rule">
    <field name="model_id" ref="model_hr_attendance_overtime_ruleset"/>
    <field name="global" eval="[Command.link(ref('hr_attendance.group_hr_attendance_manager'))]"/>
    <field name="domain_force">[('company_id', 'in', company_ids + [False])]</field>
    <field name="perm_read" eval="True"/>
    <field name="perm_create" eval="True"/>
    <field name="perm_write" eval="True"/>
    <field name="perm_unlink" eval="True"/>
</record>
```

---

## Layer 3 — Group Definitions (res.groups)

```xml
<!-- Typically in security/security.xml or views/res_groups.xml -->
<record id="group_event_user" model="res.groups">
    <field name="name">User</field>
    <field name="category_id" ref="base.module_category_services_events"/>
    <field name="implied_ids" eval="[(4, ref('base.group_user'))]"/>
</record>

<record id="group_event_manager" model="res.groups">
    <field name="name">Administrator</field>
    <field name="category_id" ref="base.module_category_services_events"/>
    <field name="implied_ids" eval="[(4, ref('group_event_user'))]"/>
</record>
```

---

## Layer 4 — Field and View-Level Restrictions

```xml
<!-- Hide a field from non-managers in the form view -->
<field name="cost_price" groups="account.group_account_manager"/>

<!-- Hide an entire page from non-HR users -->
<page string="Payroll" groups="hr_payroll.group_hr_payroll_user">
    ...
</page>

<!-- Hide a menu item -->
<menuitem id="menu_accounting" groups="account.group_account_user"/>
```

```python
# On the field definition itself (always hidden from non-members)
# addons/account/models/account_journal.py
company_id = fields.Many2one(
    'res.company',
    groups='base.group_multi_company',  # only visible when multi-company is active
)
```

---

## Magic Variables in domain_force

| Variable | Type | Value |
|----------|------|-------|
| `user` | `res.users` record | The currently authenticated user |
| `company_id` | int | Active company ID |
| `company_ids` | list of int | All companies the user has access to |
| `time` | Python `time` module | For date-based rules |

---

## Common Pitfalls

- **ACL is checked before record rules.** If a group has no ACL entry for a model, record rules are never evaluated — the user is blocked at the model level.
- **`noupdate="1"` is essential for record rules** — without it, customizations made by administrators via the UI are overwritten on every module upgrade.
- **`global` vs `groups` on ir.rule:** A rule with `global=True` applies to all users as an AND condition. A rule scoped to a group applies only to members of that group as an OR across applicable rules.
- **Empty domain `[]` means no restriction** (all records visible) — not "no records visible".
- **`sudo()` bypasses record rules** but not field-level `groups=` in views (those are UI-only anyway). Use `.with_user(user_id)` to test rules programmatically.
- **Model XML ID format:** The auto-generated XML ID for `my.model` is `model_my_model` (dots replaced with underscores).

---

## Related Patterns

- [orm-model-pattern.md](./orm-model-pattern.md) — `_check_company_auto` on models
- [module-addon-structure-pattern.md](./module-addon-structure-pattern.md) — `security/` directory placement in manifest
- [domain-filter-pattern.md](./domain-filter-pattern.md) — domain syntax used in `domain_force`
- [test-case-pattern.md](./test-case-pattern.md) — testing access errors with `assertRaises(AccessError)`
