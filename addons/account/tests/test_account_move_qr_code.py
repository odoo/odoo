# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon


@tagged('post_install', '-at_install')
class TestAccountMoveQrCode(TestAccountMoveSendCommon):
    """ The QR-code methods are provided by other modules: a fake one is used here, eligible
    in the company currency only, and requiring the city of the customer.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_currency = cls.setup_other_currency('EUR')
        cls.company_data['company'].qr_code = True
        cls.bank_account = cls.env['res.partner.bank'].create({
            'account_number': 'BE15001559627230',
            'allow_out_payment': True,
            'partner_id': cls.company_data['company'].partner_id.id,
        })
        cls.partner_a.city = 'Ramillies'

        ResPartnerBank = cls.registry['res.partner.bank']

        def _get_available_qr_methods(self):
            return [('test_qr', "Test QR", 10)]

        def _get_error_messages_for_qr(self, qr_method, debtor_partner, currency):
            if currency != self.env.company.currency_id:
                return "The test QR-code only supports the company currency."
            return None

        def _check_for_qr_code_errors(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
            if not debtor_partner.city:
                return "The test QR-code needs the city of the customer."
            return None

        def _get_qr_code_base64(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
            return f'qr:{qr_method}'

        for method in (_get_available_qr_methods, _get_error_messages_for_qr, _check_for_qr_code_errors, _get_qr_code_base64):
            cls.startClassPatcher(patch.object(ResPartnerBank, method.__name__, method))

    def _create_qr_invoice(self, partner=None, **invoice_args):
        return self._create_invoice(
            partner_id=(partner or self.partner_a).id,
            partner_bank_id=self.bank_account.id,
            invoice_line_ids=[self._prepare_invoice_line(price_unit=100)],
            post=True,
            **invoice_args,
        )

    def _get_qr_code_urls(self, invoice, **data):
        report_values = self.env['report.account.report_invoice']._get_report_values(invoice.ids, data={'report_type': 'pdf', **data})
        return report_values['qr_code_urls']

    def test_qr_code_method_follows_invoice_data(self):
        """ The method is picked from the current data of the invoice each time: once printed with
        a QR-code, an invoice whose currency changes to one no method supports has no QR-code anymore.
        """
        invoice = self._create_qr_invoice()
        self.assertEqual(invoice._get_qr_code_method(), 'test_qr')
        self.assertEqual(self._get_qr_code_urls(invoice), {invoice.id: 'qr:test_qr'})

        invoice.button_draft()
        invoice.currency_id = self.other_currency
        invoice.action_post()
        self.assertFalse(invoice._get_qr_code_method())
        self.assertEqual(self._get_qr_code_urls(invoice), {})

    def test_qr_code_missing_data(self):
        """ An eligible method with missing data blocks printing and sending, but not the customer
        portal nor the proforma.
        """
        self.partner_a.city = False
        invoice = self._create_qr_invoice()

        with self.assertRaisesRegex(UserError, "needs the city of the customer"):
            self._get_qr_code_urls(invoice)
        self.assertEqual(self._get_qr_code_urls(invoice, report_type='html'), {})
        self.assertEqual(self._get_qr_code_urls(invoice, proforma=True), {})

        wizard = self.create_send_and_print(invoice)
        with self.assertRaisesRegex(UserError, "needs the city of the customer"):
            wizard.action_send_and_print()

        # Sent in batch, the error is logged on the invoice instead of failing the whole batch
        self.partner_b.city = 'Ramillies'
        other_invoice = self._create_qr_invoice(partner=self.partner_b)
        self.create_send_and_print(invoice + other_invoice).action_send_and_print()
        with self.enter_registry_test_mode():
            self.env.ref('account.ir_cron_account_move_send').method_direct_trigger()
        self.assertFalse(invoice.invoice_pdf_report_id)
        self.assertIn("needs the city of the customer", self._get_mail_message(invoice).body)
        self.assertTrue(other_invoice.invoice_pdf_report_id)

    def test_qr_code_nothing_left_to_pay(self):
        """ A paid invoice has no QR-code, so its data is not checked. """
        self.partner_a.city = False
        invoice = self._create_qr_invoice()
        self._register_payment(invoice)

        self.assertFalse(invoice._get_qr_code_method())
        self.assertEqual(self._get_qr_code_urls(invoice), {})
