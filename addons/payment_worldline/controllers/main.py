import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment.logging import get_payment_logger

_logger = get_payment_logger(__name__)


class WorldlineController(http.Controller):
    _return_url = "/payment/worldline/return"
    _webhook_url = "/payment/worldline/webhook"

    @http.route(_return_url, type="http", auth="public", methods=["GET"])
    def worldline_return_from_checkout(self, **data):
        """Process the payment data sent by Worldline after redirection.

        :param dict data: The payment data, including the provider id appended to the URL in
                          `_prepare_redirect_form_values`.
        """
        _logger.info(
            "Handling redirection from Worldline with data:\n%s", pprint.pformat(data)
        )

        provider_id = int(data["provider_id"])
        provider_sudo = (
            request.env["payment.provider"].sudo().browse(provider_id).exists()
        )
        if not provider_sudo or provider_sudo.code != "worldline":
            _logger.warning("Received payment data with invalid provider id.")
            raise Forbidden

        try:
            # Fetch the checkout session data from Worldline.
            checkout_session_data = provider_sudo._send_api_request(
                "GET", f"hostedcheckouts/{data['hostedCheckoutId']}"
            )
        except ValidationError:
            _logger.error("Unable to process the payment data")
        else:
            payment_data = checkout_session_data.get("createdPaymentOutput", {})
            request.env["payment.transaction"].sudo()._process(
                "worldline", payment_data
            )
        return request.redirect("/payment/status")

    # csrf=False: auth="receiver" admits the caller through its inbound gate
    @http.route(
        _webhook_url,
        type="http",
        auth="receiver",
        receiver="payment.transaction:_receiver_for_worldline_webhook",
        methods=["POST"],
        csrf=False,
        typed=True,
    )
    def worldline_webhook(self):
        """Process the payment data sent by Worldline to the webhook.

        See https://docs.direct.worldline-solutions.com/en/integration/api-developer-guide/webhooks.

        :return: An empty string to acknowledge the notification.
        :rtype: str
        """
        _logger.info(
            "Notification received from Worldline with data:\n%s",
            pprint.pformat(request.get_json_data()),
        )
        request.admission.subject._process("worldline", request.admission.extra["data"])
        return request.prepare_json_response("")  # Acknowledge the notification.
