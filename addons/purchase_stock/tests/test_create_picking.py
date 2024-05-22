# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.product.tests import common
from odoo.tests import Form
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class TestCreatePicking(common.TestProductCommon):

    def setUp(self):
        super(TestCreatePicking, self).setUp()
        self.partner_id = self.env['res.partner'].create({'name': 'Wood Corner Partner'})
        self.product_id_1 = self.env['product.product'].create({'name': 'Large Desk'})
        self.product_id_2 = self.env['product.product'].create({'name': 'Conference Chair'})

        self.user_purchase_user = mail_new_test_user(
            self.env,
            name='Pauline Poivraisselle',
            login='pauline',
            email='pur@example.com',
            notification_type='inbox',
            groups='purchase.group_purchase_user',
        )

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
        for ml in self.picking.move_line_ids:
            ml.qty_done = ml.product_uom_qty
        self.picking._action_done()
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
        self.env.company.write({'po_double_validation': 'two_step','po_double_validation_amount':2000.00})

        # Draft purchase order created
        self.po = self.env['purchase.order'].with_user(self.user_purchase_user).create(self.po_vals)
        self.assertTrue(self.po, 'Purchase: no purchase order created')

        # Purchase order confirm
        self.po.button_confirm()
        self.assertEqual(self.po.state, 'to approve', 'Purchase: PO state should be "to approve".')

        # PO approved by manager
        self.po.env.user.groups_id += self.env.ref("purchase.group_purchase_manager")
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
            'route_ids': [(4, self.ref('stock.route_warehouse0_mto')), (4, self.ref('purchase_stock.route_warehouse0_buy'))],
            'seller_ids': [(6, 0, [seller.id])],
            'categ_id': self.env.ref('product.product_category_all').id,
            'supplier_taxes_id': [(6, 0, [])],
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
        self.assertEqual(purchase_order_line.price_unit, seller.price, 'The purchase order line price should be the same as the seller.')
        self.assertEqual(purchase_order_line.product_qty, customer_move.product_uom_qty, 'The purchase order line qty should be the same as the move.')
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

        # mts move will be automatically assigned
        self.assertEqual(customer_move.state, 'assigned', 'Automatically assigned due to the incoming move makes it available.')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product, stock_location), 0.0, 'Wrong quantity in stock.')

    def test_03_uom(self):
        """ Buy a dozen of products stocked in units. Check that the quantities on the purchase order
        lines as well as the received quantities are handled in dozen while the moves themselves
        are handled in units. Edit the ordered quantities, check that the quantites are correctly
        updated on the moves. Edit the ir.config_parameter to propagate the uom of the purchase order
        lines to the moves and edit a last time the ordered quantities. Receive, check the quantities.
        """
        uom_unit = self.env.ref('uom.product_uom_unit')
        uom_dozen = self.env.ref('uom.product_uom_dozen')

        self.assertEqual(self.product_id_1.uom_po_id.id, uom_unit.id)

        # buy a dozen
        po = self.env['purchase.order'].create(self.po_vals)

        po.order_line.product_qty = 1
        po.order_line.product_uom = uom_dozen.id
        po.button_confirm()

        # the move should be 12 units
        # note: move.product_qty = computed field, always in the uom of the quant
        #       move.product_uom_qty = stored field representing the initial demand in move.product_uom
        move1 = po.picking_ids.move_lines.sorted()[0]
        self.assertEqual(move1.product_uom_qty, 12)
        self.assertEqual(move1.product_uom.id, uom_unit.id)
        self.assertEqual(move1.product_qty, 12)

        # edit the so line, sell 2 dozen, the move should now be 24 units
        po.order_line.product_qty = 2
        move1 = po.picking_ids.move_lines.sorted()[0]
        self.assertEqual(move1.product_uom_qty, 24)
        self.assertEqual(move1.product_uom.id, uom_unit.id)
        self.assertEqual(move1.product_qty, 24)

        # force the propagation of the uom, sell 3 dozen
        self.env['ir.config_parameter'].sudo().set_param('stock.propagate_uom', '1')
        po.order_line.product_qty = 3
        move2 = po.picking_ids.move_lines.filtered(lambda m: m.product_uom.id == uom_dozen.id)
        self.assertEqual(move2.product_uom_qty, 1)
        self.assertEqual(move2.product_uom.id, uom_dozen.id)
        self.assertEqual(move2.product_qty, 12)

        # deliver everything
        move1.quantity_done = 24
        move2.quantity_done = 1
        po.picking_ids.button_validate()

        # check the delivered quantity
        self.assertEqual(po.order_line.qty_received, 3.0)

    def test_04_mto_multiple_po(self):
        """ Simulate a mto chain with 2 purchase order.
        Create a move with qty 1, confirm the RFQ then create a new
        move that will not be merged in the first one(simulate an increase
        order quantity on a SO). It should generate a new RFQ, validate
        and receipt the picking then try to reserve the delivery
        picking.
        """
        stock_location = self.env['ir.model.data'].xmlid_to_object('stock.stock_location_stock')
        customer_location = self.env['ir.model.data'].xmlid_to_object('stock.stock_location_customers')
        picking_type_out = self.env['ir.model.data'].xmlid_to_object('stock.picking_type_out')
        # route buy should be there by default
        partner = self.env['res.partner'].create({
            'name': 'Jhon'
        })

        seller = self.env['product.supplierinfo'].create({
            'name': partner.id,
            'price': 12.0,
        })

        product = self.env['product.product'].create({
            'name': 'product',
            'type': 'product',
            'route_ids': [(4, self.ref('stock.route_warehouse0_mto')), (4, self.ref('purchase_stock.route_warehouse0_buy'))],
            'seller_ids': [(6, 0, [seller.id])],
            'categ_id': self.env.ref('product.product_category_all').id,
        })

        # A picking is require since only moves inside the same picking are merged.
        customer_picking = self.env['stock.picking'].create({
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'partner_id': partner.id,
            'picking_type_id': picking_type_out.id,
        })

        customer_move = self.env['stock.move'].create({
            'name': 'move out',
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 80.0,
            'procure_method': 'make_to_order',
            'picking_id': customer_picking.id,
        })

        customer_move._action_confirm()

        purchase_order = self.env['purchase.order'].search([('partner_id', '=', partner.id)])
        self.assertTrue(purchase_order, 'No purchase order created.')

        # Check purchase order line data.
        purchase_order_line = purchase_order.order_line
        self.assertEqual(purchase_order_line.product_id, product, 'The product on the purchase order line is not correct.')
        self.assertEqual(purchase_order_line.price_unit, seller.price, 'The purchase order line price should be the same as the seller.')
        self.assertEqual(purchase_order_line.product_qty, customer_move.product_uom_qty, 'The purchase order line qty should be the same as the move.')

        purchase_order.button_confirm()

        customer_move_2 = self.env['stock.move'].create({
            'name': 'move out',
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 20.0,
            'procure_method': 'make_to_order',
            'picking_id': customer_picking.id,
        })

        customer_move_2._action_confirm()

        self.assertTrue(customer_move_2.exists(), 'The second customer move should not be merged in the first.')
        self.assertEqual(sum(customer_picking.move_lines.mapped('product_uom_qty')), 100.0)

        purchase_order_2 = self.env['purchase.order'].search([('partner_id', '=', partner.id), ('state', '=', 'draft')])
        self.assertTrue(purchase_order_2, 'No purchase order created.')

        purchase_order_2.button_confirm()

        purchase_order.picking_ids.move_lines.quantity_done = 80.0
        purchase_order.picking_ids.button_validate()

        purchase_order_2.picking_ids.move_lines.quantity_done = 20.0
        purchase_order_2.picking_ids.button_validate()

        self.assertEqual(sum(customer_picking.move_lines.mapped('reserved_availability')), 100.0, 'The total quantity for the customer move should be available and reserved.')

    def test_04_rounding(self):
        """ We set the Unit(s) rounding to 1.0 and ensure buying 1.2 units in a PO is rounded to 1.0
            at reception.
        """
        uom_unit = self.env.ref('uom.product_uom_unit')
        uom_unit.rounding = 1.0

        # buy a dozen
        po = self.env['purchase.order'].create(self.po_vals)

        po.order_line.product_qty = 1.2
        po.button_confirm()

        # the move should be 1.0 units
        move1 = po.picking_ids.move_lines[0]
        self.assertEqual(move1.product_uom_qty, 1.0)
        self.assertEqual(move1.product_uom.id, uom_unit.id)
        self.assertEqual(move1.product_qty, 1.0)

        # edit the so line, buy 2.4 units, the move should now be 2.0 units
        po.order_line.product_qty = 2.0
        self.assertEqual(move1.product_uom_qty, 2.0)
        self.assertEqual(move1.product_uom.id, uom_unit.id)
        self.assertEqual(move1.product_qty, 2.0)

        # deliver everything
        move1.quantity_done = 2.0
        po.picking_ids.button_validate()

        # check the delivered quantity
        self.assertEqual(po.order_line.qty_received, 2.0)

    def test_05_uom_rounding(self):
        """ We set the Unit(s) and Dozen(s) rounding to 1.0 and ensure buying 1.3 dozens in a PO is
            rounded to 1.0 at reception.
        """
        uom_unit = self.env.ref('uom.product_uom_unit')
        uom_dozen = self.env.ref('uom.product_uom_dozen')
        uom_unit.rounding = 1.0
        uom_dozen.rounding = 1.0

        # buy 1.3 dozen
        po = self.env['purchase.order'].create(self.po_vals)

        po.order_line.product_qty = 1.3
        po.order_line.product_uom = uom_dozen.id
        po.button_confirm()

        # the move should be 16.0 units
        move1 = po.picking_ids.move_lines[0]
        self.assertEqual(move1.product_uom_qty, 16.0)
        self.assertEqual(move1.product_uom.id, uom_unit.id)
        self.assertEqual(move1.product_qty, 16.0)

        # force the propagation of the uom, buy 2.6 dozens, the move 2 should have 2 dozens
        self.env['ir.config_parameter'].sudo().set_param('stock.propagate_uom', '1')
        po.order_line.product_qty = 2.6
        move2 = po.picking_ids.move_lines.filtered(lambda m: m.product_uom.id == uom_dozen.id)
        self.assertEqual(move2.product_uom_qty, 2)
        self.assertEqual(move2.product_uom.id, uom_dozen.id)
        self.assertEqual(move2.product_qty, 24)

    def create_delivery_order(self):
        stock_location = self.env['ir.model.data'].xmlid_to_object('stock.stock_location_stock')
        customer_location = self.env['ir.model.data'].xmlid_to_object('stock.stock_location_customers')
        unit = self.ref("uom.product_uom_unit")
        picking_type_out = self.env['ir.model.data'].xmlid_to_object('stock.picking_type_out')
        partner = self.env['res.partner'].create({'name': 'AAA', 'email': 'from.test@example.com'})
        supplier_info1 = self.env['product.supplierinfo'].create({
            'name': partner.id,
            'price': 50,
        })

        warehouse1 = self.env.ref('stock.warehouse0')
        route_buy = warehouse1.buy_pull_id.route_id
        route_mto = warehouse1.mto_pull_id.route_id

        product = self.env['product.product'].create({
            'name': 'Usb Keyboard',
            'type': 'product',
            'uom_id': unit,
            'uom_po_id': unit,
            'seller_ids': [(6, 0, [supplier_info1.id])],
            'route_ids': [(6, 0, [route_buy.id, route_mto.id])]
        })

        delivery_order = self.env['stock.picking'].create({
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'partner_id': partner.id,
            'picking_type_id': picking_type_out.id,
        })

        customer_move = self.env['stock.move'].create({
            'name': 'move out',
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 10.0,
            'procure_method': 'make_to_order',
            'picking_id': delivery_order.id,
        })

        customer_move._action_confirm()
        # find created po the product
        purchase_order = self.env['purchase.order'].search([('partner_id', '=', partner.id)])

        return delivery_order, purchase_order

    def test_05_propagate_deadline(self):
        """ In order to check deadline date of the delivery order is changed and the planned date not."""

        # Create Delivery Order and with propagate date and minimum delta
        delivery_order, purchase_order = self.create_delivery_order()

        # check po is created or not
        self.assertTrue(purchase_order, 'No purchase order created.')

        purchase_order_line = purchase_order.order_line

        # change scheduled date of po line.
        purchase_order_line.write({'date_planned': purchase_order_line.date_planned + timedelta(days=5)})

        # Now check scheduled date and deadline of delivery order.
        self.assertNotEqual(
            purchase_order_line.date_planned, delivery_order.scheduled_date,
            'Scheduled delivery order date should not changed.')
        self.assertEqual(
            purchase_order_line.date_planned, delivery_order.date_deadline,
            'Delivery deadline date should be changed.')

    def test_07_differed_schedule_date(self):
        warehouse = self.env['stock.warehouse'].search([], limit=1)

        with Form(warehouse) as w:
            w.reception_steps = 'three_steps'
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as line:
            line.product_id = self.product_id_1
            line.date_planned = datetime.today()
            line.product_qty = 1.0
        with po_form.order_line.new() as line:
            line.product_id = self.product_id_1
            line.date_planned = datetime.today() + timedelta(days=7)
            line.product_qty = 1.0
        po = po_form.save()

        po.button_approve()

        po.picking_ids.move_line_ids.write({
            'qty_done': 1.0
        })
        po.picking_ids.button_validate()

        pickings = self.env['stock.picking'].search([('group_id', '=', po.group_id.id)])
        for picking in pickings:
            self.assertEqual(picking.scheduled_date.date(), date.today())

    def test_update_quantity_and_return(self):
        po = self.env['purchase.order'].create(self.po_vals)

        po.order_line.product_qty = 10
        po.button_confirm()

        first_picking = po.picking_ids
        first_picking.move_lines.quantity_done = 5
        # create the backorder
        backorder_wizard_dict = first_picking.button_validate()
        backorder_wizard = Form(self.env[backorder_wizard_dict['res_model']].with_context(backorder_wizard_dict['context'])).save()
        backorder_wizard.process()

        self.assertEqual(len(po.picking_ids), 2)

        # Create a partial return
        stock_return_picking_form = Form(
            self.env['stock.return.picking'].with_context(
                active_ids=first_picking.ids,
                active_id=first_picking.ids[0],
                active_model='stock.picking'
            )
        )
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 2.0
        stock_return_picking_action = stock_return_picking.create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_pick.action_assign()
        return_pick.move_lines.quantity_done = 2
        return_pick._action_done()

        self.assertEqual(po.order_line.qty_received, 3)

        po.order_line.product_qty += 2
        backorder = po.picking_ids.filtered(lambda picking: picking.state == 'assigned')
        self.assertEqual(backorder.move_lines.product_uom_qty, 9)
