# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hmac
import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.http import request

from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_razorpay.const import HANDLED_WEBHOOK_EVENTS


_logger = get_payment_logger(__name__)


class RazorpayController(http.Controller):
    _return_url = '/payment/razorpay/return'
    _webhook_url = '/payment/razorpay/webhook'

    @http.route(
        _return_url,
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def razorpay_return_from_checkout(self, reference, **data):
        """Process the payment data sent by Razorpay after redirection from checkout.

        The route is configured with save_session=False to prevent Odoo from creating a new session
        when the user is redirected here via a POST request. Indeed, as the session cookie is
        created without a `SameSite` attribute, some browsers that don't implement the recommended
        default `SameSite=Lax` behavior will not include the cookie in the redirection request from
        the payment provider to Odoo. However, the redirection to the /payment/status page will
        satisfy any specification of the `SameSite` attribute, the session of the user will be
        retrieved and with it the transaction which will be immediately post-processed.

        :param str reference: The transaction reference embedded in the return URL.
        :param dict data: The payment data.
        """
        _logger.info("Handling redirection from Razorpay with data:\n%s", pprint.pformat(data))
        if all(f'razorpay_{key}' in data for key in ('order_id', 'payment_id', 'signature')):
            # Check the integrity of the notification.
            tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference(
                'razorpay', {'description': reference}
            )  # Use the same key as for webhook notifications' data.
            self._verify_signature(data, data.get('razorpay_signature'), tx_sudo)
            tx_sudo._process('razorpay', data)
        else:  # The customer cancelled the payment or the payment failed.
            pass  # Don't try to process this case because the payment id was not provided.

        # Redirect the user to the status page.
        return request.redirect('/payment/status')

    @http.route(_webhook_url, type='http', methods=['POST'], auth='public', csrf=False)
    def razorpay_webhook(self):
        """Process the payment data sent by Razorpay to the webhook.

        :return: An empty string to acknowledge the notification.
        :rtype: str
        """
        data = request.get_json_data()
        _logger.info("Notification received from Razorpay with data:\n%s", pprint.pformat(data))

        event_type = data['event']
        if event_type in HANDLED_WEBHOOK_EVENTS:
            entity_type = 'payment' if 'payment' in event_type else 'refund'
            entity_data = data['payload'].get(entity_type, {}).get('entity', {})
            entity_data.update(entity_type=entity_type)
            received_signature = request.httprequest.headers.get('X-Razorpay-Signature')
            tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference(
                'razorpay', entity_data
            )
            if tx_sudo:
                self._verify_signature(
                    request.httprequest.data, received_signature, tx_sudo, is_redirect=False
                )
                tx_sudo._process('razorpay', entity_data)

        return request.make_json_response('')

    @staticmethod
    def _verify_signature(
        payment_data, received_signature, tx_sudo, is_redirect=True
    ):
        """Check that the received signature matches the expected one.

        :param dict|bytes payment_data: The payment data.
        :param str received_signature: The signature to compare with the expected signature.
        :param payment.transaction tx_sudo: The sudoed transaction referenced by the payment data
        :param bool is_redirect: Whether the payment data should be treated as redirect data or as
                                 coming from a webhook notification.
        :return: None
        :raise Forbidden: If the signatures don't match.
        """
        # Check for the received signature.
        if not received_signature:
            _logger.warning("Received payment data with missing signature.")
            raise Forbidden()

        # Compare the received signature with the expected signature.
        expected_signature = tx_sudo.provider_id._razorpay_calculate_signature(
            payment_data, is_redirect=is_redirect
        )
        if (
            expected_signature is None
            or not hmac.compare_digest(received_signature, expected_signature)
        ):
            _logger.warning("Received payment data with invalid signature.")
            raise Forbidden()
