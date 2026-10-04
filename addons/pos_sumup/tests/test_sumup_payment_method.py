import json
from unittest.mock import patch

import requests
from requests import Response

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import tagged
from odoo.tools import hash_sign

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


def _response(status_code=200, json_data=None):
    response = Response()
    response.status_code = status_code
    response._content = json.dumps(json_data if json_data is not None else {}).encode()
    return response


@tagged("post_install", "-at_install")
class TestSumupPaymentMethod(TestPointOfSaleHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.main_pos_config.write(
            {
                "payment_method_ids": [
                    Command.create(
                        {
                            "name": "SumUp",
                            "type": "bank",
                            "payment_provider": "sumup",
                            "payment_method_type": "terminal",
                            "sumup_api_key": "test_api_key",
                            "sumup_merchant_code": "MTEST01",
                            "sumup_terminal_id": "rdr_test123",
                            "journal_id": cls.bank_journal.id,
                        },
                    ),
                ],
            },
        )
        cls.sumup_pm = cls.main_pos_config.payment_method_ids.filtered(
            lambda pm: pm.payment_provider == "sumup",
        )
        cls.currency = (
            cls.sumup_pm.journal_id.currency_id or cls.sumup_pm.company_id.currency_id
        )

        cls.main_pos_config.open_ui()
        cls.session = cls.main_pos_config.current_session_id
        cls.order = cls.env["pos.order"].create(
            {
                "session_id": cls.session.id,
                "company_id": cls.main_pos_config.company_id.id,
                "amount_tax": 0.0,
                "amount_total": 10.0,
                "amount_paid": 10.0,
                "amount_return": 0.0,
            },
        )

    def _make_sumup_payment(self, transaction_id="original_ctid"):
        return self.env["pos.payment"].create(
            {
                "pos_order_id": self.order.id,
                "payment_method_id": self.sumup_pm.id,
                "amount": 10.0,
                "transaction_id": transaction_id,
            },
        )

    def test_sumup_terminal_id_must_be_unique(self):
        with self.assertRaises(ValidationError):
            self.env["pos.payment.method"].create(
                {
                    "name": "SumUp 2",
                    "type": "bank",
                    "payment_provider": "sumup",
                    "sumup_terminal_id": self.sumup_pm.sumup_terminal_id,
                    "journal_id": self.bank_journal.id,
                },
            )

    def test_sumup_pay_sends_correct_request(self):
        with patch(
            "odoo.addons.pos_sumup.models.pos_payment_method.requests.post",
        ) as mock_post:
            mock_post.return_value = _response(
                200,
                {"data": {"client_transaction_id": "ctid1", "checkout_id": "chk1"}},
            )
            result = self.sumup_pm.sumup_pay(12.30)

        url = mock_post.call_args.args[0]
        kwargs = mock_post.call_args.kwargs
        self.assertIn("/merchants/MTEST01/readers/rdr_test123/checkout", url)
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test_api_key")
        self.assertEqual(
            kwargs["json"]["total_amount"],
            {
                "currency": self.currency.name,
                "minor_unit": self.currency.decimal_places,
                "value": round(12.30 * (10**self.currency.decimal_places)),
            },
        )
        self.assertEqual(result["data"]["client_transaction_id"], "ctid1")

    def test_sumup_pay_network_error(self):
        with patch(
            "odoo.addons.pos_sumup.models.pos_payment_method.requests.post",
            side_effect=requests.exceptions.ConnectionError(),
        ):
            result = self.sumup_pm.sumup_pay(10)

        self.assertIn("error", result)

    def test_sumup_refund_rejects_transaction_not_paid_with_sumup(self):
        with self.assertRaises(UserError):
            self.sumup_pm.sumup_refund(10, "some_unrelated_ctid")

    def test_sumup_refund_rejects_empty_transaction_id(self):
        with self.assertRaises(UserError):
            self.sumup_pm.sumup_refund(10, False)

    def test_sumup_refund_sends_correct_request(self):
        self._make_sumup_payment(transaction_id="ctid1")

        with (
            patch(
                "odoo.addons.pos_sumup.models.pos_payment_method.requests.get",
            ) as mock_get,
            patch(
                "odoo.addons.pos_sumup.models.pos_payment_method.requests.post",
            ) as mock_post,
        ):
            mock_get.return_value = _response(200, {"id": "real_txn_1"})
            mock_post.return_value = _response(200, {"data": {}})

            self.sumup_pm.sumup_refund(-12.30, "ctid1")

        # resolving the real SumUp transaction id
        self.assertEqual(
            mock_get.call_args.kwargs["params"],
            {"client_transaction_id": "ctid1"},
        )

        # the actual refund call, amount converted to a positive minor-unit integer
        refund_url = mock_post.call_args.args[0]
        self.assertIn("/payments/real_txn_1/refunds", refund_url)
        self.assertEqual(
            mock_post.call_args.kwargs["json"]["amount"],
            round(12.30 * (10**self.currency.decimal_places)),
        )

    def test_sumup_refund_no_matching_sumup_transaction(self):
        self._make_sumup_payment(transaction_id="ctid1")

        with patch(
            "odoo.addons.pos_sumup.models.pos_payment_method.requests.get",
        ) as mock_get:
            mock_get.return_value = _response(200, {})

            with self.assertRaises(UserError):
                self.sumup_pm.sumup_refund(-12.30, "ctid1")

    def test_sumup_cancel_sends_correct_request(self):
        with patch(
            "odoo.addons.pos_sumup.models.pos_payment_method.requests.post",
        ) as mock_post:
            mock_post.return_value = _response(200, {})
            self.sumup_pm.sumup_cancel()

        url = mock_post.call_args.args[0]
        self.assertIn("/readers/rdr_test123/terminate", url)

    def test_sumup_get_checkout_status(self):
        with patch(
            "odoo.addons.pos_sumup.models.pos_payment_method.requests.get",
        ) as mock_get:
            mock_get.return_value = _response(200, {"status": "successful"})
            result = self.sumup_pm.sumup_get_checkout_status("chk1")

        url = mock_get.call_args.args[0]
        self.assertIn("/readers/rdr_test123/checkout/chk1", url)
        self.assertEqual(result, {"status": "successful"})

    def test_webhook_notification_notifies_the_bus(self):
        token = hash_sign(
            self.env,
            "pos_sumup",
            {"payment_method_id": self.sumup_pm.id},
            expiration_hours=1,
        )
        payload = {"client_transaction_id": "ctid1", "status": "successful"}

        with patch(
            "odoo.addons.point_of_sale.models.pos_bus_mixin.PosBusMixin._notify",
        ) as mock_notify:
            response = self.url_open(
                f"/pos_sumup/notification?token={token}",
                data=json.dumps({"payload": payload}),
                headers={"Content-Type": "application/json"},
            )

        self.assertEqual(response.status_code, 200)
        mock_notify.assert_called_once_with("SUMUP_LATEST_RESPONSE", payload)

    def test_webhook_notification_ignores_invalid_token(self):
        payload = {
            "payload": {"client_transaction_id": "ctid1", "status": "successful"},
        }

        with (
            self.assertLogs(
                "odoo.addons.pos_sumup.controllers.webhook",
                level="WARNING",
            ),
            patch(
                "odoo.addons.point_of_sale.models.pos_bus_mixin.PosBusMixin._notify",
            ) as mock_notify,
        ):
            self.url_open(
                "/pos_sumup/notification?token=not_a_valid_token",
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
            )

        mock_notify.assert_not_called()
