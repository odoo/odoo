import json
from unittest.mock import patch

from odoo.tests.common import HttpCase, MockHTTPClient
from odoo.tools import hmac, mute_logger


class TestAdyenPaymentMethod(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.adyen_payment_method = cls.env["pos.electronic.payment"].create({
            "name": "Adyen",
            "payment_provider": "adyen",
            "adyen_api_key": "TEST",
            "adyen_terminal_identifier": "ADYEN123",
            "adyen_merchant_account": "ODOO",
            "adyen_test_mode": False,
            "adyen_ask_customer_for_tip": True,
            "integration_type": "terminal",
        })
        cls.currency = cls.env.company.currency_id

    def _get_expected_message_header(self, type: str, service_id: str):
        return {
            "MessageCategory": type,
            "MessageClass": "Service",
            "MessageType": "Request",
            "POIID": "ADYEN123",
            "ProtocolVersion": "3.0",
            "SaleID": f"Odoo Payment Method: Adyen (ID={self.adyen_payment_method.id})",
            "ServiceID": service_id,
        }

    def test_payment(self):
        with MockHTTPClient(method="POST", url="https://terminal-api-live.adyen.com/async", return_status=200, return_json={}) as mock_request:
            result = self.adyen_payment_method.start_payment(5.00, self.currency.id)
            mock_request.assert_called_once()
            request_body = json.loads(mock_request.calls[0].body)

        service_id = result["transaction_id"].split("/")[1]
        expected_header = self._get_expected_message_header("Payment", service_id)
        expected_payment_transaction = {
            "AmountsReq": {"Currency": self.currency.name, "RequestedAmount": 5.0},
        }
        expected_hmac = hmac(self.env, "pos_adyen", (self.adyen_payment_method.id, "ADYEN123", service_id))
        expected_sale_data = f"authorisationType=FinalAuth&manualCapture=false&metadata.payment_method_id={self.adyen_payment_method.id}&metadata.pos_hmac={expected_hmac}"

        self.assertEqual(result["transaction_id"], f"Payment/{service_id}")
        self.assertDictEqual(request_body["SaleToPOIRequest"]["MessageHeader"], expected_header)
        self.assertDictEqual(request_body["SaleToPOIRequest"]["PaymentRequest"]["PaymentTransaction"], expected_payment_transaction)
        self.assertEqual(request_body["SaleToPOIRequest"]["PaymentRequest"]["SaleData"]["SaleToAcquirerData"], expected_sale_data)

    def test_payment_allow_adjustments(self):
        with MockHTTPClient(method="POST", url="https://terminal-api-live.adyen.com/async", return_status=200, return_json={}) as mock_request:
            result = self.adyen_payment_method.start_payment(5.00, self.currency.id, {"allow_adjustments": True})
            mock_request.assert_called_once()
            request_body = json.loads(mock_request.calls[0].body)

        service_id = result["transaction_id"].split("/")[1]
        expected_hmac = hmac(self.env, "pos_adyen", (self.adyen_payment_method.id, "ADYEN123", service_id))
        expected_sale_data = f"authorisationType=PreAuth&manualCapture=true&metadata.payment_method_id={self.adyen_payment_method.id}&metadata.pos_hmac={expected_hmac}"

        self.assertEqual(request_body["SaleToPOIRequest"]["PaymentRequest"]["SaleData"]["SaleToAcquirerData"], expected_sale_data)

    def test_payment_allow_tips(self):
        with MockHTTPClient(method="POST", url="https://terminal-api-live.adyen.com/async", return_status=200, return_json={}) as mock_request:
            result = self.adyen_payment_method.start_payment(5.00, self.currency.id, {"allow_tips": True})
            mock_request.assert_called_once()
            request_body = json.loads(mock_request.calls[0].body)

        service_id = result["transaction_id"].split("/")[1]
        expected_hmac = hmac(self.env, "pos_adyen", (self.adyen_payment_method.id, "ADYEN123", service_id))
        expected_sale_data = f"authorisationType=FinalAuth&manualCapture=false&tenderOption=AskGratuity&metadata.payment_method_id={self.adyen_payment_method.id}&metadata.pos_hmac={expected_hmac}"

        self.assertEqual(request_body["SaleToPOIRequest"]["PaymentRequest"]["SaleData"]["SaleToAcquirerData"], expected_sale_data)

    def test_reversal(self):
        with MockHTTPClient(method="POST", url="https://terminal-api-live.adyen.com/async", return_status=200, return_json={}) as mock_request:
            result = self.adyen_payment_method.start_reversal(5.00, self.currency.id, "test", {"original_payment_timestamp": "fake_timestamp"})
            mock_request.assert_called_once()
            request_body = json.loads(mock_request.calls[0].body)

        service_id = result["transaction_id"].split("/")[1]
        expected_header = self._get_expected_message_header("Reversal", service_id)
        expected_original_transaction = {
            "TransactionID": "test",
            "TimeStamp": "fake_timestamp",
        }
        expected_hmac = hmac(self.env, "pos_adyen", (self.adyen_payment_method.id, "ADYEN123", service_id))
        expected_sale_data = f"currency={self.currency.name}&metadata.payment_method_id={self.adyen_payment_method.id}&metadata.pos_hmac={expected_hmac}"

        self.assertEqual(result["transaction_id"], f"Reversal/{service_id}")
        self.assertDictEqual(request_body["SaleToPOIRequest"]["MessageHeader"], expected_header)
        self.assertEqual(request_body["SaleToPOIRequest"]["ReversalRequest"]["ReversalReason"], "MerchantCancel")
        self.assertEqual(request_body["SaleToPOIRequest"]["ReversalRequest"]["ReversedAmount"], 5.0)
        self.assertDictEqual(request_body["SaleToPOIRequest"]["ReversalRequest"]["OriginalPOITransaction"]["POITransactionID"], expected_original_transaction)
        self.assertEqual(request_body["SaleToPOIRequest"]["ReversalRequest"]["SaleData"]["SaleToAcquirerData"], expected_sale_data)

    def test_cancel(self):
        with MockHTTPClient(method="POST", url="https://terminal-api-live.adyen.com/sync", return_status=200, return_json={}) as mock_request:
            self.adyen_payment_method.cancel_transaction("Payment/test")
            mock_request.assert_called_once()
            request_body = json.loads(mock_request.calls[0].body)

        expected_abort_request = {
            "AbortReason": "MerchantAbort",
            "MessageReference": {
                "MessageCategory": "Payment",
                "ServiceID": "test",
            },
        }
        self.assertDictEqual(request_body["SaleToPOIRequest"]["AbortRequest"], expected_abort_request)

    def test_adjust(self):
        mock_response = {
            "adjustAuthorisationData": "DATA2",
        }
        with MockHTTPClient(method="POST", url="https://checkout-live.adyen.com/v72/payments/Payment/test/amountUpdates", return_status=200, return_json=mock_response) as mock_request:
            result = self.adyen_payment_method.adjust_payment(5.00, self.currency.id, "Payment/test", {"metadata": {"adjust_authorisation_data": "DATA", "payment_authorized_timestamp": 0}})
            mock_request.assert_called_once()
            request_body = json.loads(mock_request.calls[0].body)

        self.assertEqual(request_body["adjustAuthorisationData"], "DATA")
        self.assertDictEqual(request_body["amount"], {"currency": self.currency.name, "value": 500})
        self.assertEqual(request_body["merchantAccount"], "ODOO")
        self.assertEqual(result["metadata"]["adjust_authorisation_data"], "DATA2")
        self.assertEqual(result["status"], "paid")

    def test_capture(self):
        with MockHTTPClient(method="POST", url="https://checkout-live.adyen.com/v72/payments/Payment/test/captures", return_status=200, return_json={}) as mock_request:
            result = self.adyen_payment_method.capture_payment(5.00, self.currency.id, "Payment/test", {"metadata": {"payment_authorized_timestamp": 0}})
            mock_request.assert_called_once()
            request_body = json.loads(mock_request.calls[0].body)

        self.assertDictEqual(request_body["amount"], {"currency": self.currency.name, "value": 500})
        self.assertEqual(request_body["merchantAccount"], "ODOO")
        self.assertEqual(result["status"], "paid")

    def test_get_pending(self):
        mock_response = {
            "SaleToPOIResponse": {
                "TransactionStatusResponse": {
                    "Response": {
                        "ErrorCondition": "InProgress",
                    },
                },
            },
        }
        with MockHTTPClient(method="POST", url="https://terminal-api-live.adyen.com/sync", return_status=200, return_json=mock_response) as mock_request:
            result = self.adyen_payment_method.get_transaction_status("Payment/test")
            mock_request.assert_called_once()
            request_body = json.loads(mock_request.calls[0].body)

        self.assertDictEqual(request_body["SaleToPOIRequest"]["TransactionStatusRequest"]["MessageReference"], {"ServiceID": "test", "MessageCategory": "Payment"})
        self.assertEqual(result["status"], "pending")

    def test_get_failed(self):
        mock_response = {
            "SaleToPOIResponse": {
                "TransactionStatusResponse": {
                    "Response": {
                        "Result": "Failure",
                        "ErrorCondition": "Test error",
                    },
                },
            },
        }
        with MockHTTPClient(method="POST", url="https://terminal-api-live.adyen.com/sync", return_status=200, return_json=mock_response) as mock_request:
            result = self.adyen_payment_method.get_transaction_status("Payment/test")
            mock_request.assert_called_once()
            json.loads(mock_request.calls[0].body)

        self.assertEqual(result["status"], "failed")
        self.assertIn("Test error", result["error"])

    def test_get_success(self):
        mock_response = {
            "SaleToPOIResponse": {
                "TransactionStatusResponse": {
                    "Response": {
                        "Result": "Success",
                    },
                    "RepeatedMessageResponse": {
                        "RepeatedResponseMessageBody": {
                            "PaymentResponse": {
                                "Response": {
                                    "Result": "Success",
                                    "AdditionalResponse": "cardType=Visa&cardHolderName=Test",
                                },
                                "POIData": {
                                    "POITransactionID": {
                                        "TransactionID": "test-transaction-id",
                                    },
                                },
                            },
                        },
                    },
                },
            },
        }
        with MockHTTPClient(method="POST", url="https://terminal-api-live.adyen.com/sync", return_status=200, return_json=mock_response) as mock_request:
            result = self.adyen_payment_method.get_transaction_status("Payment/test")
            mock_request.assert_called_once()
            json.loads(mock_request.calls[0].body)

        self.assertEqual(result["status"], "paid")
        self.assertEqual(result["card_type"], "Visa")
        self.assertEqual(result["cardholder_name"], "Test")

    def test_webhook_notification_notifies_the_bus(self):
        hmac_payload = hmac(
            self.env,
            "pos_adyen",
            (self.adyen_payment_method.id, "ADYEN123", "TEST"),
        )
        payload = {
            "SaleToPOIResponse": {
                "MessageHeader": {
                    "ProtocolVersion": "3.0",
                    "MessageClass": "Service",
                    "MessageType": "Response",
                    "MessageCategory": "Payment",
                    "POIID": "ADYEN123",
                    "ServiceID": "TEST",
                },
                "PaymentResponse": {
                    "Response": {
                        "Result": "Success",
                        "AdditionalResponse": f"metadata.pos_hmac={hmac_payload}&metadata.payment_method_id={self.adyen_payment_method.id}",
                    },
                    "POIData": {
                        "POITransactionID": {
                            "TransactionID": "FINAL",
                        },
                    },
                },
            },
        }

        with (
            patch("odoo.addons.pos_payment_method.models.pos_electronic_payment.PosElectronicPayment._notify") as mock_notify,
        ):
            response = self.url_open("/pos_adyen/notification", json=payload)

        self.assertEqual(response.status_code, 200)
        mock_notify.assert_called_once()
        self.assertEqual(mock_notify.call_args.args[0], "Payment/TEST")
        self.assertEqual(mock_notify.call_args.args[1]["status"], "paid")

    @mute_logger("odoo.addons.pos_payment_method_adyen.controllers.webhook")
    def test_webhook_bad_hmac_is_ignored(self):
        payload = {
            "SaleToPOIResponse": {
                "MessageHeader": {
                    "ProtocolVersion": "3.0",
                    "MessageClass": "Service",
                    "MessageType": "Response",
                    "MessageCategory": "Payment",
                    "POIID": "ADYEN123",
                    "ServiceID": "TEST",
                },
                "PaymentResponse": {
                    "Response": {
                        "Result": "Success",
                        "AdditionalResponse": f"metadata.pos_hmac=BAD_HMAC&metadata.payment_method_id={self.adyen_payment_method.id}",
                    },
                },
            },
        }

        with (
            patch("odoo.addons.pos_payment_method.models.pos_electronic_payment.PosElectronicPayment._notify") as mock_notify,
        ):
            response = self.url_open("/pos_adyen/notification", json=payload)

        self.assertEqual(response.status_code, 200)
        mock_notify.assert_not_called()
