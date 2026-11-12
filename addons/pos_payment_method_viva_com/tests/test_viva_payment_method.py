import base64
import json
from unittest.mock import patch

from odoo.tests.common import HttpCase, MockHTTPClient
from odoo.tools import mute_logger


class TestVivaPaymentMethod(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.viva_payment_method = cls.env["pos.electronic.payment"].create({
            "name": "Viva.com",
            "payment_provider": "viva_com",
            "viva_com_api_key": "KEY",
            "viva_com_client_secret": "SECRET",
            "viva_com_client_id": "CLIENT_ID",
            "viva_com_merchant_id": "MERCHANT_ID",
            "viva_com_terminal_id": "1234",
            "viva_com_bearer_token": "TOKEN",
            "integration_type": "terminal",
        })
        cls.currency = cls.env.company.currency_id

    def test_payment(self):
        with MockHTTPClient(method="POST", url="https://api.vivapayments.com/ecr/v1/transactions:sale", return_status=200, return_json={"success": True}) as mock_request:
            result = self.viva_payment_method.start_payment(5.00, self.currency.id)
            mock_request.assert_called_once()
            request_body = json.loads(mock_request.calls[0].body)
            request_headers = mock_request.calls[0].headers

        session_id = result["transaction_id"]
        expected_request = {
            "sessionId": session_id,
            "terminalId": "1234",
            "cashRegisterId": f"Odoo-{self.viva_payment_method.id}",
            "amount": 500,
            "currencyCode": self.currency.iso_numeric,
            "merchantReference": session_id,
            "tipAmount": 0,
        }

        self.assertEqual(request_headers["Authorization"], "Bearer TOKEN")
        self.assertTrue(session_id.startswith("Odoo-"))
        self.assertDictEqual(request_body, expected_request)
        self.assertDictEqual(result, {"transaction_id": session_id, "status": "pending"})

    def test_refund(self):
        with MockHTTPClient(method="POST", url="https://api.vivapayments.com/ecr/v1/transactions:unreferenced-refund", return_status=200, return_json={"success": True}) as mock_request:
            result = self.viva_payment_method.start_refund(5.00, self.currency.id)
            mock_request.assert_called_once()
            request_body = json.loads(mock_request.calls[0].body)
            request_headers = mock_request.calls[0].headers

        session_id = result["transaction_id"]
        expected_request = {
            "sessionId": session_id,
            "terminalId": "1234",
            "cashRegisterId": f"Odoo-{self.viva_payment_method.id}",
            "amount": 500,
            "currencyCode": self.currency.iso_numeric,
            "merchantReference": session_id,
            "tipAmount": 0,
        }

        self.assertEqual(request_headers["Authorization"], "Bearer TOKEN")
        self.assertTrue(session_id.startswith("Odoo-"))
        self.assertDictEqual(request_body, expected_request)
        self.assertDictEqual(result, {"transaction_id": session_id, "status": "pending"})

    def test_reversal(self):
        with MockHTTPClient(method="POST", url="https://api.vivapayments.com/ecr/v1/transactions:refund", return_status=200, return_json={"success": True}) as mock_request:
            result = self.viva_payment_method.start_reversal(5.00, self.currency.id, "TEST")
            mock_request.assert_called_once()
            request_body = json.loads(mock_request.calls[0].body)
            request_headers = mock_request.calls[0].headers

        session_id = result["transaction_id"]
        expected_request = {
            "sessionId": session_id,
            'parentSessionId': "TEST",
            "terminalId": "1234",
            "cashRegisterId": f"Odoo-{self.viva_payment_method.id}",
            "amount": 500,
            "currencyCode": self.currency.iso_numeric,
            "merchantReference": session_id,
            "tipAmount": 0,
        }

        self.assertEqual(request_headers["Authorization"], "Bearer TOKEN")
        self.assertTrue(session_id.startswith("Odoo-"))
        self.assertDictEqual(request_body, expected_request)
        self.assertDictEqual(result, {"transaction_id": session_id, "status": "pending"})

    def test_cancel(self):
        with MockHTTPClient(method="DELETE", url=f"https://api.vivapayments.com/ecr/v1/sessions/TEST?cashRegisterId=Odoo-{self.viva_payment_method.id}", return_status=200, return_json={"success": True}) as mock_request:
            self.viva_payment_method.cancel_transaction("TEST")
            mock_request.assert_called_once()
            request_headers = mock_request.calls[0].headers

        self.assertEqual(request_headers["Authorization"], "Bearer TOKEN")

    def test_get_success(self):
        mock_response = {
            "success": True,
            "cardType": "debit",
            "applicationLabel": "visa",
            "primaryAccountNumberMasked": "1234",
        }
        with MockHTTPClient(method="GET", url="https://api.vivapayments.com/ecr/v1/sessions/TEST", return_status=200, return_json=mock_response) as mock_request:
            result = self.viva_payment_method.get_transaction_status("TEST")
            mock_request.assert_called_once()
            request_headers = mock_request.calls[0].headers

        self.assertEqual(request_headers["Authorization"], "Bearer TOKEN")
        self.assertDictEqual(
            result,
            {
                "transaction_id": "TEST",
                "status": "paid",
                "card_type": "debit",
                "card_brand": "visa",
                "card_no": "1234",
            },
        )

    def test_get_failure(self):
        mock_response = {
            "success": False,
            "message": "ERROR",
        }
        with MockHTTPClient(method="GET", url="https://api.vivapayments.com/ecr/v1/sessions/TEST", return_status=200, return_json=mock_response) as mock_request:
            result = self.viva_payment_method.get_transaction_status("TEST")
            mock_request.assert_called_once()
            request_headers = mock_request.calls[0].headers

        self.assertEqual(request_headers["Authorization"], "Bearer TOKEN")
        self.assertDictEqual(result, {"transaction_id": "TEST", "status": "failed", "error": "ERROR"})

    def test_get_pending(self):
        with MockHTTPClient(method="GET", url="https://api.vivapayments.com/ecr/v1/sessions/TEST", return_status=202, return_json={}) as mock_request:
            result = self.viva_payment_method.get_transaction_status("TEST")
            mock_request.assert_called_once()
            request_headers = mock_request.calls[0].headers

        self.assertEqual(request_headers["Authorization"], "Bearer TOKEN")
        self.assertDictEqual(result, {"transaction_id": "TEST", "status": "pending"})

    def test_token_refresh(self):
        with (
            MockHTTPClient(method="POST", url="https://api.vivapayments.com/ecr/v1/transactions:sale", return_status=lambda req: 200 if req.headers["Authorization"] == "Bearer TOKEN2" else 401) as payment_request,
            MockHTTPClient(method="POST", url="https://accounts.vivapayments.com/connect/token", return_status=200, return_json={"access_token": "TOKEN2"}) as token_request,
        ):
            self.viva_payment_method.start_payment(5.00, self.currency.id)
            payment_request.assert_called(2)
            token_request.assert_called_once()
            first_attempt_headers = payment_request.calls[0].headers
            token_request_headers = token_request.calls[0].headers
            token_request_body = token_request.calls[0].body
            second_attempt_headers = payment_request.calls[1].headers

        self.assertEqual(first_attempt_headers["Authorization"], "Bearer TOKEN")
        self.assertEqual(token_request_headers["Authorization"], f"Basic {base64.b64encode(b"CLIENT_ID:SECRET").decode()}")
        self.assertEqual(token_request_body, "grant_type=client_credentials")
        self.assertEqual(second_attempt_headers["Authorization"], "Bearer TOKEN2")

    def test_webhook_notification_notifies_the_bus(self):
        payload = {"EventData": {"TerminalId": "1234", "MerchantTrns": "TEST"}, "EventTypeId": 1796}
        mock_response = {
            "success": True,
            "cardType": "debit",
            "applicationLabel": "visa",
            "primaryAccountNumberMasked": "1234",
        }

        with (
            patch("odoo.addons.pos_payment_method.models.pos_electronic_payment.PosElectronicPayment._notify") as mock_notify,
            MockHTTPClient(method="GET", url="https://api.vivapayments.com/ecr/v1/sessions/TEST", return_status=200, return_json=mock_response),
        ):
            response = self.url_open("/pos_viva_com/notification?token=viva_com_test", json=payload)

        self.assertEqual(response.status_code, 200)
        mock_notify.assert_called_once_with("TEST", {"status": "paid", "card_type": "debit", "card_brand": "visa", "card_no": "1234", "transaction_id": "TEST"})

    @mute_logger("odoo.addons.pos_payment_method_viva_com.controllers.webhook")
    def test_webhook_notification_ignores_invalid_token(self):
        payload = {"EventData": {"TerminalId": "1234", "MerchantTrns": "TEST"}, "EventTypeId": 1796}

        with patch("odoo.addons.pos_payment_method.models.pos_electronic_payment.PosElectronicPayment._notify") as mock_notify:
            response = self.url_open("/pos_viva_com/notification?token=BAD_TOKEN", json=payload)

        self.assertEqual(response.status_code, 404)
        mock_notify.assert_not_called()
