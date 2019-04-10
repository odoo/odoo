# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock.tests.common import TestStockCommon
from odoo.exceptions import UserError
from odoo.tests import Form


class TestPickShip(TestStockCommon):
    def create_pick_ship(self):
        picking_client = self.env['stock.picking'].create({
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_out,
        })

        dest = self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 10,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking_client.id,
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
            'state': 'waiting',
            'procure_method': 'make_to_order',
        })

        picking_pick = self.env['stock.picking'].create({
            'location_id': self.stock_location,
            'location_dest_id': self.pack_location,
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_out,
        })

        self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 10,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking_pick.id,
            'location_id': self.stock_location,
            'location_dest_id': self.pack_location,
            'move_dest_ids': [(4, dest.id)],
            'state': 'confirmed',
        })
        return picking_pick, picking_client

    def create_pick_pack_ship(self):
        picking_ship = self.env['stock.picking'].create({
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_out,
        })

        ship = self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 1,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking_ship.id,
            'location_id': self.output_location,
            'location_dest_id': self.customer_location,
        })

        picking_pack = self.env['stock.picking'].create({
            'location_id': self.stock_location,
            'location_dest_id': self.pack_location,
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_out,
        })

        pack = self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 1,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking_pack.id,
            'location_id': self.pack_location,
            'location_dest_id': self.output_location,
            'move_dest_ids': [(4, ship.id)],
        })

        picking_pick = self.env['stock.picking'].create({
            'location_id': self.stock_location,
            'location_dest_id': self.pack_location,
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_out,
        })

        self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 1,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking_pick.id,
            'location_id': self.stock_location,
            'location_dest_id': self.pack_location,
            'move_dest_ids': [(4, pack.id)],
            'state': 'confirmed',
        })
        return picking_pick, picking_pack, picking_ship

    def test_mto_moves(self):
        """
            10 in stock, do pick->ship and check ship is assigned when pick is done, then backorder of ship
        """
        picking_pick, picking_client = self.create_pick_ship()
        location = self.env['stock.location'].browse(self.stock_location)

        # make some stock
        self.env['stock.quant']._update_available_quantity(self.productA, location, 10.0)
        picking_pick.action_assign()
        picking_pick.move_lines[0].move_line_ids[0].qty_done = 10.0
        picking_pick.action_done()

        self.assertEqual(picking_client.state, 'assigned', 'The state of the client should be assigned')

        # Now partially transfer the ship
        picking_client.move_lines[0].move_line_ids[0].qty_done = 5
        picking_client.action_done() # no new in order to create backorder

        backorder = self.env['stock.picking'].search([('backorder_id', '=', picking_client.id)])
        self.assertEqual(backorder.state, 'assigned', 'Backorder should be started')

    def test_mto_moves_transfer(self):
        """
            10 in stock, 5 in pack.  Make sure it does not assign the 5 pieces in pack
        """
        picking_pick, picking_client = self.create_pick_ship()
        stock_location = self.env['stock.location'].browse(self.stock_location)
        self.env['stock.quant']._update_available_quantity(self.productA, stock_location, 10.0)
        pack_location = self.env['stock.location'].browse(self.pack_location)
        self.env['stock.quant']._update_available_quantity(self.productA, pack_location, 5.0)

        self.assertEqual(len(self.env['stock.quant']._gather(self.productA, stock_location)), 1.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.productA, pack_location)), 1.0)

        (picking_pick + picking_client).action_assign()

        move_pick = picking_pick.move_lines
        move_cust = picking_client.move_lines
        self.assertEqual(move_pick.state, 'assigned')
        self.assertEqual(picking_pick.state, 'assigned')
        self.assertEqual(move_cust.state, 'waiting')
        self.assertEqual(picking_client.state, 'waiting', 'The picking should not assign what it does not have')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, stock_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, pack_location), 5.0)

        move_pick.move_line_ids[0].qty_done = 10.0
        picking_pick.action_done()

        self.assertEqual(move_pick.state, 'done')
        self.assertEqual(picking_pick.state, 'done')
        self.assertEqual(move_cust.state, 'assigned')
        self.assertEqual(picking_client.state, 'assigned', 'The picking should not assign what it does not have')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, stock_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, pack_location), 5.0)
        self.assertEqual(sum(self.env['stock.quant']._gather(self.productA, stock_location).mapped('quantity')), 0.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.productA, pack_location)), 1.0)

    def test_mto_moves_return(self):
        picking_pick, picking_client = self.create_pick_ship()
        stock_location = self.env['stock.location'].browse(self.stock_location)
        self.env['stock.quant']._update_available_quantity(self.productA, stock_location, 10.0)

        picking_pick.action_assign()
        picking_pick.move_lines[0].move_line_ids[0].qty_done = 10.0
        picking_pick.action_done()
        self.assertEqual(picking_pick.state, 'done')
        self.assertEqual(picking_client.state, 'assigned')

        # return a part of what we've done
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=picking_pick.ids, active_id=picking_pick.ids[0],
            active_model='stock.picking'))
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 2.0  # Return only 2
        stock_return_picking_action = stock_return_picking.create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_pick.move_lines[0].move_line_ids[0].qty_done = 2.0
        return_pick.action_done()
        # the client picking should not be assigned anymore, as we returned partially what we took
        self.assertEqual(picking_client.state, 'confirmed')

    def test_mto_moves_return_extra(self):
        picking_pick, picking_client = self.create_pick_ship()
        stock_location = self.env['stock.location'].browse(self.stock_location)
        self.env['stock.quant']._update_available_quantity(self.productA, stock_location, 10.0)

        picking_pick.action_assign()
        picking_pick.move_lines[0].move_line_ids[0].qty_done = 10.0
        picking_pick.action_done()
        self.assertEqual(picking_pick.state, 'done')
        self.assertEqual(picking_client.state, 'assigned')

        # return more than we've done
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=picking_pick.ids, active_id=picking_pick.ids[0],
            active_model='stock.picking'))
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 12.0 # Return 2 extra
        stock_return_picking_action = stock_return_picking.create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])

        # Verify the extra move has been merged with the original move
        self.assertAlmostEqual(return_pick.move_lines.product_uom_qty, 12.0)
        self.assertAlmostEqual(return_pick.move_lines.quantity_done, 0.0)
        self.assertAlmostEqual(return_pick.move_lines.reserved_availability, 10.0)

    def test_mto_resupply_cancel_ship(self):
        """ This test simulates a pick pack ship with a resupply route
        set. Pick and pack are validated, ship is cancelled. This test
        ensure that new picking are not created from the cancelled
        ship after the scheduler task. The supply route is only set in
        order to make the scheduler run without mistakes (no next
        activity).
        """
        picking_pick, picking_pack, picking_ship = self.create_pick_pack_ship()
        stock_location = self.env['stock.location'].browse(self.stock_location)
        warehouse_1 = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.id)], limit=1)
        warehouse_1.write({'delivery_steps': 'pick_pack_ship'})
        warehouse_2 = self.env['stock.warehouse'].create({
            'name': 'Small Warehouse',
            'code': 'SWH'
        })
        warehouse_1.write({
            'resupply_wh_ids': [(6, 0, [warehouse_2.id])]
        })
        resupply_route = self.env['stock.location.route'].search([('supplier_wh_id', '=', warehouse_2.id), ('supplied_wh_id', '=', warehouse_1.id)])
        self.assertTrue(resupply_route)
        self.productA.write({'route_ids': [(4, resupply_route.id), (4, self.env.ref('stock.route_warehouse0_mto').id)]})

        self.env['stock.quant']._update_available_quantity(self.productA, stock_location, 10.0)

        picking_pick.action_assign()
        picking_pick.move_lines[0].move_line_ids[0].qty_done = 10.0
        picking_pick.action_done()

        picking_pack.action_assign()
        picking_pack.move_lines[0].move_line_ids[0].qty_done = 10.0
        picking_pack.action_done()

        picking_ship.action_cancel()
        picking_ship.move_lines.write({'procure_method': 'make_to_order'})

        self.env['procurement.group'].run_scheduler()
        next_activity = self.env['mail.activity'].search([('res_model', '=', 'product.template'), ('res_id', '=', self.productA.product_tmpl_id.id)])
        self.assertEqual(picking_ship.state, 'cancel')
        self.assertFalse(next_activity, 'If a next activity has been created if means that scheduler failed\
        and the end of this test do not have sense.')
        self.assertEqual(len(picking_ship.move_lines.mapped('move_orig_ids')), 0,
        'Scheduler should not create picking pack and pick since ship has been manually cancelled.')

    def test_no_backorder_1(self):
        """ Check the behavior of doing less than asked in the picking pick and chosing not to
        create a backorder. In this behavior, the second picking should obviously only be able to
        reserve what was brought, but its initial demand should stay the same and the system will
        ask the user will have to consider again if he wants to create a backorder or not.
        """
        picking_pick, picking_client = self.create_pick_ship()
        location = self.env['stock.location'].browse(self.stock_location)

        # make some stock
        self.env['stock.quant']._update_available_quantity(self.productA, location, 10.0)
        picking_pick.action_assign()
        picking_pick.move_lines[0].move_line_ids[0].qty_done = 5.0

        # create a backorder
        picking_pick.action_done()
        picking_pick_backorder = self.env['stock.picking'].search([('backorder_id', '=', picking_pick.id)])
        self.assertEqual(picking_pick_backorder.state, 'assigned')
        self.assertEqual(picking_pick_backorder.move_line_ids.product_qty, 5.0)

        self.assertEqual(picking_client.state, 'assigned')

        # cancel the backorder
        picking_pick_backorder.action_cancel()
        self.assertEqual(picking_client.state, 'assigned')

    def test_edit_done_chained_move(self):
        """ Let’s say two moves are chained: the first is done and the second is assigned.
        Editing the move line of the first move should impact the reservation of the second one.
        """
        picking_pick, picking_client = self.create_pick_ship()
        location = self.env['stock.location'].browse(self.stock_location)

        # make some stock
        self.env['stock.quant']._update_available_quantity(self.productA, location, 10.0)
        picking_pick.action_assign()
        picking_pick.move_lines[0].move_line_ids[0].qty_done = 10.0
        picking_pick.action_done()

        self.assertEqual(picking_pick.state, 'done', 'The state of the pick should be done')
        self.assertEqual(picking_client.state, 'assigned', 'The state of the client should be assigned')
        self.assertEqual(picking_pick.move_lines.quantity_done, 10.0, 'Wrong quantity_done for pick move')
        self.assertEqual(picking_client.move_lines.product_qty, 10.0, 'Wrong initial demand for client move')
        self.assertEqual(picking_client.move_lines.reserved_availability, 10.0, 'Wrong quantity already reserved for client move')

        picking_pick.move_lines[0].move_line_ids[0].qty_done = 5.0
        self.assertEqual(picking_pick.state, 'done', 'The state of the pick should be done')
        self.assertEqual(picking_client.state, 'assigned', 'The state of the client should be partially available')
        self.assertEqual(picking_pick.move_lines.quantity_done, 5.0, 'Wrong quantity_done for pick move')
        self.assertEqual(picking_client.move_lines.product_qty, 10.0, 'Wrong initial demand for client move')
        self.assertEqual(picking_client.move_lines.reserved_availability, 5.0, 'Wrong quantity already reserved for client move')

        # Check if run action_assign does not crash
        picking_client.action_assign()

    def test_edit_done_chained_move_with_lot(self):
        """ Let’s say two moves are chained: the first is done and the second is assigned.
        Editing the lot on the move line of the first move should impact the reservation of the second one.
        """
        self.productA.tracking = 'lot'
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.productA.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.productA.id,
        })
        picking_pick, picking_client = self.create_pick_ship()
        location = self.env['stock.location'].browse(self.stock_location)

        # make some stock
        self.env['stock.quant']._update_available_quantity(self.productA, location, 10.0)
        picking_pick.action_assign()
        picking_pick.move_lines[0].move_line_ids[0].write({
            'qty_done': 10.0,
            'lot_id': lot1.id,
        })
        picking_pick.action_done()

        self.assertEqual(picking_pick.state, 'done', 'The state of the pick should be done')
        self.assertEqual(picking_client.state, 'assigned', 'The state of the client should be assigned')
        self.assertEqual(picking_pick.move_lines.quantity_done, 10.0, 'Wrong quantity_done for pick move')
        self.assertEqual(picking_client.move_lines.product_qty, 10.0, 'Wrong initial demand for client move')
        self.assertEqual(picking_client.move_lines.move_line_ids.lot_id, lot1, 'Wrong lot for client move line')
        self.assertEqual(picking_client.move_lines.reserved_availability, 10.0, 'Wrong quantity already reserved for client move')

        picking_pick.move_lines[0].move_line_ids[0].lot_id = lot2.id
        self.assertEqual(picking_pick.state, 'done', 'The state of the pick should be done')
        self.assertEqual(picking_client.state, 'assigned', 'The state of the client should be partially available')
        self.assertEqual(picking_pick.move_lines.quantity_done, 10.0, 'Wrong quantity_done for pick move')
        self.assertEqual(picking_client.move_lines.product_qty, 10.0, 'Wrong initial demand for client move')
        self.assertEqual(picking_client.move_lines.move_line_ids.lot_id, lot2, 'Wrong lot for client move line')
        self.assertEqual(picking_client.move_lines.reserved_availability, 10.0, 'Wrong quantity already reserved for client move')

        # Check if run action_assign does not crash
        picking_client.action_assign()

    def test_chained_move_with_uom(self):
        """ Create pick ship with a different uom than the once used for quant.
        Check that reserved quantity and flow work correctly.
        """
        picking_client = self.env['stock.picking'].create({
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_out,
        })
        dest = self.MoveObj.create({
            'name': self.gB.name,
            'product_id': self.gB.id,
            'product_uom_qty': 5,
            'product_uom': self.uom_kg.id,
            'picking_id': picking_client.id,
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
            'state': 'waiting',
        })

        picking_pick = self.env['stock.picking'].create({
            'location_id': self.stock_location,
            'location_dest_id': self.pack_location,
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_out,
        })

        self.MoveObj.create({
            'name': self.gB.name,
            'product_id': self.gB.id,
            'product_uom_qty': 5,
            'product_uom': self.uom_kg.id,
            'picking_id': picking_pick.id,
            'location_id': self.stock_location,
            'location_dest_id': self.pack_location,
            'move_dest_ids': [(4, dest.id)],
            'state': 'confirmed',
        })
        location = self.env['stock.location'].browse(self.stock_location)
        pack_location = self.env['stock.location'].browse(self.pack_location)

        # make some stock
        self.env['stock.quant']._update_available_quantity(self.gB, location, 10000.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.gB, pack_location), 0.0)
        picking_pick.action_assign()
        picking_pick.move_lines[0].move_line_ids[0].qty_done = 5.0
        picking_pick.action_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.gB, location), 5000.0)
        self.assertEqual(self.env['stock.quant']._gather(self.gB, pack_location).quantity, 5000.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.gB, pack_location), 0.0)
        self.assertEqual(picking_client.state, 'assigned')
        self.assertEqual(picking_client.move_lines.reserved_availability, 5.0)

    def test_pick_ship_return(self):
        """ Create pick and ship. Bring it ot the customer and then return
        it to stock. This test check the state and the quantity after each move in
        order to ensure that it is correct.
        """
        picking_pick, picking_ship = self.create_pick_ship()
        stock_location = self.env['stock.location'].browse(self.stock_location)
        pack_location = self.env['stock.location'].browse(self.pack_location)
        customer_location = self.env['stock.location'].browse(self.customer_location)
        self.productA.tracking = 'lot'
        lot = self.env['stock.production.lot'].create({
            'product_id': self.productA.id,
            'name': '123456789'
        })
        self.env['stock.quant']._update_available_quantity(self.productA, stock_location, 10.0, lot_id=lot)

        picking_pick.action_assign()
        picking_pick.move_lines[0].move_line_ids[0].qty_done = 10.0
        picking_pick.action_done()
        self.assertEqual(picking_pick.state, 'done')
        self.assertEqual(picking_ship.state, 'assigned')

        picking_ship.action_assign()
        picking_ship.move_lines[0].move_line_ids[0].qty_done = 10.0
        picking_ship.action_done()

        customer_quantity = self.env['stock.quant']._get_available_quantity(self.productA, customer_location, lot_id=lot)
        self.assertEqual(customer_quantity, 10, 'It should be one product in customer')

        """ First we create the return picking for pick pinking.
        Since we do not have created the return between customer and
        output. This return should not be available and should only have
        picking pick as origin move.
        """
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=picking_pick.ids, active_id=picking_pick.ids[0],
            active_model='stock.picking'))
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 10.0
        stock_return_picking_action = stock_return_picking.create_returns()
        return_pick_picking = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])

        self.assertEqual(return_pick_picking.state, 'waiting')

        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=picking_ship.ids, active_id=picking_ship.ids[0],
            active_model='stock.picking'))
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 10.0
        stock_return_picking_action = stock_return_picking.create_returns()
        return_ship_picking = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])

        self.assertEqual(return_ship_picking.state, 'assigned', 'Return ship picking should automatically be assigned')
        """ We created the return for ship picking. The origin/destination
        link between return moves should have been created during return creation.
        """
        self.assertTrue(return_ship_picking.move_lines in return_pick_picking.move_lines.mapped('move_orig_ids'),
                        'The pick return picking\'s moves should have the ship return picking\'s moves as origin')

        self.assertTrue(return_pick_picking.move_lines in return_ship_picking.move_lines.mapped('move_dest_ids'),
                        'The ship return picking\'s moves should have the pick return picking\'s moves as destination')

        return_ship_picking.move_lines[0].move_line_ids[0].write({
            'qty_done': 10.0,
            'lot_id': lot.id,
        })
        return_ship_picking.action_done()
        self.assertEqual(return_ship_picking.state, 'done')
        self.assertEqual(return_pick_picking.state, 'assigned')

        customer_quantity = self.env['stock.quant']._get_available_quantity(self.productA, customer_location, lot_id=lot)
        self.assertEqual(customer_quantity, 0, 'It should be one product in customer')

        pack_quantity = self.env['stock.quant']._get_available_quantity(self.productA, pack_location, lot_id=lot)
        self.assertEqual(pack_quantity, 0, 'It should be one product in pack location but is reserved')

        # Should use previous move lot.
        return_pick_picking.move_lines[0].move_line_ids[0].qty_done = 10.0
        return_pick_picking.action_done()
        self.assertEqual(return_pick_picking.state, 'done')

        stock_quantity = self.env['stock.quant']._get_available_quantity(self.productA, stock_location, lot_id=lot)
        self.assertEqual(stock_quantity, 10, 'The product is not back in stock')

    def test_pick_pack_ship_return(self):
        """ This test do a pick pack ship delivery to customer and then
        return it to stock. Once everything is done, this test will check
        if all the link orgini/destination between moves are correct.
        """
        picking_pick, picking_pack, picking_ship = self.create_pick_pack_ship()
        stock_location = self.env['stock.location'].browse(self.stock_location)
        self.productA.tracking = 'serial'
        lot = self.env['stock.production.lot'].create({
            'product_id': self.productA.id,
            'name': '123456789'
        })
        self.env['stock.quant']._update_available_quantity(self.productA, stock_location, 1.0, lot_id=lot)

        picking_pick.action_assign()
        picking_pick.move_lines[0].move_line_ids[0].qty_done = 1.0
        picking_pick.action_done()

        picking_pack.action_assign()
        picking_pack.move_lines[0].move_line_ids[0].qty_done = 1.0
        picking_pack.action_done()

        picking_ship.action_assign()
        picking_ship.move_lines[0].move_line_ids[0].qty_done = 1.0
        picking_ship.action_done()

        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=picking_ship.ids, active_id=picking_ship.ids[0],
            active_model='stock.picking'))
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 1.0
        stock_return_picking_action = stock_return_picking.create_returns()
        return_ship_picking = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])

        return_ship_picking.move_lines[0].move_line_ids[0].write({
            'qty_done': 1.0,
            'lot_id': lot.id,
        })
        return_ship_picking.action_done()

        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=picking_pack.ids, active_id=picking_pack.ids[0],
            active_model='stock.picking'))
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 1.0
        stock_return_picking_action = stock_return_picking.create_returns()
        return_pack_picking = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])

        return_pack_picking.move_lines[0].move_line_ids[0].qty_done = 1.0
        return_pack_picking.action_done()

        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=picking_pick.ids, active_id=picking_pick.ids[0],
            active_model='stock.picking'))
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 1.0
        stock_return_picking_action = stock_return_picking.create_returns()
        return_pick_picking = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])

        return_pick_picking.move_lines[0].move_line_ids[0].qty_done = 1.0
        return_pick_picking.action_done()

        # Now that everything is returned we will check if the return moves are correctly linked between them.
        # +--------------------------------------------------------------------------------------------------------+
        # |         -- picking_pick(1) -->       -- picking_pack(2) -->         -- picking_ship(3) -->
        # | Stock                          Pack                         Output                          Customer
        # |         <--- return pick(6) --      <--- return pack(5) --          <--- return ship(4) --
        # +--------------------------------------------------------------------------------------------------------+
        # Recaps of final link (MO = move_orig_ids, MD = move_dest_ids)
        # picking_pick(1) : MO = (), MD = (2,6)
        # picking_pack(2) : MO = (1), MD = (3,5)
        # picking ship(3) : MO = (2), MD = (4)
        # return ship(4) : MO = (3), MD = (5)
        # return pack(5) : MO = (2, 4), MD = (6)
        # return pick(6) : MO = (1, 5), MD = ()

        self.assertEqual(len(picking_pick.move_lines.move_orig_ids), 0, 'Picking pick should not have origin moves')
        self.assertEqual(set(picking_pick.move_lines.move_dest_ids.ids), set((picking_pack.move_lines | return_pick_picking.move_lines).ids))

        self.assertEqual(set(picking_pack.move_lines.move_orig_ids.ids), set(picking_pick.move_lines.ids))
        self.assertEqual(set(picking_pack.move_lines.move_dest_ids.ids), set((picking_ship.move_lines | return_pack_picking.move_lines).ids))

        self.assertEqual(set(picking_ship.move_lines.move_orig_ids.ids), set(picking_pack.move_lines.ids))
        self.assertEqual(set(picking_ship.move_lines.move_dest_ids.ids), set(return_ship_picking.move_lines.ids))

        self.assertEqual(set(return_ship_picking.move_lines.move_orig_ids.ids), set(picking_ship.move_lines.ids))
        self.assertEqual(set(return_ship_picking.move_lines.move_dest_ids.ids), set(return_pack_picking.move_lines.ids))

        self.assertEqual(set(return_pack_picking.move_lines.move_orig_ids.ids), set((picking_pack.move_lines | return_ship_picking.move_lines).ids))
        self.assertEqual(set(return_pack_picking.move_lines.move_dest_ids.ids), set(return_pick_picking.move_lines.ids))

        self.assertEqual(set(return_pick_picking.move_lines.move_orig_ids.ids), set((picking_pick.move_lines | return_pack_picking.move_lines).ids))
        self.assertEqual(len(return_pick_picking.move_lines.move_dest_ids), 0)

    def test_merge_move_mto_mts(self):
        """ Create 2 moves of the same product in the same picking with
        one in 'MTO' and the other one in 'MTS'. The moves shouldn't be merged
        """
        picking_pick, picking_client = self.create_pick_ship()

        self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 3,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking_client.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'origin': 'MPS',
            'procure_method': 'make_to_stock',
        })
        picking_client.action_confirm()
        self.assertEqual(len(picking_client.move_lines), 2, 'Moves should not be merged')

    def test_mto_cancel_move_line(self):
        """ Create a pick ship situation. Then process the pick picking
        with a backorder. Then try to unlink the move line created on
        the ship and check if the picking and move state are updated.
        Then validate the backorder and unlink the ship move lines in
        order to check again if the picking and state are updated.
        """
        picking_pick, picking_client = self.create_pick_ship()
        location = self.env['stock.location'].browse(self.stock_location)

        # make some stock
        self.env['stock.quant']._update_available_quantity(self.productA, location, 10.0)
        picking_pick.move_lines.quantity_done = 5.0
        backorder_wizard_values = picking_pick.button_validate()
        backorder_wizard = self.env[(backorder_wizard_values.get('res_model'))].browse(backorder_wizard_values.get('res_id'))
        backorder_wizard.process()

        self.assertTrue(picking_client.move_line_ids, 'A move line should be created.')
        self.assertEqual(picking_client.move_line_ids.product_uom_qty, 5, 'The move line should have 5 unit reserved.')

        # Directly delete the move lines on the picking. (Use show detail operation on picking type)
        # Should do the same behavior than unreserve
        picking_client.move_line_ids.unlink()

        self.assertEqual(picking_client.move_lines.state, 'waiting', 'The move state should be waiting since nothing is reserved and another origin move still in progess.')
        self.assertEqual(picking_client.state, 'waiting', 'The picking state should not be ready anymore.')

        picking_client.action_assign()

        back_order = self.env['stock.picking'].search([('backorder_id', '=', picking_pick.id)])
        back_order.move_lines.quantity_done = 5
        back_order.button_validate()

        self.assertEqual(picking_client.move_lines.reserved_availability, 10, 'The total quantity should be reserved since everything is available.')
        picking_client.move_line_ids.unlink()

        self.assertEqual(picking_client.move_lines.state, 'confirmed', 'The move should be confirmed since all the origin moves are processed.')
        self.assertEqual(picking_client.state, 'confirmed', 'The picking should be confirmed since all the moves are confirmed.')

    def test_unreserve(self):
        picking_pick, picking_client = self.create_pick_ship()

        self.assertEqual(picking_pick.state, 'confirmed')
        picking_pick.do_unreserve()
        self.assertEqual(picking_pick.state, 'confirmed')
        location = self.env['stock.location'].browse(self.stock_location)
        self.env['stock.quant']._update_available_quantity(self.productA, location, 10.0)
        picking_pick.action_assign()
        self.assertEqual(picking_pick.state, 'assigned')
        picking_pick.do_unreserve()
        self.assertEqual(picking_pick.state, 'confirmed')

        self.assertEqual(picking_client.state, 'waiting')
        picking_client.do_unreserve()
        self.assertEqual(picking_client.state, 'waiting')

    def test_return_location(self):
        """ In a pick ship scenario, send two items to the customer, then return one in the ship
        location and one in a return location that is located in another warehouse.
        """
        pick_location = self.env['stock.location'].browse(self.stock_location)
        pick_location.return_location = True

        return_warehouse = self.env['stock.warehouse'].create({'name': 'return warehouse', 'code': 'rw'})
        return_location = self.env['stock.location'].create({
            'name': 'return internal',
            'usage': 'internal',
            'location_id': return_warehouse.view_location_id.id
        })

        self.env['stock.quant']._update_available_quantity(self.productA, pick_location, 10.0)
        picking_pick, picking_client = self.create_pick_ship()

        # send the items to the customer
        picking_pick.action_assign()
        picking_pick.move_lines[0].move_line_ids[0].qty_done = 10.0
        picking_pick.action_done()
        picking_client.move_lines[0].move_line_ids[0].qty_done = 10.0
        picking_client.action_done()

        # return half in the pick location
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=picking_client.ids, active_id=picking_client.ids[0],
            active_model='stock.picking'))
        return1 = stock_return_picking_form.save()
        return1.product_return_moves.quantity = 5.0
        return1.location_id = pick_location.id
        return_to_pick_picking_action = return1.create_returns()

        return_to_pick_picking = self.env['stock.picking'].browse(return_to_pick_picking_action['res_id'])
        return_to_pick_picking.move_lines[0].move_line_ids[0].qty_done = 5.0
        return_to_pick_picking.action_done()

        # return the remainig products in the return warehouse
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=picking_client.ids, active_id=picking_client.ids[0],
            active_model='stock.picking'))
        return2 = stock_return_picking_form.save()
        return2.product_return_moves.quantity = 5.0
        return2.location_id = return_location.id
        return_to_return_picking_action = return2.create_returns()

        return_to_return_picking = self.env['stock.picking'].browse(return_to_return_picking_action['res_id'])
        return_to_return_picking.move_lines[0].move_line_ids[0].qty_done = 5.0
        return_to_return_picking.action_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, pick_location), 5.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, return_location), 5.0)
        self.assertEqual(len(self.env['stock.quant'].search([('product_id', '=', self.productA.id), ('quantity', '!=', 0)])), 2)


