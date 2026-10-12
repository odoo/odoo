# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pprint

from odoo import http
from odoo.http import request

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_payu import const

_logger = get_payment_logger(__name__)


class PayuController(http.Controller):
    @http.route(
        const.PAYMENT_RETURN_ROUTE,
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def payu_return_from_checkout(self, **data):
        """Process the payment data sent by PayU after redirection from checkout.

        The route is flagged with `save_session=False` to prevent Odoo from assigning a new session
        to the user if they are redirected to this route with a POST request. Indeed, as the session
        cookie is created without a `SameSite` attribute, some browsers that don't implement the
        recommended default `SameSite=Lax` behavior will not include the cookie in the redirection
        request from the payment provider to Odoo. As the redirection to the '/payment/status' page
        will satisfy any specification of the `SameSite` attribute, the session of the user will be
        retrieved and with it the transaction which will be immediately post-processed.

        :param dict data: The payment data.
        """
        _logger.info("Handling redirection from PayU with data:\n%s", pprint.pformat(data))
        tx_sudo = self.env["payment.transaction"].sudo()._search_by_reference("payu", data)
        if tx_sudo:
            received_signature = data.get("hash")
            expected_signature = tx_sudo.provider_id._payu_generate_signature(data, incoming=True)
            payment_utils.verify_signature(received_signature, expected_signature)
            tx_sudo._record(data)
        return request.redirect("/payment/status")

    @http.route(const.WEBHOOK_ROUTE, type="http", auth="public", methods=["POST"], csrf=False)
    def payu_webhook(self, **data):
        """Process the payment data sent by PayU through the webhook.

        :return: An empty response to acknowledge the notification.
        :rtype: odoo.http.Response
        """
        _logger.info("Notification received from PayU with data:\n%s", pprint.pformat(data))
        tx_sudo = self.env["payment.transaction"].sudo()._search_by_reference("payu", data)
        if tx_sudo:
            received_signature = data.get("hash")
            expected_signature = tx_sudo.provider_id._payu_generate_signature(data, incoming=True)
            payment_utils.verify_signature(received_signature, expected_signature)
            tx_sudo._record(data)

        return request.make_json_response("")
