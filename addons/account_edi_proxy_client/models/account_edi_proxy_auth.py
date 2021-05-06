import base64
import hashlib
import hmac
import json
import requests
import time
import werkzeug.urls


class OdooEdiProxyAuth(requests.auth.AuthBase):
    """ For routes that needs to be authenticated and verified for access.
        Allows:
        1) to preserve the integrity of the message between the endpoints.
        2) to check user access rights and account validity
        3) to avoid that multiple database use the same credentials, via a refresh_token that expire after 24h.
    """

    def __init__(self, user=False):
        self.id_client = user and user.id_client or False
        self.refresh_token = user and user.refresh_token or False

    def __call__(self, request):
        # We don't sign request that still don't have a id_client/refresh_token
        if not self.id_client or not self.refresh_token:
            return request
        # craft the message (timestamp|url path|id_client|query params|body content)
        msg_timestamp = int(time.time())
        parsed_url = werkzeug.urls.url_parse(request.path_url)

        body = request.body
        if isinstance(body, bytes):
            body = body.decode()
        body = json.loads(body)

        message = '%s|%s|%s|%s|%s' % (
            msg_timestamp,  # timestamp
            parsed_url.path,  # url path
            self.id_client,
            json.dumps(werkzeug.urls.url_decode(parsed_url.query), sort_keys=True),  # url query params sorted by key
            json.dumps(body, sort_keys=True))  # http request body
        h = hmac.new(base64.b64decode(self.refresh_token), message.encode(), digestmod=hashlib.sha256)

        request.headers.update({
            'odoo-edi-client-id': self.id_client,
            'odoo-edi-signature': h.hexdigest(),
            'odoo-edi-timestamp': msg_timestamp,
        })
        return request