class TestSinglePicking(TestStockCommon):
    def test_backorder_1(self):
        """ Check the good behavior of creating a backorder for an available stock move.
        """
        delivery_order = self.env['stock.picking'].create({
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_out,
        })
        self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 2,
            'product_uom': self.productA.uom_id.id,
            'picking_id': delivery_order.id,
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
        })

        # make some stock
        pack_location = self.env['stock.location'].browse(self.pack_location)
        self.env['stock.quant']._update_available_quantity(self.productA, pack_location, 2)

        # assign
        delivery_order.action_confirm()
        delivery_order.action_assign()
        self.assertEqual(delivery_order.state, 'assigned')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, pack_location), 0.0)

        # valid with backorder creation
        delivery_order.move_lines[0].move_line_ids[0].qty_done = 1
        delivery_order.action_done()
        self.assertNotEqual(delivery_order.date_done, False)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, pack_location), 0.0)

        backorder = self.env['stock.picking'].search([('backorder_id', '=', delivery_order.id)])
        self.assertEqual(backorder.state, 'assigned')

    def test_backorder_2(self):
        """ Check the good behavior of creating a backorder for a partially available stock move.
        """
        delivery_order = self.env['stock.picking'].create({
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_out,
        })
        self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 2,
            'product_uom': self.productA.uom_id.id,
            'picking_id': delivery_order.id,
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
        })

        # make some stock
        pack_location = self.env['stock.location'].browse(self.pack_location)
        self.env['stock.quant']._update_available_quantity(self.productA, pack_location, 1)

        # assign to partially available
        delivery_order.action_confirm()
        delivery_order.action_assign()
        self.assertEqual(delivery_order.state, 'assigned')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, pack_location), 0.0)

        # valid with backorder creation
        delivery_order.move_lines[0].move_line_ids[0].qty_done = 1
        delivery_order.action_done()
        self.assertNotEqual(delivery_order.date_done, False)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, pack_location), 0.0)

        backorder = self.env['stock.picking'].search([('backorder_id', '=', delivery_order.id)])
        self.assertEqual(backorder.state, 'confirmed')

    def test_backorder_3(self):
        """ Check the good behavior of creating a backorder for an available move on a picking with
        two available moves.
        """
        delivery_order = self.env['stock.picking'].create({
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_out,
        })
        self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 2,
            'product_uom': self.productA.uom_id.id,
            'picking_id': delivery_order.id,
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
        })
        self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productB.id,
            'product_uom_qty': 2,
            'product_uom': self.productB.uom_id.id,
            'picking_id': delivery_order.id,
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
        })

        # make some stock
        pack_location = self.env['stock.location'].browse(self.pack_location)
        self.env['stock.quant']._update_available_quantity(self.productA, pack_location, 2)
        self.env['stock.quant']._update_available_quantity(self.productA, pack_location, 2)

        # assign to partially available
        delivery_order.action_confirm()
        delivery_order.action_assign()
        self.assertEqual(delivery_order.state, 'assigned')

        delivery_order.move_lines[0].move_line_ids[0].qty_done = 2
        delivery_order.action_done()

        backorder = self.env['stock.picking'].search([('backorder_id', '=', delivery_order.id)])
        self.assertEqual(backorder.state, 'confirmed')

    def test_backorder_4(self):
        """ Check the good behavior if no backorder are created
        for a picking with a missing product.
        """
        delivery_order = self.env['stock.picking'].create({
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_out,
        })
        self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 2,
            'product_uom': self.productA.uom_id.id,
            'picking_id': delivery_order.id,
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
        })
        self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productB.id,
            'product_uom_qty': 2,
            'product_uom': self.productB.uom_id.id,
            'picking_id': delivery_order.id,
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
        })

        # Update available quantities for each products
        pack_location = self.env['stock.location'].browse(self.pack_location)
        self.env['stock.quant']._update_available_quantity(self.productA, pack_location, 2)
        self.env['stock.quant']._update_available_quantity(self.productB, pack_location, 2)

        delivery_order.action_confirm()
        delivery_order.action_assign()
        self.assertEqual(delivery_order.state, 'assigned')

        # Process only one product without creating a backorder
        delivery_order.move_lines[0].move_line_ids[0].qty_done = 2
        backorder_wizard = self.env['stock.backorder.confirmation'].create({'pick_ids': [(4, delivery_order.id)]})
        backorder_wizard.process_cancel_backorder()

        # No backorder should be created and the move corresponding to the missing product should be cancelled
        backorder = self.env['stock.picking'].search([('backorder_id', '=', delivery_order.id)])
        self.assertFalse(backorder)
        self.assertEquals(delivery_order.state, 'done')
        self.assertEquals(delivery_order.move_lines[1].state, 'cancel')

    def test_extra_move_1(self):
        """ Check the good behavior of creating an extra move in a delivery order. This usecase
        simulates the delivery of 2 item while the initial stock move had to move 1 and there's
        only 1 in stock.
        """
        delivery_order = self.env['stock.picking'].create({
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_out,
        })
        move1 = self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 1,
            'product_uom': self.productA.uom_id.id,
            'picking_id': delivery_order.id,
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
        })

        # make some stock
        pack_location = self.env['stock.location'].browse(self.pack_location)
        self.env['stock.quant']._update_available_quantity(self.productA, pack_location, 1)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, pack_location), 1.0)

        # assign to available
        delivery_order.action_confirm()
        delivery_order.action_assign()
        self.assertEqual(delivery_order.state, 'assigned')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, pack_location), 0.0)

        # valid with backorder creation
        delivery_order.move_lines[0].move_line_ids[0].qty_done = 2
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, pack_location), 0.0)
        delivery_order.action_done()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, pack_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, pack_location, allow_negative=True), -1.0)

        self.assertEqual(move1.product_qty, 2.0)
        self.assertEqual(move1.quantity_done, 2.0)
        self.assertEqual(move1.reserved_availability, 0.0)
        self.assertEqual(move1.move_line_ids.product_qty, 0.0)  # change reservation to 0 for done move
        self.assertEqual(sum(move1.move_line_ids.mapped('qty_done')), 2.0)
        self.assertEqual(move1.state, 'done')

    def test_extra_move_2(self):
        """ Check the good behavior of creating an extra move in a delivery order. This usecase
        simulates the delivery of 3 item while the initial stock move had to move 1 and there's
        only 1 in stock.
        """
        delivery_order = self.env['stock.picking'].create({
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_out,
        })
        move1 = self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 1,
            'product_uom': self.productA.uom_id.id,
            'picking_id': delivery_order.id,
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
        })

        # make some stock
        pack_location = self.env['stock.location'].browse(self.pack_location)
        self.env['stock.quant']._update_available_quantity(self.productA, pack_location, 1)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, pack_location), 1.0)

        # assign to available
        delivery_order.action_confirm()
        delivery_order.action_assign()
        self.assertEqual(delivery_order.state, 'assigned')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, pack_location), 0.0)

        # valid with backorder creation
        delivery_order.move_lines[0].move_line_ids[0].qty_done = 3
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, pack_location), 0.0)
        delivery_order.action_done()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, pack_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, pack_location, allow_negative=True), -2.0)

        self.assertEqual(move1.product_qty, 3.0)
        self.assertEqual(move1.quantity_done, 3.0)
        self.assertEqual(move1.reserved_availability, 0.0)
        self.assertEqual(move1.move_line_ids.product_qty, 0.0)  # change reservation to 0 for done move
        self.assertEqual(sum(move1.move_line_ids.mapped('qty_done')), 3.0)
        self.assertEqual(move1.state, 'done')

    def test_extra_move_3(self):
        """ Check the good behavior of creating an extra move in a receipt. This usecase simulates
         the receipt of 2 item while the initial stock move had to move 1.
        """
        receipt = self.env['stock.picking'].create({
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_in,
        })
        move1 = self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 1,
            'product_uom': self.productA.uom_id.id,
            'picking_id': receipt.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
        })
        stock_location = self.env['stock.location'].browse(self.stock_location)

        # assign to available
        receipt.action_confirm()
        receipt.action_assign()
        self.assertEqual(receipt.state, 'assigned')

        # valid with backorder creation
        receipt.move_lines[0].move_line_ids[0].qty_done = 2
        receipt.action_done()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, stock_location), 2.0)

        self.assertEqual(move1.product_qty, 2.0)
        self.assertEqual(move1.quantity_done, 2.0)
        self.assertEqual(move1.reserved_availability, 0.0)
        self.assertEqual(move1.move_line_ids.product_qty, 0.0)  # change reservation to 0 for done move
        self.assertEqual(sum(move1.move_line_ids.mapped('qty_done')), 2.0)
        self.assertEqual(move1.state, 'done')

    def test_extra_move_4(self):
        """ Create a picking with similar moves (created after
        confirmation). Action done should propagate all the extra
        quantity and only merge extra moves in their original moves.
        """
        delivery = self.env['stock.picking'].create({
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_out,
        })
        self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 5,
            'quantity_done': 10,
            'product_uom': self.productA.uom_id.id,
            'picking_id': delivery.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
        })
        stock_location = self.env['stock.location'].browse(self.stock_location)
        self.env['stock.quant']._update_available_quantity(self.productA, stock_location, 5)
        delivery.action_confirm()
        delivery.action_assign()

        delivery.write({
            'move_lines': [(0, 0, {
                'name': self.productA.name,
                'product_id': self.productA.id,
                'product_uom_qty': 0,
                'quantity_done': 10,
                'state': 'assigned',
                'product_uom': self.productA.uom_id.id,
                'picking_id': delivery.id,
                'location_id': self.stock_location,
                'location_dest_id': self.customer_location,
            })]
        })
        delivery.action_done()
        self.assertEqual(len(delivery.move_lines), 2, 'Move should not be merged together')
        for move in delivery.move_lines:
            self.assertEqual(move.quantity_done, move.product_uom_qty, 'Initial demand should be equals to quantity done')

    def test_extra_move_5(self):
        """ Create a picking a move that is problematic with
        rounding (5.95 - 5.5 = 0.4500000000000002). Ensure that
        initial demand is corrct afer action_done and backoder
        are not created.
        """
        delivery = self.env['stock.picking'].create({
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_out,
        })
        product = self.kgB
        self.MoveObj.create({
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 5.5,
            'quantity_done': 5.95,
            'product_uom': product.uom_id.id,
            'picking_id': delivery.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
        })
        stock_location = self.env['stock.location'].browse(self.stock_location)
        self.env['stock.quant']._update_available_quantity(product, stock_location, 5.5)
        delivery.action_confirm()
        delivery.action_assign()
        delivery.action_done()
        self.assertEqual(delivery.move_lines.product_uom_qty, 5.95, 'Move initial demand should be 5.95')

        back_order = self.env['stock.picking'].search([('backorder_id', '=', delivery.id)])
        self.assertFalse(back_order, 'There should be no back order')

    def test_recheck_availability_1(self):
        """ Check the good behavior of check availability. I create a DO for 2 unit with
        only one in stock. After the first check availability, I should have 1 reserved
        product with one move line. After adding a second unit in stock and recheck availability.
        The DO should have 2 reserved unit, be in available state and have only one move line.
        """
        self.env['stock.quant']._update_available_quantity(self.productA, self.env['stock.location'].browse(self.stock_location), 1.0)
        delivery_order = self.env['stock.picking'].create({
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_out,
        })
        move1 = self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 2,
            'product_uom': self.productA.uom_id.id,
            'picking_id': delivery_order.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
        })
        delivery_order.action_confirm()
        delivery_order.action_assign()
        # Check State
        self.assertEqual(delivery_order.state, 'assigned')
        self.assertEqual(move1.state, 'partially_available')

        # Check reserved quantity
        self.assertEqual(move1.reserved_availability, 1.0)
        self.assertEqual(len(move1.move_line_ids), 1)
        self.assertEqual(move1.move_line_ids.product_qty, 1)

        inventory = self.env['stock.inventory'].create({
            'name': 'remove product1',
            'filter': 'product',
            'location_id': self.stock_location,
            'product_id': self.productA.id,
        })
        inventory.action_start()
        inventory.line_ids.product_qty = 2
        inventory.action_validate()
        delivery_order.action_assign()
        self.assertEqual(delivery_order.state, 'assigned')
        self.assertEqual(move1.state, 'assigned')

        # Check reserved quantity
        self.assertEqual(move1.reserved_availability, 2.0)
        self.assertEqual(len(move1.move_line_ids), 1)
        self.assertEqual(move1.move_line_ids.product_qty, 2)

    def test_recheck_availability_2(self):
        """ Same check than test_recheck_availability_1 but with lot this time.
        If the new product has the same lot that already reserved one, the move lines
        reserved quantity should be updated.
        Otherwise a new move lines with the new lot should be added.
        """
        self.productA.tracking = 'lot'
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.productA.id,
        })
        stock_location = self.env['stock.location'].browse(self.stock_location)
        self.env['stock.quant']._update_available_quantity(self.productA, stock_location, 1.0, lot_id=lot1)
        delivery_order = self.env['stock.picking'].create({
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_out,
        })
        move1 = self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 2,
            'product_uom': self.productA.uom_id.id,
            'picking_id': delivery_order.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
        })
        delivery_order.action_confirm()
        delivery_order.action_assign()
        # Check State
        self.assertEqual(delivery_order.state, 'assigned')
        self.assertEqual(move1.state, 'partially_available')

        # Check reserved quantity
        self.assertEqual(move1.reserved_availability, 1.0)
        self.assertEqual(len(move1.move_line_ids), 1)
        self.assertEqual(move1.move_line_ids.product_qty, 1)

        inventory = self.env['stock.inventory'].create({
            'name': 'remove product1',
            'filter': 'product',
            'location_id': self.stock_location,
            'product_id': self.productA.id,
        })
        inventory.action_start()
        inventory.line_ids.prod_lot_id = lot1
        inventory.line_ids.product_qty = 2
        inventory.action_validate()
        delivery_order.action_assign()
        self.assertEqual(delivery_order.state, 'assigned')
        self.assertEqual(move1.state, 'assigned')

        # Check reserved quantity
        self.assertEqual(move1.reserved_availability, 2.0)
        self.assertEqual(len(move1.move_line_ids), 1)
        self.assertEqual(move1.move_line_ids.lot_id.id, lot1.id)
        self.assertEqual(move1.move_line_ids.product_qty, 2)

    def test_recheck_availability_3(self):
        """ Same check than test_recheck_availability_2 but with different lots.
        """
        self.productA.tracking = 'lot'
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.productA.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.productA.id,
        })
        stock_location = self.env['stock.location'].browse(self.stock_location)
        self.env['stock.quant']._update_available_quantity(self.productA, stock_location, 1.0, lot_id=lot1)
        delivery_order = self.env['stock.picking'].create({
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_out,
        })
        move1 = self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 2,
            'product_uom': self.productA.uom_id.id,
            'picking_id': delivery_order.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
        })
        delivery_order.action_confirm()
        delivery_order.action_assign()
        # Check State
        self.assertEqual(delivery_order.state, 'assigned')
        self.assertEqual(move1.state, 'partially_available')

        # Check reserved quantity
        self.assertEqual(move1.reserved_availability, 1.0)
        self.assertEqual(len(move1.move_line_ids), 1)
        self.assertEqual(move1.move_line_ids.product_qty, 1)

        inventory = self.env['stock.inventory'].create({
            'name': 'remove product1',
            'filter': 'product',
            'location_id': self.stock_location,
            'product_id': self.productA.id,
        })
        inventory.action_start()
        self.env['stock.inventory.line'].create({
            'inventory_id': inventory.id,
            'location_id': inventory.location_id.id,
            'partner_id': inventory.partner_id.id,
            'prod_lot_id': lot2.id,
            'product_id': self.productA.id,
            'product_qty': 1,
        })
        inventory.action_validate()
        delivery_order.action_assign()
        self.assertEqual(delivery_order.state, 'assigned')
        self.assertEqual(move1.state, 'assigned')

        # Check reserved quantity
        self.assertEqual(move1.reserved_availability, 2.0)
        self.assertEqual(len(move1.move_line_ids), 2)
        self.assertEqual(move1.move_line_ids[0].lot_id.id, lot1.id)
        self.assertEqual(move1.move_line_ids[1].lot_id.id, lot2.id)

    def test_recheck_availability_4(self):
        """ Same check than test_recheck_availability_2 but with serial number this time.
        Serial number reservation should always create a new move line.
        """
        self.productA.tracking = 'serial'
        serial1 = self.env['stock.production.lot'].create({
            'name': 'serial1',
            'product_id': self.productA.id,
        })
        serial2 = self.env['stock.production.lot'].create({
            'name': 'serial2',
            'product_id': self.productA.id,
        })
        stock_location = self.env['stock.location'].browse(self.stock_location)
        self.env['stock.quant']._update_available_quantity(self.productA, stock_location, 1.0, lot_id=serial1)
        delivery_order = self.env['stock.picking'].create({
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_out,
        })
        move1 = self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 2,
            'product_uom': self.productA.uom_id.id,
            'picking_id': delivery_order.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
        })
        delivery_order.action_confirm()
        delivery_order.action_assign()
        # Check State
        self.assertEqual(delivery_order.state, 'assigned')
        self.assertEqual(move1.state, 'partially_available')

        # Check reserved quantity
        self.assertEqual(move1.reserved_availability, 1.0)
        self.assertEqual(len(move1.move_line_ids), 1)
        self.assertEqual(move1.move_line_ids.product_qty, 1)

        inventory = self.env['stock.inventory'].create({
            'name': 'remove product1',
            'filter': 'product',
            'location_id': self.stock_location,
            'product_id': self.productA.id,
        })
        inventory.action_start()
        self.env['stock.inventory.line'].create({
            'inventory_id': inventory.id,
            'location_id': inventory.location_id.id,
            'partner_id': inventory.partner_id.id,
            'prod_lot_id': serial2.id,
            'product_id': self.productA.id,
            'product_qty': 1,
        })
        inventory.action_validate()
        delivery_order.action_assign()
        self.assertEqual(delivery_order.state, 'assigned')
        self.assertEqual(move1.state, 'assigned')

        # Check reserved quantity
        self.assertEqual(move1.reserved_availability, 2.0)
        self.assertEqual(len(move1.move_line_ids), 2)
        self.assertEqual(move1.move_line_ids[0].lot_id.id, serial1.id)
        self.assertEqual(move1.move_line_ids[1].lot_id.id, serial2.id)

    def test_add_move_when_picking_is_available_1(self):
        """ Check that any move added in a picking once it's assigned is directly considered as
        assigned and bypass the reservation.
        """
        delivery_order = self.env['stock.picking'].create({
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_out,
        })
        self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 2,
            'product_uom': self.productA.uom_id.id,
            'picking_id': delivery_order.id,
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
        })

        # make some stock
        pack_location = self.env['stock.location'].browse(self.pack_location)
        self.env['stock.quant']._update_available_quantity(self.productA, pack_location, 2)

        # assign
        delivery_order.action_confirm()
        delivery_order.action_assign()
        self.assertEqual(delivery_order.state, 'assigned')

        # add a move
        move2 = self.MoveObj\
            .with_context(default_picking_id=delivery_order.id)\
            .create({
                'name': self.productA.name,
                'product_id': self.productB.id,
                'product_uom_qty': 1,
                'product_uom': self.productA.uom_id.id,
                'picking_id': delivery_order.id,
                'location_id': self.pack_location,
                'location_dest_id': self.customer_location,
            })

        self.assertEqual(move2.state, 'assigned')
        self.assertEqual(delivery_order.state, 'assigned')

    def test_use_create_lot_use_existing_lot_1(self):
        """ Check the behavior of a picking when `use_create_lot` and `use_existing_lot` are
        set to False and there's a move for a tracked product.
        """
        self.env['stock.picking.type']\
            .browse(self.picking_type_out)\
            .write({
                'use_create_lots': False,
                'use_existing_lots': False,
            })
        self.productA.tracking = 'lot'

        delivery_order = self.env['stock.picking'].create({
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_out,
        })
        self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 2,
            'product_uom': self.productA.uom_id.id,
            'picking_id': delivery_order.id,
            'picking_type_id': self.picking_type_out,
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
        })

        delivery_order.action_confirm()
        delivery_order.move_lines.quantity_done = 2
        # do not set a lot_id or lot_name, it should work
        delivery_order.action_done()

    def test_use_create_lot_use_existing_lot_2(self):
        """ Check the behavior of a picking when `use_create_lot` and `use_existing_lot` are
        set to True and there's a move for a tracked product.
        """
        self.env['stock.picking.type']\
            .browse(self.picking_type_out)\
            .write({
                'use_create_lots': True,
                'use_existing_lots': True,
            })
        self.productA.tracking = 'lot'

        delivery_order = self.env['stock.picking'].create({
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_out,
        })
        self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 2,
            'product_uom': self.productA.uom_id.id,
            'picking_id': delivery_order.id,
            'picking_type_id': self.picking_type_out,
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
        })

        delivery_order.action_confirm()
        delivery_order.move_lines.quantity_done = 2
        move_line = delivery_order.move_lines.move_line_ids

        # not lot_name set, should raise
        with self.assertRaises(UserError):
            delivery_order.action_done()

        # enter a new lot name, should work
        move_line.lot_name = 'newlot'
        delivery_order.action_done()

    def test_use_create_lot_use_existing_lot_3(self):
        """ Check the behavior of a picking when `use_create_lot` is set to True and
        `use_existing_lot` is set to False and there's a move for a tracked product.
        """
        self.env['stock.picking.type']\
            .browse(self.picking_type_out)\
            .write({
                'use_create_lots': True,
                'use_existing_lots': False,
            })
        self.productA.tracking = 'lot'

        delivery_order = self.env['stock.picking'].create({
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_out,
        })
        self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 2,
            'product_uom': self.productA.uom_id.id,
            'picking_id': delivery_order.id,
            'picking_type_id': self.picking_type_out,
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
        })

        delivery_order.action_confirm()
        delivery_order.move_lines.quantity_done = 2
        move_line = delivery_order.move_lines.move_line_ids

        # not lot_name set, should raise
        with self.assertRaises(UserError):
            delivery_order.action_done()

        # enter a new lot name, should work
        move_line.lot_name = 'newlot'
        delivery_order.action_done()

    def test_use_create_lot_use_existing_lot_4(self):
        """ Check the behavior of a picking when `use_create_lot` is set to False and
        `use_existing_lot` is set to True and there's a move for a tracked product.
        """
        self.env['stock.picking.type']\
            .browse(self.picking_type_out)\
            .write({
                'use_create_lots': False,
                'use_existing_lots': True,
            })
        self.productA.tracking = 'lot'

        delivery_order = self.env['stock.picking'].create({
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_out,
        })
        self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 2,
            'product_uom': self.productA.uom_id.id,
            'picking_id': delivery_order.id,
            'picking_type_id': self.picking_type_out,
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
        })

        delivery_order.action_confirm()
        delivery_order.move_lines.quantity_done = 2
        move_line = delivery_order.move_lines.move_line_ids

        # not lot_name set, should raise
        with self.assertRaises(UserError):
            delivery_order.action_done()

        # creating a lot from the view should raise
        with self.assertRaises(UserError):
            self.env['stock.production.lot']\
                .with_context(active_picking_id=delivery_order.id)\
                .create({
                    'name': 'lot1',
                    'product_id': self.productA.id,
                })

        # enter an existing lot_id, should work
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.productA.id,
        })
        move_line.lot_id = lot1
        delivery_order.action_done()

    def test_merge_moves_1(self):
        receipt = self.env['stock.picking'].create({
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_in,
        })
        self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 3,
            'product_uom': self.productA.uom_id.id,
            'picking_id': receipt.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
        })
        self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 5,
            'product_uom': self.productA.uom_id.id,
            'picking_id': receipt.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
        })
        self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 1,
            'product_uom': self.productA.uom_id.id,
            'picking_id': receipt.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
        })
        self.MoveObj.create({
            'name': self.productB.name,
            'product_id': self.productB.id,
            'product_uom_qty': 5,
            'product_uom': self.productB.uom_id.id,
            'picking_id': receipt.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
        })
        receipt.action_confirm()
        self.assertEqual(len(receipt.move_lines), 2, 'Moves were not merged')
        self.assertEqual(receipt.move_lines.filtered(lambda m: m.product_id == self.productA).product_uom_qty, 9, 'Merged quantity is not correct')
        self.assertEqual(receipt.move_lines.filtered(lambda m: m.product_id == self.productB).product_uom_qty, 5, 'Merge should not impact product B reserved quantity')

    def test_merge_moves_2(self):
        receipt = self.env['stock.picking'].create({
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_in,
        })
        self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 3,
            'product_uom': self.productA.uom_id.id,
            'picking_id': receipt.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'origin': 'MPS'
        })
        self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 5,
            'product_uom': self.productA.uom_id.id,
            'picking_id': receipt.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'origin': 'PO0001'
        })
        self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 3,
            'product_uom': self.productA.uom_id.id,
            'picking_id': receipt.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'origin': 'MPS'
        })
        receipt.action_confirm()
        self.assertEqual(len(receipt.move_lines), 1, 'Moves were not merged')
        self.assertEqual(receipt.move_lines.origin.count('MPS'), 1, 'Origin not merged together or duplicated')
        self.assertEqual(receipt.move_lines.origin.count('PO0001'), 1, 'Origin not merged together or duplicated')

    def test_merge_moves_3(self):
        """ Create 2 moves without initial_demand and already a
        quantity done. Check that we still have only 2 moves after
        validation.
        """
        receipt = self.env['stock.picking'].create({
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_in,
        })
        move_1 = self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 0,
            'product_uom': self.productA.uom_id.id,
            'picking_id': receipt.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'origin': 'MPS'
        })
        move_2 = self.MoveObj.create({
            'name': self.productB.name,
            'product_id': self.productB.id,
            'product_uom_qty': 0,
            'product_uom': self.productB.uom_id.id,
            'picking_id': receipt.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'origin': 'PO0001'
        })
        move_1.quantity_done = 5
        move_2.quantity_done = 5
        receipt.button_validate()
        self.assertEqual(len(receipt.move_lines), 2, 'Moves were not merged')

    def test_merge_chained_moves(self):
        """ Imagine multiple step delivery. Two different receipt picking for the same product should only generate
        1 picking from input to QC and another from QC to stock. The link at the end should follow this scheme.
        Move receipt 1 \
                        Move Input-> QC - Move QC -> Stock
        Move receipt 2 /
        """
        warehouse = self.env['stock.warehouse'].create({
            'name': 'TEST WAREHOUSE',
            'code': 'TEST1',
            'reception_steps': 'three_steps',
        })
        receipt1 = self.env['stock.picking'].create({
            'location_id': self.supplier_location,
            'location_dest_id': warehouse.wh_input_stock_loc_id.id,
            'partner_id': self.partner_delta_id,
            'picking_type_id': warehouse.in_type_id.id,
        })
        move_receipt_1 = self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 5,
            'product_uom': self.productA.uom_id.id,
            'picking_id': receipt1.id,
            'location_id': self.supplier_location,
            'location_dest_id': warehouse.wh_input_stock_loc_id.id,
        })
        receipt2 = self.env['stock.picking'].create({
            'location_id': self.supplier_location,
            'location_dest_id': warehouse.wh_input_stock_loc_id.id,
            'partner_id': self.partner_delta_id,
            'picking_type_id': warehouse.in_type_id.id,
        })
        move_receipt_2 = self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 3,
            'product_uom': self.productA.uom_id.id,
            'picking_id': receipt2.id,
            'location_id': self.supplier_location,
            'location_dest_id': warehouse.wh_input_stock_loc_id.id,
        })
        receipt1.action_confirm()
        receipt2.action_confirm()

        # Check following move has been created and grouped in one picking.
        self.assertTrue(move_receipt_1.move_dest_ids, 'No move created from push rules')
        self.assertTrue(move_receipt_2.move_dest_ids, 'No move created from push rules')
        self.assertEqual(move_receipt_1.move_dest_ids.picking_id, move_receipt_2.move_dest_ids.picking_id, 'Destination moves should be in the same picking')

        # Check link for input move are correct.
        input_move = move_receipt_2.move_dest_ids
        self.assertEqual(len(input_move.move_dest_ids), 1)
        self.assertEqual(set(input_move.move_orig_ids.ids), set((move_receipt_2 | move_receipt_1).ids),
                         'Move from input to QC should be merged and have the two receipt moves as origin.')
        self.assertEqual(move_receipt_1.move_dest_ids, input_move)
        self.assertEqual(move_receipt_2.move_dest_ids, input_move)

        # Check link for quality check move are also correct.
        qc_move = input_move.move_dest_ids
        self.assertEqual(len(qc_move), 1)
        self.assertTrue(qc_move.move_orig_ids == input_move, 'Move between QC and stock should only have the input move as origin')

    def test_empty_moves_validation_1(self):
        """ Use button validate on a picking that contains only moves
        without initial demand and without quantity done should be
        impossible and raise a usererror.
        """
        delivery_order = self.env['stock.picking'].create({
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_out,
        })
        self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 0,
            'product_uom': self.productA.uom_id.id,
            'picking_id': delivery_order.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
        })
        self.MoveObj.create({
            'name': self.productB.name,
            'product_id': self.productB.id,
            'product_uom_qty': 0,
            'product_uom': self.productB.uom_id.id,
            'picking_id': delivery_order.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
        })
        delivery_order.action_confirm()
        delivery_order.action_assign()
        with self.assertRaises(UserError):
            delivery_order.button_validate()

    def test_empty_moves_validation_2(self):
        """ Use button validate on a picking that contains only moves
        without initial demand but at least one with a quantity done
        should process the move with quantity done and cancel the
        other.
        """
        delivery_order = self.env['stock.picking'].create({
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_out,
        })
        move_a = self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 0,
            'product_uom': self.productA.uom_id.id,
            'picking_id': delivery_order.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
        })
        move_b = self.MoveObj.create({
            'name': self.productB.name,
            'product_id': self.productB.id,
            'product_uom_qty': 0,
            'product_uom': self.productB.uom_id.id,
            'picking_id': delivery_order.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
        })
        delivery_order.action_confirm()
        delivery_order.action_assign()
        move_a.quantity_done = 1
        delivery_order.button_validate()

        self.assertEqual(move_a.state, 'done')
        self.assertEqual(move_b.state, 'cancel')
        back_order = self.env['stock.picking'].search([('backorder_id', '=', delivery_order.id)])
        self.assertFalse(back_order, 'There should be no back order')


