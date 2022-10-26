# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common, Form
from odoo.tools import mute_logger


class TestDropship(common.TransactionCase):
    def test_change_qty(self):
        # enable the dropship and MTO route on the product
        prod = self.env['product.product'].create({'name': 'Large Desk'})
        dropshipping_route = self.env.ref('stock_dropshipping.route_drop_shipping')
        mto_route = self.env.ref('stock.route_warehouse0_mto')
        prod.write({'route_ids': [(6, 0, [dropshipping_route.id, mto_route.id])]})

        # add a vendor
        vendor1 = self.env['res.partner'].create({'name': 'vendor1'})
        seller1 = self.env['product.supplierinfo'].create({
            'partner_id': vendor1.id,
            'price': 8,
        })
        prod.write({'seller_ids': [(6, 0, [seller1.id])]})

        # sell one unit of this product
        cust = self.env['res.partner'].create({'name': 'customer1'})
        so = self.env['sale.order'].create({
            'partner_id': cust.id,
            'partner_invoice_id': cust.id,
            'partner_shipping_id': cust.id,
            'order_line': [(0, 0, {
                'name': prod.name,
                'product_id': prod.id,
                'product_uom_qty': 1.00,
                'product_uom': prod.uom_id.id,
                'price_unit': 12,
            })],
            'pricelist_id': self.env.ref('product.list0').id,
            'picking_policy': 'direct',
        })
        so.action_confirm()
        po = self.env['purchase.order'].search([('group_id', '=', so.procurement_group_id.id)])
        po_line = po.order_line

        # Check dropship count on SO and PO
        self.assertEqual(po.incoming_picking_count, 0)
        self.assertEqual(so.delivery_count, 0)

        # Check the qty on the P0
        self.assertAlmostEqual(po_line.product_qty, 1.00)

        # Update qty on SO and check PO
        so.write({'order_line': [[1, so.order_line.id, {'product_uom_qty': 2.00}]]})
        self.assertAlmostEqual(po_line.product_qty, 2.00)

        # Create a new so line
        sol2 = self.env['sale.order.line'].create({
            'order_id': so.id,
            'product_id': prod.id,
            'product_uom_qty': 3.00,
            'price_unit': 12,
        })
        # there is a new line
        pol2 = po.order_line - po_line
        # the first line is unchanged
        self.assertAlmostEqual(po_line.product_qty, 2.00)
        # the new line matches the new line on the so
        self.assertAlmostEqual(pol2.product_qty, sol2.product_uom_qty)

    def test_00_dropship(self):
        # Required for `route_id` to be visible in the view
        self.env.user.groups_id += self.env.ref('stock.group_adv_location')

        # Create a vendor
        supplier_dropship = self.env['res.partner'].create({'name': 'Vendor of Dropshipping test'})

        # Create new product without any routes
        drop_shop_product = self.env['product.product'].create({
            'name': "Pen drive",
            'type': "product",
            'categ_id': self.env.ref('product.product_category_1').id,
            'lst_price': 100.0,
            'standard_price': 0.0,
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'uom_po_id': self.env.ref('uom.product_uom_unit').id,
            'seller_ids': [(0, 0, {
                'delay': 1,
                'partner_id': supplier_dropship.id,
                'min_qty': 2.0
            })]
        })

        # Create a sales order with a line of 200 PCE incoming shipment, with route_id drop shipping
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.env['res.partner'].create({'name': 'My Test Partner'})
        so_form.payment_term_id = self.env.ref('account.account_payment_term_end_following_month')
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
        self.assertEqual(purchase.state, 'purchase', 'Purchase order should be in the approved state')

        # Check dropship count on SO and PO
        self.assertEqual(purchase.incoming_picking_count, 0)
        self.assertEqual(sale_order_drp_shpng.delivery_count, 0)
        self.assertEqual(sale_order_drp_shpng.dropship_picking_count, 1)
        self.assertEqual(purchase.dropship_picking_count, 1)

        # Send the 200 pieces
        purchase.picking_ids.move_ids.quantity_done = purchase.picking_ids.move_ids.product_qty
        purchase.picking_ids.button_validate()

        # Check one move line was created in Customers location with 200 pieces
        move_line = self.env['stock.move.line'].search([
            ('location_dest_id', '=', self.env.ref('stock.stock_location_customers').id),
            ('product_id', '=', drop_shop_product.id)])
        self.assertEqual(len(move_line.ids), 1, 'There should be exactly one move line')
