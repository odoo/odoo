from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from freezegun import freeze_time


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestAccountMoveSyncTaxLines(AccountTestInvoicingCommon):

    _test_groups = None  # FIXME list needed groups

    @classmethod
    @AccountTestInvoicingCommon.setup_country('hu')
    def setUpClass(cls):
        super().setUpClass()

        cls.tax_vat = cls.env['account.chart.template'].ref('F27')

    @freeze_time('2024-01-31')
    def test_delivery_date_currency_rate_sync(self):
        """ Test that changing the delivery_date (the exchange rate date in Hungary)
        correctly triggers a recomputation of the currency rate and
        synchronizes the journal items' balances.
        """
        currency_usd = self.setup_other_currency('USD', rates=[
            ('1900-01-01', 1.0),
            ('2024-01-29', 2.0),
            ('2024-01-30', 3.0),
        ])
        out_invoice = self._create_invoice_one_line(price_unit=10000, tax_ids=self.tax_vat, currency_id=currency_usd)

        lines = out_invoice.line_ids
        self.assertRecordValues(out_invoice, [
            {'invoice_currency_rate': 3.0, 'expected_currency_rate': 3.0, 'delivery_date': False}
        ])
        self.assertRecordValues(lines, [
            {'amount_currency': -10000.0, 'balance': -3333.33},
            {'amount_currency': -2700.0, 'balance': -900.0},
            {'amount_currency': 12700.0, 'balance': 3333.33 + 900.0},
        ])

        out_invoice.delivery_date = '2024-01-30'
        self.assertRecordValues(out_invoice, [
            {'invoice_currency_rate': 2.0, 'expected_currency_rate': 2.0}
        ])
        self.assertRecordValues(lines, [
            {'amount_currency': -10000.0, 'balance': -5000.0},
            {'amount_currency': -2700.0, 'balance': -1350.0},
            {'amount_currency': 12700.0, 'balance': 5000.0 + 1350.0},
        ])

        out_invoice.delivery_date = '2024-01-31'
        self.assertRecordValues(out_invoice, [
            {'invoice_currency_rate': 3.0, 'expected_currency_rate': 3.0}
        ])
        self.assertRecordValues(lines, [
            {'amount_currency': -10000.0, 'balance': -3333.33},
            {'amount_currency': -2700.0, 'balance': -900.0},
            {'amount_currency': 12700.0, 'balance': 3333.33 + 900.0},
        ])
