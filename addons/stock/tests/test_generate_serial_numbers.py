# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, new_test_user


class StockGenerateCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref('base.group_user').write({'implied_ids': [(4, cls.env.ref('stock.group_production_lot').id)]})
        Product = cls.env['product.product']
        cls.product_serial = Product.create({
            'name': 'Tracked by SN',
            'is_storable': True,
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
            'product_id': product.id,
            'product_uom': self.uom_unit.id,
            'location_id': self.location.id,
            'location_dest_id': self.location_dest.id,
            'move_line_ids': move_lines_vals,
        })

    def assert_move_line_vals_values(self, line_vals_list, checked_vals_list):
        self.assertEqual(len(line_vals_list), len(checked_vals_list))
        for (line_vals, checked_vals) in zip(line_vals_list, checked_vals_list):
            for checked_field in checked_vals:
                self.assertEqual(line_vals[checked_field], checked_vals[checked_field])

    def test_generate_01_sn(self):
        """ Creates a move with 5 move lines, then asks for generates 5 Serial
        Numbers. Checks move has 5 new move lines with each a SN, and the 5
        original move lines are still unchanged.
        """
        nbre_of_lines = 5
        move = self.get_new_move(nbre_of_lines)
        move._do_unreserve()
        move._generate_serial_numbers('001', nbre_of_lines)

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
        move._generate_serial_numbers('bilou-87', nbre_of_lines)
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
        move._generate_serial_numbers('005-ccc', nbre_of_lines)
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
        move._generate_serial_numbers('alpha-012-345-beta', nbre_of_lines)
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
        move._generate_serial_numbers('BAV023B00001S00001', nbre_of_lines)
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
        # Must raise an exception because `next_serial_count` must be greater than 0.
        with self.assertRaises(ValidationError):
            move._generate_serial_numbers('code-xxx', 0)

        move._generate_serial_numbers('code-xxx', 3)
        self.assertEqual(move.move_line_ids.mapped('lot_name'), ["code-xxx0", "code-xxx1", "code-xxx2"])

    def test_generate_04_generate_in_multiple_time(self):
        """ Generates a Serial Number for each move lines (except the last one)
        but with multiple assignments, and checks the generated Serial Numbers
        are what we expect.
        """
        nbre_of_lines = 10
        move = self.get_new_move(nbre_of_lines)
        move._do_unreserve()
        move._generate_serial_numbers('001', 3)
        # Second assignment
        move._generate_serial_numbers('bilou-64', 2)
        # Third assignment
        move._generate_serial_numbers('ro-1337-bot', 4)

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
        move._generate_serial_numbers('001', nbre_of_lines)

        for move_line in move.move_line_ids:
            self.assertEqual(move_line.quantity, 1)
            # The location dest must be the default one.
            self.assertEqual(move_line.location_dest_id.id, self.location_dest.id)

        # We need to activate multi-locations to use putaway rules.
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'group_ids': [(4, grp_multi_loc.id)]})
        # Creates a putaway rule
        self.env['stock.putaway.rule'].create({
            'product_id': self.product_serial.id,
            'location_in_id': self.location_dest.id,
            'location_out_id': shelf_location.id,
        })

        # Checks now with putaway...
        move = self.get_new_move(nbre_of_lines)
        move._do_unreserve()
        move._generate_serial_numbers('001', nbre_of_lines)

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
        self.env.user.write({'group_ids': [(4, self.env.ref('stock.group_stock_multi_locations').id)]})

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
            'sublocation': 'closest_location',
        })

        # Receive 1 x P
        receipt_picking = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.in_type_id.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': stock_location.id,
            'state': 'draft',
        })
        move = self.env['stock.move'].create({
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

        move._generate_serial_numbers('001', 4)

        self.assertRecordValues(move.move_line_ids, [
            {'quantity': 1, 'lot_name': '001', 'location_dest_id': sub_loc_01.id},
            {'quantity': 1, 'lot_name': '002', 'location_dest_id': sub_loc_02.id},
            {'quantity': 1, 'lot_name': '003', 'location_dest_id': sub_loc_03.id},
            {'quantity': 1, 'lot_name': '004', 'location_dest_id': sub_loc_04.id},
        ])

    def test_receipt_import_lots(self):
        """ This test ensure that with use_existing_lots is True on the picking type, the 'Import Serial/lots'
        action generate new lots or use existing lots that are available.
        It also tests that lot_id is set instead of lot_name so that the frontend correctly
        shows the lots in the lot column.
        """
        product_lot = self.env['product.product'].create({
            'name': 'Tracked by Lots',
            'is_storable': True,
            'tracking': 'lot',
        })
        abc_lot_id = self.env['stock.lot'].create({
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
        self.env['stock.move'].create({
            'product_id': product_lot.id,
            'product_uom': product_lot.uom_id.id,
            'product_uom_qty': 5.0,
            'picking_id': receipt_picking.id,
            'location_id': receipt_picking.location_id.id,
            'location_dest_id': receipt_picking.location_dest_id.id,
        })
        action_context = {
            'default_company_id': self.env.company.id,
            'default_picking_id': receipt_picking.id,
            'default_picking_type_id': self.warehouse.in_type_id.id,
            'default_location_id': receipt_picking.location_id.id,
            'default_location_dest_id': receipt_picking.location_dest_id.id,
            'default_product_id': product_lot.id,
            'default_tracking': 'lot',
        }
        move_line_vals = self.env['stock.move'].action_generate_lot_line_vals(
            action_context, 'import', None, 0, 'abc;4\ndef'
        )
        def_lot_id = self.env['stock.lot'].search([('name', '=', 'def'), ('product_id', '=', product_lot.id)])
        self.assert_move_line_vals_values(move_line_vals, [
            {'quantity': 4, 'lot_id': {'id': abc_lot_id.id, 'display_name': 'abc'}},
            {'quantity': 1, 'lot_id': {'id': def_lot_id.id, 'display_name': 'def'}},
        ])

    def test_receipt_generate_serial_numbers(self):
        """ This test ensures that with use_existing_lots is True on the picking type, the 'Generate Serial/Lots'
        action and 'Assign Serial Numbers' action generate new serials and use existing serials that are available.
        It also tests that lot_id is set instead of lot_name so that the frontend correctly
        shows the lots in the lot column.
        """
        product_lot = self.env['product.product'].create({
            'name': 'Tracked by Lots',
            'is_storable': True,
            'tracking': 'serial',
        })
        sn_t1_01 = self.env['stock.lot'].create({'product_id': product_lot.id, 'name': 'sn-t1-01'})
        sn_t1_02 = self.env['stock.lot'].create({'product_id': product_lot.id, 'name': 'sn-t1-02'})

        self.warehouse.in_type_id.use_existing_lots = True
        receipt_picking = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.in_type_id.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
            'state': 'draft',
        })
        move = self.env['stock.move'].create({
            'product_id': product_lot.id,
            'product_uom': product_lot.uom_id.id,
            'product_uom_qty': 5.0,
            'picking_id': receipt_picking.id,
            'location_id': receipt_picking.location_id.id,
            'location_dest_id': receipt_picking.location_dest_id.id,
        })

        # Test 'Generate Serial/Lots' action, from the detailed operations view
        action_context = {
            'default_company_id': self.env.company.id,
            'default_picking_id': receipt_picking.id,
            'default_picking_type_id': self.warehouse.in_type_id.id,
            'default_location_id': receipt_picking.location_id.id,
            'default_location_dest_id': receipt_picking.location_dest_id.id,
            'default_product_id': product_lot.id,
            'default_tracking': 'serial',
        }
        move_line_vals = self.env['stock.move'].action_generate_lot_line_vals(
            action_context, 'generate', 'sn-t1-01', 5, False
        )
        sn_t1_03, sn_t1_04, sn_t1_05 = self.env['stock.lot'].search(
            [('name', 'in', ['sn-t1-03', 'sn-t1-04', 'sn-t1-05']), ('product_id', '=', product_lot.id)]
        )
        self.assert_move_line_vals_values(move_line_vals, [
            {'quantity': 1, 'lot_id': {'id': sn_t1_01.id, 'display_name': 'sn-t1-01'}},
            {'quantity': 1, 'lot_id': {'id': sn_t1_02.id, 'display_name': 'sn-t1-02'}},
            {'quantity': 1, 'lot_id': {'id': sn_t1_03.id, 'display_name': 'sn-t1-03'}},
            {'quantity': 1, 'lot_id': {'id': sn_t1_04.id, 'display_name': 'sn-t1-04'}},
            {'quantity': 1, 'lot_id': {'id': sn_t1_05.id, 'display_name': 'sn-t1-05'}},
        ])

        # Test 'Assign Serial Numbers' action from the operation tree view
        move._generate_serial_numbers('sn-t2-01', 5)
        sn_t2_01, sn_t2_02, sn_t2_03, sn_t2_04, sn_t2_05 = self.env['stock.lot'].search([
            ('name', 'in', ['sn-t2-01', 'sn-t2-02', 'sn-t2-03', 'sn-t2-04', 'sn-t2-05']),
            ('product_id', '=', product_lot.id),
        ])
        self.assertRecordValues(move.move_line_ids, [
            {'quantity': 1, 'lot_id': sn_t2_01.id},
            {'quantity': 1, 'lot_id': sn_t2_02.id},
            {'quantity': 1, 'lot_id': sn_t2_03.id},
            {'quantity': 1, 'lot_id': sn_t2_04.id},
            {'quantity': 1, 'lot_id': sn_t2_05.id},
        ])

    def test_sequence_serial_numbers_access_rights(self):
        """
        This test ensures that when a user has access to generating serial numbers,
        no Sequence access error is raised.
        """
        receipt_picking = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.in_type_id.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
        })

        # Simulate context provided from JS side, cf addons/stock/static/src/widgets/generate_serial.js:63-68
        action_context = {
            'default_company_id': self.env.company.id,
            'default_picking_id': receipt_picking.id,
            'default_picking_type_id': self.warehouse.in_type_id.id,
            'default_location_id': receipt_picking.location_id.id,
            'default_location_dest_id': receipt_picking.location_dest_id.id,
            'default_product_id': self.product_serial.id,
            'default_tracking': 'serial',
        }

        inventory_user = new_test_user(
            self.env,
            login='user_without_sn_generation_rights',
            groups='stock.group_stock_user',
        )
        first_num = self.product_serial.lot_sequence_id.number_next_actual
        self.product_serial.lot_sequence_id.invalidate_recordset(['number_next_actual'])
        move_line_vals = self.env['stock.move'].with_user(inventory_user.id).action_generate_lot_line_vals(
            action_context, 'generate', self.product_serial.lot_sequence_id.next_by_id(), 5, False
        )
        self.assert_move_line_vals_values(move_line_vals, [
            {'quantity': 1, 'lot_name': self.product_serial.lot_sequence_id.get_next_char(first_num)},
            {'quantity': 1, 'lot_name': self.product_serial.lot_sequence_id.get_next_char(first_num + 1)},
            {'quantity': 1, 'lot_name': self.product_serial.lot_sequence_id.get_next_char(first_num + 2)},
            {'quantity': 1, 'lot_name': self.product_serial.lot_sequence_id.get_next_char(first_num + 3)},
            {'quantity': 1, 'lot_name': self.product_serial.lot_sequence_id.get_next_char(first_num + 4)},
        ])

        move_line_vals = self.env['stock.move'].with_user(inventory_user.id).action_generate_lot_line_vals(
            action_context, 'generate', self.product_serial.lot_sequence_id.next_by_id(), 5, False
        )
        self.assert_move_line_vals_values(move_line_vals, [
            {'quantity': 1, 'lot_name': self.product_serial.lot_sequence_id.get_next_char(first_num + 5)},
            {'quantity': 1, 'lot_name': self.product_serial.lot_sequence_id.get_next_char(first_num + 6)},
            {'quantity': 1, 'lot_name': self.product_serial.lot_sequence_id.get_next_char(first_num + 7)},
            {'quantity': 1, 'lot_name': self.product_serial.lot_sequence_id.get_next_char(first_num + 8)},
            {'quantity': 1, 'lot_name': self.product_serial.lot_sequence_id.get_next_char(first_num + 9)},
        ])
