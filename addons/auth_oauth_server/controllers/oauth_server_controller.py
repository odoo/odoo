from urllib.parse import quote

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.exceptions import AccessDenied

from odoo.addons.auth_oauth_server_base.controllers.oauth_server_controller_base import (
    NO_FRAME_HEADERS,
    OauthServerControllerBase,
)
from odoo.addons.auth_oauth_server_base.utils.oauth_utils import oauth_base_url
from odoo.addons.auth_oauth_server_base.types.types import ClientType, TokenGrantResult

CONFIDENTIAL_AUTH_METHODS = ('client_secret_basic', 'client_secret_post')


class OauthServerController(OauthServerControllerBase):

    # ------------------------------------------------------
    # Authorization server metadata
    # ------------------------------------------------------

    def _authorization_server_metadata(self, resource) -> dict:
        return {
            **super()._authorization_server_metadata(resource),
            'registration_endpoint': f'{oauth_base_url(self.env)}/oauth/register/{resource.name}',
        }

    # ------------------------------------------------------
    # Client Registration
    # ------------------------------------------------------

    @http.route('/oauth/register/<string:resource_name>', type='http', auth='public', methods=['POST'], csrf=False)
    def register(self, resource_name: str):
        payload = request.get_json_data()
        redirect_uris = payload.get('redirect_uris')
        client_name = payload.get('client_name') or 'Unnamed OAuth client'
        auth_method = payload.get('token_endpoint_auth_method', 'client_secret_basic')
        if auth_method not in self._supported_token_endpoint_auth_methods():
            self._raise_oauth_error('invalid_client_metadata', f"Unsupported token_endpoint_auth_method {auth_method}")
        client_type: ClientType = 'confidential' if auth_method in CONFIDENTIAL_AUTH_METHODS else 'public'

        resource = self._get_oauth_resource(resource_name)

        try:
            result = request.env['oauth.client']._register_client(resource, client_name, redirect_uris, client_type)
        except ValidationError:
            self._raise_oauth_error('invalid_client_metadata')

        response = {
            'client_id': result['client_id'],
            'client_name': client_name,
            'redirect_uris': redirect_uris,
            'token_endpoint_auth_method': auth_method,
            'grant_types': ['authorization_code', 'refresh_token'],
            'response_types': ['code'],
        }
        if 'client_secret' in result:
            response['client_secret'] = result['client_secret']
        return request.make_json_response(response, status=201)

    # ------------------------------------------------------
    # Authorization Code Generation
    # ------------------------------------------------------

    def _handle_authorize_request(self, client, params: dict):
        if request.env.user._is_public():
            return self._redirect_to_login()
        client.resource_id._check_user_access(request.env.user)
        # The scope sent by the oauth client is ignored and the resource scope will be enforced instead.
        params['scope'] = client.resource_id.access_token_scope
        response = request.render('auth_oauth_server.consent', {
            'client': client,
            'resource': client.resource_id,
            'params': params,
        })
        response.headers.update(NO_FRAME_HEADERS)
        return response

    def _redirect_to_login(self):
        # request.httprequest.url includes query params so it has to be url_encoded using quote.
        # Otherwise, the query params of request.httprequest.url will be interpretted as query
        # params of the final url '/web/login?redirect...'.
        response = request.redirect(f'/web/login?redirect={quote(request.httprequest.url)}')
        response.headers.update(NO_FRAME_HEADERS)
        return response

    @http.route('/oauth/authorize/submit_consent', type='http', auth='user', methods=['POST'])
    def submit_consent(self, **params):
        client = request.env['oauth.client'].sudo().search([('client_id', '=', params.get('client_id'))], limit=1)
        self._validate_authorize_request(client, params)
        try:
            client.resource_id._check_user_access(request.env.user)
        except AccessDenied as e:
            self._raise_oauth_error("authorization_failed", description=str(e))

        if params['allow'] == 'false':
            return self._redirect_to_url(
                params['redirect_uri'],
                {'error': 'access_denied', 'state': params.get('state', '')},
                local=False,
            )
        return self._issue_code_and_redirect(client, params)

    def _issue_code_and_redirect(self, client, params: dict):
        resource = client.resource_id
        code = request.env['oauth.authorization.code']._generate(
            client=client,
            redirect_uri=params['redirect_uri'],
            code_challenge=params['code_challenge'],
            scope=resource.access_token_scope,
            user=request.env.user,
        )
        return self._redirect_to_url(
            params['redirect_uri'],
            {'code': code, 'state': params.get('state', ''), 'iss': f'{oauth_base_url(self.env)}/oauth/{resource.name}'},
            local=False,
        )

    # ------------------------------------------------------
    # Exchanging Authorization Code / Refresh Token for an Access Token
    # ------------------------------------------------------

    def _redeem_authorization_code(self, client, params: dict) -> TokenGrantResult:
        return request.env['oauth.token']._redeem_authorization_code(
            code=params.get('code'),
            client=client,
            redirect_uri=params.get('redirect_uri'),
            code_verifier=params.get('code_verifier'),
        )

    def _redeem_refresh_token(self, client, params: dict) -> TokenGrantResult:
        return request.env['oauth.token']._rotate(params.get('refresh_token'), client)

    # ------------------------------------------------------
    # Revoke Access / Refresh Tokens
    # ------------------------------------------------------

    def _handle_revoke_request(self, client, token: str) -> None:
        oauth_token = request.env['oauth.token'].sudo()
        token_record = (
            oauth_token._retrieve_record_by_access_token(token, client)
            or oauth_token._retrieve_record_by_refresh_token(token, client)
        )
        if token_record:
            token_record.unlink()
