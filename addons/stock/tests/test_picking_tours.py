# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestStockPickingTour(HttpCase):
    def setUp(self):
        self.receipt = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.env.ref('stock.stock_location_stock').id,
        })

        return super().setUp()

    def _get_picking_url(self, picking_id):
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_incoming")
        return '/web#action=%s&id=%s&model=stock.picking&view_type=form' % (action['id'], picking_id)

    def test_detailed_op_no_save_1(self):
        """validate a receipt with some move without any save except the last one"""
        product_lot = self.env['product.product'].create({
            'name': 'Product Lot',
            'type': 'product',
            'tracking': 'lot',
        })
        url = self._get_picking_url(self.receipt.id)

        self.start_tour(url, 'test_detailed_op_no_save_1', login='admin', timeout=60)
        self.assertEqual(self.receipt.state, 'done')
        self.assertEqual(self.receipt.move_ids.product_uom_qty, 0)
        self.assertEqual(self.receipt.move_ids.quantity_done, 4)
        lot = self.env['stock.lot'].search([
            ('name', '=', 'lot1'),
            ('product_id', '=', product_lot.id),
        ])
        self.assertEqual(len(lot), 1)
        self.assertEqual(lot.product_qty, 4)
