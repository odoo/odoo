# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock.tests.common import TestStockCommon
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
            'type': 'product',
            'tracking': 'lot',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })
        cls.shelf1 = cls.env['stock.location'].create({
            'name': 'Shelf 1',
            'usage': 'internal',
            'location_id': cls.stock_location,
        })
        cls.pack = cls.env['stock.quant.package'].create({
            'name': 'Pack A',
        })
        cls.lot = cls.env['stock.lot'].create({
            'product_id': cls.product.id,
            'name': 'Lot 1',
            'company_id': cls.env.company.id,
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
        cls.picking_type_internal = cls.env['ir.model.data']._xmlid_to_res_id('stock.picking_type_internal')

    def test_pick_from_1(self):
        """ test quant display_name """
        self.assertEqual(self.quant.display_name, 'WH/Stock/Shelf 1 - Lot 1 - Pack A - The Owner')

    def test_pick_from_2(self):
        """ Create a move line from a quant"""
        move = self.env['stock.move'].create({
            'name': 'Test move',
            'product_id': self.product.id,
            'product_uom': self.product.uom_id.id,
            'location_id': self.stock_location,
            'location_dest_id': self.stock_location,
        })
        move_form = Form(move, view='stock.view_stock_move_operations')
        with move_form.move_line_nosuggest_ids.new() as ml:
            ml.quant_id = self.quant

        move = move_form.save()

        self.assertEqual(move.move_line_ids.lot_id, self.lot)
        self.assertEqual(move.move_line_ids.package_id, self.pack)
        self.assertEqual(move.move_line_ids.owner_id, self.partner)
        self.assertEqual(move.move_line_ids.location_id, self.shelf1)
        self.assertEqual(move.move_line_ids.qty_done, 10)

    def test_pick_from_3(self):
        """ check the quantity done is added up to the initial demand"""
        move = self.env['stock.move'].create({
            'name': 'Test move',
            'product_id': self.product.id,
            'product_uom': self.product.uom_id.id,
            'location_id': self.stock_location,
            'location_dest_id': self.stock_location,
            'picking_type_id': self.picking_type_internal,
            'state': 'draft',
            'product_uom_qty': 5,
        })
        move._action_confirm()
        move._action_assign()
        self.assertEqual(move.move_line_ids.qty_done, 0)
        move_form = Form(move, view='stock.view_stock_move_operations')
        with move_form.move_line_ids.edit(0) as ml:
            ml.quant_id = self.quant
        move = move_form.save()
        self.assertEqual(move.move_line_ids.qty_done, 5)
        self.assertEqual(move.move_line_ids.reserved_qty, 5)

    def test_pick_from_4(self):
        """ check the quantity done is not negative if the quant has negative quantity"""
        self.env['stock.quant']._update_available_quantity(self.product, self.shelf1, -20, self.lot, package_id=self.pack, owner_id=self.partner)
        self.assertEqual(self.quant.quantity, -10)
        move = self.env['stock.move'].create({
            'name': 'Test move',
            'product_id': self.product.id,
            'product_uom': self.product.uom_id.id,
            'location_id': self.stock_location,
            'location_dest_id': self.stock_location,
        })
        move_form = Form(move, view='stock.view_stock_move_operations')
        with move_form.move_line_nosuggest_ids.new() as ml:
            ml.quant_id = self.quant

        self.assertEqual(move.move_line_ids.qty_done, 0)
