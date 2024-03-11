<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data>
        <function model="stock.warehouse" name="_create_missing_pos_picking_types"/>
    </data>

    <data noupdate="1">
        <!-- After closing the PoS, open the dashboard menu -->
        <record id="action_client_pos_menu" model="ir.actions.client">
            <field name="name">Reload POS Menu</field>
            <field name="tag">reload</field>
            <field name="params" eval="{'menu_id': ref('menu_point_root')}"/>
        </record>

        <record id="product_category_pos" model="product.category">
            <field name="parent_id" ref="product.product_category_1"/>
            <field name="name">PoS</field>
        </record>

        <record id="product_product_tip" model="product.product">
            <field name="name">Tips</field>
            <field name="categ_id" ref="point_of_sale.product_category_pos"/>
            <field name="default_code">TIPS</field>
            <field name="weight">0.01</field>
            <field name="available_in_pos">False</field>
            <field name="taxes_id" eval="[(5,)]"/>
        </record>

        <record model="pos.config" id="pos_config_main" forcecreate="0">
            <field name="name">Shop</field>
        </record>

        <record id="product_product_consumable" model="product.product">
            <field name="name">Discount</field>
            <field name="available_in_pos">False</field>
            <field name="standard_price">0.00</field>
            <field name="list_price">0.00</field>
            <field name="weight">0.00</field>
            <field name="type">consu</field>
            <field name="categ_id" ref="point_of_sale.product_category_pos"/>
            <field name="uom_id" ref="uom.product_uom_unit"/>
            <field name="uom_po_id" ref="uom.product_uom_unit"/>
            <field name="default_code">DISC</field>
            <field name="purchase_ok">False</field>
        </record>

        <record id="uom.product_uom_categ_unit" model="uom.category">
            <field name="is_pos_groupable">True</field>
        </record>

        <record model="pos.bill" id="0_01" forcecreate="0">
            <field name="name">0.01</field>
            <field name="value">0.01</field>
            <field name="pos_config_ids" eval="[(6, False, [ref('point_of_sale.pos_config_main')])]"/>
        </record>

        <record model="pos.bill" id="0_02" forcecreate="0">
            <field name="name">0.02</field>
            <field name="value">0.02</field>
            <field name="pos_config_ids" eval="[(6, False, [ref('point_of_sale.pos_config_main')])]"/>
        </record>

        <record model="pos.bill" id="0_05" forcecreate="0">
            <field name="name">0.05</field>
            <field name="value">0.05</field>
            <field name="pos_config_ids" eval="[(6, False, [ref('point_of_sale.pos_config_main')])]"/>
        </record>

        <record model="pos.bill" id="0_10" forcecreate="0">
            <field name="name">0.10</field>
            <field name="value">0.10</field>
            <field name="pos_config_ids" eval="[(6, False, [ref('point_of_sale.pos_config_main')])]"/>
        </record>

        <record model="pos.bill" id="0_20" forcecreate="0">
            <field name="name">0.20</field>
            <field name="value">0.20</field>
            <field name="pos_config_ids" eval="[(6, False, [ref('point_of_sale.pos_config_main')])]"/>
        </record>

        <record model="pos.bill" id="0_25" forcecreate="0">
            <field name="name">0.25</field>
            <field name="value">0.25</field>
            <field name="pos_config_ids" eval="[(6, False, [ref('point_of_sale.pos_config_main')])]"/>
        </record>

        <record model="pos.bill" id="0_50" forcecreate="0">
            <field name="name">0.50</field>
            <field name="value">0.50</field>
            <field name="pos_config_ids" eval="[(6, False, [ref('point_of_sale.pos_config_main')])]"/>
        </record>

        <record model="pos.bill" id="1_00" forcecreate="0">
            <field name="name">1.00</field>
            <field name="value">1.00</field>
            <field name="pos_config_ids" eval="[(6, False, [ref('point_of_sale.pos_config_main')])]"/>
        </record>

        <record model="pos.bill" id="2_00" forcecreate="0">
            <field name="name">2.00</field>
            <field name="value">2.00</field>
            <field name="pos_config_ids" eval="[(6, False, [ref('point_of_sale.pos_config_main')])]"/>
        </record>

        <record model="pos.bill" id="5_00" forcecreate="0">
            <field name="name">5.00</field>
            <field name="value">5.00</field>
            <field name="pos_config_ids" eval="[(6, False, [ref('point_of_sale.pos_config_main')])]"/>
        </record>

        <record model="pos.bill" id="10_00" forcecreate="0">
            <field name="name">10.00</field>
            <field name="value">10.00</field>
            <field name="pos_config_ids" eval="[(6, False, [ref('point_of_sale.pos_config_main')])]"/>
        </record>

        <record model="pos.bill" id="20_00" forcecreate="0">
            <field name="name">20.00</field>
            <field name="value">20.00</field>
            <field name="pos_config_ids" eval="[(6, False, [ref('point_of_sale.pos_config_main')])]"/>
        </record>

        <record model="pos.bill" id="50_00" forcecreate="0">
            <field name="name">50.00</field>
            <field name="value">50.00</field>
            <field name="pos_config_ids" eval="[(6, False, [ref('point_of_sale.pos_config_main')])]"/>
        </record>

        <record model="pos.bill" id="100_00" forcecreate="0">
            <field name="name">100.00</field>
            <field name="value">100.00</field>
            <field name="pos_config_ids" eval="[(6, False, [ref('point_of_sale.pos_config_main')])]"/>
        </record>

        <record model="pos.bill" id="200_00" forcecreate="0">
            <field name="name">200.00</field>
            <field name="value">200.00</field>
            <field name="pos_config_ids" eval="[(6, False, [ref('point_of_sale.pos_config_main')])]"/>
        </record>

        <function model="pos.config" name="post_install_pos_localisation" />
    </data>
</odoo>
