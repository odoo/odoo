import base64
import hashlib
import hmac
import json
import requests
import time
import werkzeug.urls

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


class OdooEdiProxyAuth(requests.auth.AuthBase):
    """ For routes that needs to be authenticated and verified for access.
        Allows:
        1) to preserve the integrity of the message between the endpoints.
        2) to check user access rights and account validity
        3) to avoid that multiple database use the same credentials, via a refresh_token that expire after 24h.
    """

    def __init__(self, user=False):
        self.id_client = user and user.id_client or False
        self.refresh_token = user and user.sudo().refresh_token or False
        self.private_key = user and user._should_fallback_to_private_key_auth() and user.sudo().private_key or False

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

    def __sign_request_with_token(self, message, msg_timestamp):
        h = hmac.new(base64.b64decode(self.refresh_token), message.encode(), digestmod=hashlib.sha256)

        return h.hexdigest()

    def __sign_with_private_key(self, message, msg_timestamp):
        # this is a fallback to resync the token in case of of multiple database desynchronization problem
        # this happens when a database is restored from a backup or when it is copied without neutralization
        private_key = serialization.load_pem_private_key(base64.b64decode(self.private_key), password=None)
        signature = private_key.sign(
            message.encode(),
            padding=padding.PKCS1v15(),
            algorithm=hashes.SHA256(),
        )
        return base64.b64encode(signature).decode()

    def __call__(self, request):
        if not self.id_client:
            return request

        timestamp = int(time.time())
        request.headers.update({
            'odoo-edi-client-id': self.id_client,
            'odoo-edi-timestamp': timestamp,
        })
        message = self.__get_payload(request, timestamp)

        if self.private_key:
            request.headers.update({
                'odoo-edi-signature': self.__sign_with_private_key(message, timestamp),
                'odoo-edi-signature-type': 'asymmetric'
            })
        elif self.refresh_token:
            request.headers.update({
                'odoo-edi-signature': self.__sign_request_with_token(message, timestamp),
                'odoo-edi-signature-type': 'token'
            })

        return request
