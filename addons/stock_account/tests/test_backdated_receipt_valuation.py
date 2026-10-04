from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import tagged

from odoo.addons.stock_account.tests.common import TestStockValuationCommon


@tagged("post_install", "-at_install")
class TestBackdatedReceiptValuation(TestStockValuationCommon):

    def _age_last_manual_value(self, product, create_date):
        # A test runs in one transaction, so every row shares a create_date; force the
        # manual value to predate the receipt, the ordering the fix relies on.
        pv = self.env['product.value'].search(
            [('product_id', '=', product.id), ('move_id', '=', False)],
            order='id desc', limit=1,
        )
        self.env.cr.execute(
            "UPDATE product_value SET create_date = %s WHERE id = %s",
            (create_date, pv.id),
        )
        self.env.invalidate_all()
        return pv

    def test_backdated_receipt_before_manual_cost_is_valued(self):
        product = self.env['product.product'].create({
            **self.product_common_vals,
            'name': 'Avco Backdated',
            'categ_id': self.category_avco_auto.id,
            'standard_price': 0.0,
        })
        product.standard_price = 250.0
        self._age_last_manual_value(product, fields.Datetime.now() - relativedelta(years=1))

        move = self._make_in_move(product, 10, unit_cost=100.0)
        move.date = fields.Datetime.now() - relativedelta(months=1)

        product._update_standard_price()
        self.assertAlmostEqual(product.standard_price, 100.0)
        self.assertAlmostEqual(product.total_value, 1000.0)

    def test_manual_cost_without_backdated_receipt_is_kept(self):
        product = self.env['product.product'].create({
            **self.product_common_vals,
            'name': 'Avco Manual Override',
            'categ_id': self.category_avco_auto.id,
            'standard_price': 0.0,
        })
        product.standard_price = 250.0
        self._age_last_manual_value(product, fields.Datetime.now() - relativedelta(years=1))

        product._update_standard_price()
        self.assertAlmostEqual(product.standard_price, 250.0)

    def test_normal_avco_receipts_unaffected(self):
        product = self.env['product.product'].create({
            **self.product_common_vals,
            'name': 'Avco Normal',
            'categ_id': self.category_avco_auto.id,
            'standard_price': 0.0,
        })
        self._make_in_move(product, 10, unit_cost=100.0)
        self._make_in_move(product, 10, unit_cost=200.0)

        product._update_standard_price()
        self.assertAlmostEqual(product.standard_price, 150.0)
