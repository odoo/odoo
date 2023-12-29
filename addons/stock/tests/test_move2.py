# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo.addons.stock.tests.common import TestStockCommon
from odoo.exceptions import UserError

from odoo.tests import Form
from odoo.tools import float_is_zero, float_compare

from datetime import datetime
from dateutil.relativedelta import relativedelta

class TestPickShip(TestStockCommon):
    def create_pick_ship(self):
        picking_client = self.env['stock.picking'].create({
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
            'picking_type_id': self.picking_type_out,
            'state': 'draft',
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
            'picking_type_id': self.picking_type_out,
            'state': 'draft',
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
            'location_id': self.output_location,
            'location_dest_id': self.customer_location,
            'picking_type_id': self.picking_type_out,
            'state': 'draft',
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
            'location_id': self.pack_location,
            'location_dest_id': self.output_location,
            'picking_type_id': self.picking_type_out,
            'state': 'draft',
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
            'picking_type_id': self.picking_type_out,
            'state': 'draft',
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

    def test_unreserve_only_required_quantity(self):
        product_unreserve = self.env['product.product'].create({
            'name': 'product unreserve',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        stock_location = self.env['stock.location'].browse(self.stock_location)
        self.env['stock.quant']._update_available_quantity(product_unreserve, stock_location, 4.0)
        quants = self.env['stock.quant']._gather(product_unreserve, stock_location, strict=True)
        self.assertEqual(quants[0].reserved_quantity, 0)
        move = self.MoveObj.create({
            'name': product_unreserve.name,
            'product_id': product_unreserve.id,
            'product_uom_qty': 3,
            'product_uom': product_unreserve.uom_id.id,
            'state': 'confirmed',
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
        })
        move._action_assign()
        self.assertEqual(quants[0].reserved_quantity, 3)
        move_2 = self.MoveObj.create({
            'name': product_unreserve.name,
            'product_id': product_unreserve.id,
            'product_uom_qty': 2,
            'quantity': 2,
            'product_uom': product_unreserve.uom_id.id,
            'state': 'confirmed',
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
        })
        move_2._action_assign()
        move_2.picked = True
        move_2._action_done()
        quants = self.env['stock.quant']._gather(product_unreserve, stock_location, strict=True)
        self.assertEqual(quants[0].reserved_quantity, 2)


    def test_mto_moves(self):
        """
            10 in stock, do pick->ship and check ship is assigned when pick is done, then backorder of ship
        """
        picking_pick, picking_client = self.create_pick_ship()
        location = self.env['stock.location'].browse(self.stock_location)

        # make some stock
        self.env['stock.quant']._update_available_quantity(self.productA, location, 10.0)
        picking_pick.action_assign()
        picking_pick.move_ids[0].move_line_ids[0].quantity = 10.0
        picking_pick.move_ids[0].picked = True
        picking_pick._action_done()

        self.assertEqual(picking_client.state, 'assigned', 'The state of the client should be assigned')

        # Now partially transfer the ship
        picking_client.move_ids[0].move_line_ids[0].quantity = 5
        picking_client.move_ids[0].picked = True
        picking_client._action_done()  # no new in order to create backorder

        backorder = self.env['stock.picking'].search([('backorder_id', '=', picking_client.id)])
        self.assertEqual(backorder.state, 'confirmed', 'Backorder should be waiting for reservation')

    def test_mto_to_mts(self):
        """
            10 in stock, create pick and ship, change destination of pick, ship should become MTS
        """
        picking_pick, picking_ship = self.create_pick_ship()
        self.env['stock.quant'].create({
            'product_id': self.productA.id,
            'location_id': self.stock_location,
            'quantity': 10
        })
        (picking_pick + picking_ship).action_assign()
        self.assertEqual(picking_pick.state, 'assigned')
        self.assertEqual(picking_ship.state, 'waiting')
        self.assertEqual(picking_ship.move_ids.procure_method, 'make_to_order')
        picking_pick.location_dest_id = self.output_location
        picking_pick.move_ids.location_dest_id = self.output_location
        picking_pick.move_ids.picked = True
        picking_pick.button_validate()
        self.assertEqual(picking_pick.state, 'done')
        self.assertEqual(picking_ship.state, 'confirmed')
        # ship source location remains unchanged
        self.assertEqual(picking_ship.location_id.id, self.pack_location)
        self.assertEqual(picking_ship.move_ids.procure_method, 'make_to_stock')

    def test_mto_to_mts_2(self):
        """
            10 in stock, create pick and ship, cancel pick, ship should become MTS
        """
        picking_pick, picking_ship = self.create_pick_ship()
        self.env['stock.quant'].create({
            'product_id': self.productA.id,
            'location_id': self.stock_location,
            'quantity': 10
        })
        (picking_pick + picking_ship).action_assign()
        self.assertEqual(picking_pick.state, 'assigned')
        self.assertEqual(picking_ship.state, 'waiting')
        self.assertEqual(picking_ship.move_ids.procure_method, 'make_to_order')
        # this prevents cancel of ship move
        picking_pick.move_ids.propagate_cancel = False
        picking_pick.action_cancel()
        self.assertEqual(picking_pick.state, 'cancel')
        self.assertEqual(picking_ship.state, 'confirmed')
        self.assertEqual(picking_ship.move_ids.procure_method, 'make_to_stock')

    def test_mto_to_mts_3(self):
        """
            10 in stock, create pick and ship, change source of ship, ship should become MTS
        """
        picking_pick, picking_ship = self.create_pick_ship()
        self.env['stock.quant'].create({
            'product_id': self.productA.id,
            'location_id': self.stock_location,
            'quantity': 10
        })
        (picking_pick + picking_ship).action_assign()
        self.assertEqual(picking_pick.state, 'assigned')
        self.assertEqual(picking_ship.state, 'waiting')
        self.assertEqual(picking_ship.move_ids.procure_method, 'make_to_order')
        picking_ship.location_id = self.output_location
        picking_ship.move_ids.location_id = self.output_location
        picking_pick.move_ids.picked = True
        picking_pick.button_validate()
        self.assertEqual(picking_pick.state, 'done')
        self.assertEqual(picking_ship.state, 'confirmed')
        # pick destination location remains unchanged
        self.assertEqual(picking_pick.location_dest_id.id, self.pack_location)
        self.assertEqual(picking_ship.move_ids.procure_method, 'make_to_stock')

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

        move_pick = picking_pick.move_ids
        move_cust = picking_client.move_ids
        self.assertEqual(move_pick.state, 'assigned')
        self.assertEqual(picking_pick.state, 'assigned')
        self.assertEqual(move_cust.state, 'waiting')
        self.assertEqual(picking_client.state, 'waiting', 'The picking should not assign what it does not have')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, stock_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, pack_location), 5.0)

        move_pick.move_line_ids[0].quantity = 10.0
        move_pick.picked = True
        picking_pick._action_done()

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
        picking_pick.move_ids[0].move_line_ids[0].quantity = 10.0
        picking_pick.move_ids[0].picked = True
        picking_pick._action_done()
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
        return_pick.move_ids[0].move_line_ids[0].quantity = 2.0
        return_pick.move_ids[0].picked = True
        return_pick._action_done()
        # the client picking should not be assigned anymore, as we returned partially what we took
        self.assertEqual(picking_client.state, 'confirmed')

    def test_mto_moves_extra_qty(self):
        """ Ensure that a move in MTO will support an extra quantity. The extra
        move should be created in MTS even if the initial move is in MTO so that
        it won't trigger the rules. The extra move will then be merge back to the
        initial move.
        """
        picking_pick, picking_client = self.create_pick_ship()
        stock_location = self.env['stock.location'].browse(self.stock_location)
        self.productA.write({'route_ids': [(4, self.env.ref('stock.route_warehouse0_mto').id)]})
        self.env['stock.quant']._update_available_quantity(self.productA, stock_location, 10.0)
        picking_pick.action_assign()
        picking_pick.move_ids[0].move_line_ids[0].quantity = 15.0
        picking_pick.move_ids[0].picked = True
        picking_pick._action_done()
        self.assertEqual(picking_pick.state, 'done')
        self.assertEqual(picking_client.state, 'assigned')

        picking_client.move_ids[0].move_line_ids[0].quantity = 15.0
        picking_client.move_ids[0].picked = True
        picking_client.move_ids._action_done()
        self.assertEqual(len(picking_client.move_ids), 1)
        move = picking_client.move_ids
        self.assertEqual(move.procure_method, 'make_to_order')
        self.assertEqual(move.product_uom_qty, 10.0)
        self.assertEqual(move.quantity, 15.0)

    def test_mto_moves_return_extra(self):
        picking_pick, picking_client = self.create_pick_ship()
        stock_location = self.env['stock.location'].browse(self.stock_location)
        self.env['stock.quant']._update_available_quantity(self.productA, stock_location, 10.0)

        picking_pick.action_assign()
        picking_pick.move_ids[0].move_line_ids[0].quantity = 10.0
        picking_pick.move_ids[0].picked = True
        picking_pick._action_done()
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
        self.assertAlmostEqual(return_pick.move_ids.product_uom_qty, 12.0)
        self.assertAlmostEqual(return_pick.move_ids.quantity, 10.0)

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
        resupply_route = self.env['stock.route'].search([('supplier_wh_id', '=', warehouse_2.id), ('supplied_wh_id', '=', warehouse_1.id)])
        self.assertTrue(resupply_route)
        self.productA.write({'route_ids': [(4, resupply_route.id), (4, self.env.ref('stock.route_warehouse0_mto').id)]})

        self.env['stock.quant']._update_available_quantity(self.productA, stock_location, 10.0)

        picking_pick.action_assign()
        picking_pick.move_ids[0].move_line_ids[0].quantity = 10.0
        picking_pick.move_ids[0].picked = True
        picking_pick._action_done()

        picking_pack.action_assign()
        picking_pack.move_ids[0].move_line_ids[0].quantity = 10.0
        picking_pack.move_ids[0].picked = True
        picking_pack._action_done()

        picking_ship.action_cancel()
        picking_ship.move_ids.write({'procure_method': 'make_to_order'})

        self.env['procurement.group'].run_scheduler()
        next_activity = self.env['mail.activity'].search([('res_model', '=', 'product.template'), ('res_id', '=', self.productA.product_tmpl_id.id)])
        self.assertEqual(picking_ship.state, 'cancel')
        self.assertFalse(next_activity, 'If a next activity has been created if means that scheduler failed\
        and the end of this test do not have sense.')
        self.assertEqual(len(picking_ship.move_ids.mapped('move_orig_ids')), 0,
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
        picking_pick.move_ids[0].move_line_ids[0].quantity = 5.0
        picking_pick.move_ids[0].picked = True

        # create a backorder
        picking_pick._action_done()
        picking_pick_backorder = self.env['stock.picking'].search([('backorder_id', '=', picking_pick.id)])
        self.assertEqual(picking_pick_backorder.state, 'confirmed')
        self.assertEqual(picking_pick_backorder.move_ids.product_qty, 5.0)

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
        picking_pick.move_ids[0].move_line_ids[0].quantity = 10.0
        picking_pick.move_ids[0].picked = True
        picking_pick._action_done()

        self.assertEqual(picking_pick.state, 'done', 'The state of the pick should be done')
        self.assertEqual(picking_client.state, 'assigned', 'The state of the client should be assigned')
        self.assertEqual(picking_pick.move_ids.quantity, 10.0, 'Wrong quantity for pick move')
        self.assertEqual(picking_client.move_ids.product_qty, 10.0, 'Wrong initial demand for client move')
        self.assertEqual(picking_client.move_ids.quantity, 10.0, 'Wrong quantity already reserved for client move')

        picking_pick.move_ids[0].move_line_ids[0].quantity = 5.0
        self.assertEqual(picking_pick.state, 'done', 'The state of the pick should be done')
        self.assertEqual(picking_client.state, 'assigned', 'The state of the client should be partially available')
        self.assertEqual(picking_pick.move_ids.quantity, 5.0, 'Wrong quantity for pick move')
        self.assertEqual(picking_client.move_ids.product_qty, 10.0, 'Wrong initial demand for client move')
        self.assertEqual(picking_client.move_ids.quantity, 5.0, 'Wrong quantity already reserved for client move')

        # Check if run action_assign does not crash
        picking_client.action_assign()

    def test_edit_done_chained_move_with_lot(self):
        """ Let’s say two moves are chained: the first is done and the second is assigned.
        Editing the lot on the move line of the first move should impact the reservation of the second one.
        """
        self.productA.tracking = 'lot'
        lot1 = self.env['stock.lot'].create({
            'name': 'lot1',
            'product_id': self.productA.id,
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.lot'].create({
            'name': 'lot2',
            'product_id': self.productA.id,
            'company_id': self.env.company.id,
        })
        picking_pick, picking_client = self.create_pick_ship()
        location = self.env['stock.location'].browse(self.stock_location)

        # make some stock
        self.env['stock.quant']._update_available_quantity(self.productA, location, 10.0)
        picking_pick.action_assign()
        picking_pick.move_ids[0].move_line_ids[0].write({
            'quantity': 10.0,
            'lot_id': lot1.id,
        })
        picking_pick.move_ids[0].picked = True
        picking_pick._action_done()

        self.assertEqual(picking_pick.state, 'done', 'The state of the pick should be done')
        self.assertEqual(picking_client.state, 'assigned', 'The state of the client should be assigned')
        self.assertEqual(picking_pick.move_ids.quantity, 10.0, 'Wrong quantity for pick move')
        self.assertEqual(picking_client.move_ids.product_qty, 10.0, 'Wrong initial demand for client move')
        self.assertEqual(picking_client.move_ids.move_line_ids.lot_id, lot1, 'Wrong lot for client move line')
        self.assertEqual(picking_client.move_ids.quantity, 10.0, 'Wrong quantity already reserved for client move')

        picking_pick.move_ids[0].move_line_ids[0].lot_id = lot2.id
        self.assertEqual(picking_pick.state, 'done', 'The state of the pick should be done')
        self.assertEqual(picking_client.state, 'assigned', 'The state of the client should be partially available')
        self.assertEqual(picking_pick.move_ids.quantity, 10.0, 'Wrong quantity for pick move')
        self.assertEqual(picking_client.move_ids.product_qty, 10.0, 'Wrong initial demand for client move')
        self.assertEqual(picking_client.move_ids.move_line_ids.lot_id, lot2, 'Wrong lot for client move line')
        self.assertEqual(picking_client.move_ids.quantity, 10.0, 'Wrong quantity already reserved for client move')

        # Check if run action_assign does not crash
        picking_client.action_assign()

    def test_chained_move_with_uom(self):
        """ Create pick ship with a different uom than the once used for quant.
        Check that reserved quantity and flow work correctly.
        """
        picking_client = self.env['stock.picking'].create({
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
            'picking_type_id': self.picking_type_out,
            'state': 'draft',
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
            'picking_type_id': self.picking_type_out,
            'state': 'draft',
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
        picking_pick.move_ids[0].move_line_ids[0].quantity = 5.0
        picking_pick.move_ids[0].picked = True
        picking_pick._action_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.gB, location), 5000.0)
        self.assertEqual(self.env['stock.quant']._gather(self.gB, pack_location).quantity, 5000.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.gB, pack_location), 0.0)
        self.assertEqual(picking_client.state, 'assigned')
        self.assertEqual(picking_client.move_ids.quantity, 5.0)

    def test_pick_ship_return(self):
        """ Create pick and ship. Bring it to the customer and then return
        it to stock. This test check the state and the quantity after each move in
        order to ensure that it is correct.
        """
        picking_pick, picking_ship = self.create_pick_ship()
        stock_location = self.env['stock.location'].browse(self.stock_location)
        pack_location = self.env['stock.location'].browse(self.pack_location)
        customer_location = self.env['stock.location'].browse(self.customer_location)
        self.productA.tracking = 'lot'
        lot = self.env['stock.lot'].create({
            'product_id': self.productA.id,
            'name': '123456789',
            'company_id': self.env.company.id,
        })
        self.env['stock.quant']._update_available_quantity(self.productA, stock_location, 10.0, lot_id=lot)

        picking_pick.action_assign()
        picking_pick.move_ids.picked = True
        picking_pick._action_done()
        self.assertEqual(picking_pick.state, 'done')
        self.assertEqual(picking_ship.state, 'assigned')

        picking_ship.action_assign()
        picking_ship.move_ids.picked = True
        picking_ship._action_done()

        customer_quantity = self.env['stock.quant']._get_available_quantity(self.productA, customer_location, lot_id=lot)
        self.assertEqual(customer_quantity, 10, 'It should be one product in customer')

        # First we create the return picking for pick picking.
        # Since we do not have created the return between customer and
        # output. This return should not be available and should only have
        # picking pick as origin move.

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
        self.assertTrue(return_ship_picking.move_ids in return_pick_picking.move_ids.mapped('move_orig_ids'),
                        'The pick return picking\'s moves should have the ship return picking\'s moves as origin')

        self.assertTrue(return_pick_picking.move_ids in return_ship_picking.move_ids.mapped('move_dest_ids'),
                        'The ship return picking\'s moves should have the pick return picking\'s moves as destination')

        return_ship_picking.move_ids[0].move_line_ids[0].write({
            'quantity': 10.0,
            'lot_id': lot.id,
        })
        return_ship_picking.move_ids.picked = True
        return_ship_picking._action_done()
        self.assertEqual(return_ship_picking.state, 'done')
        self.assertEqual(return_pick_picking.state, 'assigned')

        customer_quantity = self.env['stock.quant']._get_available_quantity(self.productA, customer_location, lot_id=lot)
        self.assertEqual(customer_quantity, 0, 'It should be one product in customer')

        pack_quantity = self.env['stock.quant']._get_available_quantity(self.productA, pack_location, lot_id=lot)
        self.assertEqual(pack_quantity, 0, 'It should be one product in pack location but is reserved')

        # Should use previous move lot.
        return_pick_picking.move_ids[0].move_line_ids[0].quantity = 10.0
        return_pick_picking.move_ids[0].picked = True
        return_pick_picking._action_done()
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
        lot = self.env['stock.lot'].create({
            'product_id': self.productA.id,
            'name': '123456789',
            'company_id': self.env.company.id,
        })
        self.env['stock.quant']._update_available_quantity(self.productA, stock_location, 1.0, lot_id=lot)

        picking_pick.action_assign()
        picking_pick.move_ids[0].move_line_ids[0].quantity = 1.0
        picking_pick.move_ids[0].picked = True
        picking_pick._action_done()

        picking_pack.action_assign()
        picking_pack.move_ids[0].move_line_ids[0].quantity = 1.0
        picking_pack.move_ids[0].picked = True
        picking_pack._action_done()

        picking_ship.action_assign()
        picking_ship.move_ids[0].move_line_ids[0].quantity = 1.0
        picking_ship.move_ids[0].picked = True
        picking_ship._action_done()

        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=picking_ship.ids, active_id=picking_ship.ids[0],
            active_model='stock.picking'))
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 1.0
        stock_return_picking_action = stock_return_picking.create_returns()
        return_ship_picking = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])

        return_ship_picking.move_ids[0].move_line_ids[0].write({
            'quantity': 1.0,
            'lot_id': lot.id,
        })
        return_ship_picking.move_ids[0].picked = True
        return_ship_picking._action_done()

        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=picking_pack.ids, active_id=picking_pack.ids[0],
            active_model='stock.picking'))
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 1.0
        stock_return_picking_action = stock_return_picking.create_returns()
        return_pack_picking = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])

        return_pack_picking.move_ids[0].move_line_ids[0].quantity = 1.0
        return_pack_picking.move_ids[0].picked = True
        return_pack_picking._action_done()

        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=picking_pick.ids, active_id=picking_pick.ids[0],
            active_model='stock.picking'))
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 1.0
        stock_return_picking_action = stock_return_picking.create_returns()
        return_pick_picking = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])

        return_pick_picking.move_ids[0].move_line_ids[0].quantity = 1.0
        return_pick_picking.move_ids[0].picked = True
        return_pick_picking._action_done()

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

        self.assertEqual(len(picking_pick.move_ids.move_orig_ids), 0, 'Picking pick should not have origin moves')
        self.assertEqual(set(picking_pick.move_ids.move_dest_ids.ids), set((picking_pack.move_ids | return_pick_picking.move_ids).ids))

        self.assertEqual(set(picking_pack.move_ids.move_orig_ids.ids), set(picking_pick.move_ids.ids))
        self.assertEqual(set(picking_pack.move_ids.move_dest_ids.ids), set((picking_ship.move_ids | return_pack_picking.move_ids).ids))

        self.assertEqual(set(picking_ship.move_ids.move_orig_ids.ids), set(picking_pack.move_ids.ids))
        self.assertEqual(set(picking_ship.move_ids.move_dest_ids.ids), set(return_ship_picking.move_ids.ids))

        self.assertEqual(set(return_ship_picking.move_ids.move_orig_ids.ids), set(picking_ship.move_ids.ids))
        self.assertEqual(set(return_ship_picking.move_ids.move_dest_ids.ids), set(return_pack_picking.move_ids.ids))

        self.assertEqual(set(return_pack_picking.move_ids.move_orig_ids.ids), set((picking_pack.move_ids | return_ship_picking.move_ids).ids))
        self.assertEqual(set(return_pack_picking.move_ids.move_dest_ids.ids), set(return_pick_picking.move_ids.ids))

        self.assertEqual(set(return_pick_picking.move_ids.move_orig_ids.ids), set((picking_pick.move_ids | return_pack_picking.move_ids).ids))
        self.assertEqual(len(return_pick_picking.move_ids.move_dest_ids), 0)

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
        self.assertEqual(len(picking_client.move_ids), 2, 'Moves should not be merged')

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
        picking_pick.move_ids.quantity = 5.0
        picking_pick.move_ids.picked = True
        backorder_wizard_values = picking_pick.button_validate()
        backorder_wizard = self.env[(backorder_wizard_values.get('res_model'))].browse(backorder_wizard_values.get('res_id')).with_context(backorder_wizard_values['context'])
        backorder_wizard.process()

        self.assertTrue(picking_client.move_line_ids, 'A move line should be created.')
        self.assertEqual(picking_client.move_line_ids.quantity, 5, 'The move line should have 5 unit reserved.')

        # Directly delete the move lines on the picking. (Use show detail operation on picking type)
        # Should do the same behavior than unreserve
        picking_client.move_line_ids.unlink()

        self.assertEqual(picking_client.move_ids.state, 'waiting', 'The move state should be waiting since nothing is reserved and another origin move still in progess.')
        self.assertEqual(picking_client.state, 'waiting', 'The picking state should not be ready anymore.')

        picking_client.action_assign()

        back_order = self.env['stock.picking'].search([('backorder_id', '=', picking_pick.id)])
        back_order.move_ids.quantity = 5
        back_order.move_ids.picked = True
        back_order.button_validate()

        self.assertEqual(picking_client.move_ids.quantity, 10, 'The total quantity should be reserved since everything is available.')
        picking_client.move_line_ids.unlink()

        self.assertEqual(picking_client.move_ids.state, 'confirmed', 'The move should be confirmed since all the origin moves are processed.')
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
        picking_pick.move_ids[0].move_line_ids[0].quantity = 10.0
        picking_pick.move_ids[0].picked = True
        picking_pick._action_done()
        picking_client.move_ids[0].move_line_ids[0].quantity = 10.0
        picking_client.move_ids[0].picked = True
        picking_client._action_done()

        # return half in the pick location
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=picking_client.ids, active_id=picking_client.ids[0],
            active_model='stock.picking'))
        return1 = stock_return_picking_form.save()
        return1.product_return_moves.quantity = 5.0
        return1.location_id = pick_location.id
        return_to_pick_picking_action = return1.create_returns()

        return_to_pick_picking = self.env['stock.picking'].browse(return_to_pick_picking_action['res_id'])
        return_to_pick_picking.move_ids[0].move_line_ids[0].quantity = 5.0
        return_to_pick_picking.move_ids[0].picked = True
        return_to_pick_picking._action_done()

        # return the remainig products in the return warehouse
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=picking_client.ids, active_id=picking_client.ids[0],
            active_model='stock.picking'))
        return2 = stock_return_picking_form.save()
        return2.product_return_moves.quantity = 5.0
        return2.location_id = return_location.id
        return_to_return_picking_action = return2.create_returns()

        return_to_return_picking = self.env['stock.picking'].browse(return_to_return_picking_action['res_id'])
        return_to_return_picking.move_ids[0].move_line_ids[0].quantity = 5.0
        return_to_return_picking.move_ids[0].picked = True
        return_to_return_picking._action_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, pick_location), 5.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, return_location), 5.0)
        self.assertEqual(len(self.env['stock.quant'].search([('product_id', '=', self.productA.id), ('quantity', '!=', 0)])), 2)

    def test_return_lot(self):
        """ With two distinct deliveries for the same product tracked by lot, ensure that the
        return of the second picking suggest the lot from the picking returned.
        """
        self.productA.tracking = 'lot'
        lot1 = self.env['stock.lot'].create({
            'name': 'lot1',
            'product_id': self.productA.id,
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.lot'].create({
            'name': 'lot2',
            'product_id': self.productA.id,
            'company_id': self.env.company.id,
        })
        lot3 = self.env['stock.lot'].create({
            'name': 'lot3',
            'product_id': self.productA.id,
            'company_id': self.env.company.id,
        })
        stock_location = self.env['stock.location'].browse(self.stock_location)

        self.env['stock.quant']._update_available_quantity(self.productA, stock_location, 7.0, lot_id=lot1)
        self.env['stock.quant']._update_available_quantity(self.productA, stock_location, 7.0, lot_id=lot2)
        self.env['stock.quant']._update_available_quantity(self.productA, stock_location, 7.0, lot_id=lot3)

        picking_pick, picking_client = self.create_pick_ship()
        picking_pick.action_confirm()
        picking_pick.action_assign()
        picking_pick.move_ids.picked = True
        picking_pick._action_done()
        picking_client.action_confirm()
        picking_client.action_assign()
        picking_client.move_ids.picked = True
        picking_client._action_done()

        picking_pick, picking_client = self.create_pick_ship()
        picking_pick.action_confirm()
        picking_pick.action_assign()
        picking_pick.move_ids.picked = True
        picking_pick._action_done()
        picking_client.action_confirm()
        picking_client.action_assign()
        picking_client.move_ids.picked = True
        picking_client._action_done()

        # Following FIFO strategy, First picking should have empty lot1 and took 3 of lot2.
        # So the second picking contains 4 lot2 and 6 lot3
        self.assertEqual(picking_client.move_line_ids[0].lot_id, lot2)
        self.assertEqual(picking_client.move_line_ids[0].quantity, 4)
        self.assertEqual(picking_client.move_line_ids[1].lot_id, lot3)
        self.assertEqual(picking_client.move_line_ids[1].quantity, 6)

        stock_return_picking_form = Form(self.env['stock.return.picking'].with_context(
            active_ids=picking_client.ids, active_id=picking_client.ids[0], active_model='stock.picking'))
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 10.0
        return_pick = self.env['stock.picking'].browse(stock_return_picking.create_returns()['res_id'])

        self.assertEqual(len(return_pick.move_line_ids), 2)
        self.assertEqual(return_pick.move_line_ids[0].lot_id, lot2)
        self.assertEqual(return_pick.move_line_ids[0].quantity, 4)
        self.assertEqual(return_pick.move_line_ids[1].lot_id, lot3)
        self.assertEqual(return_pick.move_line_ids[1].quantity, 6)
        self.assertEqual(return_pick.picking_type_id, picking_client.location_id.warehouse_id.in_type_id)

