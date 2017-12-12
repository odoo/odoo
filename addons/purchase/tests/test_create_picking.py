# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.addons.product.tests import common


class TestCreatePicking(common.TestProductCommon):

    def setUp(self):
        super(TestCreatePicking, self).setUp()
        self.partner_id = self.env.ref('base.res_partner_1')
        self.product_id_1 = self.env.ref('product.product_product_8')
        self.product_id_2 = self.env.ref('product.product_product_11')
        res_users_purchase_user = self.env.ref('purchase.group_purchase_user')

        Users = self.env['res.users'].with_context({'no_reset_password': True, 'mail_create_nosubscribe': True})
        self.user_purchase_user = Users.create({
            'name': 'Pauline Poivraisselle',
            'login': 'pauline',
            'email': 'pur@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [res_users_purchase_user.id])]})

        self.po_vals = {
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product_id_1.name,
                    'product_id': self.product_id_1.id,
                    'product_qty': 5.0,
                    'product_uom': self.product_id_1.uom_po_id.id,
                    'price_unit': 500.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                })],
        }

    def test_00_create_picking(self):

        # Draft purchase order created
        self.po = self.env['purchase.order'].create(self.po_vals)
        self.assertTrue(self.po, 'Purchase: no purchase order created')

        # Purchase order confirm
        self.po.button_confirm()
        self.assertEqual(self.po.state, 'purchase', 'Purchase: PO state should be "Purchase')
        self.assertEqual(self.po.picking_count, 1, 'Purchase: one picking should be created')
        self.assertEqual(len(self.po.order_line.move_ids), 1, 'One move should be created')
        # Change purchase order line product quantity
        self.po.order_line.write({'product_qty': 7.0})
        self.assertEqual(len(self.po.order_line.move_ids), 1, 'The two moves should be merged in one')

        # Validate first shipment
        self.picking = self.po.picking_ids[0]
        self.picking.force_assign()
        for ml in self.picking.move_line_ids:
            ml.qty_done = ml.product_uom_qty
        self.picking.action_done()
        self.assertEqual(self.po.order_line.mapped('qty_received'), [7.0], 'Purchase: all products should be received')
        

        # create new order line
        self.po.write({'order_line': [
            (0, 0, {
                'name': self.product_id_2.name,
                'product_id': self.product_id_2.id,
                'product_qty': 5.0,
                'product_uom': self.product_id_2.uom_po_id.id,
                'price_unit': 250.0,
                'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                })]})
        self.assertEqual(self.po.picking_count, 2, 'New picking should be created')
        moves = self.po.order_line.mapped('move_ids').filtered(lambda x: x.state not in ('done', 'cancel'))
        self.assertEqual(len(moves), 1, 'One moves should have been created')

    def test_01_check_double_validation(self):

        # make double validation two step
        self.env.user.company_id.write({'po_double_validation': 'two_step','po_double_validation_amount':2000.00})

        # Draft purchase order created
        self.po = self.env['purchase.order'].sudo(self.user_purchase_user).create(self.po_vals)
        self.assertTrue(self.po, 'Purchase: no purchase order created')

        # Purchase order confirm
        self.po.button_confirm()
        self.assertEqual(self.po.state, 'to approve', 'Purchase: PO state should be "to approve".')

        # PO approved by manager
        self.po.button_approve()
        self.assertEqual(self.po.state, 'purchase', 'PO state should be "Purchase".')

    def test_02_check_mto_chain(self):
        """ Simulate a mto chain with a purchase order. Cancel the
        purchase order should also change the procure_method of the
        following move to MTS in order to be able to link it to a
        manually created purchase order.
        """
        stock_location = self.env['ir.model.data'].xmlid_to_object('stock.stock_location_stock')
        customer_location = self.env['ir.model.data'].xmlid_to_object('stock.stock_location_customers')
        # route buy should be there by default
        partner = self.env['res.partner'].create({
            'name': 'Jhon'
        })

        vendor = self.env['res.partner'].create({
            'name': 'Roger'
        })

        seller = self.env['product.supplierinfo'].create({
            'name': partner.id,
            'price': 12.0,
        })

        product = self.env['product.product'].create({
            'name': 'product',
            'type': 'product',
            'route_ids': [(4, self.ref('stock.route_warehouse0_mto')), (4, self.ref('purchase.route_warehouse0_buy'))],
            'seller_ids': [(6, 0, [seller.id])],
            'categ_id': self.env.ref('product.product_category_all').id,
        })

        customer_move = self.env['stock.move'].create({
            'name': 'move out',
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 100.0,
            'procure_method': 'make_to_order',
        })

        customer_move._action_confirm()

        purchase_order = self.env['purchase.order'].search([('partner_id', '=', partner.id)])
        self.assertTrue(purchase_order, 'No purchase order created.')

        # Check purchase order line data.
        purchase_order_line = purchase_order.order_line
        self.assertEqual(purchase_order_line.product_id, product, 'The product on the purchase order line is not correct.')
        self.assertEqual(purchase_order_line.price_unit, seller.price, 'The purchase order line price should be the same than the seller.')
        self.assertEqual(purchase_order_line.product_qty, customer_move.product_uom_qty, 'The purchase order line qty should be the same than the move.')
        self.assertEqual(purchase_order_line.price_subtotal, 1200.0, 'The purchase order line subtotal should be equal to the move qty * seller price.')

        purchase_order.button_cancel()
        self.assertEqual(purchase_order.state, 'cancel', 'Purchase order should be cancelled.')
        self.assertEqual(customer_move.procure_method, 'make_to_stock', 'Customer move should be passed to mts.')

        purchase = purchase_order.create({
            'partner_id': vendor.id,
            'order_line': [
                (0, 0, {
                    'name': product.name,
                    'product_id': product.id,
                    'product_qty': 100.0,
                    'product_uom': product.uom_po_id.id,
                    'price_unit': 11.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                })],
        })
        self.assertTrue(purchase, 'RFQ should be created')
        purchase.button_confirm()

        picking = purchase.picking_ids
        self.assertTrue(picking, 'Picking should be created')

        # Process pickings
        picking.action_confirm()
        picking.move_lines.quantity_done = 100.0
        picking.button_validate()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(product, stock_location), 100.0, 'Wrong quantity in stock.')

        customer_move._action_assign()
        self.assertEqual(customer_move.state, 'assigned', 'Reservation should work with the new quantity provided by the PO.')
