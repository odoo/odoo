# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from itertools import count
from unittest.mock import patch

from odoo import Command, fields
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.tests.common import tagged


@tagged("post_install_l10n", "post_install", "-at_install")
class TestPineLabsPaymentStatus(TestPointOfSaleHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.currency_id = cls.env.ref("base.INR")
        cls.pine_labs_payment_method = cls.env["pos.payment.method"].create({
            "name": "Pine Labs",
            "payment_method_type": "terminal",
            "use_payment_terminal": "pine_labs",
            "pine_labs_merchant": "my_merchant",
            "pine_labs_store": "my_store",
            "pine_labs_client": "my_client",
            "pine_labs_security_token": "my_token",
            "pine_labs_allowed_payment_mode": "all",
            "pine_labs_test_mode": True,
            "journal_id": cls.bank_journal.id,
        })
        cls.main_pos_config.write({
            "use_pricelist": False,
            "self_ordering_mode": "kiosk",
            "self_ordering_default_user_id": cls.pos_user.id,
            "payment_method_ids": [Command.set(cls.pine_labs_payment_method.ids)],
        })
        cls.main_pos_config.with_user(cls.pos_user).open_ui()

    def setUp(self):
        super().setUp()
        # Fake Pine Labs server: like the real API, it approves the status of any known Plutus
        # reference, whatever order or amount it was issued for.
        self.pine_labs_transactions = {}
        plutus_ids = count(1000)

        def fake_call_pine_labs(payment_method, endpoint, payload):
            if endpoint == "UploadBilledTransaction":
                plutus_id = next(plutus_ids)
                self.pine_labs_transactions[plutus_id] = payload["TransactionNumber"]
                return {"ResponseCode": 0, "ResponseMessage": "APPROVED", "PlutusTransactionReferenceID": plutus_id}
            if endpoint == "GetCloudBasedTxnStatus":
                plutus_id = int(payload["PlutusTransactionReferenceID"])
                if plutus_id not in self.pine_labs_transactions:
                    return {"ResponseCode": 1, "ResponseMessage": "INVALID PLUTUS TXN REF ID"}
                return {
                    "ResponseCode": 0,
                    "ResponseMessage": "TXN APPROVED",
                    "PlutusTransactionReferenceID": plutus_id,
                    "TransactionData": [{"Tag": "TransactionLogId", "Value": f"LOG{plutus_id}"}],
                }
            raise NotImplementedError(endpoint)

        patcher = patch("odoo.addons.pos_pine_labs.models.pos_payment_method.call_pine_labs", fake_call_pine_labs)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _create_order(self, amount):
        order = self.env["pos.order"].create({
            "session_id": self.main_pos_config.current_session_id.id,
            "company_id": self.env.company.id,
            "date_order": fields.Datetime.now(),
            "amount_total": amount,
            "amount_tax": 0,
            "amount_paid": 0,
            "amount_return": 0,
            "lines": [Command.create({
                "product_id": self.whiteboard_pen.product_variant_id.id,
                "qty": 1,
                "price_unit": amount,
                "price_subtotal": amount,
                "price_subtotal_incl": amount,
            })],
        })
        order._ensure_access_token()
        return order

    def _start_kiosk_payment(self, order):
        """ Sends the payment to the terminal as the kiosk does and returns what the kiosk receives. """
        return self.pine_labs_payment_method._payment_request_from_kiosk(order)

    def _fetch_payment_status(self, order, payment):
        params = {
            "access_token": self.main_pos_config.access_token,
            "order_id": order.id,
            "payment_method_id": self.pine_labs_payment_method.id,
            "payment_data": {
                "plutusTransactionReferenceID": payment["plutusTransactionReferenceID"],
                "pine_labs_signature": payment.get("pine_labs_signature"),
                "order_token": order.access_token,
            },
        }
        response = self.url_open(
            "/pos-self-order/pine-labs-fetch-payment-status/",
            data=json.dumps({"jsonrpc": "2.0", "params": params}),
            headers={"Content-Type": "application/json"},
        )
        return response.json()

    def test_matching_transaction_succeeds(self):
        order = self._create_order(100)
        payment = self._start_kiosk_payment(order)

        result = self._fetch_payment_status(order, payment)

        self.assertEqual(result["result"]["status"], "TXN APPROVED")
        self.assertEqual(order.state, "paid")
        self.assertEqual(order.payment_ids.amount, 100)

    def test_replay_on_another_order_is_rejected(self):
        cheap_order = self._create_order(1)
        expensive_order = self._create_order(5000)
        # The cheap transaction is paid on the terminal, but its status is never fetched for the cheap order.
        payment = self._start_kiosk_payment(cheap_order)

        result = self._fetch_payment_status(expensive_order, payment)

        self.assertNotEqual(result.get("result", {}).get("status"), "TXN APPROVED")
        self.assertEqual(expensive_order.state, "draft")
        self.assertFalse(expensive_order.payment_ids)

    def test_replay_after_amount_change_is_rejected(self):
        order = self._create_order(1)
        payment = self._start_kiosk_payment(order)
        order.amount_total = 5000

        result = self._fetch_payment_status(order, payment)

        self.assertNotEqual(result.get("result", {}).get("status"), "TXN APPROVED")
        self.assertEqual(order.state, "draft")
        self.assertFalse(order.payment_ids)

    def test_missing_or_forged_signature_is_rejected(self):
        order = self._create_order(100)
        payment = self._start_kiosk_payment(order)

        for signature in (None, "", "forged"):
            result = self._fetch_payment_status(order, {**payment, "pine_labs_signature": signature})
            self.assertNotEqual(result.get("result", {}).get("status"), "TXN APPROVED")
        self.assertEqual(order.state, "draft")
        self.assertFalse(order.payment_ids)
