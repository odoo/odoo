# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
import re

import werkzeug

from odoo import _, http
from odoo.exceptions import ValidationError
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
    )  # 'GET' or 'POST' depending on the configuration in Ogone backend
    def ogone_return_from_redirect(self, **feedback_data):
        """ Process the data returned by Ogone after redirection to the Hosted Payment Page.

        This route can also accept S2S notifications from Ogone if it is configured as a webhook in
        Ogone's backend.

        :param dict feedback_data: The feedback data
        """
        # Check the source and integrity of the data
        data = self._homogenize_data(feedback_data)
        self._verify_signature(feedback_data, data)

        # Handle the feedback data
        _logger.info("entering _handle_feedback_data with data:\n%s", pprint.pformat(data))
        request.env['payment.transaction'].sudo()._handle_feedback_data('ogone', data)
        return request.redirect('/payment/status')

    def _homogenize_data(self, data):
        """ Format keys to follow an homogenized convention inspired by Ogone Directlink API.

        The keys received from Ogone APIs have inconsistent formatting and must be homogenized to
        allow re-using the same methods. We reformat them to follow a unified nomenclature inspired
        by DirectLink's order direct endpoint.

        Formatting steps:
        1) Uppercase key strings: 'Something' -> 'SOMETHING', 'something' -> 'SOMETHING'
        2) Remove the prefix: 'CARD.SOMETHING' -> 'SOMETHING', 'ALIAS.SOMETHING' -> 'SOMETHING'
        """
        return {re.sub(r'.*\.', '', k.upper()): v for k, v in data.items()}

    def _verify_signature(self, sign_data, data):
        """ Check that the signature computed from the feedback matches the received one.

        :param dict sign_data: The original feedback data used to compute the signature
        :param dict sign_data: The formatted feedback data used to find the tx and received sig
        :return: None
        :raise: ValidationError if the signatures don't match
        """
        acquirer_sudo = request.env['payment.transaction'].sudo()._get_tx_from_feedback_data(
            'ogone', data
        ).acquirer_id  # Find the acquirer based on the transaction
        received_signature = data.get('SHASIGN')
        expected_signature = acquirer_sudo._ogone_generate_signature(sign_data)
        if received_signature != expected_signature.upper():
            raise ValidationError(
                "Ogone: " + _(
                    "Received data with invalid signature. expected: %(exp)s ; received: %(rec)s ; "
                    "data:\n%(data)s",
                    exp=expected_signature, rec=received_signature, data=pprint.pformat(sign_data)
                )
            )
