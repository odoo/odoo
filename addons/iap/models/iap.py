# -*- coding: utf-8 -*-
import contextlib
import logging
import json
import uuid

import werkzeug.urls
import requests

from odoo import api, fields, models, exceptions
from odoo.tools import pycompat

_logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = 'https://iap.odoo.com'


#----------------------------------------------------------
# Helpers for both clients and proxy
#----------------------------------------------------------
def get_endpoint(env):
    url = env['ir.config_parameter'].sudo().get_param('iap.endpoint', DEFAULT_ENDPOINT)
    return url


#----------------------------------------------------------
# Helpers for clients
#----------------------------------------------------------
class InsufficientCreditError(Exception):
    pass


class AuthenticationError(Exception):
    pass


def jsonrpc(url, method='call', params=None, timeout=15):
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
        raise exceptions.AccessError('The url that this service requested returned an error. Please contact the author the app. The url it tried to contact was ' + url)

#----------------------------------------------------------
# Helpers for proxy
#----------------------------------------------------------
class IapTransaction(object):

    def __init__(self):
        self.credit = None

def authorize(env, key, account_token, credit, dbuuid=False, description=None, credit_template=None):
    endpoint = get_endpoint(env)
    params = {
        'account_token': account_token,
        'credit': credit,
        'key': key,
        'description': description,
    }
    if dbuuid:
        params.update({'dbuuid': dbuuid})
    try:
        transaction_token = jsonrpc(endpoint + '/iap/1/authorize', params=params)
    except InsufficientCreditError as e:
        if credit_template:
            arguments = json.loads(e.args[0])
            arguments['body'] = pycompat.to_text(env['ir.qweb'].render(credit_template))
            e.args = (json.dumps(arguments),)
        raise e
    return transaction_token

def cancel(env, transaction_token, key):
    endpoint = get_endpoint(env)
    params = {
        'token': transaction_token,
        'key': key,
    }
    r = jsonrpc(endpoint + '/iap/1/cancel', params=params)
    return r

def capture(env, transaction_token, key, credit):
    endpoint = get_endpoint(env)
    params = {
        'token': transaction_token,
        'key': key,
        'credit_to_capture': credit,
    }
    r = jsonrpc(endpoint + '/iap/1/capture', params=params)
    return r


@contextlib.contextmanager
def charge(env, key, account_token, credit, dbuuid=False, description=None, credit_template=None):
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
    transaction_token = authorize(env, key, account_token, credit, dbuuid, description, credit_template)
    try:
        transaction = IapTransaction()
        transaction.credit = credit
        yield transaction
    except Exception as e:
        r = cancel(env,transaction_token, key)
        raise e
    else:
        r = capture(env,transaction_token, key, transaction.credit)

#----------------------------------------------------------
# Models for client
#----------------------------------------------------------
class IapAccount(models.Model):
    _name = 'iap.account'
    _rec_name = 'service_name'
    _description = 'IAP Account'

    service_name = fields.Char()
    account_token = fields.Char(default=lambda s: uuid.uuid4().hex)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id)

    @api.model
    def get(self, service_name, force_create=True):
        account = self.search([('service_name', '=', service_name), ('company_id', 'in', [self.env.user.company_id.id, False])])
        if not account and force_create:
            account = self.create({'service_name': service_name})
            # Since the account did not exist yet, we will encounter a NoCreditError,
            # which is going to rollback the database and undo the account creation,
            # preventing the process to continue any further.
            self.env.cr.commit()
        return account

    @api.model
    def get_credits_url(self, service_name, base_url='', credit=0, trial=False):
        dbuuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        if not base_url:
            endpoint = get_endpoint(self.env)
            route = '/iap/1/credit'
            base_url = endpoint + route
        account_token = self.get(service_name).account_token
        d = {
            'dbuuid': dbuuid,
            'service_name': service_name,
            'account_token': account_token,
            'credit': credit,
        }
        if trial:
            d.update({'trial': trial})
        return '%s?%s' % (base_url, werkzeug.urls.url_encode(d))

    @api.model
    def get_account_url(self):
        route = '/iap/services'
        endpoint = get_endpoint(self.env)
        d = {'dbuuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid')}

        return '%s?%s' % (endpoint + route, werkzeug.urls.url_encode(d))

    @api.model
    def get_credits(self, service_name):
        account = self.get(service_name, force_create=False)
        credit = 0

        if account:
            route = '/iap/1/balance'
            endpoint = get_endpoint(self.env)
            url = endpoint + route
            params = {
                'dbuuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
                'account_token': account.account_token,
                'service_name': service_name,
            }
            try:
                credit = jsonrpc(url=url, params=params)
            except Exception as e:
                _logger.info('Get credit error : %s', str(e))
                credit = -1

        return credit
