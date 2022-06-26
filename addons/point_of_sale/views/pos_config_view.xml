<?xml version="1.0" encoding="utf-8"?>
<odoo>

    <record id="pos_config_view_form" model="ir.ui.view">
        <field name="name">pos.config.form.view</field>
        <field name="model">pos.config</field>
        <field name="arch" type="xml">
            <form string="Point of Sale Configuration">
                <sheet>
                    <widget name="web_ribbon" title="Archived" bg_color="bg-danger" attrs="{'invisible': [('active', '=', True)]}"/>
                    <field name="active" invisible="1"/>
                    <field name="company_has_template" invisible="1"/>
                    <field name="has_active_session" invisible="1"/>
                    <field name="other_devices" invisible="1"/>
                    <field name="is_posbox" invisible="1"/>
                    <field name="module_pos_hr" invisible="1"/>

                    <div class="oe_title" id="title">
                        <label for="name"/>
                        <h1><field name="name" placeholder="e.g. NYC Shop"/></h1>
                    </div>
                    <!-- HIDE this div in create_mode (when '+ New Shop' is clicked in the general settings.) -->
                    <div invisible="context.get('pos_config_create_mode', False)">
                        <div class="o_notification_alert alert alert-warning" attrs="{'invisible':[('has_active_session','=', False)]}" role="alert">
                            A session is currently opened for this PoS. Some settings can only be changed after the session is closed.
                            <button class="btn" style="padding:0" name="open_ui" type="object">Click here to close the session</button>
                        </div>
                        <div class="o_notification_alert alert alert-warning" attrs="{'invisible': [('company_has_template','=',True)]}" role="alert">
                            There is no Chart of Accounts configured on the company. Please go to the invoicing settings to install a Chart of Accounts.
                        </div>
                    </div>

                    <!-- SHOW this div in create_mode (when '+ New Shop' is clicked in the general settings.) -->
                    <div class="row mt16 o_settings_container" invisible="not context.get('pos_config_create_mode', False)">
                        <div class="col-12 col-lg-6 o_setting_box">
                            <div class="o_setting_left_pane">
                                <field name="module_pos_restaurant" />
                            </div>
                            <div class="o_setting_right_pane">
                                <label for="module_pos_restaurant"/>
                            </div>
                        </div>
                    </div>

                    <!-- HIDE this div in create_mode (when '+ New Shop' is clicked in the general settings.) -->
                    <div class="row mt16 o_settings_container" invisible="context.get('pos_config_create_mode', False)">
                        <div class="col-12 col-lg-6 o_setting_box"
                             title="Employees can scan their badge or enter a PIN to log in to a PoS session. These credentials are configurable in the *HR Settings* tab of the employee form.">
                            <div class="o_setting_left_pane">
                                <field name="module_pos_hr" attrs="{'readonly': [('has_active_session','=', True)]}" />
                            </div>
                            <div class="o_setting_right_pane">
                                <span class="o_form_label">Multi Employees per Session</span>
                                <div class="text-muted">
                                    Allow to log and switch between selected Employees
                                </div>
                                <div class="content-group mt16" attrs="{'invisible': [('module_pos_hr','=',False)]}">
                                    <div class="text-warning" id="warning_text_employees">
                                        Save this page and come back here to set up the feature.
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="col-12 col-lg-6 o_setting_box" id="other_devices">
                            <div class="o_setting_left_pane">
                                <field name="other_devices" />
                            </div>
                            <div class="o_setting_right_pane">
                                <label for="other_devices" string="ePos Printer"/>
                                <div class="text-muted mb16">
                                    Connect device to your PoS without an IoT Box
                                </div>
                            </div>
                        </div>
                        <div class="col-12 col-lg-6 o_setting_box">
                            <div class="o_setting_left_pane">
                                <field name="is_posbox" />
                            </div>
                            <div class="o_setting_right_pane">
                                <label for="is_posbox" string="IoT Box"/>
                                <div class="text-muted mb16">
                                    Connect devices using an IoT Box
                                </div>
                                <div class="content-group pos_iot_config" attrs="{'invisible' : [('is_posbox', '=', False)]}">
                                    <div class="row">
                                        <label string="IoT Box IP Address" for="proxy_ip" class="col-lg-4 o_light_label"/>
                                        <field name="proxy_ip"/>
                                    </div>
                                    <div class="row iot_barcode_scanner">
                                        <label string="Barcode Scanner/Card Reader" for="iface_scan_via_proxy" class="col-lg-4 o_light_label"/>
                                        <field name="iface_scan_via_proxy"/>
                                    </div>
                                    <div class="row">
                                        <label string="Electronic Scale" for="iface_electronic_scale" class="col-lg-4 o_light_label"/>
                                        <field name="iface_electronic_scale"/>
                                    </div>
                                    <div class="row">
                                        <label string="Receipt Printer" for="iface_print_via_proxy" class="col-lg-4 o_light_label"/>
                                        <field name="iface_print_via_proxy"/>
                                    </div>
                                    <div class="row" attrs="{'invisible': [('iface_print_via_proxy', '=', False)]}">
                                        <label string="Cashdrawer" for="iface_cashdrawer" class="col-lg-4 o_light_label"/>
                                        <field name="iface_cashdrawer"/>
                                    </div>
                                    <div class="row">
                                        <label string="Customer Display" for="iface_customer_facing_display_via_proxy" class="col-lg-4 o_light_label"/>
                                        <field name="iface_customer_facing_display_via_proxy"/>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div groups="base.group_system">
                            <p>
                                More settings: <a href="#" name="%(action_pos_configuration)d" type="action" class="btn-link o_form_uri" role="button">Configurations > Settings</a>
                            </p>
                        </div>
                    </div>
                </sheet>

                <!-- Replace the default save/discard buttons so that when any of the buttons is clicked, the modal immediately closes. -->
                <footer invisible="not context.get('pos_config_open_modal', False)">
                    <button string="Save" special="save" class="btn-primary"/>
                    <button string="Discard" class="btn-secondary" special="cancel"/>
                </footer>
            </form>
        </field>
    </record>

    <record id="view_pos_config_tree" model="ir.ui.view">
        <field name="name">pos.config.tree.view</field>
        <field name="model">pos.config</field>
        <field name="arch" type="xml">
            <tree string="Point of Sale Configuration">
                <field name="name" />
                <field name="company_id"  options="{'no_create': True}" groups="base.group_multi_company"/>
            </tree>
        </field>
    </record>

    <record id="view_pos_config_search" model="ir.ui.view">
        <field name="name">pos.config.search.view</field>
        <field name="model">pos.config</field>
        <field name="arch" type="xml">
            <search string="Point of Sale Config">
                <field name="name"/>
                <field name="picking_type_id" />
                <filter string="Archived" name="inactive" domain="[('active', '=', False)]"/>
            </search>
        </field>
    </record>

    <record id="action_pos_config_kanban" model="ir.actions.act_window">
        <field name="name">Point of Sale</field>
        <field name="type">ir.actions.act_window</field>
        <field name="res_model">pos.config</field>
        <field name="view_mode">kanban,tree,form</field>
        <field name="domain"></field>
        <field name="search_view_id" ref="view_pos_config_search" />
        <field name="help" type="html">
            <p class="o_view_nocontent_smiling_face">
                Create a new PoS
            </p><p>
                Configure at least one Point of Sale.
            </p>
        </field>
    </record>

    <!-- Products sub Category -->
    <menuitem id="menu_products_pos_category"
        action="point_of_sale.product_pos_category_action"
        parent="point_of_sale.pos_menu_products_configuration"
        sequence="1"/>
    <menuitem id="pos_menu_products_attribute_action"
        action="product.attribute_action"
        parent="point_of_sale.pos_menu_products_configuration"  groups="product.group_product_variant" sequence="2"/>

    <menuitem id="menu_pos_dashboard" action="action_pos_config_kanban" parent="menu_point_root" name="Dashboard" sequence="1"/>
</odoo>
