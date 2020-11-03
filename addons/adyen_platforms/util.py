# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import decorator
import hashlib
import hmac
import json
import logging
import requests
import time

from werkzeug.urls import url_decode, url_parse
from werkzeug.exceptions import Forbidden

from odoo.http import request
from odoo.tools import float_round

_logger = logging.getLogger(__name__)
TIMEOUT = 60

def to_major_currency(amount, decimal=2):
    return float_round(amount, 0) / (10**decimal)

def to_minor_currency(amount, decimal=2):
    return int(float_round(amount, decimal) * (10**decimal))

class AdyenProxyAuth(requests.auth.AuthBase):
    def __init__(self, adyen_account_id):
        super().__init__()
        self.adyen_account_id = adyen_account_id

    def __call__(self, request):
        h = hmac.new(self.adyen_account_id.proxy_token.encode('utf-8'), digestmod=hashlib.sha256)

        # Craft the message (timestamp|url path|query params|body content)
        msg_timestamp = int(time.time())
        parsed_url = url_parse(request.path_url)
        body = request.body
        if isinstance(body, bytes):
            body = body.decode('utf-8')
        body = json.loads(body)

        message = '%s|%s|%s|%s' % (
            msg_timestamp,  # timestamp
            parsed_url.path,  # url path
            json.dumps(url_decode(parsed_url.query), sort_keys=True),  # url query params sorted by key
            json.dumps(body, sort_keys=True))  # request body

        h.update(message.encode('utf-8'))  # digest the message

        request.headers.update({
            'oe-adyen-uuid': self.adyen_account_id.adyen_uuid,
            'oe-signature': base64.b64encode(h.digest()),
            'oe-timestamp': msg_timestamp,
        })

        return request

@decorator.decorator
def odoo_payments_proxy_control(func, *args, **kwargs):
    _logger.debug('Check notification from Odoo Payments')

    adyen_uuid = request.httprequest.headers.get('oe-adyen-uuid')
    account_id = request.env['adyen.account'].sudo().search([('adyen_uuid', '=', adyen_uuid)])
    if not account_id:
        raise Forbidden()

    secret = account_id.proxy_token.encode('utf8')
    msg_signature = request.httprequest.headers.get('oe-signature')  # base64 encoded hmac sha256 digest
    msg_timestamp = request.httprequest.headers.get('oe-timestamp')

    if not (secret and msg_signature and msg_timestamp):
        raise Forbidden()

    if int(msg_timestamp) + TIMEOUT < int(time.time()):
        _logger.debug('HTTP request validation failed due to invalid timestamp for route %r', request.httprequest.path)
        raise Forbidden()

    h = hmac.new(secret, digestmod=hashlib.sha256)
    body = json.dumps(request.jsonrequest, sort_keys=True)

    message = '%s|%s|%s|%s' % (
        msg_timestamp, # timestamp
        request.httprequest.path, # url path
        json.dumps(url_decode(request.httprequest.query_string), sort_keys=True),  # url query params sorted by key
        body, # http request body
    )

    h.update(message.encode('utf-8'))

    if not hmac.compare_digest(h.digest(), base64.b64decode(msg_signature)):
        raise Forbidden()
    return func(*args, **kwargs)
