# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

import requests

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request


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
            request.env['payment.transaction'].sudo()._handle_notification_data(
                'mercado_pago', data
            )
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
                payment_id = data.get('data', {}).get('id')
                request.env['payment.transaction'].sudo()._handle_notification_data(
                    'mercado_pago', {'external_reference': reference, 'payment_id': payment_id}
                )  # Use 'external_reference' as the reference key like in the redirect data.
            except ValidationError:  # Acknowledge the notification to avoid getting spammed.
                _logger.exception("Unable to handle the notification data; skipping to acknowledge")
        return ''  # Acknowledge the notification.

    @http.route('/mercado_pago/methods', type='http')
    def mercado_pago_methods(self):

        headers = {'Content-Type':'application/json','Authorization': f'Bearer TEST-8088927131040927-082108-480b8790088df9ec287c80b5982f31ad-1074382083'}

        x = requests.get('https://api.mercadopago.com/v1/payment_methods', params=None, headers=headers, timeout=10)
        print(x)

    @http.route('/mercado_pago/create_preference', type='jsonrpc', auth='public')
    def mercado_pago_preference(self, partner_id, amount, currency, payment_method, provider_id):

        #get the list of mercado pago payment methods

        provider_sudo = request.env['payment.provider'].sudo().browse(provider_id)
        partner_sudo = partner_id and request.env['res.partner'].sudo().browse(partner_id).exists()
        #search trhotugh payment methods to find the one with this id

        y = provider_sudo.payment_method_ids.filtered(lambda l: l.id != payment_method)
        excluded_payment_methods = []
        # for z in y:
        #     excluded_payment_methods.append({'id': z.code})
        excluded_payment_methods.append({"id": "credit_card"})
        x = {
            'items': [{
                'title':'Test',
                'quantity': 1,
                'currency_id': currency,
                'unit_price': amount,
                'id': "3",
            }],
            'payment_methods': {
                'excluded_payment_types': [
        { "id": "ticket" }
    ],

            },
        }

        headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {provider_sudo.mercado_pago_access_token}' }

        f =  requests.post('https://api.mercadopago.com/checkout/preferences', json=x,
                         headers=headers, timeout=10).json()

        return f.get('id')