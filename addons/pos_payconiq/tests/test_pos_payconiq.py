import datetime
import json

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged("post_install", "-at_install")
class TestPosPayconiq(TestPointOfSaleHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Currencies and company setup
        cls.eur_currency = cls.env.ref("base.EUR")
        cls.usd_currency = cls.env.ref("base.USD")
        cls.company.currency_id = cls.eur_currency

        # Journals
        cls.payconiq_journal = cls.env["account.journal"].create(
            {
                "name": "Payconiq Journal",
                "code": "PAYCONIQ",
                "type": "bank",
                "company_id": cls.company.id,
                "currency_id": cls.eur_currency.id,
            },
        )

        # Payment Methods
        cls.payment_method_display = cls.env["pos.payment.method"].create(
            {
                "name": "Payconiq - Display",
                "payment_method_type": "external_qr",
                "use_payment_terminal": "payconiq",
                "external_qr_usage": "display",
                "company_id": cls.company.id,
                "journal_id": cls.payconiq_journal.id,
                "payconiq_api_key": "display_api_key",
                "payconiq_ppid": "display_profile_id",
            },
        )
        cls.payment_method_sticker_1 = cls.env["pos.payment.method"].create(
            {
                "name": "Payconiq - Sticker 1",
                "payment_method_type": "external_qr",
                "use_payment_terminal": "payconiq",
                "external_qr_usage": "sticker",
                "external_qr_sticker_size": "L",
                "company_id": cls.company.id,
                "journal_id": cls.payconiq_journal.id,
                "payconiq_api_key": "sticker_api_key",
                "payconiq_ppid": "sticker_profile_id",
            },
        )
        cls.payment_method_sticker_2 = cls.env["pos.payment.method"].create(
            {
                "name": "Payconiq - Sticker 2",
                "payment_method_type": "external_qr",
                "use_payment_terminal": "payconiq",
                "external_qr_usage": "sticker",
                "external_qr_sticker_size": "L",
                "company_id": cls.company.id,
                "journal_id": cls.payconiq_journal.id,
                "payconiq_api_key": "sticker_api_key",
                "payconiq_ppid": "sticker_profile_id",
            },
        )

        # Pos Config
        cls.main_pos_config.auto_validate_terminal_payment = False
        cls.main_pos_config.journal_id.currency_id = cls.eur_currency
        cls.main_pos_config.invoice_journal_id.currency_id = cls.eur_currency
        cls.main_pos_config.use_pricelist = False
        cls.main_pos_config.payment_method_ids = [
            Command.clear(),
            Command.link(cls.payment_method_display.id),
            Command.link(cls.payment_method_sticker_1.id),
            Command.link(cls.payment_method_sticker_2.id),
        ]

    # ======================================================================== #
    #                                  MODELS                                  #
    # ======================================================================== #
    def test_payconiq_supported_currency(self):
        # 1. Journal with unsupported currency → should raise error
        with self.assertRaises(ValidationError):
            self.payconiq_journal.currency_id = self.usd_currency

        # 2. Journal with no currency + unsupported company currency → should raise error
        self.payconiq_journal.currency_id = False
        with self.assertRaises(ValidationError):
            self.company.currency_id = self.usd_currency
        self.payconiq_journal.currency_id = self.eur_currency

    def test_payconiq_static_qr_creation(self):
        self.payment_method_sticker_1.external_qr_sticker_size = "M"
        expected = "https://qrcodegenerator.api.preprod.bancontact.net/qrcode?f=PNG&s=%s&c=https://payconiq.com/l/1/%s/pm%s" % (
            self.payment_method_sticker_1.external_qr_sticker_size,
            self.payment_method_sticker_1.payconiq_ppid,
            self.payment_method_sticker_1.id,
        )
        actual = self.payment_method_sticker_1.external_qr_sticker_url

        self.assertEqual(actual, expected)

    def test_payconiq_one_sticker_per_pos_config(self):
        test_config = self.env["pos.config"].create(
            {
                "name": "Test POS Config",
                "module_pos_restaurant": False,
            },
        )

        with self.assertRaises(ValidationError):
            self.payment_method_sticker_1.config_ids = [Command.link(test_config.id)]

    # ======================================================================== #
    #                                CONTROLLERS                               #
    # ======================================================================== #
    def test_payconiq_webhook_success(self):
        # Create payconiq payment
        payconiq_payment = self.env["pos.payment.payconiq"].create(
            {
                "payconiq_id": "abcdefghijqklmnopqrstuvw",
                "qr_code": "https://test.qr.code",
                "uuid": "uuid-test",
                "user_id": self.env.user.id,
            },
        )

        # Simulate webhook notification
        headers = {"content-type": "application/json"}
        now = datetime.datetime.now(datetime.timezone.utc)
        payload = {
            "paymentId": payconiq_payment.payconiq_id,
            "transferAmount": 100,
            "tippingAmount": 0,
            "amount": 100,
            "totalAmount": 100,
            "description": "Sample description",
            "createdAt": now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "expireAt": (now + datetime.timedelta(minutes=3)).strftime(
                "%Y-%m-%dT%H:%M:%S.%f",
            )[:-3]
            + "Z",
            "succeededAt": (now + datetime.timedelta(minutes=1)).strftime(
                "%Y-%m-%dT%H:%M:%S.%f",
            )[:-3]
            + "Z",
            "status": "SUCCEEDED",
            "debtor": {"name": "John", "iban": "*************12636"},
            "currency": "EUR",
        }

        response = self.url_open(
            "/webhook/payconiq",
            data=json.dumps(payload),
            headers=headers,
            method="POST",
        )
        self.assertEqual(200, response.status_code, "Webhook not OK")

    def test_payconiq_webhook_payment_not_found(self):
        # Simulate webhook notification
        headers = {"content-type": "application/json"}
        now = datetime.datetime.now(datetime.timezone.utc)
        payload = {
            "paymentId": False,
            "transferAmount": 100,
            "tippingAmount": 0,
            "amount": 100,
            "totalAmount": 100,
            "description": "Sample description",
            "createdAt": now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "expireAt": (now + datetime.timedelta(minutes=3)).strftime(
                "%Y-%m-%dT%H:%M:%S.%f",
            )[:-3]
            + "Z",
            "succeededAt": (now + datetime.timedelta(minutes=1)).strftime(
                "%Y-%m-%dT%H:%M:%S.%f",
            )[:-3]
            + "Z",
            "status": "SUCCEEDED",
            "debtor": {"name": "John", "iban": "*************12636"},
            "currency": "EUR",
        }

        response = self.url_open(
            "/webhook/payconiq",
            data=json.dumps(payload),
            headers=headers,
            method="POST",
        )
        self.assertEqual(404, response.status_code, "Webhook not NOT_FOUND")

    # ======================================================================== #
    #                                 FRONTEND                                 #
    # ======================================================================== #
    def test_payconiq_display_flow(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour("payconiq_display_flow")

    def test_payconiq_sticker_flow(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour("payconiq_sticker_flow")
