# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.tests.common import SavepointCase


class StockGenerate(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(StockGenerate, cls).setUpClass()
        Product = cls.env['product.product']
        cls.product_serial = Product.create({
            'name': 'Tracked by SN',
            'type': 'product',
            'tracking': 'serial',
        })
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')

        warehouse = cls.env['stock.warehouse'].create({
            'name': 'Base Warehouse',
            'reception_steps': 'one_step',
            'delivery_steps': 'ship_only',
            'code': 'BWH'
        })
        cls.location = cls.env['stock.location'].create({
            'name': 'Room A',
            'location_id': warehouse.lot_stock_id.id,
        })
        cls.location_dest = cls.env['stock.location'].create({
            'name': 'Room B',
            'location_id': warehouse.lot_stock_id.id,
        })

        cls.Wizard = cls.env['stock.assign.serial']

    def get_new_move(self, nbre_of_lines):
        move_lines_val = []
        for i in range(nbre_of_lines):
            move_lines_val.append({
                'product_id': self.product_serial.id,
                'product_uom_id': self.uom_unit.id,
                'location_id': self.location.id,
                'location_dest_id': self.location_dest.id
            })
        return self.env['stock.move'].create({
            'name': 'Move Test',
            'product_id': self.product_serial.id,
            'product_uom': self.uom_unit.id,
            'location_id': self.location.id,
            'location_dest_id': self.location_dest.id,
            'move_line_ids': [(0, 0, line_vals) for line_vals in move_lines_val]
        })

    def test_generate_01_sn(self):
        """ Generates a Serial Number for each move lines and checks the
        generated Serial Numbers are what we expect.
        """
        nbre_of_lines = 5
        move = self.get_new_move(nbre_of_lines)

        wiz = self.Wizard.create({
            'move_id': move.id,
            'next_serial_number': '001',
        })
        for i in range(nbre_of_lines):
            self.assertEqual(move.move_line_ids[i].qty_done, 0)
        wiz.generate_serial_numbers()
        # Checks all move lines have the right SN
        generated_numbers = ['001', '002', '003', '004', '005']
        for i in range(nbre_of_lines):
            # For a product tracked by SN, the `qty_done` is set on 1 when
            # `lot_name` is set.
            self.assertEqual(move.move_line_ids[i].qty_done, 1)
            self.assertEqual(
                move.move_line_ids[i].lot_name,
                generated_numbers[i])

    def test_generate_02_prefix_suffix(self):
        """ Generates some Serial Numbers and checks the prefix and/or suffix
        are correctly used.
        """
        nbre_of_lines = 10
        # Case #1: Prefix, no suffix
        move = self.get_new_move(nbre_of_lines)
        wiz = self.Wizard.create({
            'move_id': move.id,
            'next_serial_number': 'bilou-87',
        })
        wiz.generate_serial_numbers()
        # Checks all move lines have the right SN
        generated_numbers = [
            'bilou-87', 'bilou-88', 'bilou-89', 'bilou-90', 'bilou-91',
            'bilou-92', 'bilou-93', 'bilou-94', 'bilou-95', 'bilou-96'
        ]
        for i in range(nbre_of_lines):
            # For a product tracked by SN, the `qty_done` is set on 1 when
            # `lot_name` is set.
            self.assertEqual(move.move_line_ids[i].qty_done, 1)
            self.assertEqual(
                move.move_line_ids[i].lot_name,
                generated_numbers[i])

        # Case #2: No prefix, suffix
        move = self.get_new_move(nbre_of_lines)
        wiz = self.Wizard.create({
            'move_id': move.id,
            'next_serial_number': '005-ccc',
        })
        wiz.generate_serial_numbers()
        # Checks all move lines have the right SN
        generated_numbers = [
            '005-ccc', '006-ccc', '007-ccc', '008-ccc', '009-ccc',
            '010-ccc', '011-ccc', '012-ccc', '013-ccc', '014-ccc'
        ]
        for i in range(nbre_of_lines):
            # For a product tracked by SN, the `qty_done` is set on 1 when
            # `lot_name` is set.
            self.assertEqual(move.move_line_ids[i].qty_done, 1)
            self.assertEqual(
                move.move_line_ids[i].lot_name,
                generated_numbers[i])

        # Case #2: Prefix + suffix
        move = self.get_new_move(nbre_of_lines)
        wiz = self.Wizard.create({
            'move_id': move.id,
            'next_serial_number': 'alpha-012-345-beta',
        })
        wiz.generate_serial_numbers()
        # Checks all move lines have the right SN
        generated_numbers = [
            'alpha-012-345-beta', 'alpha-013-345-beta', 'alpha-014-345-beta',
            'alpha-015-345-beta', 'alpha-016-345-beta', 'alpha-017-345-beta',
            'alpha-018-345-beta', 'alpha-019-345-beta', 'alpha-020-345-beta',
            'alpha-021-345-beta'
        ]
        for i in range(nbre_of_lines):
            # For a product tracked by SN, the `qty_done` is set on 1 when
            # `lot_name` is set.
            self.assertEqual(move.move_line_ids[i].qty_done, 1)
            self.assertEqual(
                move.move_line_ids[i].lot_name,
                generated_numbers[i])

    def test_generate_03_raise_exception(self):
        """ Tries to generate some SN but with invalid initial number.
        """
        move = self.get_new_move(3)
        wiz = self.Wizard.create({
            'move_id': move.id,
            'next_serial_number': 'code-xxx',
        })
        with self.assertRaises(UserError):
            wiz.generate_serial_numbers()
