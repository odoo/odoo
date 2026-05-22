# View Definition Pattern

**Purpose:** Define the user interface for a model using XML records stored in `ir.ui.view`. Views are declarative: they describe layout and field placement; the web client renders them. Each view type (form, list, kanban, graph, pivot, calendar) has its own root element and conventions.

**Source:** `addons/sale/views/sale_order_views.xml`, `addons/account/models/account_move.py` (domain on fields)

---

## When to Use

- Presenting a model's data to users in the backend or portal
- Inheriting and extending an existing view from another addon
- Defining search filters, group-by options, and default views

---

## Anatomy of a View Record

```xml
<!-- Every view is an ir.ui.view record -->
<record id="view_unique_xmlid" model="ir.ui.view">
    <field name="name">model.view_type</field>        <!-- internal name -->
    <field name="model">sale.order</field>             <!-- model it targets -->
    <field name="arch" type="xml">
        <!-- root element determines view type -->
        <form>...</form>
    </field>
</record>
```

---

## Form View

```xml
<!-- addons/sale/views/sale_order_views.xml (line 252+) -->
<record id="view_order_form" model="ir.ui.view">
    <field name="name">sale.order.form</field>
    <field name="model">sale.order</field>
    <field name="arch" type="xml">
        <form string="Sales Order" class="o_sale_order">

            <!-- Status bar: workflow buttons + state pill -->
            <header>
                <button name="action_confirm" string="Confirm" type="object"
                        class="btn-primary" invisible="state != 'draft'"/>
                <field name="state" widget="statusbar"
                       statusbar_visible="draft,sent,sale"/>
            </header>

            <sheet>
                <!-- Smart buttons row (linked record counts) -->
                <div class="oe_button_box" name="button_box">
                    <button type="object" name="action_view_invoice"
                            class="oe_stat_button" icon="fa-pencil-square-o">
                        <field name="invoice_count" widget="statinfo"
                               string="Invoices"/>
                    </button>
                </div>

                <!-- Two-column header groups -->
                <group name="sale_header">
                    <group name="partner_details">
                        <field name="partner_id" options="{'no_create': True}"/>
                        <field name="partner_invoice_id"/>
                    </group>
                    <group name="order_details">
                        <field name="validity_date"
                               invisible="state == 'sale'"
                               readonly="state in ['cancel', 'sale']"/>
                        <field name="currency_id" invisible="1"/>
                    </group>
                </group>

                <!-- Tab pages -->
                <notebook>
                    <page string="Order Lines" name="order_lines">
                        <field name="order_line" widget="one2many_list">
                            <list editable="bottom">
                                <field name="product_id"/>
                                <field name="product_uom_qty"/>
                                <field name="price_unit"/>
                                <field name="price_subtotal" widget="monetary"/>
                            </list>
                        </field>
                    </page>
                    <page string="Other Info" name="other_info">
                        <group>
                            <field name="note" widget="html"/>
                        </group>
                    </page>
                </notebook>
            </sheet>

            <!-- Chatter (mail thread) -->
            <chatter/>
        </form>
    </field>
</record>
```

---

## List View

```xml
<!-- addons/sale/views/sale_order_views.xml (line 111+) -->
<record id="sale_order_tree" model="ir.ui.view">
    <field name="name">sale.order.list</field>
    <field name="model">sale.order</field>
    <field name="arch" type="xml">
        <list class="o_sale_order"
              decoration-muted="state == 'cancel'"
              decoration-success="state == 'sale'">
            <!-- Invisible columns still fetched for decoration evaluation -->
            <field name="currency_id" column_invisible="True"/>
            <field name="name" string="Order"/>
            <field name="partner_id"/>
            <field name="date_order"/>
            <field name="amount_total" widget="monetary"/>
            <field name="state" widget="badge"
                   decoration-info="state == 'draft'"
                   decoration-success="state == 'sale'"/>
            <!-- optional= makes column hideable by user -->
            <field name="user_id" widget="many2one_avatar_user" optional="show"/>
        </list>
    </field>
</record>
```

---

## Kanban View