class TestStockUOM(TestStockCommon):
    def setUp(self):
        super(TestStockUOM, self).setUp()
        self.setUpCache()

    def setUpCache(self):
        dp = self.env.ref('product.decimal_product_uom')
        dp.digits = 7

        # Trick: invoke the method 'precision_get' with the current environment.
        # This fills in the cache of the method with the right value. If we
        # don't do that, the registry will access the corresponding precision
        # with a new cursor (LazyCursor), and get a different value!
        self.assertEqual(dp.precision_get(dp.name), 7)

    def test_pickings_transfer_with_different_uom_and_back_orders(self):
        """ Picking transfer with diffrent unit of meassure. """
        # weight category
        categ_test = self.env['uom.category'].create({'name': 'Bigger than tons'})

        T_LBS = self.env['uom.uom'].create({
            'name': 'T-LBS',
            'category_id': categ_test.id,
            'uom_type': 'reference',
            'rounding': 0.01
        })
        T_GT = self.env['uom.uom'].create({
            'name': 'T-GT',
            'category_id': categ_test.id,
            'uom_type': 'bigger',
            'rounding': 0.0000001,
            'factor_inv': 2240.00,
        })
        T_TEST = self.env['product.product'].create({
            'name': 'T_TEST',
            'type': 'product',
            'uom_id': T_LBS.id,
            'uom_po_id': T_LBS.id,
            'tracking': 'lot',
        })

        # creating a variant invalidates the cache
        self.setUpCache()

        picking_in = self.env['stock.picking'].create({
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_in,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location
        })
        move = self.env['stock.move'].create({
            'name': 'First move with 60 GT',
            'product_id': T_TEST.id,
            'product_uom_qty': 60,
            'product_uom': T_GT.id,
            'picking_id': picking_in.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location
        })
        picking_in.action_confirm()

        self.assertEqual(move.product_uom_qty, 60.00, 'Wrong T_GT quantity')
        self.assertEqual(move.product_qty, 134400.00, 'Wrong T_LBS quantity')

        lot = self.env['stock.production.lot'].create({'name': 'Lot TEST', 'product_id': T_TEST.id})
        self.env['stock.move.line'].create({
            'move_id': move.id,
            'product_id': T_TEST.id,
            'product_uom_id': T_LBS.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'qty_done': 42760.00,
            'lot_id': lot.id,
        })

        picking_in.action_done()
        back_order_in = self.env['stock.picking'].search([('backorder_id', '=', picking_in.id)])

        self.assertEqual(len(back_order_in), 1.00, 'There should be one back order created')
        self.assertEqual(back_order_in.move_lines.product_qty, 91640.00, 'There should be one back order created')


