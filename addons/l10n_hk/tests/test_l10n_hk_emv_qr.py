# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nHKEmvQrCode(AccountTestInvoicingCommon):
    """ Test the generation of the EMV QR Code on invoices """

    @classmethod
    def setup_armageddon_tax(cls, tax_name, company_data):
        # Hong Kong doesn't have any tax, so this methods will throw errors if we don't return None
        return None

    @classmethod
    @AccountTestInvoicingCommon.setup_country('hk')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].qr_code = True
        cls.company_data['company'].partner_id.city = 'HK'

        cls.acc_emv_hk = cls.env['res.partner.bank'].create({
            'acc_number': '123456789012345678',
            'partner_id': cls.company_data['company'].partner_id.id,
            'proxy_type': 'mobile',
            'proxy_value': '+852-67891234',
            'include_reference': True,
        })

        cls.acc_emv_hk_without_fps_info = cls.env['res.partner.bank'].create({
            'acc_number': '1234567890',
            'partner_id': cls.company_data['company'].partner_id.id,
        })

        cls.emv_qr_invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'currency_id': cls.env.ref('base.HKD').id,
            'partner_bank_id': cls.acc_emv_hk.id,
            'company_id': cls.company_data['company'].id,
            'invoice_line_ids': [Command.create({'quantity': 1, 'price_unit': 100})],
        })

        cls.emv_qr_invoice_with_non_integer_amount = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'currency_id': cls.env.ref('base.HKD').id,
            'partner_bank_id': cls.acc_emv_hk.id,
            'company_id': cls.company_data['company'].id,
            'invoice_line_ids': [Command.create({'quantity': 1, 'price_unit': 100.5})],
        })

    def test_emv_qr_code_generation(self):
        self.emv_qr_invoice.qr_code_method = 'emv_qr'
        self.emv_qr_invoice._generate_qr_code()

        # Using invoice currency other than HKD or CNY should fail
        self.emv_qr_invoice.currency_id = self.env.ref('base.USD')
        with self.assertRaises(UserError, msg="The chosen QR-code type is not eligible for this invoice."):
            self.emv_qr_invoice._generate_qr_code()

        # Without company partner city should fail
        self.emv_qr_invoice.currency_id = self.env.ref('base.HKD')
        self.company_data['company'].partner_id.city = False
        with self.assertRaises(UserError, msg="Missing Merchant City."):
            self.emv_qr_invoice._generate_qr_code()

        # Without fps infomation should fail
        self.company_data['company'].partner_id.city = 'HK'
        self.emv_qr_invoice.partner_bank_id = self.acc_emv_hk_without_fps_info
        with self.assertRaises(UserError, msg="The account receiving the payment must have a FPS type and a FPS identifier set."):
            self.emv_qr_invoice._generate_qr_code()

    def test_emv_qr_vals(self):
        self.emv_qr_invoice.qr_code_method = 'emv_qr'
        demo_payment_reference = 'INV/TEST/0001'
        emv_qr_vals = self.emv_qr_invoice.partner_bank_id._get_qr_vals(
            qr_method=self.emv_qr_invoice.qr_code_method,
            amount=self.emv_qr_invoice.amount_residual,
            currency=self.emv_qr_invoice.currency_id,
            debtor_partner=self.emv_qr_invoice.partner_id,
            free_communication=demo_payment_reference,
            structured_communication=demo_payment_reference,
        )

        # Check the whole qr code string
        qr_code_string = ''.join(emv_qr_vals)
        self.assertEqual(qr_code_string, '00020101021226330012hk.com.hkicl0313+852-6789123452040000530334454031005802HK5914company_1_data6002HK62170513INV/TEST/00016304A154')

    def test_emv_qr_vals_with_non_integer_amount(self):
        self.emv_qr_invoice_with_non_integer_amount.qr_code_method = 'emv_qr'
        unstruct_ref = 'INV/TEST/0002'
        emv_qr_vals = self.emv_qr_invoice_with_non_integer_amount.partner_bank_id._get_qr_vals(
            qr_method=self.emv_qr_invoice_with_non_integer_amount.qr_code_method,
            amount=self.emv_qr_invoice_with_non_integer_amount.amount_residual,
            currency=self.emv_qr_invoice_with_non_integer_amount.currency_id,
            debtor_partner=self.emv_qr_invoice_with_non_integer_amount.partner_id,
            free_communication=unstruct_ref,
            structured_communication=self.emv_qr_invoice_with_non_integer_amount.payment_reference,
        )

        # Check the whole qr code string
        self.assertEqual(emv_qr_vals, '00020101021226330012hk.com.hkicl0313+852-678912345204000053033445405100.55802HK5914company_1_data6002HK62170513INV/TEST/000263049E64')

    def test_invoice_default_code(self):
        """ If no QR method is selected by default, and the country does not match, it should not be selecting the EMV QR method. """
        self.acc_emv_hk.country_code = 'NZ'

        self.assertIsNone(self.emv_qr_invoice._generate_qr_code())

    def test_invoice_wrong_method(self):
        """ If an EMV QR is selected on the invoice with a wrong country, it should raise errors messages. """
        self.acc_emv_hk.country_code = 'NZ'
        self.emv_qr_invoice.qr_code_method = 'emv_qr'

        error_message = self.acc_emv_hk._get_error_messages_for_qr('emv_qr', self.partner_a, self.env.ref('base.HKD'))
        self.assertIsNotNone(error_message)
