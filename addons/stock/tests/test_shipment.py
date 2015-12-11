# -*- coding: utf-8 -*-

from openerp.tests.common import TransactionCase

class TestShipment(TransactionCase):
    def test_shipment(self):
        UserObj = self.env['res.users']
        StockPackOpraObj = self.env['stock.pack.operation']
        PickingObj = self.env['stock.picking']

        res_users_stock_manager = UserObj.create({
            'company_id': self.env.ref('base.main_company').id,
            'name': 'Stock Manager',
            'login': 'sam',
            'email': 'stockmanager@yourcompany.com',
            'groups_id': [(4, self.env.ref('stock.group_stock_manager').id)]
            })
        self.env.uid = res_users_stock_manager.id

        incoming_move = self.env.ref("stock.incomming_shipment_icecream")
        incoming_move.action_confirm()

        pick = self.env.ref('stock.incomming_shipment')
        StockPackOpraObj.create({
            'picking_id': pick.id,
            'product_id': self.env.ref('stock.product_icecream').id,
            'product_uom_id': self.env.ref('product.product_uom_kgm').id,
            'product_qty': 40,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.env.ref('stock.stock_location_14').id
        })
        pick.with_context({'active_model': 'stock.picking', 'active_id': self.env.ref('stock.incomming_shipment').id, 'active_ids': [self.env.ref('stock.incomming_shipment').id]}).do_transfer()

        backorder = PickingObj.search([('backorder_id', '=', self.env.ref("stock.incomming_shipment").id)])[0]
        StockPackOpraObj.create({
            'picking_id': backorder.id,
            'product_id': self.env.ref('stock.product_icecream').id,
            'product_uom_id': self.env.ref('product.product_uom_kgm').id,
            'product_qty': 10,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.env.ref('stock.stock_location_14').id
        })
        backorder.do_transfer()

        shipment = PickingObj.search([('backorder_id', '=', self.env.ref("stock.incomming_shipment").id)])[0]
        self.assertEqual(shipment.state, 'done', "shipment should be close after received.")
        for move_line in shipment.move_lines:
            self.assertEqual(move_line.state, 'done', "Move line should be closed.")
