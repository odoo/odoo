# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nSGEmvQrCode(AccountTestInvoicingCommon):
    """ Test the generation of the EMV QR Code on invoices """

    @classmethod
    @AccountTestInvoicingCommon.setup_country('sg')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].qr_code = True
        cls.company_data['company'].partner_id.update({
            'country_id': cls.env.ref('base.sg').id,
            'city': 'Singapore',
        })

        cls.acc_emv_sg = cls.env['res.partner.bank'].create({
            'acc_number': '123456789012345678',
            'partner_id': cls.company_data['company'].partner_id.id,
            'proxy_type': 'uen',
            'proxy_value': '200002150HWCF',
            'include_reference': True,
        })

        cls.acc_emv_sg_without_paynow_info = cls.env['res.partner.bank'].create({
            'acc_number': '1234567890',
            'partner_id': cls.company_data['company'].partner_id.id,
        })

        cls.emv_qr_invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'currency_id': cls.env.ref('base.SGD').id,
            'partner_bank_id': cls.acc_emv_sg.id,
            'company_id': cls.company_data['company'].id,
            'invoice_line_ids': [Command.create({'quantity': 1, 'price_unit': 100})],
        })

    def test_emv_qr_code_generation(self):
        self.emv_qr_invoice.qr_code_method = 'emv_qr'
        self.emv_qr_invoice._generate_qr_code()

        # Using invoice currency other than SGD should fail
        self.emv_qr_invoice.currency_id = self.env.ref('base.USD')
        with self.assertRaises(UserError, msg="The chosen QR-code type is not eligible for this invoice."):
            self.emv_qr_invoice._generate_qr_code()

        # Without company partner city should fail
        self.emv_qr_invoice.currency_id = self.env.ref('base.SGD')
        self.company_data['company'].partner_id.city = False
        with self.assertRaises(UserError, msg="Missing Merchant City."):
            self.emv_qr_invoice._generate_qr_code()

        # Without paynow infomation should fail
        self.company_data['company'].partner_id.city = 'Singapore'
        self.emv_qr_invoice.partner_bank_id = self.acc_emv_sg_without_paynow_info
        with self.assertRaises(UserError, msg="The account receiving the payment must have a Proxy type and a Proxy value set."):
            self.emv_qr_invoice._generate_qr_code()

    def test_emv_qr_vals(self):
        self.emv_qr_invoice.qr_code_method = 'emv_qr'
        unstruct_ref = 'INV/TEST/0001'
        emv_qr_vals = self.emv_qr_invoice.partner_bank_id._get_qr_vals(
            qr_method=self.emv_qr_invoice.qr_code_method,
            amount=self.emv_qr_invoice.amount_residual,
            currency=self.emv_qr_invoice.currency_id,
            debtor_partner=self.emv_qr_invoice.partner_id,
            free_communication=unstruct_ref,
            structured_communication=self.emv_qr_invoice.payment_reference,
        )

        # Check the whole qr code string
        self.assertEqual(emv_qr_vals, '00020101021226400009SG.PAYNOW010120213200002150HWCF0301052040000530370254031005802SG5914company_1_data6009Singapore62170113INV/TEST/0001630416C8')
