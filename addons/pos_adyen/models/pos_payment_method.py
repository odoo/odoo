# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import logging
import pprint
import random
import requests
import string
from werkzeug.exceptions import Forbidden

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_payment_terminal_selection(self):
        return super(PosPaymentMethod, self)._get_payment_terminal_selection() + [('adyen', 'Adyen')]

    # Adyen
    adyen_api_key = fields.Char(string="Adyen API key", help='Used when connecting to Adyen: https://docs.adyen.com/user-management/how-to-get-the-api-key/#description', copy=False)
    adyen_terminal_identifier = fields.Char(help='[Terminal model]-[Serial number], for example: P400Plus-123456789', copy=False)
    adyen_test_mode = fields.Boolean(help='Run transactions in the test environment.')

    adyen_latest_response = fields.Char(help='Technical field used to buffer the latest asynchronous notification from Adyen.', copy=False, groups='base.group_erp_manager')
    adyen_latest_diagnosis = fields.Char(help='Technical field used to determine if the terminal is still connected.', copy=False, groups='base.group_erp_manager')

    @api.constrains('adyen_terminal_identifier')
    def _check_adyen_terminal_identifier(self):
        for payment_method in self:
            if not payment_method.adyen_terminal_identifier:
                continue
            existing_payment_method = self.search([('id', '!=', payment_method.id),
                                                   ('adyen_terminal_identifier', '=', payment_method.adyen_terminal_identifier)],
                                                  limit=1)
            if existing_payment_method:
                raise ValidationError(_('Terminal %s is already used on payment method %s.')
                                      % (payment_method.adyen_terminal_identifier, existing_payment_method.display_name))

    def _get_adyen_endpoints(self):
        return {
            'terminal_request': 'https://terminal-api-%s.adyen.com/async',
        }

    def _is_write_forbidden(self, fields):
        whitelisted_fields = set(('adyen_latest_response', 'adyen_latest_diagnosis'))
        return super(PosPaymentMethod, self)._is_write_forbidden(fields - whitelisted_fields)

    def _adyen_diagnosis_request_data(self, pos_config_name):
        service_id = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        return {
            "SaleToPOIRequest": {
                "MessageHeader": {
                    "ProtocolVersion": "3.0",
                    "MessageClass": "Service",
                    "MessageCategory": "Diagnosis",
                    "MessageType": "Request",
                    "ServiceID": service_id,
                    "SaleID": pos_config_name,
                    "POIID": self.adyen_terminal_identifier,
                },
                "DiagnosisRequest": {
                    "HostDiagnosisFlag": False
                }
            }
        }

    def get_latest_adyen_status(self, pos_config_name):
        _logger.info('get_latest_adyen_status\n%s', pos_config_name)
        self.ensure_one()

        latest_response = self.sudo().adyen_latest_response
        latest_response = json.loads(latest_response) if latest_response else False

        return {
            'latest_response': latest_response,
        }

    def proxy_adyen_request(self, data, operation=False):
        ''' Necessary because Adyen's endpoints don't have CORS enabled '''
        if data['SaleToPOIRequest']['MessageHeader']['MessageCategory'] == 'Payment': # Clear only if it is a payment request
            self.sudo().adyen_latest_response = ''  # avoid handling old responses multiple times

        if not operation:
            operation = 'terminal_request'

        return self._proxy_adyen_request_direct(data, operation)

    def _proxy_adyen_request_direct(self, data, operation):
        self.ensure_one()
        TIMEOUT = 10

        _logger.info('request to adyen\n%s', pprint.pformat(data))

        environment = 'test' if self.adyen_test_mode else 'live'
        endpoint = self._get_adyen_endpoints()[operation] % environment
        headers = {
            'x-api-key': self.adyen_api_key,
        }
        req = requests.post(endpoint, json=data, headers=headers, timeout=TIMEOUT)

        # Authentication error doesn't return JSON
        if req.status_code == 401:
            return {
                'error': {
                    'status_code': req.status_code,
                    'message': req.text
                }
            }

        if req.text == 'ok':
            return True

        return req.json()
