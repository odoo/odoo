import json
from unittest.mock import patch
from urllib.parse import parse_qs

from odoo.exceptions import (
    AccessDenied,
    AccessError,
    MissingError,
    UserError,
    ValidationError,
)
from odoo.tests.common import HttpCase, MockHTTPClient
from odoo.tools import mute_logger

from odoo.addons.pos_payment_method_bancontact_pay.errors.exceptions import (
    BancontactSignatureValidationError,
)


class TestBancontactPaymentMethod(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bancontact_payment_method = cls.env["pos.electronic.payment"].create({
            "name": "Bancontact",
            "payment_provider": "bancontact_pay",
            "bancontact_ppid": "PPID",
            "bancontact_api_key": "TOKEN",
            "bancontact_usage": "display",
            "integration_type": "qr",
        })
        cls.currency = cls.env.ref("base.EUR")

    def test_payment_in_display_usage(self):
        mock_response = {
            "paymentId": "TEST",
            "_links": {"qrcode": {"href": "MOCK_QR"}},
        }
        with MockHTTPClient(method="POST", url="https://merchant.api.bancontact.net/v3/payments", return_status=200, return_json=mock_response) as mock_request:
            result = self.bancontact_payment_method.start_payment(5.00, self.currency.id, {"shop_name": "SHOP", "payment_uuid": "mockUuid"})
            mock_request.assert_called_once()
            request_body = json.loads(mock_request.calls[0].body)
            request_headers = mock_request.calls[0].headers

        expected_request = {
            "amount": 500,
            "callbackUrl": f"{self.base_url()}/bancontact_pay/webhook?payment_method_id={self.bancontact_payment_method.id}",
            "currency": "EUR",
            "description": f"Payment at {self.env.company.name}\nPOS SHOP",
            "identifyCallbackUrl": f"{self.base_url()}/bancontact_pay/webhook?payment_method_id={self.bancontact_payment_method.id}",
            "reference": "mockUuid",
        }

        self.assertEqual(request_headers["Authorization"], "Bearer TOKEN")
        self.assertDictEqual(request_body, expected_request)
        self.assertDictEqual(result, {"transaction_id": "TEST", "qr_code": "MOCK_QR&f=SVG", "status": "pending"})

    def test_payment_in_sticker_usage(self):
        mock_response = {
            "paymentId": "TEST",
        }
        self.bancontact_payment_method.bancontact_usage = "sticker"
        with MockHTTPClient(method="POST", url="https://merchant.api.bancontact.net/v3/payments/pos", return_status=200, return_json=mock_response) as mock_request:
            result = self.bancontact_payment_method.start_payment(5.00, self.currency.id, {"shop_name": "SHOP", "payment_uuid": "mockUuid"})
            mock_request.assert_called_once()
            request_body = json.loads(mock_request.calls[0].body)
            request_headers = mock_request.calls[0].headers

        expected_request = {
            "amount": 500,
            "callbackUrl": f"{self.base_url()}/bancontact_pay/webhook?payment_method_id={self.bancontact_payment_method.id}",
            "currency": "EUR",
            "description": f"Payment at {self.env.company.name}\nPOS SHOP",
            "identifyCallbackUrl": f"{self.base_url()}/bancontact_pay/webhook?payment_method_id={self.bancontact_payment_method.id}",
            "reference": "mockUuid",
            "posId": f"pm{self.bancontact_payment_method.id}",
            "shopName": "SHOP",
        }

        self.assertEqual(request_headers["Authorization"], "Bearer TOKEN")
        self.assertDictEqual(request_body, expected_request)
        self.assertDictEqual(result, {"transaction_id": "TEST", "qr_code": False, "status": "pending"})

    def test_payment_bad_currency(self):
        with self.assertRaises(ValidationError):
            self.bancontact_payment_method.start_payment(5.00, self.env.ref("base.USD").id)

    @mute_logger("odoo.addons.pos_payment_method_bancontact_pay.models.pos_electronic_payment")
    def test_payment_http_error(self):
        expected_exceptions = {
            400: MissingError,
            401: AccessDenied,
            403: AccessDenied,
            404: UserError,
            422: ValidationError,
            429: AccessDenied,
            500: AccessError,
            503: AccessError,
        }
        for status, expected_exception in expected_exceptions.items():
            with (
                MockHTTPClient(method="POST", url="https://merchant.api.bancontact.net/v3/payments", return_status=status),
                self.assertRaises(expected_exception),
            ):
                self.bancontact_payment_method.start_payment(5.00, self.currency.id)

    def test_cancel(self):
        with MockHTTPClient(method="DELETE", url="https://merchant.api.bancontact.net/v3/payments/TEST", return_status=200) as mock_request:
            self.bancontact_payment_method.cancel_transaction("TEST")
            mock_request.assert_called_once()
            request_headers = mock_request.calls[0].headers

        self.assertEqual(request_headers["Authorization"], "Bearer TOKEN")

    def test_cancel_status_422(self):
        with (
            MockHTTPClient(method="DELETE", url="https://merchant.api.bancontact.net/v3/payments/TEST", return_status=422),
            self.assertRaises(ValidationError) as exception_cm,
        ):
            self.bancontact_payment_method.cancel_transaction("TEST")

        self.assertIn("cannot be cancelled at this time", exception_cm.exception.args[0])

    def test_get_status(self):
        expected_results = {
            "SUCCEEDED": {"status": "paid"},
            "CANCELLED": {"status": "failed", "error": None},
            "FAILED": {"status": "failed", "error": "The QR code payment failed."},
            "EXPIRED": {"status": "failed", "error": "The QR code has expired."},
            "PENDING": {"status": "pending"},
            "IDENTIFIED": {"status": "pending"},
            "AUTHORIZED": {"status": "pending"},
            "PENDING_MERCHANT_ACKNOWLEDGEMENT": {"status": "pending"},
        }
        for status, expected_result in expected_results.items():
            with MockHTTPClient(method="GET", url="https://merchant.api.bancontact.net/v3/payments/TEST", return_status=200, return_json={"status": status}) as mock_request:
                result = self.bancontact_payment_method.get_transaction_status("TEST")
                mock_request.assert_called_once()
                request_headers = mock_request.calls[0].headers

            self.assertEqual(request_headers["Authorization"], "Bearer TOKEN")
            self.assertDictEqual(result, {"transaction_id": "TEST", **expected_result})

    def test_webhook_notification_notifies_the_bus(self):
        payload = {"status": "SUCCEEDED", "paymentId": "TEST"}

        with (
            patch("odoo.addons.pos_payment_method.models.pos_electronic_payment.PosElectronicPayment._notify") as mock_notify,
            patch("odoo.addons.pos_payment_method_bancontact_pay.controllers.signature.BancontactSignatureValidation.verify_signature"),
        ):
            response = self.url_open(f"/bancontact_pay/webhook?payment_method_id={self.bancontact_payment_method.id}", json=payload)

        self.assertEqual(response.status_code, 200)
        mock_notify.assert_called_once_with("TEST", {"status": "paid"})

    @mute_logger("odoo.addons.pos_payment_method_bancontact_pay.controllers.webhook")
    def test_webhook_notification_ignores_invalid_payment_method(self):
        payload = {"status": "SUCCEEDED", "paymentId": "TEST"}

        with (
            patch("odoo.addons.pos_payment_method.models.pos_electronic_payment.PosElectronicPayment._notify") as mock_notify,
            patch("odoo.addons.pos_payment_method_bancontact_pay.controllers.signature.BancontactSignatureValidation.verify_signature"),
        ):
            response = self.url_open("/bancontact_pay/webhook?payment_method_id=999999", json=payload)

        self.assertEqual(response.status_code, 400)
        mock_notify.assert_not_called()

    @mute_logger("odoo.addons.pos_payment_method_bancontact_pay.controllers.webhook")
    def test_webhook_notification_ignores_invalid_signature(self):
        payload = {"status": "SUCCEEDED", "paymentId": "TEST"}

        with (
            patch("odoo.addons.pos_payment_method.models.pos_electronic_payment.PosElectronicPayment._notify") as mock_notify,
            patch("odoo.addons.pos_payment_method_bancontact_pay.controllers.signature.BancontactSignatureValidation.verify_signature", side_effect=BancontactSignatureValidationError),
        ):
            response = self.url_open(f"/bancontact_pay/webhook?payment_method_id={self.bancontact_payment_method.id}", json=payload)

        self.assertEqual(response.status_code, 403)
        mock_notify.assert_not_called()

    @mute_logger("odoo.addons.pos_payment_method_bancontact_pay.controllers.webhook")
    def test_webhook_notification_ignores_invalid_status(self):
        payload = {"status": "UNKNOWN", "paymentId": "TEST"}

        with (
            patch("odoo.addons.pos_payment_method.models.pos_electronic_payment.PosElectronicPayment._notify") as mock_notify,
            patch("odoo.addons.pos_payment_method_bancontact_pay.controllers.signature.BancontactSignatureValidation.verify_signature"),
        ):
            response = self.url_open(f"/bancontact_pay/webhook?payment_method_id={self.bancontact_payment_method.id}", json=payload)

        self.assertEqual(response.status_code, 204)
        mock_notify.assert_not_called()

    def test_download_sticker(self):
        self.authenticate("admin", "admin")
        self.bancontact_payment_method.bancontact_usage = "sticker"
        with (
            MockHTTPClient(method="GET", url="https://qrcodegenerator.api.bancontact.net/qrcode", return_status=200, return_body=b"MOCKQR") as mock_request,
            patch("PIL.Image.open") as image_mock,
        ):
            response = self.url_open(f"/bancontact_pay/sticker/{self.bancontact_payment_method.id}")
            mock_request.assert_called_once()
            query_params = parse_qs(mock_request.calls[0].url.split("?")[1])

        self.assertEqual(image_mock.call_count, 2)
        self.assertEqual(query_params["f"][0], "PNG")
        self.assertEqual(query_params["s"][0], "XL")
        self.assertEqual(query_params["c"][0], f"https://payconiq.com/l/1/PPID/pm{self.bancontact_payment_method.id}")
        self.assertEqual(response.headers["Content-Type"], "image/png")
        self.assertEqual(response.headers["Content-Disposition"], 'attachment; filename="Bancontact.png"')
        self.assertEqual(response.headers["Cache-Control"], "no-cache")
        self.assertEqual(response.status_code, 200)
