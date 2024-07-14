import base64
import hashlib
import hmac
import json
import requests
import time
import werkzeug.urls


class OdooFinAuth(requests.auth.AuthBase):
    """ This is used to sign the request going towards OdooFin
        e.g.:
            requests.get(ODOOFIN + '/example', auth=OdooFinAuth())
            By using `auth=OdooFinAuth(self)` when doing a http request, the request will be signed and
            the signature is added on the request headers.
            On the reception side, we verifiy the integrity of the request.
            If the signature doesn't match, then Forbidden is raised.
    """
    def __init__(self, record=None):
        self.access_token = record and record.access_token or False
        self.refresh_token = record and record.refresh_token or False
        self.client_id = record and record.client_id or False

    def __call__(self, request):
        # We don't sign request that still don't have a client_id/refresh_token
        if not self.client_id or not self.refresh_token:
            return request
        # craft the message (timestamp|url path|client_id|access_token|query params|body content)
        msg_timestamp = int(time.time())
        parsed_url = werkzeug.urls.url_parse(request.path_url)

        body = request.body
        if isinstance(body, bytes):
            body = body.decode('utf-8')
        body = json.loads(body)

        message = '%s|%s|%s|%s|%s|%s' % (
            msg_timestamp,  # timestamp
            parsed_url.path,  # url path
            self.client_id,
            self.access_token,
            json.dumps(werkzeug.urls.url_decode(parsed_url.query), sort_keys=True),  # url query params sorted by key
            json.dumps(body, sort_keys=True))  # http request body

        h = hmac.new(base64.b64decode(self.refresh_token), message.encode('utf-8'), digestmod=hashlib.sha256)

        request.headers.update({
            'odoofin-client-id': self.client_id,
            'odoofin-access-token': self.access_token,
            'odoofin-signature': base64.b64encode(h.digest()),
            'odoofin-timestamp': msg_timestamp,
        })
        return request
