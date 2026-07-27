from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from werkzeug.exceptions import BadRequest, default_exceptions

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessDenied

from odoo.addons.auth_oauth_server_base.utils.oauth_utils import oauth_base_url
from odoo.addons.auth_oauth_server_base.types.types import AuthMethod, TokenGrantResult

# Anti-clickjacking: the login screen and consent screen must never be
# embeddable in an iframe by a third-party page - only opened as a normal top-level navigation or new tab.
NO_FRAME_HEADERS = {
    'X-Frame-Options': 'DENY',
    'Content-Security-Policy': "frame-ancestors 'none'",
}


class OauthServerControllerBase(http.Controller):
    """Shared HTTP surface for an OAuth 2.1 authorization server.
    Concrete controllers subclass this and implement the template methods below."""

    # ------------------------------------------------------
    # Protected resource metadata
    # ------------------------------------------------------

    @http.route(
        '/.well-known/oauth-protected-resource/<string:resource_name>',
        type='http', auth='public', methods=['GET'],
    )
    def protected_resource_metadata(self, resource_name: str):
        resource = self._get_oauth_resource(resource_name)
        base_url = oauth_base_url(self.env)
        return request.make_json_response({
            'resource': f'{base_url}/{resource.name}',
            'authorization_servers': [f'{base_url}/oauth/{resource.name}'],
        })

    # ------------------------------------------------------
    # Authorization server metadata
    # ------------------------------------------------------

    @http.route(
        '/.well-known/oauth-authorization-server/oauth/<string:resource_name>',
        type='http', auth='public', methods=['GET'],
    )
    def authorization_server_metadata(self, resource_name: str):
        resource = self._get_oauth_resource(resource_name)
        return request.make_json_response(self._authorization_server_metadata(resource))

    def _authorization_server_metadata(self, resource) -> dict:
        base_url = oauth_base_url(self.env)
        return {
            'issuer': f'{base_url}/oauth/{resource.name}',
            'authorization_endpoint': f'{base_url}/oauth/authorize',
            'token_endpoint': f'{base_url}/oauth/token',
            'revocation_endpoint': f'{base_url}/oauth/revoke',
            'response_types_supported': ['code'],
            'grant_types_supported': ['authorization_code', 'refresh_token'],
            'code_challenge_methods_supported': ['S256'],
            'token_endpoint_auth_methods_supported': self._supported_token_endpoint_auth_methods(),
            'scopes_supported': [resource.access_token_scope],
        }

    def _supported_token_endpoint_auth_methods(self) -> list[AuthMethod]:
        return ['none', 'client_secret_basic', 'client_secret_post']

    # ------------------------------------------------------
    # Authorization Code Generation
    # ------------------------------------------------------

    @http.route('/oauth/authorize', type='http', auth='public', methods=['GET'])
    def authorize(self, **params):
        client = request.env['oauth.client'].sudo().search([('client_id', '=', params.get('client_id'))], limit=1)
        self._validate_authorize_request(client, params)
        try:
            return self._handle_authorize_request(client, params)
        except AccessDenied as e:
            self._raise_oauth_error("authorization_failed", description=str(e))

    def _validate_authorize_request(self, client, params: dict) -> None:
        if not client:
            self._raise_oauth_error("authorization_failed", description="Unknown client_id")
        if not client._is_redirect_uri_registered(params.get('redirect_uri')):
            self._raise_oauth_error("authorization_failed", description="redirect_uri is not registered for this client")
        if params.get('response_type') != 'code':
            self._raise_oauth_error("authorization_failed", description="Only response_type=code is supported")
        if params.get('code_challenge_method') != 'S256' or not params.get('code_challenge'):
            self._raise_oauth_error("authorization_failed", description="PKCE with S256 is required (OAuth 2.1)")

    def _handle_authorize_request(self, client, params: dict):
        raise NotImplementedError

    # ------------------------------------------------------
    # Exchanging Authorization Code / Refresh Token for an Access Token
    # ------------------------------------------------------

    @http.route('/oauth/token', type='http', auth='public', methods=['POST'], csrf=False)
    def token(self, **params):
        try:
            client = self._authenticate_client(params)
        except AccessDenied as e:
            self._raise_oauth_error('invalid_client', description=str(e), status=401)

        grant_type = params.get('grant_type')
        try:
            if grant_type == 'authorization_code':
                result = self._redeem_authorization_code(client, params)
            elif grant_type == 'refresh_token':
                result = self._redeem_refresh_token(client, params)
            else:
                self._raise_oauth_error('unsupported_grant_type')
        except AccessDenied as e:
            self._raise_oauth_error('invalid_grant', description=str(e))
        return request.make_json_response(result)

    def _redeem_authorization_code(self, client, params: dict) -> TokenGrantResult:
        """Redeem an authorization_code for an access, refresh token pair on behalf of the already-authenticated `client`."""
        raise NotImplementedError

    def _redeem_refresh_token(self, client, params: dict) -> TokenGrantResult:
        """Redeem a refresh_token for a new access, refresh token pair and revoke the old access, refresh tokens,
        on behalf of the already-authenticated `client`."""
        raise NotImplementedError

    # ------------------------------------------------------
    # Revoke Access / Refresh Tokens
    # ------------------------------------------------------

    @http.route('/oauth/revoke', type='http', auth='public', methods=['POST'], csrf=False)
    def revoke(self, **params):
        try:
            client = self._authenticate_client(params)
        except AccessDenied as e:
            self._raise_oauth_error('invalid_client', description=str(e), status=401)

        self._handle_revoke_request(client, params.get('token'))
        # RFC 7009: always report success so that an attacker can't differentiate between
        # a rejected revoke request because the token doesn't exist and a rejected revoke
        # request because the token belongs to a different client.
        return request.make_json_response({})

    def _handle_revoke_request(self, client, token: str) -> None:
        """Revoke `token` (if it exists) on behalf of the authenticated `client`."""
        raise NotImplementedError

    # ------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------

    def _get_oauth_resource(self, resource_name: str):
        # Sudo is used because the metadata endpoints are public: an unauthenticated client must be
        # able to discover the resources protected by this server.
        resource = self.env['oauth.resource'].sudo().search([('name', '=', resource_name)], limit=1)
        if not resource:
            self._raise_oauth_error("invalid_resource", f"OAuth resource {resource_name} isn't available", status=404)
        return resource

    def _authenticate_client(self, params: dict):
        """Resolve and authenticate the client presenting this request, from either the
        client_id/client_secret request params or an HTTP Basic Authorization header.

        Raises AccessDenied if the client is unknown or if a confidential client's secret
        doesn't check out.
        """
        auth_header = request.httprequest.authorization
        client_id = params.get('client_id') or (auth_header.username if auth_header else None)
        client = request.env['oauth.client'].sudo().search([('client_id', '=', client_id)], limit=1)
        if not client:
            raise AccessDenied(self.env._("Invalid client credentials"))

        if client.client_type == 'confidential':
            secret = params.get('client_secret') or (auth_header.password if auth_header else None)
            if not client._verify_client_secret(secret):
                raise AccessDenied(self.env._("Invalid client credentials"))
        return client

    def _raise_oauth_error(self, error: str, description: str | None = None, status: int = 400) -> None:
        body = {'error': error}
        if description:
            body['error_description'] = description
        exception_cls = default_exceptions.get(status, BadRequest)
        raise exception_cls(response=request.make_json_response(body, status=status))

    def _redirect_to_url(self, redirect_url: str, params: dict, local: bool):
        """Redirect back to 'redirect_url', merging 'params' into the query string of the redirect_url.

        request.redirect_query can't be used here: it unconditionally appends '?', which adds a
        second '?' when the redirect_uri already has a query string.
        """
        uri_parts = urlsplit(redirect_url)
        query = urlencode([*parse_qsl(uri_parts.query, keep_blank_values=True), *params.items()])
        return request.redirect(urlunsplit(uri_parts._replace(query=query)), local=local)
