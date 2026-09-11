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
        cls.other_currency = cls.setup_other_currency('EUR', rates=[
            ('2026-06-01', 1),
            ('2026-06-02', 2),
            ('2026-06-03', 3)])

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
        self.assertRecordValues(out_invoice, [
            {'invoice_currency_rate': 3.0, 'expected_currency_rate': 3.0}
        ])
        self.assertRecordValues(lines, [
            {'amount_currency': -10000.0, 'balance': -3333.33},
            {'amount_currency': -2700.0, 'balance': -900.0},
            {'amount_currency': 12700.0, 'balance': 3333.33 + 900.0},
        ])

    @freeze_time('2026-06-02')
    def test_currency_rate_manual_change(self):
        """
        Ensure that if invoice_currency_rate is manually set and invoice_date is not set,
        posting the invoice doesn't change the currency rate back to default
        """
        invoice1 = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'invoice_date': False,
            'delivery_date': '2026-06-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({'quantity': 1, 'price_unit': 60})],
            'currency_id': self.other_currency.id,
        }])
        self.assertEqual(invoice1.invoice_currency_rate, 1.0)
        self.env.cr.execute(f""" UPDATE account_move SET create_date = '2026-06-02' where id  = {invoice1.id}""")
        invoice1.invalidate_recordset(['create_date'])
        # currency rate of the invoice creation date that will be computed on action_post
        invoice1.invoice_currency_rate = 2
        invoice1.action_post()
        self.assertRecordValues(invoice1.line_ids, [
            {'amount_currency':   -60.0, 'balance':   -30.0},  # Product line
            {'amount_currency':    60.0, 'balance':    30.0},  # Receivable line
        ])
        invoice1.button_draft()
        invoice1.invoice_date = False
        invoice1.invoice_currency_rate = 2
        with freeze_time('2026-06-03'):
            invoice1.action_post()
        self.assertRecordValues(invoice1.line_ids, [
            {'amount_currency':   -60.0, 'balance':   -30.0},  # Product line
            {'amount_currency':    60.0, 'balance':    30.0},  # Receivable line
        ])