```xml
<!-- addons/sale/views/sale_order_views.xml (line 68+) -->
<record id="view_sale_order_kanban" model="ir.ui.view">
    <field name="name">sale.order.kanban</field>
    <field name="model">sale.order</field>
    <field name="arch" type="xml">
        <kanban class="o_kanban_mobile" sample="1" quick_create="false">
            <field name="currency_id"/>
            <progressbar field="activity_state"
                colors='{"planned": "success", "today": "warning", "overdue": "danger"}'/>
            <templates>
                <t t-name="card">
                    <field name="partner_id" class="fw-bolder fs-5"/>
                    <field name="amount_total" widget="monetary"/>
                    <field name="state" widget="label_selection"/>
                </t>
            </templates>
        </kanban>
    </field>
</record>
```

---

## Graph / Pivot / Calendar Views

```xml
<!-- Graph -->
<record id="view_sale_order_graph" model="ir.ui.view">
    <field name="model">sale.order</field>
    <field name="arch" type="xml">
        <graph string="Sales Orders" sample="1">
            <field name="partner_id"/>
            <field name="amount_total" type="measure"/>
        </graph>
    </field>
</record>

<!-- Pivot -->
<record id="view_sale_order_pivot" model="ir.ui.view">
    <field name="model">sale.order</field>
    <field name="arch" type="xml">
        <pivot string="Sales Orders" sample="1">
            <field name="date_order" type="row"/>
            <field name="amount_total" type="measure"/>
        </pivot>
    </field>
</record>

<!-- Calendar -->
<record id="view_sale_order_calendar" model="ir.ui.view">
    <field name="model">sale.order</field>
    <field name="arch" type="xml">
        <calendar string="Sales Orders" date_start="activity_date_deadline"
                  color="state" mode="month" event_limit="5" quick_create="0">
            <field name="partner_id" avatar_field="avatar_128"/>
            <field name="amount_total" widget="monetary"/>
        </calendar>
    </field>
</record>
```

---

## View Inheritance

```xml
<!-- Extend an existing view without copying it -->
<record id="view_order_tree_custom" model="ir.ui.view">
    <field name="model">sale.order</field>
    <field name="inherit_id" ref="sale.sale_order_tree"/>   <!-- XMLID of parent -->
    <field name="arch" type="xml">
        <!-- XPath or shorthand field selector -->
        <field name="date_order" position="after">
            <field name="commitment_date" optional="hide"/>
        </field>
        <!-- Or use XPath for precise targeting -->
        <xpath expr="//list" position="attributes">
            <attribute name="editable">top</attribute>
        </xpath>
    </field>
</record>
```

---

## Common Field Widgets

| Widget | Field type | Use |
|--------|-----------|-----|
| `monetary` | Float | Amount with currency symbol |
| `statusbar` | Selection | Workflow progress bar in form header |
| `badge` | Selection | Colored pill badge in lists |
| `many2one_avatar_user` | Many2one | User with avatar thumbnail |
| `one2many_list` | One2many | Inline editable table |
| `html` | Html | Rich-text editor |
| `kanban_activity` | Many2many | Activity indicator dot |
| `statinfo` | Integer/Float | Smart button counter |

---

## Common Pitfalls

- **`invisible` vs `column_invisible`:** Use `column_invisible` on list-view fields to hide the column entirely (including header). `invisible` hides the cell value per row but keeps the column.
- **`decoration-*` attributes** evaluate Python expressions and require all referenced fields to be present in the view (even as `column_invisible`).
- **`position="attributes"` on `<list>`** is the only way to modify list-level attributes (editability, default_order) via inheritance.
- **`noupdate="1"` on `<odoo>`** in data files prevents re-applying XML on module upgrade — use for demo data, not for view definitions.
- **View priority:** Higher `<field name="priority">` integer wins when multiple views of the same type exist for the same model.

---

## Related Patterns

- [module-addon-structure-pattern.md](./module-addon-structure-pattern.md) — where view files live in the addon
- [security-model-pattern.md](./security-model-pattern.md) — `groups=` attribute on views/fields
- [domain-filter-pattern.md](./domain-filter-pattern.md) — `domain=` on Many2one and search views
