import pprint

from odoo import http
from odoo.http import request

from odoo.addons.payment.logging import get_payment_logger

_logger = get_payment_logger(__name__)


class BuckarooController(http.Controller):
    _return_url = "/payment/buckaroo/return"
    _webhook_url = "/payment/buckaroo/webhook"

    # csrf=False: auth="receiver" admits the caller through its inbound gate
    @http.route(
        _return_url,
        type="http",
        auth="receiver",
        receiver="payment.transaction:_receiver_for_buckaroo_return",
        methods=["POST"],
        csrf=False,
        save_session=False,
        typed=True,
    )
    def buckaroo_return_from_checkout(self, **raw_data):
        """Process the payment data sent by Buckaroo after redirection from checkout.

        The route is flagged with `save_session=False` to prevent Odoo from assigning a new session
        to the user if they are redirected to this route with a POST request. Indeed, as the session
        cookie is created without a `SameSite` attribute, some browsers that don't implement the
        recommended default `SameSite=Lax` behavior will not include the cookie in the redirection
        request from the payment provider to Odoo. As the redirection to the '/payment/status' page
        will satisfy any specification of the `SameSite` attribute, the session of the user will be
        retrieved and with it the transaction which will be immediately post-processed.

        :param dict raw_data: The un-formatted payment data
        """
        _logger.info(
            "handling redirection from Buckaroo with data:\n%s",
            pprint.pformat(raw_data),
        )
        request.admission.subject._process("buckaroo", request.admission.extra["data"])
        return request.redirect("/payment/status")

    # csrf=False: auth="receiver" admits the caller through its inbound gate
    @http.route(
        _webhook_url,
        type="http",
        auth="receiver",
        receiver="payment.transaction:_receiver_for_buckaroo_webhook",
        methods=["POST"],
        csrf=False,
        typed=True,
    )
    def buckaroo_webhook(self, **raw_data):
        """Process the payment data sent by Buckaroo to the webhook.

        See https://www.pronamic.nl/wp-content/uploads/2013/04/BPE-3.0-Gateway-HTML.1.02.pdf.

        :param dict raw_data: The un-formatted payment data
        :return: An empty string to acknowledge the notification
        :rtype: str
        """
        _logger.info(
            "notification received from Buckaroo with data:\n%s",
            pprint.pformat(raw_data),
        )
        request.admission.subject._process("buckaroo", request.admission.extra["data"])
        return ""
