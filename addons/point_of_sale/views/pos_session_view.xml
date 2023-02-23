<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_pos_session_form" model="ir.ui.view">
        <field name="name">pos.session.form.view</field>
        <field name="model">pos.session</field>
        <field name="arch" type="xml">
            <form string="Point of Sale Session" create="0" edit="0">
                <header>
                    <button name="open_frontend_cb" type="object" string="Continue Selling"
                        attrs="{'invisible' : ['|', ('rescue', '=', True), ('state', 'not in', ['opening_control', 'opened'])]}"/>
                    <button id="validate_closing_control" name="action_pos_session_closing_control" type="object" string="Close Session &amp; Post Entries" states="closing_control"
                            attrs="{'invisible': [ '|', '&amp;',('state', '!=', 'closing_control'), ('rescue', '=', False),
                                '&amp;',('state', '=', 'closed'), ('rescue', '=', True)]}"
                    class="oe_highlight"/>
                    <field name="state" widget="statusbar" statusbar_visible="opened,closing_control,closed" nolabel="1" />
                </header>
                <sheet>
                    <field name="failed_pickings" invisible="1"/>
                    <field name="rescue" invisible="1"/>
                    <div class="oe_button_box" name="button_box">
                        <button name="action_view_order"
                            class="oe_stat_button"
                            icon="fa-shopping-basket"
                            type="object">
                            <field name="order_count" widget="statinfo" string="Orders"/>
                        </button>
                        <button class="oe_stat_button" name="action_stock_picking" type="object" icon="fa-truck" attrs="{'invisible':[('picking_count', '=', 0)]}">
                            <field name="picking_count" widget="statinfo" string="Pickings" attrs="{'invisible': [('failed_pickings', '!=', False)]}"/>
                            <field name="picking_count" widget="statinfo" string="Pickings" class="text-danger" attrs="{'invisible': [('failed_pickings', '=', False)]}"/>
                        </button>
                        <button
                            name="action_show_payments_list"
                            type="object"
                            class="oe_stat_button"
                            icon="fa-dollar"
                            >
                            <field name="total_payments_amount" widget="statinfo" string="Payments"/>
                        </button>
                        <button
                            name="show_journal_items"
                            type="object"
                            class="oe_stat_button"
                            icon="fa-bars"
                            string="Journal Items"
                            groups="account.group_account_readonly"
                            >
                        </button>
                        <button
                            name="show_cash_register"
                            type="object"
                            class="oe_stat_button"
                            icon="fa-bars"
                            string="Cash Register"
                            attrs="{'invisible':[('cash_control', '=', False)]}"
                            groups="account.group_account_readonly"
                        />
                    </div>
                    <h1 class="oe_title">
                        <field name="name" attrs="{'invisible': [('name','=','/')]}" class="oe_inline"/>
                    </h1>
                    <group>
                        <field name="cash_control" invisible="1" />
                        <field name="user_id"/>
                        <field name="currency_id" invisible="1"/>
                        <field name="config_id" readonly="1"/>
                        <field name="move_id" readonly="1" groups="account.group_account_readonly" />
                        <field name="start_at" attrs="{'invisible' : [('state', '=', 'opening_control')]}"/>
                        <field name="stop_at" attrs="{'invisible' : [('state', '!=', 'closed')]}"/>
                        <field name="cash_register_balance_start"/>
                        <field name="cash_register_balance_end_real" attrs="{'invisible': [('state', '!=', 'closed')]}"/>
                    </group>
                </sheet>
                <div class="oe_chatter">
                    <field name="activity_ids"/>
                    <field name="message_follower_ids"/>
                    <field name="message_ids"/>
                </div>
            </form>
        </field>
    </record>

    <record id="view_pos_session_tree" model="ir.ui.view">
        <field name="name">pos.session.tree.view</field>
        <field name="model">pos.session</field>
        <field name="arch" type="xml">
            <tree string="Point of Sale Session" create="0" sample="1">
                <field name="name" decoration-bf="1"/>
                <field name="config_id" />
                <field name="user_id" widget="many2one_avatar_user"/>
                <field name="start_at" />
                <field name="stop_at" />
                <field name="state" widget="badge" decoration-info="state in ('opening_control')" decoration-success="state in ('opened', 'closed')" decoration-warning="state == 'closing_control'" />
            </tree>
        </field>
    </record>

    <record model="ir.ui.view" id="view_pos_session_kanban">
        <field name="name">pos.session.kanban</field>
        <field name="model">pos.session</field>
        <field name="arch" type="xml">
            <kanban class="o_kanban_mobile" create="0" sample="1">
                <field name="config_id" />
                <field name="name" />
                <field name="user_id" />
                <field name="start_at" />
                <field name="state" />
                <templates>
                    <t t-name="kanban-box">
                        <div t-attf-class="oe_kanban_card oe_kanban_global_click">
                            <div class="o_kanban_record_top">
                                <div class="o_kanban_record_headings">
                                    <strong class="o_kanban_record_title"><span><field name="config_id"/></span></strong>
                                </div>
                                <field name="state" widget="label_selection" options="{'classes': {'opening_control': 'default',
                                        'opened': 'success', 'closing_control': 'warning', 'closed': 'warning'}}"/>
                            </div>
                            <div class="o_kanban_record_body">
                                <field name="name" />
                            </div>
                            <div class="o_kanban_record_bottom">
                                <div class="oe_kanban_bottom_left">
                                    <span><field name="start_at" /></span>
                                </div>
                                <div class="oe_kanban_bottom_right">
                                    <field name="user_id" widget="many2one_avatar_user"/>
                                </div>
                            </div>
                        </div>
                    </t>
                </templates>
            </kanban>
        </field>
    </record>

    <record id="view_pos_session_search" model="ir.ui.view">
        <field name="name">pos.session.search.view</field>
        <field name="model">pos.session</field>
        <field name="arch" type="xml">
            <search string="Point of Sale Session">
                <field name="name"/>
                <field name="config_id" />
                <field name="user_id" />
                <filter name="my_sessions" string="My Sessions" domain="[('user_id', '=', uid)]"/>
                <separator/>
                <filter name="open_sessions" string="In Progress" domain="[('state', '=', 'opened')]"/>
                <separator/>
                <filter string="Opening Date" name="start_date" date="start_at" />
                <group expand="0" string="Group By">
                    <filter string="Opened By" name="user" domain="[]" context="{'group_by' : 'user_id'}"/>
                    <filter string="Point of Sale" name="point_of_sale" domain="[]" context="{'group_by': 'config_id'}"/>
                    <filter string="Status" name="status" domain="[]" context="{'group_by': 'state'}"/>
                    <filter string="Opening Date" name="opening_date" domain="[]" context="{'group_by': 'start_at'}"/>
                    <filter string="Closing Date" name="closing_date" domain="[]" context="{'group_by': 'stop_at'}"/>
                </group>
            </search>
        </field>
    </record>

    <record id="action_pos_session" model="ir.actions.act_window">
        <field name="name">Sessions</field>
        <field name="type">ir.actions.act_window</field>
        <field name="res_model">pos.session</field>
        <field name="view_mode">tree,kanban,form</field>
        <field name="search_view_id" ref="view_pos_session_search" />
        <field name="help" type="html">
            <p class="o_view_nocontent_empty_folder">
                No sessions found
            </p><p>
                A session is a period of time, usually one day, during which you sell through the Point of Sale.
            </p>
        </field>
    </record>

    <record id="mail_activity_old_session" model="mail.activity.type">
        <field name="name">Session open over 7 days</field>
        <field name="summary">note</field>
        <field name="category">default</field>
        <field name="res_model">pos.session</field>
        <field name="icon">fa-tasks</field>
        <field name="delay_count">0</field>
    </record>

    <menuitem
        id="menu_pos_session_all"
        parent="menu_point_of_sale"
        action="action_pos_session"
        sequence="2"
        groups="group_pos_manager"/>
</odoo>
