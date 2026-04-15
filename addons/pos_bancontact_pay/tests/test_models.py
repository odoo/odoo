import json
import uuid
from contextlib import contextmanager
from unittest.mock import patch

from requests import Response

from odoo import Command
from odoo.exceptions import (
    AccessDenied,
    AccessError,
    MissingError,
    UserError,
    ValidationError,
)
from odoo.tests.common import tagged

from odoo.addons.point_of_sale.tests.common import CommonPosTest
from odoo.addons.pos_bancontact_pay import const
from odoo.addons.pos_bancontact_pay.tests.common import TestBancontactPay


@tagged("post_install", "-at_install")
class TestModels(TestBancontactPay, CommonPosTest):

    # --------------------------
    # Currency
    # --------------------------
    def test_journal_supported_currency(self):
        ### Company EUR ###
        # EUR --> USD
        with self.assertRaises(ValidationError):
            self.bancontact_journal.currency_id = self.usd_currency
        # EUR -> False
        self.bancontact_journal.currency_id = False
        # False -> USD
        with self.assertRaises(ValidationError):
            self.bancontact_journal.currency_id = self.usd_currency
        # False -> EUR
        self.bancontact_journal.currency_id = self.eur_currency

        ### Company USD ###
        self.company.currency_id = self.usd_currency
        # EUR --> False
        with self.assertRaises(ValidationError):
            self.bancontact_journal.currency_id = False
        # EUR --> USD
        with self.assertRaises(ValidationError):
            self.bancontact_journal.currency_id = self.usd_currency

    def test_payment_method_supported_currency(self):
        usd_journal = self.env["account.journal"].create({
            "name": "USD Journal",
            "code": "USDJOURNAL",
            "type": "bank",
            "company_id": self.company.id,
            "currency_id": self.usd_currency.id,
        })

        # False --> USD Journal
        with self.assertRaises(ValidationError):
            self.payment_method_sticker_1.journal_id = usd_journal

        # False --> EUR Journal
        self.payment_method_sticker_1.journal_id = self.bancontact_journal

        # EUR journal --> USD Journal
        with self.assertRaises(ValidationError):
            self.payment_method_sticker_1.journal_id = usd_journal

    def test_company_supported_currency(self):
        ### Journal EUR ###
        # EUR --> USD
        self.company.currency_id = self.usd_currency
        # USD --> EUR
        self.company.currency_id = self.eur_currency

        ### Journal False ###
        self.bancontact_journal.currency_id = False
        # EUR --> USD
        with self.assertRaises(ValidationError):
            self.company.currency_id = self.usd_currency

    # --------------------------
    # Payment Methods
    # --------------------------
    def test_default_payment_methods(self):
        default_methods = self.env['pos.config']._default_payment_methods()
        bancontact_methods = [method for method in default_methods if method.payment_provider == 'bancontact_pay']

        # Has display methods
        display_methods = [method for method in bancontact_methods if method.bancontact_usage == 'display']
        self.assertEqual(len(display_methods), 1)

        # No sticker methods
        sticker_methods = [method for method in bancontact_methods if method.bancontact_usage == 'sticker']
        self.assertEqual(len(sticker_methods), 0)

    def test_one_bancontact_sticker_per_pos_config(self):
        test_config = self.env["pos.config"].create(
            {
                "name": "Test POS Config",
                "module_pos_restaurant": False,
            },
        )
        payment_method_sticker_3 = self.env["pos.payment.method"].create(
            {
                "name": "Bancontact - Sticker 3",
                "payment_method_type": "external_qr",
                "payment_provider": "bancontact_pay",
                "bancontact_usage": "sticker",
                "company_id": self.company.id,
                "journal_id": self.bancontact_journal.id,
                "bancontact_api_key": "sticker_api_key",
                "bancontact_ppid": "sticker_profile_id",
            },
        )

        # Assigning sticker already assigned to another POS config via pos.payment.method
        with self.assertRaises(ValidationError):
            self.payment_method_sticker_1.config_ids = [Command.link(test_config.id)]

        # Assigning sticker already assigned to another POS config via pos.config
        payment_method_sticker_3.config_ids = [Command.clear()]
        with self.assertRaises(ValidationError):
            test_config.payment_method_ids = [Command.link(self.payment_method_sticker_1.id)]

        # Assigning a new sticker to the POS config should work
        test_config.payment_method_ids = [Command.link(payment_method_sticker_3.id)]

    # --------------------------------------
    # Create Bancontact Payment
    # --------------------------------------
    def test_create_bancontact_payment_wrong_provider(self):
        with (self.assertRaises(ValidationError)):
            self.bank_payment_method.create_bancontact_payment({})

    def test_create_bancontact_payment_success(self):
        generated_bancontact_id = self._generate_bancontact_id()
        generated_qr_code = self._generate_qr_code()

        with self.mock_bancontact_call(bancontact_id=generated_bancontact_id, qr_code=generated_qr_code):
            result = self.payment_method_display.create_bancontact_payment({})
            self.assertEqual(result, {"bancontact_id": generated_bancontact_id, "qr_code": generated_qr_code + "&f=SVG"})

    def test_create_bancontact_payment_api_error(self):
        codes = [(400, MissingError), (401, AccessDenied), (403, AccessDenied),
                 (404, UserError), (422, ValidationError), (429, AccessDenied),
                 (500, AccessError), (503, AccessError)]

        for status_code, expected_exception in codes:
            with self.mock_bancontact_call(post_status_code=status_code), self.assertRaises(expected_exception):
                self.payment_method_display.create_bancontact_payment({})

    # --------------------------------------
    # Cancel Bancontact Payment
    # --------------------------------------
    def test_cancel_bancontact_payment_wrong_provider(self):
        with (self.assertRaises(ValidationError)):
            self.bank_payment_method.cancel_bancontact_payment("bancontact_id")

    def test_cancel_bancontact_payment_success(self):
        with self.mock_bancontact_call():
            self.payment_method_display.cancel_bancontact_payment("bancontact_id")

    def test_cancel_bancontact_payment_api_error(self):
        codes = [(400, MissingError), (401, AccessDenied), (403, AccessDenied),
                 (404, UserError), (422, ValidationError), (429, AccessDenied),
                 (500, AccessError), (503, AccessError)]

        for status_code, expected_exception in codes:
            with self.mock_bancontact_call(delete_status_code=status_code), self.assertRaises(expected_exception):
                self.payment_method_display.cancel_bancontact_payment("bancontact_id")

    # --------------------------------------
    # Prepare Bancontact Payment Request
    # --------------------------------------
    def test_prepare_display_payment_request(self):
        uuid_str = str(uuid.uuid4())
        actual = self.payment_method_display._prepare_display_payment_request({
            "uuid": uuid_str,
            "configId": 1,
            "amount": 10.00,
            "currency": "EUR",
            "description": "sample description",
        })
        expected = [
            f"{const.API_URLS['preprod']['merchant']}/v3/payments",
            {
                "reference": uuid_str.replace("-", ""),
                "amount": 1000,
                "currency": "EUR",
                "description": "sample description",
                "identifyCallbackUrl": f"{self.payment_method_display.get_base_url()}/bancontact_pay/webhook?config_id=1&ppid={self.payment_method_display.bancontact_ppid}&mode=test",
                "callbackUrl": f"{self.payment_method_display.get_base_url()}/bancontact_pay/webhook?config_id=1&ppid={self.payment_method_display.bancontact_ppid}&mode=test",
            },
        ]
        self.assertEqual(actual, expected)

    def test_prepare_sticker_payment_request(self):
        uuid_str = str(uuid.uuid4())
        actual = self.payment_method_sticker_1._prepare_sticker_payment_request({
            "uuid": uuid_str,
            "configId": 1,
            "amount": 10.00,
            "currency": "EUR",
            "description": "sample description",
            "shopName": "Shop Name",
        })
        expected = [
            f"{const.API_URLS['preprod']['merchant']}/v3/payments/pos",
            {
                "reference": uuid_str.replace("-", ""),
                "amount": 1000,
                "currency": "EUR",
                "description": "sample description",
                "identifyCallbackUrl": f"{self.payment_method_sticker_1.get_base_url()}/bancontact_pay/webhook?config_id=1&ppid={self.payment_method_sticker_1.bancontact_ppid}&mode=test",
                "callbackUrl": f"{self.payment_method_sticker_1.get_base_url()}/bancontact_pay/webhook?config_id=1&ppid={self.payment_method_sticker_1.bancontact_ppid}&mode=test",
                "posId": f"pm{self.payment_method_sticker_1.id}",
                "shopId": "pos1",
                "shopName": "Shop Name",
            },
        ]
        self.assertEqual(actual, expected)

    # --------------------------------------
    # Helpers
    # --------------------------------------
    @contextmanager
    def mock_bancontact_call(self, bancontact_id=None, qr_code=None, post_status_code=200, delete_status_code=200):
        def mock_post(url, **kwargs):
            response = Response()

            if 200 <= post_status_code < 300:
                payment_id = bancontact_id or self._generate_bancontact_id()
                href = qr_code or self._generate_qr_code()
                response._content = json.dumps(
                    {
                        "paymentId": payment_id,
                        "_links": {"qrcode": {"href": href}},
                    },
                ).encode()

            response.status_code = post_status_code
            return response

        def mock_delete(url, **kwargs):
            response = Response()
            response.status_code = delete_status_code
            return response

        with (patch("odoo.addons.pos_bancontact_pay.models.pos_payment_method.requests.post", mock_post),
              patch("odoo.addons.pos_bancontact_pay.models.pos_payment_method.requests.delete", mock_delete)):
            yield

    def _generate_bancontact_id(self):
        return "bancontact_" + str(uuid.uuid4())

    def _generate_qr_code(self):
        return "https://example.com/bancontact_qrcode/" + str(uuid.uuid4())
