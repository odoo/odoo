from odoo import Command, fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools import SQL
from freezegun import freeze_time


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestAccountMoveSyncTaxLines(AccountTestInvoicingCommon):

    _test_user_groups = None  # FIXME list needed groups

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
        """ Test that changing the delivery_date (which sets the taxable supply date, the exchange rate date in Hungary)
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

        # The taxable supply date, not the delivery date, defines the currency rate
        out_invoice.taxable_supply_date = '2024-01-30'
        self.assertRecordValues(out_invoice, [
            {'delivery_date': fields.Date.from_string('2024-01-31'), 'invoice_currency_rate': 2.0, 'expected_currency_rate': 2.0},
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
        self.env.execute_query(SQL(" UPDATE account_move SET create_date = '2026-06-02' where id  = %s", invoice1.id))
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

    @freeze_time('2026-06-03')
    def test_taxable_supply_date_at_post(self):
        """ At posting, the taxable supply date is set from the delivery date, or the invoice date, and it defines the
        accounting date.
        """
        invoices = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({'quantity': 1, 'price_unit': 60})],
            **dates,
        } for dates in ({'invoice_date': '2026-06-02', 'delivery_date': '2026-06-01'}, {'invoice_date': '2026-06-02'}, {}, {'invoice_date': '2026-05-15'})])
        self.assertRecordValues(invoices, [
            {'taxable_supply_date': fields.Date.from_string('2026-06-01'), 'date': fields.Date.from_string('2026-06-01')},
            {'taxable_supply_date': False, 'date': fields.Date.from_string('2026-06-02')},
            {'taxable_supply_date': False, 'date': fields.Date.from_string('2026-06-03')},
            {'taxable_supply_date': False, 'date': fields.Date.from_string('2026-05-15')},
        ])

        self.env.company.fiscalyear_lock_date = '2026-05-31'
        invoices.action_post()
        self.assertRecordValues(invoices, [
            {'taxable_supply_date': fields.Date.from_string('2026-06-01'), 'date': fields.Date.from_string('2026-06-01')},
            {'taxable_supply_date': fields.Date.from_string('2026-06-02'), 'date': fields.Date.from_string('2026-06-02')},
            {'taxable_supply_date': fields.Date.from_string('2026-06-03'), 'date': fields.Date.from_string('2026-06-03')},
            # The accounting date of a locked period is moved to the first open date
            {'taxable_supply_date': fields.Date.from_string('2026-05-15'), 'date': fields.Date.from_string('2026-06-03')},
        ])

    @freeze_time('2026-06-03')
    def test_taxable_supply_date_at_post_currency_rate(self):
        """ Setting the taxable supply date at posting keeps a manually changed currency rate, otherwise it uses the
        currency rate of the taxable supply date.
        """
        invoices = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({'quantity': 1, 'price_unit': 60})],
            'currency_id': self.other_currency.id,
        } for _i in range(2)])
        self.env.execute_query(SQL("UPDATE account_move SET create_date = '2026-06-03' WHERE id IN %s", tuple(invoices.ids)))
        invoices.invalidate_recordset(['create_date'])
        invoices[0].invoice_currency_rate = 5
        with freeze_time('2026-06-04'):
            invoices.action_post()
        self.assertRecordValues(invoices, [
            {'taxable_supply_date': fields.Date.from_string('2026-06-04'), 'invoice_currency_rate': 5.0},
            {'taxable_supply_date': fields.Date.from_string('2026-06-04'), 'invoice_currency_rate': 3.0},
        ])

    @freeze_time('2026-06-01')
    def test_vendor_bill_accounting_date(self):
        """ The VAT of a bill can only be deducted once both the supply and the bill are received: its accounting date is
        the latest of the taxable supply date and the bill date.
        """
        bills = self.env['account.move'].create([{
            'move_type': move_type,
            'partner_id': self.partner_a.id,
            'invoice_date': invoice_date,
            'taxable_supply_date': taxable_supply_date,
            'invoice_line_ids': [Command.create({'quantity': 1, 'price_unit': 60})],
        } for move_type, invoice_date, taxable_supply_date in (
            ('in_invoice', '2026-06-10', '2026-06-20'),
            ('in_refund', '2026-06-20', '2026-06-10'),
        )])
        self.assertRecordValues(bills, [
            {'date': fields.Date.from_string('2026-06-20')},
            {'date': fields.Date.from_string('2026-06-20')},
        ])

    @freeze_time('2026-06-04')
    def test_credit_note_currency_rate(self):
        """ A credit note copies the currency rate of the original invoice, but its currency rate date is its own
        invoice date, not the taxable supply date.
        """
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2026-06-03',
            'taxable_supply_date': '2026-06-02',
            'invoice_line_ids': [Command.create({'quantity': 1, 'price_unit': 60})],
            'currency_id': self.other_currency.id,
        })
        invoice.action_post()
        credit_note = self._reverse_invoice(invoice, date='2026-06-04')
        self.assertRecordValues(credit_note, [{
            'taxable_supply_date': fields.Date.from_string('2026-06-02'),
            'date': fields.Date.from_string('2026-06-04'),
            'invoice_currency_rate': invoice.invoice_currency_rate,
        }])

        credit_note.invoice_date = '2026-06-03'
        self.assertRecordValues(credit_note, [{'date': fields.Date.from_string('2026-06-03'), 'invoice_currency_rate': 2.0}])
