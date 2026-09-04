# Part of Odoo. See LICENSE file for full copyright and licensing details.
""" Implementation of "INVENTORY VALUATION TESTS (With valuation layers)" spreadsheet. """

from odoo.addons.mrp_account.tests.common import TestBomPriceOperationCommon

PRICE = 718.75 + 2 * 321.25 - 100  # component price + operations - glass cost


class TestMrpValuationOperationStandard(TestBomPriceOperationCommon):

    _test_user_groups = (
        'mrp.group_mrp_user',  # subject: manufacturing orders drive the valuation layers (implies stock.group_stock_user)
        'mrp.group_mrp_routings',  # subject: work order / routing operations and their cost
        'stock.group_stock_manager',  # setup: _make_in_move sets value_manual -> inverse creates product.value (stock.group_stock_manager)
        'account.group_account_invoice',  # subject: stock valuation journal entries asserted by the tests
    )

    _test_user_name = 'Test User'

    def test_fifo_byproduct(self):
        """ Check that a MO byproduct with a cost share calculates correct svl """
        self.glass.sudo().categ_id = self.category_fifo  # setup master-data
        self.glass.sudo().qty_available = 0  # setup master-data
        self.scrap_wood.sudo().categ_id = self.category_avco  # setup master-data
        byproduct_cost_share = 0.13

        self._make_in_move(self.glass, 1, 10)
        self._make_in_move(self.glass, 1, 20)

        mo = self._create_mo(self.bom_1, 2)
        self._produce(mo, 1)
        action = mo.button_mark_done()
        self.env['mrp.production.backorder'].with_context(**action['context']).create({}).action_backorder()
        mo = mo.production_group_id.production_ids[-1]
        self.assertEqual(self.glass.total_value, 20)
        self.assertEqual(self.dining_table.total_value, self.company.currency_id.round((PRICE + 10) * (1 - byproduct_cost_share)))
        self.assertEqual(self.scrap_wood.total_value, self.company.currency_id.round((PRICE + 10) * byproduct_cost_share))
        self._produce(mo)
        mo.button_mark_done()
        self.assertEqual(self.glass.total_value, 0)
        self.assertEqual(self.dining_table.total_value, self.company.currency_id.round((2 * PRICE + 30) * (1 - byproduct_cost_share)))
        moves = self.env['stock.move'].search([
            ('product_id', '=', self.scrap_wood.id),
        ])
        # price_unit = total_cost * cost_share% / qty_in_product_uom
        # line 1 (8 units, 1%):    (P+N) * 0.01 / 8  = (P+N) / 800
        # line 2 (1 dozen, 12%):   (P+N) * 0.12 / 12 = (P+N) / 100
        self.assertRecordValues(moves, [
            {'value': self.company.currency_id.round((PRICE + 10) * 0.01), 'price_unit': (PRICE + 10) / 800},
            {'value': self.company.currency_id.round((PRICE + 10) * 0.12), 'price_unit': (PRICE + 10) / 100},
            {'value': self.company.currency_id.round((PRICE + 20) * 0.01), 'price_unit': (PRICE + 20) / 800},
            {'value': self.company.currency_id.round((PRICE + 20) * 0.12), 'price_unit': (PRICE + 20) / 100},
        ])

    # def test_average_cost_unbuild_with_byproducts(self):
    #     """ Ensures that an unbuild for a manufacturing order using avg cost products won't copy
    #         the value of the main product for every byproduct line, regardless of their real value.
    #     """
    #     self.dining_table.categ_id = self.category_avco
    #     self.glass.categ_id = self.category_avco
    #     self.scrap_wood.categ_id = self.category_avco
    #     byproduct_cost_share = 0.13
    #
    #     self._make_in_move(self.glass, 10)
    #     production = self._create_mo(self.bom_1, 1)
    #     self._produce(production)
    #     production.button_mark_done()
    #
    #     self.assertEqual(self.scrap_wood.total_value, (PRICE + 10) * byproduct_cost_share)
    #     self.assertRecordValues(production.move_finished_ids, [
    #         {'product_id': self.dining_table.id, 'value': (PRICE + 10) * (1 - byproduct_cost_share)},
    #         {'product_id': self.scrap_wood.id, 'value': (PRICE + 10) * 0.12},
    #         {'product_id': self.scrap_wood.id, 'value': (PRICE + 10) * 0.1},
    #     ])
    #
    #     action = production.button_unbuild()
    #     wizard = Form(self.env[action['res_model']].with_context(action['context']))
    #     wizard.product_qty = 1
    #     unbuild = wizard.save()
    #     unbuild.action_validate()
    #
    #     unbuild_move = self.env['stock.move'].search([('reference', '=', unbuild.name)])
    #     self.assertRecordValues(unbuild_move, [
    #         {'product_id': self.dining_table.id, 'value': (PRICE + 10) * (1 - byproduct_cost_share)},
    #         {'product_id': self.scrap_wood.id, 'value': (PRICE + 10) * byproduct_cost_share},
    #         {'product_id': self.glass.id, 'value': 10},
    #     ])

    def test_standard_finished_byproduct_price_unit(self):
        """Standard-cost byproducts use their own standard_price when the
        finished product is standard cost — the MO has no influence."""
        (self.dining_table | self.scrap_wood).sudo().categ_id = self.category_standard
        self._make_in_move(self.glass, 1, 10)
        mo = self._create_mo(self.bom_1, 1)
        self._produce(mo)
        mo.button_mark_done()
        self.assertEqual(mo.move_byproduct_ids.mapped('price_unit'), [30.0, 30.0])

    def test_fifo_finished_standard_byproduct_price_unit(self):
        """Standard-cost byproducts use their own standard_price even when the
        finished product is FIFO. Their cost_share is still deducted from the
        finished product so no value disappears from inventory."""
        self.scrap_wood.sudo().categ_id = self.category_standard
        self._make_in_move(self.glass, 1, 10)
        mo = self._create_mo(self.bom_1, 1)
        self._produce(mo)
        mo.button_mark_done()
        self.assertEqual(mo.move_byproduct_ids.mapped('price_unit'), [30.0, 30.0])
        total_cost = PRICE + 10
        byproduct_cost_share = sum(self.bom_1.byproduct_ids.mapped('cost_share')) / 100
        self.assertEqual(
            self.dining_table.total_value,
            self.company.currency_id.round(total_cost * (1 - byproduct_cost_share)),
        )
