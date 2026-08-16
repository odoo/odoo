import logging

import requests

from odoo import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PeppolIAPConnector:
    """HTTP REST client for non-authenticated /api/peppol/2/* (_make_request is jsonrpc only)"""

    def __init__(self, company):
        assert company.exists()
        self.company = company
        self.env = company.env
        self.proxy_mode = company._get_peppol_edi_mode()
        assert self.proxy_mode in ('prod', 'test')

    def _request(self, method, endpoint, *, params=None, data=None):
        headers = {'Content-Type': 'application/json'}
        response_vals = {}
        base_url = self.env['account_edi_proxy_client.user']._account_peppol_get_endpoints(self.proxy_mode)
        try:
            if method == 'GET':
                response = requests.get(base_url + endpoint, params=params, timeout=(2, 5), headers=headers)
            else:
                response = requests.post(base_url + endpoint, json=data, timeout=(2, 5), headers=headers)
            response_vals = response.json()
            response.raise_for_status()
        except (requests.exceptions.RequestException, ValueError) as e:
            message = response_vals.get('message') if isinstance(response_vals, dict) else None
            _logger.warning("Peppol proxy request to %s failed: %s", endpoint, e)
            raise UserError(message or _("Failed to connect to Odoo Peppol Proxy."))
        return response_vals

    def can_connect(self, *, peppol_identifier, db_uuid, callback_url, connect_token, contact_email=None, webhook_url=None):
        return self._request('GET', '/api/peppol/2/can_connect', params={
            'dbuuid': db_uuid,
            'peppol_identifier': peppol_identifier,
            'callback_url': callback_url,
            'webhook_url': webhook_url,
            'connect_token': connect_token,
            'contact_email': contact_email,
        })

    def create_connection(self, *, peppol_identifier, db_uuid, public_key, auth_token=None, **company_details):
        response_vals = self._request('POST', '/api/peppol/2/connect', data={
            'peppol_identifier': peppol_identifier,
            'dbuuid': db_uuid,
            'company_id': self.company.id,
            'public_key': public_key,
            'auth_token': auth_token,
            **company_details,
        })
        if response_vals.get('code') and not response_vals.get('id_client'):
            raise UserError(response_vals.get('message') or _("Peppol registration failed."))
        return response_vals
