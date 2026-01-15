import json
import logging
import requests

from odoo import _

REQUEST_TIMEOUT = 10
PINE_LABS_AUTO_CANCEL_DURATION_MIN = 10
ALLOWED_ENDPOINTS = ['UploadBilledTransaction', 'GetCloudBasedTxnStatus', 'CancelTransactionForced']
ALLOWED_PAYMENT_MODES_MAPPING = {
    'all': 0,
    'card': 1,
    'upi': 10,
}

_logger = logging.getLogger(__name__)


def call_pine_labs(payment_method: object, endpoint: str, payload: dict) -> dict:
    """
    Make a request to Pine Labs POS API.

    :return The content of the response parsed from json
    """
    if endpoint not in ALLOWED_ENDPOINTS:
        raise ValueError(f"Invalid endpoint: '{endpoint}'. Allowed endpoints are: {ALLOWED_ENDPOINTS}")
    payload |= pine_labs_request_body(endpoint == 'UploadBilledTransaction', payment_method=payment_method)
    pine_labs_url = _get_pine_labs_url(payment_method=payment_method)
    url = pine_labs_url + endpoint
    try:
        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()
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

def pine_labs_request_body(payment_mode: bool, payment_method: object) -> dict:
    """
    :param payment_mode: If set, includes allowed payment mode and auto-cancel duration in
                        the request body for `UploadBilledTransaction` endpoint.

    rtype: dict
    """
    request_parameters = {
        'MerchantID': payment_method.pine_labs_merchant,
        'StoreID': payment_method.pine_labs_store,
        'ClientID': payment_method.pine_labs_client,
        'SecurityToken': payment_method.pine_labs_security_token
    }
    if payment_mode:
        # Added AutoCancelDurationInMinutes set to 10 minutes for automatically cancelling transactions on the Pine Labs side in case of lost transaction request data from the PoS system.
        pine_labs_auto_cancel_duration = payment_method.env['ir.config_parameter'].sudo().get_param('pos_pine_labs.payment_auto_cancel_duration', PINE_LABS_AUTO_CANCEL_DURATION_MIN)
        request_parameters.update({
            'AllowedPaymentMode': ALLOWED_PAYMENT_MODES_MAPPING.get(payment_method.pine_labs_allowed_payment_mode),
            'AutoCancelDurationInMinutes': pine_labs_auto_cancel_duration
        })
    return request_parameters

def _get_pine_labs_url(payment_method) -> str:
    if payment_method.env['ir.config_parameter'].sudo().get_param('pos_pine_labs.pine_labs_proxy_endpoint', ''):
        return payment_method.env['ir.config_parameter'].sudo().get_param('pos_pine_labs.pine_labs_proxy_endpoint')
    _logger.warning('To use Pine Labs outside India and Malesia, the Pine Labs Proxy Endpoint must be set because the Pine Labs URL is only accessible in India and Malesia.')
    if payment_method.pine_labs_test_mode:
        return 'https://www.plutuscloudserviceuat.in:8201/API/CloudBasedIntegration/V1/'
    return 'https://www.plutuscloudservice.in:8201/API/CloudBasedIntegration/V1/'
