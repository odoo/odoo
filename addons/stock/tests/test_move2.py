# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock.tests.common import TestStockCommon
from odoo.exceptions import UserError
from odoo import api, registry
from odoo.tests.common import TransactionCase


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
        picking_pick.do_transfer()

        self.assertEqual(picking_client.state, 'assigned', 'The state of the client should be assigned')

        # Now partially transfer the ship
        picking_client.move_lines[0].move_line_ids[0].qty_done = 5
        picking_client.do_transfer() # no new in order to create backorder

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
        picking_pick.do_transfer()

        self.assertEqual(move_pick.state, 'done')
        self.assertEqual(picking_pick.state, 'done')
        self.assertEqual(move_cust.state, 'assigned')
        self.assertEqual(picking_client.state, 'assigned', 'The picking should not assign what it does not have')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, stock_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, pack_location), 5.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.productA, stock_location)), 0.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.productA, pack_location)), 1.0)

    def test_mto_moves_return(self):
        picking_pick, picking_client = self.create_pick_ship()
        stock_location = self.env['stock.location'].browse(self.stock_location)
        self.env['stock.quant']._update_available_quantity(self.productA, stock_location, 10.0)

        picking_pick.action_assign()
        picking_pick.move_lines[0].move_line_ids[0].qty_done = 10.0
        picking_pick.do_transfer()
        self.assertEqual(picking_pick.state, 'done')
        self.assertEqual(picking_client.state, 'assigned')

        # return a part of what we've done
        stock_return_picking = self.env['stock.return.picking']\
            .with_context(active_ids=picking_pick.ids, active_id=picking_pick.ids[0])\
            .create({})
        stock_return_picking.product_return_moves.quantity = 2.0 # Return only 2
        stock_return_picking_action = stock_return_picking.create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_pick.move_lines[0].move_line_ids[0].qty_done = 2.0
        return_pick.do_transfer()
        # the client picking should not be assigned anymore, as we returned partially what we took
        self.assertEqual(picking_client.state, 'confirmed')

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
        picking_pick.do_transfer()
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
        stock_return_picking = self.env['stock.return.picking']\
            .with_context(active_ids=picking_pick.ids, active_id=picking_pick.ids[0])\
            .create({})
        stock_return_picking.product_return_moves.quantity = 10.0
        stock_return_picking_action = stock_return_picking.create_returns()
        return_pick_picking = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])

        self.assertEqual(return_pick_picking.state, 'waiting')

        stock_return_picking = self.env['stock.return.picking']\
            .with_context(active_ids=picking_ship.ids, active_id=picking_ship.ids[0])\
            .create({})
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

        stock_return_picking = self.env['stock.return.picking']\
            .with_context(active_ids=picking_ship.ids, active_id=picking_ship.ids[0])\
            .create({})
        stock_return_picking.product_return_moves.quantity = 1.0
        stock_return_picking_action = stock_return_picking.create_returns()
        return_ship_picking = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])

        return_ship_picking.move_lines[0].move_line_ids[0].write({
            'qty_done': 1.0,
            'lot_id': lot.id,
        })
        return_ship_picking.action_done()

        stock_return_picking = self.env['stock.return.picking']\
            .with_context(active_ids=picking_pack.ids, active_id=picking_pack.ids[0])\
            .create({})
        stock_return_picking.product_return_moves.quantity = 1.0
        stock_return_picking_action = stock_return_picking.create_returns()
        return_pack_picking = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])

        return_pack_picking.move_lines[0].move_line_ids[0].qty_done = 1.0
        return_pack_picking.action_done()

        stock_return_picking = self.env['stock.return.picking']\
            .with_context(active_ids=picking_pick.ids, active_id=picking_pick.ids[0])\
            .create({})
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

    def test_put_in_pack(self):
        """ In a pick pack ship scenario, create two packs in pick and check that
        they are correctly recognised and handled by the pack and ship picking.
        Along this test, we'll use action_toggle_processed to process a pack
        from the entire_package_ids one2many and we'll directly fill the move
        lines, the latter is the behavior when the user did not enable the display
        of entire packs on the picking type.
        """
        picking_pick, picking_pack, picking_ship = self.create_pick_pack_ship()
        ship_move = self.env['stock.move'].create({
            'name': self.productB.name,
            'product_id': self.productB.id,
            'product_uom_qty': 4,
            'product_uom': self.productB.uom_id.id,
            'picking_id': picking_ship.id,
            'location_id': self.output_location,
            'location_dest_id': self.customer_location,
        })

        pack_move = self.env['stock.move'].create({
            'name': self.productB.name,
            'product_id': self.productB.id,
            'product_uom_qty': 4,
            'product_uom': self.productB.uom_id.id,
            'picking_id': picking_pack.id,
            'location_id': self.pack_location,
            'location_dest_id': self.output_location,
            'move_dest_ids': [(4, ship_move.id)],
        })

        self.env['stock.move'].create({
            'name': self.productB.name,
            'product_id': self.productB.id,
            'product_uom_qty': 4,
            'product_uom': self.productB.uom_id.id,
            'picking_id': picking_pick.id,
            'location_id': self.stock_location,
            'location_dest_id': self.pack_location,
            'move_dest_ids': [(4, pack_move.id)],
            'state': 'confirmed',
        })
        stock_location = self.env['stock.location'].browse(self.stock_location)

        self.env['stock.quant']._update_available_quantity(self.productA, stock_location, 1.0)
        self.env['stock.quant']._update_available_quantity(self.productB, stock_location, 4.0)
        picking_pick.action_assign()
        picking_pick.move_line_ids.filtered(lambda ml: ml.product_id == self.productA).qty_done = 1.0
        picking_pick.move_line_ids.filtered(lambda ml: ml.product_id == self.productB).qty_done = 2.0
        first_pack = picking_pick.put_in_pack()
        picking_pick.move_line_ids.filtered(lambda ml: ml.product_id == self.productB and ml.qty_done == 0.0).qty_done = 2.0
        second_pack = picking_pick.put_in_pack()
        picking_pick.button_validate()
        self.assertEqual(len(first_pack.quant_ids), 2)
        self.assertEqual(len(second_pack.quant_ids), 1)
        picking_pack.action_assign()
        self.assertEqual(len(picking_pack.entire_package_ids), 2)
        output_sub_location = self.env['stock.location'].create({'name': 'sub1', 'location_id': self.output_location})
        picking_pack.entire_package_ids[0].with_context(
            {'picking_id': picking_pack.id, 'destination_location': output_sub_location.id}).action_toggle_processed()
        picking_pack.entire_package_ids[1].with_context(
            {'picking_id': picking_pack.id, 'destination_location': output_sub_location.id}).action_toggle_processed()
        self.assertEqual(picking_pack.move_line_ids[:1].location_dest_id, output_sub_location)
        picking_pack.button_validate()
        self.assertEqual(first_pack.location_id, output_sub_location)
        self.assertEqual(second_pack.location_id, output_sub_location)
        self.assertEqual(len(picking_pack.entire_package_ids), 2)
        picking_ship.action_assign()
        self.assertEqual(picking_ship.move_line_ids[:1].location_id, output_sub_location)
        for move_line in picking_ship.move_line_ids:
            move_line.qty_done = move_line.product_uom_qty
        picking_ship.button_validate()
        quants_of_products_ab = self.env['stock.quant'].search([('product_id', 'in', (self.productA.id, self.productB.id))])
        quants_of_product_a = quants_of_products_ab.filtered(lambda q: q.product_id == self.productA)
        quants_of_product_b = quants_of_products_ab.filtered(lambda q: q.product_id == self.productB)
        self.assertEqual(quants_of_products_ab.mapped('location_id.id'), [self.customer_location])
        self.assertEqual(len(quants_of_product_a), 1)
        self.assertEqual(len(quants_of_product_b), 2)

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
        delivery_order.do_transfer()
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
        delivery_order.do_transfer()
        self.assertNotEqual(delivery_order.date_done, False)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, pack_location), 0.0)

        backorder = self.env['stock.picking'].search([('backorder_id', '=', delivery_order.id)])
        self.assertEqual(backorder.state, 'confirmed')

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
        delivery_order.with_context(debug=True).do_transfer()
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
        delivery_order.do_transfer()
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
        receipt.with_context(debug=True).do_transfer()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.productA, stock_location), 2.0)

        self.assertEqual(move1.product_qty, 2.0)
        self.assertEqual(move1.quantity_done, 2.0)
        self.assertEqual(move1.reserved_availability, 0.0)
        self.assertEqual(move1.move_line_ids.product_qty, 0.0)  # change reservation to 0 for done move
        self.assertEqual(sum(move1.move_line_ids.mapped('qty_done')), 2.0)
        self.assertEqual(move1.state, 'done')

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
        inventory.action_done()
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
        inventory.action_done()
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
        inventory.action_done()
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
        inventory.action_done()
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
        delivery_order.force_assign()
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
        delivery_order.force_assign()
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
        delivery_order.force_assign()
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
        delivery_order.force_assign()
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
        with registry().cursor() as cr:
            env = api.Environment(cr, 1, {})
            dp = env.ref('product.decimal_product_uom')
            self.old_digits = dp.digits
            dp.digits = 7
        super(TestStockUOM, self).setUp()

    def tearDown(self):
        super(TestStockUOM, self).tearDown()
        with self.registry.cursor() as cr:
            env = api.Environment(cr, 1, {})
            dp = env.ref('product.decimal_product_uom')
            dp.digits = self.old_digits

    def test_pickings_transfer_with_different_uom_and_back_orders(self):
        """ Picking transfer with diffrent unit of meassure. """
        # weight category
        categ_test = self.env['product.uom.categ'].create({'name': 'Bigger than tons'})

        T_LBS = self.env['product.uom'].create({
            'name': 'T-LBS',
            'category_id': categ_test.id,
            'uom_type': 'reference',
            'rounding': 0.01
        })
        T_GT = self.env['product.uom'].create({
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


class TestRoutes(TransactionCase):
    def test_pick_ship_1(self):
        """ Enable the pick ship route, force a procurement group on the
        pick. When a second move is added, make sure the `partner_id` and
        `origin` fields are erased.
        """
        product1 = self.env['product.product'].create({
            'name': 'product a',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        uom_unit = self.env.ref('product.product_uom_unit')
        wh = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.id)], limit=1)

        # create and get back the pick ship route
        wh.write({'delivery_steps': 'pick_ship'})
        pick_ship_route = wh.route_ids.filtered(lambda r: 'Pick + Ship' in r.name)

        # create a procurement group and set in on the pick procurement rule
        procurement_group0 = self.env['procurement.group'].create({})
        pick_rule = pick_ship_route.pull_ids.filtered(lambda rule: 'Stock -> Output' in rule.name)
        push_rule = pick_ship_route.pull_ids - pick_rule
        pick_rule.write({
            'group_propagation_option': 'fixed',
            'group_id': procurement_group0.id,
        })

        stock_location = pick_rule.location_src_id
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
            'product_id': product1.id,
            'product_uom': uom_unit.id,
            'product_uom_qty': 1.0,
            'warehouse_id': wh.id,
            'group_id': procurement_group1.id,
            'origin': 'origin1',
        })

        move2 = self.env['stock.move'].create({
            'name': 'second out move',
            'procure_method': 'make_to_order',
            'location_id': ship_location.id,
            'location_dest_id': customer_location.id,
            'product_id': product1.id,
            'product_uom': uom_unit.id,
            'product_uom_qty': 1.0,
            'warehouse_id': wh.id,
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

