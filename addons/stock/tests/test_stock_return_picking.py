# -*- coding: utf-8 -*-

from odoo.addons.stock.tests.common import TestStockCommon
from odoo.tests import Form

class TestReturnPicking(TestStockCommon):

    def test_stock_return_picking_line_creation(self):
        StockReturnObj = self.env['stock.return.picking']

        picking_out = self.PickingObj.create({
            'picking_type_id': self.picking_type_out,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        move_1 = self.MoveObj.create({
            'name': self.UnitA.name,
            'product_id': self.UnitA.id,
            'product_uom_qty': 2,
            'product_uom': self.uom_unit.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        move_2 = self.MoveObj.create({
            'name': self.UnitA.name,
            'product_id': self.UnitA.id,
            'product_uom_qty': 1,
            'product_uom': self.uom_dozen.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        picking_out.action_confirm()
        picking_out.action_assign()
        move_1.quantity = 2
        move_2.quantity = 1
        picking_out.move_ids.picked = True
        picking_out.button_validate()
        StockReturnObj.with_context(active_id=picking_out.id, active_ids=picking_out.ids, active_model='stock.picking').create({})

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
        wh_stock = self.env['stock.location'].browse(self.stock_location)
        customer_location = self.env['stock.location'].browse(self.customer_location)

        product_serial = self.env['product.product'].create({
            'name': 'Tracked by SN',
            'is_storable': True,
            'tracking': 'serial',
        })
        serial1 = self.env['stock.lot'].create({
            'name': 'serial1',
            'product_id': product_serial.id,
        })
        self.env['stock.quant']._update_available_quantity(product_serial, wh_stock, 1.0, lot_id=serial1)

        picking = self.PickingObj.create({
            'picking_type_id': self.picking_type_out,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
        })
        self.MoveObj.create({
            'name': product_serial.name,
            'product_id': product_serial.id,
            'product_uom_qty': 1,
            'product_uom': self.uom_unit.id,
            'picking_id': picking.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
        })

        picking.action_confirm()
        picking.action_assign()
        picking.move_ids.move_line_ids.quantity = 1
        picking.action_put_in_pack()
        picking.move_ids.picked = True
        picking.button_validate()
        customer_stock = self.env['stock.quant']._gather(product_serial, customer_location, lot_id=serial1)
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
        self.assertFalse(self.env['stock.quant']._gather(product_serial, customer_location, lot_id=serial1))

    def test_return_location(self):
        """ test default return location are taken into account
        """
        # Make a delivery
        wh_stock = self.env['stock.location'].browse(self.stock_location)
        self.env['stock.quant']._update_available_quantity(self.productA, wh_stock, 100)

        delivery_picking = self.PickingObj.create({
            'picking_type_id': self.picking_type_out,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
        })
        out_move = self.MoveObj.create({
            'name': "OUT move",
            'product_id':self.productA.id,
            'product_uom_qty': 1,
            'picking_id': delivery_picking.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
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
        partner = self.env['res.partner'].create({'name': 'Jean'})
        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_in,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'partner_id': partner.id,
            'move_ids': [(0, 0, {
                'name': self.UnitA.name,
                'product_id': self.UnitA.id,
                'product_uom_qty': 1,
                'product_uom': self.uom_unit.id,
                'location_id': self.supplier_location,
                'location_dest_id': self.stock_location,
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
        product_serial = self.env['product.product'].create({
            'name': 'Tracked by SN',
            'is_storable': True,
            'tracking': 'serial',
        })
        # Create a stock picking with moves
        original_picking = self.PickingObj.create({
            'picking_type_id': self.picking_type_in,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'move_ids': [(0, 0, {
                'name': product_serial.name,
                'product_id': product_serial.id,
                'location_id': self.supplier_location,
                'location_dest_id': self.stock_location,
                'product_uom_qty': 10,
                'product_uom': self.uom_unit.id,
            })],
        })
        original_picking.action_confirm()
        # Update the lots of move lines
        for i in range(10):
            original_picking.move_line_ids[i].lot_name = f'Test Lot {i}'
        original_picking.button_validate()
        # Create a return picking with the above respected picking
        return_picking_wizard = self.env['stock.return.picking'].with_context(
            active_id=original_picking.id, active_ids=original_picking.ids, active_model='stock.picking'
        ).create({})
        # Change the quantity of the product return move from 0 to 3
        return_picking_wizard.product_return_moves.quantity = 3.0
        # Create a return picking exchange
        return_picking_wizard.action_create_exchanges()

        # There should be 3 transfers: original, return, exchange
        self.assertEqual(
            len(self.env['stock.picking'].search([('product_id', '=', product_serial.id)])), 3
        )

        return_picking = original_picking.return_ids
        exchange_picking = return_picking.return_ids

        # Original: one return (return picking), type in, 10 items
        self.assertEqual(original_picking.return_count, 1)
        self.assertEqual(original_picking.picking_type_id.id, self.picking_type_in)
        self.assertEqual(len(original_picking.move_line_ids), 10)

        # Return: one return (exchange picking), type out, 3 item
        self.assertEqual(return_picking.return_count, 1)
        self.assertEqual(return_picking.picking_type_id.id, self.picking_type_out)
        self.assertEqual(len(return_picking.move_line_ids), 3)
        # By default, the serial IDs picked are the first 3 of the original picking
        # and it should not be possible to create new serial numbers.
        self.assertListEqual(return_picking.move_line_ids.lot_id.ids, original_picking.move_line_ids[:3].lot_id.ids)
        self.assertEqual(return_picking.move_ids.display_assign_serial, False)

        # Exchange: no returns, type in, 3 item
        self.assertEqual(exchange_picking.return_count, 0)
        self.assertEqual(exchange_picking.picking_type_id.id, self.picking_type_in)
        self.assertEqual(len(exchange_picking.move_line_ids), 3)
        # There should be not pre-selected serial IDs for the exchange picking
        # and it should be possible to create new serial numbers because it's an incoming picking.
        self.assertListEqual(exchange_picking.move_line_ids.lot_id.ids, [])
        self.assertEqual(exchange_picking.move_ids.display_assign_serial, True)

    def test_stock_picking_report_has_return(self):
        """
        Ensures that only returned serialized products are marked as returned.

        Scenario:
        - A delivery of two serialized units
        - One unit is returned

        Expected:
        - The stock lot report lists two entries
        - Only the returned unit has `has_return = True`, the other remains `False`
        """
        wh_stock = self.env['stock.location'].browse(self.stock_location)
        partner = self.env['res.partner'].create({'name': 'Test Customer'})

        product_serial = self.env['product.product'].create({
            'name': 'Tracked by SN',
            'is_storable': True,
            'tracking': 'serial',
        })

        serial_1 = self.env['stock.lot'].create({'name': 'SN1', 'product_id': product_serial.id})
        serial_2 = self.env['stock.lot'].create({'name': 'SN2', 'product_id': product_serial.id})

        self.env['stock.quant']._update_available_quantity(product_serial, wh_stock, 1.0, lot_id=serial_1)
        self.env['stock.quant']._update_available_quantity(product_serial, wh_stock, 1.0, lot_id=serial_2)

        picking = self.PickingObj.create({
            'partner_id': partner.id,
            'picking_type_id': self.picking_type_out,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'move_ids': [(0, 0, {
                'name': 'Move SN',
                'product_id': product_serial.id,
                'product_uom_qty': 2,
                'product_uom': product_serial.uom_id.id,
                'location_id': self.stock_location,
                'location_dest_id': self.customer_location,
            })],
        })

        picking.action_confirm()
        picking.action_assign()
        picking.move_ids.picked = True
        picking.button_validate()

        return_wizard = self.env['stock.return.picking'].with_context(active_id=picking.id, active_model='stock.picking').create({})
        return_wizard.product_return_moves.quantity = 1
        res = return_wizard.action_create_returns()
        return_picking = self.PickingObj.browse(res["res_id"])

        return_picking.action_confirm()
        return_picking.move_ids.picked = True
        return_picking.button_validate()
        self.env['stock.move.line'].flush_model()

        lot_report = self.env['stock.lot.report'].search([
            ('partner_id', '=', partner.id),
        ], order='id')
        self.assertRecordValues(lot_report, [
            {'lot_id': serial_1.id, 'has_return': True},
            {'lot_id': serial_2.id, 'has_return': False},
        ])

    def test_product_quantities_in_return_for_exchange(self):
        """ Ensure that on-hand and forecast quantities are correctly computed
        whe doing an exchange on an incoming picking. """
        original_picking = self.PickingObj.create({
            'picking_type_id': self.picking_type_in,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'move_ids': [(0, 0, {
                'name': self.productA.name,
                'product_id': self.productA.id,
                'location_id': self.supplier_location,
                'location_dest_id': self.stock_location,
                'product_uom_qty': 10,
                'product_uom': self.uom_unit.id,
            })],
        })
        original_picking.button_validate()

        # Product received: both on-hand and forecasted quantities should be 10
        self.assertEqual(self.productA.qty_available, 10)
        self.assertEqual(self.productA.virtual_available, 10)

        return_picking_wizard = self.env['stock.return.picking'].with_context(
            active_id=original_picking.id, active_ids=original_picking.ids, active_model='stock.picking'
        ).create({})
        return_picking_wizard.product_return_moves.quantity = 2
        return_picking_wizard.action_create_exchanges()

        return_picking = original_picking.return_ids
        exchange_picking = return_picking.return_ids

        return_picking.button_validate()

        # 2 products returned: on-hand = 8, forecasted = 10
        self.assertEqual(self.productA.qty_available, 8)
        self.assertEqual(self.productA.virtual_available, 10)

        exchange_picking.button_validate()

        # 2 exchanged products received: both on-hand and forecasted quantities should be 10
        self.assertEqual(self.productA.qty_available, 10)
        self.assertEqual(self.productA.virtual_available, 10)
