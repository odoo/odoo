import re
from requests import Response
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tools import hmac
from odoo.tests.common import tagged
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged('post_install', '-at_install')
class TestAdyenPoS(TestPointOfSaleHttpCommon):
    def setUp(self):
        super().setUp()
        self.main_pos_config.write({
            "payment_method_ids": [
                Command.create({
                    "name": "Adyen",
                    "adyen_api_key": "my_adyen_api_key",
                    "adyen_terminal_identifier": "my_adyen_terminal",
                    "adyen_test_mode": False,
                    "use_payment_terminal": "adyen",
                    "payment_method_type": "terminal",
                    'journal_id': self.bank_journal.id,
                }),
            ],
        })

    def mock_adyen_post(self, url, headers, json, **kwargs):
        response = Response()
        response._content = b"{}"

        if url != "https://terminal-api-live.adyen.com/async":
            response.status_code = 404
            return response
        self.assertEqual(headers.get("x-api-key"), "my_adyen_api_key")

        message = json["SaleToPOIRequest"]
        self.assertEqual(message["MessageHeader"]["POIID"], "my_adyen_terminal")
        if "PaymentRequest" in message:
            expected_hash = self.get_expected_hash(message["MessageHeader"]["ServiceID"], message["PaymentRequest"]["SaleData"]["SaleTransactionID"]["TransactionID"])
            received_hash = self.parse_received_hash(message["PaymentRequest"]["SaleData"]["SaleToAcquirerData"])

            self.assertEqual(received_hash, expected_hash)
            self.assertEqual(message["PaymentRequest"]["PaymentTransaction"]["AmountsReq"]["Currency"], "USD")
            self.assertEqual(message["PaymentRequest"]["PaymentTransaction"]["AmountsReq"]["RequestedAmount"], 1.98)
        elif "ReversalRequest" in message:
            self.assertEqual(message["ReversalRequest"]["ReversalReason"], "MerchantCancel")
            self.assertEqual(message["ReversalRequest"]["ReversedAmount"], 1.98)
            pass
        else:
            raise ValidationError("Unexpected Adyen request received")

        response.status_code = 200
        return response

    def get_expected_hash(self, service_id, transaction_id):
        return hmac(
            env=self.env,
            scope='pos_adyen_payment',
            message=(f"{self.main_pos_config.name} (ID: {self.main_pos_config.id})", service_id, "my_adyen_terminal", transaction_id)
        )

    def parse_received_hash(self, sale_to_acquirer_data):
        hash_regex = r"metadata\.pos_hmac=(.+)"
        match = re.search(hash_regex, sale_to_acquirer_data)
        self.assertIsNotNone(match, "POS HMAC could not be parsed from request to Adyen")
        return match and match[1]

    def test_adyen_basic_order(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()

        with patch('odoo.addons.pos_adyen.models.pos_payment_method.requests.post', self.mock_adyen_post), \
             patch('odoo.addons.pos_adyen.controllers.main.consteq', lambda a, b: a == "dummy_hmac"):
            self.start_pos_tour('PosAdyenPaymentTour')

    def test_adyen_refund_order(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()

        with patch('odoo.addons.pos_adyen.models.pos_payment_method.requests.post', self.mock_adyen_post), \
             patch('odoo.addons.pos_adyen.controllers.main.consteq', lambda a, b: a == "dummy_hmac"):
            self.start_pos_tour('PosAdyenRefundTour')
