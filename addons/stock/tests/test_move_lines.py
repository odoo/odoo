# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.stock.tests.common import TestStockCommon
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged, Form


class TestStockMoveLine(TestStockCommon):
    _test_user_groups = (
        'product.group_product_manager',  # FIXME: use base.group_user
        'stock.group_stock_user',
    )

    _test_user_name = 'Test Product Manager'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids += cls.env.ref("stock.group_tracking_owner")
        cls.env.user.group_ids += cls.env.ref("stock.group_tracking_lot")
        cls.env.user.group_ids += cls.env.ref("stock.group_production_lot")
        cls.env.user.group_ids += cls.env.ref('stock.group_stock_multi_locations')
        cls.product = cls.env['product.product'].create({
            'name': 'Product A',
            'is_storable': True,
            'tracking': 'lot',
        })
        cls.pack = cls.env['stock.package'].create({
            'name': 'Pack A',
        })
        cls.package_type = cls.env['stock.package.type'].create({
            'name': 'Super Package Type',
        })
        cls.lot = cls.env['stock.lot'].create({
            'product_id': cls.product.id,
            'name': 'Lot 1',
        })
        cls.partner = cls.env['res.partner'].create({
            'name': 'The Owner',
            'email': 'owner@example.com',
        })

        cls.quant = cls.env['stock.quant'].create({
            'product_id': cls.product.id,
            'location_id': cls.shelf_1.id,
            'quantity': 10,
            'lot_id': cls.lot.id,
            'package_id': cls.pack.id,
            'owner_id': cls.partner.id,
        })

    def test_pick_from_1(self):
        """ test quant display_name """
        self.assertEqual(self.quant.display_name, 'BWH/Stock/Shelf 1 - Lot 1 - Pack A - The Owner')

    def test_pick_from_2(self):
        """ Create a move line from a quant"""
        move = self.env['stock.move'].create({
            'product_id': self.product.id,
            'uom_id': self.product.uom_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
        })
        move_form = Form(move, view='stock.view_stock_move_operations')
        with move_form.move_line_ids.new() as ml:
            ml.quant_id = self.quant

        move = move_form.save()

        self.assertEqual(move.move_line_ids.lot_id, self.lot)
        self.assertEqual(move.move_line_ids.package_id, self.pack)
        self.assertEqual(move.move_line_ids.owner_id, self.partner)
        self.assertEqual(move.move_line_ids.location_id, self.shelf_1)
        self.assertEqual(move.move_line_ids.quantity, 10)

    def test_pick_from_3(self):
        """ check the quantity done is added up to the initial demand"""
        move = self.env['stock.move'].create({
            'product_id': self.product.id,
            'uom_id': self.product.uom_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_int.id,
            'state': 'draft',
            'product_uom_qty': 5,
        })
        move._action_confirm()
        move._action_assign()
        move.move_line_ids.quantity = 0
        self.assertEqual(move.move_line_ids.quantity, 0)
        move_form = Form(move, view='stock.view_stock_move_operations')
        with move_form.move_line_ids.edit(0) as ml:
            ml.quant_id = self.quant
        move = move_form.save()
        self.assertEqual(move.move_line_ids.quantity, 5)

    def test_pick_from_4(self):
        """ check the quantity done is not negative if the quant has negative quantity"""
        self.env['stock.quant']._update_available_quantity(self.product, self.shelf_1, -20, lot_id=self.lot, package_id=self.pack, owner_id=self.partner)
        self.assertEqual(self.quant.quantity, -10)
        move = self.env['stock.move'].create({
            'product_id': self.product.id,
            'uom_id': self.product.uom_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
        })
        move_form = Form(move, view='stock.view_stock_move_operations')
        with move_form.move_line_ids.new() as ml:
            ml.quant_id = self.quant

        self.assertEqual(move.move_line_ids.quantity, 0)

    def test_pick_from_5(self):
        """ check small quantities get handled correctly """
        precision = self.env.ref('uom.decimal_product_uom')
        precision.sudo().digits = 6
        self.product.uom_id = self.uom_kg
        move = self.env['stock.move'].create({
            'product_id': self.product.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'product_uom_qty': 1e-5,
        })
        move_form = Form(move, view='stock.view_stock_move_operations')
        with move_form.move_line_ids.new() as ml:
            ml.quant_id = self.quant
        move = move_form.save()
        self.assertAlmostEqual(
            move.move_line_ids.quantity,
            1e-5,
            delta=1e-6,
            msg="Small line quantity should get detected",
        )

    def test_put_in_pack_with_several_move_lines(self):
        picking1 = self.env['stock.picking'].create({
            'name': 'Picking 1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
        })
        picking2 = picking1.copy({'name': 'picking 2'})
        move_line1 = self.env['stock.move.line'].create({
            'picking_id': picking1.id,
            'product_id': self.productA.id,
            'quantity': 1,
        })
        move_line2 = self.env['stock.move.line'].create({
            'picking_id': picking2.id,
            'product_id': self.productA.id,
            'quantity': 1,
        })
        (move_line1 | move_line2).action_put_in_pack()
        self.assertEqual(move_line1.result_package_id, move_line2.result_package_id)

    def test_put_in_pack_with_split_picking_error(self):
        """
        Check putting in pack with splitting. It should throw an error,
        because multiple MLs are passed
        """

        move1 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.productA.id,
            'uom_id': self.uom_unit.id,
            'product_uom_qty': 12.0,
            'move_line_ids': [Command.create({
                'product_id': self.productA.id,
                'quantity': qty,
                'uom_id': self.uom_unit.id,
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
            }) for qty in (6, 6)],
        })

        with self.assertRaises(ValueError):
            move1.move_line_ids.action_put_in_pack(package_type_id=self.package_type.id, package_capacity=6)

    def test_put_in_pack_with_split_moves(self):
        """
        Check putting in pack with splitting from the Moves button.
        First time it should throw an error because we are trying to Put in Pack with
        a capacity higher than the ML quantity.
        Next time it should split existing line into 3 lines with quantity 5, 5, and 2.
        """

        move1 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.productA.id,
            'uom_id': self.uom_unit.id,
            'product_uom_qty': 12.0,
            'move_line_ids': [Command.create({
                'product_id': self.productA.id,
                'quantity': 12,
                'uom_id': self.uom_unit.id,
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
            })],
        })

        with self.assertRaises(ValidationError):
            move1.move_line_ids.action_put_in_pack(package_type_id=self.package_type.id, package_capacity=13)

        move1.move_line_ids.action_put_in_pack(package_type_id=self.package_type.id, package_capacity=5)
        self.assertEqual(len(move1.move_line_ids), 3)
        move_line1, move_line2, move_line3 = move1.move_line_ids[0], move1.move_line_ids[1], move1.move_line_ids[2]
        self.assertEqual(move_line1.quantity, 5.0)
        self.assertEqual(move_line2.quantity, 5.0)
        self.assertEqual(move_line3.quantity, 2.0)
        self.assertEqual(move_line1.result_package_id.package_type_id.id, self.package_type.id)
        self.assertEqual(move_line2.result_package_id.package_type_id.id, self.package_type.id)
        self.assertEqual(move_line3.result_package_id.package_type_id.id, self.package_type.id)

    def test_put_in_pack_with_split_moves_with_package(self):
        """
        Check putting in pack with splitting from the Moves button with a package.
        Should split existing line into 2 lines with quantity 5, 7, with the first
        one having a package, and the second one not.
        """

        move1 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.productA.id,
            'uom_id': self.uom_unit.id,
            'product_uom_qty': 12.0,
            'move_line_ids': [Command.create({
                'product_id': self.productA.id,
                'quantity': 12,
                'uom_id': self.uom_unit.id,
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
            })],
        })

        move1.move_line_ids.action_put_in_pack(package_id=self.pack.id, package_capacity=5)
        self.assertEqual(len(move1.move_line_ids), 2)
        move_line1, move_line2 = move1.move_line_ids[0], move1.move_line_ids[1]
        self.assertEqual(move_line1.quantity, 5.0)
        self.assertEqual(move_line2.quantity, 7.0)
        self.assertEqual(move_line1.result_package_id.id, self.pack.id)
        self.assertEqual(move_line2.result_package_id.id, False)

    def test_multi_edit_quant_and_lot(self):
        """
        Ensure that the quant_id and lot_id cannot be updated in multi-edit mode when the move lines use different products.
        """
        self.env['stock.quant']._update_available_quantity(self.product, self.shelf_1, 20, lot_id=self.lot, owner_id=self.partner)
        quant_productA = self.env['stock.quant']._update_available_quantity(self.productA, self.shelf_1, 20, owner_id=self.partner)
        picking1 = self.env['stock.picking'].create({
            'name': 'Picking 1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
        })
        move_line1 = self.env['stock.move.line'].create({
            'picking_id': picking1.id,
            'product_id': self.product.id,
            'quantity': 1,
        })
        move_line2 = self.env['stock.move.line'].create({
            'picking_id': picking1.id,
            'product_id': self.productA.id,
            'quantity': 1,
        })
        with self.assertRaises(UserError):
            (move_line1 | move_line2).lot_id = self.lot
        with self.assertRaises(UserError):
            (move_line1 | move_line2).quant_id = quant_productA

    def test_lot_creation_from_move_line_with_generic_stock(self):
        """
        Test that if the product already have quantities and after that tracking is set to serial,
        we can create a lot and assign it to the move.
        """
        self.productA.tracking = "none"

        self.env["stock.quant"]._update_available_quantity(self.productA, self.stock_location, 100)

        self.productA.tracking = "serial"

        serial_lot = self.env["stock.lot"].create(
            {
                "name": "SN001",
                "product_id": self.productA.id,
                "company_id": self.env.company.id,
            }
        )

        move = self.env["stock.move"].create(
            {
                "product_id": self.productA.id,
                "product_uom_qty": 1.0,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "lot_ids": [Command.link(serial_lot.id)],
            }
        )

        line = move.move_line_ids[0]
        self.assertEqual(line.lot_id, serial_lot)

    def test_action_detailed_operations_domain_includes_new_lines(self):
        """Test that newly created move lines remain visible in detailed operations view."""
        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_in.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'move_ids': [Command.create({
                'product_id': self.productA.id,
                'product_uom_qty': 10.0,
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
            })],
        })
        receipt.action_confirm()
        initial_move_line = receipt.move_line_ids
        self.assertRecordValues(initial_move_line, [{'quantity': 10.0}])
        action = receipt.action_detailed_operations()
        self.assertEqual(initial_move_line, self.env['stock.move.line'].search(action['domain']))

        new_move_line = self.env['stock.move.line'].create({
            'picking_id': receipt.id,
            'product_id': self.productA.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'move_id': receipt.move_ids.id,
            'quantity': 5.0,
        })
        self.assertEqual(initial_move_line | new_move_line, self.env['stock.move.line'].search(action['domain']))
