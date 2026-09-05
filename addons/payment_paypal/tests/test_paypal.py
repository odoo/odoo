# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_paypal.controllers.main import PaypalController
from odoo.addons.payment_paypal.tests.common import PaypalCommon


@tagged("post_install", "-at_install")
class PaypalTest(PaypalCommon, PaymentHttpCommon):
    def test_processing_values(self):
        tx = self._create_transaction(flow="direct")
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value={"id": self.order_id},
        ):
            processing_values = tx._get_processing_values()
        self.assertEqual(processing_values["order_id"], self.order_id)

    def test_apm_rendering_values(self):
        """Test that an alternative payment method redirects the customer to PayPal."""
        bancontact_pm = self.env.ref("payment_paypal.payment_method_bancontact").id
        tx = self._create_transaction(flow="redirect", payment_method_id=bancontact_pm)
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value=self.apm_order_data,
        ):
            processing_values = tx._get_processing_values()
        form_info = self._extract_values_from_html_form(processing_values["redirect_form_html"])
        self.assertEqual(form_info["action"], self.payer_action_url)
        self.assertEqual(form_info["method"], "get")
        self.assertEqual(tx.provider_reference, self.order_id)

    def test_order_payload_values_for_public_user(self):
        """If a payment is made with the public user we need to make sure that the email address is
        not sent to PayPal and that we provide the country code of the company instead."""
        paypal_pm = self.env.ref("payment_paypal.payment_method_paypal").id
        tx = self._create_transaction(
            flow="direct", partner_id=self.public_user.partner_id.id, payment_method_id=paypal_pm
        )
        payload = tx._paypal_prepare_order_payload()
        customer_payload = payload["payment_source"]["paypal"]
        self.assertTrue("email_address" not in customer_payload)
        self.assertEqual(customer_payload["address"]["country_code"], self.company.country_id.code)

    @mute_logger("odoo.addons.payment_paypal.controllers.main")
    def test_complete_order_confirms_transaction(self):
        """Test the processing of a webhook notification."""
        tx = self._create_transaction("direct")
        normalized_data = PaypalController._normalize_paypal_data(
            self, self.completed_order, is_capture_request=True
        )
        tx.with_context(payment_safe_write=True)._process(normalized_data)
        self.assertEqual(tx.state, "done")
        self.assertEqual(tx.provider_reference, normalized_data["id"])

    def test_feedback_processing(self):
        normalized_data = PaypalController._normalize_paypal_data(
            self, self.payment_data.get("resource")
        )

        # Confirmed transaction
        tx = self._create_transaction("direct")
        tx.with_context(payment_safe_write=True)._process(normalized_data)
        self.assertEqual(tx.state, "done")
        self.assertEqual(tx.provider_reference, normalized_data["id"])

        # Pending transaction
        self.reference = "Test Transaction 2"
        tx = self._create_transaction("direct")
        payload = {
            **normalized_data,
            "reference_id": self.reference,
            "status": "PENDING",
            "pending_reason": "multi_currency",
        }
        tx.with_context(payment_safe_write=True)._process(payload)
        self.assertEqual(tx.state, "pending")
        self.assertEqual(tx.state_message, payload["pending_reason"])

    @mute_logger("odoo.addons.payment_paypal.controllers.main")
    def test_webhook_notification_confirms_transaction(self):
        """Test the processing of a webhook notification."""
        tx = self._create_transaction("direct")
        url = self._build_url(PaypalController._webhook_url)
        with patch(
            "odoo.addons.payment_paypal.controllers.main.PaypalController"
            "._verify_notification_origin"
        ):
            self._make_json_request(url, data=self.payment_data)
        self._run_processing()
        self.assertEqual(tx.state, "done")

    @mute_logger("odoo.addons.payment_paypal.controllers.main")
    def test_order_declined_webhook_errors_transaction(self):
        """Test that a `CHECKOUT.ORDER.DECLINED` webhook notification errors the transaction."""
        tx = self._create_transaction("redirect")
        url = self._build_url(PaypalController._webhook_url)
        with patch(
            "odoo.addons.payment_paypal.controllers.main.PaypalController"
            "._verify_notification_origin"
        ):
            self._make_json_request(url, data=self.declined_notification)
        self._run_processing()
        self.assertEqual(tx.state, "error")
        self.assertEqual(tx.state_message, "The provided payment source cannot be used.")

    @mute_logger("odoo.addons.payment_paypal.controllers.main")
    def test_capture_denied_webhook_updates_tx_error_status(self):
        """Test that a `PAYMENT.CAPTURE.DENIED` webhook notification cancels the transaction.

        The transaction is matched through the order id (`provider_reference`) as the denied capture
        resource does not echo back the shared reference_id.
        """
        tx = self._create_transaction("redirect")
        self._update_transaction(tx, provider_reference=self.order_id)
        denied_notification = {
            "event_type": "PAYMENT.CAPTURE.DENIED",
            "resource": {
                "id": "8SS60826HT082593F",
                "status": "DECLINED",
                "amount": {"currency_code": self.currency.name, "value": str(self.amount)},
                "supplementary_data": {"related_ids": {"order_id": self.order_id}},
            },
        }
        url = self._build_url(PaypalController._webhook_url)
        with patch(
            "odoo.addons.payment_paypal.controllers.main.PaypalController"
            "._verify_notification_origin"
        ):
            self._make_json_request(url, data=denied_notification)
        self._run_processing()
        self.assertEqual(tx.state, "error")

    @mute_logger("odoo.addons.payment_paypal.controllers.main")
    def test_webhook_notification_triggers_origin_check(self):
        """Test that receiving a webhook notification triggers an origin check."""
        self._create_transaction("direct")
        url = self._build_url(PaypalController._webhook_url)
        with patch(
            "odoo.addons.payment_paypal.controllers.main.PaypalController"
            "._verify_notification_origin"
        ) as origin_check_mock:
            self._make_json_request(url, data=self.payment_data)
            self.assertEqual(origin_check_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_paypal.controllers.main")
    def test_webhook_notification_skips_processing_for_errored_txs(self):
        self._create_transaction("direct")
        PaymentTransaction = self.env.registry["payment.transaction"]
        url = self._build_url(PaypalController._webhook_url)
        with (
            patch.object(
                PaymentTransaction, "_send_api_request", side_effect=ValidationError("Test error")
            ),
            patch.object(PaymentTransaction, "_record") as record_mock,
        ):
            self._make_json_request(url, data=self.payment_data)
            self.assertEqual(record_mock.call_count, 0)

    def test_provide_shipping_address(self):
        if "sale.order" not in self.env:
            self.skipTest("Skipping shipping address test because sale is not installed.")

        product = self.env["product.product"].create({"name": "$5", "list_price": 5.0})
        order = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "order_line": [Command.create({"product_id": product.id})],
        })
        paypal_pm = self.env.ref("payment_paypal.payment_method_paypal").id
        tx = self._create_transaction(
            flow="direct", sale_order_ids=[Command.set(order.ids)], payment_method_id=paypal_pm
        )

        payload = tx._paypal_prepare_order_payload()
        self.assertEqual(
            payload["payment_source"]["paypal"]["experience_context"]["shipping_preference"],
            "SET_PROVIDED_ADDRESS",
            "Address should be provided when possible",
        )
        self.assertDictEqual(
            payload["purchase_units"][0]["shipping"]["address"],
            {
                "address_line_1": tx.partner_id.street,
                "address_line_2": tx.partner_id.street2,
                "postal_code": tx.partner_id.zip,
                "admin_area_2": tx.partner_id.city,
                "country_code": tx.partner_id.country_code,
            },
        )

        # Set country to one where state is required
        self.partner.country_id = self.env.ref("base.us")
        payload = tx._paypal_prepare_order_payload()
        self.assertEqual(
            payload["payment_source"]["paypal"]["experience_context"]["shipping_preference"],
            "NO_SHIPPING",
            "No shipping should be set if address values are incomplete",
        )
        self.assertNotIn("shipping", payload["purchase_units"][0])

        self.partner.child_ids = [
            Command.create({
                "name": tx.partner_id.name,
                "type": "delivery",
                "street": "40 Wall Street",
                "city": "New York City",
                "zip": "10005",
                "state_id": self.env.ref("base.state_us_27").id,
                "country_id": tx.partner_id.country_id.id,
            })
        ]
        shipping_partner = tx.sale_order_ids.partner_shipping_id = self.partner.child_ids
        payload = tx._paypal_prepare_order_payload()
        self.assertEqual(
            payload["payment_source"]["paypal"]["experience_context"]["shipping_preference"],
            "SET_PROVIDED_ADDRESS",
            "Address should be provided when partner has a complete delivery address",
        )
        self.assertDictEqual(
            payload["purchase_units"][0]["shipping"]["address"],
            {
                "address_line_1": shipping_partner.street,
                "postal_code": shipping_partner.zip,
                "admin_area_1": shipping_partner.state_id.code,
                "admin_area_2": shipping_partner.city,
                "country_code": shipping_partner.country_code,
            },
        )
