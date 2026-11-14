import json
from urllib.parse import parse_qs, urlsplit
from unittest.mock import MagicMock, patch

from requests.exceptions import RequestException, Timeout

from odoo.tests.common import tagged
from odoo.tools import hash_sign, mute_logger, verify_hash_signed

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.pos_worldline.models.worldline_api_request import WorldlineApiRequest


@tagged("post_install", "-at_install")
class TestWorldlinePosPaymentMethod(TestPointOfSaleHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.main_pos_config.write({
            "payment_method_ids": [
                (0, 0, {
                    "name": "Worldline",
                    "use_payment_terminal": "worldline_api",
                    "worldline_terminal_id": "WORLDLINE123",
                    "worldline_merchant_id": "MERCHANT123",
                    "payment_method_type": "terminal",
                    "journal_id": cls.bank_journal.id,
                }),
            ],
        })
        cls.worldline_payment_method = cls.main_pos_config.payment_method_ids.filtered(lambda pm: pm.use_payment_terminal == "worldline_api")

    def _mock_response(self, status_code=202, json_data=None):
        response = MagicMock()
        response.status_code = status_code
        response.json.return_value = json_data or {}
        response.text = json.dumps(json_data or {})
        return response

    def test_payment(self):
        with patch(
            "odoo.addons.pos_worldline.models.worldline_api_request.requests.post",
            return_value=self._mock_response(),
        ) as mock_post:
            self.worldline_payment_method.worldline_create_transaction("CardPayment", 5.00, "uuid", 1)
            url = mock_post.call_args.args[0]
            headers = mock_post.call_args.kwargs.get("headers")
            payload = mock_post.call_args.kwargs.get("json")

        self.assertIn(f"/terminals/{self.worldline_payment_method.worldline_terminal_id}/payments", url)
        self.assertIn("Bearer", headers["Authorization"])

        service_request = payload["SaleToPOIServiceRequest"]["ServiceRequest"]
        payment_transaction = service_request["PaymentRequest"]["PaymentTransaction"]
        self.assertEqual(payment_transaction["TransactionType"], "CardPayment")
        self.assertEqual(payment_transaction["TransactionIdentification"]["TransactionReference"], "uuid")
        self.assertEqual(payment_transaction["TransactionDetails"]["TotalAmount"], 5.00)
        self.assertNotIn("OriginalTransaction", payment_transaction)
        self.assertEqual(
            service_request["Environment"]["POI"]["Identification"]["Identification"],
            self.worldline_payment_method.worldline_terminal_id,
        )
        header = payload["SaleToPOIServiceRequest"]["Header"]
        webhook_url = urlsplit(header["WebhookUrl"])
        self.assertEqual(f"{webhook_url.scheme}://{webhook_url.netloc}{webhook_url.path}", self.worldline_payment_method.worldline_webhook_url)
        webhook_payload = parse_qs(webhook_url.query)["payload"][0]
        self.assertEqual(verify_hash_signed(self.env(su=True), 'pos_worldline', webhook_payload), {
            "exchange_id": header["ExchangeIdentification"],
            "payment_uuid": "uuid",
            "payment_method_id": self.worldline_payment_method.id,
            "pos_session_id": 1,
        })

    def test_refund(self):
        with patch(
            "odoo.addons.pos_worldline.models.worldline_api_request.requests.post",
            return_value=self._mock_response(),
        ) as mock_post:
            self.worldline_payment_method.worldline_create_transaction("Refund", 5.00, "uuid", 1)
            payload = mock_post.call_args.kwargs.get("json")

        payment_transaction = payload["SaleToPOIServiceRequest"]["ServiceRequest"]["PaymentRequest"]["PaymentTransaction"]
        self.assertEqual(payment_transaction["TransactionType"], "Refund")
        self.assertEqual(payment_transaction["TransactionDetails"]["TotalAmount"], 5.00)
        self.assertNotIn("OriginalTransaction", payment_transaction)

    @mute_logger('odoo.addons.pos_worldline.models.worldline_api_request')
    def test_payment_error(self):
        with patch(
            "odoo.addons.pos_worldline.models.worldline_api_request.requests.post",
            return_value=self._mock_response(status_code=400, json_data={"message": "Invalid terminal"}),
        ):
            result = self.worldline_payment_method.worldline_create_transaction("CardPayment", 5.00, "uuid", 1)

        self.assertEqual(result, {"error": "Invalid terminal"})

    @mute_logger('odoo.addons.pos_worldline.models.worldline_api_request')
    def test_payment_request_exception(self):
        with patch(
            "odoo.addons.pos_worldline.models.worldline_api_request.requests.post",
            side_effect=RequestException("Connection failed"),
        ):
            result = self.worldline_payment_method.worldline_create_transaction("CardPayment", 5.00, "uuid", 1)

        self.assertEqual(result, {"error": "Connection failed"})

    @mute_logger('odoo.addons.pos_worldline.models.worldline_api_request')
    def test_payment_request_timeout(self):
        with patch(
            "odoo.addons.pos_worldline.models.worldline_api_request.requests.post",
            side_effect=Timeout(),
        ):
            result = self.worldline_payment_method.worldline_create_transaction("CardPayment", 5.00, "uuid", 1)

        self.assertEqual(result, {
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
        with patch(
            "odoo.addons.pos_worldline.models.worldline_api_request.requests.post",
            return_value=self._mock_response(status_code=200, json_data=approved_response),
        ) as mock_post:
            result = self.worldline_payment_method.worldline_get_transaction_status("exchange-id")
            url = mock_post.call_args.args[0]
            payload = mock_post.call_args.kwargs.get("json")

        self.assertTrue(url.endswith("/status/sync"))
        status_request_data = payload["SaleToPOIMessageStatusRequest"]["StatusRequest"]["MessageStatusRequestData"]
        self.assertEqual(status_request_data["ExchangeIdentification"], "exchange-id")
        self.assertEqual(result, {
            "status": "done",
            "exchange_id": "exchange-id",
            "transaction_id": "2;00999100022;92986866332;",
            "success": True,
            "card_brand": "MAESTRO",
            "card_no": "5006",
            "payment_method_authcode": "678803",
        })

    @mute_logger('odoo.addons.pos_worldline.models.worldline_api_request')
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
            (200, in_progress_response, {"status": "pending"}),
            (200, waiting_card_response, {"status": "pending"}),
            (202, {"requestId": "550e8400-e29b-41d4-a716-446655440000"}, {"status": "pending"}),  # Terminal timeout
            (400, {"message": "Invalid terminal"}, {"status": "pending", "error": "Invalid terminal"}),
        ]:
            with self.subTest(status_code=status_code), patch(
                "odoo.addons.pos_worldline.models.worldline_api_request.requests.post",
                return_value=self._mock_response(status_code=status_code, json_data=json_data),
            ):
                result = self.worldline_payment_method.worldline_get_transaction_status("exchange-id")
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
        with patch(
            "odoo.addons.pos_worldline.models.worldline_api_request.requests.post",
            return_value=self._mock_response(status_code=200, json_data=failed_response),
        ):
            result = self.worldline_payment_method.worldline_get_transaction_status("exchange-id")

        self.assertEqual(result, {
            "status": "done",
            "exchange_id": "exchange-id",
            "transaction_id": None,
            "success": False,
            "error": "Transaction was cancelled on the terminal. Please try again.",
        })

    @mute_logger('odoo.addons.pos_worldline.models.worldline_api_request')
    def test_transaction_status_timeout(self):
        # The transaction may still complete on the terminal: it stays pending, but the error is reported.
        with patch(
            "odoo.addons.pos_worldline.models.worldline_api_request.requests.post",
            side_effect=Timeout(),
        ):
            result = self.worldline_payment_method.worldline_get_transaction_status("exchange-id")

        self.assertEqual(result, {
            "status": "pending",
            "error": "Worldline request to terminal WORLDLINE123 timed out. Please make sure the terminal is connected to internet and try again.",
        })

    def test_get_error_message(self):
        currency_name = (self.worldline_payment_method.journal_id.currency_id or self.worldline_payment_method.company_id.currency_id).name
        for response, expected in [
            ({"Response": "Successful"}, False),
            (
                {"Response": "Failed", "ResponseReason": "Busy", "AdditionalResponseInformation": "WPI_ERR_COND_BUSY:Busy, another request already running"},
                "The terminal is currently busy with a different transaction. Please try again later.",
            ),
            (
                {"Response": "Failed", "ResponseReason": "NotAllowed", "AdditionalResponseInformation": "WPI_ERR_COND_INVALID_CURRENCY:EP2_E_CURR_NOT_INITIALIZED"},
                f"The currency {currency_name} is not supported by the terminal. Contact Worldline to activate it.",
            ),
            (
                {"Response": "Failed", "ResponseReason": "UnknownReason", "AdditionalResponseInformation": "WPI_ERR_UNKNOWN"},
                "An error has occured during transaction handling, please try again.",
            ),
        ]:
            with self.subTest(response=response):
                self.assertEqual(self.worldline_payment_method._worldline_get_error_message(response), expected)

    def test_action_worldline_test(self):
        with patch(
            "odoo.addons.pos_worldline.models.worldline_api_request.requests.post",
            return_value=self._mock_response(),
        ) as mock_post:
            action = self.worldline_payment_method.action_worldline_test()
            url = mock_post.call_args.args[0]
            payload = mock_post.call_args.kwargs.get("json")

        self.assertTrue(url.endswith(f"/terminals/{self.worldline_payment_method.worldline_terminal_id}/device"))
        image_screen = payload["SaleToPOIDeviceRequest"]["DeviceRequest"]["InputRequest"]["DisplayOutput"]["MessageContent"]["ImageScreen"]
        self.assertTrue(image_screen["ImageBase64"])
        self.assertEqual(action["tag"], "display_notification")
        self.assertEqual(action["params"]["type"], "success")

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
            self.registry["pos.config"],
            "_notify",
            lambda _self, name, message: notifications.append((message["pos_session_id"], message)),
        ):
            if webhook_payload is None:
                webhook_payload = WorldlineApiRequest(self.worldline_payment_method)._get_webhook_payload(
                    exchange_id, "payment-uuid", self.main_pos_config.current_session_id.id,
                )
            response = self.url_open(
                f"/pos_worldline/webhook?payload={webhook_payload}",
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
            )
        self.assertEqual(response.status_code, 200)
        return notifications

    def test_webhook_approved(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        session = self.main_pos_config.current_session_id
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

        self.assertEqual(notifications, [(session.id, {
            "payment_uuid": "payment-uuid",
            "exchange_id": "exchange-id",
            "transaction_id": "2;00999100022;92986866332;",
            "success": True,
            "card_brand": "MAESTRO",
            "card_no": "5006",
            "payment_method_authcode": "678803",
            "pos_session_id": session.id,
        })])

    def test_webhook_cancelled(self):
        # A cancelled transaction comes back without TransactionReference: the payment line is identified by the signed payload.
        self.main_pos_config.with_user(self.pos_user).open_ui()
        session = self.main_pos_config.current_session_id
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

        self.assertEqual(notifications, [(session.id, {
            "payment_uuid": "payment-uuid",
            "exchange_id": "exchange-id",
            "transaction_id": None,
            "success": False,
            "error": "Transaction was cancelled on the terminal. Please try again.",
            "pos_session_id": session.id,
        })])

    def test_webhook_transaction_timeout(self):
        # A transaction that never started on the terminal is reported with the "Abort" message function and
        # without Environment: the payment line is identified by the signed payload.
        self.main_pos_config.with_user(self.pos_user).open_ui()
        session = self.main_pos_config.current_session_id
        notifications = self._post_webhook({
            "Environment": {},
            "ServiceContent": "FinancialPaymentResponse",
            "Response": {
                "Response": "Failed",
                "ResponseReason": "Refusal",
                "AdditionalResponseInformation": "WPI_ERR_COND_TRANSACTION_TIMEOUT:Operation timed out",
            },
        }, message_function="Abort")

        self.assertEqual(notifications, [(session.id, {
            "payment_uuid": "payment-uuid",
            "exchange_id": "exchange-id",
            "transaction_id": None,
            "success": False,
            "error": "The transaction did not start on the terminal in time. Please make sure the terminal is turned on and connected to the internet, then try again.",
            "pos_session_id": session.id,
        })])

    @mute_logger('odoo.addons.pos_worldline.controllers.webhook')
    def test_webhook_invalid_payload(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        session = self.main_pos_config.current_session_id
        service_response = {
            "Response": {"Response": "Successful"},
            "PaymentResponse": {
                "SaleTransactionIdentification": {"TransactionReference": "payment-uuid"},
            },
        }
        # Payload signed for a different request
        other_payload = WorldlineApiRequest(self.worldline_payment_method)._get_webhook_payload("other-exchange-id", "payment-uuid", session.id)
        self.assertFalse(self._post_webhook(service_response, webhook_payload=other_payload))
        # Payload signed with a different scope
        forged_payload = hash_sign(self.env(su=True), "other_scope", {
            "exchange_id": "exchange-id",
            "payment_uuid": "payment-uuid",
            "payment_method_id": self.worldline_payment_method.id,
            "pos_session_id": session.id,
        })
        self.assertFalse(self._post_webhook(service_response, webhook_payload=forged_payload))
        self.assertFalse(self._post_webhook(service_response, webhook_payload=""))
        self.assertFalse(self._post_webhook(service_response, webhook_payload="not-a-payload"))
