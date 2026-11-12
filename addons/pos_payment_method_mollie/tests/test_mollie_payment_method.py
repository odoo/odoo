from unittest.mock import patch

from odoo.tests.common import HttpCase
from odoo.tools import hash_sign, mute_logger, verify_hash_signed


class TestMolliePaymentMethod(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        payment_provider = cls.env["payment.provider"].create({"name": "Mollie Test", "code": "mollie", "mollie_api_key": "mockApiKey"})
        cls.mollie_payment_method = cls.env["pos.electronic.payment"].create({
            "name": "Mollie",
            "payment_provider": "mollie",
            "mollie_terminal_id": "MOLLIE123",
            "mollie_payment_provider_id": payment_provider.id,
            "integration_type": "terminal",
        })
        cls.currency_id = cls.env.company.currency_id.id

    def test_payment(self):
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value={"id": "test", "status": "open"},
        ) as mock_request:
            result = self.mollie_payment_method.start_payment(5.00, self.currency_id)
            method, path = mock_request.call_args.args
            payload = mock_request.call_args.kwargs.get("json")

        expected_webhook_url = f"{self.mollie_payment_method.get_base_url()}/pos_mollie/webhook"
        webhook_url, webhook_payload = payload["webhookUrl"].split("?payload=")
        signed_payload = verify_hash_signed(self.env, "pos_mollie", webhook_payload)

        self.assertEqual(method, "POST")
        self.assertEqual(path, "/payments")
        self.assertEqual(payload["amount"]["value"], "5.00")
        self.assertEqual(payload["description"], f"Odoo Payment Method: Mollie (ID={self.mollie_payment_method.id})")
        self.assertEqual(payload["method"], "pointofsale")
        self.assertEqual(payload["terminalId"], self.mollie_payment_method.mollie_terminal_id)
        self.assertEqual(webhook_url, expected_webhook_url)
        self.assertEqual(signed_payload["payment_method_id"], self.mollie_payment_method.id)
        self.assertEqual(result["transaction_id"], "test")

    def test_refund(self):
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value={"id": "test", "status": "open"},
        ) as mock_request:
            result = self.mollie_payment_method.start_reversal(5.00, self.currency_id, "test")
            method, path = mock_request.call_args.args
            payload = mock_request.call_args.kwargs.get("json")

        self.assertEqual(method, "POST")
        self.assertEqual(path, "/payments/test/refunds")
        self.assertEqual(payload["amount"]["value"], "5.00")
        self.assertEqual(payload["description"], f"Odoo Payment Method: Mollie (ID={self.mollie_payment_method.id})")
        self.assertEqual(result["transaction_id"], "test/refunds/test")

    def test_cancel(self):
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value={"id": "test", "status": "open"},
        ) as mock_request:
            self.mollie_payment_method.cancel_transaction("test")
            method, path = mock_request.call_args.args

        self.assertEqual(method, "DELETE")
        self.assertEqual(path, "/payments/test")

    def test_get_pending(self):
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value={"id": "test", "status": "open"},
        ) as mock_request:
            result = self.mollie_payment_method.get_transaction_status("test")
            method, path = mock_request.call_args.args

        self.assertEqual(method, "GET")
        self.assertEqual(path, "/payments/test")
        self.assertEqual(result["transaction_id"], "test")
        self.assertEqual(result["status"], "pending")

    def test_get_expired(self):
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value={"id": "test", "status": "expired"},
        ):
            result = self.mollie_payment_method.get_transaction_status("test")

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"], self.env._("The payment has timed out."))

    def test_get_failed(self):
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value={"id": "test", "status": "failed", "statusReason": {"message": "Test error"}},
        ):
            result = self.mollie_payment_method.get_transaction_status("test")

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"], "Test error")

    def test_get_success(self):
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value={"id": "test", "status": "paid", "details": {"cardFunding": "Debit", "cardNumber": "1234", "cardLabel": "Visa"}},
        ):
            result = self.mollie_payment_method.get_transaction_status("test")

        self.assertEqual(result["status"], "paid")
        self.assertEqual(result["card_type"], "Debit")
        self.assertEqual(result["card_no"], "1234")
        self.assertEqual(result["card_brand"], "Visa")

    def test_get_pending_refund_returns_success(self):
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value={"id": "test", "status": "pending"},
        ):
            result = self.mollie_payment_method.get_transaction_status("test/refunds/test")

        self.assertEqual(result["status"], "paid")

    def test_webhook_notification_notifies_the_bus(self):
        payload = hash_sign(
            self.env,
            "pos_mollie",
            {"payment_method_id": self.mollie_payment_method.id},
            expiration_hours=27,
        )

        with (
            patch("odoo.addons.pos_payment_method.models.pos_electronic_payment.PosElectronicPayment._notify") as mock_notify,
            patch(
                "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
                return_value={"id": "test", "status": "paid", "details": {"cardFunding": "Debit", "cardNumber": "1234", "cardLabel": "Visa"}},
            ),
        ):
            response = self.url_open(f"/pos_mollie/webhook?id=TEST&payload={payload}", method="POST")

        self.assertEqual(response.status_code, 200)
        mock_notify.assert_called_once_with("TEST", {"transaction_id": "TEST", "status": "paid", "card_type": "Debit", "card_no": "1234", "card_brand": "Visa"})

    @mute_logger("odoo.addons.pos_payment_method_mollie.controllers.webhook")
    def test_webhook_notification_ignores_invalid_payload(self):
        with patch("odoo.addons.pos_payment_method.models.pos_electronic_payment.PosElectronicPayment._notify") as mock_notify:
            response = self.url_open("/pos_mollie/webhook?id=TEST&payload=BAD_PAYLOAD", method="POST")

        self.assertEqual(response.status_code, 200)
        mock_notify.assert_not_called()
