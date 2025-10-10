from unittest.mock import patch

from requests import Response

from odoo.tests.common import tagged

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


def _build_terminal_payment_payload(
    payment_method,
    transaction_id,
    sale_id,
    service_id,
):
    return {
        "SaleToPOIRequest": {
            "MessageHeader": {
                "ProtocolVersion": "3.0",
                "MessageClass": "Service",
                "MessageType": "Request",
                "MessageCategory": "Payment",
                "SaleID": sale_id,
                "ServiceID": service_id,
                "POIID": payment_method.adyen_terminal_identifier,
            },
            "PaymentRequest": {
                "SaleData": {
                    "SaleTransactionID": {
                        "TransactionID": transaction_id,
                        "TimeStamp": "2024-01-01T00:00:00",
                    },
                },
                "PaymentTransaction": {
                    "AmountsReq": {
                        "Currency": payment_method.company_id.currency_id.name or "USD",
                        "RequestedAmount": 10,
                    },
                },
            },
        },
    }


@tagged("post_install", "-at_install")
class TestAdyenPoS(TestPointOfSaleHttpCommon):
    def test_adyen_basic_order(self):
        self.main_pos_config.write(
            {
                "payment_method_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Adyen",
                            "use_payment_terminal": True,
                            "adyen_api_key": "my_adyen_api_key",
                            "adyen_terminal_identifier": "my_adyen_terminal",
                            "adyen_test_mode": False,
                            "adyen_region": "eu",
                            "adyen_api_url_prefix": "1797a841fbb37ca7-AdyenDemo",
                            "use_payment_terminal": "adyen",
                            "payment_method_type": "terminal",
                            "journal_id": self.bank_journal.id,
                        },
                    ),
                ],
            },
        )
        self.main_pos_config.with_user(self.pos_user).open_ui()

        def post(url, **kwargs):
            # TODO: check that the data passed by pos to adyen is correct
            response = Response()
            response.status_code = 200
            response._content = b"ok"
            response.encoding = "utf-8"
            response.headers["Content-Type"] = "text/plain"
            return response

        with patch(
            "odoo.addons.pos_adyen.models.pos_payment_method.requests.post",
            post,
        ), patch("odoo.addons.pos_adyen.controllers.main.consteq", lambda a, b: True):
            self.start_pos_tour("PosAdyenTour")

    def test_terminal_request_uses_region_suffix(self):
        payment_method = self.env["pos.payment.method"].create(
            {
                "name": "Adyen Region",
                "use_payment_terminal": "adyen",
                "adyen_api_key": "demo_key",
                "adyen_terminal_identifier": "P400Plus-123456789",
                "adyen_test_mode": False,
                "adyen_region": "us",
                "adyen_api_url_prefix": "1797a841fbb37ca7-AdyenDemo",
                "payment_method_type": "terminal",
                "journal_id": self.bank_journal.id,
            },
        )

        class DummyResponse:
            status_code = 200
            text = "ok"

            def json(self):
                return {}

        payload = _build_terminal_payment_payload(
            payment_method,
            "txn-1",
            "Sale-1",
            "Svc-1",
        )
        with patch(
            "odoo.addons.pos_adyen.models.pos_payment_method.requests.post",
            return_value=DummyResponse(),
        ) as mock_post:
            result = payment_method.sudo().proxy_adyen_request(payload)
            self.assertTrue(result)
            self.assertEqual(
                mock_post.call_args[0][0],
                "https://terminal-api-live-us.adyen.com/async",
            )

        payment_method.write({"adyen_region": False})
        payload_no_region = _build_terminal_payment_payload(
            payment_method,
            "txn-2",
            "Sale-2",
            "Svc-2",
        )
        with patch(
            "odoo.addons.pos_adyen.models.pos_payment_method.requests.post",
            return_value=DummyResponse(),
        ) as mock_post:
            result = payment_method.sudo().proxy_adyen_request(payload_no_region)
            self.assertTrue(result)
            self.assertEqual(
                mock_post.call_args[0][0],
                "https://terminal-api-live.adyen.com/async",
            )
