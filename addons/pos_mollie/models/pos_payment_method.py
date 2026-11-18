# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import requests

from werkzeug import urls

from odoo import fields, models, _
from odoo.release import version

_logger = logging.getLogger(__name__)


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    mollie_api_key = fields.Char(string="Mollie API key")
    mollie_terminal_id = fields.Char(string="Mollie Terminal ID")

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('mollie', 'Mollie')]

    def mollie_payment_request(self, data):
        """ Creates payment records on mollie. This method will be called from POS.

        :param dict data: payment details received from the POS.
        :return Details of mollie payment record received from the mollie.
        :rtype: dict
        """
        self.ensure_one()
        payment_payload = self._prepare_payment_payload(data)
        return self._mollie_api_call('/payments', data=payment_payload, method='POST')

    def _prepare_payment_payload(self, data):
        """ Prepares the payload for the mollie api call for payment creation.

        Learn more at: https://docs.mollie.com/reference/v2/payments-api/create-payment

        :param dict data: payment details.
        :return data in the format needed for the mollie payments.
        :rtype: dict
        """
        base_url = self.get_base_url()
        order_type = data.get('order_type', 'pos')
        webhook_url = urls.url_join(base_url, f"/pos_mollie/webhook/{order_type}/{self.id}")
        return {
            'amount': {
                'currency': data['currency'],
                'value': f"{data['amount']:.2f}"
            },
            'description': data['description'],
            'webhookUrl': webhook_url,
            'method': 'pointofsale',
            'terminalId': self.mollie_terminal_id,
            'metadata': {
                'pos_reference': data['pos_reference'],
                'session_id': data['session_id'],
                'order_type': order_type
            }
        }

    def _get_mollie_payment_status(self, transaction_id):
        """ Fetch status of the mollie payment using transaction ID.

        :param str transaction_id: ID of payment record of mollie.
        :return details of mollie payment record.
        :rtype: dict
        """
        return self._mollie_api_call(f'/payments/{transaction_id}', method='GET')

    def _mollie_process_webhook(self, webhook_data, payment_type):
        """ This method handles details received with mollie. This method called
        when payment status changed for mollie payment record.

        More details at: https://docs.mollie.com/overview/webhooks

        :param dict webhook_data: data received from the mollie webhook.
        :param str payment_type: type of order.
        """
        self.ensure_one()
        payment_status = self._get_mollie_payment_status(webhook_data.get('id'))
        if payment_status and payment_status.get('status'):
            mollie_session = self.env['pos.session'].browse(payment_status['metadata']['session_id'])
            status_data = {
                'id': payment_status['id'],
                'status': payment_status.get('status'),
                'config_id': mollie_session.config_id.id
            }
            self.env["bus.bus"].sudo()._sendone(mollie_session._get_bus_channel_name(), "MOLLIE_STATUS_UPDATE", status_data)

    def _mollie_api_call(self, endpoint, data=None, method='POST'):
        """ This is the main method responsible to call mollie API.

        Learn about mollie authentication: https://docs.mollie.com/overview/authentication

        :param str endpoint: endpoint for the API.
        :param dict data: payload for the request.
        :param str method: type of methid GET or POST.
        :return response of the API call.
        :rtype: dict
        """
        self.ensure_one()
        headers = {
            'content-type': 'application/json',
            "Authorization": f'Bearer {self.mollie_api_key}',
            # See https://docs.mollie.com/integration-partners/user-agent-strings
            "User-Agent": f'Odoo/{version} MollieNativeOdooPos/1.0',
        }

        endpoint = f'/v2/{endpoint.strip("/")}'
        url = urls.url_join('https://api.mollie.com/', endpoint)

        _logger.info('Mollie POS Terminal CALL on: %s', url)

        try:
            response = requests.request(method, url, json=data, headers=headers, timeout=60)
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            error_details = response.json()
            _logger.exception("MOLLIE-POS-ERROR \n %s", error_details)
            return {'detail': error_details.get('detail')}
        except requests.exceptions.RequestException as e:
            msg = _('Unable to communicate with Mollie')
            _logger.exception("MOLLIE-POS-ERROR %s %s \n %s", msg, url, e)
            return {'detail': msg}
        return response.json()
