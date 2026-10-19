import requests
import logging

from odoo import _
REQUEST_TIMEOUT = 10

_logger = logging.getLogger(__name__)

class RazorpayPosRequest:
    def __init__(self, payment_method):
        self.razorpay_test_mode = payment_method.razorpay_test_mode
        self.razorpay_api_key = payment_method.sudo().razorpay_api_key
        self.razorpay_username = payment_method.razorpay_username
        self.razorpay_tid = payment_method.razorpay_tid
        self.razorpay_allowed_payment_modes = payment_method.razorpay_allowed_payment_modes
        self.payment_method = payment_method
        self.session = requests.Session()

    def _razorpay_get_endpoint(self, endpoint):
        if endpoint in ['unified/refund', 'void']:
            if self.razorpay_test_mode:
                return 'https://demo.ezetap.com/api/2.0/payment/'
            return 'https://www.ezetap.com/api/2.0/payment/'
        if self.razorpay_test_mode:
            return 'https://demo.ezetap.com/api/3.0/p2padapter/'
        return 'https://www.ezetap.com/api/3.0/p2padapter/'

    def _call_razorpay(self, endpoint, payload):
        """ Make a request to Razorpay POS API.

        :param str endpoint: The endpoint to be reached by the request.
        :param dict payload: The payload of the request.
        :return The JSON-formatted content of the response.
        :rtype: dict
        """
        url = f'{self._razorpay_get_endpoint(endpoint)}{endpoint}'
        try:
            response = self.session.post(url, json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            res_json = response.json()
        except requests.exceptions.RequestException as error:
            _logger.warning('Cannot connect with Razorpay POS. Error: %s', error)
            return {'errorMessage': str(error)}
        except ValueError as error:
            _logger.warning('Cannot decode response json. Error: %s', error)
            return {'errorMessage': _('Cannot decode Razorpay POS response')}
        return res_json

    def _razorpay_get_payment_request_body(self, payment_mode=True):
        request_parameters = {
            'pushTo': {
                'deviceId': f'{self.razorpay_tid}|ezetap_android',
            },
        }
        if payment_mode:
            request_parameters.update({'mode': self.razorpay_allowed_payment_modes.upper()})
        request_parameters.update(self._razorpay_get_request_parameters())
        return request_parameters

    def _razorpay_get_request_parameters(self):
        return {
            'username': self.razorpay_username,
            'appKey': self.razorpay_api_key,
        }
