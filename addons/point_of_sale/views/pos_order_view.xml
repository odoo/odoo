<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_pos_pos_form" model="ir.ui.view">
        <field name="name">pos.order.form</field>
        <field name="model">pos.order</field>
        <field name="arch" type="xml">
            <form string="Point of Sale Orders" create="0">
                <header>
                    <button name="%(action_pos_payment)d" string="Payment" class="oe_highlight" type="action" states="draft" />
                    <button name="action_pos_order_invoice" string="Invoice" type="object"
                            attrs="{'invisible': [('state','!=','paid')]}"/>
                    <button name="refund" string="Return Products" type="object"
                        attrs="{'invisible':['|', ('state','=','draft'), ('has_refundable_lines', '=', False)]}"/>
                    <field name="state" widget="statusbar" statusbar_visible="draft,paid,done" />
                    <field name="has_refundable_lines" invisible="1" />
                    <field name="refunded_orders_count" invisible="1" />
                </header>
                <sheet>
                <field name="failed_pickings" invisible="1"/>
                <field name="is_refunded" invisible="1"/>
                <div class="oe_button_box" name="button_box">
                    <button name="action_stock_picking"
                        type="object"
                        class="oe_stat_button"
                        icon="fa-truck"
                        attrs="{'invisible':[('picking_count', '=', 0)]}">
                        <field name="picking_count" widget="statinfo" string="Pickings" attrs="{'invisible': [('failed_pickings', '!=', False)]}"/>
                        <field name="picking_count" widget="statinfo" string="Pickings" class="text-danger" attrs="{'invisible': [('failed_pickings', '=', False)]}"/>
                    </button>
                    <button name="action_view_invoice"
                        string="Invoice"
                        type="object"
                        class="oe_stat_button"
                        icon="fa-pencil-square-o"
                        attrs="{'invisible':[('state','!=','invoiced')]}">
                    </button>
                    <button name="action_view_refund_orders"
                        type="object"
                        class="oe_stat_button"
                        icon="fa-undo"
                        attrs="{'invisible':[('is_refunded', '=', False)]}">
                        <field name="refund_orders_count" widget="statinfo" string="Refunds" />
                    </button>
                    <button name="action_view_refunded_orders"
                        type="object"
                        class="oe_stat_button"
                        icon="fa-shopping-cart "
                        attrs="{'invisible':[('refunded_orders_count', '=', 0)]}">
                        <field name="refunded_orders_count" widget="statinfo" string="Refunded Orders" />
                    </button>
                </div>
                <group col="4" colspan="4" name="order_fields">
                    <field name="name"/>
                    <field name="date_order"/>
                    <field name="session_id" />
                    <field string="User" name="user_id"/>
                    <field name="partner_id" context="{'res_partner_search_mode': 'customer'}" attrs="{'readonly': [('state','=','invoiced')]}"/>
                    <field name="fiscal_position_id" options="{'no_create': True}"/>
                </group>
                <notebook colspan="4">
                    <page string="Products" name="products">
                        <field name="lines" colspan="4" nolabel="1">
                            <tree string="Order lines" editable="bottom">
                                <field name="full_product_name"/>
                                <field name="pack_lot_ids" widget="many2many_tags" groups="stock.group_production_lot"/>
                                <field name="qty"/>
                                <field name="customer_note" optional="hide"/>
                                <field name="product_uom_id" string="UoM" groups="uom.group_uom"/>
                                <field name="price_unit" widget="monetary"/>
                                <field name="is_total_cost_computed" invisible="1"/>
                                <field name="total_cost" attrs="{'invisible': [('is_total_cost_computed','=', False)]}" optional="hide" widget="monetary"/>
                                <field name="margin" attrs="{'invisible': [('is_total_cost_computed','=', False)]}" optional="hide" widget="monetary"/>
                                <field name="margin_percent" attrs="{'invisible': [('is_total_cost_computed','=', False)]}" optional="hide" widget="percentage"/>
                                <field name="discount" string="Disc.%"/>
                                <field name="tax_ids_after_fiscal_position" widget="many2many_tags" string="Taxes"/>
                                <field name="tax_ids" widget="many2many_tags" invisible="1"/>
                                <field name="price_subtotal" widget="monetary" force_save="1"/>
                                <field name="price_subtotal_incl" widget="monetary" force_save="1"/>
                                <field name="currency_id" invisible="1"/>
                                <field name="refunded_qty" optional="hide" />
                            </tree>
                            <form string="Order lines">
                                <group col="4">
                                    <field name="full_product_name"/>
                                    <field name="qty"/>
                                    <field name="discount"/>
                                    <field name="price_unit" widget="monetary"/>
                                    <field name="price_subtotal" invisible="1" widget="monetary" force_save="1"/>
                                    <field name="price_subtotal_incl" invisible="1" widget="monetary" force_save="1"/>
                                    <field name="tax_ids_after_fiscal_position" widget="many2many_tags" string="Taxes"/>
                                    <field name="tax_ids" widget="many2many_tags" invisible="1"/>
                                    <field name="pack_lot_ids" widget="many2many_tags" groups="stock.group_production_lot"/>
                                    <field name="notice"/>
                                    <field name="currency_id" invisible="1"/>
                                </group>
                            </form>
                        </field>
                        <group class="oe_subtotal_footer oe_right" colspan="2" name="order_total">
                            <field name="amount_tax"
                                   force_save="1"
                                   widget="monetary"/>
                            <div class="oe_subtotal_footer_separator oe_inline o_td_label">
                                <label for="amount_total" />
                                <button name="button_dummy"
                                    states="draft" string="(update)" class="oe_edit_only oe_link"/>
                            </div>
                            <field name="amount_total"
                                   force_save="1"
                                   nolabel="1"
                                   class="oe_subtotal_footer_separator"
                                   widget="monetary"/>
                            <field name="amount_paid"
                                string="Total Paid (with rounding)"
                                class="oe_subtotal_footer_separator"
                                widget="monetary"
                                attrs="{'invisible': [('amount_paid','=', 'amount_total')]}"/>
                            <label for="margin"/>
                            <div class="text-nowrap">
                                <field name="margin" class="oe_inline" attrs="{'invisible': [('is_total_cost_computed','=', False)]}"/>
                                <span class="oe_inline" attrs="{'invisible': [('is_total_cost_computed','=', False)]}">
                                    (<field name="margin_percent" nolabel="1" class="oe_inline" widget="percentage"/>)
                                </span>
                                <span attrs="{'invisible': [('is_total_cost_computed','=', True)]}">TBD</span>
                            </div>
                            <field name="is_total_cost_computed" invisible="1"/>
                            <field name="currency_id" invisible="1"/>
                        </group>
                        <div class="clearfix"/>
                    </page>
                    <page string="Payments" name="payments">
                        <field name="payment_ids" colspan="4" nolabel="1">
                            <tree string="Payments">
                                <field name="currency_id" invisible="1" />
                                <field name="payment_date"/>
                                <field name="payment_method_id"/>
                                <field name="amount"/>
                            </tree>
                        </field>
                    </page>
                    <page name="extra" string="Extra Info">
                        <group >
                            <group
                                string="Accounting"
                                groups="account.group_account_manager"
                                attrs="{'invisible':['|', ('session_move_id','=', False), ('state', '=', 'invoiced')]}"
                            >
                                <field name="session_move_id" readonly="1" />
                            </group>
                            <group string="Other Information">
                                <field name="pos_reference"/>
                                <field name="company_id" groups="base.group_multi_company"/>
                                <field name="pricelist_id" groups="product.group_product_pricelist"/>
                            </group>
                        </group>
                    </page>
                    <page string="Notes" name="notes">
                        <field name="note"/>
                    </page>
                </notebook>
            </sheet>
            </form>
        </field>
    </record>

    <record model="ir.ui.view" id="view_pos_order_kanban">
        <field name="name">pos.order.kanban</field>
        <field name="model">pos.order</field>
        <field name="arch" type="xml">
            <kanban class="o_kanban_mobile" create="0" sample="1">
                <field name="name"/>
                <field name="partner_id"/>
                <field name="amount_total"/>
                <field name="date_order"/>
                <field name="state"/>
                <field name="pos_reference"/>
                <field name="partner_id"/>
                <field name="currency_id"/>
                <templates>
                    <t t-name="kanban-box">
                        <div t-attf-class="oe_kanban_card oe_kanban_global_click">
                            <div class="o_kanban_record_top">
                                <div class="o_kanban_record_headings">
                                    <strong class="o_kanban_record_title">
                                        <span t-if="record.partner_id.value">
                                            <t t-esc="record.partner_id.value"/>
                                        </span>
                                        <span t-else="">
                                            <t t-esc="record.name.value"/>
                                        </span>
                                    </strong>
                                </div>
                                <strong><field name="amount_total" widget="monetary"/></strong>
                            </div>
                            <div class="row">
                                <div class="col-12">
                                <span><t t-esc="record.pos_reference.value"/></span>
                            </div>
                            </div>
                            <div class="row">
                                <div class="col-8 text-muted">
                                    <span><t t-esc="record.date_order.value"/></span>
                                </div>
                                <div class="col-4">
                                    <span class="float-end text-end">
                                        <field name="state" widget="label_selection" options="{'classes': {'draft': 'default',
                                        'invoiced': 'success', 'cancel': 'danger'}}"/>
                                    </span>
                                </div>
                            </div>
                        </div>
                    </t>
                </templates>
            </kanban>
        </field>
    </record>
    <record model="ir.ui.view" id="view_pos_order_pivot">
        <field name="name">pos.order.pivot</field>
        <field name="model">pos.order</field>
        <field name="arch" type="xml">
            <pivot string="PoS Orders" sample="1">
                <field name="date_order" type="row"/>
                <field name="margin"/>
                <field name="margin_percent" invisible="1"/>
                <field name="amount_total" type="measure"/>
            </pivot>
        </field>
    </record>

    <record id="action_pos_pos_form" model="ir.actions.act_window">
        <field name="name">Orders</field>
        <field name="type">ir.actions.act_window</field>
        <field name="res_model">pos.order</field>
        <field name="view_mode">tree,form,kanban,pivot</field>
        <field name="view_id" eval="False"/>
        <field name="domain">[]</field>
        <field name="help" type="html">
            <p class="o_view_nocontent_empty_folder">
                No orders found
            </p><p>
                To record new orders, start a new session.
            </p>
        </field>
    </record>

    <record id="action_pos_sale_graph" model="ir.actions.act_window">
        <field name="name">Orders</field>
        <field name="type">ir.actions.act_window</field>
        <field name="res_model">pos.order</field>
        <field name="view_mode">graph,tree,form,kanban,pivot</field>
        <field name="domain">[('state', 'not in', ['draft', 'cancel', 'invoiced'])]</field>
        <field name="help" type="html">
            <p class="o_view_nocontent_smiling_face">
                No data yet!
            </p><p>
                Create a new POS order
            </p>
        </field>
    </record>

    <record id="view_pos_order_tree" model="ir.ui.view">
        <field name="name">pos.order.tree</field>
        <field name="model">pos.order</field>
        <field name="arch" type="xml">
            <tree string="POS Orders" create="0" sample="1" decoration-info="state == 'draft'" decoration-muted="state == 'cancel'">
                <field name="currency_id" invisible="1"/>
                <field name="name" decoration-bf="1"/>
                <field name="session_id" />
                <field name="date_order"/>
                <field name="pos_reference"/>
                <field name="partner_id"/>
                <field string="Cashier" name="user_id" widget="many2one_avatar_user"/>
                <field name="amount_total" sum="Amount total" widget="monetary" decoration-bf="1"/>
                <field name="state" widget="badge" decoration-info="state == 'draft'" decoration-success="state not in ('draft','cancel')"/>
            </tree>
        </field>
    </record>
    <record id="view_pos_order_tree_no_session_id" model="ir.ui.view">
        <field name="name">pos.order.tree_no_session_id</field>
        <field name="model">pos.order</field>
        <field name="mode">primary</field>
        <field name="priority">1000</field>
        <field name="inherit_id" ref="point_of_sale.view_pos_order_tree"/>
        <field name="arch" type="xml">
            <xpath expr="//field[@name='session_id']" position="replace"></xpath>
        </field>
    </record>

    <record id="view_pos_order_search" model="ir.ui.view">
        <field name="name">pos.order.search.view</field>
        <field name="model">pos.order</field>
        <field name="arch" type="xml">
            <search string="Point of Sale Orders">
                <field name="name"/>
                <field name="config_id"/>
            </search>
        </field>
    </record>

    <menuitem id="menu_point_ofsale" parent="menu_point_of_sale" action="action_pos_pos_form" sequence="2" groups="group_pos_manager,group_pos_user"/>

    <record id="view_pos_order_line" model="ir.ui.view">
        <field name="name">pos.order.line.tree</field>
        <field name="model">pos.order.line</field>
        <field name="arch" type="xml">
            <tree string="POS Order lines">
                <field name="product_id" readonly="1"/>
                <field name="qty" readonly="1" sum="Total qty"/>
                <field name="discount" readonly="1"/>
                <field name="price_unit" readonly="1" widget="monetary"/>
                <field name="price_subtotal" readonly="1" sum="Sum of subtotals" widget="monetary"/>
                <field name="price_subtotal_incl" readonly="1" sum="Sum of subtotals" widget="monetary"/>
                <field name="create_date" readonly="1"/>
                <field name="currency_id" invisible="1"/>
            </tree>
        </field>
    </record>

    <record id="view_pos_order_line_form" model="ir.ui.view">
        <field name="name">pos.order.line.form</field>
        <field name="model">pos.order.line</field>
        <field name="arch" type="xml">
            <form string="POS Order line">
                <group col="4">
                    <field name="product_id" />
                    <field name="qty" />
                    <field name="discount"/>
                    <field name="price_unit" widget="monetary"/>
                    <field name="create_date" />
                    <field name="currency_id"/>
                </group>
            </form>
        </field>
    </record>

    <record id="action_pos_order_line" model="ir.actions.act_window">
        <field name="name">Sale line</field>
        <field name="type">ir.actions.act_window</field>
        <field name="res_model">pos.order.line</field>
        <field name="view_mode">tree</field>
        <field name="view_id" ref="view_pos_order_line"/>
    </record>

    <record id="action_pos_order_line_form" model="ir.actions.act_window">
        <field name="name">Sale line</field>
        <field name="type">ir.actions.act_window</field>
        <field name="res_model">pos.order.line</field>
        <field name="view_mode">form,tree</field>
        <field name="view_id" ref="view_pos_order_line_form"/>
    </record>

    <record id="action_pos_order_line_day" model="ir.actions.act_window">
        <field name="name">Sale line</field>
        <field name="type">ir.actions.act_window</field>
        <field name="res_model">pos.order.line</field>
        <field name="view_mode">tree</field>
        <field name="view_id" ref="view_pos_order_line"/>
        <field name="domain">[('create_date', '&gt;=', time.strftime('%Y-%m-%d 00:00:00')),('create_date', '&lt;=', time.strftime('%Y-%m-%d 23:59:59'))]</field>
    </record>

    <record id="view_pos_order_tree_all_sales_lines" model="ir.ui.view">
        <field name="name">pos.order.line.all.sales.tree</field>
        <field name="model">pos.order.line</field>
        <field name="arch" type="xml">
            <tree string="POS Orders lines">
                <field name="order_id" />
                <field name="create_date" />
                <field name="product_id" />
                <field name="qty" />
                <field name="price_unit" widget="monetary"/>
                <field name="currency_id" invisible="1"/>
            </tree>
        </field>
    </record>
     <record id="action_pos_all_sales_lines" model="ir.actions.act_window">
        <field name="name">All sales lines</field>
        <field name="type">ir.actions.act_window</field>
        <field name="res_model">pos.order.line</field>
        <field name="view_id" ref="view_pos_order_tree_all_sales_lines" />
    </record>

    <record id="view_pos_order_filter" model="ir.ui.view">
        <field name="name">pos.order.list.select</field>
        <field name="model">pos.order</field>
        <field name="arch" type="xml">
            <search string="Search Sales Order">
                <field name="name"/>
                <field name="pos_reference"/>
                <field name="date_order"/>
                <field name="user_id"/>
                <field name="partner_id"/>
                <field name="session_id"/>
                <filter string="Invoiced" name="invoiced" domain="[('state', '=', 'invoiced')]"/>
                <filter string="Posted" name="posted" domain="[('state', '=', 'done')]"/>
                <separator/>
                <filter string="Order Date" name="order_date" date="date_order"/>
                <group expand="0" string="Group By">
                    <filter string="Session" name="session" domain="[]" context="{'group_by': 'session_id'}"/>
                    <filter string="User" name="user_id" domain="[]" context="{'group_by': 'user_id'}"/>
                    <filter string="Customer" name="customer" domain="[]" context="{'group_by': 'partner_id'}"/>
                    <filter string="Status" name="status" domain="[]" context="{'group_by': 'state'}"/>
                    <filter string="Order Date" name="order_month" domain="[]" context="{'group_by': 'date_order'}"/>
                </group>
            </search>
        </field>
    </record>

    <record id="pos_rounding_form_view_inherited" model="ir.ui.view">
        <field name="name">pos.cash.rounding.form.inherited</field>
        <field name="model">account.cash.rounding</field>
        <field name="inherit_id" ref="account.rounding_form_view"/>
        <field name="arch" type="xml">
            <xpath expr="//div[hasclass('oe_title')]" position="before">
                <div class="o_notification_alert alert alert-warning" role="alert">
                  The Point of Sale only supports the "add a rounding line" rounding strategy.
                </div>
            </xpath>
        </field>
    </record>
</odoo>
