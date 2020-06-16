# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.exceptions import ValidationError
from odoo.tests import tagged

CH_IBAN = 'CH15 3881 5158 3845 3843 7'
QR_IBAN = 'CH21 3080 8001 2345 6782 7'


@tagged('post_install', '-at_install')
class TestSwissQR(AccountingTestCase):

    def setUp(self):
        super(TestSwissQR, self).setUp()
        # Activate SwissQR in Swiss invoices
        self.env['ir.config_parameter'].create(
            {'key': 'l10n_ch.print_qrcode', 'value': '1'}
        )
        self.customer = self.env['res.partner'].create(
            {
                "name": "Partner",
                "street": "Route de Berne 41",
                "street2": "",
                "zip": "1000",
                "city": "Lausanne",
                "country_id": self.env.ref("base.ch").id,
            }
        )
        self.env.user.company_id.partner_id.write(
            {
                "street": "Route de Berne 88",
                "street2": "",
                "zip": "2000",
                "city": "Neuchâtel",
                "country_id": self.env.ref('base.ch').id,
            }
        )
        self.invoice1 = self.create_invoice('base.CHF')
        sale_journal = self.env['account.journal'].search([("type", "=", "sale")])
        sale_journal.invoice_reference_model = "ch"

    def create_invoice(self, currency_to_use='base.CHF'):
        """ Generates a test invoice """

        product = self.env.ref("product.product_product_4")
        acc_type = self.env.ref('account.data_account_type_current_assets')
        account = self.env['account.account'].search(
            [('user_type_id', '=', acc_type.id)], limit=1
        )
        invoice = (
            self.env['account.move']
            .with_context(default_type='out_invoice')
            .create(
                {
                    'type': 'out_invoice',
                    'partner_id': self.customer.id,
                    'currency_id': self.env.ref(currency_to_use).id,
                    'date': time.strftime('%Y') + '-12-22',
                    'invoice_line_ids': [
                        (
                            0,
                            0,
                            {
                                'name': product.name,
                                'product_id': product.id,
                                'account_id': account.id,
                                'quantity': 1,
                                'price_unit': 42.0,
                            },
                        )
                    ],
                }
            )
        )

        return invoice

    def create_account(self, number):
        """ Generates a test res.partner.bank. """
        return self.env['res.partner.bank'].create(
            {
                'acc_number': number,
                'partner_id': self.env.user.company_id.partner_id.id,
            }
        )

    def swissqr_not_generated(self, invoice):
        """ Prints the given invoice and tests that no Swiss QR generation is triggered. """
        self.assertFalse(
            invoice.can_generate_qr_bill(),
            'No Swiss QR should be generated for this invoice',
        )

    def swissqr_generated(self, invoice, ref_type='NON'):
        """ Prints the given invoice and tests that a Swiss QR generation is triggered. """
        self.assertTrue(
            invoice.can_generate_qr_bill(), 'A Swiss QR can be generated'
        )

        if ref_type == 'QRR':
            self.assertTrue(invoice.invoice_payment_ref)
            struct_ref = invoice.invoice_payment_ref
            unstr_msg = invoice.ref or invoice.name or ''
        else:
            struct_ref = ''
            unstr_msg = invoice.invoice_payment_ref or invoice.ref or invoice.name or ''
        unstr_msg = (unstr_msg or invoice.number).replace('/', '%2F')

        payload = (
            "SPC%0A"
            "0200%0A"
            "1%0A"
            "{iban}%0A"
            "K%0A"
            "YourCompany%0A"
            "Route+de+Berne+88%0A"
            "2000+Neuch%C3%A2tel%0A"
            "%0A%0A"
            "CH%0A"
            "%0A%0A%0A%0A%0A%0A%0A"
            "42.00%0A"
            "CHF%0A"
            "K%0A"
            "Partner%0A"
            "Route+de+Berne+41%0A"
            "1000+Lausanne%0A"
            "%0A%0A"
            "CH%0A"
            "{ref_type}%0A"
            "{struct_ref}%0A"
            "{unstr_msg}%0A"
            "EPD"
        ).format(
            iban=invoice.invoice_partner_bank_id.sanitized_acc_number,
            ref_type=ref_type,
            struct_ref=struct_ref or '',
            unstr_msg=unstr_msg,
        )

        expected_url = ("/report/barcode/?type=QR&value={}"
                        "&width=256&height=256&quiet=1").format(payload)

        url = invoice.invoice_partner_bank_id.build_swiss_code_url(
            invoice.amount_residual,
            invoice.currency_id.name,
            None,
            invoice.partner_id,
            None,
            invoice.invoice_payment_ref,
            invoice.ref or invoice.name,
        )
        self.assertEqual(url, expected_url)

    def test_swissQR_missing_bank(self):
        # Let us test the generation of a SwissQR for an invoice, first by showing an
        # QR is included in the invoice is only generated when Odoo has all the data it needs.
        self.invoice1.post()
        self.swissqr_not_generated(self.invoice1)

    def test_swissQR_iban(self):
        # Now we add an account for payment to our invoice
        # Here we don't use a structured reference
        iban_account = self.create_account(CH_IBAN)
        self.invoice1.invoice_partner_bank_id = iban_account
        self.invoice1.post()
        self.swissqr_generated(self.invoice1, ref_type="NON")

    def test_swissQR_qriban(self):
        # Now use a proper QR-IBAN, we are good to print a QR Bill
        qriban_account = self.create_account(QR_IBAN)
        self.assertTrue(qriban_account.acc_type, 'qr-iban')
        self.invoice1.invoice_partner_bank_id = qriban_account
        self.invoice1.post()
        self.swissqr_generated(self.invoice1, ref_type="QRR")
