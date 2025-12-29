# -*- coding: utf-8 -*-

from odoo import Command
from odoo.addons.stock.tests.common import TestStockCommon
from odoo.tests import tagged, Form


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestReturnPicking(TestStockCommon):

    def test_stock_return_picking_line_creation(self):
        picking_out = self.PickingObj.create({
            'picking_type_id': self.picking_type_out.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })
        move_1 = self.MoveObj.create({
            'product_id': self.productA.id,
            'product_uom_qty': 2,
            'uom_id': self.uom_unit.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })
        move_2 = self.MoveObj.create({
            'product_id': self.productA.id,
            'product_uom_qty': 1,
            'uom_id': self.uom_dozen.id,
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
        return_picking = picking_out._create_return()

        # Check return line of uom_unit move
        return_move = return_picking.move_ids.filtered(lambda m: m.move_orig_ids.id == move_1.id)
        self.assertEqual(return_move.product_id.id, self.productA.id, 'Return line should have exact same product as outgoing move')
        self.assertEqual(return_move.uom_id.id, move_1.uom_id.id, 'Return line should have exact same uom as move uom')
        self.assertEqual(return_move.quantity, 0, 'Return line should have 0 quantity')
        # Check return line of uom_dozen move
        return_move = return_picking.move_ids.filtered(lambda m: m.move_orig_ids.id == move_2.id)
        self.assertEqual(return_move.product_id.id, self.productA.id, 'Return line should have exact same product as outgoing move')
        self.assertEqual(return_move.uom_id.id, move_2.uom_id.id, 'Return line should have exact same uom as move uom')
        self.assertEqual(return_move.quantity, 0, 'Return line should have 0 quantity')

    def test_return_picking_SN_pack(self):
        """
            Test returns of pickings with serial tracked products put in packs
        """
        product_serial = self.env['product.product'].create({
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
            'product_id': product_serial.id,
            'product_uom_qty': 1,
            'uom_id': self.uom_unit.id,
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

        picking2 = picking._create_return()

        # Assigned user should not be copied
        self.assertTrue(picking.user_id)
        self.assertFalse(picking2.user_id)

        picking2.move_ids.product_uom_qty = 1
        picking2.action_assign()
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
            'product_id':self.productA.id,
            'product_uom_qty': 1,
            'picking_id': delivery_picking.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })
        out_move.quantity = 1
        delivery_picking.button_validate()

        # Create return
        return_picking = delivery_picking._create_return()
        self.assertEqual(return_picking.location_dest_id, out_move.location_id)

    def test_return_incoming_picking(self):
        """
            Test returns of incoming pickings have the same partner assigned to them
        """
        partner = self.env['res.partner'].create({'name': 'Jean'})
        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_in.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'partner_id': partner.id,
            'move_ids': [Command.create({
                'product_id': self.productA.id,
                'product_uom_qty': 1,
                'uom_id': self.uom_unit.id,
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
            })],
        })
        receipt.button_validate()
        # create a return picking
        return_picking = receipt._create_return()
        return_picking.move_ids.product_uom_qty = 1.0
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
            'picking_type_id': self.picking_type_in.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'move_ids': [Command.create({
                'product_id': product_serial.id,
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
                'product_uom_qty': 10,
                'uom_id': self.uom_unit.id,
            })],
        })
        original_picking.action_confirm()
        # Update the lots of move lines
        for i in range(10):
            original_picking.move_line_ids[i].lot_name = f'Test Lot {i}'
        original_picking.button_validate()
        # Create a return picking with the above respected picking for 3 products
        return_picking = original_picking._create_return()
        return_picking.move_ids.product_uom_qty = 3.0
        return_picking.action_confirm()
        return_picking.action_assign()

        # Create a return picking exchange
        return_picking.action_exchange()

        # There should be 3 transfers: original, return, exchange
        self.assertEqual(
            len(self.env['stock.picking'].search([('product_id', '=', product_serial.id)])), 3
        )

        return_picking = original_picking.return_ids
        exchange_picking = return_picking.return_ids
        exchange_picking.action_confirm()
        exchange_picking.action_assign()

        # Original: one return (return picking), type in, 10 items
        self.assertEqual(original_picking.return_count, 1)
        self.assertEqual(original_picking.picking_type_id, self.picking_type_in)
        self.assertEqual(len(original_picking.move_line_ids), 10)

        # Return: one return (exchange picking), type out, 3 item
        self.assertEqual(return_picking.return_count, 1)
        self.assertEqual(return_picking.picking_type_id, self.picking_type_out)
        self.assertEqual(len(return_picking.move_line_ids), 3)
        # By default, the serial IDs picked are the first 3 of the original picking
        # and it should not be possible to create new serial numbers.
        self.assertListEqual(return_picking.move_line_ids.lot_id.ids, original_picking.move_line_ids[:3].lot_id.ids)
        self.assertEqual(return_picking.move_ids.display_assign_serial, False)

        # Exchange: no returns, type in, 3 item
        self.assertEqual(exchange_picking.return_count, 0)
        self.assertEqual(exchange_picking.picking_type_id, self.picking_type_in)
        self.assertEqual(len(exchange_picking.move_line_ids), 3)
        # There should be not pre-selected serial IDs for the exchange picking
        # and it should be possible to create new serial numbers because it's an incoming picking.
        self.assertListEqual(exchange_picking.move_line_ids.lot_id.ids, [])
        self.assertEqual(exchange_picking.move_ids.display_assign_serial, True)

    def test_return_picking_with_different_uom(self):
        """
        Ensure that the return picking uses the same UoM as the original stock move.

        - A product has 'kg' as its default UoM.
        - A stock move is created using 'g' as the UoM with a quantity of 1000 g.
        - A return is initiated for this move.

        Expected behavior:
        - The return picking move should use 'g' as the UoM (same as the original move),
          not the product's default UoM ('kg').
        """
        receipt = self.PickingObj.create({
            'partner_id': self.partner.id,
            'picking_type_id': self.picking_type_in.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'move_ids': [Command.create({
                'product_id': self.kgB.id,
                'product_uom_qty': 1000,
                'uom_id': self.uom_gram.id,
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
            })],
        })
        receipt.action_confirm()
        self.assertEqual(receipt.state, 'assigned')
        receipt.button_validate()
        # create a return picking
        return_picking = receipt._create_return()
        return_picking.move_ids.product_uom_qty = 1000.0
        self.assertEqual(return_picking.move_ids.product_uom.id, self.uom_gram.id)
        self.assertEqual(return_picking.move_ids.product_uom_qty, 1000.0)
        return_picking.button_validate()
        self.assertEqual(return_picking.state, 'done')

    def test_product_quantities_in_return_for_exchange(self):
        """ Ensure that on-hand and forecast quantities are correctly computed
        whe doing an exchange on an incoming picking. """
        original_picking = self.PickingObj.create({
            'picking_type_id': self.picking_type_in.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'move_ids': [(0, 0, {
                'product_id': self.productA.id,
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
                'product_uom_qty': 10,
                'uom_id': self.uom_unit.id,
            })],
        })
        original_picking.button_validate()

        # Product received: both on-hand and forecasted quantities should be 10
        self.assertEqual(self.productA.qty_available, 10)
        self.assertEqual(self.productA.virtual_available, 10)

        return_picking = original_picking._create_return()
        return_picking.move_ids.product_uom_qty = 2
        return_picking.action_confirm()
        return_picking.action_assign()
        return_picking.action_exchange()

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
