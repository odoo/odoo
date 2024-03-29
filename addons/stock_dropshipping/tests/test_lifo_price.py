# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, tools
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon
from odoo.tests import tagged, common, Form


@tagged('-at_install', 'post_install')
class TestLifoPrice(ValuationReconciliationTestCommon):

    def test_lifoprice(self):
        # Required for `uom_id` to be visible in the view
        self.env.user.groups_id += self.env.ref('uom.group_uom')

        # Set product category removal strategy as LIFO
        product_category_001 = self.env['product.category'].create({
            'name': 'Lifo Category',
            'removal_strategy_id': self.env.ref('stock.removal_lifo').id,
            'property_valuation': 'real_time',
            'property_cost_method': 'fifo',
        })
        res_partner_3 = self.env['res.partner'].create({'name': 'My Test Partner'})

        # Set a product as using lifo price
        product_form = Form(self.env['product.product'])
        product_form.default_code = 'LIFO'
        product_form.name = 'LIFO Ice Cream'
        product_form.detailed_type = 'product'
        product_form.categ_id = product_category_001
        # <field name="list_price" position="attributes">
        #     <attribute name="readonly">product_variant_count &gt; 1</attribute>
        #     <attribute name="invisible">1</attribute>
        # </field>
        # <field name="list_price" position="after">
        #     <field name="lst_price" class="oe_inline" widget='monetary' options="{'currency_field': 'currency_id', 'field_digits': True}"/>
        # </field>
        # @api.onchange('lst_price')
        # def _set_product_lst_price(self):
        #     ...
        #         product.write({'list_price': value})
        product_form.lst_price = 100.0
        product_form.uom_id = self.env.ref('uom.product_uom_kgm')
        product_form.uom_po_id = self.env.ref('uom.product_uom_kgm')
        # these are not available (visible) in either product or variant
        # for views, apparently from the UI you can only set the product
        # category (or hand-assign the property_* version which seems...)
        # product_form.categ_id.valuation = 'real_time'
        # product_form.categ_id.property_cost_method = 'fifo'
        product_form.categ_id.property_stock_account_input_categ_id = self.company_data['default_account_stock_in']
        product_form.categ_id.property_stock_account_output_categ_id = self.company_data['default_account_stock_out']
        product_lifo_icecream = product_form.save()

        product_lifo_icecream.standard_price = 70.0

        # I create a draft Purchase Order for first in move for 10 pieces at 60 euro
        order_form = Form(self.env['purchase.order'])
        order_form.partner_id = res_partner_3
        with order_form.order_line.new() as line:
            line.product_id = product_lifo_icecream
            line.product_qty = 10.0
            line.price_unit = 60.0
        purchase_order_lifo1 = order_form.save()

        # I create a draft Purchase Order for second shipment for 30 pieces at 80 euro
        order2_form = Form(self.env['purchase.order'])
        order2_form.partner_id = res_partner_3
        with order2_form.order_line.new() as line:
            line.product_id = product_lifo_icecream
            line.product_qty = 30.0
            line.price_unit = 80.0
        purchase_order_lifo2 = order2_form.save()

        # I confirm the first purchase order
        purchase_order_lifo1.button_confirm()

        # I check the "Approved" status of purchase order 1
        self.assertEqual(purchase_order_lifo1.state, 'purchase')

        # Process the receipt of purchase order 1
        purchase_order_lifo1.picking_ids[0].move_ids.quantity = purchase_order_lifo1.picking_ids[0].move_ids.product_qty
        purchase_order_lifo1.picking_ids[0].move_ids.picked = True
        purchase_order_lifo1.picking_ids[0].button_validate()

        # I confirm the second purchase order
        purchase_order_lifo2.button_confirm()

        # Process the receipt of purchase order 2
        purchase_order_lifo2.picking_ids[0].move_ids.quantity = purchase_order_lifo2.picking_ids[0].move_ids.product_qty
        purchase_order_lifo2.picking_ids[0].move_ids.picked = True
        purchase_order_lifo2.picking_ids[0].button_validate()

        # Let us send some goods
        out_form = Form(self.env['stock.picking'])
        out_form.picking_type_id = self.company_data['default_warehouse'].out_type_id
        with out_form.move_ids_without_package.new() as move:
            move.product_id = product_lifo_icecream
            move.quantity = 20.0
            move.picked = True
            move.date = fields.Datetime.now()
        outgoing_lifo_shipment = out_form.save()

        # I assign this outgoing shipment
        outgoing_lifo_shipment.action_assign()

        # Process the delivery of the outgoing shipment
        outgoing_lifo_shipment.button_validate()

        # Check if the move value correctly reflects the fifo costing method
        self.assertEqual(outgoing_lifo_shipment.move_ids.stock_valuation_layer_ids.value, -1400.0, 'Stock move value should have been 1400 euro')
