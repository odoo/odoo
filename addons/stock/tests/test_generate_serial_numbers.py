# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests.common import Form, TransactionCase


class StockGenerateCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Product = cls.env['product.product']
        cls.product_serial = Product.create({
            'name': 'Tracked by SN',
            'type': 'product',
            'tracking': 'serial',
        })
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')

        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Base Warehouse',
            'reception_steps': 'one_step',
            'delivery_steps': 'ship_only',
            'code': 'BWH'
        })
        cls.location = cls.env['stock.location'].create({
            'name': 'Room A',
            'location_id': cls.warehouse.lot_stock_id.id,
        })
        cls.location_dest = cls.env['stock.location'].create({
            'name': 'Room B',
            'location_id': cls.warehouse.lot_stock_id.id,
        })

        cls.Wizard = cls.env['stock.assign.serial']


    def _import_lots(self, lots, move):
        location_id = move.location_id
        move_lines_vals = move.split_lots(lots)
        move_lines_commands = move._generate_serial_move_line_commands(move_lines_vals, location_dest_id=location_id)
        move.update({'move_line_ids': move_lines_commands})

    def get_new_move(self, nbre_of_lines=0, product=False):
        product = product or self.product_serial
        move_lines_vals = [Command.create({
                'product_id': product.id,
                'product_uom_id': self.uom_unit.id,
                'quantity': 1,
                'location_id': self.location.id,
                'location_dest_id': self.location_dest.id,
            }) for i in range(nbre_of_lines)]
        return self.env['stock.move'].create({
            'name': 'Move Test',
            'product_id': product.id,
            'product_uom': self.uom_unit.id,
            'location_id': self.location.id,
            'location_dest_id': self.location_dest.id,
            'move_line_ids': move_lines_vals,
        })

    def test_generate_01_sn(self):
        """ Creates a move with 5 move lines, then asks for generates 5 Serial
        Numbers. Checks move has 5 new move lines with each a SN, and the 5
        original move lines are still unchanged.
        """
        nbre_of_lines = 5
        move = self.get_new_move(nbre_of_lines)
        move._do_unreserve()
        form_wizard = Form(self.env['stock.assign.serial'].with_context(
            default_move_id=move.id,
            default_next_serial_number='001',
            default_next_serial_count=nbre_of_lines,
        ))
        wiz = form_wizard.save()
        wiz.generate_serial_numbers()

        # Checks new move lines have the right SN
        generated_numbers = ['001', '002', '003', '004', '005']
        self.assertEqual(len(move.move_line_ids), len(generated_numbers))
        for move_line in move.move_line_ids:
            # For a product tracked by SN, the `quantity` is set on 1 when
            # `lot_name` is set.
            self.assertEqual(move_line.quantity, 1)
            self.assertEqual(move_line.lot_name, generated_numbers.pop(0))

    def test_generate_02_prefix_suffix(self):
        """ Generates some Serial Numbers and checks the prefix and/or suffix
        are correctly used.
        """
        nbre_of_lines = 10
        # Case #1: Prefix, no suffix
        move = self.get_new_move(nbre_of_lines)
        move._do_unreserve()
        form_wizard = Form(self.env['stock.assign.serial'].with_context(
            default_move_id=move.id,
            default_next_serial_number='bilou-87',
            default_next_serial_count=nbre_of_lines,
        ))
        wiz = form_wizard.save()
        wiz.generate_serial_numbers()
        # Checks all move lines have the right SN
        generated_numbers = [
            'bilou-87', 'bilou-88', 'bilou-89', 'bilou-90', 'bilou-91',
            'bilou-92', 'bilou-93', 'bilou-94', 'bilou-95', 'bilou-96'
        ]
        for move_line in move.move_line_ids:
            # For a product tracked by SN, the `quantity` is set on 1 when
            # `lot_name` is set.
            self.assertEqual(move_line.quantity, 1)
            self.assertEqual(
                move_line.lot_name,
                generated_numbers.pop(0)
            )

        # Case #2: No prefix, suffix
        move = self.get_new_move(nbre_of_lines)
        move._do_unreserve()
        form_wizard = Form(self.env['stock.assign.serial'].with_context(
            default_move_id=move.id,
            default_next_serial_number='005-ccc',
            default_next_serial_count=nbre_of_lines,
        ))
        wiz = form_wizard.save()
        wiz.generate_serial_numbers()
        # Checks all move lines have the right SN
        generated_numbers = [
            '005-ccc', '006-ccc', '007-ccc', '008-ccc', '009-ccc',
            '010-ccc', '011-ccc', '012-ccc', '013-ccc', '014-ccc'
        ]
        for move_line in move.move_line_ids:
            # For a product tracked by SN, the `quantity` is set on 1 when
            # `lot_name` is set.
            self.assertEqual(move_line.quantity, 1)
            self.assertEqual(
                move_line.lot_name,
                generated_numbers.pop(0)
            )

        # Case #3: Prefix + suffix
        move = self.get_new_move(nbre_of_lines)
        form_wizard = Form(self.env['stock.assign.serial'].with_context(
            default_move_id=move.id,
            default_next_serial_number='alpha-012-345-beta',
            default_next_serial_count=nbre_of_lines,
        ))
        wiz = form_wizard.save()
        wiz.generate_serial_numbers()
        # Checks all move lines have the right SN
        generated_numbers = [
            'alpha-012-345-beta', 'alpha-012-346-beta', 'alpha-012-347-beta',
            'alpha-012-348-beta', 'alpha-012-349-beta', 'alpha-012-350-beta',
            'alpha-012-351-beta', 'alpha-012-352-beta', 'alpha-012-353-beta',
            'alpha-012-354-beta'
        ]
        for move_line in move.move_line_ids:
            # For a product tracked by SN, the `quantity` is set on 1 when
            # `lot_name` is set.
            self.assertEqual(move_line.quantity, 1)
            self.assertEqual(
                move_line.lot_name,
                generated_numbers.pop(0)
            )

        # Case #4: Prefix + suffix, identical number pattern
        move = self.get_new_move(nbre_of_lines)
        form_wizard = Form(self.env['stock.assign.serial'].with_context(
            default_move_id=move.id,
            default_next_serial_number='BAV023B00001S00001',
            default_next_serial_count=nbre_of_lines,
        ))
        wiz = form_wizard.save()
        wiz.generate_serial_numbers()
        # Checks all move lines have the right SN
        generated_numbers = [
            'BAV023B00001S00001', 'BAV023B00001S00002', 'BAV023B00001S00003',
            'BAV023B00001S00004', 'BAV023B00001S00005', 'BAV023B00001S00006',
            'BAV023B00001S00007', 'BAV023B00001S00008', 'BAV023B00001S00009',
            'BAV023B00001S00010'
        ]
        for move_line in move.move_line_ids:
            # For a product tracked by SN, the `quantity` is set on 1 when
            # `lot_name` is set.
            self.assertEqual(move_line.quantity, 1)
            self.assertEqual(
                move_line.lot_name,
                generated_numbers.pop(0)
            )

    def test_generate_03_raise_exception(self):
        """ Tries to generate some SN but with invalid initial number.
        """
        move = self.get_new_move(3)
        form_wizard = Form(self.env['stock.assign.serial'].with_context(
            default_move_id=move.id,
            default_next_serial_number='code-xxx',
        ))

        form_wizard.next_serial_count = 0
        # Must raise an exception because `next_serial_count` must be greater than 0.
        with self.assertRaises(ValidationError):
            form_wizard.save()

        form_wizard.next_serial_count = 3
        wiz = form_wizard.save()
        wiz.generate_serial_numbers()
        self.assertEqual(move.move_line_ids.mapped('lot_name'), ["code-xxx0", "code-xxx1", "code-xxx2"])

    def test_generate_04_generate_in_multiple_time(self):
        """ Generates a Serial Number for each move lines (except the last one)
        but with multiple assignments, and checks the generated Serial Numbers
        are what we expect.
        """
        nbre_of_lines = 10
        move = self.get_new_move(nbre_of_lines)
        move._do_unreserve()
        form_wizard = Form(self.env['stock.assign.serial'].with_context(
            default_move_id=move.id,
        ))
        # First assignment
        form_wizard.next_serial_count = 3
        form_wizard.next_serial_number = '001'
        wiz = form_wizard.save()
        wiz.generate_serial_numbers()
        # Second assignment
        form_wizard.next_serial_count = 2
        form_wizard.next_serial_number = 'bilou-64'
        wiz = form_wizard.save()
        wiz.generate_serial_numbers()
        # Third assignment
        form_wizard.next_serial_count = 4
        form_wizard.next_serial_number = 'ro-1337-bot'
        wiz = form_wizard.save()
        wiz.generate_serial_numbers()

        # Checks all move lines have the right SN
        generated_numbers = [
            # Correspond to the first assignment
            '001', '002', '003',
            # Correspond to the second assignment
            'bilou-64', 'bilou-65',
            # Correspond to the third assignment
            'ro-1337-bot', 'ro-1338-bot', 'ro-1339-bot', 'ro-1340-bot',
        ]
        self.assertEqual(len(move.move_line_ids), len(generated_numbers))
        for move_line in move.move_line_ids:
            self.assertEqual(move_line.quantity, 1)
            self.assertEqual(move_line.lot_name, generated_numbers.pop(0))
        for move_line in (move.move_line_ids - move.move_line_ids):
            self.assertEqual(move_line.quantity, 0)
            self.assertEqual(move_line.lot_name, False)

    def test_generate_with_putaway(self):
        """ Checks the `location_dest_id` of generated move lines is correclty
        set in fonction of defined putaway rules.
        """
        nbre_of_lines = 4
        shelf_location = self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.location_dest.id,
        })

        # Checks a first time without putaway...
        move = self.get_new_move(nbre_of_lines)
        form_wizard = Form(self.env['stock.assign.serial'].with_context(
            default_move_id=move.id,
        ))
        form_wizard.next_serial_count = nbre_of_lines
        form_wizard.next_serial_number = '001'
        wiz = form_wizard.save()
        wiz.generate_serial_numbers()

        for move_line in move.move_line_ids:
            self.assertEqual(move_line.quantity, 1)
            # The location dest must be the default one.
            self.assertEqual(move_line.location_dest_id.id, self.location_dest.id)

        # We need to activate multi-locations to use putaway rules.
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id)]})
        # Creates a putaway rule
        self.env['stock.putaway.rule'].create({
            'product_id': self.product_serial.id,
            'location_in_id': self.location_dest.id,
            'location_out_id': shelf_location.id,
        })

        # Checks now with putaway...
        move = self.get_new_move(nbre_of_lines)
        move._do_unreserve()
        form_wizard = Form(self.env['stock.assign.serial'].with_context(
            default_move_id=move.id,
        ))
        form_wizard.next_serial_count = nbre_of_lines
        form_wizard.next_serial_number = '001'
        wiz = form_wizard.save()
        wiz.generate_serial_numbers()

        for move_line in move.move_line_ids:
            self.assertEqual(move_line.quantity, 1)
            # The location dest must be now the one from the putaway.
            self.assertEqual(move_line.location_dest_id.id, shelf_location.id)

    def test_generate_with_putaway_02(self):
        """
        Suppose a tracked-by-USN product P
        Sub locations in WH/Stock + Storage Category
        The Storage Category adds a capacity constraint (max 1 x P / Location)
        - Plan a receipt with 2 x P
        - Receive 4 x P
        -> The test ensures that the destination locations are correct
        """
        stock_location = self.warehouse.lot_stock_id
        self.env.user.write({'groups_id': [(4, self.env.ref('stock.group_stock_storage_categories').id)]})
        self.env.user.write({'groups_id': [(4, self.env.ref('stock.group_stock_multi_locations').id)]})

        # max 1 x product_serial
        stor_category = self.env['stock.storage.category'].create({
            'name': 'Super Storage Category',
            'product_capacity_ids': [(0, 0, {
                'product_id': self.product_serial.id,
                'quantity': 1,
            })]
        })

        # 5 sub locations with the storage category
        # (the last one should never be used)
        sub_loc_01, sub_loc_02, sub_loc_03, sub_loc_04, dummy = self.env['stock.location'].create([{
            'name': 'Sub Location %s' % i,
            'usage': 'internal',
            'location_id': stock_location.id,
            'storage_category_id': stor_category.id,
        } for i in [1, 2, 3, 4, 5]])

        self.env['stock.putaway.rule'].create({
            'location_in_id': stock_location.id,
            'location_out_id': stock_location.id,
            'product_id': self.product_serial.id,
            'storage_category_id': stor_category.id,
        })

        # Receive 1 x P
        receipt_picking = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.in_type_id.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': stock_location.id,
            'state': 'draft',
        })
        move = self.env['stock.move'].create({
            'name': self.product_serial.name,
            'product_id': self.product_serial.id,
            'product_uom': self.product_serial.uom_id.id,
            'product_uom_qty': 2.0,
            'picking_id': receipt_picking.id,
            'location_id': receipt_picking.location_id.id,
            'location_dest_id': receipt_picking.location_dest_id.id,
        })
        receipt_picking.action_confirm()

        self.assertEqual(move.move_line_ids[0].location_dest_id, sub_loc_01)
        self.assertEqual(move.move_line_ids[1].location_dest_id, sub_loc_02)

        form_wizard = Form(self.env['stock.assign.serial'].with_context(
            default_move_id=move.id,
            default_next_serial_number='001',
            default_next_serial_count=4,
        ))
        wiz = form_wizard.save()
        wiz.generate_serial_numbers()

        self.assertRecordValues(move.move_line_ids, [
            {'quantity': 1, 'lot_name': '001', 'location_dest_id': sub_loc_01.id},
            {'quantity': 1, 'lot_name': '002', 'location_dest_id': sub_loc_02.id},
            {'quantity': 1, 'lot_name': '003', 'location_dest_id': sub_loc_03.id},
            {'quantity': 1, 'lot_name': '004', 'location_dest_id': sub_loc_04.id},
        ])

    def test_import_lots(self):
        product_lot = self.env['product.product'].create({
            'name': 'Tracked by Lots',
            'type': 'product',
            'tracking': 'lot',
        })
        lot_id = self.env['stock.lot'].create({
            'product_id': product_lot.id,
            'name': 'abc',
        })
        self.warehouse.in_type_id.use_existing_lots = True
        receipt_picking = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.in_type_id.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
            'state': 'draft',
        })
        move = self.env['stock.move'].create({
            'name': product_lot.name,
            'product_id': product_lot.id,
            'product_uom': product_lot.uom_id.id,
            'product_uom_qty': 5.0,
            'picking_id': receipt_picking.id,
            'location_id': receipt_picking.location_id.id,
            'location_dest_id': receipt_picking.location_dest_id.id,
        })
        self._import_lots("abc;4\ndef", move)
        self.assertIn(lot_id, move.move_line_ids.lot_id)
        self.assertRecordValues(move.move_line_ids, [
            {'quantity': 4, 'lot_name': 'abc'},
            {'quantity': 1, 'lot_name': 'def'},
        ])
