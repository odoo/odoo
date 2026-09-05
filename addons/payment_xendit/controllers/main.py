# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools import consteq, str2bool

from odoo.addons.payment import utils as payment_utils


_logger = logging.getLogger(__name__)


class XenditController(http.Controller):

    _webhook_url = '/payment/xendit/webhook'
    _return_url = '/payment/xendit/return'

    @http.route(_webhook_url, type='http', methods=['POST'], auth='public', csrf=False)
    def xendit_webhook(self):
        """ Process the notification data sent by Xendit to the webhook.

        :return: The 'accepted' string to acknowledge the notification.
        """
        data = request.get_json_data()
        _logger.info("Notification received from Xendit with data:\n%s", pprint.pformat(data))

        try:
            # Real webhooks are wrapped in an envelope; unwrap before processing.
            event = None
            if 'event' in data and 'data' in data:
                event = data.get('event')
                data = data['data']

            # Check the integrity of the notification.
            received_token = request.httprequest.headers.get('x-callback-token')
            tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                'xendit', data
            )
            self._verify_notification_token(received_token, tx_sudo)

            if event == 'payment_token.activation':
                # Provides the masked card number inline, sparing the extra API call otherwise
                # needed to tokenize from a payment notification.
                if tx_sudo.tokenize:
                    tx_sudo._xendit_tokenize_from_notification_data(data)
            else:
                # Handle the notification data.
                tx_sudo._handle_notification_data('xendit', data)
        except ValidationError:
            _logger.exception("Unable to handle notification data; skipping to acknowledge.")

        return request.make_json_response(['accepted'], status=200)

    @http.route(_return_url, type='http', methods=['GET'], auth='public')
    def xendit_return(self, tx_ref=None, success=False, access_token=None, **data):
        """Check the transaction status with Xendit after returning from checkout, falling back
        to pending if the webhook notification hasn't come in yet."""
        if access_token and str2bool(success, default=False):
            # A checkout redirect leaves the transaction in `draft` until this return or the
            # webhook processes it, but a token charge requiring 3DS authentication is already
            # `pending` by the time the customer comes back from the challenge.
            tx_sudo = request.env['payment.transaction'].sudo().search([
                ('provider_code', '=', 'xendit'),
                ('reference', '=', tx_ref),
                ('state', 'in', ('draft', 'pending')),
            ], limit=1)
            if tx_sudo and payment_utils.check_access_token(access_token, tx_ref, tx_sudo.amount):
                tx_sudo._xendit_sync_from_provider()
                if tx_sudo.state == 'draft':
                    tx_sudo._set_pending()
        return request.redirect('/payment/status')

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
