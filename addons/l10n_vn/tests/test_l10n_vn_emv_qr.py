# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nVNEmvQrCode(AccountTestInvoicingCommon):
    """ Test the generation of the EMV QR Code on invoices """

    @classmethod
    @AccountTestInvoicingCommon.setup_country('vn')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].qr_code = True
        cls.company_data['company'].partner_id.update({
            'country_id': cls.env.ref('base.vn').id,
            'city': 'Vietnam',
        })

        cls.bank_vn = cls.env['res.bank'].create({
            'name': 'VN Bank',
            'bic': '970422',
        })

        cls.acc_emv_vn = cls.env['res.partner.bank'].create({
            'acc_number': '123456789012345678',
            'bank_id': cls.bank_vn.id,
            'partner_id': cls.company_data['company'].partner_id.id,
            'proxy_type': 'bank_acc',
            'proxy_value': '660704060000129',
            'include_reference': True,
        })

        cls.acc_emv_vn_without_paynow_info = cls.env['res.partner.bank'].create({
            'acc_number': '1234567890',
            'partner_id': cls.company_data['company'].partner_id.id,
        })

        cls.emv_qr_invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'currency_id': cls.env.ref('base.VND').id,
            'partner_bank_id': cls.acc_emv_vn.id,
            'company_id': cls.company_data['company'].id,
            'invoice_line_ids': [Command.create({'quantity': 1, 'price_unit': 100})],
        })

    def test_emv_qr_code_generation(self):
        self.emv_qr_invoice.qr_code_method = 'emv_qr'
        self.emv_qr_invoice._generate_qr_code()

        # Using invoice currency other than VND should fail
        self.emv_qr_invoice.currency_id = self.env.ref('base.USD')
        with self.assertRaises(UserError, msg="The chosen QR-code type is not eligible for this invoice."):
            self.emv_qr_invoice._generate_qr_code()

        # Without company partner city should fail
        self.emv_qr_invoice.currency_id = self.env.ref('base.VND')
        self.company_data['company'].partner_id.city = False
        with self.assertRaises(UserError, msg="Missing Merchant City."):
            self.emv_qr_invoice._generate_qr_code()

        # Without paynow infomation should fail
        self.company_data['company'].partner_id.city = 'Vietnam'
        self.emv_qr_invoice.partner_bank_id = self.acc_emv_vn_without_paynow_info
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
        self.assertEqual(emv_qr_vals, '00020101021238590010A0000007270129000697042201156607040600001290208QRIBFTTA52040000530370454031005802VN5914company_1_data6007Vietnam62150811INVTEST000163042656')

    def test_remove_vietnamese_accents(self):
        accent_string = "áàảãạăắằẳẵặâấầẩẫậÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬéèẻẽẹêếềểễệÉÈẺẼẸÊẾỀỂỄỆóòỏõọôốồổỗộơớờởỡợÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢíìỉĩịÍÌỈĨỊúùủũụưứừửữựÚÙỦŨỤƯỨỪỬỮỰýỳỷỹỵÝỲỶỸỴđĐ"
        result = self.env['res.partner.bank']._remove_accents(accent_string)
        self.assertEqual(result, "aaaaaaaaaaaaaaaaaAAAAAAAAAAAAAAAAAeeeeeeeeeeeEEEEEEEEEEEoooooooooooooooooOOOOOOOOOOOOOOOOOiiiiiIIIIIuuuuuuuuuuuUUUUUUUUUUUyyyyyYYYYYdD")

    def test_emv_qr_vals_with_accent_partner(self):
        self.company_data['company'].partner_id.name = 'áÁéÉóÓíÍúÚýÝđĐ'
        self.emv_qr_invoice.qr_code_method = 'emv_qr'
        unstruct_ref = 'INV/TEST/0002'
        emv_qr_vals = self.emv_qr_invoice.partner_bank_id._get_qr_vals(
            qr_method=self.emv_qr_invoice.qr_code_method,
            amount=self.emv_qr_invoice.amount_residual,
            currency=self.emv_qr_invoice.currency_id,
            debtor_partner=self.emv_qr_invoice.partner_id,
            free_communication=unstruct_ref,
            structured_communication=self.emv_qr_invoice.payment_reference,
        )

        # Check the whole qr code string
        self.assertEqual(emv_qr_vals, '00020101021238590010A0000007270129000697042201156607040600001290208QRIBFTTA52040000530370454031005802VN5914aAeEoOiIuUyYdD6007Vietnam62150811INVTEST00026304E1C2')
