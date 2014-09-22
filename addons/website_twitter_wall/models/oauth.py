# -*- coding: utf-8 -*-
from base64 import standard_b64encode
from hashlib import sha1
from hmac import new
from random import randint
from time import time
from urllib2 import Request, quote, urlopen


class Oauth(object):

    def __init__(self, API_key, API_secret):
        self.REQUEST_URL = "https://api.twitter.com/oauth/request_token"
        self.AUTHORIZE_URL = "https://api.twitter.com/oauth/authorize"
        self.ACCESS_URL = "https://api.twitter.com/oauth/access_token"

        self.API_key = API_key
        self.API_secret = API_secret
        self.Oauth_Token = None
        self.Oauth_Token_Secret = None
        self.parameters = {}

    def _get_nonce(self):
        NONCE = ""
        for i in range(32):
            NONCE += chr(randint(97, 122))
        return NONCE

    def _get_timestamp(self):
        return str(int(time()))

    def _generate_header(self, URL, signature_method, oauth_version, callback_url=None, request_token=None, oauth_verifier=None, params=None, method='POST'):
        self.parameters = {}
        if params:
            self.parameters.update(params)
        if callback_url:
            self.parameters['oauth_callback'] = callback_url
        if request_token:
            self.parameters['oauth_token'] = request_token
        if oauth_verifier:
            self.parameters['oauth_verifier'] = oauth_verifier
        if self.Oauth_Token:
            self.parameters['oauth_token'] = self.Oauth_Token
        self.parameters['oauth_consumer_key'] = self.API_key
        self.parameters['oauth_nonce'] = self._get_nonce()
        self.parameters['oauth_signature_method'] = signature_method
        self.parameters['oauth_timestamp'] = self._get_timestamp()
        self.parameters['oauth_version'] = oauth_version
        self.parameters['oauth_signature'] = self._build_signature(URL, method)
        if method == 'GET':
            return self.to_get_header()
        return self.to_header()

    def _build_signature(self, URL, method):
        BASE_STRING = method + '&' + quote(URL, '') + '&' + quote(self.to_parameter_string(), '')
        SIGNING_KEY = quote(self.API_secret, '') + '&' + (quote(self.Oauth_Token_Secret, '') if self.Oauth_Token_Secret else '')
        return standard_b64encode(new(SIGNING_KEY.encode(), BASE_STRING.encode(), sha1).digest()).decode('ascii')

    def to_header(self, realm=''):
        """Serialize as a header for an HTTPAuth request."""
        auth_header = 'OAuth realm="%s"' % realm
        # Add the oauth parameters.
        if self.parameters:
            for k, v in self.parameters.iteritems():
                if k[:6] == 'oauth_':
                    auth_header += ', %s="%s"' % (k, quote(v, ''))
        return auth_header

    def to_get_header(self):
        """Serialize as a header for an HTTPAuth GET request."""
        auth_header = ""
        # Add the oauth parameters.
        if self.parameters:
            for k, v in self.parameters.iteritems():
                auth_header += '&%s=%s' % (quote(k, ''), quote(v, ''))
        return auth_header

    def to_parameter_string(self):
        """Return a string that contains the parameters that must be signed."""
        params = self.parameters
        try:
            del params['oauth_signature']
        except:
            pass
        key_values = [(quote(str(k), ''), quote(str(v), '')) for k, v in params.items()]
        key_values.sort()
        return '&'.join(['%s=%s' % (k, v) for k, v in key_values])

    def _string_to_dict(self, request_response):
        return dict(item.split("=") for item in request_response.split("&"))

    def _access_token(self, request_token, oauth_verifier):
        HEADER = self._generate_header(self.ACCESS_URL, 'HMAC-SHA1', '1.0', request_token=request_token, oauth_verifier=oauth_verifier)

        HTTP_REQUEST = Request(self.ACCESS_URL)
        HTTP_REQUEST.add_header('Authorization', HEADER)
        access_token_response = urlopen(HTTP_REQUEST, '').read()
        access_token_response = self._string_to_dict(access_token_response)
        return access_token_response

    def set_access_token(self, Oauth_Token, Oauth_Token_Secret):
        self.Oauth_Token = Oauth_Token
        self.Oauth_Token_Secret = Oauth_Token_Secret
