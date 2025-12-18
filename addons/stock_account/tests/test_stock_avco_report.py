# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock_account.tests.common import TestStockValuationCommon


class TestStockValuation(TestStockValuationCommon):
    def test_avco_report_in_move_new_value(self):
        """Check that the top line of the stock.avco.report's avco value
        matches the standard_price when the value of an in_move
        has been changed after the following out move
        """
        product = self.product_avco_auto
        move_in = self._make_in_move(product, 2, 10)
        self._make_out_move(product, 2)
        move_in.value = 24
        self._make_in_move(product, 1, 10)
        report_lines = self.env['stock.avco.report'].search([('product_id', '=', product.id)])
        report_lines._compute_cumulative_fields()
        self.assertEqual(report_lines[0].avco_value, 10)
        self.assertEqual(product.standard_price, 10)
