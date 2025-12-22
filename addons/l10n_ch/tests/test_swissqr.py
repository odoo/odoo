# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools.misc import mod10r

CH_IBAN = 'CH15 3881 5158 3845 3843 7'
QR_IBAN = 'CH21 3080 8001 2345 6782 7'


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSwissQR(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('ch')
    def setUpClass(cls):
        super().setUpClass()

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

        account = self.env['account.account'].search(
            [('account_type', '=', 'asset_current')], limit=1
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
        self.assertTrue(
            invoice.partner_bank_id._get_error_messages_for_qr('ch_qr', invoice.partner_id, invoice.currency_id),
            'No Swiss QR should be generated for this invoice',
        )

    def swissqr_generated(self, invoice, ref_type='NON'):
        """ Ensure correct params for Swiss QR generation. """

        self.assertFalse(
            invoice.partner_bank_id._get_error_messages_for_qr('ch_qr', invoice.partner_id, invoice.currency_id), 'A Swiss QR can be generated'
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
            "S\n"
            "company_1_data\n"
            "Route de Berne\n"
            "88\n"
            "2000\n"
            "Neuchâtel\n"
            "CH\n"
            "\n\n\n\n\n\n\n"
            "42.00\n"
            "CHF\n"
            "S\n"
            "Partner\n"
            "Route de Berne\n"
            "41\n"
            "1000\n"
            "Lausanne\n"
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

    def test_swiss_order_reference_qrr_for_qr_code(self):
        """
        Test that the order reference is correctly generated for QR-Code
        We summon the skipTest if Sale is not installed (instead of creating a whole module for one test)
        """
        if 'sale.order' not in self.env:
            self.skipTest('`sale` is not installed')

        payment_custom = self.env['ir.module.module']._get('payment_custom')
        if payment_custom.state != 'installed':
            self.skipTest("payment_custom module is not installed")

        provider = self.env['payment.provider'].create({
            'name': 'Test',
            'code': 'custom',
        })
        invoice_journal = self.env['account.journal'].search(
            [('type', '=', 'sale'), ('company_id', '=', self.env.company.id)], limit=1)
        invoice_journal.write({'invoice_reference_model': 'ch'})
        order = self.env['sale.order'].create({
            'name': "S00001",
            'partner_id': self.env['res.partner'].search([("name", '=', 'Partner')])[0].id,
            'order_line': [
                (0, 0, {'product_id': self.product_a.id, 'price_unit': 100}),
            ],
        })
        payment_transaction = self.env['payment.transaction'].create({
            'provider_id': provider.id,
            'payment_method_id': self.env.ref('payment.payment_method_unknown').id,
            'sale_order_ids': [order.id],
            'partner_id': self.env['res.partner'].search([("name", '=', 'Partner')])[0].id,
            'amount': 100,
            'currency_id': self.env.company.currency_id.id,
        })
        payment_transaction._set_pending()

        self.assertEqual(order.reference, mod10r(order.reference[:-1]))
