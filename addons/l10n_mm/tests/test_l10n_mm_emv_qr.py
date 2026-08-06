# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged

MERCHANT_NAME_MM = 'ကုမ္ပဏီ'
MERCHANT_CITY_MM = 'ရန်ကုန်'


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nMMEmvQrCode(AccountTestInvoicingCommon):
    """ Test the generation of the MMQR code on invoices """
    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    @AccountTestInvoicingCommon.setup_country('mm')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].qr_code = True
        cls.company_data['company'].partner_id.update({
            'country_id': cls.env.ref('base.mm').id,
            'city': 'Yangon',
        })

        cls.acc_emv_mm = cls.env['res.partner.bank'].create({
            'account_number': '123456789012345678',
            'partner_id': cls.company_data['company'].partner_id.id,
            'proxy_type': 'merchant_id',
            'proxy_value': '1234567890123456',
            'l10n_mm_merchant_name': MERCHANT_NAME_MM,
            'l10n_mm_merchant_city': MERCHANT_CITY_MM,
            'include_reference': True,
            'allow_out_payment': True,
        })

        cls.acc_emv_mm_without_mmqr_info = cls.env['res.partner.bank'].create({
            'account_number': '1234567890',
            'partner_id': cls.company_data['company'].partner_id.id,
            'allow_out_payment': True,
        })

        cls.emv_qr_invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'currency_id': cls.env.ref('base.MMK').id,
            'partner_bank_id': cls.acc_emv_mm.id,
            'company_id': cls.company_data['company'].id,
            'invoice_line_ids': [Command.create({'quantity': 1, 'price_unit': 100})],
        })

    def _get_qr_vals(self, free_communication='INV/TEST/0001'):
        self.emv_qr_invoice.qr_code_method = 'emv_qr'
        return self.emv_qr_invoice.partner_bank_id._get_qr_vals(
            qr_method=self.emv_qr_invoice.qr_code_method,
            amount=self.emv_qr_invoice.amount_residual,
            currency=self.emv_qr_invoice.currency_id,
            debtor_partner=self.emv_qr_invoice.partner_id,
            free_communication=free_communication,
            structured_communication=self.emv_qr_invoice.payment_reference,
        )

    def test_emv_qr_vals(self):
        qr_vals = self._get_qr_vals()

        # Check the whole qr code string
        self.assertEqual(
            qr_vals,
            '000201'                                                    # Payload Format Indicator
            '010212'                                                    # Point of Initiation Method
            '26480015com.mmqrpay.www'                                   # Merchant Account Information: GUID
            '01151234567890123450206000000'                             # Merchant ID and Terminal ID
            '52040000'                                                  # Merchant Category Code
            '5303104'                                                   # Transaction Currency: MMK
            '5403100'                                                   # Transaction Amount
            '5802MM'                                                    # Country Code
            '5914company_1_data'                                        # Merchant Name
            '6006Yangon'                                                # Merchant City
            '62170513INV/TEST/0001'                                     # Additional Data Field: Reference Label
            f'64280002MY0107{MERCHANT_NAME_MM}0207{MERCHANT_CITY_MM}'   # Merchant Information - Language Template
            '63045B15'                                                  # CRC16
        )
        # Only the first 15 digits of the 16-digit Merchant ID are populated in the QR code.
        self.assertNotIn('1234567890123456', qr_vals)

    def test_emv_qr_optional_vals(self):
        """ Check the fallbacks and the truncations applied to the optional values. """
        # Without a terminal ID, the default '000000' value is used, and the Myanmar Unicode
        # city falls back on the city of the account holder.
        self.acc_emv_mm.l10n_mm_terminal_id = False
        self.acc_emv_mm.l10n_mm_merchant_city = False
        qr_vals = self._get_qr_vals()
        self.assertIn('0206000000', qr_vals)
        self.assertIn(f'0002MY0107{MERCHANT_NAME_MM}0206Yangon', qr_vals)

        # The merchant city is optional, unlike the language preference and the merchant name.
        self.company_data['company'].partner_id.city = False
        self.assertIn(f'64170002MY0107{MERCHANT_NAME_MM}', self._get_qr_vals())

        # The reference label (tag 62, sub-tag 05) is capped at 25 characters.
        qr_vals = self._get_qr_vals(free_communication='INV/2026/00001/A-VERY-LONG-REFERENCE')
        self.assertIn('62290525INV/2026/00001/A-VERY-LON', qr_vals)

    def test_emv_qr_code_generation_errors(self):
        self.emv_qr_invoice.qr_code_method = 'emv_qr'
        self.emv_qr_invoice._generate_qr_code()

        # Using an invoice currency other than MMK should fail
        self.emv_qr_invoice.currency_id = self.env.ref('base.USD')
        with self.assertRaises(UserError, msg="Can't generate an MMQR code with a currency other than MMK."):
            self.emv_qr_invoice._generate_qr_code()

        # Without the account holder city should fail, tag 60 is mandatory
        self.emv_qr_invoice.currency_id = self.env.ref('base.MMK')
        self.company_data['company'].partner_id.city = False
        with self.assertRaises(UserError, msg="Missing Merchant City."):
            self.emv_qr_invoice._generate_qr_code()

        # Without the Myanmar Unicode merchant name should fail, tag 64 is mandatory
        self.company_data['company'].partner_id.city = 'Yangon'
        self.acc_emv_mm.l10n_mm_merchant_name = False
        with self.assertRaises(UserError, msg="Missing Merchant Name (Myanmar Unicode)."):
            self.emv_qr_invoice._generate_qr_code()

        # Without any MMQR information should fail
        self.acc_emv_mm.l10n_mm_merchant_name = MERCHANT_NAME_MM
        self.emv_qr_invoice.partner_bank_id = self.acc_emv_mm_without_mmqr_info
        with self.assertRaises(UserError, msg="The proxy type of an MMQR code must be a Merchant ID."):
            self.emv_qr_invoice._generate_qr_code()

    def test_mm_proxy_constraints(self):
        with self.assertRaises(ValidationError, msg="The Merchant ID of an MMQR code must be 16 digits long."):
            self.acc_emv_mm.proxy_value = '123456789012345'
        self.acc_emv_mm.invalidate_recordset()

        with self.assertRaises(ValidationError, msg="The Merchant ID of an MMQR code must only contain digits."):
            self.acc_emv_mm.proxy_value = '12345678901234AB'
        self.acc_emv_mm.invalidate_recordset()

        with self.assertRaises(ValidationError, msg="The Terminal ID of an MMQR code must be at most 25 digits long."):
            self.acc_emv_mm.l10n_mm_terminal_id = '0' * 26
