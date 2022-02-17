# Part of Odoo. See LICENSE file for full copyright and licensing details.

# import hashlib
# import hmac
# import json
import logging
import pprint
# from datetime import datetime

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class FlutterwaveController(http.Controller):
    _return_url = '/payment/flutterwave/return'
    _webhook_url = '/payment/flutterwave/webhook'

    @http.route(_return_url, type='http', auth='public', csrf=False)  # TODO ANV check if POST or GET and remove CSRF if GET
    def flutterwave_return_from_checkout(self, **data):
        """ Process the notification data sent by Flutterwave after redirection from checkout.

        :param dict data: The GET params appended to the URL in `_stripe_create_checkout_session` TODO check
        """
        # Handle the notification data
        request.env['payment.transaction'].sudo()._handle_notification_data('flutterwave', data)

        # Redirect the user to the status page
        return request.redirect('/payment/status')

    @http.route(_webhook_url, type='json', auth='public')
    def flutterwave_webhook(self):
        """ Process the notification data sent by Flutterwave to the webhook.

        :return: An empty string to acknowledge the notification
        :rtype: str
        """
        data = request.jsonrequest
        _logger.info("notification received from Flutterwave with data:\n%s", pprint.pformat(data))
        try:
            # Handle the notification data
            request.env['payment.acquirer'].sudo()._handle_notification_data('flutterwave', data)
        except ValidationError:  # Acknowledge the notification to avoid getting spammed
            _logger.exception("unable to handle the notification data; skipping to acknowledge")
        return ''
