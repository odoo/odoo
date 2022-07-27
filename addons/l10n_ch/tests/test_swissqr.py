# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged

CH_IBAN = 'CH15 3881 5158 3845 3843 7'
QR_IBAN = 'CH21 3080 8001 2345 6782 7'


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSwissQR(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_ch.l10nch_chart_template'):
        super().setUpClass(chart_template_ref=chart_template_ref)

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
        self.product = self.env['product.product'].create({
            'name': 'Customizable Desk',
        })
        self.invoice1 = self.create_invoice('base.CHF')
        sale_journal = self.env['account.journal'].search([("type", "=", "sale")])
        sale_journal.invoice_reference_model = "ch"

    def create_invoice(self, currency_to_use='base.CHF'):
        """ Generates a test invoice """

        acc_type = self.env.ref('account.data_account_type_current_assets')
        account = self.env['account.account'].search(
            [('user_type_id', '=', acc_type.id)], limit=1
        )
        invoice = (
            self.env['account.move']
            .create(
                {
                    'move_type': 'out_invoice',
                    'partner_id': self.customer.id,
                    'currency_id': self.env.ref(currency_to_use).id,
                    'date': time.strftime('%Y') + '-12-22',
                    'invoice_line_ids': [
                        (
                            0,
                            0,
                            {
                                'name': self.product.name,
                                'product_id': self.product.id,
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
            invoice.partner_bank_id._eligible_for_qr_code('ch_qr', invoice.partner_id, invoice.currency_id),
            'No Swiss QR should be generated for this invoice',
        )

    def swissqr_generated(self, invoice, ref_type='NON'):
        """ Ensure correct params for Swiss QR generation. """

        self.assertTrue(
            invoice.partner_bank_id._eligible_for_qr_code('ch_qr', invoice.partner_id, invoice.currency_id), 'A Swiss QR can be generated'
        )

        if ref_type == 'QRR':
            self.assertTrue(invoice.payment_reference)
            struct_ref = invoice.payment_reference
            unstr_msg = invoice.ref or invoice.name or ''
        else:
            struct_ref = ''
            unstr_msg = invoice.payment_reference or invoice.ref or invoice.name or ''
        unstr_msg = unstr_msg or invoice.number

        payload = (
            "SPC\n"
            "0200\n"
            "1\n"
            "{iban}\n"
            "K\n"
            "company_1_data\n"
            "Route de Berne 88\n"
            "2000 Neuchâtel\n"
            "\n\n"
            "CH\n"
            "\n\n\n\n\n\n\n"
            "42.00\n"
            "CHF\n"
            "K\n"
            "Partner\n"
            "Route de Berne 41\n"
            "1000 Lausanne\n"
            "\n\n"
            "CH\n"
            "{ref_type}\n"
            "{struct_ref}\n"
            "{unstr_msg}\n"
            "EPD"
        ).format(
            iban=invoice.partner_bank_id.sanitized_acc_number,
            ref_type=ref_type,
            struct_ref=struct_ref or '',
            unstr_msg=unstr_msg,
        )

        expected_params = {
            'barcode_type': 'QR',
            'barLevel': 'M',
            'width': 256,
            'height': 256,
            'quiet': 1,
            'mask': 'ch_cross',
            'value': payload,
        }

        params = invoice.partner_bank_id._get_qr_code_generation_params(
            'ch_qr', 42.0, invoice.currency_id, invoice.partner_id, unstr_msg, struct_ref
        )

        self.assertEqual(params, expected_params)

    def test_swissQR_missing_bank(self):
        # Let us test the generation of a SwissQR for an invoice, first by showing an
        # QR is included in the invoice is only generated when Odoo has all the data it needs.
        self.invoice1.action_post()
        self.swissqr_not_generated(self.invoice1)

    def test_swissQR_iban(self):
        # Now we add an account for payment to our invoice
        # Here we don't use a structured reference
        iban_account = self.create_account(CH_IBAN)
        self.invoice1.partner_bank_id = iban_account
        self.invoice1.action_post()
        self.swissqr_generated(self.invoice1, ref_type="NON")

    def test_swissQR_qriban(self):
        # Now use a proper QR-IBAN, we are good to print a QR Bill
        qriban_account = self.create_account(QR_IBAN)
        self.assertTrue(qriban_account.l10n_ch_qr_iban)
        self.invoice1.partner_bank_id = qriban_account
        self.invoice1.action_post()
        self.swissqr_generated(self.invoice1, ref_type="QRR")
