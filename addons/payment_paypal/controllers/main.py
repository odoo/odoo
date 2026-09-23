import pprint

from odoo import http
from odoo.http import request

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger

_logger = get_payment_logger(__name__)


class PaypalController(http.Controller):
    _complete_url = "/payment/paypal/complete_order"
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
            request.env["payment.transaction"]
            .sudo()
            ._search_by_reference("paypal", {"reference_id": reference})
        )
        if tx_sudo:
            idempotency_key = payment_utils.generate_idempotency_key(
                tx_sudo, scope="payment_request_controller"
            )
            response = tx_sudo._send_api_request(
                "POST",
                f"/v2/checkout/orders/{order_id}/capture",
                idempotency_key=idempotency_key,
            )
            normalized_response = request.env[
                "payment.transaction"
            ]._normalize_paypal_data(response)
            tx_sudo = (
                request.env["payment.transaction"]
                .sudo()
                ._search_by_reference("paypal", normalized_response)
            )
            tx_sudo._process("paypal", normalized_response)

    # csrf=False: auth="receiver" admits the caller through its inbound gate
    @http.route(
        _webhook_url,
        type="http",
        auth="receiver",
        receiver="payment.transaction:_receiver_for_paypal_webhook",
        methods=["POST"],
        csrf=False,
        typed=True,
    )
    def paypal_webhook(self):
        """Process the payment data sent by PayPal to the webhook.

        See https://developer.paypal.com/docs/api/webhooks/v1/.

        :return: An empty string to acknowledge the notification.
        :rtype: str
        """
        _logger.info(
            "Notification received from PayPal with data:\n%s",
            pprint.pformat(request.get_json_data()),
        )
        request.admission.subject._process("paypal", request.admission.extra["data"])
        return request.prepare_json_response("")
