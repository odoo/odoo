# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

import requests
from requests.exceptions import ConnectionError, HTTPError
from werkzeug import urls

from odoo import _, http
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class PaypalController(http.Controller):
    _return_url = '/payment/paypal/dpn/'
    _notify_url = '/payment/paypal/ipn/'

    @http.route(
        _return_url, type='http', auth='public', methods=['GET', 'POST'], csrf=False,
        save_session=False
    )
    def paypal_dpn(self, **data):
        """ Route used by the PDT notification.

        The "PDT notification" is actually POST data sent along the user redirection.
        The route also allows the GET method in case the user clicks on "go back to merchant site".

        The route is flagged with `save_session=False` to prevent Odoo from assigning a new session
        to the user if they are redirected to this route with a POST request. Indeed, as the session
        cookie is created without a `SameSite` attribute, some browsers that don't implement the
        recommended default `SameSite=Lax` behavior will not include the cookie in the redirection
        request from the payment provider to Odoo. As the redirection to the '/payment/status' page
        will satisfy any specification of the `SameSite` attribute, the session of the user will be
        retrieved and with it the transaction which will be immediately post-processed.
        """
        _logger.info("beginning DPN with post data:\n%s", pprint.pformat(data))
        if not data:  # The customer has cancelled the payment
            pass  # Redirect them to the status page to browse the draft transaction
        else:
            try:
                notification_data = self._validate_pdt_data_authenticity(**data)
            except ValidationError:
                _logger.exception("could not verify the origin of the PDT; discarding it")
            else:
                request.env['payment.transaction'].sudo()._handle_feedback_data(
                    'paypal', notification_data
                )

        return request.redirect('/payment/status')

    def _validate_pdt_data_authenticity(self, **data):
        """ Validate the authenticity of PDT data and return the retrieved notification data.

        The validation is done in four steps:

        1. Make a POST request to Paypal with the `tx`, the GET param received with the PDT data,
           and the two other required params `cmd` and `at`.
        2. PayPal sends back a response text starting with either 'SUCCESS' or 'FAIL'. If the
           validation was a success, the notification data are appended to the response text as a
           string formatted as follows: 'SUCCESS\nparam1=value1\nparam2=value2\n...'
        3. Extract the notification data and process these instead of the PDT data.
        4. Return an empty HTTP 200 response (done at the end of the route controller).

        See https://developer.paypal.com/docs/api-basics/notifications/payment-data-transfer/.

        :param dict data: The data whose authenticity must be checked.
        :return: The retrieved notification data
        :raise ValidationError: if the authenticity could not be verified
        """
        if 'tx' not in data:  # We did not receive PDT data but directly notification data
            # When PDT is not enabled, PayPal sends directly the notification data instead. We can't
            # verify them but we can process them as is.
            notification_data = data
        else:
            acquirer_sudo = request.env['payment.transaction'].sudo()._get_tx_from_feedback_data(
                'paypal', data
            ).acquirer_id
            if not acquirer_sudo.paypal_pdt_token:  # We received PDT data but can't verify them
                raise ValidationError("PayPal: The PDT token is not set; cannot verify data origin")
            else:  # The PayPal account is configured to receive PDT data, and the PDT token is set
                # Request a PDT data authenticity check and the notification data to PayPal
                url = acquirer_sudo._paypal_get_api_url()
                payload = {
                    'cmd': '_notify-synch',
                    'tx': data['tx'],
                    'at': acquirer_sudo.paypal_pdt_token,
                }
                try:
                    response = requests.post(url, data=payload, timeout=10)
                    response.raise_for_status()
                except (ConnectionError, HTTPError):
                    raise ValidationError("PayPal: Encountered an error when verifying PDT origin")
                else:
                    notification_data = self._parse_pdt_validation_response(response.text)
                    if notification_data is None:
                        raise ValidationError("PayPal: The PDT origin was not verified by PayPal")

        return notification_data

    @staticmethod
    def _parse_pdt_validation_response(response_content):
        """ Parse the validation response and return the parsed notification data.

        :param str response_content: The PDT validation request response
        :return: The parsed notification data
        :rtype: dict
        """
        response_items = response_content.splitlines()
        if response_items[0] == 'SUCCESS':
            notification_data = {}
            for notification_data_param in response_items[1:]:
                key, raw_value = notification_data_param.split('=', 1)
                notification_data[key] = urls.url_unquote_plus(raw_value)
            return notification_data
        return None

    @http.route(_notify_url, type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def paypal_ipn(self, **data):
        """ Route used by the IPN. """
        _logger.info("beginning IPN with post data:\n%s", pprint.pformat(data))
        try:
            self._validate_ipn_data_authenticity(**data)
            request.env['payment.transaction'].sudo()._handle_feedback_data('paypal', data)
        except ValidationError:  # Acknowledge the notification to avoid getting spammed
            _logger.exception("unable to handle the IPN data; skipping to acknowledge the notif")
        return ''

    def _validate_ipn_data_authenticity(self, **data):
        """ Validate the authenticity of IPN data.

        The verification is done in three steps:

        1. POST the complete, unaltered, message back to Paypal (preceded by
           `cmd=_notify-validate`), in the same encoding.
        2. PayPal sends back either 'VERIFIED' or 'INVALID'.
        3. Return an empty HTTP 200 response (done at the end of the route method).

        See https://developer.paypal.com/docs/api-basics/notifications/ipn/IPNIntro/.

        :param dict data: The data whose authenticity must be checked.
        :return: None
        :raise ValidationError: if the authenticity could not be verified
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
