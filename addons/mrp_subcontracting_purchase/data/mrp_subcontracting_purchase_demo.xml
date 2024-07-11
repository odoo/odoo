<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">
        <record id="purchase_order_subcontracting" model="purchase.order">
            <field name="partner_id" ref="base.partner_demo_portal"/>
            <field name="user_id" ref="base.user_admin"/>
            <field name="state">purchase</field>
            <field name="order_line" model="purchase.order.line" eval="[(5, 0, 0),
                (0, 0, {
                    'product_id': ref('product.product_delivery_02'),
                    'price_unit': 10.0,
                    'name': 'Office Lamp',
                    'product_qty': 5.0,
                    'date_planned': time.strftime('%Y-%m-%d')}),
            ]"/>
        </record>
    </data>
</odoo>
