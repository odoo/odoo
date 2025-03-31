# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools import consteq


_logger = logging.getLogger(__name__)


class XenditController(http.Controller):

    _webhook_url = '/payment/xendit/webhook'

    @http.route('/payment/xendit/payment', type='json', auth='public')
    def xendit_payment(self, reference, token_ref):
        """ Make a payment by token request and handle the response.

        :param str reference: The reference of the transaction.
        :param str token_ref: The reference of the Xendit token to use to make the payment.
        :return: None
        """
        tx_sudo = request.env['payment.transaction'].sudo().search([('reference', '=', reference)])
        tx_sudo._xendit_create_charge(token_ref)

    @http.route(_webhook_url, type='http', methods=['POST'], auth='public', csrf=False)
    def xendit_webhook(self):
        """ Process the notification data sent by Xendit to the webhook.

        :return: The 'accepted' string to acknowledge the notification.
        """
        data = request.get_json_data()
        _logger.info("Notification received from Xendit with data:\n%s", pprint.pformat(data))

        try:
            # Check the integrity of the notification.
            received_token = request.httprequest.headers.get('x-callback-token')
            tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                'xendit', data
            )
            self._verify_notification_token(received_token, tx_sudo)

            # Handle the notification data.
            tx_sudo._handle_notification_data('xendit', data)
        except ValidationError:
            _logger.exception("Unable to handle notification data; skipping to acknowledge.")

        return request.make_json_response(['accepted'], status=200)

    def _verify_notification_token(self, received_token, tx_sudo):
        """ Check that the received token matches the saved webhook token.

        :param str received_token: The callback token received with the notification data.
        :param payment.transaction tx_sudo: The transaction referenced by the notification data.
        :return: None
        :raise Forbidden: If the tokens don't match.
        """
        # Check for the received token.
        if not received_token:
            _logger.warning("Received notification with missing token.")
            raise Forbidden()

        if not consteq(tx_sudo.provider_id.xendit_webhook_token, received_token):
            _logger.warning("Received notification with invalid callback token %r.", received_token)
            raise Forbidden()
