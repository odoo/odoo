# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from freezegun import freeze_time

from odoo.addons.stock.tests.common import TestStockCommon
from odoo.exceptions import UserError
from odoo.tests import Form


class StockMoveLine(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.groups_id += cls.env.ref("stock.group_tracking_owner")
        cls.env.user.groups_id += cls.env.ref("stock.group_tracking_lot")
        cls.env.user.groups_id += cls.env.ref("stock.group_production_lot")
        cls.env.user.groups_id += cls.env.ref('stock.group_stock_multi_locations')
        cls.product = cls.env['product.product'].create({
            'name': 'Product A',
            'is_storable': True,
            'tracking': 'lot',
        })
        cls.shelf1 = cls.env['stock.location'].create({
            'name': 'Shelf 1',
            'usage': 'internal',
            'location_id': cls.stock_location.id,
        })
        cls.pack = cls.env['stock.quant.package'].create({
            'name': 'Pack A',
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
            'location_id': cls.shelf1.id,
            'quantity': 10,
            'lot_id': cls.lot.id,
            'package_id': cls.pack.id,
            'owner_id': cls.partner.id,
        })

    def test_pick_from_1(self):
        """ test quant display_name """
        self.assertEqual(self.quant.display_name, 'Test /Stock/Shelf 1 - Lot 1 - Pack A - The Owner')

    def test_pick_from_2(self):
        """ Create a move line from a quant"""
        move = self.env['stock.move'].create({
            'name': 'Test move',
            'product_id': self.product.id,
            'product_uom': self.product.uom_id.id,
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
        self.assertEqual(move.move_line_ids.location_id, self.shelf1)
        self.assertEqual(move.move_line_ids.quantity, 10)

    def test_pick_from_3(self):
        """ check the quantity done is added up to the initial demand"""
        move = self.env['stock.move'].create({
            'name': 'Test move',
            'product_id': self.product.id,
            'product_uom': self.product.uom_id.id,
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
        self.env['stock.quant']._update_available_quantity(self.product, self.shelf1, -20, lot_id=self.lot, package_id=self.pack, owner_id=self.partner)
        self.assertEqual(self.quant.quantity, -10)
        move = self.env['stock.move'].create({
            'name': 'Test move',
            'product_id': self.product.id,
            'product_uom': self.product.uom_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
        })
        move_form = Form(move, view='stock.view_stock_move_operations')
        with move_form.move_line_ids.new() as ml:
            ml.quant_id = self.quant

        self.assertEqual(move.move_line_ids.quantity, 0)

    def test_pick_from_5(self):
        """ check small quantities get handled correctly """
        with self.with_user('admin'):
            self.env.ref('product.decimal_product_uom').digits = 6
        self.product.uom_id = self.uom_kg
        move = self.env['stock.move'].create({
            'name': 'Test move',
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
        self.assertEqual(len(picking1.package_level_ids), 0)
        self.assertEqual(len(picking2.package_level_ids), 0)

    def test_multi_edit_quant_and_lot(self):
        """
        Ensure that the quant_id and lot_id cannot be updated in multi-edit mode when the move lines use different products.
        """
        self.env['stock.quant']._update_available_quantity(self.product, self.shelf1, 20, lot_id=self.lot, owner_id=self.partner)
        quant_productA = self.env['stock.quant']._update_available_quantity(self.productA, self.shelf1, 20, owner_id=self.partner)
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

    def test_move_line_date(self):
        # we need to freezetime due to write time being too fast for date changes to be observed
        with freeze_time() as freeze:
            move = self.env['stock.move'].create({
                'name': 'test_move_line_date',
                'location_id': self.stock_location.id,
                'location_dest_id': self.customer_location.id,
                'product_id': self.productA.id,
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 10.0,
            })
            move.quantity = 1
            ml = move.move_line_ids
            self.assertFalse(ml.picked, "Move line shouldn't be 'picked' yet")
            freeze.tick(delta=datetime.timedelta(seconds=2))
            create_date = ml.date
            ml.quantity = 2
            self.assertFalse(ml.picked, "Move line shouldn't be 'picked' yet")
            self.assertEqual(ml.date, create_date, "Increasing a quantity that isn't 'picked' shouldn't update its date")
            freeze.tick(delta=datetime.timedelta(seconds=2))
            ml.picked = True
            update_date_1 = ml.date
            self.assertTrue(update_date_1 > create_date, "Marking a ml as 'picked' should update its date")
            freeze.tick(delta=datetime.timedelta(seconds=2))
            ml.quantity = 3
            update_date_2 = ml.date
            self.assertTrue(update_date_2 > update_date_1, "Increasing a ml's quantity should update its date")
            freeze.tick(delta=datetime.timedelta(seconds=2))
            ml.product_uom_id = self.uom_dozen
            update_date_3 = ml.date
            self.assertTrue(update_date_3 > update_date_2, "Increasing a ml's quantity (via UoM type) should update its date")
            freeze.tick(delta=datetime.timedelta(seconds=2))
            ml.quantity = 2
            self.assertEqual(update_date_3, ml.date, "Decreasing a ml's quantity shouldn't update its date")
            freeze.tick(delta=datetime.timedelta(seconds=2))
            ml.write({
                'product_uom_id': self.uom_unit.id,
                'quantity': 24
            })
            # 2 dozen = 24 units
            self.assertEqual(update_date_3, ml.date, "Quantity change check for date should take into account UoM conversion")
            freeze.tick(delta=datetime.timedelta(seconds=2))
            ml.write({
                'product_uom_id': self.uom_dozen.id,
                'quantity': 3
            })
            # 36 units > 24 units
            self.assertTrue(ml.date > update_date_3, "Quantity change check for date should take into account UoM conversion")
