# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command

from odoo.tests import common, tagged, Form
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
        po = self.env['purchase.order'].search([('reference_ids', '=', so.stock_reference_ids.id)])
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
        self.dropship_product.description = "internal note"
        self.dropship_product.description_pickingout = "description_out"
        # Required for `route_id` to be visible in the view
        self.env.user.group_ids += self.env.ref('stock.group_adv_location')

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
                line.route_ids = self.dropshipping_route
        sale_order_drp_shpng = so_form.save()

        # Confirm sales order
        sale_order_drp_shpng.action_confirm()

        # Check the sales order created a reference which has a procurement of 200 pieces
        self.assertTrue(sale_order_drp_shpng.stock_reference_ids, 'SO should have procurement group')

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

        # Check description is not the internal note
        self.assertNotEqual(move_line.move_id.description_picking, self.dropship_product.description)
        self.assertEqual(move_line.move_id.description_picking, self.dropship_product.description_pickingout)

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
        """ Check if the partner_id of a `stock.lot` is computed correctly
            in case the delivery is a dropship transfer
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
        sale_order.picking_ids.move_line_ids.lot_id.invalidate_recordset(fnames=['partner_ids'])
        self.assertEqual(sale_order.picking_ids.move_line_ids.lot_id.partner_ids[0], self.customer)

    def test_sol_reserved_qty_wizard_dropship(self):
        """
        Check that the reserved qty wizard related to a sol is computed from
        the PO if the product is dropshipped and check that the linked pol is updated.
        Check that both are again updated when the dropship is returned.
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
        self.assertEqual(purchase_order.order_line.qty_received, 3.0)
        stock_return_picking_form = Form(self.env['stock.return.picking'].with_context(
            active_ids=picking_dropship.ids,
            active_id=picking_dropship.id,
            active_model='stock.picking'
        ))
        return_wiz = stock_return_picking_form.save()
        return_wiz.product_return_moves.quantity = 3
        res = return_wiz.action_create_returns()
        return_picking = self.env['stock.picking'].browse(res['res_id'])
        return_picking.button_validate()
        self.assertEqual(sale_order.order_line.qty_delivered, 0)
        self.assertEqual(purchase_order.order_line.qty_received, 0)

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
        self.env.user.group_ids += self.env.ref('stock.group_adv_location')

        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.customer
        with mute_logger('odoo.tests.common.onchange'):
            with so_form.order_line.new() as line:
                line.product_id = self.dropship_product
                line.product_uom_qty = 1
                line.route_ids = self.dropshipping_route
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
                line.route_ids = self.dropshipping_route
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

    def test_search_lot_partner_from_dropship(self):
        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [Command.create({
                'product_id': self.lot_dropship_product.id,
                'product_uom_qty': 1.0,
            })],
        })
        sale_order.action_confirm()
        purchase_order = sale_order.stock_reference_ids.purchase_ids
        purchase_order.button_confirm()
        dropship_picking = purchase_order.picking_ids
        dropship_picking.move_line_ids.lot_name = 'dropship lot'
        dropship_picking.move_ids.picked = True
        dropship_picking.button_validate()
        action_view_stock_serial_domain = self.customer.action_view_stock_serial()['domain']
        customer_lots = self.env['stock.lot'].search(action_view_stock_serial_domain)
        self.assertEqual(customer_lots, dropship_picking.move_ids.lot_ids)

    def test_delivery_type(self):
        # Create an operation type starting as incoming/internal.
        operation_type = self.env['stock.picking.type'].create({
            "name": "test",
            "sequence_code": "TEST",
            "code": "incoming"
        })

        # Update the code/type to outgoing/delivery.
        operation_type.write({
            "code": "outgoing"
        })

        # Trigger re-computes.
        operation_type.default_location_src_id
        operation_type.default_location_dest_id

        self.assertEqual(operation_type.code, "outgoing")

        # Expect source location to be warehouse's location.
        self.assertEqual(
            operation_type.default_location_src_id,
            operation_type.warehouse_id.lot_stock_id
        )

        # Expect destination location to be customer's location.
        self.assertEqual(
            operation_type.default_location_dest_id,
            self.env.ref('stock.stock_location_customers')
        )

    def test_non_dropship_mtso_unaffected_by_dropship_logic(self):
        '''
        When using MTSO routes, ensure that purchases are only created for the
        difference between stock and SO qty, instead of the full SO qty.
        '''
        # Make delivery default to MTSO
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        warehouse.delivery_route_id.rule_ids.procure_method = 'mts_else_mto'

        product = self.env['product.product'].create({
            'name': 'Super Product',
            'is_storable': "True",
            'lst_price': 100.0,
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'seller_ids': [
                Command.create({
                    'partner_id': self.supplier.id,
                    'price': 4
                }),
            ],
        })
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': product.id,
            'inventory_quantity': 5,
            'location_id': warehouse.lot_stock_id.id,
        }).action_apply_inventory()

        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [Command.create({
                'product_id': product.id,
                'product_uom_qty': 6,
            })],
        })
        sale_order.action_confirm()
        po = sale_order._get_purchase_orders()
        self.assertTrue(po)
        po.button_confirm()
        sale_order.order_line.product_uom_qty = 8
        po = sorted(sale_order._get_purchase_orders(), key=lambda order: order.id)
        self.assertEqual(len(po), 2)
        self.assertEqual(po[1].order_line.product_uom_qty, 2)


