# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pprint

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_iyzico import const


_logger = get_payment_logger(__name__)


class IyzicoController(http.Controller):

    @http.route(
        const.PAYMENT_RETURN_ROUTE, type='http', auth='public', methods=['POST'], csrf=False,
        save_session=False
    )
    def iyzico_return_from_payment(self, tx_ref='', **data):
        """Process the payment data sent by Iyzico after redirection from checkout.

        The route is flagged with `save_session=False` to prevent Odoo from assigning a new session
        to the user if they are redirected to this route with a POST request. Indeed, as the session
        cookie is created without a `SameSite` attribute, some browsers that don't implement the
        recommended default `SameSite=Lax` behavior will not include the cookie in the redirection
        request from the payment provider to Odoo. As the redirection to the '/payment/status' page
        will satisfy any specification of the `SameSite` attribute, the session of the user will be
        retrieved and with it the transaction which will be immediately post-processed.

        :param str tx_ref: The reference of the related transaction.
        :param dict data: The payment data.
        """
        _logger.info("Handling redirection from Iyzico with data:\n%s", pprint.pformat(data))
        if token := data.get('token'):
            self._verify_and_process(tx_ref, token)
        else:
            _logger.warning("Received payment data with missing token.")

        return request.redirect('/payment/status')

    @http.route(const.WEBHOOK_ROUTE, type='http', auth='public', methods=['POST'], csrf=False)
    def iyzico_webhook(self):
        """Process the payment data sent by Iyzico to the webhook.

        See https://docs.iyzico.com/en/advanced/webhook.

        :return: An empty response to acknowledge the notification.
        :rtype: odoo.http.Response
        """
        data = request.get_json_data()
        _logger.info("Notification received from Iyzico with data:\n%s", pprint.pformat(data))

        if token := data.get('token'):
            self._verify_and_process(data['paymentConversationId'], token)
        else:
            _logger.warning("Received webhook data with missing token.")

        return request.make_json_response('')  # Acknowledge the notification.

    @staticmethod
    def _verify_and_process(tx_ref, token):
        """Verify and process the payment data sent by Iyzico.

        :param str tx_ref: The reference of the transaction.
        :param str token: The iyzico transaction token to fetch transaction details.
        :return: None
        """
        tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference(
            'iyzico', {'reference': tx_ref}
        )
        if not tx_sudo:
            return
        try:
            verified_payment_data = tx_sudo._send_api_request(
                'POST',
                'payment/iyzipos/checkoutform/auth/ecom/detail',
                json={
                    'conversationId': tx_sudo.reference,
                    'locale': request.env.lang == 'tr_TR' and 'tr' or 'en',
                    'token': token,
                },
            )
            tx_sudo._process('iyzico', verified_payment_data)
        except ValidationError:
            _logger.error("Unable to process the payment data.")
