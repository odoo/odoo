# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestFlatRateScheme(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_chart_template('uk')
    def setUpClass(cls):
        super().setUpClass()
        ChartTemplate = cls.env['account.chart.template']
        cls.fiscal_position_frs = ChartTemplate.ref('account_fiscal_position_flat_rate_scheme')
        cls.tax_purchase_goods = ChartTemplate.ref('PT_20_G')
        cls.tax_purchase_services = ChartTemplate.ref('PT_20_S')
        cls.tax_purchase_capital_goods = ChartTemplate.ref('PT_20_FRS')
        cls.tax_purchase_irrecoverable = ChartTemplate.ref('PT_20_FRS_IRRECOVERABLE')

        cls.product_goods = cls._create_product(name='Goods', type='consu')
        cls.product_service = cls._create_product(name='Service', type='service')

    def _create_bill(self, price_unit, product=None):
        return self._create_invoice_one_line(
            move_type='in_invoice',
            price_unit=price_unit,
            product_id=product,
            tax_ids=self.tax_purchase_capital_goods,
            invoice_date='2025-01-15',
        )

    def test_frs_fiscal_position_maps_purchase_taxes(self):
        for tax in self.tax_purchase_goods + self.tax_purchase_services:
            with self.subTest(tax=tax.name):
                self.assertEqual(self.fiscal_position_frs.map_tax(tax), self.tax_purchase_irrecoverable)

    def test_frs_irrecoverable_tax_is_expensed(self):
        bill = self._create_invoice_one_line(
            move_type='in_invoice',
            price_unit=100.0,
            tax_ids=self.tax_purchase_irrecoverable,
            invoice_date='2025-01-15',
            post=True,
        )
        tax_line = bill.line_ids.filtered('tax_line_id')
        self.assertRecordValues(tax_line, [{
            'account_id': self.env['account.chart.template'].ref('695000').id,
            'balance': 20.0,
            'tax_tag_ids': [],
        }])

    def test_frs_capital_goods_reclaim_valid(self):
        bill = self._create_bill(2500.0, product=self.product_goods)
        action = bill.action_post()
        self.assertEqual(bill.state, 'posted')
        self.assertFalse(action and action.get('tag') == 'display_notification')

    def test_frs_capital_goods_reclaim_warning(self):
        for name, price_unit, product in (
            ("goods below £2,000 including VAT", 1500.0, self.product_goods),
            ("service", 2500.0, self.product_service),
            ("no product", 2500.0, None),
        ):
            with self.subTest(name):
                bill = self._create_bill(price_unit, product=product)
                action = bill.action_post()
                self.assertEqual(bill.state, 'posted')
                self.assertEqual(action['tag'], 'display_notification')
                self.assertIn(bill.display_name, action['params']['message'])
