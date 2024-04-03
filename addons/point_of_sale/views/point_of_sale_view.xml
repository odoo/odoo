<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Top menu item -->
    <menuitem
        id="menu_point_root"
        name="Point of Sale"
        groups="group_pos_manager,group_pos_user"
        web_icon="point_of_sale,static/description/icon.svg"
        sequence="50"/>

    <!-- Orders menu -->
    <menuitem id="menu_point_of_sale"
        name="Orders"
        parent="menu_point_root"
        sequence="10"/>

    <menuitem id="menu_point_of_sale_customer"
        name="Customers"
        parent="menu_point_of_sale"
        action="account.res_partner_action_customer"
        sequence="100"/>

    <!-- Reporting menu -->
    <menuitem id="menu_point_rep"
        name="Reporting"
        parent="menu_point_root"
        sequence="90"
        groups="group_pos_manager"/>

    <!-- Config menu and sub menus -->
    <menuitem id="menu_point_config_product"
        name="Configuration"
        parent="menu_point_root"
        sequence="100"
        groups="group_pos_manager"/>

    <menuitem id="pos_menu_products_configuration"
        name="Products"
        parent="menu_point_config_product"
        sequence="11"/>

    <record id="action_pos_configuration" model="ir.actions.act_window">
        <field name="name">Settings</field>
        <field name="type">ir.actions.act_window</field>
        <field name="res_model">res.config.settings</field>
        <field name="view_mode">form</field>
        <field name="target">inline</field>
        <field name="context">{'module' : 'point_of_sale', 'bin_size': False}</field>
    </record>

    <menuitem id="menu_pos_global_settings"
        name="Settings"
        parent="menu_point_config_product"
        sequence="0"
        action="action_pos_configuration"
        groups="base.group_system"/>
</odoo>
