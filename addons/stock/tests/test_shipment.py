# -*- coding: utf-8 -*-

from odoo.addons.stock.tests.common2 import TestStockCommon


class TestInventory(TestStockCommon):

    def test_shipment(self):
        # TDE NOTE: this test replaces test/shipment.yml present until saas-10
        # TDE TODO
        # pickign.action_confirm -> confirm moves
        # picking.do_prepare_partial, should create pack ops, write on it ?

        # create and confirm an incoming move of product 3
        incoming_move = self._create_move_in(self.product_3, self.warehouse_1, create_picking=True, product_uom_qty=50)
        incoming_move._action_confirm()

        # receive only 40 units of products; this will create a backorder of incoming shipment for the remaining 10
        pack_operation = self._create_pack_operation(
            self.product_3, 40.0, incoming_move.picking_id,
            location_id=self.env.ref('stock.stock_location_suppliers').id,  # TDE FIXME: locations
            location_dest_id=self.location_1.id)

        incoming_move.picking_id.with_context(active_model='stock.picking', active_id=incoming_move.picking_id.id, active_ids=[incoming_move.picking_id.id]).do_transfer()

        # check backorder shipment after receiving partial shipment and check remaining shipment
        for move_line in incoming_move.picking_id.move_lines:
            self.assertEqual(move_line.product_qty, 40)
            self.assertEqual(move_line.state, 'done')
        backorder = self.env['stock.picking'].search([('backorder_id', '=', incoming_move.picking_id.id)])
        for move_line in backorder.move_lines:
            self.assertEqual(move_line.product_qty, 10)
            self.assertIn(move_line.state, ['assigned', 'waiting', 'confirmed'])

        backorder.with_context(active_model='stock.picking', active_id=backorder.id, active_ids=[backorder.id])

        # receive the remaining 10 units from the backorder
        pack_operation = self._create_pack_operation(
            self.product_3, 10.0, backorder,
            location_id=self.env.ref('stock.stock_location_suppliers').id,  # TDE FIXME: locations
            location_dest_id=self.location_1.id)

        backorder.do_transfer()

        # check the incoming shipment after receipt
        backorder = self.env['stock.picking'].search([('backorder_id', '=', incoming_move.picking_id.id)])
        self.assertEqual(backorder.state, 'done')
        for move_line in backorder.move_lines:
            self.assertEqual(move_line.state, 'done')
