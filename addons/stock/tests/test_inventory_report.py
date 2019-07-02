# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import fields
from odoo.tools import date_utils
from odoo.tests.common import TransactionCase

class TestInventoryReport(TransactionCase):
    def setUp(self):
        super(TestInventoryReport, self).setUp()
        self.stock_quant_history = self.env['stock.quantity.history'].create({})
        self.customer_location = self.env.ref('stock.stock_location_customers')
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.uom_unit = self.env.ref('uom.product_uom_unit')

        self.product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id
        })

        # Define some old dates
        self.move_date = date_utils.add(fields.Datetime.now(), days=-2)
        self.before_move_date = date_utils.add(fields.Datetime.now(), days=-7)
        self.after_move_date = fields.Datetime.now()
        # Update product quantity
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product1.id,
            'location_id': self.stock_location.id,
            'inventory_quantity': 100
        })

        # Create a move...
        self.move1 = self.env['stock.move'].create({
            'name': 'product1_from_stock_to_customer',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 50.0,
        })
        # ... and confirm it
        self.move1._action_confirm()
        self.move1._action_assign()
        self.move1.move_line_ids[0].qty_done = 50
        self.move1._action_done()

        # Reasign date of move line
        self.move1.date = self.move_date
        for move_line in self.move1.move_line_ids:
            move_line.date = self.move1.date

    def test_inventory_report_1(self):
        """ Check that asking a report at date before a move, we get product
        quantity corresponding what we have before this move.
        """
        # Just ensure that id do not raise an error.
        self.stock_quant_history.date = self.before_move_date
        self.stock_quant_history.open_at_date()

        report_line = self.env['stock.inventory.report'].search([
            ('product_id', '=', self.product1.id),
            ('location_id', '=', self.customer_location.id),
            ('date', '<=', self.before_move_date)
        ])
        self.assertEqual(report_line.quantity, 0)

        report_line = self.env['stock.inventory.report'].search([
            ('product_id', '=', self.product1.id),
            ('location_id', '=', self.stock_location.id),
            ('date', '<=', self.before_move_date)
        ])
        self.assertEqual(report_line.quantity, 0)

    def test_inventory_report_2(self):
        """ Check that asking a report at date after a move, we don't take this
        move in count when inventory report determines the products quantity.
        """

        self.stock_quant_history.date = self.after_move_date
        self.stock_quant_history.open_at_date()

        report_line = self.env['stock.inventory.report'].search([
            ('product_id', '=', self.product1.id),
            ('location_id', '=', self.customer_location.id),
            ('date', '<=', self.after_move_date)
        ])
        self.assertEqual(report_line.quantity, 50)

        report_line = self.env['stock.inventory.report'].search([
            ('product_id', '=', self.product1.id),
            ('location_id', '=', self.stock_location.id),
            ('date', '<=', self.after_move_date)
        ])
        self.assertEqual(sum(report_line.mapped('quantity')), 50)
