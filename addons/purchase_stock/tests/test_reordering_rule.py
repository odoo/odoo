# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.tests import Form

class TestReorderingRule(TransactionCase):

    def test_reordering_rule(self):
        """
            - Receive products in 2 steps
            - The product has a reordering rule
            - On the po generated, the source document should be the name of the reordering rule
        """
        warehouse_1 = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.id)], limit=1)
        warehouse_1.write({'reception_steps': 'two_steps'})

        # Create a supplier
        partner = self.env['res.partner'].create({
            'name': 'Smith'
        })

        # create product and set the vendor
        product_form = Form(self.env['product.product'])
        product_form.name = 'Product A'
        product_form.type = 'product'
        with product_form.seller_ids.new() as seller:
            seller.name = partner
        product_form.route_ids.add(self.env.ref('purchase_stock.route_warehouse0_buy'))
        product_01 = product_form.save()

        # create reordering rule
        orderpoint_form = Form(self.env['stock.warehouse.orderpoint'])
        orderpoint_form.warehouse_id = warehouse_1
        orderpoint_form.location_id = warehouse_1.lot_stock_id
        orderpoint_form.product_id = product_01
        orderpoint_form.product_min_qty = 0.000
        orderpoint_form.product_max_qty = 0.000
        order_point = orderpoint_form.save()

        # Create Delivery Order of 10 product
        picking_form = Form(self.env['stock.picking'])
        picking_form.partner_id = partner
        picking_form.picking_type_id = self.env.ref('stock.picking_type_out')
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = product_01
            move.product_uom_qty = 10.0
        customer_picking = picking_form.save()

        # picking confirm
        customer_picking.action_confirm()

        # Run scheduler
        self.env['procurement.group'].run_scheduler()

        # Check purchase order created or not
        purchase_order = self.env['purchase.order'].search([('partner_id', '=', partner.id)])
        self.assertTrue(purchase_order, 'No purchase order created.')

        # On the po generated, the source document should be the name of the reordering rule
        self.assertEqual(order_point.name, purchase_order.origin, 'Source document on purchase order should be the name of the reordering rule.')
