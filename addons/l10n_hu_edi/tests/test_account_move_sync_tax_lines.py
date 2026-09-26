from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from freezegun import freeze_time


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestAccountMoveSyncTaxLines(AccountTestInvoicingCommon):

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
            ('2024-01-30', 2.0),
            ('2024-01-31', 3.0),
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
        # Known limitation: invoice_currency_rate is not updated here because 2.0
        # (the rate set from the previous delivery_date) no longer matches the
        # invoice_date rate (3.0), so it cannot be distinguished from a manually-edited rate.
        self.assertRecordValues(out_invoice, [
            {'invoice_currency_rate': 2.0, 'expected_currency_rate': 3.0}
        ])
        self.assertRecordValues(lines, [
            {'amount_currency': -10000.0, 'balance': -5000.0},
            {'amount_currency': -2700.0, 'balance': -1350.0},
            {'amount_currency': 12700.0, 'balance': 5000.0 + 1350.0},
        ])

    @freeze_time('2024-01-31')
    def test_delivery_date_currency_rate_set_at_creation(self):
        """ Test that changing the delivery_date (the exchange rate date in Hungary)
        correctly triggers a recomputation of the currency rate even when the
        delivery_date was set before creation of invoice (e.g. first save).
        """
        currency_usd = self.setup_other_currency('USD', rates=[
            ('1900-01-01', 1.0),
            ('2024-01-30', 2.0),  # delivery_date rate
            ('2024-01-31', 3.0),  # invoice_date / today rate
        ])

        # Simulate webclient create: invoice_currency_rate=3.0 is explicitly sent in vals
        out_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': self.company_data['default_journal_sale'].id,
            'partner_id': self.partner_a.id,
            'currency_id': currency_usd.id,
            'invoice_date': '2024-01-31',
            'delivery_date': '2024-01-30',
            'invoice_currency_rate': 3.0,  # wrong rate from invoice_date — triggers ORM protection
            'invoice_line_ids': [Command.create({
                'name': 'Test line',
                'price_unit': 10000,
                'tax_ids': [Command.set(self.tax_vat.ids)],
            })],
        })

        self.assertRecordValues(out_invoice, [
            {'invoice_currency_rate': 2.0, 'expected_currency_rate': 2.0}
        ])

    @freeze_time('2024-01-31')
    def test_delivery_date_currency_rate_manual_not_overwritten(self):
        """ Test that when the user manually edits invoice_currency_rate,
        subsequently changing delivery_date does NOT overwrite that manual rate.
        """
        currency_usd = self.setup_other_currency('USD', rates=[
            ('1900-01-01', 1.0),
            ('2024-01-30', 2.0),
            ('2024-01-31', 3.0),
        ])

        out_invoice = self._create_invoice_one_line(
            price_unit=10000,
            tax_ids=self.tax_vat,
            currency_id=currency_usd,
            invoice_date='2024-01-31',
        )

        # Simulate webclient write: user manually set rate to 5.0, then also sets delivery_date.
        manual_rate = 5.0
        out_invoice.write({
            'delivery_date': '2024-01-30',
            'invoice_currency_rate': manual_rate,
        })

        # Manual rate should be preserved (5.0 != invoice_date rate 3.0, so set by user).
        self.assertRecordValues(out_invoice, [
            {'invoice_currency_rate': manual_rate, 'expected_currency_rate': 2.0}
        ])
