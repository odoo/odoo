# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

import requests
from requests.exceptions import HTTPError, RequestException

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

DPOPAY_DEFAULT_TIMEOUT = 35


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    dpopay_client_id = fields.Char(string='DPO Pay Client ID', help="The Client ID provided by DPO Pay for authenticating requests.")
    dpopay_client_secret = fields.Char(string='DPO Pay Client Secret', help="The Client Secret provided by DPO Pay for secure access. Keep it confidential.")
    dpopay_mid = fields.Char(string='DPO Pay Merchant ID', help="Enter the Merchant ID assigned by DPO Pay (e.g., 123456789012).")
    dpopay_tid = fields.Char(string='DPO Pay Terminal ID', help="Enter the unique Terminal ID (TID) of your DPO Pay POS terminal (e.g., XXXXXXXX).")
    dpopay_payment_mode = fields.Selection(
        selection=[('card', 'Card'), ('momo', 'Mobile Money')],
        default='card',
        help="Choose allowed payment mode:\nCard - regular card payments\nMobile Money - M-Pesa / Airtel Mobile Money",
    )
    dpopay_chain_id = fields.Char(string='DPO Pay Chain-ID', help="Enter the Chain-ID header value(e.g., DPO-DTM-Testing)")
    dpopay_test_mode = fields.Boolean(string='Enable Test Mode', help="Check this to use DPO Pay's sandbox environment for testing purposes.")
    dpopay_bearer_token = fields.Char(default='Token', help="Bearer token used for authenticating requests. Automatically refreshed when expired.")

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('dpopay', 'DPO Pay')]

    def _is_write_forbidden(self, fields):
        # Allow the modification of these fields even if a pos_session is open
        whitelisted_fields = {'dpopay_bearer_token', 'dpopay_payment_mode'}
        return super()._is_write_forbidden(fields - whitelisted_fields)

    def _get_transaction_type(self):
        if self.dpopay_payment_mode == 'momo':
            return 'pushPaymentDpoMomoSale'
        return 'pushPaymentSale'

    def send_dpopay_request(self, data, endpoint):
        self.ensure_one()
        if endpoint == 'start-transaction':
            data['transactionType'] = self._get_transaction_type()
        return self._execute_dpopay_api_request(data, endpoint)

    def _get_dpopay_base_url(self, is_token=False):
        self.ensure_one()
        host = (self.dpopay_test_mode and 'api-dev.network.global') or 'api.network.global'

        if is_token:
            return f'https://{host}/v1'
        return f'https://{host}/ngenius-webapi/payments/push/v1/tid:{self.dpopay_tid}/mid:{self.dpopay_mid}'

    def _dpopay_headers(self, token_expired=False):
        self.ensure_one()
        token = self._generate_dpopay_token() if token_expired else self.dpopay_bearer_token
        return {
            'Authorization': f'Bearer {token}',
            'Chain-ID': self.dpopay_chain_id,
        }

    def _generate_dpopay_token(self):
        self.ensure_one()
        auth = requests.auth.HTTPBasicAuth(self.dpopay_client_id, self.dpopay_client_secret)
        url = f'{self._get_dpopay_base_url(is_token=True)}/tokenkc/generate'

        _logger.info('Sending request to %s to generate new token', url)
        response = requests.get(url, auth=auth, timeout=DPOPAY_DEFAULT_TIMEOUT)
        response_json = response.json()
        response.raise_for_status()
        access_token = response_json.get('access_token')

        if not access_token:
            raise UserError(_('Unable to retrieve DPO Pay bearer token: check Client ID and Client Secret.'))

        # The token is short-lived and refreshed automatically to keep the payment flow working.
        # sudo() is used because POS users only have read access to this model.
        self.sudo().write({'dpopay_bearer_token': access_token})
        return access_token

    def _execute_dpopay_api_request(self, payload, endpoint):
        self.ensure_one()
        if endpoint not in ('start-transaction', 'get-result', 'get-status', 'cancel-transaction'):
            raise UserError(_('Invalid endpoint'))

        mode = 'Test' if self.dpopay_test_mode else 'Production'
        url = f'{self._get_dpopay_base_url()}/{endpoint}'
        try:
            def _send_request(token_expired=False):
                headers = self._dpopay_headers(token_expired)
                _logger.info('Sending request to %s | Mode: %s | Headers: %s', url, mode, list(headers.keys()))
                response = requests.post(url, json=payload, headers=headers, timeout=DPOPAY_DEFAULT_TIMEOUT)
                response_json = response.json()
                return response, response_json

            response, response_json = _send_request()
            errorCode = response_json.get('error_code') or response_json.get('resultCode')
            # Refresh Token and Retry the request if the token is expired (999912) or invalid (999913)
            if response.status_code == 401 and errorCode in ('999912', '999913'):
                _logger.info('Token expired or invalid — regenerating token...')
                response, response_json = _send_request(token_expired=True)

            response.raise_for_status()
            return response_json

        except HTTPError as error:
            _logger.warning('HTTPError: %s', error)
            error_json = error.response.json()
            error_code = str(error_json.get('error_code') or error_json.get('errorCode') or error_json.get('resultCode'))
            error_message = error_json.get('errorMessage') or error_json.get('error_description') or error_json.get('resultDescription') or str(error_json)

            if error_code == "403":
                error_message = _("Please ensure the device is online and confirm that the Merchant ID (MID) and Terminal ID (TID) are correct. %s", error_message)

            if error_code == "999911":
                error_message = _("Invalid Chain ID. Please verify the configuration. %s", error_message)

            return {'errorMessage': error_message}

        except RequestException as error:
            _logger.warning('%s: %s', error.__class__.__name__, error)
            return {'errorMessage': str(error)}
