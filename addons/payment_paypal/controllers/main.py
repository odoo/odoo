# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_paypal import const

_logger = get_payment_logger(__name__)


class PaypalController(http.Controller):
    _webhook_url = "/payment/paypal/webhook/"

    @http.route(const.PAYMENT_COMPLETE_ORDER_ROUTE, type="jsonrpc", methods=["POST"], auth="public")
    def paypal_complete_order(self, reference):
        """Make a capture request and process the payment data.

        :param str reference: The reference of the transaction whose order must be captured
        :return: None
        """
        tx_sudo = (
            self
            .env["payment.transaction"]
            .sudo()
            ._search_by_reference("paypal", {"reference_id": reference})
        )
        if tx_sudo:
            self._paypal_capture_order(tx_sudo)

    @http.route(const.PAYMENT_RETURN_ROUTE, type="http", methods=["GET"], auth="public")
    def paypal_return_from_checkout(self, **data):
        """Process the payment data sent by PayPal after redirection from an alternative payment
        method checkout.

        :param dict data: The transaction reference embedded in the return URL, together with the
                          payment data appended by PayPal
        :return: The redirection to the payment status page
        """
        self._handle_redirection(data)
        return request.redirect("/payment/status")

    @http.route(const.PAYMENT_CANCEL_ROUTE, type="http", methods=["GET"], auth="public")
    def paypal_cancel_payment(self, **data):
        """Process the payment cancellation initiated by the customer sent by PayPal after
        redirection from an alternative payment method checkout.

        :param dict data: The transaction reference embedded in the return URL, together with the
                          payment data appended by PayPal
        :return: The redirection to the payment status page
        """
        self._handle_redirection(data, is_canceled=True)
        return request.redirect("/payment/status")

    def _handle_redirection(self, data, is_canceled=False):
        """Process the payment data of the transaction the customer was redirected back from.

        :param dict data: The transaction reference embedded in the return URL, together with the
                          payment data appended by PayPal
        :param bool is_canceled: Whether the customer canceled the payment
        :rtype: None
        """
        _logger.info("Handling redirection from PayPal with data:\n%s", pprint.pformat(data))

        if not payment_utils.check_access_token(data.get("access_token"), data.get("reference")):
            _logger.warning("Received invalid access token in paypal redirection")
            raise Forbidden

        tx_sudo = (
            self
            .env["payment.transaction"]
            .sudo()
            ._search_by_reference("paypal", {"reference_id": data.get("reference")})
        )
        if not tx_sudo:
            return

        if tx_sudo.payment_method_code in {"paypal", "card"}:
            self._paypal_capture_order(tx_sudo)
        else:
            order_id = tx_sudo.provider_reference
            order_details = tx_sudo._send_api_request("GET", f"/v2/checkout/orders/{order_id}")
            normalized_data = self._normalize_paypal_data(order_details)
            if is_canceled:
                normalized_data["status"] = "CANCELED"
            tx_sudo._record(normalized_data)

    def _paypal_capture_order(self, tx_sudo):
        """Capture the order of the transaction and record the resulting payment data on it.

        :param payment.transaction tx_sudo: The sudoed transaction to capture the order for
        :rtype: None
        :raise ValidationError: If the 3D Secure authentication failed
        """
        order_id = tx_sudo.provider_reference
        if tx_sudo.payment_method_code == "card":
            order_details = tx_sudo._send_api_request("GET", f"/v2/checkout/orders/{order_id}")
            card_info = order_details.get("payment_source", {}).get("card", {})
            auth_result = card_info.get("authentication_result", {})
            if auth_result and auth_result.get("liability_shift") != "POSSIBLE":
                raise ValidationError(self.env._("3D Secure authentication failed."))

        idempotency_key = payment_utils.generate_idempotency_key(tx_sudo, scope="capture_order")
        response = tx_sudo._send_api_request(
            "POST", f"/v2/checkout/orders/{order_id}/capture", idempotency_key=idempotency_key
        )
        tx_sudo._record(self._normalize_paypal_data(response, is_capture_request=True))

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
        elif event_type in const.MERCHANT_WEBHOOK_EVENTS:
            self._handle_merchant_notification(data)
        return request.make_json_response("")

    def _handle_checkout_notification(self, data):
        """Handle a checkout webhook notification and record the payment data on the transaction.

        :param dict data: The notification data sent by PayPal
        :return: None
        """
        normalized_data = self._normalize_paypal_data(data.get("resource"))
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
            self._verify_notification_origin(data, tx_sudo.provider_id)
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

    def _normalize_paypal_data(self, data, is_capture_request=False):
        """Normalize the payment data received from PayPal.

        The payment data received from PayPal has a different format depending on whether the data
        come from the payment request response (order creation or capture), or from the webhook.

        :param dict data: The data to normalize
        :param bool is_capture_request: Whether the data came from a capture API call
        :return: The normalized data
        :rtype: dict
        """
        purchase_unit = data["purchase_units"][0]
        result = {
            "payment_source": data.get("payment_source"),
            "reference_id": purchase_unit.get("reference_id"),
            "purchase_units": data.get("purchase_units"),
        }
        if not is_capture_request:
            result.update({
                **purchase_unit,
                "txn_type": data.get("intent"),
                "id": data.get("id"),
                "status": data.get("status"),
            })
        elif captured := purchase_unit.get("payments", {}).get("captures"):
            result.update({**captured[0], "txn_type": "CAPTURE"})
        else:
            _logger.warning("Invalid response format; can't normalize.")
        return result

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
