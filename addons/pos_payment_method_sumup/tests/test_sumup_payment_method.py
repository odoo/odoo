import json
from unittest.mock import patch

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import HttpCase, MockHTTPClient
from odoo.tools import hash_sign, mute_logger, verify_hash_signed


class TestSumupPaymentMethod(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sumup_payment_method = cls.env["pos.electronic.payment"].create({
            "name": "SumUp",
            "payment_provider": "sumup",
            "sumup_terminal_id": "SUMUP123",
            "sumup_merchant_code": "MERCHANT",
            "sumup_api_key": "SECRET",
            "integration_type": "terminal",
        })
        cls.currency = cls.env.company.currency_id

    def test_terminal_id_must_be_unique(self):
        with self.assertRaises(ValidationError):
            self.env["pos.electronic.payment"].create({
                "name": "SumUp 2",
                "payment_provider": "sumup",
                "sumup_terminal_id": "SUMUP123",
                "sumup_merchant_code": "MERCHANT",
                "sumup_api_key": "SECRET",
                "integration_type": "terminal",
            })

    def test_payment(self):
        with MockHTTPClient(method="POST", url="https://api.sumup.com/v0.1/merchants/MERCHANT/readers/SUMUP123/checkout", return_status=200, return_json={"data": {"client_transaction_id": "TEST"}}) as mock_request:
            result = self.sumup_payment_method.start_payment(5.00, self.currency.id)
            mock_request.assert_called_once()
            request_body = json.loads(mock_request.calls[0].body)
            request_headers = mock_request.calls[0].headers

        expected_total_amount = {
            "currency": self.currency.name,
            "minor_unit": 2,
            "value": 500,
        }
        return_url = request_body["return_url"]
        token = return_url.split("token=")[1]
        decoded_token = verify_hash_signed(self.env, "pos_sumup", token)

        self.assertEqual(result["transaction_id"], "TEST")
        self.assertEqual(request_headers["Authorization"], "Bearer SECRET")
        self.assertDictEqual(request_body["total_amount"], expected_total_amount)
        self.assertDictEqual(decoded_token, {"payment_method_id": self.sumup_payment_method.id})
        self.assertTrue(return_url.startswith(f"{self.sumup_payment_method.get_base_url()}/pos_sumup/notification?token="))

    def test_payment_network_error(self):
        # Not mocking the request is equivalent to a network exception
        result = self.sumup_payment_method.start_payment(5.00, self.currency.id)

        self.assertEqual(result["error"], self.env._("Could not reach SumUp. Please try again."))

    def test_payment_sumup_error(self):
        with MockHTTPClient(method="POST", url="https://api.sumup.com/v0.1/merchants/MERCHANT/readers/SUMUP123/checkout", return_status=400, return_json={"errors": {"detail": "ERROR"}}):
            result = self.sumup_payment_method.start_payment(5.00, self.currency.id)

        self.assertEqual(result["error"], "ERROR")

    def test_cancel(self):
        with MockHTTPClient(method="POST", url="https://api.sumup.com/v0.1/merchants/MERCHANT/readers/SUMUP123/terminate", return_status=200, return_json={"data": {"client_transaction_id": "TEST"}}) as mock_request:
            result = self.sumup_payment_method.cancel_transaction("TEST")
            mock_request.assert_called_once()
            request_headers = mock_request.calls[0].headers

        self.assertEqual(request_headers["Authorization"], "Bearer SECRET")
        self.assertIsInstance(result, dict)

    def test_reversal(self):
        with (
            MockHTTPClient(method="GET", url="https://api.sumup.com/v2.1/merchants/MERCHANT/transactions", return_status=200, return_json={"id": "TEST_ID"}) as mock_transaction_request,
            MockHTTPClient(method="POST", url="https://api.sumup.com/v1.0/merchants/MERCHANT/payments/TEST_ID/refunds", return_status=200, return_json={}) as mock_refund_request,
        ):
            result = self.sumup_payment_method.start_reversal(5.00, self.currency.id, "TEST")
            mock_transaction_request.assert_called_once()
            mock_refund_request.assert_called_once()
            transaction_request_params = mock_transaction_request.calls[0].url.split("?")[1]
            request_body = json.loads(mock_refund_request.calls[0].body)
            transaction_request_headers = mock_transaction_request.calls[0].headers
            refund_request_headers = mock_refund_request.calls[0].headers

        expected_result = {
            "transaction_id": "TEST_ID",
            "status": "paid",
        }

        self.assertEqual(transaction_request_headers["Authorization"], "Bearer SECRET")
        self.assertEqual(transaction_request_params, "client_transaction_id=TEST")

        self.assertEqual(refund_request_headers["Authorization"], "Bearer SECRET")
        self.assertEqual(request_body["amount"], 500)
        self.assertDictEqual(result, expected_result)

    def test_reversal_bad_transaction_id(self):
        with (
            MockHTTPClient(method="GET", url="https://api.sumup.com/v2.1/merchants/MERCHANT/transactions", return_status=404) as mock_request,
        ):
            with self.assertRaises(UserError):
                self.sumup_payment_method.start_reversal(5.00, self.currency.id, "TEST")
            mock_request.assert_called_once()

    def test_get_success(self):
        with MockHTTPClient(method="GET", url="https://api.sumup.com/v2.1/merchants/MERCHANT/transactions", return_status=200, return_json={"status": "SUCCESSFUL"}) as mock_request:
            result = self.sumup_payment_method.get_transaction_status("TEST")
            mock_request.assert_called_once()
            request_params = mock_request.calls[0].url.split("?")[1]
            request_headers = mock_request.calls[0].headers

        self.assertEqual(request_headers["Authorization"], "Bearer SECRET")
        self.assertEqual(request_params, "client_transaction_id=TEST")
        self.assertEqual(result["status"], "paid")

    def test_get_pending(self):
        with MockHTTPClient(method="GET", url="https://api.sumup.com/v2.1/merchants/MERCHANT/transactions", return_status=200, return_json={"status": "PENDING"}):
            result = self.sumup_payment_method.get_transaction_status("TEST")

        self.assertEqual(result["status"], "pending")

    def test_get_failed(self):
        with MockHTTPClient(method="GET", url="https://api.sumup.com/v2.1/merchants/MERCHANT/transactions", return_status=200, return_json={"status": "FAILED"}):
            result = self.sumup_payment_method.get_transaction_status("TEST")

        self.assertEqual(result["status"], "failed")

    def test_webhook_notification_notifies_the_bus(self):
        token = hash_sign(
            self.env,
            "pos_sumup",
            {"payment_method_id": self.sumup_payment_method.id},
            expiration_hours=1,
        )
        payload = {"payload": {"client_transaction_id": "ctid1", "status": "successful"}}

        with patch(
            "odoo.addons.pos_payment_method.models.pos_electronic_payment.PosElectronicPayment._notify",
        ) as mock_notify:
            response = self.url_open(f"/pos_sumup/notification?token={token}", json=payload)

        self.assertEqual(response.status_code, 200)
        mock_notify.assert_called_once_with("ctid1", {"status": "paid"})

    @mute_logger("odoo.addons.pos_payment_method_sumup.controllers.webhook")
    def test_webhook_notification_ignores_invalid_token(self):
        payload = {"payload": {"client_transaction_id": "ctid1", "status": "successful"}}

        with (
            patch(
                "odoo.addons.pos_payment_method.models.pos_electronic_payment.PosElectronicPayment._notify",
            ) as mock_notify,
        ):
            self.url_open("/pos_sumup/notification?token=not_a_valid_token", json=payload)

        mock_notify.assert_not_called()
