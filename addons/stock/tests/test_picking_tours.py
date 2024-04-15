# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
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
        self.assertEqual(self.receipt.move_ids.quantity, 4)
        lot = self.env['stock.lot'].search([
            ('name', '=', 'lot1'),
            ('product_id', '=', product_lot.id),
        ])
        self.assertEqual(len(lot), 1)
        self.assertEqual(lot.product_qty, 4)

    def test_generate_serial_1(self):
        """generate some serial numbers in the detailed operation modal"""
        product_serial = self.env['product.product'].create({
            'name': 'Product Serial',
            'type': 'product',
            'tracking': 'serial',
        })
        url = self._get_picking_url(self.receipt.id)

        self.start_tour(url, 'test_generate_serial_1', login='admin', timeout=60)
        self.assertEqual(self.receipt.state, 'done')
        self.assertEqual(self.receipt.move_ids.product_uom_qty, 0)
        self.assertEqual(self.receipt.move_ids.quantity, 5)
        self.assertEqual(len(self.receipt.move_ids.move_line_ids), 5)

        serial = self.env['stock.lot'].search([
            ('name', 'ilike', 'serial_n_%'),
            ('product_id', '=', product_serial.id),
        ])
        self.assertEqual(len(serial), 5)

    def test_generate_serial_2(self):
        """ Generate lot numbers in the detailed operation modal """
        product_lot_1 = self.env['product.product'].create({
            'name': 'Product Lot 1',
            'type': 'product',
            'tracking': 'lot',
        })
        url = self._get_picking_url(self.receipt.id)
        self.start_tour(url, 'test_generate_serial_2', login='admin', timeout=60)
        self.assertEqual(self.receipt.state, 'done')
        self.assertEqual(self.receipt.move_ids.product_uom_qty, 100)
        self.assertEqual(self.receipt.move_ids.quantity, 100)
        self.assertEqual(len(self.receipt.move_ids.move_line_ids), 11)

        lots_batch_1 = self.env['stock.lot'].search([
            ('name', 'ilike', 'lot_n_1_%'),
            ('product_id', '=', product_lot_1.id)
        ], order='name asc')
        lots_batch_2 = self.env['stock.lot'].search([
            ('name', 'ilike', 'lot_n_2_%'),
            ('product_id', '=', product_lot_1.id)
        ], order='name asc')
        self.assertEqual(len(lots_batch_1), 7)
        self.assertEqual(lots_batch_1[-1].product_qty, 5)
        self.assertEqual(len(lots_batch_2), 4)
        self.assertEqual(lots_batch_2[-1].product_qty, 11)

    def test_inventory_adjustment_apply_all(self):
        """
        Checks if the "Apply All" button works for all new entries, even if
        it was pressed immediately after entering the last entry's quantity
        (without clicking on anything else)
        """
        self.env['product.product'].create([
            {'name': 'Product 1', 'type': 'product'},
            {'name': 'Product 2', 'type': 'product'},
        ])

        menu = self.env.ref('stock.menu_action_inventory_tree')
        url = '/web#menu_id=%s&model=stock.quant&view_type=list' % (menu['id'])

        # We need a bigger window, so the "Apply All" button is immediately visible
        self.browser_size = '1920,1080'
        self.start_tour(url, 'test_inventory_adjustment_apply_all', login='admin', timeout=60)

    def test_add_new_line(self):
        product_one, _ = self.env["product.product"].create([
            {
                'name': 'Product one',
                'type': 'product',
                'tracking': 'serial',
            },
            {
                'name': 'Product two',
                'type': 'product',
                'tracking': 'serial',
            }
        ])

        self.receipt.write({
            "move_ids": [Command.create({
                "name": "test",
                "product_uom_qty": 1,
                "product_id": product_one.id,
                "location_id": self.receipt.location_id.id,
                "location_dest_id": self.receipt.location_dest_id.id,
            })]
        })

        self.receipt.action_confirm()
        self.receipt.move_ids.move_line_ids.lot_name = "one"

        url = self._get_picking_url(self.receipt.id)
        self.start_tour(url, 'test_add_new_line', login='admin', timeout=60)

        names = self.receipt.move_ids.move_line_ids.mapped('lot_name')
        self.assertEqual(names, ["two", "one"])

    def test_edit_existing_line(self):
        self.uom_unit = self.env.ref('uom.product_uom_unit')
        product_one = self.env['product.product'].create({
            'name': 'Product one',
            'type': 'product',
            'tracking': 'serial',
        })

        self.receipt.write({
            "move_ids": [Command.create({
                "name": "test",
                "product_id": product_one.id,
                "location_id": self.receipt.location_id.id,
                "location_dest_id": self.receipt.location_dest_id.id,
                "product_uom_qty": 1,
            })]
        })

        self.receipt.action_confirm()
        self.receipt.move_ids.move_line_ids.lot_name = "one"

        url = self._get_picking_url(self.receipt.id)
        self.start_tour(url, 'test_edit_existing_line', login='admin', timeout=60)

        names = self.receipt.move_ids.move_line_ids.mapped('lot_name')
        self.assertEqual(names, ["one", "two"])
