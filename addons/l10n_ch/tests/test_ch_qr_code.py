# -*- coding:utf-8 -*-

from odoo import Command
from odoo.tests import tagged
from odoo.exceptions import UserError
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSwissQRCode(AccountTestInvoicingCommon):
    """ Tests the generation of Swiss QR-codes on invoices
    """

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_ch.l10nch_chart_template'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.company_data['company'].qr_code = True
        cls.company_data['company'].country_id = None

        cls.swiss_iban = cls.env['res.partner.bank'].create({
            'acc_number': 'CH15 3881 5158 3845 3843 7',
            'partner_id': cls.company_data['company'].partner_id.id,
        })

        cls.swiss_qr_iban = cls.env['res.partner.bank'].create({
            'acc_number': 'CH21 3080 8001 2345 6782 7',
            'partner_id': cls.company_data['company'].partner_id.id,
        })

        cls.ch_qr_invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'currency_id': cls.env.ref('base.CHF').id,
            'partner_bank_id': cls.swiss_iban.id,
            'company_id': cls.company_data['company'].id,
            'payment_reference': "Papa a vu le fifi de lolo",
            'invoice_line_ids': [
                Command.create({
                    'quantity': 1,
                    'price_unit': 100,
                    'tax_ids': [],
                })
            ],
        })

    def _assign_partner_address(self, partner):
        partner.write({
            'country_id': self.env.ref('base.ch').id,
            'street': "Crab street, 11",
            'city': "Crab City",
            'zip': "4242",
        })

    def test_swiss_qr_code_generation(self):
        """ Check different cases of Swiss QR-code generation, when qr_method is
        specified beforehand.
        """
        self.ch_qr_invoice.qr_code_method = 'ch_qr'

        # First check with a regular IBAN
        with self.assertRaises(UserError, msg="It shouldn't be possible to generate a Swiss QR-code for partners without a complete Swiss address."):
            self.ch_qr_invoice._generate_qr_code()

        # Setting the address should make it work
        self._assign_partner_address(self.ch_qr_invoice.company_id.partner_id)
        self._assign_partner_address(self.ch_qr_invoice.partner_id)

        self.ch_qr_invoice._generate_qr_code()

        # Now, check with a QR-IBAN as the payment account
        self.ch_qr_invoice.partner_bank_id = self.swiss_qr_iban

        with self.assertRaises(UserError, msg="It shouldn't be possible to generate a Swiss QR-cde for a QR-IBAN without giving it a valid QR-reference as payment reference."):
            self.ch_qr_invoice._generate_qr_code()

        # Assigning a QR reference should fix it
        self.ch_qr_invoice.payment_reference = '210000000003139471430009017'

        # even if the invoice is not issued from Switzerland we want to generate the code
        self.ch_qr_invoice.company_id.partner_id.country_id = self.env.ref('base.fr')
        self.ch_qr_invoice._generate_qr_code()

    def test_ch_qr_code_detection(self):
        """ Checks Swiss QR-code auto-detection when no specific QR-method
        is given to the invoice.
        """
        self._assign_partner_address(self.ch_qr_invoice.company_id.partner_id)
        self._assign_partner_address(self.ch_qr_invoice.partner_id)
        self.ch_qr_invoice._generate_qr_code()
        self.assertEqual(self.ch_qr_invoice.qr_code_method, 'ch_qr', "Swiss QR-code generator should have been chosen for this invoice.")
