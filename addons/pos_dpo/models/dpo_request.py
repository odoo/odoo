# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

import requests
from requests.exceptions import ConnectionError, RequestException, Timeout

from odoo import _
from odoo.exceptions import UserError

#TODO: need to change 
REQUEST_TIMEOUT = 50

_logger = logging.getLogger(__name__)


def _get_dpo_base_url(payment_method, is_token=False):
    host = 'api-dev.network.global' if payment_method.dpo_test_mode else 'api.network.global'
    if is_token:
        return f'https://{host}/v1'
    return f'https://{host}/ngenius-webapi/payments/push/v1/tid:{payment_method.dpo_tid}/mid:{payment_method.dpo_mid}'


def _dpo_headers(token, dpo_test_mode):
    if dpo_test_mode:
        return {'Authorization': f'Bearer {token}', 'Chain-ID': 'DPO-DTM-Testing'}
    return {'Authorization': f'Bearer {token}'}


def refresh_dpo_token(payment_method):
    session = requests.Session()
    auth = requests.auth.HTTPBasicAuth(payment_method.dpo_client_id, payment_method.dpo_client_secret)

    try:
        response = session.get(
            f'{_get_dpo_base_url(payment_method, is_token=True)}/tokenkc/generate',
            auth=auth,
            timeout=REQUEST_TIMEOUT,
        )
        access_token = response.json().get('access_token')
        if not access_token:
            raise UserError(_('Unable to retrieve DPO bearer token: check Client ID and Client Secret.'))
        payment_method.write({"dpo_bearer_token": access_token})
        return _dpo_headers(access_token, payment_method.dpo_test_mode)

    except (ConnectionError, RequestException):
        _logger.exception('Failed to retrieve DPO bearer token: network or connection issue.')
        raise UserError(_('Could not connect to DPO API. Please check your internet connection.'))

    except (Timeout, ValueError):
        _logger.exception('DPO request failed on token generation')
        raise UserError(_('Unexpected error occurred while communicating with DPO.'))


def execute_dpo_api_request(payment_method, payload, endpoint, action):
    session = requests.Session()
    session.headers.update(_dpo_headers(payment_method.dpo_bearer_token, payment_method.dpo_test_mode))
    url = f'{_get_dpo_base_url(payment_method)}/{endpoint}'

    try:
        _logger.info(
            'Sending request to %s | Mode: %s | Headers present: %s',
            url,
            'Test' if payment_method.dpo_test_mode else 'Production',
            list(session.headers.keys()),
        )
        response = session.request(action, url, json=payload, timeout=REQUEST_TIMEOUT)
        data = response.json()

        if data.get('error_code') in ['999912', '999913']:
            _logger.info('Token expired/invalid, renewing token...')
            session.headers.update(refresh_dpo_token(payment_method))
            response = session.request(action, url, json=payload, timeout=REQUEST_TIMEOUT)
            data = response.json()
        return data

    except (ConnectionError, RequestException):
        _logger.exception('network or connection issue.')
        raise UserError(_('Could not connect to DPO API. Please check your internet connection.'))

    except (Timeout, ValueError):
        _logger.exception('DPO request failed on %s', url)
        return {'errorMessage': _('Unexpected error occurred while communicating with DPO.')}
