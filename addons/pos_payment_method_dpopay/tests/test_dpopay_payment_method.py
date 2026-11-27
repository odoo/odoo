import json
from unittest.mock import patch

from odoo.tests.common import MockHTTPClient, TransactionCase, mute_logger


class TestDpoPayPaymentMethod(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dpopay_payment_method = cls.env["pos.electronic.payment"].create({
            "name": "DPO Pay",
            "payment_provider": "dpopay",
            "dpopay_bearer_token": "TOKEN",
            "dpopay_chain_id": "CHAIN",
            "dpopay_client_id": "CLIENT",
            "dpopay_client_secret": "SECRET",
            "dpopay_mid": "MID",
            "dpopay_tid": "TID",
            "dpopay_payment_mode": "card",
            "integration_type": "terminal",
        })
        cls.currency = cls.env.company.currency_id

    def test_payment_card(self):
        with (
            MockHTTPClient(method="POST", url="https://api.network.global/ngenius-webapi/payments/push/v1/tid:TID/mid:MID/get-status", return_status=200, return_json={"displayText": "NO TXN / SYSTEM IDLE"}) as mock_status_request,
            MockHTTPClient(method="POST", url="https://api.network.global/ngenius-webapi/payments/push/v1/tid:TID/mid:MID/start-transaction", return_status=200, return_json={}) as mock_payment_request,
        ):
            result = self.dpopay_payment_method.start_payment(5.00, self.currency.id)
            mock_status_request.assert_called_once()
            mock_payment_request.assert_called_once()
            request_body = json.loads(mock_payment_request.calls[0].body)

        self.assertDictEqual(request_body, {
            "amount": "500",
            "currency": str(self.currency.iso_numeric),
            "sourceId": result["transaction_id"],
            "transactionType": "pushPaymentSale",
        })
        self.assertEqual(len(result["transaction_id"]), 15)
        self.assertEqual(result["status"], "pending")

    def test_payment_momo(self):
        self.dpopay_payment_method.dpopay_payment_mode = "momo"
        with (
            MockHTTPClient(method="POST", url="https://api.network.global/ngenius-webapi/payments/push/v1/tid:TID/mid:MID/get-status", return_status=200, return_json={"displayText": "NO TXN / SYSTEM IDLE"}),
            MockHTTPClient(method="POST", url="https://api.network.global/ngenius-webapi/payments/push/v1/tid:TID/mid:MID/start-transaction", return_status=200, return_json={}) as mock_payment_request,
        ):
            self.dpopay_payment_method.start_payment(5.00, self.currency.id)
            request_body = json.loads(mock_payment_request.calls[0].body)

        self.assertEqual(request_body["transactionType"], "pushPaymentDpoMomoSale")

    @mute_logger("odoo.addons.pos_payment_method_dpopay.models.pos_electronic_payment")
    def test_payment_api_error(self):
        self.dpopay_payment_method.dpopay_payment_mode = "momo"
        with (
            MockHTTPClient(method="POST", url="https://api.network.global/ngenius-webapi/payments/push/v1/tid:TID/mid:MID/get-status", return_status=400, return_json={"errorMessage": "ERROR"}),
        ):
            result = self.dpopay_payment_method.start_payment(5.00, self.currency.id)

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"], "ERROR")

    def test_cancel(self):
        with (
            MockHTTPClient(method="POST", url="https://api.network.global/ngenius-webapi/payments/push/v1/tid:TID/mid:MID/cancel-transaction", return_status=200, return_json={}) as mock_request,
        ):
            self.dpopay_payment_method.cancel_transaction("test")
            mock_request.assert_called_once()
            request_body = json.loads(mock_request.calls[0].body)

        self.assertEqual(request_body["sourceId"], "test")

    def test_get_pending(self):
        with (
            MockHTTPClient(method="POST", url="https://api.network.global/ngenius-webapi/payments/push/v1/tid:TID/mid:MID/get-status", return_status=200, return_json={"complete": False}) as mock_request,
        ):
            result = self.dpopay_payment_method.get_transaction_status("test")
            mock_request.assert_called_once()
            request_body = json.loads(mock_request.calls[0].body)

        self.assertEqual(request_body["sourceId"], "test")
        self.assertEqual(result["status"], "pending")

    def test_get_terminal_offline(self):
        with (
            MockHTTPClient(method="POST", url="https://api.network.global/ngenius-webapi/payments/push/v1/tid:TID/mid:MID/get-status", return_status=200, return_json={"offline": True}),
        ):
            result = self.dpopay_payment_method.get_transaction_status("test")

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"], "DPO Pay terminal is currently offline.")

    def test_get_declined(self):
        with (
            MockHTTPClient(method="POST", url="https://api.network.global/ngenius-webapi/payments/push/v1/tid:TID/mid:MID/get-status", return_status=200, return_json={"declined": True}),
        ):
            result = self.dpopay_payment_method.get_transaction_status("test")

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"], "Payment is declined by DPO Pay.")

    def test_get_failed(self):
        with (
            MockHTTPClient(method="POST", url="https://api.network.global/ngenius-webapi/payments/push/v1/tid:TID/mid:MID/get-status", return_status=200, return_json={"complete": True, "success": False}),
        ):
            result = self.dpopay_payment_method.get_transaction_status("test")

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"], "Payment is unsuccessful.")

    def test_get_success(self):
        mock_response = {
            "Acquirer Name": "BANK",
            "authCode": "1234",
            "CardHolderName": "NAME",
            "panMasked": "XXXXXXX5555",
            "cardType": "VISA",
            "rrn": "RRN",
        }
        with (
            patch("time.sleep"),
            MockHTTPClient(method="POST", url="https://api.network.global/ngenius-webapi/payments/push/v1/tid:TID/mid:MID/get-status", return_status=200, return_json={"complete": True, "success": True}),
            MockHTTPClient(method="POST", url="https://api.network.global/ngenius-webapi/payments/push/v1/tid:TID/mid:MID/get-result", return_status=200, return_json=mock_response) as mock_request,
        ):
            result = self.dpopay_payment_method.get_transaction_status("test")
            mock_request.assert_called_once()

        self.assertDictEqual(result, {"transaction_id": "test",
            "status": "paid",
            "payment_method_issuer_bank": "BANK",
            "payment_method_authcode": "1234",
            "cardholder_name": "NAME",
            "card_no": "5555",
            "card_brand": "VISA",
            "payment_method_payment_mode": "CARD",
            "payment_ref_no": "RRN",
        })

    @mute_logger("odoo.addons.pos_payment_method_dpopay.models.pos_electronic_payment")
    def test_token_refresh(self):
        with (
            MockHTTPClient(method="POST", url="https://api.network.global/ngenius-webapi/payments/push/v1/tid:TID/mid:MID/get-status", return_status=401, return_json={"error_code": "999912"}),
            MockHTTPClient(method="GET", url="https://api.network.global/v1/tokenkc/generate", return_status=200, return_json={"access_token": "NEW_TOKEN"}),
        ):
            self.dpopay_payment_method.get_transaction_status("test")

        self.assertEqual(self.dpopay_payment_method.dpopay_bearer_token, "NEW_TOKEN")