@tagged('post_install', '-at_install')
class TestDropshipPostInstall(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.supplier, cls.customer = cls.env['res.partner'].create([
            {'name': 'Vendor Man'},
            {'name': 'Customer Man'},
        ])
        cls.dropship_product = cls.env['product.product'].create({
            'name': 'Dropshipped Product',
            'tracking': 'none',
            'standard_price': 20,
            'invoice_policy': 'delivery',
            'seller_ids': [Command.create({
                'partner_id': cls.supplier.id,
            })],
            'route_ids': [Command.link(cls.env.ref('stock_dropshipping.route_drop_shipping').id)],
        })

    def test_dropshipping_tracked_product(self):
        supplier, customer = self.supplier, self.customer
        product_lot = self.dropship_product
        product_lot.categ_id.property_cost_method = 'standard'
        sale_order = self.env['sale.order'].create({
            'partner_id': customer.id,
            'order_line': [Command.create({
                'product_id': product_lot.id,
                'product_uom_qty': 1,
            })]
        })
        sale_order.action_confirm()
        # Confirm PO
        purchase = self.env['purchase.order'].search([('partner_id', '=', supplier.id)])
        self.assertTrue(purchase, "an RFQ should have been created")
        purchase.button_confirm()
        dropship_picking = sale_order.picking_ids
        dropship_picking.action_confirm()
        with Form(dropship_picking) as picking_form:
            with picking_form.move_ids.new() as move:
                move.product_id = product_lot
                move.quantity = 1
        dropship_picking.button_validate()
        self.assertEqual(dropship_picking.state, 'done')

    def test_return_dropship_vendor_is_other_company(self):
        other_company = self.env['res.company'].create({'name': 'company vendor'})
        product = self.dropship_product
        product.seller_ids.partner_id = other_company.partner_id.id
        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [Command.create({
                'product_id': product.id,
                'product_uom_qty': 2,
            })],
        })
        sale_order.action_confirm()
        purchase_order = sale_order._get_purchase_orders()
        purchase_order.button_confirm()
        dropship_picking = purchase_order.picking_ids
        dropship_picking.move_ids.quantity = 2
        dropship_picking.button_validate()
        self.assertEqual(sale_order.order_line.qty_delivered, 2)
        self.assertEqual(purchase_order.order_line.qty_received, 2)
        stock_return_picking_form = Form(self.env['stock.return.picking'].with_context(
            active_ids=dropship_picking.ids,
            active_id=dropship_picking.id,
            active_model='stock.picking',
        ))
        return_wiz = stock_return_picking_form.save()
        return_wiz.product_return_moves.quantity = 2
        res = return_wiz.action_create_returns()
        return_picking = self.env['stock.picking'].browse(res['res_id'])
        return_picking.button_validate()
        self.assertEqual(sale_order.order_line.qty_delivered, 0)
        self.assertEqual(purchase_order.order_line.qty_received, 0)

    def test_so_cancel_creates_one_activity_on_po(self):
        """
        Create Sale order with dropshipping product, confirm it, confirm the generated
        purchase order, then cancel the sale order. This should create an activity on the
        purchase order.
        """
        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [Command.create({
                'product_id': self.dropship_product.id,
            })],
        })
        sale_order.action_confirm()
        purchase_order = self.env['purchase.order'].search([
            ('origin', '=', sale_order.name)
        ], limit=1)
        purchase_order.button_confirm()
        sale_order._action_cancel()
        self.assertEqual(len(purchase_order.activity_ids), 1)
