# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.exceptions import ValidationError
from odoo.tests import tagged

CH_IBAN = 'CH15 3881 5158 3845 3843 7'
QR_IBAN = 'CH21 3080 8001 2345 6782 7'

@tagged('post_install', '-at_install')
class SwissQRTest(AccountingTestCase):

    def setUp(self):
        super(SwissQRTest, self).setUp()
        # Activate SwissQR in Swiss invoices
        self.env['ir.config_parameter'].create({
            'key': 'l10n_ch.print_qrcode',
            'value': '1',
        })
        self.env.ref("base.res_partner_2").country_id = self.env.ref('base.ch')
        self.env.user.company_id.partner_id.country_id = self.env.ref('base.ch')

    def create_invoice(self, currency_to_use='base.CHF'):
        """ Generates a test invoice """
        invoice = self.env['account.move'].with_context(default_type='out_invoice').create({
            'type': 'out_invoice',
            'partner_id': self.env.ref("base.res_partner_2").id,
            'currency_id': self.env.ref(currency_to_use).id,
            'invoice_date': time.strftime('%Y') + '-12-22',
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': self.env.ref("product.product_product_4").id,
                    'quantity': 1,
                    'price_unit': 42,
                }),
            ],
        })
        invoice.post()

        return invoice

    def create_account(self, number):
        """ Generates a test res.partner.bank. """
        return self.env['res.partner.bank'].create({
            'acc_number': number,
            'partner_id': self.env.user.company_id.partner_id.id,
        })

    def print_isr(self, invoice):
        try:
            invoice.isr_print()
            return True
        except ValidationError:
            return False

    def swissqr_not_generated(self, invoice):
        """ Prints the given invoice and tests that no Swiss QR generation is triggered. """
        self.assertFalse(invoice.validate_swiss_code_arguments(), 'No Swiss QR should be generated for this invoice')

    def swissqr_generated(self, invoice):
        """ Prints the given invoice and tests that a Swiss QR generation is triggered. """
        self.assertTrue(invoice.validate_swiss_code_arguments(), 'A Swiss QR can be generated')
        expected_url = (
            '/report/barcode/?type=QR&value='
            'SPC%0A0200%0A1%0ACH2130808001234567827%0A'
            'YourCompany%0AK%0A250+Executive+Park+Blvd%2C+Suite+3400%0A'
            '94134+San+Francisco%0A%0A%0ACH%0A%0A%0A%0A%0A%0A%0A%0A'
            '42.0%0ACHF%0ADeco+Addict%0AK%0A325+Elsie+Drive%0A26807+Franklin%0A'
            '%0A%0ACH%0AQRR%0A{}%0A{}%0AEPD%0A'
            '&width=256&height=256&humanreadable=1').format(
                    invoice.l10n_ch_isr_number, invoice.name.replace('/', '%2F'))
        url = invoice.build_swiss_code_url()
        self.assertEqual(url, expected_url)

    def test_swissQR(self):
        #Let us test the generation of a SwissQR for an invoice, first by showing an
        #QR is included in the invoice is only generated when Odoo has all the data it needs.
        invoice_1 = self.create_invoice('base.CHF')
        self.swissqr_not_generated(invoice_1)

        #Now we add an account for payment to our invoice, but still cannot generate the QR
        iban_account = self.create_account(CH_IBAN)
        invoice_1.invoice_partner_bank_id = iban_account
        self.swissqr_not_generated(invoice_1)

        #Now use a proper QR-IBAN, but still cannot generate the QR
        iban_account = self.create_account(QR_IBAN)
        self.assertTrue(iban_account.acc_type, 'qr-iban')
        self.swissqr_not_generated(invoice_1)

        #Finally, we use add an ISR subscription number. The Swiss QR should now be available to generate
        iban_account.l10n_ch_isr_subscription_chf = '010391391'
        invoice_1.invoice_partner_bank_id = iban_account
        self.swissqr_generated(invoice_1)
