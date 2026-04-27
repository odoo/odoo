# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

import hashlib
import hmac
import logging
import requests
import time

from werkzeug.urls import url_join

from odoo.exceptions import UserError, ValidationError
from odoo.addons.sale_shopee import const

_logger = logging.getLogger(__name__)


# === CUSTOM EXCEPTION CLASSES === #

class ShopeeRateLimitError(Exception):
    """ When the API rate limit of Shopee is reached. """

    def __init__(self, operation):
        self.operation = operation
        super().__init__()


# === ONBOARDING === #

def get_public_sign(account, path, timestamp):
    """ Given the request params, returns the signing string used to sign the request.

    :param account: shopee.account
    :param str path: The path of the request
    :param int timestamp: The timestamp of the request
    :return: The public signing string
    :rtype: str
    """
    account.ensure_one()
    return hmac.new(
        account.partner_key.encode(),
        _get_public_signing_string(account, path, timestamp).encode(),
        hashlib.sha256,
    ).hexdigest()

# === API COMMUNICATIONS === #

def request_access_token(shop, main_account_id=False, is_refresh=False):
    """ Request the access tokens for a specific shop.

    see https://open.shopee.com/developer-guide/20

    Note: self.ensure_one()

    :param shop: shopee.shop
    :param int main_account_id:
    :param bool is_refresh: If True, the request is to refresh the token
    :return: The list of shop identifiers associated with the main account
    :rtype: list
    :raise: UserError if authorization_code is missing but it's not a refresh request
    """
    shop.ensure_one()

    authorization_code = shop.env.context.get('authorization_code')
    if not is_refresh and not authorization_code:
        raise UserError(shop.env._(
            "Authorization Code is required to request an Access Token."
            " Please authorize the connection first."
        ))

    body = {
        'partner_id': shop.account_id.partner_identifier,
    }
    if main_account_id:
        body['main_account_id'] = main_account_id
    else:
        body['shop_id'] = shop.shop_identifier

    if is_refresh:
        body['refresh_token'] = shop.refresh_token
        operation = 'refresh_token'
    else:
        body['code'] = authorization_code
        operation = 'get_token'

    response = make_shopee_api_request(shop, operation, body=body, method='POST')
    expire_in = response['expire_in']
    shop.update({
        'refresh_token': response['refresh_token'],
        'access_token': response['access_token'],
        'access_token_expiration_date': datetime.now() + timedelta(seconds=expire_in),
    })
    return response.get('shop_id_list')


def make_shopee_api_request(shop, operation, params=None, body=None, method='GET'):
    """ Send an API request to Shopee.

    :param shop: shopee.shop
    :param operation: str
    :param dict params: Query parameters
    :param dict body: Request body
    :param str method: HTTP method
    :return: The response content of the request
    :rtype: dict
    :raise: UserError if the request fails
    """
    shop.ensure_one()
    account = shop.account_id
    api_type = const.API_OPERATIONS_MAPPING[operation]['api_type']

    if not params:
        params = {}

    if api_type != 'public':  # Require an access token
        params['shop_id'] = shop.shop_identifier
        # Ensure that we have an access token. If not, we request one.
        if not shop.access_token or not shop.access_token_expiration_date:
            request_access_token(shop)
        # If we have one, but it expired, we refresh it
        elif shop.access_token_expiration_date < datetime.now() + timedelta(minutes=5):
            request_access_token(shop, is_refresh=True)
        params['access_token'] = shop.access_token

    path = const.API_OPERATIONS_MAPPING[operation]['url_path']
    timestamp = int(time.time())
    params.update({
        'partner_id': account.partner_identifier,
        'sign': get_api_sign(shop, operation, timestamp),
        'timestamp': timestamp,
    })

    _logger.info(
        "Operation: %(operation)s\n\tParams: %(params)s\n\tBody: %(body)s",
        {'operation': operation, 'params': params, 'body': body if body else '/'},
    )

    resp = requests.request(
        method,
        f'{const.API_PATHS[account.api_endpoint]}{path}',
        params=params,
        json=body,
    )
    if resp.status_code == 429:
        raise ShopeeRateLimitError(operation)
    if resp.status_code != 200:
        raise ValidationError(shop.env._(
            "At shop - %(shop_name)s, error %(error_code)s occurred during operation"
            " %(operation)s when contacting the Shopee API:\n\n%(error_message)s",
            shop_name=shop.name,
            operation=operation,
            error_code=resp.status_code,
            error_message=resp.text,
        ))
    if not 'application/json' in resp.headers.get('Content-Type', ''):
        response_content = resp.content
    else:
        response_content = resp.json()

        # Simple error catching with a clear message on the issue.
        if response_content.get('error'):
            message = _get_error_message(response_content)
            raise UserError(shop.env._(
                "At shop - %(shop_name)s, error %(error_code)s occurred during operation"
                " %(operation)s when contacting the Shopee API. Shopee sent:\n\n%(error_message)s",
                shop_name=shop.name,
                operation=operation,
                error_code=response_content['error'],
                error_message=message,
            ))
        _logger.info(response_content)
    if isinstance(response_content, dict) and response_content.get('response'):
        return response_content['response']
    return response_content


def get_api_sign(shop, operation, timestamp):
    """ Get the API sign for a specific shop.

    :param shop: shopee.shop
    :param str operation: The operation to perform
    :param int timestamp: The timestamp of the request
    :return: The API sign
    :rtype: str
    """
    shop.ensure_one()
    account = shop.account_id
    api_type = const.API_OPERATIONS_MAPPING[operation]['api_type']
    path = const.API_OPERATIONS_MAPPING[operation]['url_path']
    signing_string = _get_public_signing_string(account, path, timestamp)
    if api_type != 'public':
        signing_string += f'{shop.access_token}{shop.shop_identifier}'
    return hmac.new(
        account.partner_key.encode(),
        signing_string.encode(),
        hashlib.sha256,
    ).hexdigest()


def _get_public_signing_string(account, path, timestamp):
    """ Given the request params, returns the signing string used to sign the request. """
    return f'{account.partner_identifier}{path}{timestamp}'


def _get_error_message(response_content):
    """ Create an error message from the response content of a Shopee API request.

    :param dict response_content: The response content of the request
    :return: The error message
    :rtype: str
    """
    message = response_content['message']
    if response_content.get('response'):
        for order in response_content['response'].get('result_list', []):
            if order and order.get('fail_message'):
                message += f"\n{order['order_sn']}: {order['fail_message']}"
    return message
