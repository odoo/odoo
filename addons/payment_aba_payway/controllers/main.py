# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pprint

from odoo import http
from odoo.http import request

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_aba_payway import const

_logger = get_payment_logger(__name__)


class AbaPaywayController(http.Controller):
    @http.route(const.PAYMENT_RETURN_ROUTE, type="http", auth="public", methods=["GET"])
    def aba_payway_return_from_checkout(self, **data):
        """Fetch the status of the transaction from ABA PayWay after redirection from the checkout.

        The status is only fetched if the webhook notification was not received yet.

        :param dict data: The transaction reference (`tran_id`) embedded in the return URL.
        :return: A redirection to the payment status page.
        :rtype: Response
        """
        _logger.info("Handling redirection from ABA PayWay with data:\n%s", pprint.pformat(data))
        tx_sudo = self.env["payment.transaction"].sudo()._search_by_reference("aba_payway", data)
        if tx_sudo and tx_sudo.state == "draft" and not tx_sudo.payment_data_ids:
            tx_sudo._aba_payway_sync_from_provider()
        return request.redirect("/payment/status")

    @http.route(
        const.WEBHOOK_ROUTE,
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def aba_payway_webhook(self):
        """Process the payment data sent by ABA PayWay to the webhook.

        The route is flagged with `save_session=False` to prevent Odoo from assigning a new session
        to the user.

        :return: An empty JSON response to acknowledge the notification.
        :rtype: Response
        """
        data = request.get_json_data()
        _logger.info("Notification received from ABA PayWay with data:\n%s", pprint.pformat(data))
        tx_sudo = self.env["payment.transaction"].sudo()._search_by_reference("aba_payway", data)
        if tx_sudo:
            # The signature is computed from all the values of the payment data, sorted by key
            received_signature = request.httprequest.headers.get("X-PayWay-HMAC-SHA512")
            expected_signature = tx_sudo.provider_id._aba_payway_calculate_signature(
                data, keys=sorted(data)
            )
            payment_utils.verify_signature(received_signature, expected_signature)
            tx_sudo._record(data)
        return request.make_json_response({})
