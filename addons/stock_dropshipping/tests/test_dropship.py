# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command

from odoo.tests import common, Form
from odoo.tools import mute_logger


class TestDropship(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dropshipping_route = cls.env.ref('stock_dropshipping.route_drop_shipping')
        cls.supplier = cls.env['res.partner'].create({'name': 'Vendor'})
        cls.customer = cls.env['res.partner'].create({'name': 'Customer'})
        # dropship route to be added in test
        cls.dropship_product = cls.env['product.product'].create({
            'name': "Pen drive",
            'is_storable': True,
            'lst_price': 100.0,
            'standard_price': 0.0,
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'seller_ids': [(0, 0, {
                'delay': 1,
                'partner_id': cls.supplier.id,
                'min_qty': 2.0
            })],
        })

        cls.lot_dropship_product = cls.env['product.product'].create({
            'name': "Serial product",
            'tracking': 'lot',
            'seller_ids': [(0, 0, {
                'partner_id': cls.supplier.id,
            })],
            'route_ids': [(4, cls.dropshipping_route.id, 0)]
        })

    def test_change_qty(self):
        # enable the dropship route on the product
        self.dropship_product.write({'route_ids': [(6, 0, [self.dropshipping_route.id])]})

        # sell one unit of dropship product
        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'partner_invoice_id': self.customer.id,
            'partner_shipping_id': self.customer.id,
            'order_line': [(0, 0, {
                'name': self.dropship_product.name,
                'product_id': self.dropship_product.id,
                'product_uom_qty': 1.00,
                'price_unit': 12,
            })],
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
            'product_id': self.dropship_product.id,
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
        self.dropship_product.description_purchase = "description_purchase"
        # Required for `route_id` to be visible in the view
        self.env.user.groups_id += self.env.ref('stock.group_adv_location')

        # Create a sales order with a line of 200 PCE incoming shipment, with route_id drop shipping
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.customer
        so_form.payment_term_id = self.env.ref('account.account_payment_term_end_following_month')
        with mute_logger('odoo.tests.common.onchange'):
            # otherwise complains that there's not enough inventory and
            # apparently that's normal according to @jco and @sle
            with so_form.order_line.new() as line:
                line.product_id = self.dropship_product
                line.product_uom_qty = 200
                line.price_unit = 1.00
                line.route_id = self.dropshipping_route
        sale_order_drp_shpng = so_form.save()

        # Confirm sales order
        sale_order_drp_shpng.action_confirm()

        # Check the sales order created a procurement group which has a procurement of 200 pieces
        self.assertTrue(sale_order_drp_shpng.procurement_group_id, 'SO should have procurement group')

        # Check a quotation was created to a certain vendor and confirm so it becomes a confirmed purchase order
        purchase = self.env['purchase.order'].search([('partner_id', '=', self.supplier.id)])
        self.assertTrue(purchase, "an RFQ should have been created by the scheduler")
        self.assertIn("description_purchase", purchase.order_line.name)
        purchase.button_confirm()
        self.assertEqual(purchase.state, 'purchase', 'Purchase order should be in the approved state')

        # Check dropship count on SO and PO
        self.assertEqual(purchase.incoming_picking_count, 0)
        self.assertEqual(sale_order_drp_shpng.delivery_count, 0)
        self.assertEqual(sale_order_drp_shpng.dropship_picking_count, 1)
        self.assertEqual(purchase.dropship_picking_count, 1)

        # Send the 200 pieces
        purchase.picking_ids.move_ids.quantity = purchase.picking_ids.move_ids.product_qty
        purchase.picking_ids.move_ids.picked = True
        self.assertNotIn("description_purchase", purchase.picking_ids.move_ids.description_picking)
        purchase.picking_ids.button_validate()

        # Check one move line was created in Customers location with 200 pieces
        move_line = self.env['stock.move.line'].search([
            ('location_dest_id', '=', self.env.ref('stock.stock_location_customers').id),
            ('product_id', '=', self.dropship_product.id)])
        self.assertEqual(len(move_line.ids), 1, 'There should be exactly one move line')

    def test_sale_order_picking_partner(self):
        """ Test that the partner is correctly set on the picking and the move when the product is dropshipped or not."""

        # Create a vendor and a customer
        supplier_dropship = self.env['res.partner'].create({'name': 'Vendor'})
        customer = self.env['res.partner'].create({'name': 'Customer'})

        # Create new product without any routes
        super_product = self.env['product.product'].create({
            'name': "Super product",
            'seller_ids': [(0, 0, {
                'partner_id': supplier_dropship.id,
            })],
        })

        # Create a sale order
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = customer
        with so_form.order_line.new() as line:
            line.product_id = super_product
        sale_order = so_form.save()

        # Confirm sale order
        sale_order.action_confirm()

        # Check the partner of the related picking and move
        self.assertEqual(sale_order.picking_ids.partner_id, customer)
        self.assertEqual(sale_order.picking_ids.move_ids.partner_id, customer)

        # Add a dropship route to the product
        super_product.route_ids = [self.env.ref('stock_dropshipping.route_drop_shipping').id]

        # Create a sale order
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = customer
        with so_form.order_line.new() as line:
            line.product_id = super_product
        sale_order = so_form.save()

        # Confirm sale order
        sale_order.action_confirm()

        # Check a quotation was created to a certain vendor and confirm it, so it becomes a confirmed purchase order
        purchase = self.env['purchase.order'].search([('partner_id', '=', supplier_dropship.id)])
        self.assertTrue(purchase, "an RFQ should have been created by the scheduler")
        purchase.button_confirm()
        self.assertEqual(purchase.state, 'purchase', 'Purchase order should be in the approved state')

        # Check the partner of the related picking and move
        self.assertEqual(sale_order.picking_ids.partner_id, supplier_dropship)
        self.assertEqual(sale_order.picking_ids.move_ids.partner_id, customer)

    def test_dropshipped_lot_last_delivery(self):
        """ Check if the `last_delivery_partner_id` of a `stock.lot` is computed correctly
            in case the last delivery is a dropship transfer
        """
        # Create a sale order
        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [(0, 0, {
                'product_id': self.lot_dropship_product.id
            })]
        })
        sale_order.action_confirm()
        # Confirm PO
        purchase = self.env['purchase.order'].search([('partner_id', '=', self.supplier.id)])
        self.assertTrue(purchase, "an RFQ should have been created")
        purchase.button_confirm()
        sale_order.picking_ids.move_line_ids.lot_name = '123'
        sale_order.picking_ids.move_ids.picked = True
        sale_order.picking_ids.button_validate()
        self.assertEqual(sale_order.picking_ids.state, 'done')
        self.assertEqual(sale_order.picking_ids.move_line_ids.lot_id.name, '123')
        self.assertEqual(sale_order.picking_ids.move_line_ids.lot_id.last_delivery_partner_id, self.customer)

    def test_sol_reserved_qty_wizard_dropship(self):
        """
        Check that the reserved qty wizard related to a sol is computed from
        the PO if the product is dropshipped.
        """
        product = self.dropship_product
        product.route_ids = self.dropshipping_route
        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [Command.create({
                'product_id': product.id,
                'product_uom_qty': 3.0,
            })]
        })
        sale_order.action_confirm()
        self.assertEqual(sale_order.order_line.qty_available_today, 0.0)
        purchase_order = self.env['purchase.order'].search([('partner_id', '=', self.supplier.id)])
        purchase_order.button_confirm()
        picking_dropship = sale_order.picking_ids.filtered(lambda p: p.picking_type_id)
        self.assertTrue(picking_dropship)
        self.assertEqual(sale_order.order_line.qty_available_today, 3.0)
        self.assertRecordValues(sale_order.order_line, [{'qty_available_today': 3.0, 'qty_delivered': 0.0}])
        picking_dropship.move_ids.quantity = 3.0
        picking_dropship.move_ids.picked = True
        picking_dropship.button_validate()
        self.assertEqual(sale_order.order_line.qty_delivered, 3.0)

    def test_correct_vendor_dropship(self):
        self.supplier_2 = self.env['res.partner'].create({'name': 'Vendor 2'})
        # dropship route to be added in test
        self.dropship_product = self.env['product.product'].create({
            'name': "Pen drive",
            'is_storable': "True",
            'lst_price': 100.0,
            'standard_price': 0.0,
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'seller_ids': [
                (0, 0, {
                    'delay': 10,
                    'partner_id': self.supplier.id,
                    'min_qty': 2.0,
                    'price': 4
                }),
                (0, 0, {
                    'delay': 5,
                    'partner_id': self.supplier_2.id,
                    'min_qty': 1.0,
                    'price': 10
                })
            ],
        })
        self.env.user.groups_id += self.env.ref('stock.group_adv_location')

        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.customer
        with mute_logger('odoo.tests.common.onchange'):
            with so_form.order_line.new() as line:
                line.product_id = self.dropship_product
                line.product_uom_qty = 1
                line.route_id = self.dropshipping_route
        sale_order_drp_shpng = so_form.save()
        sale_order_drp_shpng.action_confirm()

        purchase = self.env['purchase.order'].search([('partner_id', '=', self.supplier_2.id)])
        self.assertTrue(purchase, "an RFQ should have been created by the scheduler")
        self.assertTrue((purchase.date_planned - purchase.date_order).days == 5, "The second supplier has a delay of 5 days")
        self.assertTrue(purchase.amount_untaxed == 10, "the suppliers sells the item for 10$")

        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.customer
        with mute_logger('odoo.tests.common.onchange'):
            with so_form.order_line.new() as line:
                line.product_id = self.dropship_product
                line.product_uom_qty = 2
                line.route_id = self.dropshipping_route
        sale_order_drp_shpng = so_form.save()
        sale_order_drp_shpng.action_confirm()

        purchase = self.env['purchase.order'].search([('partner_id', '=', self.supplier.id)])
        self.assertTrue(purchase, "an RFQ should have been created by the scheduler")
        self.assertTrue((purchase.date_planned - purchase.date_order).days == 10, "The first supplier has a delay of 10 days")
        self.assertTrue(purchase.amount_untaxed == 8, "The price should be 4 * 2")

    def test_add_dropship_product_to_subcontracted_service_po(self):
        """
        P1, a service product subcontracted to vendor V
        P2, a dropshipped product provided by V
        Confirm a SO with 1 x P1. On the generated PO, add 1 x P2 and confirm.
        It should create a dropship picking. Process the picking. It should add
        one SOL for P2.
        """
        supplier = self.dropship_product.seller_ids.partner_id
        delivery_addr = self.env['res.partner'].create({
            'name': 'Super Address',
            'type': 'delivery',
            'parent_id': self.customer.id,
        })

        subcontracted_service = self.env['product.product'].create({
            'name': 'SuperService',
            'type': 'service',
            'service_to_purchase': True,
            'seller_ids': [(0, 0, {'partner_id': supplier.id})],
        })

        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'partner_shipping_id': delivery_addr.id,
            'order_line': [(0, 0, {
                'product_id': subcontracted_service.id,
                'product_uom_qty': 1.00,
            })],
        })
        so.action_confirm()
        po = so._get_purchase_orders()
        self.assertTrue(po)

        po.order_line = [(0, 0, {
            'product_id': self.dropship_product.id,
            'product_qty': 1.00,
            'product_uom_id': self.dropship_product.uom_id.id,
        })]
        po.button_confirm()
        dropship = po.picking_ids
        self.assertTrue(dropship.is_dropship)
        self.assertRecordValues(dropship.move_ids, [
            {'product_id': self.dropship_product.id, 'partner_id': delivery_addr.id},
        ])

        dropship.move_ids.quantity = 1
        dropship.button_validate()
        self.assertEqual(dropship.state, 'done')
        self.assertRecordValues(so.order_line, [
            {'product_id': subcontracted_service.id, 'product_uom_qty': 1.0, 'qty_delivered': 0.0},
            {'product_id': self.dropship_product.id, 'product_uom_qty': 0.0, 'qty_delivered': 1.0},
        ])
