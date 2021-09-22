# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

import requests

from odoo import _, http
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class PaypalController(http.Controller):
    _return_url = '/payment/paypal/dpn/'
    _notify_url = '/payment/paypal/ipn/'

    @http.route(_return_url, type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def paypal_dpn(self, **data):
        """ Route used by the PDT notification.

        The "PDT notification" is actually POST data sent along the user redirection.
        The route also allows the GET method in case the user clicks on "go back to merchant site".
        """
        _logger.info("beginning DPN with post data:\n%s", pprint.pformat(data))
        try:
            self._validate_data_authenticity(**data)
        except ValidationError:
            pass  # The transaction has been moved to state 'error'. Redirect to /payment/status.
        else:
            if data:
                request.env['payment.transaction'].sudo()._handle_feedback_data('paypal', data)
            else:
                pass  # The customer has cancelled the payment, don't do anything
        return request.redirect('/payment/status')

    @http.route(_notify_url, type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def paypal_ipn(self, **data):
        """ Route used by the IPN. """
        _logger.info("beginning IPN with post data:\n%s", pprint.pformat(data))
        try:
            self._validate_data_authenticity(**data)
            request.env['payment.transaction'].sudo()._handle_feedback_data('paypal', data)
        except ValidationError:  # Acknowledge the notification to avoid getting spammed
            _logger.exception("unable to handle the IPN data; skipping to acknowledge the notif")
        return ''

    def _validate_data_authenticity(self, **data):
        """ Validate the authenticity of data received through DPN or IPN

        The verification is done in three steps:
          - 1: POST the complete, unaltered, message back to Paypal (preceded by
               `cmd=_notify-validate`), in the same encoding.
          - 2: PayPal sends back either 'VERIFIED' or 'INVALID'.
          - 3: Return an empty HTTP 200 response (done at the end of the route method).
        See https://developer.paypal.com/docs/api-basics/notifications/ipn/IPNIntro

        As per https://developer.paypal.com/docs/api-basics/notifications/payment-data-transfer/,
        PDT notifications should be verified in a similar but different manner:
          - The transaction ID should be retrieved from the GET param `tx`.
          - The POST should use `_notify-synch` (as per previous versions of this method) as `cmd`,
            and only have as params the transaction ID and the PDT Identity Token (under the key
            `at`, as per previous versions of this method).
          - The payment data should be parsed from the response of the check request.
        In practice, however, the transaction ID is never given by PayPal and the documentation
        has no mention of `_notify_synch` nor `at`. Because of this, PDT cannot be verified as
        prescribed by the documentation.
        Nevertheless, previous versions of this method used a bad heuristic (assessing the presence
        of the optional, PDT-specific, param `amt`) to determine whether the notification was a PDT.
        Since PDT notifications have in practice always been successfully authenticated by using the
        IPN protocol, this method does explicitly that for both PDT and IPN.

        :param dict data: The data whose authenticity to check
        :return: None
        :raise: ValidationError if the authenticity could not be verified
        """
        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_feedback_data(
            'paypal', data
        )
        acquirer_sudo = tx_sudo.acquirer_id

        # Request PayPal for an authenticity check
        data['cmd'] = '_notify-validate'
        response = requests.post(acquirer_sudo._paypal_get_api_url(), data, timeout=60)
        response.raise_for_status()

        # Inspect the response code and raise if not 'VERIFIED'.
        response_code = response.text
        if response_code == 'VERIFIED':
            _logger.info("authenticity of notification data verified")
        else:
            if response_code == 'INVALID':
                error_message = "PayPal: " + _("Notification data were not acknowledged.")
            else:
                error_message = "PayPal: " + _(
                    "Received unrecognized authentication check response code: received %s, "
                    "expected VERIFIED or INVALID.",
                    response_code
                )
            tx_sudo._set_error(error_message)
            raise ValidationError(error_message)
