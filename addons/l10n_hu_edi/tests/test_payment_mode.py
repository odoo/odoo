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

    def test_payment_mode_from_payment_method(self):
        """ Without NAV payment mode, the one of the journal of the payment method is sent to NAV. """
        invoice = self.create_invoice_simple()
        for payment_method_line, payment_mode in ((self.cash_method_line, 'CASH'), (self.bank_method_line, 'TRANSFER')):
            with self.subTest(payment_mode=payment_mode):
                invoice.preferred_payment_method_line_id = payment_method_line
                self.assertEqual(invoice._l10n_hu_edi_get_payment_mode(), payment_mode)
        self.assertFalse(invoice.l10n_hu_payment_mode)

        invoice.preferred_payment_method_line_id = self.cash_method_line
        invoice.action_post()
        self.assertIn(b'<paymentMethod>CASH</paymentMethod>', invoice._l10n_hu_edi_generate_xml())
        report = self.env['ir.actions.report']._render_qweb_html('account.account_invoices', invoice.ids)[0]
        self.assertIn(b'Payment Mode', report)
        self.assertIn(b'Cash', report)

    def test_payment_mode_set_by_hand(self):
        """ A payment mode set by hand is kept, whatever the payment method; vendor bills keep the one of the vendor. """
        invoice = self.create_invoice_simple()
        invoice.write({'l10n_hu_payment_mode': 'CARD', 'preferred_payment_method_line_id': self.bank_method_line.id})
        invoice.preferred_payment_method_line_id = self.cash_method_line
        self.assertEqual(invoice.l10n_hu_payment_mode, 'CARD')
        self.assertEqual(invoice._l10n_hu_edi_get_payment_mode(), 'CARD')

        bill = self.create_bill_simple()
        bill.preferred_payment_method_line_id = self.cash_journal.outbound_payment_method_line_ids[:1]
        self.assertFalse(bill._l10n_hu_edi_get_payment_mode())

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
