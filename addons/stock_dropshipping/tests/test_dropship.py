# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common, Form
from odoo.tools import mute_logger


class TestDropship(common.TransactionCase):

    def test_00_dropship(self):

        # Create a vendor
        supplier_dropship = self.env['res.partner'].create({'name': 'Vendor of Dropshipping test'})

        # Create new product without any routes
        drop_shop_product = self.env['product.product'].create({
            'name': "Pen drive",
            'type': "product",
            'categ_id': self.env.ref('product.product_category_1').id,
            'lst_price': 100.0,
            'standard_price': 0.0,
            'uom_id': self.env.ref('product.product_uom_unit').id,
            'uom_po_id': self.env.ref('product.product_uom_unit').id,
            'seller_ids': [(0, 0, {
                'delay': 1,
                'name': supplier_dropship.id,
                'min_qty': 2.0
            })]
        })

        # Create a sales order with a line of 200 PCE incoming shipment, with route_id drop shipping
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.env.ref('base.res_partner_2')
        so_form.payment_term_id = self.env.ref('account.account_payment_term')
        with mute_logger('odoo.tests.common.onchange'):
            # otherwise complains that there's not enough inventory and
            # apparently that's normal according to @jco and @sle
            with so_form.order_line.new() as line:
                line.product_id = drop_shop_product
                line.product_uom_qty = 200
                line.price_unit = 1.00
                line.route_id = self.env.ref('stock_dropshipping.route_drop_shipping')
        sale_order_drp_shpng = so_form.save()

        # Confirm sales order
        sale_order_drp_shpng.action_confirm()

        # Check the sales order created a procurement group which has a procurement of 200 pieces
        self.assertTrue(sale_order_drp_shpng.procurement_group_id, 'SO should have procurement group')

        # Check a quotation was created to a certain vendor and confirm so it becomes a confirmed purchase order
        purchase = self.env['purchase.order'].search([('partner_id', '=', supplier_dropship.id)])
        self.assertTrue(purchase, "an RFQ should have been created by the scheduler")
        purchase.button_confirm()
        self.assertEquals(purchase.state, 'purchase', 'Purchase order should be in the approved state')
        self.assertEquals(len(purchase.ids), 1, 'There should be one picking')

        # Send the 200 pieces
        purchase.picking_ids.move_lines.quantity_done = purchase.picking_ids.move_lines.product_qty
        purchase.picking_ids.button_validate()

        # Check one move line was created in Customers location with 200 pieces
        move_line = self.env['stock.move.line'].search([
            ('location_dest_id', '=', self.env.ref('stock.stock_location_customers').id),
            ('product_id', '=', drop_shop_product.id)])
        self.assertEquals(len(move_line.ids), 1, 'There should be exactly one move line')
