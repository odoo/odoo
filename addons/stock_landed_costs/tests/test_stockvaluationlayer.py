# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" Implementation of "INVENTORY VALUATION TESTS (With valuation layers)" spreadsheet. """

from odoo.tests import Form, tagged
from odoo.addons.stock_account.tests.test_stockvaluationlayer import TestStockValuationCommon


class TestStockValuationLC(TestStockValuationCommon):
    @classmethod
    def setUpClass(cls):
        super(TestStockValuationLC, cls).setUpClass()
        cls.productlc1 = cls.env['product.product'].create({
            'name': 'product1',
            'type': 'service',
            'landed_cost_ok': True,
            'categ_id': cls.env.ref('product.product_category_all').id,
        })

    def _make_lc(self, move, amount):
        picking = move.picking_id
        lc = Form(self.env['stock.landed.cost'])
        lc.account_journal_id = self.env['account.journal'].search([('name', 'ilike', '%misc%')], limit=1)
        lc.picking_ids.add(move.picking_id)
        with lc.cost_lines.new() as cost_line:
            cost_line.product_id = self.productlc1
            cost_line.price_unit = amount
        lc = lc.save()
        lc.compute_landed_cost()
        lc.button_validate()
        return lc


@tagged('post_install', '-at_install')
class TestStockValuationLCFIFO(TestStockValuationLC):
    def setUp(self):
        super(TestStockValuationLCFIFO, self).setUp()
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'

    def test_normal_1(self):
        move1 = self._make_in_move(self.product1, 10, unit_cost=10, create_picking=True)
        move2 = self._make_in_move(self.product1, 10, unit_cost=20)
        lc = self._make_lc(move1, 100)
        move3 = self._make_out_move(self.product1, 1)

        self.assertEqual(self.product1.value_svl, 380)
        self.assertEqual(self.product1.quantity_svl, 19)

    def test_negative_1(self):
        self.product1.standard_price = 10
        move1 = self._make_out_move(self.product1, 2, force_assign=True)
        move2 = self._make_in_move(self.product1, 10, unit_cost=15, create_picking=True)
        lc = self._make_lc(move2, 100)

        self.assertEqual(self.product1.value_svl, 200)
        self.assertEqual(self.product1.quantity_svl, 8)

    def test_alreadyout_1(self):
        move1 = self._make_in_move(self.product1, 10, unit_cost=10, create_picking=True)
        move2 = self._make_out_move(self.product1, 10)
        lc = self._make_lc(move1, 100)

        self.assertEqual(self.product1.value_svl, 0)
        self.assertEqual(self.product1.quantity_svl, 0)

    def test_alreadyout_2(self):
        move1 = self._make_in_move(self.product1, 10, unit_cost=10, create_picking=True)
        move2 = self._make_in_move(self.product1, 10, unit_cost=20)
        move2 = self._make_out_move(self.product1, 1)
        lc = self._make_lc(move1, 100)

        self.assertEqual(self.product1.value_svl, 380)
        self.assertEqual(self.product1.quantity_svl, 19)

    def test_alreadyout_3(self):
        move1 = self._make_in_move(self.product1, 10, unit_cost=10, create_picking=True)
        move2 = self._make_out_move(self.product1, 10)
        move1.move_line_ids.qty_done = 15
        lc = self._make_lc(move1, 60)

        self.assertEqual(self.product1.value_svl, 70)
        self.assertEqual(self.product1.quantity_svl, 5)
