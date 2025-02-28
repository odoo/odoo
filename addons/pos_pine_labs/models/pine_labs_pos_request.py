import json
import logging
import requests

from odoo import _

REQUEST_TIMEOUT = 10
PINE_LABS_AUTO_CANCEL_DURATION_MIN = 10

_logger = logging.getLogger(__name__)

class PineLabsPosRequest:

    def __init__(self, payment_method):
        self.pm = payment_method

    def _get_pine_labs_url(self):
        if self.pm.env['ir.config_parameter'].sudo().get_param('pos_pine_labs.pine_labs_proxy_endpoint', ''):
            return self.pm.env['ir.config_parameter'].sudo().get_param('pos_pine_labs.pine_labs_proxy_endpoint')
        _logger.warning('To use Pine Labs outside India and Malesia, the Pine Labs Proxy Endpoint must be set because the Pine Labs URL is only accessible in India and Malesia.')
        if self.pm.pine_labs_test_mode:
            return 'https://www.plutuscloudserviceuat.in:8201/API/CloudBasedIntegration/V1/'
        return 'https://www.plutuscloudservice.in:8201/API/CloudBasedIntegration/V1/'

    def call_pine_labs(self, endpoint, payload):
        """
        Make a request to Pine Labs POS API.

        :param str endpoint: The endpoint to be reached by the request.
        :param dict payload: The payload of the request.
        :return The JSON-formatted content of the response.
        :rtype: dict
        """
        payload |= self.pine_labs_request_body(endpoint == 'UploadBilledTransaction')
        pine_labs_url = self._get_pine_labs_url()
        url = f'{pine_labs_url}{endpoint}'
        try:
            response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            res_json = response.json()
        except requests.exceptions.ConnectionError as error:
            _logger.warning('Connection Error: %r with the given URL %r', error, url)
            return {'errorMessage': error}
        except requests.exceptions.HTTPError as error:
            _logger.warning('HTTPError: %r', error)
            return {'errorMessage': error}
        except requests.exceptions.Timeout as error:
            _logger.warning('Timeout: %r', error)
            return {'errorMessage': error}
        except json.decoder.JSONDecodeError as error:
            _logger.warning('JSONDecodeError: %r', error)
            return {'errorMessage': error}
        return res_json

    def pine_labs_request_body(self, payment_mode=False):
        """
        param (bool, optional) payment_mode: If True, includes allowed payment mode and auto-cancel duration in
                                                the request body for `UploadBilledTransaction` endpoint.
                                                Defaults to False.

        rtype: dict
        """
        request_parameters = {
            'MerchantID': self.pm.pine_labs_merchant,
            'StoreID': self.pm.pine_labs_store,
            'ClientID': self.pm.pine_labs_client,
            'SecurityToken': self.pm.pine_labs_security_token
        }
        if payment_mode:
            # Added AutoCancelDurationInMinutes set to 10 minutes for automatically cancelling transactions on the Pine Labs side in case of lost transaction request data from the PoS system.
            pine_labs_auto_cancel_duration = self.pm.env['ir.config_parameter'].sudo().get_param('pos_pine_labs.payment_auto_cancel_duration', PINE_LABS_AUTO_CANCEL_DURATION_MIN)
            request_parameters.update({
                'AllowedPaymentMode': self._get_allowed_payment_mode(),
                'AutoCancelDurationInMinutes': pine_labs_auto_cancel_duration
            })
        return request_parameters

    def _get_allowed_payment_mode(self):
        allowed_payment_modes_mapping = {
            'all': 0,
            'card': 1,
            'upi': 10,
        }
        return allowed_payment_modes_mapping.get(self.pm.pine_labs_allowed_payment_mode)
