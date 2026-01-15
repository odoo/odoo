import base64
import hashlib
import hmac
import json
import time
from typing import Literal

import requests
import werkzeug.urls


class OdooEdiProxyAuth(requests.auth.AuthBase):
    """ For routes that needs to be authenticated and verified for access.
        Allows:
        1) to preserve the integrity of the message between the endpoints.
        2) to check user access rights and account validity
        3) to avoid that multiple database use the same credentials, via a refresh_token that expire after 24h.
    """

    def __init__(self, user=False, auth_type: Literal['hmac', 'asymmetric'] = 'hmac'):
        self.id_client = user and user.id_client or False
        self.auth_type = auth_type
        self.refresh_token = user and user.sudo().refresh_token or False
        self.private_key = user and user.sudo().private_key_id or False

    def __get_payload(self, request, msg_timestamp):
        # craft the message (timestamp|url path|id_client|query params|body content)
        parsed_url = werkzeug.urls.url_parse(request.path_url)

        body = request.body
        if isinstance(body, bytes):
            body = body.decode()
        body = json.loads(body)

        return '%s|%s|%s|%s|%s' % (
            msg_timestamp,  # timestamp
            parsed_url.path,  # url path
            self.id_client,
            json.dumps(werkzeug.urls.url_decode(parsed_url.query), sort_keys=True),  # url query params sorted by key
            json.dumps(body, sort_keys=True))  # http request body

    def __sign_request_with_token(self, message):
        h = hmac.new(base64.b64decode(self.refresh_token), message.encode(), digestmod=hashlib.sha256)

        return h.hexdigest()

    def __sign_with_private_key(self, message):
        # this is a fallback to resync the token in case of of multiple database desynchronization problem
        # this happens when a database is restored from a backup or when it is copied without neutralization
        return self.private_key._sign(message.encode(), formatting='base64').decode()

    def __call__(self, request):
        if not self.id_client:
            return request

        timestamp = int(time.time())
        request.headers.update({
            'odoo-edi-client-id': self.id_client,
            'odoo-edi-timestamp': timestamp,
        })
        message = self.__get_payload(request, timestamp)

        if self.auth_type == 'asymmetric' and self.private_key:
            request.headers.update({
                'odoo-edi-signature': self.__sign_with_private_key(message),
                'odoo-edi-signature-type': 'asymmetric'
            })
        elif self.refresh_token:
            request.headers.update({
                'odoo-edi-signature': self.__sign_request_with_token(message),
                'odoo-edi-signature-type': 'hmac'
            })

        return request
