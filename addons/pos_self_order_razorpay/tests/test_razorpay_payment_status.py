# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from itertools import count
from unittest.mock import patch
from uuid import uuid4

from odoo import Command, fields
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.pos_razorpay.models.razorpay_pos_request import RazorpayPosRequest
from odoo.tests.common import tagged


@tagged("post_install_l10n", "post_install", "-at_install")
class TestRazorpayPaymentStatus(TestPointOfSaleHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.currency_id = cls.env.ref("base.INR")
        cls.razorpay_payment_method = cls.env["pos.payment.method"].create({
            "name": "Razorpay",
            "payment_method_type": "terminal",
            "use_payment_terminal": "razorpay",
            "razorpay_tid": "my_tid",
            "razorpay_allowed_payment_modes": "all",
            "razorpay_username": "my_username",
            "razorpay_api_key": "my_token",
            "razorpay_test_mode": True,
            "journal_id": cls.bank_journal.id,
        })
        cls.main_pos_config.write({
            "use_pricelist": False,
            "self_ordering_mode": "kiosk",
            "self_ordering_default_user_id": cls.pos_user.id,
            "payment_method_ids": [Command.set(cls.razorpay_payment_method.ids)],
        })
        cls.main_pos_config.with_user(cls.pos_user).open_ui()

    def setUp(self):
        super().setUp()
        # Fake Razorpay server: like the real API, it approves the status of any known Razorpay
        # reference, whatever order or amount it was issued for.
        self.razorpay_transactions = {}
        p2p_request_ids = count(1000)

        def fake_call_razorpay(payment_method, endpoint, payload):
            if endpoint == "pay":
                p2p_request_id = next(p2p_request_ids)
                self.razorpay_transactions[p2p_request_id] = payload["externalRefNumber"]
                return {"success": True, "p2pRequestId": p2p_request_id}
            if endpoint == "status":
                p2p_request_id = int(payload["origP2pRequestId"])
                if p2p_request_id not in self.razorpay_transactions:
                    return {"success": False, "errorMessage": "Unknown p2pRequestId"}
                return {
                    "success": True,
                    "status": "AUTHORIZED",
                    "messageCode": "P2P_DEVICE_TXN_DONE",
                    "p2pRequestId": p2p_request_id,
                    "nameOnCard": "Test User",
                    "externalRefNumber": self.razorpay_transactions[p2p_request_id],
                }
            raise NotImplementedError(endpoint)
        self.fake_call_razorpay = fake_call_razorpay

    def _create_order(self, amount):
        order = self.env["pos.order"].create({
            "uuid": uuid4(),
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
        return self.razorpay_payment_method._payment_request_from_kiosk(order)

    def _fetch_payment_status(self, order, payment):
        params = {
            "access_token": self.main_pos_config.access_token,
            "order_id": order.id,
            "payment_method_id": self.razorpay_payment_method.id,
            "payment_data": {
                "p2pRequestId": payment["p2pRequestId"],
                "razorpay_signature": payment.get("razorpay_signature"),
                "order_token": order.access_token,
            },
        }
        response = self.url_open(
            "/pos-self-order/razorpay-fetch-payment-status/",
            data=json.dumps({"jsonrpc": "2.0", "params": params}),
            headers={"Content-Type": "application/json"},
        )
        return response.json()

    def test_matching_transaction_succeeds(self):
        order = self._create_order(100)
        result = {}
        with patch.object(RazorpayPosRequest, "_call_razorpay", self.fake_call_razorpay):
            payment = self._start_kiosk_payment(order)
            result = self._fetch_payment_status(order, payment)

        self.assertTrue(result["result"]["status"])
        self.assertEqual(order.state, "paid")
        self.assertEqual(order.payment_ids.amount, 100)

    def test_replay_on_another_order_is_rejected(self):
        cheap_order = self._create_order(1)
        expensive_order = self._create_order(5000)
        # The cheap transaction is paid on the terminal, but its status is never fetched for the cheap order.
        result = {}
        with patch.object(RazorpayPosRequest, "_call_razorpay", self.fake_call_razorpay):
            payment = self._start_kiosk_payment(cheap_order)
            result = self._fetch_payment_status(expensive_order, payment)
        self.assertFalse(result.get("result", {}).get("status"))
        self.assertEqual(expensive_order.state, "draft")
        self.assertFalse(expensive_order.payment_ids)

    def test_replay_after_amount_change_is_rejected(self):
        order = self._create_order(1)
        result = {}
        with patch.object(RazorpayPosRequest, "_call_razorpay", self.fake_call_razorpay):
            payment = self._start_kiosk_payment(order)
            order.amount_total = 5000
            result = self._fetch_payment_status(order, payment)
        self.assertFalse(result.get("result", {}).get("status"))
        self.assertEqual(order.state, "draft")
        self.assertFalse(order.payment_ids)

    def test_missing_or_forged_signature_is_rejected(self):
        order = self._create_order(100)
        with patch.object(RazorpayPosRequest, "_call_razorpay", self.fake_call_razorpay):
            payment = self._start_kiosk_payment(order)
            for signature in (None, "", "forged"):
                result = self._fetch_payment_status(order, {**payment, "razorpay_signature": signature})
                self.assertFalse(result.get("result", {}).get("status"))
        self.assertEqual(order.state, "draft")
        self.assertFalse(order.payment_ids)
