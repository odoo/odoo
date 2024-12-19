# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged
from .common import PurchaseTestCommon


class TestMoveCancelPropagation(PurchaseTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env['res.partner'].create({'name': 'abc'})
        cls.group = cls.env['procurement.group'].create({'partner_id': cls.customer.id, 'name': 'New Group'})
        cls.warehouse = cls.warehouse_1
        seller = cls.env['product.supplierinfo'].create({
            'partner_id': cls.customer.id,
            'price': 100.0,
            'company_id': cls.stock_company.id,
        })
        product = cls.env['product.product'].create({
            'name': 'Geyser',
            'is_storable': True,
            'route_ids': [(4, cls.route_mto), (4, cls.route_buy)],
            'seller_ids': [(6, 0, [seller.id])],
        })
        cls.picking_out = cls.env['stock.picking'].create({
            'location_id': cls.warehouse.out_type_id.default_location_src_id.id,
            'location_dest_id': cls.customer_location.id,
            'partner_id': cls.customer.id,
            'group_id': cls.group.id,
            'picking_type_id': cls.picking_type_out.id,
            'company_id': cls.stock_company.id,
        })
        cls.move = cls.env['stock.move'].create({
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 10,
            'product_uom': product.uom_id.id,
            'picking_id': cls.picking_out.id,
            'group_id': cls.group.id,
            'location_id': cls.warehouse.out_type_id.default_location_src_id.id,
            'location_dest_id': cls.customer_location.id,
            'procure_method': 'make_to_order',
            'company_id': cls.stock_company.id,
        })

    def test_01_cancel_draft_purchase_order_one_steps(self):
        """ Check the picking and moves status related PO, When canceling purchase order
            Ex.
                1) Set one steps of receiption and delivery on the warehouse.
                2) Create Delivery order with mto move and confirm the order, related RFQ should be generated.
                3) Cancel 'draft' purchase order should not cancel < Delivery >
        """
        self.warehouse.write({'delivery_steps': 'ship_only', 'reception_steps': 'one_step'})
        self.picking_out.write({'location_id': self.warehouse.out_type_id.default_location_src_id.id})
        self.move.write({'location_id': self.warehouse.out_type_id.default_location_src_id.id})
        self.picking_out.action_confirm()

        # Find PO related to picking.
        purchase_order = self.env['purchase.order'].search([('partner_id', '=', self.customer.id)])

        # Po should be create related picking.
        self.assertTrue(purchase_order, 'No purchase order created.')

        # Check status of Purchase Order
        self.assertEqual(purchase_order.state, 'draft', "Purchase order should be in 'draft' state.")

        # Cancel Purchase order.
        purchase_order.button_cancel()

        # Check the status of picking after canceling po.
        self.assertNotEqual(self.picking_out.state, 'cancel')

    def test_02_cancel_confirm_purchase_order_one_steps(self):
        """ Check the picking and moves status related purchase order, When canceling purchase order
            after confirming.
            Ex.
                1) Set one steps of receiption and delivery on the warehouse.
                2) Create Delivery order with mto move and confirm the order, related RFQ should be generated.
                3) Cancel 'confirmed' purchase order, should cancel releted < Receiption >
                  but it should not cancel < Delivery > order.
        """
        self.warehouse.write({'delivery_steps': 'ship_only', 'reception_steps': 'one_step'})
        self.picking_out.write({'location_id': self.warehouse.out_type_id.default_location_src_id.id})
        self.move.write({'location_id': self.warehouse.out_type_id.default_location_src_id.id})
        self.picking_out.action_confirm()

        # Find PO related to picking.
        purchase_order = self.env['purchase.order'].search([('partner_id', '=', self.customer.id)])
        # Po should be create related picking.
        self.assertTrue(purchase_order, 'No purchase order created.')

        # Check status of Purchase Order
        self.assertEqual(purchase_order.state, 'draft', "Purchase order should be in 'draft' state.")
        purchase_order .button_confirm()
        picking_in = purchase_order.picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse.in_type_id)
        # Cancel Purchase order.
        purchase_order .button_cancel()

        # Check the status of picking after canceling po.
        self.assertEqual(picking_in.state, 'cancel')
        self.assertNotEqual(self.picking_out.state, 'cancel')

    def test_03_cancel_draft_purchase_order_two_steps_push(self):
        """ Check the picking and moves status related PO, When canceling purchase order
            in 'draft' state.
            Ex.
                1) Set two steps of receiption and delivery on the warehouse.
                2) Create Delivery order with mto move and confirm the order, related RFQ should be generated.
                3) Cancel 'draft' purchase order should cancel < Input to Stock>
                  but it should not cancel < PICK, Delivery >
        """
        self.warehouse.write({'delivery_steps': 'pick_ship', 'reception_steps': 'two_steps'})
        self.move.write({
            'picking_id': False,
            'picking_type_id': self.warehouse.pick_type_id.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.warehouse.pick_type_id.default_location_dest_id.id,
            'location_final_id': self.customer_location.id,
        })
        self.move._action_confirm()
        self.assertEqual(self.move.picking_id.state, 'waiting')

        # Find purchase order related to picking.
        purchase_order = self.env['purchase.order'].search([('partner_id', '=', self.customer.id)])
        # Purchase order should be created for picking.
        self.assertTrue(purchase_order, 'No purchase order created.')
        # Check status of Purchase Order
        self.assertEqual(purchase_order.state, 'draft', "Purchase order should be in 'draft' state.")
        # Cancel Purchase order.
        purchase_order.button_cancel()

        # Check the status of picking after canceling po.
        self.assertNotEqual(self.move.picking_id.state, 'cancel')

    def test_04_cancel_confirm_purchase_order_two_steps_push(self):
        """ Check the picking and moves status related PO, When canceling purchase order
            Ex.
                1) Set 2 steps of receiption and delivery on the warehouse.
                2) Create Delivery order with mto move and confirm the order, related RFQ should be generated.
                3) Cancel 'comfirm' purchase order should cancel releted < Receiption Picking IN, INT>
                  not < PICK, SHIP >
        """
        self.warehouse.write({'delivery_steps': 'pick_ship', 'reception_steps': 'two_steps'})
        self.move.write({
            'picking_id': False,
            'picking_type_id': self.warehouse.pick_type_id.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.warehouse.pick_type_id.default_location_dest_id.id,
            'location_final_id': self.customer_location.id,
        })
        self.move._action_confirm()
        self.assertEqual(self.move.picking_id.state, 'waiting')

        # Find PO related to picking.
        purchase_order = self.env['purchase.order'].search([('partner_id', '=', self.customer.id)])
        # Po should be create related picking.
        self.assertTrue(purchase_order, 'purchase order is created.')

        # Check status of Purchase Order
        self.assertEqual(purchase_order.state, 'draft', "Purchase order should be in 'draft' state.")

        purchase_order.button_confirm()
        picking_in = purchase_order.picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse.in_type_id)
        # Cancel Purchase order.
        purchase_order.button_cancel()

        # Check the status of picking after canceling po.
        self.assertEqual(picking_in.state, 'cancel')
        self.assertNotEqual(self.move.picking_id.state, 'cancel')

    def test_05_cancel_draft_purchase_order_three_steps_push(self):
        """ Check the picking and moves status related PO, When canceling purchase order
            Ex.
                1) Set 3 steps of receiption and delivery on the warehouse.
                2) Create Delivery order with mto move and confirm the order, related RFQ should be generated.
                3) Cancel 'draft' purchase order should cancel releted < Receiption Picking  IN>
                  not < PICK, PACK, SHIP >
        """
        self.warehouse.write({'delivery_steps': 'pick_pack_ship', 'reception_steps': 'three_steps'})
        self.move.write({
            'picking_id': False,
            'picking_type_id': self.warehouse.pick_type_id.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.warehouse.pick_type_id.default_location_dest_id.id,
            'location_final_id': self.customer_location.id,
        })
        self.move._action_confirm()
        self.assertEqual(self.move.picking_id.state, 'waiting')

        # Find PO related to picking.
        purchase_order = self.env['purchase.order'].search([('partner_id', '=', self.customer.id)])
        # Po should be create related picking.
        self.assertTrue(purchase_order, 'No purchase order created.')

        # Check status of Purchase Order
        self.assertEqual(purchase_order.state, 'draft', "Purchase order should be in 'draft' state.")
        # Cancel Purchase order.
        purchase_order.button_cancel()

        self.assertNotEqual(self.move.picking_id.state, 'cancel')

    def test_06_cancel_confirm_purchase_order_three_steps_push(self):
        """ Check the picking and moves status related PO, When canceling purchase order
            Ex.
                1) Set 3 steps of receiption and delivery on the warehouse.
                2) Create Delivery order with mto move and confirm the order, related RFQ should be generated.
                3) Cancel 'comfirm' purchase order should cancel releted < Receiption Picking IN, INT>
                  not < PICK, PACK, SHIP >
        """
        self.warehouse.write({'delivery_steps': 'pick_pack_ship', 'reception_steps': 'three_steps'})
        self.move.write({
            'picking_id': False,
            'picking_type_id': self.warehouse.pick_type_id.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.warehouse.pick_type_id.default_location_dest_id.id,
            'location_final_id': self.customer_location.id,
        })
        self.move._action_confirm()
        self.assertEqual(self.move.picking_id.state, 'waiting')

        # Find PO related to picking.
        purchase_order = self.env['purchase.order'].search([('partner_id', '=', self.customer.id)])
        # Po should be create related picking.
        self.assertTrue(purchase_order, 'No purchase order created.')

        # Check status of Purchase Order
        self.assertEqual(purchase_order.state, 'draft', "Purchase order should be in 'draft' state.")

        purchase_order.button_confirm()
        picking_in = purchase_order.picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse.in_type_id)
        # Cancel Purchase order.
        purchase_order.button_cancel()

        # Check the status of picking after canceling po.
        self.assertEqual(picking_in.state, 'cancel')
        self.assertNotEqual(self.move.picking_id.state, 'cancel')

    def test_cancel_move_lines_operation(self):
        """Check for done and cancelled moves. Ensure that the RFQ cancellation
        will not impact the delivery state if it's already cancelled.
        """
        seller = self.env['product.supplierinfo'].with_user(self.user_stock_manager).create({
            'partner_id': self.partner.id,
            'price': 10.0,
        })
        product_car = self.env['product.product'].with_user(self.user_stock_manager).create({
            'name': 'Car',
            'is_storable': True,
            'route_ids': [(4, self.ref('stock.route_warehouse0_mto')), (4, self.ref('purchase_stock.route_warehouse0_buy'))],
            'seller_ids': [(6, 0, [seller.id])],
        })
        customer_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'partner_id': self.partner.id,
            'picking_type_id': self.picking_type_out.id,
        })
        customer_move = self.env['stock.move'].create({
            'name': 'move out',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': product_car.id,
            'product_uom': product_car.uom_id.id,
            'product_uom_qty': 10.0,
            'procure_method': 'make_to_order',
            'picking_id': customer_picking.id,
        })
        customer_move._action_confirm()
        purchase_order = self.env['purchase.order'].search([('partner_id', '=', self.partner.id)])
        customer_move._action_cancel()
        self.assertEqual(customer_move.state, 'cancel', 'Move should be cancelled')
        purchase_order.button_cancel()
        self.assertEqual(customer_move.state, 'cancel', 'State of cancelled and done moves should not change.')
