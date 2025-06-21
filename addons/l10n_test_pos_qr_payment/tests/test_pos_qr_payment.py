# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import tagged
from odoo.tools import mute_logger
from .common import TestPosQrCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUiSEPA(TestPosQrCommon):

    @classmethod
    @TestPosQrCommon.setup_country('be')
    def setUpClass(cls):
        super().setUpClass()

        # Set Bank Account on journal
        cls.bank_account = cls.env['res.partner.bank'].create({
            'acc_number': 'BE15001559627230',
            'partner_id': cls.company_data['company'].partner_id.id,
        })
        cls.company_data['default_journal_bank'].write({'bank_account_id': cls.bank_account.id})

        # Setup QR Payment method for SEPA
        qr_payment = cls.env['pos.payment.method'].sudo().create({
            'name': 'QR Code',
            'journal_id': cls.company_data['default_journal_bank'].id,
            'payment_method_type': "qr_code",
            'qr_code_method': "sct_qr"
        })
        cls.main_pos_config.write({
            'payment_method_ids': [(4, qr_payment.id)]
        })

    @mute_logger('odoo.http')
    def test_01_pos_order_with_sepa_qr_payment_fail(self):
        """ Test Point of Sale QR Payment flow with SEPA.
            In this test the QR payment method is missing the required fields and will display an error message.
        """

        # Set non sepa bank account to make the test failed
        self.bank_account.write({
            'acc_number': 'SA4420000001234567891234',
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()

        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PaymentScreenWithQRPaymentFailure', login="pos_user")

    def test_02_pos_order_with_sepa_qr_payment(self):
        """ Test Point of Sale QR Payment flow with SEPA
        """

        # Set info that were wrong in test_01
        self.bank_account.write({
            'acc_number': 'BE15001559627230',
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()

        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PaymentScreenWithQRPayment', login="pos_user")


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUiCH(TestPosQrCommon):

    @classmethod
    @TestPosQrCommon.setup_country('ch')
    def setUpClass(cls):
        super().setUpClass()

        # Set required fields for Swiss QR bank account partner
        cls.company_data['company'].partner_id.write({
            'street': "Crab street, 11",
            'city': "Crab City",
            'zip': "4242",
        })

        # Set Bank Account on journal
        cls.bank_account = cls.env['res.partner.bank'].create({
            'acc_number': 'CH15 3881 5158 3845 3843 7',
            'partner_id': cls.company_data['company'].partner_id.id,
        })
        cls.company_data['default_journal_bank'].write({'bank_account_id': cls.bank_account.id})

        # Setup QR Payment method for Swiss QR
        qr_payment = cls.env['pos.payment.method'].sudo().create({
            'name': 'QR Code',
            'journal_id': cls.company_data['default_journal_bank'].id,
            'payment_method_type': "qr_code",
            'qr_code_method': "ch_qr"
        })
        cls.main_pos_config.write({
            'payment_method_ids': [(4, qr_payment.id)]
        })

        cls.env['res.partner'].create({
            'name': 'AAA Partner Swiss',
            'country_id': cls.env.ref('base.ch').id,
            'street': "Crab street, 11",
            'city': "Crab City",
            'zip': "4242",
        })

    @mute_logger('odoo.http')
    def test_01_pos_order_with_swiss_qr_payment_fail(self):
        """ Test Point of Sale QR Payment flow with Swiss QR.
            In this test the QR payment will fail as we are not selecting a swiss customer
        """
        self.main_pos_config.with_user(self.pos_user).open_ui()

        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PaymentScreenWithQRPaymentFailure', login="pos_user")

    def test_02_pos_order_with_swiss_qr_payment(self):
        """ Test Point of Sale QR Payment flow with Swiss QR
            We have to select a customer based in Switzerland or Lichtestein to use this payment method
        """
        self.main_pos_config.with_user(self.pos_user).open_ui()

        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PaymentScreenWithQRPaymentSwiss', login="pos_user")


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUiHK(TestPosQrCommon):

    @classmethod
    def setup_armageddon_tax(cls, tax_name, company_data):
        # Hong Kong doesn't have any tax, so this methods will throw errors if we don't return None
        return None

    @classmethod
    @TestPosQrCommon.setup_country('hk')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].partner_id.update({
            'city': 'HK',
        })

        # Set Bank Account on journal
        cls.bank_account = cls.env['res.partner.bank'].create({
            'acc_number': '123-123456-123',
            'partner_id': cls.company_data['company'].partner_id.id,
        })
        cls.company_data['default_journal_bank'].write({'bank_account_id': cls.bank_account.id})

        # Setup QR Payment method for EMV(FPS)
        qr_payment = cls.env['pos.payment.method'].sudo().create({
            'name': 'QR Code',
            'journal_id': cls.company_data['default_journal_bank'].id,
            'payment_method_type': "qr_code",
            'qr_code_method': "emv_qr"
        })
        cls.main_pos_config.write({
            'payment_method_ids': [(4, qr_payment.id)]
        })

    @mute_logger('odoo.http')
    def test_01_pos_order_with_fps_qr_payment_fail(self):
        """ Test Point of Sale QR Payment flow with FPS.
            In this test the QR payment method is missing the required fields and will display an error message.
        """
        self.main_pos_config.with_user(self.pos_user).open_ui()

        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PaymentScreenWithQRPaymentFailure', login="pos_user")

    def test_02_pos_order_with_emv_qr_payment(self):
        """ Test Point of Sale QR Payment flow with FPS.
        """

        # Set missing info that were missing in test_01
        self.bank_account.write({
            'proxy_type': 'mobile',
            'proxy_value': '+852-67891234',
            'include_reference': True,
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()

        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PaymentScreenWithQRPayment', login="pos_user")


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUIBR(TestPosQrCommon):

    @classmethod
    @TestPosQrCommon.setup_country('br')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].partner_id.update({
            'country_id': cls.env.ref('base.br').id,
            'city': 'BR',
        })

        # Set Bank Account on journal
        cls.bank_account = cls.env["res.partner.bank"].create({
            "acc_number": "123456789012345678",
            "partner_id": cls.company_data["company"].partner_id.id,
        })
        cls.company_data['default_journal_bank'].write({'bank_account_id': cls.bank_account.id})

        # Setup QR Payment method for PIX
        qr_payment = cls.env['pos.payment.method'].sudo().create({
            'name': 'QR Code',
            'journal_id': cls.company_data['default_journal_bank'].id,
            'payment_method_type': "qr_code",
            'qr_code_method': "emv_qr"
        })
        cls.main_pos_config.write({
            'payment_method_ids': [(4, qr_payment.id)]
        })

    @mute_logger('odoo.http')
    def test_01_pos_order_with_pix_qr_payment_fail(self):
        """ Test Point of Sale QR Payment flow with PIX.
            In this test the QR payment method is missing the required fields and will display an error message.
        """
        self.main_pos_config.with_user(self.pos_user).open_ui()

        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PaymentScreenWithQRPaymentFailure', login="pos_user")

    def test_02_pos_order_with_pix_qr_payment(self):
        """ Test Point of Sale QR Payment flow with PIX
        """

        # Set missing info that were missing in test_01
        self.bank_account.write({
            "proxy_type": "br_random",
            "proxy_value": "71d6c6e1-64ea-4a11-9560-a10870c40ca2",
            "include_reference": True,
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()

        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PaymentScreenWithQRPayment', login="pos_user")
