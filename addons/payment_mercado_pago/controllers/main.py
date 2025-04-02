# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

import requests

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)


class MercadoPagoController(http.Controller):
    _return_url = '/payment/mercado_pago/return'
    _webhook_url = '/payment/mercado_pago/webhook'

    @http.route(_return_url, type='http', methods=['GET'], auth='public')
    def mercado_pago_return_from_checkout(self, **data): #will probably not need it
        """ Process the notification data sent by Mercado Pago after redirection from checkout.

        :param dict data: The notification data.
        """
        # Handle the notification data.
        _logger.info("Handling redirection from Mercado Pago with data:\n%s", pprint.pformat(data))
        if data.get('payment_id') != 'null':
            self._verify_and_handle_notification_data(data)
        else:  # The customer cancelled the payment by clicking on the return button.
            pass  # Don't try to process this case because the payment id was not provided.

        # Redirect the user to the status page.
        return request.redirect('/payment/status')

    @http.route(
        f'{_webhook_url}/<reference>', type='http', auth='public', methods=['POST'], csrf=False
    )
    def mercado_pago_webhook(self, reference, **_kwargs):
        """ Process the notification data sent by Mercado Pago to the webhook.

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
            # Handle the notification data.
            try:
                self._verify_and_handle_notification_data(
                    {'external_reference': reference, 'payment_id': data.get('data', {}).get('id')}
                )  # Use 'external_reference' as the reference key like in the redirect data.
            except ValidationError:  # Acknowledge the notification to avoid getting spammed.
                _logger.exception("Unable to handle the notification data; skipping to acknowledge")
        return ''  # Acknowledge the notification.

    @staticmethod
    def _verify_and_handle_notification_data(data):
        """ Verify and process the notification data sent by Mercado Pago.

        :param dict data: The notification data.
        :return: None
        """
        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
            'mercado_pago', data
        )
        # Verify the notification data.
        verified_data = tx_sudo.provider_id._mercado_pago_make_request(
            f'/v1/payments/{data.get("payment_id")}', method='GET'
        )
        tx_sudo._handle_notification_data('mercado_pago', verified_data)

    @http.route('/mercado_pago/methods', type='http')
    def mercado_pago_methods(self):

        headers = {'Content-Type':'application/json','Authorization': f'Bearer TEST-8088927131040927-082108-480b8790088df9ec287c80b5982f31ad-1074382083'}

        x = requests.get('https://api.mercadopago.com/v1/payment_methods', params=None, headers=headers, timeout=10)
        print(x)


    @http.route('/payment/mercado_pago/payments', type='jsonrpc', auth='public')
    def make_mp_transacton(self, payment_method_id, payer, provider_id, reference, transaction_amount, token=None, issuer_id=None):
        provider_sudo = request.env['payment.provider'].sudo().browse(provider_id)
        tx_sudo = request.env['payment.transaction'].sudo().search([('reference', '=', reference)])

        payload = {
            "transaction_amount": transaction_amount,
            "description": reference,
            "installments": 1,
            "payment_method_id": payment_method_id,
            "payer": payer,
            **self.card_payment_values(token, issuer_id)
        }

        response_content = provider_sudo._mercado_pago_make_request(endpoint='/v1/payments', payload=payload, method='POST', idempotency_key=payment_utils.generate_idempotency_key(tx_sudo))

        tx_sudo._handle_notification_data(
            'mercado_pago', dict(response_content, merchantReference=reference, **self.card_payment_values(token, issuer_id)),  # Match the transaction
        )

    def card_payment_values(self, token, issuer_id):
        if token and issuer_id:
            return {"token": token, "issuer_id": issuer_id}
        return {}
