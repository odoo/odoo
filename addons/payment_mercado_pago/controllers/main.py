# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pprint

from odoo import fields, http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger


_logger = get_payment_logger(__name__)


class MercadoPagoController(http.Controller):
    _return_url = '/payment/mercado_pago/return'
    _webhook_url = '/payment/mercado_pago/webhook'

    @http.route('/payment/mercado_pago/payments', type='jsonrpc', auth='public')
    def mercado_pago_payment(
        self, provider_id, reference, transaction_amount, payer, payment_method_id, token=None,
        issuer_id=None
    ):
        """Make a payment request and process the payment data.

        :param int provider_id: The provider handling the transaction, as a `payment.provider` id
        :param str reference: The reference of the transaction
        :param int transaction_amount: The amount of the transaction in minor units of the currency
        :param int payment_method_id: The payment method of the transaction.
        :param int payer: The payer making the transaction.
        :param dict payment_method_id: The details of the payment method used for the transaction.
        :param int token: The transaction token of card received from Mercado Pago.
        :param int issuer_id: The issuer id of the card received from Mercado Pago.
        :return: The JSON-formatted content of the response
        :rtype: dict
        """

        provider_sudo = request.env['payment.provider'].sudo().browse(provider_id)
        tx_sudo = request.env['payment.transaction'].sudo().search([('reference', '=', reference)])

        data = tx_sudo._mercado_pago_prepare_payment_request_payload()
        data.update({
            'transaction_amount': float(transaction_amount),
            'payment_method_id': payment_method_id,
            'token': token,
            'issuer_id': issuer_id,
        })

        if provider_sudo.mercado_pago_access_token:
            if provider_sudo.mercado_pago_access_token_expiry < fields.Datetime.now():
                provider_sudo._mercado_pago_refresh_token()

        response_content = tx_sudo._send_api_request(
            'POST',
            endpoint='/v1/payments',
            json=data,
            idempotency_key=payment_utils.generate_idempotency_key(
                tx_sudo, scope='payment_request_token'
            )
        )
        tx_sudo._process(
            'mercado_pago', dict(response_content, merchantReference=reference, token=token)
        )

    @http.route(_return_url, type='http', methods=['GET'], auth='public')
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
        f'{_webhook_url}/<reference>', type='http', auth='public', methods=['POST'], csrf=False
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
