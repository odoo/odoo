# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form, tagged
from odoo.addons.l10n_hu_edi.tests.common import L10nHuEdiTestCommon


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestL10nHuEdiPaymentMode(L10nHuEdiTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cash_journal = cls.env['account.journal'].create({'name': 'Cash', 'type': 'cash', 'code': 'TCSH'})
        cls.cash_method_line = cls.cash_journal.inbound_payment_method_line_ids[:1]
        cls.bank_method_line = cls.company_data['default_journal_bank'].inbound_payment_method_line_ids[:1]
        cls.cash_rounding_5 = cls.env['account.cash.rounding'].create({
            'name': 'Rounding to 5 HUF',
            'rounding': 5.0,
            'currency_ids': cls.env.ref('base.HUF').ids,
            'payment_method_line_ids': cls.cash_journal.inbound_payment_method_line_ids.ids,
        })

    def test_payment_mode_follows_payment_method(self):
        invoice = self.create_invoice_simple()
        with Form(invoice) as invoice_form:
            invoice_form.preferred_payment_method_line_id = self.cash_method_line
            self.assertEqual(invoice_form.l10n_hu_payment_mode, 'CASH')
            invoice_form.preferred_payment_method_line_id = self.bank_method_line
            self.assertEqual(invoice_form.l10n_hu_payment_mode, 'TRANSFER')
            # Card payments are received on the bank journal: the payment mode can still be set by hand.
            invoice_form.l10n_hu_payment_mode = 'CARD'
        self.assertEqual(invoice.l10n_hu_payment_mode, 'CARD')

    def test_payment_mode_kept(self):
        """ Invoices sent to NAV and vendor bills keep their payment mode. """
        invoice = self.create_invoice_simple()
        invoice.write({'preferred_payment_method_line_id': self.cash_method_line.id})
        invoice.action_post()
        self.assertEqual(invoice.l10n_hu_payment_mode, 'CASH')
        invoice.l10n_hu_edi_state = 'confirmed'
        invoice.preferred_payment_method_line_id = self.bank_method_line
        self.assertEqual(invoice.l10n_hu_payment_mode, 'CASH')

        bill = self.create_bill_simple()
        bill.write({'l10n_hu_payment_mode': 'TRANSFER'})
        bill.preferred_payment_method_line_id = self.cash_journal.outbound_payment_method_line_ids[:1]
        self.assertEqual(bill.l10n_hu_payment_mode, 'TRANSFER')

    def test_payment_mode_cash_rounding(self):
        """ Invoices in cash get the cash rounding of the cash journals, whichever of the payment method or the NAV
        payment mode is set. """
        self.env.user.group_ids += self.env.ref('account.group_cash_rounding')
        invoice_payment_method, invoice_cash, invoice_transfer = (self.create_invoice_simple(amount=1002.0) for _i in range(3))
        with Form(invoice_payment_method) as invoice_form:
            invoice_form.preferred_payment_method_line_id = self.cash_method_line
        with Form(invoice_cash) as invoice_form:
            invoice_form.l10n_hu_payment_mode = 'CASH'
        with Form(invoice_transfer) as invoice_form:
            invoice_form.l10n_hu_payment_mode = 'TRANSFER'

        self.assertEqual((invoice_payment_method | invoice_cash).invoice_cash_rounding_id, self.cash_rounding_5)
        self.assertFalse(invoice_transfer.invoice_cash_rounding_id)
        for invoice in invoice_payment_method | invoice_cash:
            self.assertTrue(invoice.currency_id.is_zero(invoice.amount_total % 5))
