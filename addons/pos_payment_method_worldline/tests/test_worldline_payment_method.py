import json
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from requests.exceptions import RequestException, Timeout

from odoo.tests.common import HttpCase, MockHTTPClient
from odoo.tools import hash_sign, mute_logger, verify_hash_signed

from odoo.addons.pos_payment_method_worldline.models.worldline_api_request import (
    WorldlineApiRequest,
)


class TestWorldlinePaymentMethod(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.worldline_payment_method = cls.env["pos.electronic.payment"].create({
            "name": "Worldline",
            "payment_provider": "worldline",
            "worldline_terminal_id": "WORLDLINE123",
            "worldline_merchant_id": "MERCHANT123",
            "worldline_api_key": "SECRET",
            "integration_type": "terminal",
        })
        cls.currency = cls.env.company.currency_id
        cls.worldline_base_url = "https://api.terminal.global.worldline-solutions.com/api/v2/merchants/MERCHANT123/terminals/WORLDLINE123"

    def _check_auth_header(self, req):
        self.assertEqual(req.headers["Authorization"], "Bearer SECRET")

    def test_payment(self):
        with MockHTTPClient(
            method="POST",
            url=f"{self.worldline_base_url}/payments",
            return_status=200,
            return_json={},
            side_effect=self._check_auth_header,
        ) as mock_request:
            result = self.worldline_payment_method.start_payment(5.00, self.currency.id)
            mock_request.assert_called_once()
            request_body = json.loads(mock_request.calls[0].body)

        service_request = request_body["SaleToPOIServiceRequest"]["ServiceRequest"]
        payment_transaction = service_request["PaymentRequest"]["PaymentTransaction"]
        self.assertEqual(payment_transaction["TransactionType"], "CardPayment")
        self.assertEqual(payment_transaction["TransactionIdentification"]["TransactionReference"], result["transaction_id"])
        self.assertEqual(payment_transaction["TransactionDetails"]["TotalAmount"], 5.00)
        self.assertNotIn("OriginalTransaction", payment_transaction)
        self.assertEqual(
            service_request["Environment"]["POI"]["Identification"]["Identification"],
            self.worldline_payment_method.worldline_terminal_id,
        )
        header = request_body["SaleToPOIServiceRequest"]["Header"]
        webhook_url = urlsplit(header["WebhookUrl"])
        self.assertEqual(f"{webhook_url.scheme}://{webhook_url.netloc}{webhook_url.path}", self.worldline_payment_method.worldline_webhook_url)
        webhook_payload = parse_qs(webhook_url.query)["payload"][0]
        self.assertEqual(verify_hash_signed(self.env(su=True), "pos_worldline", webhook_payload), {
            "exchange_id": header["ExchangeIdentification"],
            "payment_method_id": self.worldline_payment_method.id,
        })

    def test_refund(self):
        with MockHTTPClient(
            method="POST",
            url=f"{self.worldline_base_url}/payments",
            return_status=200,
            return_json={},
            side_effect=self._check_auth_header,
        ) as mock_request:
            self.worldline_payment_method.start_refund(5.00, self.currency.id)
            mock_request.assert_called_once()
            request_body = json.loads(mock_request.calls[0].body)

        payment_transaction = request_body["SaleToPOIServiceRequest"]["ServiceRequest"]["PaymentRequest"]["PaymentTransaction"]
        self.assertEqual(payment_transaction["TransactionType"], "Refund")
        self.assertEqual(payment_transaction["TransactionDetails"]["TotalAmount"], 5.00)
        self.assertNotIn("OriginalTransaction", payment_transaction)

    @mute_logger('odoo.addons.pos_payment_method_worldline.models.worldline_api_request')
    def test_payment_error(self):
        with MockHTTPClient(
            method="POST",
            url=f"{self.worldline_base_url}/payments",
            return_status=400,
            return_json={"message": "Invalid terminal"},
            side_effect=self._check_auth_header,
        ) as mock_request:
            result = self.worldline_payment_method.start_payment(5.00, self.currency.id)
            mock_request.assert_called_once()

        self.assertDictEqual(result, {"status": "failed", "error": "Invalid terminal"})

    @mute_logger('odoo.addons.pos_payment_method_worldline.models.worldline_api_request')
    def test_payment_request_exception(self):
        with patch(
            "odoo.addons.pos_payment_method_worldline.models.worldline_api_request.requests.post",
            side_effect=RequestException("Connection failed"),
        ):
            result = self.worldline_payment_method.start_payment(5.00, self.currency.id)

        self.assertEqual(result, {"status": "failed", "error": "Connection failed"})

    @mute_logger('odoo.addons.pos_payment_method_worldline.models.worldline_api_request')
    def test_payment_request_timeout(self):
        with patch(
            "odoo.addons.pos_payment_method_worldline.models.worldline_api_request.requests.post",
            side_effect=Timeout(),
        ):
            result = self.worldline_payment_method.start_payment(5.00, self.currency.id)

        self.assertEqual(result, {
            "status": "failed",
            "error": "Worldline request to terminal WORLDLINE123 timed out. Please make sure the terminal is connected to internet and try again.",
        })

    def test_transaction_status(self):
        approved_response = {
            "data": {
                "SaleToPOIMessageStatusResponse": {
                    "StatusResponse": {
                        "Environment": {"Card": {"CardBrand": "MAESTRO", "MaskedPAN": "XXXXXXXXXXXXX5006"}},
                        "MessageStatusResponseData": {
                            "TransactionResponse": {"Response": "Successful"},
                            "RepeatedPaymentResponse": {
                                "POITransactionIdentification": {"TransactionReference": "2;00999100022;92986866332;"},
                                "RetailerPaymentResult": {
                                    "TransactionResponse": {
                                        "AuthorisationResult": {
                                            "ResponseToAuthorisation": {"Response": "Approved"},
                                            "AuthorisationCode": "678803",
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            },
        }
        with MockHTTPClient(
            method="POST",
            url=f"{self.worldline_base_url}/status/sync",
            return_status=200,
            return_json=approved_response,
            side_effect=self._check_auth_header,
        ) as mock_request:
            result = self.worldline_payment_method.get_transaction_status("exchange-id")
            mock_request.assert_called_once()
            request_body = json.loads(mock_request.calls[0].body)

        status_request_data = request_body["SaleToPOIMessageStatusRequest"]["StatusRequest"]["MessageStatusRequestData"]
        self.assertEqual(status_request_data["ExchangeIdentification"], "exchange-id")
        self.assertEqual(result, {
            "status": "paid",
            "transaction_id": "exchange-id",
            "final_transaction_id": "2;00999100022;92986866332;",
            "card_brand": "MAESTRO",
            "card_no": "XXXXXXXXXXXXX5006",
            "payment_method_authcode": "678803",
        })

    @mute_logger('odoo.addons.pos_payment_method_worldline.models.worldline_api_request')
    def test_transaction_status_pending(self):
        in_progress_response = {
            "data": {
                "SaleToPOIMessageStatusResponse": {
                    "StatusResponse": {
                        "MessageStatusResponseData": {
                            "TransactionResponse": {"Response": "Failed", "ResponseReason": "InProgress"},
                        },
                    },
                },
            },
        }
        # Status returned while the transaction (payment or refund) waits for a card on the terminal
        waiting_card_response = {
            "data": {
                "SaleToPOIMessageStatusResponse": {
                    "StatusResponse": {
                        "MessageStatusResponseData": {
                            "TransactionResponse": {"Response": "Successful"},
                        },
                    },
                },
            },
        }
        for status_code, json_data, expected in [
            (200, in_progress_response, {"status": "pending", "transaction_id": "exchange-id"}),
            (200, waiting_card_response, {"status": "pending", "transaction_id": "exchange-id"}),
            (202, {"requestId": "550e8400-e29b-41d4-a716-446655440000"}, {"status": "pending", "transaction_id": "exchange-id"}),  # Terminal timeout
            (400, {"message": "Invalid terminal"}, {"error": "Invalid terminal", "transaction_id": "exchange-id"}),
        ]:
            with (
                self.subTest(status_code=status_code),
                MockHTTPClient(
                    method="POST",
                    url=f"{self.worldline_base_url}/status/sync",
                    return_status=status_code,
                    return_json=json_data,
                    side_effect=self._check_auth_header,
                ) as mock_request,
            ):
                result = self.worldline_payment_method.get_transaction_status("exchange-id")
                mock_request.assert_called_once()
                self.assertEqual(result, expected)

    def test_transaction_status_failed(self):
        failed_response = {
            "data": {
                "SaleToPOIMessageStatusResponse": {
                    "StatusResponse": {
                        "MessageStatusResponseData": {
                            "TransactionResponse": {
                                "Response": "Failed",
                                "ResponseReason": "Cancel",
                                "AdditionalResponseInformation": "WPI_ERR_COND_USER_CANCEL:EFT_E_CARDHOLDER_ABORT",
                            },
                            "RepeatedPaymentResponse": {
                                "SaleTransactionIdentification": {},
                                "POITransactionIdentification": {},
                                "RetailerPaymentResult": {
                                    "TransactionType": "CardPayment",
                                    "TransactionResponse": {"AuthorisationResult": {"ResponseToAuthorisation": {"Response": "Declined"}}},
                                },
                                "PaymentReceipt": [],
                            },
                        },
                    },
                },
            },
        }
        with MockHTTPClient(
            method="POST",
            url=f"{self.worldline_base_url}/status/sync",
            return_status=200,
            return_json=failed_response,
            side_effect=self._check_auth_header,
        ) as mock_request:
            result = self.worldline_payment_method.get_transaction_status("exchange-id")
            mock_request.assert_called_once()

        self.assertEqual(result, {
            "status": "failed",
            "transaction_id": "exchange-id",
            "error": "Transaction was cancelled on the terminal. Please try again.",
        })

    @mute_logger('odoo.addons.pos_payment_method_worldline.models.worldline_api_request')
    def test_transaction_status_timeout(self):
        # The transaction may still complete on the terminal: it stays pending, but the error is reported.
        with patch(
            "odoo.addons.pos_worldline.models.worldline_api_request.requests.post",
            side_effect=Timeout(),
        ):
            result = self.worldline_payment_method.get_transaction_status("exchange-id")

        self.assertEqual(result, {
            "transaction_id": "exchange-id",
            "error": "Worldline request to terminal WORLDLINE123 timed out. Please make sure the terminal is connected to internet and try again.",
        })

    def test_get_error_message(self):
        for response, expected in [
            ({"Response": "Successful"}, None),
            (
                {"Response": "Failed", "ResponseReason": "Busy", "AdditionalResponseInformation": "WPI_ERR_COND_BUSY:Busy, another request already running"},
                "The terminal is currently busy with a different transaction. Please try again later.",
            ),
            (
                {"Response": "Failed", "ResponseReason": "NotAllowed", "AdditionalResponseInformation": "WPI_ERR_COND_INVALID_CURRENCY:EP2_E_CURR_NOT_INITIALIZED"},
                "This currency is not supported by the terminal. Contact Worldline to activate it.",
            ),
            (
                {"Response": "Failed", "ResponseReason": "UnknownReason", "AdditionalResponseInformation": "WPI_ERR_UNKNOWN"},
                "An error has occured during transaction handling, please try again.",
            ),
        ]:
            with self.subTest(response=response):
                self.assertEqual(self.worldline_payment_method._worldline_get_error_message(response), expected)

    def _post_webhook(self, service_response, exchange_id="exchange-id", webhook_payload=None, message_function="SaleFinancialServiceResponse"):
        payload = {
            "data": {
                "SaleToPOIServiceResponse": {
                    "Header": {"MessageFunction": message_function, "ExchangeIdentification": exchange_id},
                    "ServiceResponse": {
                        "Environment": {"POI": {"Identification": {"Identification": self.worldline_payment_method.worldline_terminal_id}}},
                        **service_response,
                    },
                },
            },
        }
        notifications = []
        with patch.object(
            self.registry["pos.electronic.payment"],
            "_notify",
            lambda _self, transaction_id, message: notifications.append((transaction_id, message)),
        ):
            if webhook_payload is None:
                webhook_payload = WorldlineApiRequest(self.worldline_payment_method)._get_webhook_payload(
                    exchange_id,
                )
            response = self.url_open(
                f"/pos_worldline/webhook?payload={webhook_payload}",
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
            )
        self.assertEqual(response.status_code, 200)
        return notifications

    def test_webhook_approved(self):
        notifications = self._post_webhook({
            "Response": {"Response": "Successful"},
            "Environment": {
                "POI": {"Identification": {"Identification": self.worldline_payment_method.worldline_terminal_id}},
                "Card": {"CardBrand": "MAESTRO", "MaskedPAN": "XXXXXXXXXXXXX5006"},
            },
            "PaymentResponse": {
                "SaleTransactionIdentification": {"TransactionReference": "payment-uuid"},
                "POITransactionIdentification": {"TransactionReference": "2;00999100022;92986866332;"},
                "RetailerPaymentResult": {
                    "TransactionResponse": {
                        "AuthorisationResult": {
                            "ResponseToAuthorisation": {"Response": "Approved"},
                            "AuthorisationCode": "678803",
                        },
                    },
                },
            },
        })

        self.assertEqual(notifications, [("exchange-id", {
            "transaction_id": "exchange-id",
            "final_transaction_id": "2;00999100022;92986866332;",
            "status": "paid",
            "card_brand": "MAESTRO",
            "card_no": "XXXXXXXXXXXXX5006",
            "payment_method_authcode": "678803",
        })])

    def test_webhook_cancelled(self):
        # A cancelled transaction comes back without TransactionReference: the payment line is identified by the signed payload.
        notifications = self._post_webhook({
            "Response": {
                "Response": "Failed",
                "ResponseReason": "Cancel",
                "AdditionalResponseInformation": "WPI_ERR_COND_USER_CANCEL:EFT_E_CARDHOLDER_ABORT",
            },
            "PaymentResponse": {
                "SaleTransactionIdentification": {},
                "POITransactionIdentification": {},
            },
        })

        self.assertEqual(notifications, [("exchange-id", {
            "transaction_id": "exchange-id",
            "status": "failed",
            "error": "Transaction was cancelled on the terminal. Please try again.",
        })])

    def test_webhook_transaction_timeout(self):
        # A transaction that never started on the terminal is reported with the "Abort" message function and
        # without Environment: the payment line is identified by the signed payload.
        notifications = self._post_webhook({
            "Environment": {},
            "ServiceContent": "FinancialPaymentResponse",
            "Response": {
                "Response": "Failed",
                "ResponseReason": "Refusal",
                "AdditionalResponseInformation": "WPI_ERR_COND_TRANSACTION_TIMEOUT:Operation timed out",
            },
        }, message_function="Abort")

        self.assertEqual(notifications, [("exchange-id", {
            "transaction_id": "exchange-id",
            "status": "failed",
            "error": "The transaction did not start on the terminal in time. Please make sure the terminal is turned on and connected to the internet, then try again.",
        })])

    @mute_logger('odoo.addons.pos_payment_method_worldline.controllers.webhook')
    def test_webhook_invalid_payload(self):
        service_response = {
            "Response": {"Response": "Successful"},
            "PaymentResponse": {
                "SaleTransactionIdentification": {"TransactionReference": "payment-uuid"},
            },
        }
        # Payload signed for a different request
        other_payload = WorldlineApiRequest(self.worldline_payment_method)._get_webhook_payload("other-exchange-id")
        self.assertFalse(self._post_webhook(service_response, webhook_payload=other_payload))
        # Payload signed with a different scope
        forged_payload = hash_sign(self.env(su=True), "other_scope", {
            "exchange_id": "exchange-id",
            "payment_method_id": self.worldline_payment_method.id,
        })
        self.assertFalse(self._post_webhook(service_response, webhook_payload=forged_payload))
        self.assertFalse(self._post_webhook(service_response, webhook_payload=""))
        self.assertFalse(self._post_webhook(service_response, webhook_payload="not-a-payload"))
