# -*- coding: utf-8 -*-

from odoo.addons.stock.tests.common import TestStockCommon
from odoo.tests import Form

class TestReturnPicking(TestStockCommon):

    def test_stock_return_picking_line_creation(self):
        StockReturnObj = self.env['stock.return.picking']

        picking_out = self.PickingObj.create({
            'picking_type_id': self.picking_type_out.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })
        move_1 = self.MoveObj.create({
            'name': self.UnitA.name,
            'product_id': self.UnitA.id,
            'product_uom_qty': 2,
            'product_uom': self.uom_unit.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })
        move_2 = self.MoveObj.create({
            'name': self.UnitA.name,
            'product_id': self.UnitA.id,
            'product_uom_qty': 1,
            'product_uom': self.uom_dozen.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })
        picking_out.action_confirm()
        picking_out.action_assign()
        move_1.quantity = 2
        move_2.quantity = 1
        picking_out.move_ids.picked = True
        picking_out.button_validate()
        return_picking = StockReturnObj.create({
            'picking_id': picking_out.id,
        })
        return_picking._compute_moves_locations()

        ReturnPickingLineObj = self.env['stock.return.picking.line']
        # Check return line of uom_unit move
        return_line = ReturnPickingLineObj.search([('move_id', '=', move_1.id), ('wizard_id.picking_id', '=', picking_out.id)], limit=1)
        self.assertEqual(return_line.product_id.id, self.UnitA.id, 'Return line should have exact same product as outgoing move')
        self.assertEqual(return_line.uom_id.id, self.uom_unit.id, 'Return line should have exact same uom as product uom')
        self.assertEqual(return_line.quantity, 0, 'Return line should have 0 quantity')
        return_line.quantity = 2
        # Check return line of uom_dozen move
        return_line = ReturnPickingLineObj.search([('move_id', '=', move_2.id), ('wizard_id.picking_id', '=', picking_out.id)], limit=1)
        self.assertEqual(return_line.product_id.id, self.UnitA.id, 'Return line should have exact same product as outgoing move')
        self.assertEqual(return_line.uom_id.id, self.uom_unit.id, 'Return line should have exact same uom as product uom')
        self.assertEqual(return_line.quantity, 0, 'Return line should have 0 quantity')
        return_line.quantity = 1

    def test_return_picking_SN_pack(self):
        """
            Test returns of pickings with serial tracked products put in packs
        """
        product_serial = self.env['product.product'].with_user(self.user_stock_manager).create({
            'name': 'Tracked by SN',
            'is_storable': True,
            'tracking': 'serial',
        })
        serial1 = self.env['stock.lot'].create({
            'name': 'serial1',
            'product_id': product_serial.id,
        })
        self.env['stock.quant']._update_available_quantity(product_serial, self.stock_location, 1.0, lot_id=serial1)

        picking = self.PickingObj.create({
            'picking_type_id': self.picking_type_out.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })
        self.MoveObj.create({
            'name': product_serial.name,
            'product_id': product_serial.id,
            'product_uom_qty': 1,
            'product_uom': self.uom_unit.id,
            'picking_id': picking.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })

        picking.action_confirm()
        picking.action_assign()
        picking.move_ids.move_line_ids.quantity = 1
        picking.action_put_in_pack()
        picking.move_ids.picked = True
        picking.button_validate()
        customer_stock = self.env['stock.quant']._gather(product_serial, self.customer_location, lot_id=serial1)
        self.assertEqual(len(customer_stock), 1)
        self.assertEqual(customer_stock.quantity, 1)

        return_wizard = self.env['stock.return.picking'].with_context(active_id=picking.id, active_model='stock.picking').create({})
        return_wizard.product_return_moves.quantity = 1
        res = return_wizard.action_create_returns()
        picking2 = self.PickingObj.browse(res["res_id"])

        # Assigned user should not be copied
        self.assertTrue(picking.user_id)
        self.assertFalse(picking2.user_id)

        picking2.action_confirm()
        picking2.move_ids.move_line_ids.quantity = 1
        picking2.move_ids.picked = True
        picking2.button_validate()
        self.assertFalse(self.env['stock.quant']._gather(product_serial, self.customer_location, lot_id=serial1))

    def test_return_location(self):
        """ test default return location are taken into account
        """
        # Make a delivery
        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 100)

        delivery_picking = self.PickingObj.create({
            'picking_type_id': self.picking_type_out.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })
        out_move = self.MoveObj.create({
            'name': "OUT move",
            'product_id':self.productA.id,
            'product_uom_qty': 1,
            'picking_id': delivery_picking.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })
        out_move.quantity = 1
        delivery_picking.button_validate()

        # Create return
        return_wizard = self.env['stock.return.picking'].with_context(active_id=delivery_picking.id, active_model='stock.picking').create({})
        return_wizard.product_return_moves.quantity = 1
        res = return_wizard.action_create_returns()
        return_picking = self.PickingObj.browse(res["res_id"])
        self.assertEqual(return_picking.location_dest_id, out_move.location_id)

    def test_return_incoming_picking(self):
        """
            Test returns of incoming pickings have the same partner assigned to them
        """
        partner = self.env['res.partner'].with_user(self.user_stock_manager).create({'name': 'Jean'})
        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_in.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'partner_id': partner.id,
            'move_ids': [(0, 0, {
                'name': self.UnitA.name,
                'product_id': self.UnitA.id,
                'product_uom_qty': 1,
                'product_uom': self.uom_unit.id,
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
            })],
        })
        receipt.button_validate()
        # create a return picking
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=receipt.ids, active_id=receipt.ids[0],
            active_model='stock.picking'))
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 1.0
        stock_return_picking_action = stock_return_picking.action_create_returns()
        return_picking = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_picking.button_validate()
        self.assertEqual(return_picking.move_ids[0].partner_id.id, receipt.partner_id.id)

    def test_stock_return_for_exchange(self):
        '''
        Test the stock return for exchange by creating a picking with moves and
        create a return exchange.
        '''
        # create a storable product
        product_serial = self.env['product.product'].with_user(self.user_stock_manager).create({
            'name': 'Tracked by SN',
            'is_storable': True,
            'tracking': 'serial',
        })
        # Create a stock picking with moves
        picking = self.PickingObj.create({
            'picking_type_id': self.picking_type_in.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'move_ids': [(0, 0, {
                'name': product_serial.name,
                'product_id': product_serial.id,
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
                'product_uom_qty': 1,
                'product_uom': self.uom_unit.id,
            })],
        })
        picking.action_confirm()
        # Update the lots of move lines
        picking.move_line_ids.write({
            'lot_name': 'Alsh',
        })
        picking.button_validate()
        # Create a return picking with the above respected picking
        return_picking = self.env['stock.return.picking'].with_context(active_id=picking.id, active_ids=picking.ids, active_model='stock.picking').create({})
        # Change the quantity of the product return move from 0 to 1
        return_picking.product_return_moves.quantity = 1.0
        # Create a return picking exchange
        res = return_picking.action_create_exchanges()
        return_picking = self.env['stock.picking'].browse(res['res_id'])
        self.assertTrue(return_picking)
        self.assertEqual(len(return_picking.move_ids), 1)
