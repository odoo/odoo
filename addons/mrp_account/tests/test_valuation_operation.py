# Part of Odoo. See LICENSE file for full copyright and licensing details.
""" Implementation of "INVENTORY VALUATION TESTS (With valuation layers)" spreadsheet. """

from odoo.addons.mrp_account.tests.common import TestBomPriceOperationCommon
from odoo.tests import Form

PRICE = 718.75 + 2 * 321.25 - 100  # component price + operations - glass cost


class TestMrpValuationOperationStandard(TestBomPriceOperationCommon):

    def test_fifo_byproduct(self):
        """ Check that a MO byproduct with a cost share calculates correct svl """
        self.glass.categ_id = self.category_fifo
        self.glass.qty_available = 0
        self.scrap_wood.categ_id = self.category_avco
        byproduct_cost_share = 0.13

        self._make_in_move(self.glass, 1, 10)
        self._make_in_move(self.glass, 1, 20)

        mo = self._create_mo(self.bom_1, 2)
        self._produce(mo, 1)
        action = mo.button_mark_done()
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_backorder()
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
        self.assertRecordValues(moves, [
            {'value': self.company.currency_id.round((PRICE + 10) * 0.01)},
            {'value': self.company.currency_id.round((PRICE + 10) * 0.12)},
            {'value': self.company.currency_id.round((PRICE + 20) * 0.01)},
            {'value': self.company.currency_id.round((PRICE + 20) * 0.12)},
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
