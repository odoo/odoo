# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import hashlib
import hmac
import json
import requests
import time
import werkzeug.urls

class AdyenProxyAuth(requests.auth.AuthBase):
    def __init__(self, adyen_account_id):
        super(AdyenProxyAuth, self).__init__()
        self.adyen_account_id = adyen_account_id

    def __call__(self, request):
        h = hmac.new(self.adyen_account_id.proxy_token.encode('utf-8'), digestmod=hashlib.sha256)

        # Craft the message (timestamp|url path|query params|body content)
        msg_timestamp = int(time.time())
        parsed_url = werkzeug.urls.url_parse(request.path_url)
        body = request.body
        if isinstance(body, bytes):
            body = body.decode('utf-8')
        body = json.loads(body)

        message = '%s|%s|%s|%s' % (
            msg_timestamp,  # timestamp
            parsed_url.path,  # url path
            json.dumps(werkzeug.urls.url_decode(parsed_url.query), sort_keys=True),  # url query params sorted by key
            json.dumps(body, sort_keys=True))  # request body

        h.update(message.encode('utf-8'))  # digest the message

        request.headers.update({
            'oe-adyen-uuid': self.adyen_account_id.adyen_uuid,
            'oe-signature': base64.b64encode(h.digest()),
            'oe-timestamp': msg_timestamp,
        })

        return request
