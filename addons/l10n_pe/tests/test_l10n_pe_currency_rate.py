from odoo import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPeCurrencyRate(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('pe')
    def setUpClass(cls):
        super().setUpClass()
        cls.other_currency = cls.setup_other_currency('USD', rates=[
            ('2016-01-01', 3.0),
            ('2017-01-01', 2.0),
        ])
        cls.invoice = cls._create_move('out_invoice', '2016-06-01')

    @classmethod
    def _create_move(cls, move_type, invoice_date, **kwargs):
        return cls.env['account.move'].create({
            'move_type': move_type,
            'partner_id': cls.partner_a.id,
            'invoice_date': invoice_date,
            'currency_id': cls.other_currency.id,
            'invoice_line_ids': [Command.create({'name': 'line', 'price_unit': 1200.0, 'tax_ids': []})],
            **kwargs,
        })

    def test_credit_note_uses_origin_invoice_currency_rate(self):
        credit_note = self._create_move('out_refund', '2017-06-01', reversed_entry_id=self.invoice.id)
        self.assertRecordValues(credit_note, [{
            'invoice_currency_rate': 3.0,
            'expected_currency_rate': 3.0,
            'amount_total_signed': -400.0,
        }])

    def test_debit_note_uses_origin_invoice_currency_rate(self):
        debit_note = self._create_move('out_invoice', '2017-06-01', debit_origin_id=self.invoice.id)
        self.assertRecordValues(debit_note, [{
            'invoice_currency_rate': 3.0,
            'expected_currency_rate': 3.0,
            'amount_total_signed': 400.0,
        }])

    def test_reversal_of_credit_note_uses_origin_invoice_currency_rate(self):
        credit_note = self._create_move('out_refund', '2017-06-01', reversed_entry_id=self.invoice.id)
        reversal = self._create_move('out_invoice', '2017-06-15', reversed_entry_id=credit_note.id)
        self.assertRecordValues(reversal, [{
            'invoice_currency_rate': 3.0,
            'expected_currency_rate': 3.0,
            'amount_total_signed': 400.0,
        }])

    def test_credit_note_linked_after_creation_uses_origin_invoice_currency_rate(self):
        credit_note = self._create_move('out_refund', '2017-06-01')
        self.assertRecordValues(credit_note, [{'invoice_currency_rate': 2.0, 'amount_total_signed': -600.0}])
        credit_note.reversed_entry_id = self.invoice
        self.assertRecordValues(credit_note, [{'invoice_currency_rate': 3.0, 'amount_total_signed': -400.0}])
