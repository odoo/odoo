# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

import requests
from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class PaypalController(http.Controller):
    _return_url = '/payment/paypal/return/'
    _webhook_url = '/payment/paypal/webhook/'

    @http.route(
        _return_url, type='http', auth='public', methods=['GET', 'POST'], csrf=False,
        save_session=False
    )
    def paypal_return_from_checkout(self, **data):
        """ Process the notification data (PDT) sent by PayPal after redirection from checkout.

        The "Payment Data Transfer" notification is actually the notification data sent along the
        redirect. See https://developer.paypal.com/api/nvp-soap/payment-data-transfer/.

        The route accept both GET and POST requests because PayPal seems to switch between the two
        depending on whether PDT is enabled, the customer pays anonymously (without logging in on
        PayPal), the customer clicks on "go back to merchant site" and cancels the payment, etc.

        The route is flagged with `save_session=False` to prevent Odoo from assigning a new session
        to the user if they are redirected to this route with a POST request. Indeed, as the session
        cookie is created without a `SameSite` attribute, some browsers that don't implement the
        recommended default `SameSite=Lax` behavior will not include the cookie in the redirection
        request from the payment provider to Odoo. As the redirection to the '/payment/status' page
        will satisfy any specification of the `SameSite` attribute, the session of the user will be
        retrieved and with it the transaction which will be immediately post-processed.
        """
        _logger.info("handling redirection from PayPal with data:\n%s", pprint.pformat(data))

        # Check the origin of the notification
        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_feedback_data(
            'paypal', data
        )
        self._verify_notification_origin(data, tx_sudo)

        # Handle the notification data
        if data:
            request.env['payment.transaction'].sudo()._handle_feedback_data('paypal', data)
        else:  # The customer has cancelled the payment
            pass  # Redirect the customer to the status page
        return request.redirect('/payment/status')

    @http.route(_webhook_url, type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def paypal_webhook(self, **data):
        """ Process the notification data (IPN) sent by PayPal to the webhook.

        The "Instant Payment Notification" is a classical webhook notification.
        See https://developer.paypal.com/api/nvp-soap/ipn/.

        :param dict data: The notification data
        :return: An empty string to acknowledge the notification
        :rtype: str
        """
        _logger.info("notification received from PayPal with data:\n%s", pprint.pformat(data))
        try:
            # Check the origin and integrity of the notification
            tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_feedback_data(
                'paypal', data
            )
            self._verify_notification_origin(data, tx_sudo)

            # Handle the notification data
            request.env['payment.transaction'].sudo()._handle_feedback_data('paypal', data)
        except ValidationError:  # Acknowledge the notification to avoid getting spammed
            _logger.exception("unable to handle the notification data; skipping to acknowledge")
        return ''

    @staticmethod
    def _verify_notification_origin(notification_data, tx_sudo):
        """ Check that the notification was sent by Alipay.

        The verification is done in three steps:
          - 1: POST the complete message back to Paypal with the additional param
               `cmd=_notify-validate`, in the same encoding.
          - 2: PayPal sends back either 'VERIFIED' or 'INVALID'.
          - 3: Return an empty HTTP 200 response if the notification origin is verified by PayPal,
               raise an HTTP 403 otherwise.
        See https://developer.paypal.com/api/nvp-soap/ipn/IPNImplementation/

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

        :param dict notification_data: The notification data
        :param recordset tx_sudo: The sudoed transaction referenced in the notification data, as a
                                        `payment.transaction` record
        :return: None
        :raise: :class:`werkzeug.exceptions.Forbidden` if the notification origin can't be verified
        """

        # Request PayPal for an authenticity check
        url = tx_sudo.acquirer_id._paypal_get_api_url()
        payload = dict(notification_data, cmd='_notify-validate')
        try:
            response = requests.post(url, payload, timeout=60)
            response.raise_for_status()
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as error:
            _logger.exception(
                "could not verify notification origin at %(url)s with data: %(data)s:\n%(error)s",
                {
                    'url': url,
                    'data': pprint.pformat(notification_data),
                    'error': pprint.pformat(error.response.text),
                },
            )
            raise Forbidden()
        else:
            response_content = response.text
            if response_content != 'VERIFIED':
                _logger.error(
                    "PayPal did not confirm the origin of the notification with data:\n%s",
                    pprint.pformat(notification_data),
                )
                raise Forbidden()
