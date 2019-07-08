# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.tests.common import Form, SavepointCase


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

    def test_set_multiple_lot_name_01(self):
        """ Sets five SN in one time in stock move view form, then checks five
        first move lines have the right `lot_name`.
        """
        move = self.get_new_move(10)
        # We must begin with a move with 10 move lines.
        self.assertEqual(len(move.move_line_ids), 10)

        value_list = [
            'abc-235',
            'abc-237',
            'abc-238',
            'abc-282',
            'abc-301',
        ]
        values = '\n'.join(value_list)

        move_form = Form(move, view='stock.view_stock_move_operations')
        with move_form.move_line_ids.edit(0) as line:
            line.lot_name = values
        move = move_form.save()

        # After we set multiple SN, we must still have 10 move lines.
        self.assertEqual(len(move.move_line_ids), 10)
        # Then we look each SN name is correct.
        for i in range(10):
            value = False
            if i < len(value_list):
                value = value_list[i]
            self.assertEqual(
                move.move_line_ids[i].lot_name,
                value
            )

    def test_set_multiple_lot_name_02(self):
        """ Sets five SN in one time in a stock move with only one move line,
        then checks additionnal move lines have been create and have each the
        correct SN.
        """
        move = self.get_new_move(1)
        # We must begin with a move with only one move line
        self.assertEqual(len(move.move_line_ids), 1)

        value_list = [
            'abc-235',
            'abc-237',
            'abc-238',
            'abc-282',
            'abc-301',
        ]
        values = '\n'.join(value_list)

        move_form = Form(move, view='stock.view_stock_move_operations')
        with move_form.move_line_ids.edit(0) as line:
            line.lot_name = values
        move = move_form.save()

        # After we set multiple SN, we must have a line for each value.
        self.assertEqual(len(move.move_line_ids), len(value_list))
        # Then we look each SN name is correct.
        for (move_line, line) in zip(move.move_line_ids, value_list):
            self.assertEqual(move_line.lot_name, line)

    def test_set_multiple_lot_name_03_empty_values(self):
        """ Sets multiple values with some empty lines in one time, then checks
        we haven't create useless move line and all move line's `lot_name` have
        been correctly set.
        """
        move = self.get_new_move(5)
        # We must begin with a move with five move lines.
        self.assertEqual(len(move.move_line_ids), 5)

        value_list = [
            '',
            'abc-235',
            '',
            'abc-237',
            '',
            '',
            'abc-238',
            'abc-282',
            'abc-301',
            '',
        ]
        values = '\n'.join(value_list)

        # Checks we have more values than move lines.
        self.assertTrue(len(move.move_line_ids) < len(value_list))
        move_form = Form(move, view='stock.view_stock_move_operations')
        with move_form.move_line_ids.edit(0) as line:
            line.lot_name = values
        move = move_form.save()

        filtered_value_list = list(filter(lambda line: len(line), value_list))
        # After we set multiple SN, we must have a line for each value.
        self.assertEqual(len(move.move_line_ids), len(filtered_value_list))
        # Then we look each SN name is correct.
        for (move_line, line) in zip(move.move_line_ids, filtered_value_list):
            self.assertEqual(move_line.lot_name, line)
