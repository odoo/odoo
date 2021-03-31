# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging
import pprint
import re

import werkzeug

from odoo import _, http
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools import ustr

_logger = logging.getLogger(__name__)


class OgoneController(http.Controller):
    _flexcheckout_return_url = '/payment/ogone/flexcheckout'
    _directlink_return_url = '/payment/ogone/directlink'

    @http.route(
        _flexcheckout_return_url, type='http', auth='public', methods=['GET', 'POST'], csrf=False
    )  # 'GET' or 'POST' depending on the configuration in Ogone backend
    def ogone_return_from_flexcheckout(self, **feedback_data):
        """ Process the data returned by Ogone after redirection to Flexcheckout.

        :param dict feedback_data: The feedback data
        """
        # Check the source and integrity of the data
        data = self._homogenize_data(feedback_data)
        self._verify_signature(feedback_data, data)

        # Create a token from the feedback data
        data['FEEDBACK_TYPE'] = 'flexcheckout'
        _logger.info("entering _handle_feedback_data with data:\n%s", pprint.pformat(data))
        tx_sudo = request.env['payment.transaction'].sudo()._handle_feedback_data('ogone', data)

        # Process the payment through the token
        tree = tx_sudo._ogone_send_order_request(request_3ds_authentication=True)

        # Handle the response
        redirect_html_element = tree.find('HTML_ANSWER')
        if redirect_html_element:
            # Ogone has inserted an HTML_ANSWER element in its response XML tree. This means that a
            # redirection to DirectLink's authentication page is required, as FlexCheckout is not
            # capable of handling authentications...
            # As per the documentation, the HTML must be inserted as-is into the current page, and
            # consists of a <form> bundled with a script to auto-submit the form once its inserted.
            # The content of the HTML is not sanitized to preserve the redirection in the script.
            # After redirection, the customer comes back to the directlink return URL and we proceed
            # with the (now authenticated) payment request.
            redirect_html = ustr(base64.b64decode(redirect_html_element.text))
            return request.render(
                'payment_ogone.directlink_feedback', {'redirect_html': redirect_html}
            )
        else:
            feedback_data = {
                'FEEDBACK_TYPE': 'directlink',
                'ORDERID': tree.get('orderID'),
                'tree': tree,
            }
            _logger.info(
                "entering _handle_feedback_data with data:\n%s", pprint.pformat(feedback_data)
            )
            request.env['payment.transaction'].sudo()._handle_feedback_data('ogone', feedback_data)
            if tx_sudo.state in ('cancel', 'error'):
                tx_sudo.token_id.active = False  # The initial payment failed, archive the token
            return werkzeug.utils.redirect('/payment/status')

    @http.route(
        _directlink_return_url, type='http', auth='public', methods=['GET', 'POST'], csrf=False
    )  # 'GET' or 'POST' depending on the configuration in Ogone backend
    def ogone_return_from_directlink(self, **feedback_data):
        """ Process the data returned by Ogone after redirection to Directlink authentication page.

        A redirection to Directlink can happen if a 3DS1 authentication is requested when sending
        the request for a new order. This should normally only happen for the first payment of a
        token as this is the only case where we specifically request the authentication if necessary
        and handle the redirection request if one is returned.

        :param dict feedback_data: The feedback data
        """
        # Check the source and integrity of the data
        data = self._homogenize_data(feedback_data)
        self._verify_signature(feedback_data, data)

        # Handle the feedback data
        data['FEEDBACK_TYPE'] = 'directlink'
        _logger.info("entering _handle_feedback_data with data:\n%s", pprint.pformat(data))
        tx_sudo = request.env['payment.transaction'].sudo()._handle_feedback_data('ogone', data)
        if tx_sudo.state in ('cancel', 'error'):
            tx_sudo.token_id.active = False  # The initial payment failed, archive the token
        return werkzeug.utils.redirect('/payment/status')

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
