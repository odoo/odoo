# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import hashlib
import logging

import requests

from odoo import api, fields, models
from odoo.exceptions import AccessDenied, ValidationError
from odoo.tools import hmac

_logger = logging.getLogger(__name__)

# scope of the code verifier derivation, see odoo.tools.hmac
VERIFIER_SCOPE = 'auth_oauth_pkce_verifier'


class AuthOauthProvider(models.Model):
    """Class defining the configuration values of an OAuth2 provider"""

    _name = 'auth.oauth.provider'
    _description = 'OAuth2 provider'
    _order = 'sequence, name'

    name = fields.Char(string='Provider name', required=True)  # Name of the OAuth2 entity, Google, etc
    client_id = fields.Char(string='Client ID')  # Our identifier
    client_secret = fields.Char(
        groups='base.group_system',
        help="Only needed when the client is registered as confidential on the provider "
             "side. Sent to the token endpoint along with the code verifier. "
             "Leave empty for a public client.",
    )
    client_secret_method = fields.Selection(
        selection=[
            ('post', "POST Parameter"),
            ('basic', "Authorization Header"),
        ],
        string='Client Secret Sent As',
        default='post',
        required=True,
        help="How the client secret reaches the token endpoint.\n"
             "POST Parameter: as a client_secret field of the request body.\n"
             "Authorization Header: as the password of an HTTP Basic authorization "
             "header, with the client id as the user.",
    )
    flow = fields.Selection(
        selection=[
            ('implicit', "Implicit"),
            ('pkce', "Authorization Code (PKCE)"),
        ],
        string='OAuth2 Flow',
        default='implicit',
        required=True,
        help="Implicit: the provider hands over an access token directly.\n"
             "Authorization Code (PKCE): the provider hands over a single use code, "
             "exchanged for an access token on the token endpoint.",
    )
    auth_endpoint = fields.Char(string='Authorization URL', required=True)  # OAuth provider URL to authenticate users
    token_endpoint = fields.Char(
        string='Token URL',
        help="Provider endpoint trading the authorization code for an access token. "
             "Required by the PKCE flow.",
    )
    scope = fields.Char(default='openid profile email')  # OAUth user data desired to access
    validation_endpoint = fields.Char(string='UserInfo URL', required=True)  # OAuth provider URL to get user information
    access_token_method = fields.Selection(
        selection=[
            ('param', "Query Parameter"),
            ('header', "Authorization Header"),
        ],
        string='Access Token Sent As',
        default='param',
        required=True,
        help="How the access token reaches the UserInfo and data endpoints.\n"
             "Query Parameter: as an access_token field of the query string.\n"
             "Authorization Header: as a Bearer credential, which "
             "is the form modern providers are expected to support.",
    )
    data_endpoint = fields.Char()
    enabled = fields.Boolean(string='Allowed')
    icon = fields.Char(string='Custom Material Symbols Icon', default='login')
    css_class = fields.Char(string='CSS class', default='oi oi-fw text-primary')
    body = fields.Char(required=True, string="Login button label", help='Link text in Login Dialog', translate=True)
    sequence = fields.Integer(default=10)

    @api.constrains('flow', 'token_endpoint')
    def _check_pkce_token_endpoint(self):
        for provider in self:
            if provider.flow == 'pkce' and not provider.token_endpoint:
                raise ValidationError(self.env._(
                    "A Token URL is required to use the PKCE flow on provider %(name)s.",
                    name=provider.name,
                ))

    def _get_code_verifier(self, session_id, nonce):
        """Derive the code verifier of one authorization request.

        :param str session_id: session the authorization request was issued to
        :param str nonce: nonce of the authorization request
        :return: a 64 characters verifier, within the RFC 7636 §4.1 bounds
        :rtype: str
        """
        self.ensure_one()
        # hexdigest: 64 characters, all of them in the unreserved set
        return hmac(self.env(su=True), VERIFIER_SCOPE, (session_id, self.id, nonce))

    def _get_code_challenge(self, code_verifier):
        """Derive the challenge sent along the authorization request from the
        verifier kept for the token request.
        """
        digest = hashlib.sha256(code_verifier.encode('ascii')).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b'=').decode('ascii')

    def _exchange_code_for_token(self, code, code_verifier, redirect_uri):
        """Trade the authorization code for an access token.

        :param str code: the code handed over by the provider on the callback
        :param str code_verifier: the verifier matching the challenge sent along
            the authorization request
        :param str redirect_uri: same value as the one of the authorization request
        :return: the token endpoint response
        :rtype: dict
        :raise AccessDenied: if the provider turns the exchange down
        """
        self.ensure_one()
        # sudo: the token request is issued from a route with no user, and the
        # client secret is restricted to the system group
        provider = self.sudo()
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': provider.client_id,
            'code_verifier': code_verifier,
        }
        # the client id stays in the body either way: the PKCE flow asks for it
        # (RFC 7636 §4.3) whether or not the client authenticates itself
        auth = None
        if provider.client_secret:
            if provider.client_secret_method == 'basic':
                auth = (provider.client_id or '', provider.client_secret)
            else:
                data['client_secret'] = provider.client_secret
        try:
            response = requests.post(
                provider.token_endpoint,
                data=data,
                auth=auth,
                headers={'Accept': 'application/json'},
                timeout=10,
            )
        except requests.RequestException:
            _logger.warning("OAuth2 PKCE: token endpoint of provider %r is unreachable", provider.name)
            raise AccessDenied()
        try:
            token = response.json()
        except ValueError:
            token = None
        if not isinstance(token, dict):
            _logger.warning("OAuth2 PKCE: provider %r sent a malformed token response", provider.name)
            raise AccessDenied()

        if not response.ok or token.get('error'):
            _logger.warning(
                "OAuth2 PKCE: provider %r turned the code exchange down (%s): %s",
                provider.name, response.status_code,
                token.get('error_description') or token.get('error'),
            )
            raise AccessDenied()
        if not token.get('access_token'):
            _logger.warning("OAuth2 PKCE: provider %r sent no access token", provider.name)
            raise AccessDenied()
        return token
