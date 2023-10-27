# -*- coding: utf-8 -*-

from odoo.addons.stock.tests.common import TestStockCommon

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
        return_picking = StockReturnObj.with_context(active_id=picking_out.id, active_ids=picking_out.ids).create({
            'location_id': self.stock_location,
            'picking_id': picking_out.id,
        })
        return_picking._compute_moves_locations()

        ReturnPickingLineObj = self.env['stock.return.picking.line']
        # Check return line of uom_unit move
        return_line = ReturnPickingLineObj.search([('move_id', '=', move_1.id), ('wizard_id.picking_id', '=', picking_out.id)], limit=1)
        self.assertEqual(return_line.product_id.id, self.UnitA.id, 'Return line should have exact same product as outgoing move')
        self.assertEqual(return_line.uom_id.id, self.uom_unit.id, 'Return line should have exact same uom as product uom')
        # Check return line of uom_dozen move
        return_line = ReturnPickingLineObj.search([('move_id', '=', move_2.id), ('wizard_id.picking_id', '=', picking_out.id)], limit=1)
        self.assertEqual(return_line.product_id.id, self.UnitA.id, 'Return line should have exact same product as outgoing move')
        self.assertEqual(return_line.uom_id.id, self.uom_unit.id, 'Return line should have exact same uom as product uom')

    def test_return_picking_SN_pack(self):
        """
            Test returns of pickings with serial tracked products put in packs
        """
        wh_stock = self.env['stock.location'].browse(self.stock_location)
        customer_location = self.env['stock.location'].browse(self.customer_location)

        product_serial = self.env['product.product'].create({
            'name': 'Tracked by SN',
            'type': 'product',
            'tracking': 'serial',
        })
        serial1 = self.env['stock.lot'].create({
            'name': 'serial1',
            'product_id': product_serial.id,
            'company_id': self.env.company.id,
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

        return_wizard = self.env['stock.return.picking'].with_context(active_id=picking.id, active_ids=picking.ids).create({
            'location_id': picking.location_id.id,
            'picking_id': picking.id,
        })
        return_wizard._compute_moves_locations()
        res = return_wizard.create_returns()
        picking2 = self.PickingObj.browse(res["res_id"])

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

        # Setup default location
        return_location = self.env['stock.location'].create({
            'name': 'return internal',
            'usage': 'internal',
            'return_location' : True
        })
        delivery_picking.picking_type_id.default_location_return_id = return_location

        # Create return
        return_wizard = self.env['stock.return.picking'].with_context(active_id=delivery_picking.id, active_model='stock.picking').create({})
        res = return_wizard.create_returns()
        return_picking = self.PickingObj.browse(res["res_id"])
        self.assertEqual(return_picking.location_dest_id, return_location)
