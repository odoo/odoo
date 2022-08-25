<?xml version="1.0" encoding="utf-8"?>
<odoo>
        <!-- Partners with Barcodes -->
        <record id='base.res_partner_1'  model='res.partner'> <field name='barcode'>0420100000005</field> </record>
        <record id='base.res_partner_2'  model='res.partner'> <field name='barcode'>0420200000004</field> </record>
        <record id='base.res_partner_3'  model='res.partner'> <field name='barcode'>0420300000003</field> </record>
        <record id='base.res_partner_4'  model='res.partner'> <field name='barcode'>0420400000002</field> </record>
        <record id='base.res_partner_4'  model='res.partner'> <field name='barcode'>0420700000009</field> </record>
        <record id='base.res_partner_10' model='res.partner'> <field name='barcode'>0421000000003</field> </record>
        <record id='base.res_partner_12'  model='res.partner'> <field name='barcode'>0420800000008</field> </record>
        <record id='base.res_partner_18' model='res.partner'> <field name='barcode'>0421800000005</field> </record>

        <record id="base.user_root" model="res.users">
            <field name="barcode">0410100000006</field>
            <field name="groups_id" eval="[(4,ref('group_pos_manager'))]"/>
        </record>

        <record id="base.user_demo" model="res.users">
            <field name="groups_id" eval="[(4, ref('group_pos_user'))]"/>
        </record>


        <!-- Resource: pos.category -->
        <record id="pos_category_miscellaneous" model="pos.category">
          <field name="name">Miscellaneous</field>
        </record>
        <record id="pos_category_desks" model="pos.category">
          <field name="name">Desks</field>
        </record>
        <record id="pos_category_chairs" model="pos.category">
          <field name="name">Chairs</field>
        </record>

        <record model="pos.config" id="pos_config_main">
            <field name="iface_start_categ_id" ref="pos_category_chairs"/>
            <field name="start_category">True</field>
        </record>

        <!-- Resource: product.product -->
        <record id="stock.product_cable_management_box" model="product.product">
          <field name="pos_categ_id" ref="point_of_sale.pos_category_miscellaneous"/>
        </record>
        <record id="wall_shelf" model="product.product">
          <field name="available_in_pos">True</field>
          <field name="list_price">1.98</field>
          <field name="name">Wall Shelf Unit</field>
          <field name="default_code">FURN_0009</field>
          <field name="type">product</field>
          <field name="weight">0.01</field>
          <field name="to_weight">True</field>
          <field name="barcode">2100002000003</field>
          <field name="taxes_id" eval='[(5,)]'/>
          <field name="categ_id" ref="product.product_category_5"/>
          <field name="pos_categ_id" ref="pos_category_miscellaneous"/>
          <field name="uom_id" ref="uom.product_uom_unit" />
          <field name="uom_po_id" ref="uom.product_uom_unit" />
          <field name="image_1920" type="base64" file="point_of_sale/static/img/wall_shelf_unit.png"/>
        </record>
        <record id="small_shelf" model="product.product">
          <field name="available_in_pos">True</field>
          <field name="list_price">2.83</field>
          <field name="name">Small Shelf</field>
          <field name="default_code">FURN_0008</field>
          <field name="type">product</field>
          <field name="weight">0.01</field>
          <field name="taxes_id" eval='[(5,)]'/>
          <field name="categ_id" ref="product.product_category_5"/>
          <field name="pos_categ_id" ref="pos_category_miscellaneous"/>
          <field name="to_weight">True</field>
          <field name="uom_id" ref="uom.product_uom_unit" />
          <field name="uom_po_id" ref="uom.product_uom_unit" />
          <field name="image_1920" type="base64" file="point_of_sale/static/img/small_shelf.png"/>
        </record>

        <record id="letter_tray" model="product.product">
          <field name="available_in_pos">True</field>
          <field name="list_price">4.80</field>
          <field name="name">Letter Tray</field>
          <field name="default_code">FURN_0004</field>
          <field name="type">product</field>
          <field name="weight">0.01</field>
          <field name="to_weight">True</field>
          <field name="categ_id" ref="product.product_category_5"/>
          <field name="pos_categ_id" ref="pos_category_miscellaneous"/>
          <field name="uom_id" ref="uom.product_uom_unit" />
          <field name="uom_po_id" ref="uom.product_uom_unit" />
          <field name="image_1920" type="base64" file="point_of_sale/static/img/letter_tray.png"/>
        </record>
        <record id="desk_organizer" model="product.product">
          <field name="available_in_pos">True</field>
          <field name="list_price">5.10</field>
          <field name="name">Desk Organizer</field>
          <field name="default_code">FURN_0001</field>
          <field name="to_weight">True</field>
          <field name="barcode">2300001000008</field>
          <field name="type">product</field>
          <field name="weight">0.01</field>
          <field name="categ_id" ref="product.product_category_5"/>
          <field name="pos_categ_id" ref="pos_category_miscellaneous"/>
          <field name="uom_id" ref="uom.product_uom_unit" />
          <field name="uom_po_id" ref="uom.product_uom_unit" />
          <field name="image_1920" type="base64" file="point_of_sale/static/img/desk_organizer.png"/>
          <field name="taxes_id" eval='[(5,)]'/>  <!-- no taxes -->
        </record>

        <function model="ir.model.data" name="_update_xmlids">
            <value model="base" eval="[{
                'xml_id': 'point_of_sale.desk_organizer_product_template',
                'record': obj().env.ref('point_of_sale.desk_organizer').product_tmpl_id,
                'noupdate': True,
            }]"/>
        </function>

        <record id="size_attribute" model="product.attribute">
            <field name="name">Size</field>
            <field name="sequence">30</field>
            <field name="display_type">radio</field>
            <field name="create_variant">no_variant</field>
        </record>
        <record id="size_attribute_s" model="product.attribute.value">
            <field name="name">S</field>
            <field name="sequence">1</field>
            <field name="attribute_id" ref="size_attribute"/>
        </record>
        <record id="size_attribute_m" model="product.attribute.value">
            <field name="name">M</field>
            <field name="sequence">2</field>
            <field name="attribute_id" ref="size_attribute"/>
        </record>
        <record id="size_attribute_l" model="product.attribute.value">
            <field name="name">L</field>
            <field name="sequence">3</field>
            <field name="attribute_id" ref="size_attribute"/>
        </record>
        <record id="desk_organizer_size" model="product.template.attribute.line">
            <field name="product_tmpl_id" ref="point_of_sale.desk_organizer_product_template"/>
            <field name="attribute_id" ref="size_attribute"/>
            <field name="value_ids" eval="[(6, 0, [ref('size_attribute_s'), ref('size_attribute_m'), ref('size_attribute_l')])]"/>
        </record>

        <record id="fabric_attribute" model="product.attribute">
            <field name="name">Fabric</field>
            <field name="sequence">40</field>
            <field name="display_type">select</field>
            <field name="create_variant">no_variant</field>
        </record>
        <record id="fabric_attribute_plastic" model="product.attribute.value">
            <field name="name">Plastic</field>
            <field name="sequence">1</field>
            <field name="attribute_id" ref="fabric_attribute"/>
        </record>
        <record id="fabric_attribute_leather" model="product.attribute.value">
            <field name="name">Leather</field>
            <field name="sequence">2</field>
            <field name="attribute_id" ref="fabric_attribute"/>
        </record>
        <record id="fabric_attribute_custom" model="product.attribute.value">
            <field name="name">Custom</field>
            <field name="sequence">3</field>
            <field name="attribute_id" ref="fabric_attribute"/>
            <field name="is_custom">True</field>
        </record>
        <record id="desk_organizer_fabric" model="product.template.attribute.line">
            <field name="product_tmpl_id" ref="point_of_sale.desk_organizer_product_template"/>
            <field name="attribute_id" ref="fabric_attribute"/>
            <field name="value_ids" eval="[(6, 0, [ref('fabric_attribute_plastic'), ref('fabric_attribute_leather'), ref('fabric_attribute_custom')])]"/>
        </record>

        <record id="magnetic_board" model="product.product">
          <field name="available_in_pos">True</field>
          <field name="list_price">1.98</field>
          <field name="name">Magnetic Board</field>
          <field name="default_code">FURN_0005</field>
          <field name="type">product</field>
          <field name="weight">0.01</field>
          <field name="barcode">2301000000006</field>
          <field name="to_weight">True</field>
          <field name="categ_id" ref="product.product_category_5"/>
          <field name="pos_categ_id" ref="pos_category_miscellaneous"/>
          <field name="uom_id" ref="uom.product_uom_unit" />
          <field name="uom_po_id" ref="uom.product_uom_unit" />
          <field name="image_1920" type="base64" file="point_of_sale/static/img/magnetic_board.png"/>
        </record>
        <record id="monitor_stand" model="product.product">
          <field name="available_in_pos">True</field>
          <field name="list_price">3.19</field>
          <field name="name">Monitor Stand</field>
          <field name="default_code">FURN_0006</field>
          <field name="type">product</field>
          <field name="weight">0.01</field>
          <field name="to_weight">True</field>
          <field name="categ_id" ref="product.product_category_5"/>
          <field name="pos_categ_id" ref="pos_category_miscellaneous"/>
          <field name="uom_id" ref="uom.product_uom_unit" />
          <field name="uom_po_id" ref="uom.product_uom_unit" />
          <field name="image_1920" type="base64" file="point_of_sale/static/img/monitor_stand.png"/>
        </record>
        <record id="desk_pad" model="product.product">
          <field name="available_in_pos">True</field>
          <field name="list_price">1.98</field>
          <field name="name">Desk Pad</field>
          <field name="default_code">FURN_0002</field>
          <field name="type">product</field>
          <field name="weight">0.01</field>
          <field name="to_weight">True</field>
          <field name="categ_id" ref="product.product_category_5"/>
          <field name="pos_categ_id" ref="pos_category_miscellaneous"/>
          <field name="uom_id" ref="uom.product_uom_unit" />
          <field name="uom_po_id" ref="uom.product_uom_unit" />
          <field name="image_1920" type="base64" file="point_of_sale/static/img/desk_pad.png"/>
        </record>

        <record id="whiteboard" model="product.product">
          <field name="available_in_pos">True</field>
          <field name="list_price">1.70</field>
          <field name="name">Whiteboard</field>
          <field name="to_weight">True</field>
          <field name="type">product</field>
          <field name="weight">0.01</field>
          <field name="categ_id" ref="product.product_category_5"/>
          <field name="uom_id" ref="uom.product_uom_unit" />
          <field name="uom_po_id" ref="uom.product_uom_unit" />
          <field name="image_1920" type="base64" file="point_of_sale/static/img/whiteboard.png"/>
        </record>

        <record id="led_lamp" model="product.product">
          <field name="available_in_pos">True</field>
          <field name="list_price">0.90</field>
          <field name="name">LED Lamp</field>
          <field name="default_code">FURN_0003</field>
          <field name="type">product</field>
          <field name="weight">0.01</field>
          <field name="to_weight">True</field>
          <field name="categ_id" ref="product.product_category_5"/>
          <field name="pos_categ_id" ref="pos_category_miscellaneous"/>
          <field name="uom_id" ref="uom.product_uom_unit" />
          <field name="uom_po_id" ref="uom.product_uom_unit" />
          <field name="image_1920" type="base64" file="point_of_sale/static/img/led_lamp.png"/>
        </record>

        <record id="newspaper_rack" model="product.product">
          <field name="available_in_pos">True</field>
          <field name="list_price">1.28</field>
          <field name="name">Newspaper Rack</field>
          <field name="default_code">FURN_0007</field>
          <field name="type">product</field>
          <field name="weight">0.01</field>
          <field name="to_weight">True</field>
          <field name="barcode">2100001000004</field>
          <field name="categ_id" ref="product.product_category_5"/>
          <field name="pos_categ_id" ref="pos_category_miscellaneous"/>
          <field name="uom_id" ref="uom.product_uom_unit" />
          <field name="uom_po_id" ref="uom.product_uom_unit" />
          <field name="image_1920" type="base64" file="point_of_sale/static/img/newspaper_stand.png"/>
        </record>

        <record id="whiteboard_pen" model="product.product">
          <field name="available_in_pos">True</field>
          <field name="list_price">1.20</field>
          <field name="name">Whiteboard Pen</field>
          <field name="weight">0.01</field>
          <field name="default_code">CONS_0001</field>
          <field name="to_weight">True</field>
          <field name="categ_id" ref="product.product_category_consumable"/>
          <field name="pos_categ_id" ref="pos_category_miscellaneous"/>
          <field name="uom_id" ref="uom.product_uom_unit" />
          <field name="uom_po_id" ref="uom.product_uom_unit" />
          <field name="image_1920" type="base64" file="point_of_sale/static/img/whiteboard_pen.png"/>
        </record>

        <record id="product.product_product_1" model="product.product">
          <field name="available_in_pos" eval="True"/>
          <field name="pos_categ_id" ref="pos_category_miscellaneous"/>
        </record>
        <record id="product.product_product_2" model="product.product">
          <field name="available_in_pos" eval="True"/>
          <field name="pos_categ_id" ref="pos_category_miscellaneous"/>
        </record>
        <record id="product.product_delivery_01" model="product.product">
          <field name="available_in_pos" eval="True"/>
          <field name="pos_categ_id" ref="pos_category_chairs"/>
        </record>
        <record id="product.product_delivery_02" model="product.product">
          <field name="available_in_pos" eval="True"/>
          <field name="pos_categ_id" ref="pos_category_miscellaneous"/>
        </record>
        <record id="product.product_order_01" model="product.product">
          <field name="available_in_pos" eval="True"/>
          <field name="pos_categ_id" ref="pos_category_miscellaneous"/>
        </record>
        <record id="product.product_product_3" model="product.product">
          <field name="available_in_pos" eval="True"/>
          <field name="pos_categ_id" ref="pos_category_desks"/>
        </record>
        <record id="product.product_product_4_product_template" model="product.template">
          <field name="available_in_pos" eval="True"/>
          <field name="pos_categ_id" ref="pos_category_desks"/>
        </record>
        <record id="product.product_product_5" model="product.product">
          <field name="available_in_pos" eval="True"/>
          <field name="pos_categ_id" ref="pos_category_desks"/>
        </record>
        <record id="product.product_product_6" model="product.product">
          <field name="available_in_pos" eval="True"/>
          <field name="pos_categ_id" ref="pos_category_miscellaneous"/>
        </record>
        <record id="product.product_product_7" model="product.product">
          <field name="available_in_pos" eval="True"/>
          <field name="pos_categ_id" ref="pos_category_miscellaneous"/>
        </record>
        <record id="product.product_product_8" model="product.product">
          <field name="available_in_pos" eval="True"/>
          <field name="pos_categ_id" ref="pos_category_desks"/>
        </record>
        <record id="product.product_product_9" model="product.product">
          <field name="available_in_pos" eval="True"/>
          <field name="pos_categ_id" ref="pos_category_miscellaneous"/>
        </record>
        <record id="product.product_product_10" model="product.product">
          <field name="available_in_pos" eval="True"/>
          <field name="pos_categ_id" ref="pos_category_miscellaneous"/>
        </record>
        <record id="product.product_product_11" model="product.product">
          <field name="available_in_pos" eval="True"/>
          <field name="pos_categ_id" ref="pos_category_chairs"/>
        </record>
        <record id="product.product_product_11b" model="product.product">
          <field name="available_in_pos" eval="True"/>
          <field name="pos_categ_id" ref="pos_category_chairs"/>
        </record>
        <record id="product.product_product_12" model="product.product">
          <field name="available_in_pos" eval="True"/>
          <field name="pos_categ_id" ref="pos_category_chairs"/>
        </record>
        <record id="product.product_product_13" model="product.product">
          <field name="available_in_pos" eval="True"/>
          <field name="pos_categ_id" ref="pos_category_desks"/>
        </record>
        <record id="product.product_product_16" model="product.product">
          <field name="available_in_pos" eval="True"/>
          <field name="pos_categ_id" ref="pos_category_miscellaneous"/>
        </record>
        <record id="product.product_product_20" model="product.product">
          <field name="available_in_pos" eval="True"/>
          <field name="pos_categ_id" ref="pos_category_miscellaneous"/>
        </record>
        <record id="product.product_product_22" model="product.product">
          <field name="available_in_pos" eval="True"/>
          <field name="pos_categ_id" ref="pos_category_miscellaneous"/>
        </record>
        <record id="product.product_product_24" model="product.product">
          <field name="available_in_pos" eval="True"/>
          <field name="pos_categ_id" ref="pos_category_miscellaneous"/>
        </record>
        <record id="product.product_product_25" model="product.product">
          <field name="available_in_pos" eval="True"/>
          <field name="pos_categ_id" ref="pos_category_miscellaneous"/>
        </record>
        <record id="product.product_product_27" model="product.product">
          <field name="available_in_pos" eval="True"/>
          <field name="pos_categ_id" ref="pos_category_miscellaneous"/>
        </record>
        <record id="product.consu_delivery_03" model="product.product">
          <field name="available_in_pos" eval="True"/>
          <field name="pos_categ_id" ref="pos_category_desks"/>
        </record>
        <record id="product.consu_delivery_02" model="product.product">
          <field name="available_in_pos" eval="True"/>
          <field name="pos_categ_id" ref="pos_category_miscellaneous"/>
        </record>
        <record id="product.consu_delivery_01" model="product.product">
          <field name="available_in_pos" eval="True"/>
          <field name="pos_categ_id" ref="pos_category_miscellaneous"/>
        </record>
</odoo>
