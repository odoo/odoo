# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pprint

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger

from odoo.addons.payment_mercado_pago import const


_logger = get_payment_logger(__name__)


class MercadoPagoPaymentController(http.Controller):

    @http.route('/payment/mercado_pago/payments', type='jsonrpc', auth='public')
    def mercado_pago_payment(
        self, reference, transaction_amount, token, installments, payment_method_brand, issuer_id
    ):
        """Make a payment request and process the payment data.

        :param str reference: The reference of the transaction
        :param int transaction_amount: The amount of the transaction in minor units of the currency
        :param int token: The transaction token of card received from Mercado Pago.
        :param int installments:
        :param int payment_method_brand: The payment method of the transaction.
        :param int issuer_id: The issuer id of the card received from Mercado Pago.
        :rtype: None
        """
        tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference(
            'mercado_pago', {'external_reference': reference}
        )
        payload = tx_sudo._mercado_pago_prepare_payment_request_payload()
        payload.update({
            'transaction_amount': float(transaction_amount),
            'token': token,
            'installments': installments,
            'payment_method_id': payment_method_brand,
            'issuer_id': issuer_id,
        })
        response_content = tx_sudo._send_api_request(
            'POST',
            endpoint='/v1/payments',
            json=payload,
            idempotency_key=payment_utils.generate_idempotency_key(tx_sudo, scope='direct_payment'),
        )
        tx_sudo._process(
            'mercado_pago', dict(response_content, merchantReference=reference, token=token)
        )

    @http.route(const.PAYMENT_RETURN_ROUTE, type='http', methods=['GET'], auth='public')
    def mercado_pago_return_from_checkout(self, **data):
        """Process the payment data sent by Mercado Pago after redirection from checkout.

        :param dict data: The payment data.
        """
        _logger.info("Handling redirection from Mercado Pago with data:\n%s", pprint.pformat(data))
        if data.get('payment_id') != 'null':
            self._verify_and_process(data)
        else:  # The customer cancelled the payment by clicking on the return button.
            pass  # Don't try to process this case because the payment id was not provided.

        # Redirect the user to the status page.
        return request.redirect('/payment/status')

    @http.route(
        f'{const.WEBHOOK_ROUTE}/<reference>', type='http', auth='public', methods=['POST'],
        csrf=False
    )
    def mercado_pago_webhook(self, reference, **_kwargs):
        """ Process the payment data sent by Mercado Pago to the webhook.

        :param str reference: The transaction reference embedded in the webhook URL.
        :param dict _kwargs: The extra query parameters.
        :return: An empty string to acknowledge the notification.
        :rtype: str
        """
        data = request.get_json_data()
        _logger.info("Notification received from Mercado Pago with data:\n%s", pprint.pformat(data))

        # Mercado Pago sends two types of asynchronous notifications: webhook notifications and
        # IPNs which are very similar to webhook notifications but are sent later and contain less
        # information. Therefore, we filter the notifications we receive based on the 'action'
        # (type of event) key as it is not populated for IPNs, and we don't want to process the
        # other types of events.
        if data.get('action') in ('payment.created', 'payment.updated'):
            self._verify_and_process(
                {'external_reference': reference, 'payment_id': data.get('data', {}).get('id')}
            )  # Use 'external_reference' as the reference key like in the redirect data.
        return ''  # Acknowledge the notification.

    @staticmethod
    def _verify_and_process(data):
        """Verify and process the payment data sent by Mercado Pago.

        :param dict data: The payment data.
        :return: None
        """
        tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference(
            'mercado_pago', data
        )
        if not tx_sudo:
            return

        try:
            verified_data = tx_sudo._send_api_request(
                'GET', f'/v1/payments/{data.get("payment_id")}'
            )
        except ValidationError:
            _logger.error("Unable to verify the payment data")
        else:
            tx_sudo._process('mercado_pago', verified_data)
