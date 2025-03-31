# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import fields, Command
from odoo.tests import Form
from odoo.addons.purchase_stock.tests.common import PurchaseTestCommon


class TestPurchaseOldRules(PurchaseTestCommon):

    def create_picking_out(self, warehouse):
        customer_location = self.env.ref('stock.stock_location_customers')
        picking_out = self.env['stock.picking'].create({
            'location_id': warehouse.out_type_id.default_location_src_id.id,
            'location_dest_id': customer_location.id,
            'partner_id': self.customer.id,
            'group_id': self.group.id,
            'picking_type_id': warehouse.out_type_id.id,
        })
        self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 10,
            'product_uom': self.product.uom_id.id,
            'picking_id': picking_out.id,
            'group_id': self.group.id,
            'location_id': warehouse.out_type_id.default_location_src_id.id,
            'location_dest_id': customer_location.id,
            'procure_method': 'make_to_order',
        })
        return picking_out

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env['res.partner'].create({'name': 'abc'})
        cls.group = cls.env['procurement.group'].create({'partner_id': cls.customer.id, 'name': 'New Group'})
        cls.product = cls.env['product.product'].create({
            'name': 'Geyser',
            'is_storable': True,
            'route_ids': [Command.link(cls.route_mto), Command.link(cls.route_buy)],
            'seller_ids': [Command.create({
                'partner_id': cls.customer.id,
                'price': 100.0,
            })],
        })

        # Since the old rules are still a valid setup for multi-step routes, we need to make sure they still work.
        # Create a warehouse with 3 steps using old rules setup so we need to restore it only once.
        mto_route = cls.env['stock.route'].browse(cls.route_mto)
        buy_route = cls.env['stock.route'].browse(cls.route_buy)
        cls.warehouse_3_steps = cls.env['stock.warehouse'].create({
            'name': 'Warehouse 3 steps',
            'code': '3S',
            'reception_steps': 'three_steps',
            'delivery_steps': 'pick_pack_ship',
        })
        delivery_route_3 = cls.warehouse_3_steps.delivery_route_id
        delivery_route_3.rule_ids[0].write({
            'location_dest_id': delivery_route_3.rule_ids[1].location_src_id.id,
        })
        delivery_route_3.rule_ids[1].write({'action': 'pull'})
        delivery_route_3.rule_ids[2].write({'action': 'pull'})
        mto_route.rule_ids.filtered(lambda r: r.picking_type_id == cls.warehouse_3_steps.pick_type_id).write({
            'location_dest_id': delivery_route_3.rule_ids[1].location_src_id.id,
        })
        reception_route_3 = cls.warehouse_3_steps.reception_route_id
        reception_route_3.rule_ids[0].write({'action': 'pull_push'})
        reception_route_3.rule_ids[1].write({'action': 'pull_push'})
        buy_route.rule_ids.filtered(lambda r: r.picking_type_id == cls.warehouse_3_steps.in_type_id).write({
            'location_dest_id': reception_route_3.rule_ids[0].location_src_id.id,
        })

        # Create a warehouse with 2 steps using old rules setup.
        cls.warehouse_2_steps = cls.env['stock.warehouse'].create({
            'name': 'Warehouse 2 steps',
            'code': '2S',
            'reception_steps': 'two_steps',
            'delivery_steps': 'pick_ship',
        })
        delivery_route_2 = cls.warehouse_2_steps.delivery_route_id
        delivery_route_2.rule_ids[0].write({
            'location_dest_id': delivery_route_2.rule_ids[1].location_src_id.id,
        })
        delivery_route_2.rule_ids[1].write({'action': 'pull'})
        mto_route.rule_ids.filtered(lambda r: r.picking_type_id == cls.warehouse_2_steps.pick_type_id).write({
            'location_dest_id': delivery_route_2.rule_ids[1].location_src_id.id,
        })
        reception_route_2 = cls.warehouse_2_steps.reception_route_id
        reception_route_2.rule_ids[0].write({'action': 'pull_push'})
        buy_route.rule_ids.filtered(lambda r: r.picking_type_id == cls.warehouse_2_steps.in_type_id).write({
            'location_dest_id': reception_route_2.rule_ids[0].location_src_id.id,
        })

    def test_03_cancel_draft_purchase_order_two_steps_pull(self):
        """ Check the picking and moves status related PO, When canceling purchase order
            in 'draft' state.
            Ex.
                1) Set two steps of receiption and delivery on the warehouse.
                2) Create Delivery order with mto move and confirm the order, related RFQ should be generated.
                3) Cancel 'draft' purchase order should cancel < Input to Stock>
                  but it should not cancel < PICK, Delivery >
        """
        picking_out = self.create_picking_out(self.warehouse_2_steps)
        picking_out.action_confirm()

        # Find purchase order related to picking.
        purchase_order = self.env['purchase.order'].search([('partner_id', '=', self.customer.id)])
        # Purchase order should be created for picking.
        self.assertTrue(purchase_order, 'No purchase order created.')

        picking_ids = self.env['stock.picking'].search([('group_id', '=', self.group.id)])

        storage = picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_2_steps.store_type_id and r.group_id.id == self.group.id)
        pick = picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_2_steps.pick_type_id and r.group_id.id == self.group.id)

        # Check status of Purchase Order
        self.assertEqual(purchase_order.state, 'draft', "Purchase order should be in 'draft' state.")
        # Cancel Purchase order.
        purchase_order.button_cancel()

        # Check the status of picking after canceling po.
        for res in storage:
            self.assertEqual(res.state, 'cancel')
        self.assertNotEqual(pick.state, 'cancel')
        self.assertNotEqual(picking_out.state, 'cancel')

    def test_04_cancel_confirm_purchase_order_two_steps_pull(self):
        """ Check the picking and moves status related PO, When canceling purchase order
            Ex.
                1) Set 2 steps of receiption and delivery on the warehouse.
                2) Create Delivery order with mto move and confirm the order, related RFQ should be generated.
                3) Cancel 'confirm' purchase order should cancel releted < Receiption Picking IN, STOR>
                  not < PICK, SHIP >
        """
        picking_out = self.create_picking_out(self.warehouse_2_steps)
        picking_out.action_confirm()

        # Find PO related to picking.
        purchase_order = self.env['purchase.order'].search([('partner_id', '=', self.customer.id)])
        # Po should be create related picking.
        self.assertTrue(purchase_order, 'purchase order is created.')

        picking_ids = self.env['stock.picking'].search([('group_id', '=', self.group.id)])

        internal = picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_2_steps.int_type_id)
        pick = picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_2_steps.pick_type_id)

        # Check status of Purchase Order
        self.assertEqual(purchase_order.state, 'draft', "Purchase order should be in 'draft' state.")

        purchase_order.button_confirm()
        picking_in = purchase_order.picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_2_steps.in_type_id)
        # Cancel Purchase order.
        purchase_order.button_cancel()

        # Check the status of picking after canceling po.
        self.assertEqual(picking_in.state, 'cancel')
        for res in internal:
            self.assertEqual(res.state, 'cancel')
        self.assertNotEqual(pick.state, 'cancel')
        self.assertNotEqual(picking_out.state, 'cancel')

    def test_05_cancel_draft_purchase_order_three_steps_pull(self):
        """ Check the picking and moves status related PO, When canceling purchase order
            Ex.
                1) Set 3 steps of receiption and delivery on the warehouse.
                2) Create Delivery order with mto move and confirm the order, related RFQ should be generated.
                3) Cancel 'draft' purchase order should cancel releted < Receiption Picking  IN>
                  not < PICK, PACK, SHIP >
        """
        picking_out = self.create_picking_out(self.warehouse_3_steps)
        picking_out.action_confirm()
        # Find PO related to picking.
        purchase_order = self.env['purchase.order'].search([('partner_id', '=', self.customer.id)])
        # Po should be create related picking.
        self.assertTrue(purchase_order, 'No purchase order created.')

        picking_ids = self.env['stock.picking'].search([('group_id', '=', self.group.id)])

        internal = picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_3_steps.int_type_id)
        pick = picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_3_steps.pick_type_id)
        pack = picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_3_steps.pack_type_id)

        # Check status of Purchase Order
        self.assertEqual(purchase_order.state, 'draft', "Purchase order should be in 'draft' state.")
        # Cancel Purchase order.
        purchase_order.button_cancel()

        # Check the status of picking after canceling po.
        for res in internal:
            self.assertEqual(res.state, 'cancel')
        self.assertNotEqual(pick.state, 'cancel')
        self.assertNotEqual(pack.state, 'cancel')
        self.assertNotEqual(picking_out.state, 'cancel')

    def test_06_cancel_confirm_purchase_order_three_steps_pull(self):
        """ Check the picking and moves status related PO, When canceling purchase order
            Ex.
                1) Set 3 steps of receiption and delivery on the warehouse.
                2) Create Delivery order with mto move and confirm the order, related RFQ should be generated.
                3) Cancel 'comfirm' purchase order should cancel releted < Receiption Picking IN, INT>
                  not < PICK, PACK, SHIP >
        """
        picking_out = self.create_picking_out(self.warehouse_3_steps)
        picking_out.action_confirm()

        # Find PO related to picking.
        purchase_order = self.env['purchase.order'].search([('partner_id', '=', self.customer.id)])
        # Po should be create related picking.
        self.assertTrue(purchase_order, 'No purchase order created.')

        picking_ids = self.env['stock.picking'].search([('group_id', '=', self.group.id)])

        internal = picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_3_steps.int_type_id)
        pick = picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_3_steps.pick_type_id)
        pack = picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_3_steps.pack_type_id)

        # Check status of Purchase Order
        self.assertEqual(purchase_order.state, 'draft', "Purchase order should be in 'draft' state.")

        purchase_order.button_confirm()
        picking_in = purchase_order.picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_3_steps.in_type_id)
        # Cancel Purchase order.
        purchase_order.button_cancel()

        # Check the status of picking after canceling po.
        self.assertEqual(picking_in.state, 'cancel')
        for res in internal:
            self.assertEqual(res.state, 'cancel')
        self.assertNotEqual(pick.state, 'cancel')
        self.assertNotEqual(pack.state, 'cancel')
        self.assertNotEqual(picking_out.state, 'cancel')

    def test_02_product_route_level_delays(self):
        """ In order to check dates, set product's Delivery Lead Time
            and warehouse route's delay."""

        company = self.env.ref('base.main_company')
        company.write({'po_lead': 1.00})

        warehouse = self.warehouse_3_steps
        # Set delay on push rule
        for push_rule in warehouse.reception_route_id.rule_ids:
            push_rule.write({'delay': 2})

        rule_delay = sum(warehouse.reception_route_id.rule_ids.mapped('delay'))
        date_planned = fields.Datetime.now() + timedelta(days=10)
        # Create procurement order of product_1
        self.env['procurement.group'].run([self.env['procurement.group'].Procurement(
            self.product_1, 5.000, self.uom_unit, warehouse.lot_stock_id, 'Test scheduler for RFQ', '/', self.env.company,
            {
                'warehouse_id': warehouse,
                'date_planned': date_planned,  # 10 days added to current date of procurement to get future schedule date and order date of purchase order.
                'date_deadline': date_planned,  # 10 days added to current date of procurement to get future schedule date and order date of purchase order.
                'rule_id': warehouse.buy_pull_id,
                'group_id': False,
                'route_ids': [],
            }
        )])

        # Confirm purchase order
        purchase = self.env['purchase.order.line'].search([('product_id', '=', self.product_1.id)], limit=1).order_id
        purchase.button_confirm()
        # Check order date of purchase order
        order_date = date_planned - timedelta(days=self.product_1.seller_ids.delay + rule_delay)
        self.assertEqual(purchase.date_order, order_date, 'Order date should be equal to: Date of the procurement order - Delivery Lead Time(supplier and pull rules).')

        # Check scheduled date of purchase order
        schedule_date = order_date + timedelta(days=self.product_1.seller_ids.delay + rule_delay)
        self.assertEqual(date_planned, schedule_date, 'Schedule date should be equal to: Order date of Purchase order + Delivery Lead Time(supplier and pull rules).')

        # Check the picking crated or not
        self.assertTrue(purchase.picking_ids, "Picking should be created.")

        # Check scheduled date of Internal Type shipment
        incoming_shipment1 = self.env['stock.picking'].search([('move_ids.product_id', 'in', (self.product_1.id, self.product_2.id)), ('picking_type_id', '=', warehouse.qc_type_id.id), ('location_id', '=', warehouse.wh_input_stock_loc_id.id), ('location_dest_id', '=', warehouse.wh_qc_stock_loc_id.id)])
        incoming_shipment1_date = order_date + timedelta(days=self.product_1.seller_ids.delay)
        self.assertEqual(incoming_shipment1.scheduled_date, incoming_shipment1_date, 'Schedule date of Internal Type shipment for input stock location should be equal to: schedule date of purchase order + push rule delay.')
        self.assertEqual(incoming_shipment1.date_deadline, incoming_shipment1_date)
        old_deadline1 = incoming_shipment1.date_deadline

        incoming_shipment2 = self.env['stock.picking'].search([('picking_type_id', '=', warehouse.store_type_id.id), ('location_id', '=', warehouse.wh_qc_stock_loc_id.id), ('location_dest_id', '=', warehouse.lot_stock_id.id)])
        incoming_shipment2_date = schedule_date - timedelta(days=incoming_shipment2.move_ids[0].rule_id.delay)
        self.assertEqual(incoming_shipment2.scheduled_date, incoming_shipment2_date, 'Schedule date of Internal Type shipment for quality control stock location should be equal to: schedule date of Internal type shipment for input stock location + push rule delay..')
        self.assertEqual(incoming_shipment2.date_deadline, incoming_shipment2_date)
        old_deadline2 = incoming_shipment2.date_deadline

        # Modify the date_planned of the purchase -> propagate the deadline
        purchase_form = Form(purchase)
        purchase_form.date_planned = purchase.date_planned + timedelta(days=1)
        purchase_form.save()
        self.assertEqual(incoming_shipment2.date_deadline, old_deadline2 + timedelta(days=1), 'Deadline should be propagate')
        self.assertEqual(incoming_shipment1.date_deadline, old_deadline1 + timedelta(days=1), 'Deadline should be propagate')
