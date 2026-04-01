# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.tests.common import TransactionCase


class StockMove(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.product = cls.env['product.product'].create({
            'name': 'Product A',
            'is_storable': True,
        })
        cls.env['stock.quant']._update_available_quantity(cls.product, cls.stock_location, 10.0)
        cls.product_consu = cls.env['product.product'].create({
            'name': 'Product A',
            'type': 'consu',
        })

    def test_show_detailed(self):
        """
        Create an delivery immediate transfer with a storable and a consumable
        product. The consumable product should not create move line from quants.
        """
        # create a delivery order
        picking = Form(self.env['stock.picking'].with_context(default_picking_type_id=self.ref('stock.picking_type_out')))
        with picking.move_ids.new() as move:
            move.product_id = self.product
            move.product_uom_qty = 1.0
        with picking.move_ids.new() as move:
            move.product_id = self.product_consu
            move.product_uom_qty = 1.0
        picking = picking.save()

        self.assertEqual(picking.move_ids[0].show_quant, True)
        self.assertEqual(picking.move_ids[1].show_quant, False)

    def test_create_move_line_reserved(self):
        """ Create a delivery immediate transfer with a storable product.
        The move line should be reserved.
        """
        # create a delivery order
        picking = Form(self.env['stock.picking'].with_context(default_picking_type_id=self.ref('stock.picking_type_out')))
        with picking.move_ids.new() as move:
            move.product_id = self.product
            move.product_uom_qty = 2.0
        picking = picking.save()

        # we check that changing the quantity while still in draft doesn't change the state of the move
        picking.move_ids.write({'product_uom_qty': 1})
        self.assertEqual(picking.move_ids.state, 'draft')

        self.env['stock.move.line'].create({
            'move_id': picking.move_ids.id,
            'product_id': self.product.id,
            'quantity': 1.0,
        })
        self.assertEqual(picking.move_ids.quantity, 1.0)
        self.assertEqual(picking.move_ids.state, 'assigned')
        self.assertEqual(picking.move_ids.picked, False)