class TestRoutes(TestStockCommon):
    def setUp(self):
        super(TestRoutes, self).setUp()
        self.product1 = self.env['product.product'].create({
            'name': 'product a',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        self.uom_unit = self.env.ref('uom.product_uom_unit')

    def _enable_pick_ship(self):
        self.wh = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.id)], limit=1)

        # create and get back the pick ship route
        self.wh.write({'delivery_steps': 'pick_ship'})
        
        self.pick_ship_route = self.wh.route_ids.filtered(lambda r: '(pick + ship)' in r.name)
    def test_pick_ship_1(self):
        """ Enable the pick ship route, force a procurement group on the
        pick. When a second move is added, make sure the `partner_id` and
        `origin` fields are erased.
        """
        self._enable_pick_ship()

        # create a procurement group and set in on the pick stock rule
        procurement_group0 = self.env['procurement.group'].create({})
        pick_rule = self.pick_ship_route.rule_ids.filtered(lambda rule: 'Stock → Output' in rule.name)
        push_rule = self.pick_ship_route.rule_ids - pick_rule
        pick_rule.write({
            'group_propagation_option': 'fixed',
            'group_id': procurement_group0.id,
        })

        ship_location = pick_rule.location_id
        customer_location = push_rule.location_id
        partners = self.env['res.partner'].search([], limit=2)
        partner0 = partners[0]
        partner1 = partners[1]
        procurement_group1 = self.env['procurement.group'].create({'partner_id': partner0.id})
        procurement_group2 = self.env['procurement.group'].create({'partner_id': partner1.id})

        move1 = self.env['stock.move'].create({
            'name': 'first out move',
            'procure_method': 'make_to_order',
            'location_id': ship_location.id,
            'location_dest_id': customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'warehouse_id': self.wh.id,
            'group_id': procurement_group1.id,
            'origin': 'origin1',
        })

        move2 = self.env['stock.move'].create({
            'name': 'second out move',
            'procure_method': 'make_to_order',
            'location_id': ship_location.id,
            'location_dest_id': customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'warehouse_id': self.wh.id,
            'group_id': procurement_group2.id,
            'origin': 'origin2',
        })

        # first out move, the "pick" picking should have a partner and an origin
        move1._action_confirm()
        picking_pick = move1.move_orig_ids.picking_id
        self.assertEqual(picking_pick.partner_id.id, procurement_group1.partner_id.id)
        self.assertEqual(picking_pick.origin, move1.group_id.name)

        # second out move, the "pick" picking should have lost its partner and origin
        move2._action_confirm()
        self.assertEqual(picking_pick.partner_id.id, False)
        self.assertEqual(picking_pick.origin, False)

    def test_replenish_pick_ship_1(self):
        """ Creates 2 warehouses and make a replenish using one warehouse
        to ressuply the other one, Then check if the quantity and the product are matching
        """
        self.product_uom_qty = 42

        warehouse_1 = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.id)], limit=1)
        warehouse_2 = self.env['stock.warehouse'].create({
            'name': 'Small Warehouse',
            'code': 'SWH'
        })
        warehouse_1.write({
            'resupply_wh_ids': [(6, 0, [warehouse_2.id])]
        })
        resupply_route = self.env['stock.location.route'].search([('supplier_wh_id', '=', warehouse_2.id), ('supplied_wh_id', '=', warehouse_1.id)])
        self.assertTrue(resupply_route, "Ressuply route not found")
        self.product1.write({'route_ids': [(4, resupply_route.id), (4, self.env.ref('stock.route_warehouse0_mto').id)]})
        self.wh = warehouse_1

        replenish_wizard = self.env['product.replenish'].create({
            'product_id': self.product1.id,
            'product_tmpl_id': self.product1.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'quantity': self.product_uom_qty,
            'warehouse_id': self.wh.id,
        })

        replenish_wizard.launch_replenishment()
        last_picking_id = self.env['stock.picking'].search([('origin', '=', 'Manual Replenishment')])[-1]
        self.assertTrue(last_picking_id, 'Picking not found')
        move_line = last_picking_id.move_lines.search([('product_id','=', self.product1.id)])
        self.assertTrue(move_line,'The product is not in the picking')
        self.assertEqual(move_line[0].product_uom_qty, self.product_uom_qty, 'Quantities does not match')
        self.assertEqual(move_line[1].product_uom_qty, self.product_uom_qty, 'Quantities does not match')

    def test_push_rule_on_move_1(self):
        """ Create a route with a push rule, force it on a move, check that it is applied.
        """
        self._enable_pick_ship()
        stock_location = self.env.ref('stock.stock_location_stock')

        push_location = self.env['stock.location'].create({
            'location_id': stock_location.location_id.id,
            'name': 'push location',
        })

        # TODO: maybe add a new type on the "applicable on" fields?
        route = self.env['stock.location.route'].create({
            'name': 'new route',
            'rule_ids': [(0, False, {
                'name': 'create a move to push location',
                'location_src_id': stock_location.id,
                'location_id': push_location.id,
                'company_id': self.env.user.company_id.id,
                'action': 'push',
                'auto': 'manual',
                'picking_type_id': self.env.ref('stock.picking_type_in').id,
            })],
        })
        move1 = self.env['stock.move'].create({
            'name': 'move with a route',
            'location_id': stock_location.id,
            'location_dest_id': stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'route_ids': [(4, route.id)]
        })
        move1._action_confirm()

        pushed_move = move1.move_dest_ids
        self.assertEqual(pushed_move.location_dest_id.id, push_location.id)

    def test_mtso_mto(self):
        """ Run a procurement for 5 products when there are only 4 in stock then
        check that MTO is applied on the moves when the rule is set to 'mts_else_mto'
        """
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.id)], limit=1)
        warehouse.delivery_steps = 'pick_pack_ship'
        partner_demo_customer = self.env.ref('base.res_partner_1')
        final_location = partner_demo_customer.property_stock_customer
        product_a = self.env['product.product'].create({
            'name': 'ProductA',
            'type': 'product',
        })

        self.env['stock.quant']._update_available_quantity(product_a, warehouse.wh_output_stock_loc_id, 4.0)

        # We set quantities in the stock location to avoid warnings
        # triggered by '_onchange_product_id_check_availability'
        self.env['stock.quant']._update_available_quantity(product_a, warehouse.lot_stock_id, 4.0)

        # We alter one rule and we set it to 'mts_else_mto'
        values = {'warehouse_id': warehouse}
        rule = self.env['procurement.group']._get_rule(product_a, final_location, values)
        rule.procure_method = 'mts_else_mto'

        pg = self.env['procurement.group'].create({'name': 'Test-pg-mtso-mto'})

        self.env['procurement.group'].run([
            pg.Procurement(
                product_a,
                5.0,
                product_a.uom_id,
                final_location,
                'test_mtso_mto',
                'test_mtso_mto',
                warehouse.company_id,
                {
                    'warehouse_id': warehouse,
                    'group_id': pg
                }
            )
        ])

        qty_available = self.env['stock.quant']._get_available_quantity(product_a, warehouse.wh_output_stock_loc_id)

        # 3 pickings should be created.
        picking_ids = self.env['stock.picking'].search([('group_id', '=', pg.id)])
        self.assertEquals(len(picking_ids), 3)
        for picking in picking_ids:
            # Only the picking from Stock to Pack should be MTS
            if picking.location_id == warehouse.lot_stock_id:
                self.assertEquals(picking.move_lines.procure_method, 'make_to_stock')
            else:
                self.assertEquals(picking.move_lines.procure_method, 'make_to_order')

            self.assertEquals(len(picking.move_lines), 1)
            self.assertEquals(picking.move_lines.product_uom_qty, 5, 'The quantity of the move should be the same as on the SO')
        self.assertEqual(qty_available, 4, 'The 4 products should still be available')

    def test_mtso_mts(self):
        """ Run a procurement for 4 products when there are 4 in stock then
        check that MTS is applied on the moves when the rule is set to 'mts_else_mto'
        """
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.id)], limit=1)
        warehouse.delivery_steps = 'pick_pack_ship'
        partner_demo_customer = self.env.ref('base.res_partner_1')
        final_location = partner_demo_customer.property_stock_customer
        product_a = self.env['product.product'].create({
            'name': 'ProductA',
            'type': 'product',
        })

        self.env['stock.quant']._update_available_quantity(product_a, warehouse.wh_output_stock_loc_id, 4.0)

        # We alter one rule and we set it to 'mts_else_mto'
        values = {'warehouse_id': warehouse}
        rule = self.env['procurement.group']._get_rule(product_a, final_location, values)
        rule.procure_method = 'mts_else_mto'

        pg = self.env['procurement.group'].create({'name': 'Test-pg-mtso-mts'})

        self.env['procurement.group'].run([
            pg.Procurement(
                product_a,
                4.0,
                product_a.uom_id,
                final_location,
                'test_mtso_mts',
                'test_mtso_mts',
                warehouse.company_id,
                {
                    'warehouse_id': warehouse,
                    'group_id': pg
                }
            )
        ])

        # A picking should be created with its move having MTS as procure method.
        picking_ids = self.env['stock.picking'].search([('group_id', '=', pg.id)])
        self.assertEquals(len(picking_ids), 1)
        picking = picking_ids
        self.assertEquals(picking.move_lines.procure_method, 'make_to_stock')
        self.assertEquals(len(picking.move_lines), 1)
        self.assertEquals(picking.move_lines.product_uom_qty, 4)

    def test_mtso_multi_pg(self):
        """ Run 3 procurements for 2 products at the same times when there are 4 in stock then
        check that MTS is applied on the moves when the rule is set to 'mts_else_mto'
        """
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.id)], limit=1)
        warehouse.delivery_steps = 'pick_pack_ship'
        partner_demo_customer = self.env.ref('base.res_partner_1')
        final_location = partner_demo_customer.property_stock_customer
        product_a = self.env['product.product'].create({
            'name': 'ProductA',
            'type': 'product',
        })

        self.env['stock.quant']._update_available_quantity(product_a, warehouse.wh_output_stock_loc_id, 4.0)

        # We alter one rule and we set it to 'mts_else_mto'
        values = {'warehouse_id': warehouse}
        rule = self.env['procurement.group']._get_rule(product_a, final_location, values)
        rule.procure_method = 'mts_else_mto'

        pg1 = self.env['procurement.group'].create({'name': 'Test-pg-mtso-mts-1'})
        pg2 = self.env['procurement.group'].create({'name': 'Test-pg-mtso-mts-2'})
        pg3 = self.env['procurement.group'].create({'name': 'Test-pg-mtso-mts-3'})

        self.env['procurement.group'].run([
            pg1.Procurement(
                product_a,
                2.0,
                product_a.uom_id,
                final_location,
                'test_mtso_mts_1',
                'test_mtso_mts_1',
                warehouse.company_id,
                {
                    'warehouse_id': warehouse,
                    'group_id': pg1
                }
            ),
            pg2.Procurement(
                product_a,
                2.0,
                product_a.uom_id,
                final_location,
                'test_mtso_mts_2',
                'test_mtso_mts_2',
                warehouse.company_id,
                {
                    'warehouse_id': warehouse,
                    'group_id': pg2
                }
            ),
            pg3.Procurement(
                product_a,
                2.0,
                product_a.uom_id,
                final_location,
                'test_mtso_mts_3',
                'test_mtso_mts_3',
                warehouse.company_id,
                {
                    'warehouse_id': warehouse,
                    'group_id': pg3
                }
            )
        ])

        pickings_pg1 = self.env['stock.picking'].search([('group_id', '=', pg1.id)])
        pickings_pg2 = self.env['stock.picking'].search([('group_id', '=', pg2.id)])
        pickings_pg3 = self.env['stock.picking'].search([('group_id', '=', pg3.id)])

        # The 2 first procurements should have create only 1 picking since enough quantities
        # are left in the delivery location
        self.assertEquals(len(pickings_pg1), 1)
        self.assertEquals(len(pickings_pg2), 1)
        self.assertEquals(pickings_pg1.move_lines.procure_method, 'make_to_stock')
        self.assertEquals(pickings_pg2.move_lines.procure_method, 'make_to_stock')

        # The last one should have 3 pickings as there's nothing left in the delivery location
        self.assertEquals(len(pickings_pg3), 3)
        for picking in pickings_pg3:
            # Only the picking from Stock to Pack should be MTS
            if picking.location_id == warehouse.lot_stock_id:
                self.assertEquals(picking.move_lines.procure_method, 'make_to_stock')
            else:
                self.assertEquals(picking.move_lines.procure_method, 'make_to_order')

            # All the moves should be should have the same quantity as it is on each procurements
            self.assertEquals(len(picking.move_lines), 1)
            self.assertEquals(picking.move_lines.product_uom_qty, 2)
