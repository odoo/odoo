import logging
import requests

from odoo.exceptions import UserError
from odoo.tools.urls import urljoin

from odoo.addons.account_peppol.exceptions import get_peppol_error_message

_logger = logging.getLogger(__name__)

TIMEOUT = 10
PEPPOL_PROXY_URLS = {
    'prod': 'https://peppol.api.odoo.com',
    'test': 'https://peppol.test.odoo.com',
}


class PeppolIAPConnector:

    def __init__(self, company):
        assert company.exists()
        self.company = company
        self.env = company.env
        proxy_mode = company._get_peppol_edi_mode()
        assert proxy_mode in ('prod', 'test')
        self.proxy_mode = proxy_mode
        self.base_url = PEPPOL_PROXY_URLS[proxy_mode]

    def request_public_http(self, method, endpoint, data=None, params=None):
        headers = {'Content-Type': 'application/json'}
        url = urljoin(self.base_url, endpoint)
        response_vals = {}
        try:
            response = requests.request(method, url, json=data, params=params, timeout=TIMEOUT, headers=headers)
            response_vals = response.json()
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            if response_vals and 'code' in response_vals:
                raise UserError(get_peppol_error_message(self.env, response_vals))
            _logger.debug("Failed to connect to Odoo Peppol Proxy %s, %s", endpoint, e)
            raise UserError(self.env._("Failed to connect to Odoo Peppol Proxy."))
        return response_vals

    def can_connect(self, *, peppol_identifier, db_uuid, callback_url, connect_token):
        params = {'dbuuid': db_uuid, 'peppol_identifier': peppol_identifier, 'callback_url': callback_url, 'connect_token': connect_token}
        return self.request_public_http('GET', '/api/peppol/2/can_connect', params=params)

    def create_connection(self, *, peppol_identifier, db_uuid, public_key, auth_token=None, **company_details):
        params = {
            'peppol_identifier': peppol_identifier,
            'dbuuid': db_uuid,
            'company_id': self.company.id,
            'public_key': public_key,
            'auth_token': auth_token,
            **company_details
        }
        response = self.request_public_http('POST', '/api/peppol/2/connect', data=params)
        return response
