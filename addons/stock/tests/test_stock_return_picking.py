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
        move_1.quantity_done = 2
        move_2.quantity_done = 1
        picking_out.button_validate()
        return_wizard = StockReturnObj.with_context(active_id=picking_out.id, active_ids=picking_out.ids).create({
            'location_id': self.stock_location,
            'picking_id': picking_out.id,
        })
        return_wizard._onchange_picking_id()

        ReturnPickingLineObj = self.env['stock.return.picking.line']
        # Check return line of uom_unit move
        return_line = ReturnPickingLineObj.search([('move_id', '=', move_1.id), ('wizard_id.picking_id', '=', picking_out.id)], limit=1)
        self.assertEqual(return_line.product_id.id, self.UnitA.id, 'Return line should have exact same product as outgoing move')
        self.assertEqual(return_line.uom_id.id, self.uom_unit.id, 'Return line should have exact same uom as product uom')
        # Check return line of uom_dozen move
        return_line = ReturnPickingLineObj.search([('move_id', '=', move_2.id), ('wizard_id.picking_id', '=', picking_out.id)], limit=1)
        self.assertEqual(return_line.product_id.id, self.UnitA.id, 'Return line should have exact same product as outgoing move')
        self.assertEqual(return_line.uom_id.id, self.uom_unit.id, 'Return line should have exact same uom as product uom')
