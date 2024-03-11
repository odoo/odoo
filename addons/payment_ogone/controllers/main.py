# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hmac
import logging
import pprint
import re

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class OgoneController(http.Controller):
    _return_url = '/payment/ogone/return'
    _backward_compatibility_urls = [
        '/payment/ogone/accept', '/payment/ogone/test/accept',
        '/payment/ogone/decline', '/payment/ogone/test/decline',
        '/payment/ogone/exception', '/payment/ogone/test/exception',
        '/payment/ogone/cancel', '/payment/ogone/test/cancel',
        '/payment/ogone/validate/accept',
        '/payment/ogone/validate/decline',
        '/payment/ogone/validate/exception',
    ]  # Facilitates the migration of users who registered the URLs in Ogone's backend prior to 14.3

    @http.route(
        [_return_url] + _backward_compatibility_urls, type='http', auth='public',
        methods=['GET', 'POST'], csrf=False
    )  # Redirect are made with GET requests only. Webhook notifications can be set to GET or POST.
    def ogone_return_from_checkout(self, **raw_data):
        """ Process the notification data sent by Ogone after redirection from checkout.

        This route can also accept S2S notifications from Ogone if it is configured as a webhook in
        Ogone's backend. The user can choose between GET or POST for the webhook notifications.

        :param dict raw_data: The un-formatted notification data
        """
        _logger.info("handling redirection from Ogone with data:\n%s", pprint.pformat(raw_data))
        data = self._normalize_data_keys(raw_data)

        # Check the integrity of the notification
        received_signature = data.get('SHASIGN')
        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
            'ogone', data
        )
        self._verify_notification_signature(raw_data, received_signature, tx_sudo)

        # Handle the notification data
        tx_sudo._handle_notification_data('ogone', data)
        return request.redirect('/payment/status')

    @staticmethod
    def _normalize_data_keys(data):
        """ Set all keys of a dictionary to upper-case.

        The keys received from Ogone APIs have inconsistent formatting and must be homogenized to
        allow re-using the same methods. We reformat them to follow a unified nomenclature inspired
        by Ogone Directlink API.

        Formatting steps:
        1) Uppercase key strings: 'Something' -> 'SOMETHING', 'something' -> 'SOMETHING'
        2) Remove the prefix: 'CARD.SOMETHING' -> 'SOMETHING', 'ALIAS.SOMETHING' -> 'SOMETHING'

        :param dict data: The data whose keys to normalize
        :return: The normalized data
        :rtype: dict
        """
        return {re.sub(r'.*\.', '', k.upper()): v for k, v in data.items()}

    @staticmethod
    def _verify_notification_signature(notification_data, received_signature, tx_sudo):
        """ Check that the received signature matches the expected one.

        :param dict notification_data: The notification data
        :param str received_signature: The signature received with the notification data
        :param recordset tx_sudo: The sudoed transaction referenced by the notification data, as a
                                  `payment.transaction` record
        :return: None
        :raise: :class:`werkzeug.exceptions.Forbidden` if the signatures don't match
        """
        # Check for the received signature
        if not received_signature:
            _logger.warning("received notification with missing signature")
            raise Forbidden()

        # Compare the received signature with the expected signature computed from the data
        expected_signature = tx_sudo.provider_id._ogone_generate_signature(notification_data)
        if not hmac.compare_digest(received_signature, expected_signature.upper()):
            _logger.warning("received notification with invalid signature")
            raise Forbidden()
