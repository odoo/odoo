# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_paypal import const
from odoo.addons.payment_paypal import utils as paypal_utils

_logger = get_payment_logger(__name__)


class PaypalController(http.Controller):
    _complete_url = "/payment/paypal/complete_order"
    _return_url = "/payment/paypal/return"
    _cancel_url = "/payment/paypal/cancel"
    _webhook_url = "/payment/paypal/webhook/"

    @http.route(_complete_url, type="jsonrpc", auth="public", methods=["POST"])
    def paypal_complete_order(self, order_id, reference):
        """Make a capture request and process the payment data.

        :param string order_id: The order id provided by PayPal to identify the order.
        :param str reference: The reference of the transaction, used to generate the idempotency
                              key.
        :return: None
        """
        tx_sudo = (
            self
            .env["payment.transaction"]
            .sudo()
            ._search_by_reference("paypal", {"reference_id": reference})
        )
        if tx_sudo:
            if tx_sudo.operation == "validation":
                # The customer approved the setup token; upgrade it to a payment token.
                tx_sudo._paypal_create_payment_token()
            else:
                self._paypal_capture_order(tx_sudo, order_id)

    @http.route(_return_url, type="http", auth="public", methods=["GET"], save_session=False)
    def paypal_return_from_checkout(self, token=None, **data):
        """Process the payment data sent by PayPal after redirection from an alternative payment
        method checkout.

        :param dict data: The transaction reference embedded in the return URL, together
                          with the data appended by PayPal (e.g. `token`, `PayerID`).
        """
        _logger.info("Handling redirection from PayPal with data:\n%s", pprint.pformat(data))
        tx_sudo = (
            self
            .env["payment.transaction"]
            .sudo()
            ._search_by_reference("paypal", {"reference_id": data.get("reference")})
        )
        if tx_sudo:
            order_id = token or tx_sudo.provider_reference
            if tx_sudo.operation == "validation":
                tx_sudo._paypal_create_payment_token()
            elif tx_sudo.payment_method_code in {"paypal", "card"}:
                self._paypal_capture_order(tx_sudo, order_id)
            else:
                normalized_data = self._fetch_normalized_paypal_order(tx_sudo, order_id)
                tx_sudo._record(normalized_data)
        return request.redirect("/payment/status")

    @http.route(_cancel_url, type="http", auth="public", methods=["GET"], save_session=False)
    def paypal_cancel_payment(self, token=None, **data):
        """Process the payment cancellation initated by the customer sent by PayPal after
        redirection from an alternative payment method checkout.

        :param dict data: The transaction reference embedded in the return URL, together
                            with the data appended by PayPal (e.g. `token`, `PayerID`).
        """
        _logger.info("Handling redirection from PayPal with data:\n%s", pprint.pformat(data))
        tx_sudo = (
            self
            .env["payment.transaction"]
            .sudo()
            ._search_by_reference("paypal", {"reference_id": data.get("reference")})
        )
        if tx_sudo:
            order_id = token or tx_sudo.provider_reference
            if tx_sudo.operation == "validation":
                normalized_data = {"id": tx_sudo.provider_reference}
            else:
                normalized_data = self._fetch_normalized_paypal_order(tx_sudo, order_id)
            normalized_data["status"] = "CANCELED"
            tx_sudo._record(normalized_data)
        return request.redirect("/payment/status")

    @http.route(_webhook_url, type="http", auth="public", methods=["POST"], csrf=False)
    def paypal_webhook(self):
        """Process the webhook notification sent by PayPal to the webhook.

        See https://developer.paypal.com/docs/api/webhooks/v1/.

        :return: An empty string to acknowledge the notification
        :rtype: str
        """
        data = request.get_json_data()
        _logger.info("Notification received from PayPal with data:\n%s", pprint.pformat(data))
        event_type = data.get("event_type")
        if event_type in const.CHECKOUT_WEBHOOK_EVENTS:
            self._handle_checkout_notification(data)
        elif event_type in const.CAPTURE_WEBHOOK_EVENTS:
            self._handle_capture_notification(data)
        elif event_type in const.VAULT_WEBHOOK_EVENTS:
            self._handle_vault_notification(data)
        elif event_type in const.MERCHANT_WEBHOOK_EVENTS:
            self._handle_merchant_notification(data)
        return request.make_json_response("")

    def _handle_checkout_notification(self, data):
        """Handle a checkout webhook notification and record the payment data on the transaction.

        :param dict data: The notification data sent by PayPal
        :return: None
        """
        normalized_data = paypal_utils.normalize_paypal_payment_data(data.get("resource"))
        tx_sudo = (
            self.env["payment.transaction"].sudo()._search_by_reference("paypal", normalized_data)
        )
        if not tx_sudo:
            return

        # Check the origin and integrity of the notification
        try:
            self._verify_notification_origin(data, tx_sudo.provider_id)
        except ValidationError:
            tx_sudo.with_context(
                # The verification request is idempotent; the handler is safe to replay
                payment_safe_write=True
            )._set_error(self.env._("Unable to verify the payment data"))
        else:
            if data.get("event_type") == "CHECKOUT.ORDER.DECLINED":
                normalized_data["status"] = "DECLINED"
                if errors := normalized_data.get("most_recent_errors"):
                    normalized_data["state_message"] = errors[0].get("description")
            tx_sudo._record(normalized_data)

    def _handle_capture_notification(self, data):
        """Process a payment capture notification and record the payment on the transaction.

        :param dict data: The notification data sent by PayPal.
        :return: None
        """
        resource = data.get("resource", {})
        tx_sudo = self.env["payment.transaction"].sudo()
        provider_reference = (
            resource.get("supplementary_data", {}).get("related_ids", {}).get("order_id")
        )
        if provider_reference:
            tx_sudo = tx_sudo.search(
                [("provider_code", "=", "paypal"), ("provider_reference", "=", provider_reference)],
                limit=1,
            )  # Instead of searching with provider reference possible to get order from PayPal.
        if not tx_sudo:
            return
        try:
            self._verify_notification_origin(data, tx_sudo=tx_sudo)
        except ValidationError:
            tx_sudo.with_context(
                # The verification request is idempotent; the handler is safe to replay.
                payment_safe_write=True
            )._set_error(self.env._("Unable to verify the payment data"))
        else:
            normalized_data = {
                "reference_id": tx_sudo.reference,
                "id": resource.get("id"),
                "status": resource.get("status"),
                "amount": resource.get("amount"),
            }
            tx_sudo._record(normalized_data)

    def _handle_merchant_notification(self, data):
        """Handle a merchant webhook onboarding notification and update the provider accordingly.

        :param dict data: The notification data sent by PayPal
        :rtype: None
        """
        # Find the provider linked to the merchant account
        merchant_id = data.get("resource", {}).get("merchant_id")
        if not merchant_id:
            return
        provider_sudo = (
            request
            .env["payment.provider"]
            .sudo()
            .search([("code", "=", "paypal"), ("paypal_account_id", "=", merchant_id)], limit=1)
        )
        if not provider_sudo:
            return

        # Check the origin and integrity of the notification
        self._verify_notification_origin(data, provider_sudo=provider_sudo)

        # The only handled merchant event is the confirmation of the merchant's email address
        provider_sudo.paypal_email_confirmed = True

    def _handle_vault_notification(self, notification_data):
        """Create a token from a `VAULT.PAYMENT-TOKEN.CREATED` webhook notification.

        See https://developer.paypal.com/api/rest/webhooks/event-names/#vault.

        :param dict notification_data: The full notification payload.
        :return: None
        """
        resource = notification_data.get("resource", {})
        provider_reference = resource.get("metadata", {}).get("order_id")
        if not provider_reference:
            return
        tx_sudo = (
            self.env["payment.transaction"]
            .sudo()
            .search(
                [("provider_code", "=", "paypal"), ("provider_reference", "=", provider_reference)],
                limit=1,
            )
        )
        if not tx_sudo or tx_sudo.token_id:
            return
        try:
            self._verify_notification_origin(notification_data, tx_sudo)
        except ValidationError:
            tx_sudo.with_context(
                # The verification request is idempotent; the handler is safe to replay.
                payment_safe_write=True
            )._set_error(self.env._("Unable to verify the tokenization data"))
        else:
            normalized_data = paypal_utils.normalize_paypal_payment_data(
                resource,
                event_type=notification_data.get("event_type"),
                payment_method_code=tx_sudo.payment_method_code,
            )
            tx_sudo._record(normalized_data)

    def _verify_notification_origin(self, payment_data, provider_sudo):
        """Check that the notification was sent by PayPal.

        See https://developer.paypal.com/docs/api/webhooks/v1/#verify-webhook-signature_post.

        :param dict payment_data: The payment data
        :param payment.provider provider_sudo: The sudoed provider handling the notification
        :return: None
        :raise Forbidden: If the notification origin can't be verified
        """
        headers = request.httprequest.headers
        if not provider_sudo:
            _logger.warning("Received payment data with no transaction or provider.")
            raise Forbidden
        data = {
            "transmission_id": headers.get("PAYPAL-TRANSMISSION-ID"),
            "transmission_time": headers.get("PAYPAL-TRANSMISSION-TIME"),
            "cert_url": headers.get("PAYPAL-CERT-URL"),
            "auth_algo": headers.get("PAYPAL-AUTH-ALGO"),
            "transmission_sig": headers.get("PAYPAL-TRANSMISSION-SIG"),
            "webhook_id": provider_sudo.paypal_webhook_id,
            "webhook_event": payment_data,
        }
        verification = provider_sudo._send_api_request(
            "POST", "/v1/notifications/verify-webhook-signature", json=data
        )
        if verification.get("verification_status") != "SUCCESS":
            _logger.warning("Received payment data that was not verified by PayPal.")
            raise Forbidden

    def _paypal_capture_order(self, tx_sudo, order_id):
        """Capture the order and record the resulting payment data on the transaction.

        :param payment.transaction tx_sudo: The sudoed transaction to capture the order for.
        :param str order_id: The order id provided by PayPal to identify the order.
        :return: None
        :raise ValidationError: If the 3D Secure authentication failed.
        """
        if tx_sudo.payment_method_code == "card":
            order_details = tx_sudo._send_api_request("GET", f"/v2/checkout/orders/{order_id}")
            card_info = order_details.get("payment_source", {}).get("card", {})
            auth_result = card_info.get("authentication_result", {})
            if auth_result and auth_result.get("liability_shift") != "POSSIBLE":
                raise ValidationError(self.env._("3D Secure authentication failed."))

        idempotency_key = payment_utils.generate_idempotency_key(
            tx_sudo, scope="payment_request_controller"
        )
        response = tx_sudo._send_api_request(
            "POST", f"/v2/checkout/orders/{order_id}/capture", idempotency_key=idempotency_key
        )
        normalized_response = paypal_utils.normalize_paypal_payment_data(
            response, has_capture_data=True
        )
        tx_sudo = (
            self
            .env["payment.transaction"]
            .sudo()
            ._search_by_reference("paypal", normalized_response)
        )
        if tx_sudo:
            tx_sudo._record(normalized_response)

    def _fetch_normalized_paypal_order(self, tx_sudo, order_id):
        order_details = tx_sudo._send_api_request(
            "GET", f"/v2/checkout/orders/{order_id}"
        )
        return paypal_utils.normalize_paypal_payment_data(order_details)
