from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import tagged

from odoo.addons.stock_account.tests.common import TestStockValuationCommon


@tagged("post_install", "-at_install")
class TestBackdatedReceiptValuation(TestStockValuationCommon):

    def _create_avco_product(self):
        return self.env['product.product'].create({
            **self.product_common_vals,
            'name': 'Avco Product',
            'categ_id': self.category_avco_auto.id,
            'standard_price': 0.0,
        })

    def _last_manual_value(self, product):
        return self.env['product.value'].search(
            [('product_id', '=', product.id), ('move_id', '=', False)], order='id desc', limit=1)

    def test_backdated_receipt_before_manual_cost_is_valued(self):
        product = self._create_avco_product()
        product.standard_price = 250.0
        move = self._make_in_move(product, 10, unit_cost=100.0)

        move.date = fields.Datetime.now() - relativedelta(months=1)

        product._update_standard_price()
        self.assertAlmostEqual(product.standard_price, 100.0)
        self.assertAlmostEqual(product.total_value, 1000.0)
        self.assertLess(self._last_manual_value(product).date, move.date)

    def test_backdated_receipt_not_crossing_manual_cost_keeps_it(self):
        product = self._create_avco_product()
        move = self._make_in_move(product, 10, unit_cost=100.0)
        move.date = fields.Datetime.now() - relativedelta(months=1)
        product.standard_price = 250.0
        manual_value_date = self._last_manual_value(product).date

        move.date = fields.Datetime.now() - relativedelta(months=2)

        self.assertEqual(self._last_manual_value(product).date, manual_value_date)
        product._update_standard_price()
        self.assertAlmostEqual(product.standard_price, 250.0)

    def test_normal_avco_receipts_unaffected(self):
        product = self._create_avco_product()
        self._make_in_move(product, 10, unit_cost=100.0)
        self._make_in_move(product, 10, unit_cost=200.0)

        product._update_standard_price()
        self.assertAlmostEqual(product.standard_price, 150.0)
