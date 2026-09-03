from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessDenied

from odoo.addons.base.models.res_users import check_identity
from odoo.addons.auth_oauth_server_base.types.types import TokenGrantResult
from odoo.addons.auth_oauth_server_base.utils.oauth_utils import ACCESS_TOKEN_TTL_SECONDS, verifier_matches_challenge


class OauthToken(models.Model):
    _name = 'oauth.token'
    _description = 'The oauth access and refresh tokens and access data (client, user, scope)'

    client_id = fields.Many2one('oauth.client', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', required=True, ondelete='cascade')
    scope = fields.Char(required=True)
    # Related so that a user can see the application name in their preferences without read access on oauth.client.
    client_name = fields.Char(related='client_id.client_name', string="Application")
    # The Many2one relation is defined on res.users.apikeys and oauth.refresh.token so that they are deleted when
    # oauth.token record is deleted (ondelete='cascade'). Otherwise, The oauth.token will be linked to a
    # single access_token and a single refresh token.
    access_token_ids = fields.One2many('res.users.apikeys', 'oauth_token_id')
    refresh_token_ids = fields.One2many('oauth.refresh.token', 'oauth_token_id')

    def _redeem_authorization_code(self, code, client, redirect_uri, code_verifier) -> TokenGrantResult:
        authorization_code = self.env['oauth.authorization.code']._retrieve_record(code, client, redirect_uri)
        if not authorization_code:
            raise AccessDenied(self.env._("Invalid authorization code"))
        if not verifier_matches_challenge(code_verifier, authorization_code.code_challenge):
            authorization_code.sudo().unlink()
            raise AccessDenied(self.env._("Invalid PKCE code_verifier"))

        user, scope = authorization_code.user_id, authorization_code.scope
        authorization_code.sudo().unlink()

        access_token, refresh_token = self._generate(client, user, scope)
        return {
            'access_token': access_token,
            'token_type': 'Bearer',
            'expires_in': ACCESS_TOKEN_TTL_SECONDS,
            'refresh_token': refresh_token,
            'scope': scope,
        }

    def _generate(self, client, user, scope):
        client.resource_id._check_user_access(user)

        oauth_token = self.sudo().create({
            'client_id': client.id,
            'user_id': user.id,
            'scope': scope,
        })
        access_token = oauth_token._generate_access_token(client, user)
        refresh_token = self.env['oauth.refresh.token']._generate(oauth_token)
        return access_token, refresh_token

    def _generate_access_token(self, client, user):
        self.ensure_one()
        access_token, access_token_id = self.env['res.users.apikeys'].with_user(user).sudo()._generate_access_token(
            scope=self.scope,
            name=f'OAuth: {client.client_name}',
            expiration_date=fields.Datetime.now() + timedelta(seconds=ACCESS_TOKEN_TTL_SECONDS)
        )
        self.env['res.users.apikeys'].sudo().browse(access_token_id).oauth_token_id = self
        return access_token

    def _rotate(self, refresh_token, client) -> TokenGrantResult:
        oauth_token = self._retrieve_record_by_refresh_token(refresh_token, client)
        if not oauth_token:
            raise AccessDenied(self.env._("Invalid refresh token"))
        user, scope = oauth_token.user_id, oauth_token.scope
        oauth_token.sudo().unlink()

        new_access_token, new_refresh_token = self._generate(client, user, scope)

        return {
            'access_token': new_access_token,
            'token_type': 'Bearer',
            'expires_in': ACCESS_TOKEN_TTL_SECONDS,
            'refresh_token': new_refresh_token,
            'scope': scope,
        }

    @api.model
    def _retrieve_record_by_access_token(self, access_token, client):
        access_token_id, user_id = self.env['res.users.apikeys']._retrieve_record(access_token)
        if not access_token_id:
            return self
        access_token_record = self.env['res.users.apikeys'].sudo().browse(access_token_id)
        return access_token_record.oauth_token_id.filtered(
            lambda oauth_token: oauth_token.client_id == client and oauth_token.user_id.id == user_id
        )

    @api.model
    def _retrieve_record_by_refresh_token(self, refresh_token, client):
        refresh_token_record = self.env['oauth.refresh.token']._retrieve_record(refresh_token)
        return refresh_token_record.oauth_token_id.sudo().filtered(
            lambda oauth_token: oauth_token.client_id.id == client.id
        )

    @check_identity
    def action_remove(self):
        self.check_access('unlink')
        # cascades to res.users.apikeys (access token) and oauth.refresh.token
        self.unlink()
