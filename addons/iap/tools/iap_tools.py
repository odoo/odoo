# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import contextlib
import logging
import json
import requests
import uuid

from odoo import exceptions, _
from odoo.tools import pycompat

_logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = 'https://iap.odoo.com'

#----------------------------------------------------------
# Helpers for both clients and proxy
#----------------------------------------------------------

def iap_get_endpoint(env):
    url = env['ir.config_parameter'].sudo().get_param('iap.endpoint', DEFAULT_ENDPOINT)
    return url

#----------------------------------------------------------
# Helpers for clients
#----------------------------------------------------------

class InsufficientCreditError(Exception):
    pass


def iap_jsonrpc(url, method='call', params=None, timeout=15):
    """
    Calls the provided JSON-RPC endpoint, unwraps the result and
    returns JSON-RPC errors as exceptions.
    """
    payload = {
        'jsonrpc': '2.0',
        'method': method,
        'params': params,
        'id': uuid.uuid4().hex,
    }

    _logger.info('iap jsonrpc %s', url)
    try:
        req = requests.post(url, json=payload, timeout=timeout)
        req.raise_for_status()
        response = req.json()
        if 'error' in response:
            name = response['error']['data'].get('name').rpartition('.')[-1]
            message = response['error']['data'].get('message')
            if name == 'InsufficientCreditError':
                e_class = InsufficientCreditError
            elif name == 'AccessError':
                e_class = exceptions.AccessError
            elif name == 'UserError':
                e_class = exceptions.UserError
            else:
                raise requests.exceptions.ConnectionError()
            e = e_class(message)
            e.data = response['error']['data']
            raise e
        return response.get('result')
    except (ValueError, requests.exceptions.ConnectionError, requests.exceptions.MissingSchema, requests.exceptions.Timeout, requests.exceptions.HTTPError) as e:
        raise exceptions.AccessError(
            _('The url that this service requested returned an error. Please contact the author of the app. The url it tried to contact was %s', url)
        )

#----------------------------------------------------------
# Helpers for proxy
#----------------------------------------------------------

class IapTransaction(object):

    def __init__(self):
        self.credit = None


def iap_authorize(env, key, account_token, credit, dbuuid=False, description=None, credit_template=None):
    endpoint = iap_get_endpoint(env)
    params = {
        'account_token': account_token,
        'credit': credit,
        'key': key,
        'description': description,
    }
    if dbuuid:
        params.update({'dbuuid': dbuuid})
    try:
        transaction_token = iap_jsonrpc(endpoint + '/iap/1/authorize', params=params)
    except InsufficientCreditError as e:
        if credit_template:
            arguments = json.loads(e.args[0])
            arguments['body'] = pycompat.to_text(env['ir.qweb']._render(credit_template))
            e.args = (json.dumps(arguments),)
        raise e
    return transaction_token


def iap_cancel(env, transaction_token, key):
    endpoint = iap_get_endpoint(env)
    params = {
        'token': transaction_token,
        'key': key,
    }
    r = iap_jsonrpc(endpoint + '/iap/1/cancel', params=params)
    return r


def iap_capture(env, transaction_token, key, credit):
    endpoint = iap_get_endpoint(env)
    params = {
        'token': transaction_token,
        'key': key,
        'credit_to_capture': credit,
    }
    r = iap_jsonrpc(endpoint + '/iap/1/capture', params=params)
    return r


@contextlib.contextmanager
def iap_charge(env, key, account_token, credit, dbuuid=False, description=None, credit_template=None):
    """
    Account charge context manager: takes a hold for ``credit``
    amount before executing the body, then captures it if there
    is no error, or cancels it if the body generates an exception.

    :param str key: service identifier
    :param str account_token: user identifier
    :param int credit: cost of the body's operation
    :param description: a description of the purpose of the charge,
                        the user will be able to see it in their
                        dashboard
    :type description: str
    :param credit_template: a QWeb template to render and show to the
                            user if their account does not have enough
                            credits for the requested operation
    :type credit_template: str
    """
    transaction_token = iap_authorize(env, key, account_token, credit, dbuuid, description, credit_template)
    try:
        transaction = IapTransaction()
        transaction.credit = credit
        yield transaction
    except Exception as e:
        r = iap_cancel(env,transaction_token, key)
        raise e
    else:
        r = iap_capture(env,transaction_token, key, transaction.credit)
