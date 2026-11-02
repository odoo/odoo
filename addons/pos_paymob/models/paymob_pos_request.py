# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

import requests

_logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10

PAYMOB_STAGING_URL = 'https://accept-alpha.paymob.com'
PAYMOB_PRODUCTION_URLS = {
    'EG': 'https://accept.paymob.com',
    'AE': 'https://uae.paymob.com',
}


class PaymobPosRequest:
    """ Paymob "Order Through Notifications" REST API: authenticate, then register an
    order which notifies the terminal. The result arrives via callback, not these calls. """

    def __init__(self, api_key, base_url):
        self.api_key = api_key
        self.base_url = base_url
        self.auth_token = None

    def _call(self, method, endpoint, payload):
        """ Call Paymob and return the decoded JSON, or an {'errorMessage': ...} dict on failure. """
        url = self.base_url + endpoint
        try:
            response = requests.request(method, url, json=payload, timeout=REQUEST_TIMEOUT)
            return response.json()
        except requests.exceptions.RequestException as error:
            _logger.warning("Cannot connect with Paymob. Error: %s", error)
            return {'errorMessage': str(error)}
        except ValueError as error:
            _logger.warning("Cannot decode Paymob response. Error: %s", error)
            return {'errorMessage': "Cannot decode Paymob response. Error: %s" % error}

    def authenticate(self):
        response = self._call('post', '/api/auth/tokens', {'api_key': self.api_key})
        self.auth_token = response.get('token')
        return response

    def _authenticated_post(self, endpoint, payload):
        if not self.auth_token:
            auth_response = self.authenticate()
            if not self.auth_token:
                return auth_response
        payload = dict(payload, auth_token=self.auth_token)
        return self._call('post', endpoint, payload)

    def create_order(self, payload):
        return self._authenticated_post('/api/ecommerce/orders', payload)

    def send_refund(self, payload):
        return self._authenticated_post('/api/ecommerce/orders/send_refund_notification', payload)

    def send_void(self, payload):
        return self._authenticated_post('/api/ecommerce/orders/send_void_notification', payload)

    def get_transaction(self, transaction_id):
        """ Paymob's Transaction Inquiry: the authoritative state of a transaction. """
        try:
            # The id reaches us from an unverified callback; keep it out of the URL path unless it is an int.
            transaction_id = int(transaction_id)
        except (TypeError, ValueError):
            return {'errorMessage': "Invalid Paymob transaction id: %s" % transaction_id}
        if not self.auth_token:
            auth_response = self.authenticate()
            if not self.auth_token:
                return auth_response
        url = '%s/api/acceptance/transactions/%s' % (self.base_url, transaction_id)
        try:
            response = requests.get(
                url, headers={'Authorization': 'Bearer ' + self.auth_token}, timeout=REQUEST_TIMEOUT)
            return response.json()
        except requests.exceptions.RequestException as error:
            _logger.warning("Cannot connect with Paymob. Error: %s", error)
            return {'errorMessage': str(error)}
        except ValueError as error:
            _logger.warning("Cannot decode Paymob response. Error: %s", error)
            return {'errorMessage': "Cannot decode Paymob response. Error: %s" % error}
