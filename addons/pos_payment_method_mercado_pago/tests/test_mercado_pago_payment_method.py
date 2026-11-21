import hashlib
import hmac
import json
from unittest.mock import patch

from odoo.tests import MockHTTPClient
from odoo.tests.common import HttpCase
from odoo.tools import mute_logger

from odoo.addons.pos_payment_method_mercado_pago.models.mercado_pago_pos_request import (
    MERCADO_PAGO_PLATFORM_ID,
)


class TestMercadoPagoPaymentMethod(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with patch("odoo.addons.pos_payment_method_mercado_pago.models.pos_electronic_payment.PosElectronicPayment._mp_find_terminal", return_value="MODEL_SERIAL"):
            cls.mercado_payment_method = cls.env["pos.electronic.payment"].create({
                "name": "Mercado Pago",
                "payment_provider": "mercado_pago",
                "mp_bearer_token": "TOKEN",
                "mp_webhook_secret_key": "SECRET",
                "mp_id_point_smart": "SERIAL",
                "integration_type": "terminal",
            })
        cls.currency_id = cls.env.company.currency_id.id

    def _check_auth_header(self, req):
        self.assertEqual(req.headers["Authorization"], "Bearer TOKEN")

    def test_payment(self):
        with (
            MockHTTPClient(
                method="POST",
                url="https://api.mercadopago.com/v1/orders",
                return_status=200,
                return_json={"id": "ORDER123"},
                side_effect=self._check_auth_header,
            ) as mock_request,
            patch("uuid.UUID.hex", "mockUuid"),
        ):
            result = self.mercado_payment_method.start_payment(5.00, self.currency_id)
            mock_request.assert_called_once()
            request_body = json.loads(mock_request.calls[0].body)

        expected_request_body = {
            "config": {"point": {"terminal_id": "MODEL_SERIAL"}},
            "expiration_time": "PT30M",
            "external_reference": f"{self.mercado_payment_method.id}_mockUuid",
            "integration_data": {
                "platform_id": MERCADO_PAGO_PLATFORM_ID,
            },
            "transactions": {"payments": [{"amount": "5.00"}]},
            "type": "point",
        }

        self.assertEqual(result["transaction_id"], "ORDER123")
        self.assertEqual(result["status"], "pending")
        self.assertDictEqual(request_body, expected_request_body)

    def test_full_refund(self):
        with (
            MockHTTPClient(
                method="GET",
                url="https://api.mercadopago.com/v1/orders/ORDER123",
                return_status=200,
                return_json={"transactions": {"payments": [{"amount": "5.00"}]}},
                side_effect=self._check_auth_header,
            ) as mock_get_order_request,
            MockHTTPClient(
                method="POST",
                url="https://api.mercadopago.com/v1/orders/ORDER123/refund",
                return_status=200,
                return_json={"id": "REFUND123"},
                side_effect=self._check_auth_header,
            ) as mock_refund_request,
        ):
            result = self.mercado_payment_method.start_reversal(5.00, self.currency_id, "ORDER123")
            mock_get_order_request.assert_called_once()
            mock_refund_request.assert_called_once()
            request_body = json.loads(mock_refund_request.calls[0].body)

        self.assertEqual(result["transaction_id"], "REFUND123")
        self.assertEqual(result["status"], "paid")
        self.assertDictEqual(request_body, {})

    def test_partial_refund(self):
        with (
            MockHTTPClient(
                method="GET",
                url="https://api.mercadopago.com/v1/orders/ORDER123",
                return_status=200,
                return_json={
                    "transactions": {
                        "payments": [{"id": "PAYMENT123", "amount": "5.00"}],
                    },
                },
                side_effect=self._check_auth_header,
            ) as mock_get_order_request,
            MockHTTPClient(
                method="POST",
                url="https://api.mercadopago.com/v1/orders/ORDER123/refund",
                return_status=200,
                return_json={"id": "REFUND123"},
                side_effect=self._check_auth_header,
            ) as mock_refund_request,
        ):
            result = self.mercado_payment_method.start_reversal(3.00, self.currency_id, "ORDER123")
            mock_get_order_request.assert_called_once()
            mock_refund_request.assert_called_once()
            request_body = json.loads(mock_refund_request.calls[0].body)

        self.assertEqual(result["transaction_id"], "REFUND123")
        self.assertEqual(result["status"], "paid")
        self.assertDictEqual(request_body, {"transactions": [{"amount": "3.00", "id": "PAYMENT123"}]})

    def test_get_pending(self):
        with (
            MockHTTPClient(
                method="GET",
                url="https://api.mercadopago.com/v1/orders/ORDER123",
                return_status=200,
                return_json={"status": "created"},
                side_effect=self._check_auth_header,
            ) as mock_request,
        ):
            result = self.mercado_payment_method.get_transaction_status("ORDER123")
            mock_request.assert_called_once()

        self.assertEqual(result["status"], "pending")

    def test_get_failed(self):
        with (
            MockHTTPClient(
                method="GET",
                url="https://api.mercadopago.com/v1/orders/ORDER123",
                return_status=200,
                return_json={"status": "canceled"},
                side_effect=self._check_auth_header,
            ) as mock_request,
        ):
            result = self.mercado_payment_method.get_transaction_status("ORDER123")
            mock_request.assert_called_once()

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"], self.env._("The payment has been cancelled on the terminal."))

    def test_get_success(self):
        with (
            MockHTTPClient(
                method="GET",
                url="https://api.mercadopago.com/v1/orders/ORDER123",
                return_status=200,
                return_json={"status": "processed"},
                side_effect=self._check_auth_header,
            ) as mock_request,
        ):
            result = self.mercado_payment_method.get_transaction_status("ORDER123")
            mock_request.assert_called_once()

        self.assertEqual(result["status"], "paid")

    def test_get_action_required(self):
        with (
            MockHTTPClient(
                method="GET",
                url="https://api.mercadopago.com/v1/orders/ORDER123",
                return_status=200,
                return_json={"status": "action_required"},
                side_effect=self._check_auth_header,
            ) as mock_request,
        ):
            result = self.mercado_payment_method.get_transaction_status("ORDER123")
            mock_request.assert_called_once()

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["mercado_pago_status"], "action_required")

    def test_webhook_notification_notifies_the_bus(self):
        hmac_data = b"id:order123;request-id:REQUESTID;ts:1234;"
        expected_hmac = hmac.new(b"SECRET", hmac_data, hashlib.sha256).hexdigest()
        headers = {
            "X-Request-Id": "REQUESTID",
            "X-Signature": f"ts=1234,v1={expected_hmac}",
        }
        body = {
            "type": "order",
            "data": {
                "external_reference": f"{self.mercado_payment_method.id}_abc123",
            },
        }

        with (
            patch("odoo.addons.pos_payment_method.models.pos_electronic_payment.PosElectronicPayment._notify") as mock_notify,
            MockHTTPClient(
                method="GET",
                url="https://api.mercadopago.com/v1/orders/ORDER123",
                return_status=200,
                return_json={"status": "processed"},
                side_effect=self._check_auth_header,
            ) as mock_request,
        ):
            response = self.url_open("/pos_mercado_pago/notification?data.id=ORDER123", headers=headers, json=body)

        self.assertEqual(response.status_code, 200)
        mock_notify.assert_called_once()
        mock_request.assert_called_once()
        self.assertEqual(mock_notify.call_args.args[0], "ORDER123")
        self.assertEqual(mock_notify.call_args.args[1]["status"], "paid")

    @mute_logger("odoo.addons.pos_payment_method_mercado_pago.controllers.webhook")
    def test_webhook_bad_hmac_is_ignored(self):
        headers = {
            "X-Request-Id": "REQUESTID",
            "X-Signature": "ts=1234,v1=deadbeef",
        }
        body = {
            "type": "order",
            "data": {
                "external_reference": f"{self.mercado_payment_method.id}_abc123",
            },
        }

        with (
            patch("odoo.addons.pos_payment_method.models.pos_electronic_payment.PosElectronicPayment._notify") as mock_notify,
            MockHTTPClient(
                method="GET",
                url="https://api.mercadopago.com/v1/orders/ORDER123",
                return_status=200,
                return_json={"status": "processed"},
                side_effect=self._check_auth_header,
            ) as mock_request,
        ):
            response = self.url_open("/pos_mercado_pago/notification?data.id=ORDER123", headers=headers, json=body)

        self.assertEqual(response.status_code, 200)
        mock_notify.assert_not_called()
        mock_request.assert_not_called()