class TestSinglePicking(TestStockCommon):
    def test_backorder_1(self):
        """ Check the good behavior of creating a backorder for an available stock move.
        """
        delivery_order = self.env['stock.picking'].create({
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
            'picking_type_id': self.picking_type_out,
            'state': 'draft',
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
        delivery_order.move_ids[0].move_line_ids[0].quantity = 1
        delivery_order.move_ids[0].picked = True
        delivery_order._action_done()
        self.assertNotEqual(delivery_order.date_done, False)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, pack_location), 1.0)

        backorder = self.env['stock.picking'].search([('backorder_id', '=', delivery_order.id)])
        self.assertEqual(backorder.state, 'confirmed')
        backorder.action_assign()
        self.assertEqual(backorder.state, 'assigned')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, pack_location), 0.0)

    def test_backorder_2(self):
        """ Check the good behavior of creating a backorder for a partially available stock move.
        """
        delivery_order = self.env['stock.picking'].create({
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
            'picking_type_id': self.picking_type_out,
            'state': 'draft',
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
        delivery_order.move_ids[0].move_line_ids[0].quantity = 1
        delivery_order.move_ids[0].picked = True
        delivery_order._action_done()
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
            'picking_type_id': self.picking_type_out,
            'state': 'draft',
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

        delivery_order.move_ids[0].move_line_ids[0].quantity = 2
        delivery_order.move_ids[0].picked = True
        delivery_order._action_done()

        backorder = self.env['stock.picking'].search([('backorder_id', '=', delivery_order.id)])
        self.assertEqual(backorder.state, 'confirmed')

    def test_backorder_4(self):
        """ Check the good behavior if no backorder are created
        for a picking with a missing product.
        """
        delivery_order = self.env['stock.picking'].create({
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
            'picking_type_id': self.picking_type_out,
            'state': 'draft',
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
        delivery_order.move_ids[0].move_line_ids[0].quantity = 2
        delivery_order.move_ids[0].picked = True

        res_dict = delivery_order.button_validate()
        backorder_wizard = Form(self.env['stock.backorder.confirmation'].with_context(res_dict['context'])).save()
        backorder_wizard.process_cancel_backorder()

        # No backorder should be created and the move corresponding to the missing product should be cancelled
        backorder = self.env['stock.picking'].search([('backorder_id', '=', delivery_order.id)])
        self.assertFalse(backorder)
        self.assertEqual(delivery_order.state, 'done')
        self.assertEqual(delivery_order.move_ids[1].state, 'cancel')

    def test_assign_deadline(self):
        """ Check if similar items with shorter deadline are prioritized. """
        delivery_order = self.PickingObj.create({
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
            'picking_type_id': self.picking_type_out,
            'state': 'draft',
        })
        # Avoid to merge move3 and move4 for the test case
        self.env['ir.config_parameter'].create({
            'key': 'stock.merge_only_same_date',
            'value': True
        })
        move1 = self.MoveObj.create({
            'name': "move1",
            'product_id': self.productA.id,
            'product_uom_qty': 4,
            'product_uom': self.productA.uom_id.id,
            'picking_id': delivery_order.id,
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
            'date_deadline': datetime.now() + relativedelta(days=1)
        })
        move2 = self.MoveObj.create({
            'name': "move2",
            'product_id': self.productA.id,
            'product_uom_qty': 4,
            'product_uom': self.productA.uom_id.id,
            'picking_id': delivery_order.id,
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
            'date_deadline': datetime.now() + relativedelta(days=2)
        })
        move3 = self.MoveObj.create({
            'name': "move3",
            'product_id': self.productA.id,
            'product_uom_qty': 1,
            'product_uom': self.productA.uom_id.id,
            'picking_id': delivery_order.id,
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
            'date': datetime.now() + relativedelta(days=10)
        })
        move4 = self.MoveObj.create({
            'name': "move4",
            'product_id': self.productA.id,
            'product_uom_qty': 1,
            'product_uom': self.productA.uom_id.id,
            'picking_id': delivery_order.id,
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
            'date': datetime.now() + relativedelta(days=0)
        })

        # make some stock
        pack_location = self.env['stock.location'].browse(self.pack_location)
        self.StockQuantObj._update_available_quantity(self.productA, pack_location, 2)

        # assign to partially available
        delivery_order.action_confirm()
        delivery_order.action_assign()

        self.assertEqual(move1.quantity, 2, "Earlier deadline should have reserved quantity")
        self.assertEqual(move2.quantity, 0, "Later deadline should not have reserved quantity")

        # add new stock
        self.StockQuantObj._update_available_quantity(self.productA, pack_location, 2)
        delivery_order.action_assign()
        self.assertEqual(move1.quantity, 4, "Earlier deadline should have reserved quantity")
        self.assertEqual(move2.quantity, 0, "Later deadline should not have reserved quantity")

        self.StockQuantObj._update_available_quantity(self.productA, pack_location, 1)
        delivery_order.action_assign()
        self.assertEqual(move1.quantity, 4, "Earlier deadline should have reserved quantity")
        self.assertEqual(move2.quantity, 1, "Move with deadline should take priority")
        self.assertEqual(move3.quantity, 0, "Move without deadline should not have reserved quantity")
        self.assertEqual(move4.quantity, 0, "Move without deadline should not have reserved quantity")

        self.StockQuantObj._update_available_quantity(self.productA, pack_location, 4)
        delivery_order.action_assign()
        self.assertEqual(move1.quantity, 4, "Earlier deadline should have reserved quantity")
        self.assertEqual(move2.quantity, 4, "Move with deadline should take priority")
        self.assertEqual(move3.quantity, 0, "Latest move without deadline should not have reserved quantity")
        self.assertEqual(move4.quantity, 1, "Earlier move without deadline should take the priority")

    def test_extra_move_1(self):
        """ Check the good behavior of creating an extra move in a delivery order. This usecase
        simulates the delivery of 2 item while the initial stock move had to move 1 and there's
        only 1 in stock.
        """
        delivery_order = self.env['stock.picking'].create({
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
            'picking_type_id': self.picking_type_out,
            'state': 'draft',
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
        delivery_order.move_ids[0].move_line_ids[0].quantity = 2
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, pack_location), 0.0)
        delivery_order.move_ids[0].picked = True
        delivery_order._action_done()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, pack_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, pack_location, allow_negative=True), -1.0)

        self.assertEqual(move1.product_qty, 1.0)
        self.assertEqual(move1.quantity, 2.0)
        self.assertEqual(move1.state, 'done')

    def test_extra_move_2(self):
        """ Check the good behavior of creating an extra move in a delivery order. This usecase
        simulates the delivery of 3 item while the initial stock move had to move 1 and there's
        only 1 in stock.
        """
        delivery_order = self.env['stock.picking'].create({
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
            'picking_type_id': self.picking_type_out,
            'state': 'draft',
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
        delivery_order.move_ids[0].move_line_ids[0].quantity = 3
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, pack_location), 0.0)
        delivery_order.move_ids[0].picked = True
        delivery_order._action_done()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, pack_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, pack_location, allow_negative=True), -2.0)

        self.assertEqual(move1.product_qty, 1.0)
        self.assertEqual(move1.quantity, 3.0)
        self.assertEqual(move1.state, 'done')

    def test_extra_move_3(self):
        """ Check the good behavior of creating an extra move in a receipt. This usecase simulates
         the receipt of 2 item while the initial stock move had to move 1.
        """
        receipt = self.env['stock.picking'].create({
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'picking_type_id': self.picking_type_in,
            'state': 'draft',
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
        receipt.move_ids[0].move_line_ids[0].quantity = 2
        receipt.move_ids[0].picked = True
        receipt._action_done()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, stock_location), 2.0)

        self.assertEqual(move1.product_qty, 1.0)
        self.assertEqual(move1.quantity, 2.0)
        self.assertEqual(move1.state, 'done')

    def test_extra_move_4(self):
        """ Create a picking with similar moves (created after
        confirmation). Action done should propagate all the extra
        quantity and only merge extra moves in their original moves.
        """
        delivery = self.env['stock.picking'].create({
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'picking_type_id': self.picking_type_out,
            'state': 'draft',
        })
        self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 5,
            'quantity': 10,
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
            'move_ids': [(0, 0, {
                'name': self.productA.name,
                'product_id': self.productA.id,
                'product_uom_qty': 0,
                'quantity': 10,
                'state': 'assigned',
                'product_uom': self.productA.uom_id.id,
                'picking_id': delivery.id,
                'location_id': self.stock_location,
                'location_dest_id': self.customer_location,
            })]
        })
        delivery.move_ids.picked = True
        delivery._action_done()
        self.assertEqual(len(delivery.move_ids), 2, 'Move should not be merged together')
        for move in delivery.move_ids:
            self.assertNotEqual(move.quantity, move.product_uom_qty, 'Initial demand shouldn\'t be modified')

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
            'picking_type_id': self.picking_type_out,
            'state': 'draft',
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
        self.assertEqual(move1.quantity, 1.0)
        self.assertEqual(len(move1.move_line_ids), 1)

        inventory_quant = self.env['stock.quant'].create({
            'location_id': self.stock_location,
            'product_id': self.productA.id,
            'inventory_quantity': 2
        })
        inventory_quant.action_apply_inventory()
        delivery_order.action_assign()
        self.assertEqual(delivery_order.state, 'assigned')
        self.assertEqual(move1.state, 'assigned')

        # Check reserved quantity
        self.assertEqual(move1.quantity, 2.0)
        self.assertEqual(len(move1.move_line_ids), 1)

    def test_recheck_availability_2(self):
        """ Same check than test_recheck_availability_1 but with lot this time.
        If the new product has the same lot that already reserved one, the move lines
        reserved quantity should be updated.
        Otherwise a new move lines with the new lot should be added.
        """
        self.productA.tracking = 'lot'
        lot1 = self.env['stock.lot'].create({
            'name': 'lot1',
            'product_id': self.productA.id,
            'company_id': self.env.company.id,
        })
        stock_location = self.env['stock.location'].browse(self.stock_location)
        self.env['stock.quant']._update_available_quantity(self.productA, stock_location, 1.0, lot_id=lot1)
        delivery_order = self.env['stock.picking'].create({
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'picking_type_id': self.picking_type_out,
            'state': 'draft',
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
        self.assertEqual(move1.quantity, 1.0)
        self.assertEqual(len(move1.move_line_ids), 1)

        inventory_quant = self.env['stock.quant'].create({
            'location_id': self.stock_location,
            'product_id': self.productA.id,
            'inventory_quantity': 2,
            'lot_id': lot1.id
        })
        inventory_quant.action_apply_inventory()
        delivery_order.action_assign()
        self.assertEqual(delivery_order.state, 'assigned')
        self.assertEqual(move1.state, 'assigned')

        # Check reserved quantity
        self.assertEqual(move1.quantity, 2.0)
        self.assertEqual(len(move1.move_line_ids), 1)
        self.assertEqual(move1.move_line_ids.lot_id.id, lot1.id)
        self.assertEqual(move1.move_line_ids.quantity, 2)

    def test_recheck_availability_3(self):
        """ Same check than test_recheck_availability_2 but with different lots.
        """
        self.productA.tracking = 'lot'
        lot1 = self.env['stock.lot'].create({
            'name': 'lot1',
            'product_id': self.productA.id,
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.lot'].create({
            'name': 'lot2',
            'product_id': self.productA.id,
            'company_id': self.env.company.id,
        })
        stock_location = self.env['stock.location'].browse(self.stock_location)
        self.env['stock.quant']._update_available_quantity(self.productA, stock_location, 1.0, lot_id=lot1)
        delivery_order = self.env['stock.picking'].create({
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'picking_type_id': self.picking_type_out,
            'state': 'draft',
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
        self.assertEqual(move1.quantity, 1.0)
        self.assertEqual(len(move1.move_line_ids), 1)

        inventory_quant = self.env['stock.quant'].create({
            'location_id': self.stock_location,
            'product_id': self.productA.id,
            'inventory_quantity': 1,
            'lot_id': lot2.id
        })
        inventory_quant.action_apply_inventory()
        delivery_order.action_assign()
        self.assertEqual(delivery_order.state, 'assigned')
        self.assertEqual(move1.state, 'assigned')

        # Check reserved quantity
        self.assertEqual(move1.quantity, 2.0)
        self.assertEqual(len(move1.move_line_ids), 2)
        move_lines = move1.move_line_ids.sorted()
        self.assertEqual(move_lines[0].lot_id.id, lot1.id)
        self.assertEqual(move_lines[1].lot_id.id, lot2.id)

    def test_recheck_availability_4(self):
        """ Same check than test_recheck_availability_2 but with serial number this time.
        Serial number reservation should always create a new move line.
        """
        self.productA.tracking = 'serial'
        serial1 = self.env['stock.lot'].create({
            'name': 'serial1',
            'product_id': self.productA.id,
            'company_id': self.env.company.id,
        })
        serial2 = self.env['stock.lot'].create({
            'name': 'serial2',
            'product_id': self.productA.id,
            'company_id': self.env.company.id,
        })
        stock_location = self.env['stock.location'].browse(self.stock_location)
        self.env['stock.quant']._update_available_quantity(self.productA, stock_location, 1.0, lot_id=serial1)
        delivery_order = self.env['stock.picking'].create({
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'picking_type_id': self.picking_type_out,
            'state': 'draft',
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
        self.assertEqual(move1.quantity, 1.0)
        self.assertEqual(len(move1.move_line_ids), 1)

        inventory_quant = self.env['stock.quant'].create({
            'location_id': self.stock_location,
            'product_id': self.productA.id,
            'inventory_quantity': 1,
            'lot_id': serial2.id
        })
        inventory_quant.action_apply_inventory()
        delivery_order.action_assign()
        self.assertEqual(delivery_order.state, 'assigned')
        self.assertEqual(move1.state, 'assigned')

        # Check reserved quantity
        self.assertEqual(move1.quantity, 2.0)
        self.assertEqual(len(move1.move_line_ids), 2)
        move_lines = move1.move_line_ids.sorted()
        self.assertEqual(move_lines[0].lot_id.id, serial1.id)
        self.assertEqual(move_lines[1].lot_id.id, serial2.id)

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
            'picking_type_id': self.picking_type_out,
            'state': 'draft',
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
        delivery_order.move_ids.quantity = 2
        delivery_order.move_ids.picked = True
        # do not set a lot_id or lot_name, it should work
        delivery_order._action_done()

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
            'picking_type_id': self.picking_type_out,
            'state': 'draft',
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
        delivery_order.move_ids.quantity = 2
        move_line = delivery_order.move_ids.move_line_ids
        delivery_order.move_ids.picked = True

        # not lot_name set, should raise
        with self.assertRaises(UserError):
            delivery_order._action_done()

        # enter a new lot name, should work
        move_line.lot_name = 'newlot'
        delivery_order._action_done()

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
            'picking_type_id': self.picking_type_out,
            'state': 'draft',
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
        delivery_order.move_ids.quantity = 2
        move_line = delivery_order.move_ids.move_line_ids
        delivery_order.move_ids.picked = True

        # not lot_name set, should raise
        with self.assertRaises(UserError):
            delivery_order._action_done()

        # enter a new lot name, should work
        move_line.lot_name = 'newlot'
        delivery_order._action_done()

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
            'picking_type_id': self.picking_type_out,
            'state': 'draft',
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
        delivery_order.move_ids.quantity = 2
        move_line = delivery_order.move_ids.move_line_ids
        delivery_order.move_ids.picked = True

        # not lot_name set, should raise
        with self.assertRaises(UserError):
            delivery_order._action_done()

        # creating a lot from the view should raise
        with self.assertRaises(UserError):
            self.env['stock.lot']\
                .with_context(active_picking_id=delivery_order.id)\
                .create({
                    'name': 'lot1',
                    'product_id': self.productA.id,
                    'company_id': self.env.company.id,
                })

        # enter an existing lot_id, should work
        lot1 = self.env['stock.lot'].create({
            'name': 'lot1',
            'product_id': self.productA.id,
            'company_id': self.env.company.id,
        })
        move_line.lot_id = lot1
        delivery_order._action_done()

    def test_merge_moves_1(self):
        receipt = self.env['stock.picking'].create({
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'picking_type_id': self.picking_type_in,
            'state': 'draft',
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
        self.assertEqual(len(receipt.move_ids), 2, 'Moves were not merged')
        self.assertEqual(receipt.move_ids.filtered(lambda m: m.product_id == self.productA).product_uom_qty, 9, 'Merged quantity is not correct')
        self.assertEqual(receipt.move_ids.filtered(lambda m: m.product_id == self.productB).product_uom_qty, 5, 'Merge should not impact product B reserved quantity')

    def test_merge_moves_2(self):
        receipt = self.env['stock.picking'].create({
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'picking_type_id': self.picking_type_in,
            'state': 'draft',
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
        self.assertEqual(len(receipt.move_ids), 1, 'Moves were not merged')
        self.assertEqual(receipt.move_ids.origin.count('MPS'), 1, 'Origin not merged together or duplicated')
        self.assertEqual(receipt.move_ids.origin.count('PO0001'), 1, 'Origin not merged together or duplicated')

    def test_merge_moves_3(self):
        """ Create 2 moves without initial_demand and already a
        quantity done. Check that we still have only 2 moves after
        validation.
        """
        receipt = self.env['stock.picking'].create({
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'picking_type_id': self.picking_type_in,
            'state': 'draft',
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
        move_1.quantity = 5
        move_2.quantity = 5
        receipt.button_validate()
        self.assertEqual(len(receipt.move_ids), 2, 'Moves were not merged')

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
            'picking_type_id': warehouse.in_type_id.id,
            'state': 'draft',
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
            'picking_type_id': warehouse.in_type_id.id,
            'state': 'draft',
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

    def test_merge_chained_moves_multi_confirm(self):
        """ Imagine multiple step delivery. A receipt picking for the same product should by add to
        a existing picking from input to QC and another from QC to stock.
        This existing picking is confirm in the same time (not possible in stock, but can be with batch picking)
        and have some move to merge.
        """
        warehouse = self.env['stock.warehouse'].create({
            'name': 'TEST WAREHOUSE',
            'code': 'TEST1',
            'reception_steps': 'three_steps',
        })
        receipt1 = self.env['stock.picking'].create({
            'location_id': self.supplier_location,
            'location_dest_id': warehouse.wh_input_stock_loc_id.id,
            'picking_type_id': warehouse.in_type_id.id,
            'state': 'draft',
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
            'location_id': warehouse.wh_input_stock_loc_id.id,
            'location_dest_id': warehouse.wh_qc_stock_loc_id.id,
            'picking_type_id': warehouse.int_type_id.id,
            'state': 'draft',
        })
        move1_receipt_2 = self.MoveObj.create({
            'name': self.productB.name,
            'product_id': self.productB.id,
            'product_uom_qty': 1,
            'product_uom': self.productB.uom_id.id,
            'picking_id': receipt2.id,
            'location_id': warehouse.wh_input_stock_loc_id.id,
            'location_dest_id':  warehouse.wh_qc_stock_loc_id.id,
        })
        move2_receipt_2 = self.MoveObj.create({
            'name': self.productB.name,
            'product_id': self.productB.id,
            'product_uom_qty': 2,
            'product_uom': self.productB.uom_id.id,
            'picking_id': receipt2.id,
            'location_id': warehouse.wh_input_stock_loc_id.id,
            'location_dest_id': warehouse.wh_qc_stock_loc_id.id,
        })
        (receipt1 | receipt2).action_confirm()

        # Check following move has been created
        self.assertTrue(move_receipt_1.move_dest_ids, 'No move created from push rules')
        self.assertTrue((move1_receipt_2 | move2_receipt_2).exists().move_dest_ids, 'No move created from push rules')
        self.assertEqual(len((move1_receipt_2 | move2_receipt_2).exists()), 1, 'Move has been merged with the other one')
        self.assertEqual(move_receipt_1.move_dest_ids.picking_id, receipt2, 'Dest Move of receipt1 should be in the receipt2')

        # Check no move is still in draft
        self.assertTrue("draft" not in (receipt1 | receipt2).move_ids.mapped("state"))

        # Check the content of the pickings
        self.assertEqual(receipt1.move_ids.mapped("product_uom_qty"), [5])
        self.assertEqual(receipt2.move_ids.filtered(lambda m: m.product_id == self.productB).mapped("product_uom_qty"), [3])
        self.assertEqual(receipt2.move_ids.filtered(lambda m: m.product_id == self.productA).mapped("product_uom_qty"), [5])

    def test_empty_moves_validation_1(self):
        """ Use button validate on a picking that contains only moves
        without initial demand and without quantity done should be
        impossible and raise a usererror.
        """
        delivery_order = self.env['stock.picking'].create({
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'picking_type_id': self.picking_type_out,
            'state': 'draft',
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
            'picking_type_id': self.picking_type_out,
            'state': 'draft',
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
        move_a.quantity = 1
        move_a.picked = True
        delivery_order.button_validate()

        self.assertEqual(move_a.state, 'done')
        self.assertEqual(move_b.state, 'cancel')
        back_order = self.env['stock.picking'].search([('backorder_id', '=', delivery_order.id)])
        self.assertFalse(back_order, 'There should be no back order')

    def test_unlink_move_1(self):
        picking = Form(self.env['stock.picking'])
        ptout = self.env['stock.picking.type'].browse(self.picking_type_out)
        picking.picking_type_id = ptout
        with picking.move_ids_without_package.new() as move:
            move.product_id = self.productA
            move.quantity = 10
        picking = picking.save()
        self.assertEqual(picking.state, 'assigned')

        picking = Form(picking)
        picking.move_ids_without_package.remove(0)
        picking = picking.save()
        self.assertEqual(len(picking.move_ids_without_package), 0)

    def test_additional_move_1(self):
        """ On a planned trasfer, add a stock move when the picking is already ready. Check that
        the check availability button appears and work.
        """
        # Make some stock for productA and productB.
        receipt = self.env['stock.picking'].create({
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'picking_type_id': self.picking_type_in,
            'state': 'draft',
        })
        move_1 = self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 10,
            'product_uom': self.productA.uom_id.id,
            'picking_id': receipt.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
        })
        move_2 = self.MoveObj.create({
            'name': self.productB.name,
            'product_id': self.productB.id,
            'product_uom_qty': 10,
            'product_uom': self.productB.uom_id.id,
            'picking_id': receipt.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
        })
        receipt.action_confirm()
        move_1.quantity = 10
        move_2.quantity = 10
        receipt.move_ids.picked = True
        receipt.button_validate()
        self.assertEqual(self.productA.qty_available, 10)
        self.assertEqual(self.productB.qty_available, 10)

        # Create a delivery for 1 productA, reserve, check the picking is ready
        delivery_order = self.env['stock.picking'].create({
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'picking_type_id': self.picking_type_out,
            'move_type': 'one',
            'state': 'draft',
        })
        move_3 = self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 10,
            'product_uom': self.productA.uom_id.id,
            'picking_id': delivery_order.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
        })
        delivery_order.action_confirm()
        delivery_order.action_assign()
        self.assertEqual(delivery_order.state, 'assigned')

        # Add a unit of productB, the check_availability button should appear.
        delivery_order = Form(delivery_order)
        with delivery_order.move_ids_without_package.new() as move:
            move.product_id = self.productB
            move.product_uom_qty = 10
        delivery_order = delivery_order.save()

        # The autocofirm ran, the picking shoud be confirmed and reservable.
        self.assertEqual(delivery_order.state, 'confirmed')
        self.assertEqual(delivery_order.show_check_availability, True)

        delivery_order.action_assign()
        self.assertEqual(delivery_order.state, 'assigned')
        self.assertEqual(delivery_order.show_check_availability, False)

        stock_location = self.env['stock.location'].browse(self.stock_location)
        self.assertEqual(self.env['stock.quant']._gather(self.productA, stock_location).reserved_quantity, 10.0)
        self.assertEqual(self.env['stock.quant']._gather(self.productB, stock_location).reserved_quantity, 10.0)

    def test_additional_move_2(self):
        """ On an immediate trasfer, add a stock move when the picking is already ready. Check that
        the check availability button doest not appear.
        """
        # Create a delivery for 1 productA, check the picking is ready
        delivery_order = self.env['stock.picking'].create({
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'picking_type_id': self.picking_type_out,
            'move_ids_without_package': [(0, 0, {
                'name': self.productA.name,
                'product_id': self.productA.id,
                'product_uom': self.productA.uom_id.id,
                'location_id': self.stock_location,
                'location_dest_id': self.customer_location,
                'quantity': 5,
            })],
        })
        self.assertEqual(delivery_order.state, 'assigned')

        # Add a unit of productB, the check_availability button should not appear.
        delivery_order = Form(delivery_order)
        with delivery_order.move_ids_without_package.new() as move:
            move.product_id = self.productB
        delivery_order = delivery_order.save()

        self.assertEqual(delivery_order.state, 'assigned')
        self.assertEqual(delivery_order.show_check_availability, False)

    def test_owner_1(self):
        # Required for `owner_id` to be visible in the view
        self.env.user.groups_id += self.env.ref("stock.group_tracking_owner")
        """Make a receipt, set an owner and validate"""
        owner1 = self.env['res.partner'].create({'name': 'owner'})
        receipt = self.env['stock.picking'].create({
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'picking_type_id': self.picking_type_in,
            'state': 'draft',
        })
        move1 = self.env['stock.move'].create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 1,
            'product_uom': self.productA.uom_id.id,
            'picking_id': receipt.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
        })
        receipt.action_confirm()
        receipt = Form(receipt)
        receipt.owner_id = owner1
        receipt = receipt.save()
        receipt.button_validate()

        supplier_location = self.env['stock.location'].browse(self.supplier_location)
        stock_location = self.env['stock.location'].browse(self.stock_location)
        supplier_quant = self.env['stock.quant']._gather(self.productA, supplier_location)
        stock_quant = self.env['stock.quant']._gather(self.productA, stock_location)

        self.assertEqual(supplier_quant.owner_id, owner1)
        self.assertEqual(supplier_quant.quantity, -1)
        self.assertEqual(stock_quant.owner_id, owner1)
        self.assertEqual(stock_quant.quantity, 1)

    def test_putaway_for_picking_sml(self):
        """ Checks picking's move lines will take in account the putaway rules
        to define the `location_dest_id`.
        """
        partner = self.env['res.partner'].create({'name': 'Partner'})
        supplier_location = self.env['stock.location'].browse(self.supplier_location)
        stock_location = self.env['stock.location'].create({
            'name': 'test-stock',
            'usage': 'internal',
        })
        shelf_location = self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': stock_location.id,
        })

        # We need to activate multi-locations to use putaway rules.
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id)]})
        putaway_product = self.env['stock.putaway.rule'].create({
            'product_id': self.productA.id,
            'location_in_id': stock_location.id,
            'location_out_id': shelf_location.id,
        })
        # Changes config of receipt type to allow to edit move lines directly.
        picking_type = self.env['stock.picking.type'].browse(self.picking_type_in)
        picking_type.show_reserved = True

        receipt_form = Form(self.env['stock.picking'], view='stock.view_picking_form')
        receipt_form.partner_id = partner
        receipt_form.picking_type_id = picking_type
        # <field name="location_id" invisible="picking_type_code' == 'incoming'"
        receipt_form.location_dest_id = stock_location
        receipt = receipt_form.save()

        with receipt_form.move_ids_without_package.new() as move:
            move.product_id = self.productA
            move.quantity = 1.0


        # with Form(receipt.move_ids_without_package, view='stock.view_stock_move_operations') as form:
        #     with form.move_line_ids.new() as move_line:
        #         # move_line.product_id = self.productA
        #         move_line.location_dest_id = stock_location
        #         move_line.quantity = 1.0

        receipt = receipt_form.save()
        # Checks receipt has still its destination location and checks its move
        # line took the one from the putaway rule.
        self.assertEqual(receipt.location_dest_id.id, stock_location.id)
        self.assertEqual(receipt.move_line_ids.location_dest_id.id, shelf_location.id)

    def test_cancel_plan_transfer(self):
        """ Test canceling plan transfer """
        # Create picking with stock move.
        picking = self.env['stock.picking'].create({
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
            'picking_type_id': self.picking_type_out,
            'state': 'draft',
            'move_ids': [(0, 0, {
                'name': self.productA.name,
                'product_id': self.productA.id,
                'product_uom_qty': 10,
                'product_uom': self.productA.uom_id.id,
                'location_id': self.pack_location,
                'location_dest_id': self.customer_location,
            })]
        })
        # Confirm the outgoing picking, state should be changed.
        picking.action_confirm()
        self.assertEqual(picking.state, 'confirmed', "Picking should be in a confirmed state.")

        # Picking in a confirmed state and try to cancel it.
        picking.action_cancel()
        self.assertEqual(picking.state, 'cancel', "Picking should be in a cancel state.")

    def test_immediate_transfer(self):
        """ Test picking should be in ready state if immediate transfer and SML is created via view +
            Test picking cancelation with immediate transfer and done quantity"""
        # create picking with stock move line
        picking = self.env['stock.picking'].create({
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
            'picking_type_id': self.picking_type_out,
            'move_line_ids': [(0, 0, {
                'product_id': self.productA.id,
                'quantity': 10,
                'product_uom_id': self.productA.uom_id.id,
                'location_id': self.pack_location,
                'location_dest_id': self.customer_location,
            })]
        })

        self.assertEqual(picking.state, 'assigned', "Picking should not be in a draft state.")
        self.assertEqual(len(picking.move_ids), 1, "Picking should have stock move.")
        picking.action_cancel()
        self.assertEqual(picking.move_ids.state, 'cancel', "Stock move should be in a cancel state.")
        self.assertEqual(picking.state, 'cancel', "Picking should be in a cancel state.")

    def test_immediate_picking_with_lot(self):
        self.productA.tracking = 'serial'
        picking = self.env['stock.picking'].create({
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'picking_type_id': self.picking_type_in,
            'move_line_ids': [(0, 0, {
                'product_id': self.productA.id,
                'product_uom_id': self.productA.uom_id.id,
                'location_id': self.supplier_location,
                'location_dest_id': self.stock_location,
                'quantity': 1,
                'lot_name': '12345',
            })]
        })

        self.assertEqual(len(picking.move_line_ids), 1, "Picking should have a single move line")
        picking.button_validate()
        self.assertEqual(len(picking.move_line_ids), 1, "Picking should have a single move line")

class TestStockUOM(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        dp = cls.env.ref('product.decimal_product_uom')
        dp.digits = 7

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

        picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_in,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'state': 'draft',
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
        picking_in.do_unreserve()

        self.assertEqual(move.product_uom_qty, 60.00, 'Wrong T_GT quantity')
        self.assertEqual(move.product_qty, 134400.00, 'Wrong T_LBS quantity')

        lot = self.env['stock.lot'].create({'name': 'Lot TEST', 'product_id': T_TEST.id, 'company_id': self.env.company.id, })
        self.env['stock.move.line'].create({
            'move_id': move.id,
            'product_id': T_TEST.id,
            'product_uom_id': T_LBS.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'quantity': 42760.00,
            'lot_id': lot.id,
        })
        picking_in.move_ids.picked = True
        picking_in._action_done()
        back_order_in = self.env['stock.picking'].search([('backorder_id', '=', picking_in.id)])

        self.assertEqual(len(back_order_in), 1.00, 'There should be one back order created')
        self.assertEqual(back_order_in.move_ids.product_qty, 91640.00, 'There should be one back order created')

    def test_move_product_with_different_uom(self):
        """ Product defined in g with 0.01 rounding
        Decimal Accuracy (DA) 3 digits.
        Quantity on hand: 149.88g
        Picking of 1kg
        kg has 0.0001 rounding
        Due to conversions, we may end up reserving 150g
        (more than the quantity in stock), we check that
        we reserve less than the quantity in stock
        """
        precision = self.env.ref('product.decimal_product_uom')
        precision.digits = 3

        self.uom_kg.rounding = 0.0001
        self.uom_gm.rounding = 0.01

        product_G = self.env['product.product'].create({
            'name': 'Product G',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'uom_id': self.uom_gm.id,
            'uom_po_id': self.uom_gm.id,
        })

        stock_location = self.env['stock.location'].browse(self.stock_location)
        self.env['stock.quant']._update_available_quantity(product_G, stock_location, 149.88)
        self.assertEqual(len(product_G.stock_quant_ids), 1, 'One quant should exist for the product.')
        quant = product_G.stock_quant_ids

        # transfer 1kg of product_G
        picking = self.env['stock.picking'].create({
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'state': 'draft',
        })

        move = self.env['stock.move'].create({
            'name': 'test_reserve_product_G',
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'picking_id': picking.id,
            'product_id': product_G.id,
            'product_uom': self.uom_kg.id,
            'product_uom_qty': 1,
        })

        self.assertEqual(move.product_uom.id, self.uom_kg.id)
        self.assertEqual(move.product_uom_qty, 1.0)

        picking.action_confirm()
        picking.action_assign()

        self.assertEqual(product_G.uom_id.rounding, 0.01)
        self.assertEqual(move.product_uom.rounding, 0.0001)

        self.assertEqual(len(picking.move_line_ids), 1, 'One move line should exist for the picking.')
        move_line = picking.move_line_ids
        # check that we do not reserve more (in the same UOM) than the quantity in stock
        self.assertEqual(quant.quantity, 149.88)
        # check that we reserve the same quantity in the ml and the quant
        self.assertEqual(move_line.quantity_product_uom, quant.reserved_quantity)

    def test_update_product_move_line_with_different_uom(self):
        """ Check that when the move line and corresponding
        product have different UOM with possibly conflicting
        precisions, we do not reserve more than the quantity
        in stock. Similar initial configuration as
        test_move_product_with_different_uom.
        """
        precision = self.env.ref('product.decimal_product_uom')
        precision.digits = 3
        precision_digits = precision.digits

        self.uom_kg.rounding = 0.0001
        self.uom_gm.rounding = 0.01

        product_LtDA = self.env['product.product'].create({
            'name': 'Product Less than DA',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'uom_id': self.uom_gm.id,
            'uom_po_id': self.uom_gm.id,
        })

        product_GtDA = self.env['product.product'].create({
            'name': 'Product Greater than DA',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'uom_id': self.uom_gm.id,
            'uom_po_id': self.uom_gm.id,
        })

        stock_location = self.env['stock.location'].browse(self.stock_location)

        # quantity in hand converted to kg is not more precise than the DA
        self.env['stock.quant']._update_available_quantity(product_LtDA, stock_location, 149)
        # quantity in hand converted to kg is more precise than the DA
        self.env['stock.quant']._update_available_quantity(product_GtDA, stock_location, 149.88)

        self.assertEqual(len(product_LtDA.stock_quant_ids), 1, 'One quant should exist for the product.')
        self.assertEqual(len(product_GtDA.stock_quant_ids), 1, 'One quant should exist for the product.')
        quant_LtDA = product_LtDA.stock_quant_ids
        quant_GtDA = product_GtDA.stock_quant_ids

        # create 2 moves of 1kg
        move_LtDA = self.env['stock.move'].create({
            'name': 'test_reserve_product_LtDA',
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'product_id': product_LtDA.id,
            'product_uom': self.uom_kg.id,
            'product_uom_qty': 1,
        })

        move_GtDA = self.env['stock.move'].create({
            'name': 'test_reserve_product_GtDA',
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'product_id': product_GtDA.id,
            'product_uom': self.uom_kg.id,
            'product_uom_qty': 1,
        })

        self.assertEqual(move_LtDA.state, 'draft')
        self.assertEqual(move_GtDA.state, 'draft')
        move_LtDA._action_confirm()
        move_GtDA._action_confirm()
        self.assertEqual(move_LtDA.state, 'confirmed')
        self.assertEqual(move_GtDA.state, 'confirmed')
        # check availability, less than initial demand
        move_LtDA._action_assign()
        move_GtDA._action_assign()
        self.assertEqual(move_LtDA.state, 'partially_available')
        self.assertEqual(move_GtDA.state, 'partially_available')
        # the initial demand is 1kg
        self.assertEqual(move_LtDA.product_uom.id, self.uom_kg.id)
        self.assertEqual(move_GtDA.product_uom.id, self.uom_kg.id)
        self.assertEqual(move_LtDA.product_uom_qty, 1.0)
        self.assertEqual(move_GtDA.product_uom_qty, 1.0)
        # one move line is created
        self.assertEqual(len(move_LtDA.move_line_ids), 1)
        self.assertEqual(len(move_GtDA.move_line_ids), 1)

        # increase quantity by 0.14988 kg (more precise than DA)
        self.env['stock.quant']._update_available_quantity(product_LtDA, stock_location, 149.88)
        self.env['stock.quant']._update_available_quantity(product_GtDA, stock_location, 149.88)

        # _update_reserved_quantity is called on a move only in _action_assign
        move_LtDA._action_assign()
        move_GtDA._action_assign()

        # as the move line for LtDA and its corresponding quant can be
        # in different UOMs, a new move line can be created
        # from _update_reserved_quantity
        move_lines_LtDA = self.env["stock.move.line"].search([
            ('product_id', '=', quant_LtDA.product_id.id),
            ('location_id', '=', quant_LtDA.location_id.id),
            ('lot_id', '=', quant_LtDA.lot_id.id),
            ('package_id', '=', quant_LtDA.package_id.id),
            ('owner_id', '=', quant_LtDA.owner_id.id),
            ('quantity_product_uom', '!=', 0)
        ])
        reserved_on_move_lines_LtDA = sum(move_lines_LtDA.mapped('quantity_product_uom'))

        move_lines_GtDA = self.env["stock.move.line"].search([
            ('product_id', '=', quant_GtDA.product_id.id),
            ('location_id', '=', quant_GtDA.location_id.id),
            ('lot_id', '=', quant_GtDA.lot_id.id),
            ('package_id', '=', quant_GtDA.package_id.id),
            ('owner_id', '=', quant_GtDA.owner_id.id),
            ('quantity_product_uom', '!=', 0)
        ])
        reserved_on_move_lines_GtDA = sum(move_lines_GtDA.mapped('quantity_product_uom'))

        # check that we reserve the same quantity in the ml and the quant
        self.assertEqual(reserved_on_move_lines_LtDA, 298.8)
        self.assertEqual(reserved_on_move_lines_LtDA, quant_LtDA.reserved_quantity)
        self.assertEqual(reserved_on_move_lines_GtDA, 299.7)
        self.assertEqual(reserved_on_move_lines_GtDA, quant_GtDA.reserved_quantity)


class TestRoutes(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product1 = cls.env['product.product'].create({
            'name': 'product a',
            'type': 'product',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.partner = cls.env['res.partner'].create({'name': 'Partner'})

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

        ship_location = pick_rule.location_dest_id
        customer_location = push_rule.location_dest_id
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
        resupply_route = self.env['stock.route'].search([('supplier_wh_id', '=', warehouse_2.id), ('supplied_wh_id', '=', warehouse_1.id)])
        self.assertTrue(resupply_route, "Ressuply route not found")
        self.product1.write({'route_ids': [(4, resupply_route.id), (4, self.env.ref('stock.route_warehouse0_mto').id)]})
        self.wh = warehouse_1

        replenish_wizard = self.env['product.replenish'].with_context(default_product_tmpl_id=self.product1.product_tmpl_id.id).create({
            'product_id': self.product1.id,
            'product_tmpl_id': self.product1.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'quantity': self.product_uom_qty,
            'warehouse_id': self.wh.id,
        })

        genrated_picking = replenish_wizard.launch_replenishment()
        links = genrated_picking.get("params", {}).get("links")
        url = links and links[0].get("url", "") or ""
        picking_id, model_name = self.url_extract_rec_id_and_model(url)

        last_picking_id = False
        if picking_id and model_name:
            last_picking_id = self.env[model_name[0]].browse(int(picking_id[0]))
        self.assertTrue(last_picking_id, 'Picking not found')
        move_line = last_picking_id.move_ids.search([('product_id', '=', self.product1.id)])
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
        route = self.env['stock.route'].create({
            'name': 'new route',
            'rule_ids': [(0, False, {
                'name': 'create a move to push location',
                'location_src_id': stock_location.id,
                'location_dest_id': push_location.id,
                'company_id': self.env.company.id,
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

    def test_location_dest_update(self):
        """ Check the location dest of a stock move changed by a push rule
        with auto field set to transparent is done correctly. The stock_move
        is create with the move line directly to pass into action_confirm() via
        action_done(). """
        self.wh = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.id)], limit=1)
        new_loc = self.env['stock.location'].create({
            'name': 'New_location',
            'usage': 'internal',
            'location_id': self.env.ref('stock.stock_location_locations').id,
        })
        picking_type = self.env['stock.picking.type'].create({
            'name': 'new_picking_type',
            'code': 'internal',
            'sequence_code': 'NPT',
            'default_location_src_id': self.env.ref('stock.stock_location_stock').id,
            'default_location_dest_id': new_loc.id,
            'warehouse_id': self.wh.id,
        })
        route = self.env['stock.route'].create({
            'name': 'new route',
            'rule_ids': [(0, False, {
                'name': 'create a move to push location',
                'location_src_id': self.env.ref('stock.stock_location_stock').id,
                'location_dest_id': new_loc.id,
                'company_id': self.env.company.id,
                'action': 'push',
                'auto': 'transparent',
                'picking_type_id': picking_type.id,
            })],
        })
        product = self.env['product.product'].create({
            'name': 'new_product',
            'type': 'product',
            'route_ids': [(4, route.id)]
        })
        move1 = self.env['stock.move'].create({
            'name': 'move with a route',
            'location_id': self.supplier_location,
            'location_dest_id': self.env.ref('stock.stock_location_stock').id,
            'product_id': product.id,
            'product_uom_qty': 1.0,
            'product_uom': self.uom_unit.id,
            'move_line_ids': [(0, 0, {
                'product_id': product.id,
                'product_uom_id': self.uom_unit.id,
                'location_id': self.supplier_location,
                'location_dest_id': self.env.ref('stock.stock_location_stock').id,
                'quantity': 1.00,
            })],
        })
        move1.picked = True
        move1._action_done()
        self.assertEqual(move1.location_dest_id, new_loc)
        positive_quant = product.stock_quant_ids.filtered(lambda q: q.quantity > 0)
        self.assertEqual(positive_quant.location_id, new_loc)

    def test_mtso_mto(self):
        """ Run a procurement for 5 products when there are only 4 in stock then
        check that MTO is applied on the moves when the rule is set to 'mts_else_mto'
        """
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.id)], limit=1)
        warehouse.delivery_steps = 'pick_pack_ship'
        partner_demo_customer = self.partner
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
        self.assertEqual(len(picking_ids), 3)
        for picking in picking_ids:
            # Only the picking from Stock to Pack should be MTS
            if picking.location_id == warehouse.lot_stock_id:
                self.assertEqual(picking.move_ids.procure_method, 'make_to_stock')
            else:
                self.assertEqual(picking.move_ids.procure_method, 'make_to_order')

            self.assertEqual(len(picking.move_ids), 1)
            self.assertEqual(picking.move_ids.product_uom_qty, 5, 'The quantity of the move should be the same as on the SO')
        self.assertEqual(qty_available, 4, 'The 4 products should still be available')

    def test_mtso_mts(self):
        """ Run a procurement for 4 products when there are 4 in stock then
        check that MTS is applied on the moves when the rule is set to 'mts_else_mto'
        """
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.id)], limit=1)
        warehouse.delivery_steps = 'pick_pack_ship'
        partner_demo_customer = self.partner
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
        self.assertEqual(len(picking_ids), 1)
        picking = picking_ids
        self.assertEqual(picking.move_ids.procure_method, 'make_to_stock')
        self.assertEqual(len(picking.move_ids), 1)
        self.assertEqual(picking.move_ids.product_uom_qty, 4)

    def test_mtso_multi_pg(self):
        """ Run 3 procurements for 2 products at the same times when there are 4 in stock then
        check that MTS is applied on the moves when the rule is set to 'mts_else_mto'
        """
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.id)], limit=1)
        warehouse.delivery_steps = 'pick_pack_ship'
        partner_demo_customer = self.partner
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
        self.assertEqual(len(pickings_pg1), 1)
        self.assertEqual(len(pickings_pg2), 1)
        self.assertEqual(pickings_pg1.move_ids.procure_method, 'make_to_stock')
        self.assertEqual(pickings_pg2.move_ids.procure_method, 'make_to_stock')

        # The last one should have 3 pickings as there's nothing left in the delivery location
        self.assertEqual(len(pickings_pg3), 3)
        for picking in pickings_pg3:
            # Only the picking from Stock to Pack should be MTS
            if picking.location_id == warehouse.lot_stock_id:
                self.assertEqual(picking.move_ids.procure_method, 'make_to_stock')
            else:
                self.assertEqual(picking.move_ids.procure_method, 'make_to_order')

            # All the moves should be should have the same quantity as it is on each procurements
            self.assertEqual(len(picking.move_ids), 1)
            self.assertEqual(picking.move_ids.product_uom_qty, 2)

    def test_mtso_mto_adjust_01(self):
        """ Run '_adjust_procure_method' for products A & B:
        - Product A has 5.0 available
        - Product B has 3.0 available
        Stock moves (SM) are created for 4.0 units
        After '_adjust_procure_method':
        - SM for A is 'make_to_stock'
        - SM for B is 'make_to_order'
        """
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.id)], limit=1)
        final_location = self.partner.property_stock_customer
        product_A = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        product_B = self.env['product.product'].create({
            'name': 'Product B',
            'type': 'product',
        })

        # We alter one rule and we set it to 'mts_else_mto'
        rule = self.env['procurement.group']._get_rule(product_A, final_location, {'warehouse_id': warehouse})
        rule.procure_method = 'mts_else_mto'

        self.env['stock.quant']._update_available_quantity(product_A, warehouse.lot_stock_id, 5.0)
        self.env['stock.quant']._update_available_quantity(product_B, warehouse.lot_stock_id, 3.0)

        move_tmpl = {
            'name': 'Product',
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 4.0,
            'location_id': warehouse.lot_stock_id.id,
            'location_dest_id': self.partner.property_stock_customer.id,
            'warehouse_id': warehouse.id,
        }
        move_A_vals = dict(move_tmpl)
        move_A_vals.update({
            'product_id': product_A.id,
        })
        move_A = self.env['stock.move'].create(move_A_vals)
        move_B_vals = dict(move_tmpl)
        move_B_vals.update({
            'product_id': product_B.id,
        })
        move_B = self.env['stock.move'].create(move_B_vals)
        moves = move_A + move_B

        self.assertEqual(move_A.procure_method, 'make_to_stock', 'Move A should be "make_to_stock"')
        self.assertEqual(move_B.procure_method, 'make_to_stock', 'Move A should be "make_to_order"')
        moves._adjust_procure_method()
        self.assertEqual(move_A.procure_method, 'make_to_stock', 'Move A should be "make_to_stock"')
        self.assertEqual(move_B.procure_method, 'make_to_order', 'Move A should be "make_to_order"')

    def test_mtso_mto_adjust_02(self):
        """ Run '_adjust_procure_method' for products A & B:
        - Product A has 5.0 available
        - Product B has 3.0 available
        Stock moves (SM) are created for 2.0 + 2.0 units
        After '_adjust_procure_method':
        - SM for A is 'make_to_stock'
        - SM for B is 'make_to_stock' and 'make_to_order'
        """
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.id)], limit=1)
        final_location = self.partner.property_stock_customer
        product_A = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        product_B = self.env['product.product'].create({
            'name': 'Product B',
            'type': 'product',
        })

        # We alter one rule and we set it to 'mts_else_mto'
        rule = self.env['procurement.group']._get_rule(product_A, final_location, {'warehouse_id': warehouse})
        rule.procure_method = 'mts_else_mto'

        self.env['stock.quant']._update_available_quantity(product_A, warehouse.lot_stock_id, 5.0)
        self.env['stock.quant']._update_available_quantity(product_B, warehouse.lot_stock_id, 3.0)

        move_tmpl = {
            'name': 'Product',
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
            'location_id': warehouse.lot_stock_id.id,
            'location_dest_id': self.partner.property_stock_customer.id,
            'warehouse_id': warehouse.id,
        }
        move_A1_vals = dict(move_tmpl)
        move_A1_vals.update({
            'product_id': product_A.id,
        })
        move_A1 = self.env['stock.move'].create(move_A1_vals)
        move_A2_vals = dict(move_tmpl)
        move_A2_vals.update({
            'product_id': product_A.id,
        })
        move_A2 = self.env['stock.move'].create(move_A2_vals)
        move_B1_vals = dict(move_tmpl)
        move_B1_vals.update({
            'product_id': product_B.id,
        })
        move_B1 = self.env['stock.move'].create(move_B1_vals)
        move_B2_vals = dict(move_tmpl)
        move_B2_vals.update({
            'product_id': product_B.id,
        })
        move_B2 = self.env['stock.move'].create(move_B2_vals)
        moves = move_A1 + move_A2 + move_B1 + move_B2

        self.assertEqual(move_A1.procure_method, 'make_to_stock', 'Move A1 should be "make_to_stock"')
        self.assertEqual(move_A2.procure_method, 'make_to_stock', 'Move A2 should be "make_to_stock"')
        self.assertEqual(move_B1.procure_method, 'make_to_stock', 'Move B1 should be "make_to_stock"')
        self.assertEqual(move_B2.procure_method, 'make_to_stock', 'Move B2 should be "make_to_stock"')
        moves._adjust_procure_method()
        self.assertEqual(move_A1.procure_method, 'make_to_stock', 'Move A1 should be "make_to_stock"')
        self.assertEqual(move_A2.procure_method, 'make_to_stock', 'Move A2 should be "make_to_stock"')
        self.assertEqual(move_B1.procure_method, 'make_to_stock', 'Move B1 should be "make_to_stock"')
        self.assertEqual(move_B2.procure_method, 'make_to_order', 'Move B2 should be "make_to_order"')

    def test_mtso_mto_adjust_03(self):
        """ Run '_adjust_procure_method' for products A with 4.0 available
        2 Stock moves (SM) are created:
        - SM1 for 5.0 Units
        - SM2 for 3.0 Units
        SM1 is confirmed, so 'virtual_available' is -1.0.
        SM1 should become 'make_to_order'
        SM2 should remain 'make_to_stock'
        """
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.id)], limit=1)
        final_location = self.partner.property_stock_customer
        product_A = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })

        # We alter one rule and we set it to 'mts_else_mto'
        rule = self.env['procurement.group']._get_rule(product_A, final_location, {'warehouse_id': warehouse})
        rule.procure_method = 'mts_else_mto'

        self.env['stock.quant']._update_available_quantity(product_A, warehouse.lot_stock_id, 4.0)

        move_tmpl = {
            'name': 'Product',
            'product_id': product_A.id,
            'product_uom': self.uom_unit.id,
            'location_id': warehouse.lot_stock_id.id,
            'location_dest_id': self.partner.property_stock_customer.id,
            'warehouse_id': warehouse.id,
        }
        move_A1_vals = dict(move_tmpl)
        move_A1_vals.update({
            'product_uom_qty': 5.0,
        })
        move_A1 = self.env['stock.move'].create(move_A1_vals)
        move_A2_vals = dict(move_tmpl)
        move_A2_vals.update({
            'product_uom_qty': 3.0,
        })
        move_A2 = self.env['stock.move'].create(move_A2_vals)
        moves = move_A1 + move_A2

        self.assertEqual(move_A1.procure_method, 'make_to_stock', 'Move A1 should be "make_to_stock"')
        self.assertEqual(move_A2.procure_method, 'make_to_stock', 'Move A2 should be "make_to_stock"')
        move_A1._action_confirm()
        moves._adjust_procure_method()
        self.assertEqual(move_A1.procure_method, 'make_to_order', 'Move A should be "make_to_stock"')
        self.assertEqual(move_A2.procure_method, 'make_to_stock', 'Move A should be "make_to_order"')

    def test_delay_alert_3(self):
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        warehouse.delivery_steps = 'pick_pack_ship'
        partner_demo_customer = self.partner
        final_location = partner_demo_customer.property_stock_customer
        product_a = self.env['product.product'].create({
            'name': 'ProductA',
            'type': 'product',
        })
        pg = self.env['procurement.group'].create({'name': 'Test-delay_alert_3'})
        self.env['procurement.group'].run([
            pg.Procurement(
                product_a,
                4.0,
                product_a.uom_id,
                final_location,
                'delay',
                'delay',
                warehouse.company_id,
                {
                    'warehouse_id': warehouse,
                    'group_id': pg
                }
            ),
        ])
        ship, pack, pick = self.env['stock.move'].search([('product_id',  '=', product_a.id)])

        # by default they all the same `date`
        self.assertEqual(set((ship + pack + pick).mapped('date')), {pick.date})

        # pick - pack - ship
        ship.date += timedelta(days=2)
        pack.date += timedelta(days=1)
        self.assertFalse(pick.delay_alert_date)
        self.assertFalse(pack.delay_alert_date)
        self.assertFalse(ship.delay_alert_date)

        # move the pack after the ship
        # pick - ship - pack
        pack.date += timedelta(days=2)
        self.assertFalse(pick.delay_alert_date)
        self.assertFalse(pack.delay_alert_date)
        self.assertTrue(ship.delay_alert_date)
        self.assertAlmostEqual(ship.delay_alert_date, pack.date)

        # restore the pack before the ship
        # pick - pack - ship
        pack.date -= timedelta(days=2)
        self.assertFalse(pick.delay_alert_date)
        self.assertFalse(pack.delay_alert_date)
        self.assertFalse(ship.delay_alert_date)

        # move the pick after the pack
        # pack - ship - pick
        pick.date += timedelta(days=3)
        self.assertFalse(pick.delay_alert_date)
        self.assertTrue(pack.delay_alert_date)
        self.assertFalse(ship.delay_alert_date)
        self.assertAlmostEqual(pack.delay_alert_date, pick.date)

        # move the ship before the pack
        # ship - pack - pick
        ship.date -= timedelta(days=2)
        self.assertFalse(pick.delay_alert_date)
        self.assertTrue(pack.delay_alert_date)
        self.assertTrue(ship.delay_alert_date)
        self.assertAlmostEqual(pack.delay_alert_date, pick.date)
        self.assertAlmostEqual(ship.delay_alert_date, pack.date)

        # move the pack at the end
        # ship - pick - pack
        pack.date = pick.date + timedelta(days=2)
        self.assertFalse(pick.delay_alert_date)
        self.assertFalse(pack.delay_alert_date)
        self.assertTrue(ship.delay_alert_date)
        self.assertAlmostEqual(ship.delay_alert_date, pack.date)

        # fix the ship
        ship.date = pack.date + timedelta(days=2)
        self.assertFalse(pick.delay_alert_date)
        self.assertFalse(pack.delay_alert_date)
        self.assertFalse(ship.delay_alert_date)

    def test_packaging_route(self):
        """Create a route for product and another route for its packaging. Create
        a move of this product with this packaging. Check packaging route has
        priority over product route.
        """
        stock_location = self.env.ref('stock.stock_location_stock')

        push_location_1 = self.env['stock.location'].create({
            'location_id': stock_location.location_id.id,
            'name': 'push location 1',
        })

        push_location_2 = self.env['stock.location'].create({
            'location_id': stock_location.location_id.id,
            'name': 'push location 2',
        })

        route_on_product = self.env['stock.route'].create({
            'name': 'route on product',
            'rule_ids': [(0, False, {
                'name': 'create a move to push location 1',
                'location_src_id': stock_location.id,
                'location_dest_id': push_location_1.id,
                'company_id': self.env.company.id,
                'action': 'push',
                'auto': 'manual',
                'picking_type_id': self.env.ref('stock.picking_type_in').id,
            })],
        })

        route_on_packaging = self.env['stock.route'].create({
            'name': 'route on packaging',
            'packaging_selectable': True,
            'rule_ids': [(0, False, {
                'name': 'create a move to push location 2',
                'location_src_id': stock_location.id,
                'location_dest_id': push_location_2.id,
                'company_id': self.env.company.id,
                'action': 'push',
                'auto': 'manual',
                'picking_type_id': self.env.ref('stock.picking_type_in').id,
            })],
        })

        product = self.env['product.product'].create({
            'name': 'Product with packaging',
            'type': 'product',
            'route_ids': [(4, route_on_product.id, 0)]
        })

        packaging = self.env['product.packaging'].create({
            'name': 'box',
            'product_id': product.id,
            'route_ids': [(4, route_on_packaging.id, 0)]
        })


        move1 = self.env['stock.move'].create({
            'name': 'move with a route',
            'location_id': stock_location.id,
            'location_dest_id': stock_location.id,
            'product_id': product.id,
            'product_packaging_id': packaging.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1._action_confirm()

        pushed_move = move1.move_dest_ids
        self.assertEqual(pushed_move.location_dest_id.id, push_location_2.id)


class TestAutoAssign(TestStockCommon):
    def create_pick_ship(self):
        picking_client = self.env['stock.picking'].create({
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location,
            'picking_type_id': self.picking_type_out,
            'state': 'draft',
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
            'picking_type_id': self.picking_type_out,
            'state': 'draft',
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

    def test_auto_assign_0(self):
        """Create a outgoing MTS move without enough products in stock, then
        validate a incoming move to check if the outgoing move is automatically
        assigned.
        """
        pack_location = self.env['stock.location'].browse(self.pack_location)
        stock_location = self.env['stock.location'].browse(self.stock_location)
        self.env['stock.picking.type'].browse(self.picking_type_out).reservation_method = 'at_confirm'

        # create customer picking and move
        customer_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'picking_type_id': self.picking_type_out,
            'state': 'draft',
        })
        customer_move = self.env['stock.move'].create({
            'name': 'customer move',
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'product_id': self.productA.id,
            'product_uom': self.productA.uom_id.id,
            'product_uom_qty': 10.0,
            'picking_id': customer_picking.id,
            'picking_type_id': self.picking_type_out,
        })
        customer_picking.action_confirm()
        customer_picking.action_assign()
        self.assertEqual(customer_move.state, 'confirmed')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, stock_location), 0)

        # create supplier picking and move
        supplier_picking = self.env['stock.picking'].create({
            'location_id': self.customer_location,
            'location_dest_id': self.stock_location,
            'picking_type_id': self.picking_type_in,
            'state': 'draft',
        })
        supplier_move = self.env['stock.move'].create({
            'name': 'test_transit_1',
            'location_id': self.customer_location,
            'location_dest_id': self.stock_location,
            'product_id': self.productA.id,
            'product_uom': self.productA.uom_id.id,
            'product_uom_qty': 10.0,
            'picking_id': supplier_picking.id,
        })
        supplier_picking.action_confirm()
        supplier_picking.action_assign()
        supplier_move.picked = True
        supplier_picking._action_done()

        # customer move should be automatically assigned and no more available product in stock
        self.assertEqual(customer_move.state, 'assigned')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, stock_location), 0)

    def test_auto_assign_1(self):
        """Create a outgoing MTO move without enough products, then validate a
        move to make it available to check if the outgoing move is not
        automatically assigned.
        """
        picking_pick, picking_client = self.create_pick_ship()
        pack_location = self.env['stock.location'].browse(self.pack_location)
        stock_location = self.env['stock.location'].browse(self.stock_location)
        self.env['stock.picking.type'].browse(self.picking_type_out).reservation_method = 'at_confirm'

        # make some stock
        self.env['stock.quant']._update_available_quantity(self.productA, stock_location, 10.0)

        # create another move to make product available in pack_location
        picking_pick_2 = self.env['stock.picking'].create({
            'location_id': self.stock_location,
            'location_dest_id': self.pack_location,
            'picking_type_id': self.picking_type_out,
            'state': 'draft',
        })
        self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 10,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking_pick_2.id,
            'location_id': self.stock_location,
            'location_dest_id': self.pack_location,
            'state': 'confirmed',
        })
        picking_pick_2.action_assign()
        picking_pick_2.move_ids[0].move_line_ids[0].quantity = 10.0
        picking_pick_2.move_ids[0].picked = True
        picking_pick_2._action_done()

        self.assertEqual(picking_client.state, 'waiting', "MTO moves can't be automatically assigned.")
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, pack_location), 10.0)

    def test_auto_assign_reservation_method(self):
        """Test different stock.picking.type reservation methods by:
        1. Create multiple delivery picking types with different reservation methods
        2. Create/confirm outgoing pickings for each of these picking types for a product not in stock
        3. Create/do an incoming picking that fulfills all of the outgoing pickings
        4. Check that only the correct outgoing pickings are auto_assigned
        5. Additionally check that auto-assignment at confirmation correctly works when products are in stock
        Note, default reservation method is expected to be covered by other tests.
        Also check reservation_dates are as expected
        """

        stock_location = self.env['stock.location'].browse(self.stock_location)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, stock_location), 0)
        picking_type_out1 = self.env['stock.picking.type'].browse(self.picking_type_out).copy()
        picking_type_out2 = picking_type_out1.copy()
        picking_type_out3 = picking_type_out1.copy()
        picking_type_out4 = picking_type_out1.copy()
        picking_type_out1.reservation_method = 'manual'
        picking_type_out2.reservation_method = 'by_date'
        picking_type_out2.reservation_days_before = '1'
        picking_type_out3.reservation_method = 'by_date'
        picking_type_out3.reservation_days_before = '10'
        picking_type_out4.reservation_method = 'at_confirm'

        # 'manual' assign picking => should never auto-assign
        customer_picking1 = self.env['stock.picking'].create({
            'name': "Delivery 1",
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'picking_type_id': picking_type_out1.id,
            'state': 'draft',
        })

        # 'by_date' picking w/ 1 day before scheduled date auto-assign setting, set to 5 days in advance => shouldn't auto-assign
        customer_picking2 = customer_picking1.copy({'name': "Delivery 2",
                                                    'picking_type_id': picking_type_out2.id,
                                                    'scheduled_date': customer_picking1.scheduled_date + timedelta(days=5)})
        # 'by_date' picking w/ 10 days before scheduled date auto-assign setting, set to 5 days in advance => should auto-assign
        customer_picking3 = customer_picking2.copy({'name': "Delivery 3", 'picking_type_id': picking_type_out3.id})
        customer_picking4 = customer_picking3.copy({'name': "Delivery 4", 'picking_type_id': picking_type_out3.id})
        # 'at_confirm' picking
        customer_picking5 = customer_picking1.copy({'name': "Delivery 5", 'picking_type_id': picking_type_out4.id})

        # create their associated moves (needs to be in form view so compute functions properly trigger)
        customer_picking1 = Form(customer_picking1)
        with customer_picking1.move_ids_without_package.new() as move:
            move.product_id = self.productA
            move.product_uom_qty = 10
        customer_picking1 = customer_picking1.save()

        customer_picking2 = Form(customer_picking2)
        with customer_picking2.move_ids_without_package.new() as move:
            move.product_id = self.productA
            move.product_uom_qty = 10
        customer_picking2 = customer_picking2.save()

        customer_picking3 = Form(customer_picking3)
        with customer_picking3.move_ids_without_package.new() as move:
            move.product_id = self.productA
            move.product_uom_qty = 10
        customer_picking3 = customer_picking3.save()

        customer_picking4 = Form(customer_picking4)
        with customer_picking4.move_ids_without_package.new() as move:
            move.product_id = self.productA
            move.product_uom_qty = 10
        customer_picking4 = customer_picking4.save()

        customer_picking5 = Form(customer_picking5)
        with customer_picking5.move_ids_without_package.new() as move:
            move.product_id = self.productA
            move.product_uom_qty = 10
        customer_picking5 = customer_picking5.save()

        customer_picking1.action_assign()
        customer_picking2.action_assign()
        customer_picking3.action_assign()
        self.assertEqual(customer_picking1.move_ids.quantity, 0, "There should be no products available to reserve yet.")
        self.assertEqual(customer_picking2.move_ids.quantity, 0, "There should be no products available to reserve yet.")
        self.assertEqual(customer_picking3.move_ids.quantity, 0, "There should be no products available to reserve yet.")

        self.assertFalse(customer_picking1.move_ids.reservation_date, "Reservation Method: 'manual' shouldn't have a reservation_date")
        self.assertEqual(customer_picking2.move_ids.reservation_date, (customer_picking2.scheduled_date - timedelta(days=1)).date(),
                         "Reservation Method: 'by_date' should have a reservation_date = scheduled_date - reservation_days_before")
        self.assertFalse(customer_picking5.move_ids.reservation_date, "Reservation Method: 'at_confirm' shouldn't have a reservation_date until confirmed")

        # create supplier picking and move
        supplier_picking = self.env['stock.picking'].create({
            'location_id': self.customer_location,
            'location_dest_id': self.stock_location,
            'picking_type_id': self.picking_type_in,
            'state': 'draft',
        })
        supplier_move = self.env['stock.move'].create({
            'name': 'test_transit_1',
            'location_id': self.customer_location,
            'location_dest_id': self.stock_location,
            'product_id': self.productA.id,
            'product_uom': self.productA.uom_id.id,
            'product_uom_qty': 50.0,
            'picking_id': supplier_picking.id,
        })
        supplier_move.quantity = 50
        supplier_move.picked = True
        supplier_picking._action_done()

        self.assertEqual(customer_picking1.move_ids.quantity, 0, "Reservation Method: 'manual' shouldn't ever auto-assign")
        self.assertEqual(customer_picking2.move_ids.quantity, 0, "Reservation Method: 'by_date' shouldn't auto-assign when not within reservation date range")
        self.assertEqual(customer_picking3.move_ids.quantity, 10, "Reservation Method: 'by_date' should auto-assign when within reservation date range")
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, stock_location), 40)

        customer_picking4.action_confirm()
        customer_picking5.action_confirm()
        self.assertEqual(customer_picking4.move_ids.quantity, 10, "Reservation Method: 'by_date' should auto-assign when within reservation date range at confirmation")
        self.assertEqual(customer_picking5.move_ids.quantity, 10, "Reservation Method: 'at_confirm' should auto-assign at confirmation")

    def test_serial_lot_ids(self):
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.customer_location = self.env.ref('stock.stock_location_customers')
        self.supplier_location = self.env.ref('stock.stock_location_suppliers')
        self.uom_unit = self.env.ref('uom.product_uom_unit')
        self.product_serial = self.env['product.product'].create({
            'name': 'PSerial',
            'type': 'product',
            'tracking': 'serial',
            'categ_id': self.env.ref('product.product_category_all').id,
        })

        move = self.env['stock.move'].create({
            'name': 'TestReceive',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product_serial.id,
            'product_uom': self.uom_unit.id,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
        })
        self.assertEqual(move.state, 'draft')
        lot1 = self.env['stock.lot'].create({
            'name': 'serial1',
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.lot'].create({
            'name': 'serial2',
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
        })
        lot3 = self.env['stock.lot'].create({
            'name': 'serial3',
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
        })
        move.lot_ids = [(4, lot1.id)]
        move.lot_ids = [(4, lot2.id)]
        move.lot_ids = [(4, lot3.id)]
        self.assertEqual(move.quantity, 3.0)
        move.lot_ids = [(3, lot2.id)]
        self.assertEqual(move.quantity, 2.0)

        self.uom_dozen = self.env.ref('uom.product_uom_dozen')
        move = self.env['stock.move'].create({
            'name': 'TestReceiveDozen',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product_serial.id,
            'product_uom': self.uom_dozen.id,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
        })
        move.lot_ids = [(4, lot1.id)]
        move.lot_ids = [(4, lot2.id)]
        move.lot_ids = [(4, lot3.id)]
        self.assertEqual(move.quantity, 3.0/12.0)
