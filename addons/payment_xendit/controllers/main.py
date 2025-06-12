# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.http import request
from odoo.tools import consteq, str2bool

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger


_logger = get_payment_logger(__name__)


class XenditController(http.Controller):

    _webhook_url = '/payment/xendit/webhook'
    _return_url = '/payment/xendit/return'

    @http.route('/payment/xendit/payment', type='jsonrpc', auth='public')
    def xendit_payment(self, reference, token_ref, auth_id=None):
        """ Make a payment by token request and handle the response.

        :param str reference: The reference of the transaction.
        :param str token_ref: The reference of the Xendit token to use to make the payment.
        :param str auth_id: The authentication id to use to make the payment.
        :return: None
        """
        tx_sudo = request.env['payment.transaction'].sudo().search([('reference', '=', reference)])
        tx_sudo._xendit_create_charge(token_ref, auth_id=auth_id)

    @http.route(_webhook_url, type='http', methods=['POST'], auth='public', csrf=False)
    def xendit_webhook(self):
        """Process the payment data sent by Xendit to the webhook.

        :return: The 'accepted' string to acknowledge the notification.
        """
        data = request.get_json_data()
        _logger.info("Notification received from Xendit with data:\n%s", pprint.pformat(data))

        received_token = request.httprequest.headers.get('x-callback-token')
        tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference('xendit', data)
        if tx_sudo:
            self._verify_notification_token(received_token, tx_sudo)
            tx_sudo._process('xendit', data)

        return request.make_json_response(['accepted'], status=200)

    @http.route(_return_url, type='http', methods=['GET'], auth='public')
    def xendit_return(self, tx_ref=None, success=False, access_token=None, **data):
        """Set draft transaction to pending after successfully returning from Xendit."""
        if access_token and str2bool(success, default=False):
            tx_sudo = request.env['payment.transaction'].sudo().search([
                ('provider_code', '=', 'xendit'),
                ('reference', '=', tx_ref),
                ('state', '=', 'draft'),
            ], limit=1)
            if tx_sudo and payment_utils.check_access_token(access_token, tx_ref, tx_sudo.amount):
                tx_sudo._set_pending()
        return request.redirect('/payment/status')

    def _verify_notification_token(self, received_token, tx_sudo):
        """ Check that the received token matches the saved webhook token.

        :param str received_token: The callback token received with the payment data.
        :param payment.transaction tx_sudo: The transaction referenced by the payment data.
        :return: None
        :raise Forbidden: If the tokens don't match.
        """
        # Check for the received token.
        if not received_token:
            _logger.warning("Received payment data with missing token.")
            raise Forbidden()

        if not consteq(tx_sudo.provider_id.xendit_webhook_token, received_token):
            _logger.warning("Received payment data with invalid callback token %r.", received_token)
            raise Forbidden()
