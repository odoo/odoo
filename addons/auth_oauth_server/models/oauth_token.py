from odoo import api, fields, models
from odoo.exceptions import AccessDenied

from odoo.addons.base.models.res_users import check_identity
from odoo.addons.auth_oauth_server_base.types.types import TokenGrantResult
from odoo.addons.auth_oauth_server_base.utils.oauth_utils import ACCESS_TOKEN_TTL_SECONDS, verifier_matches_challenge


class OauthToken(models.Model):
    _name = 'oauth.token'
    _description = 'The oauth access and refresh tokens and access data (client, user, scope)'

    name = fields.Char(required=True)
    client_id = fields.Many2one('oauth.client', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', required=True, ondelete='cascade', index=True)
    scope = fields.Char(required=True)
    # The Many2one relation is defined on oauth.access.token and oauth.refresh.token so that they are deleted when
    # oauth.token record is deleted (ondelete='cascade'). Otherwise, The oauth.token will be linked to a
    # single access_token and a single refresh token.
    access_token_ids = fields.One2many('oauth.access.token', 'oauth_token_id')
    refresh_token_ids = fields.One2many('oauth.refresh.token', 'oauth_token_id')

    def _redeem_authorization_code(self, code, client, redirect_uri, code_verifier, client_name=None) -> TokenGrantResult:
        authorization_code = self.env['oauth.authorization.code']._retrieve_record(code, client, redirect_uri)
        if not authorization_code:
            raise AccessDenied(self.env._("Invalid authorization code"))
        if not verifier_matches_challenge(code_verifier, authorization_code.code_challenge):
            authorization_code.sudo().unlink()
            raise AccessDenied(self.env._("Invalid PKCE code_verifier"))

        user, scope = authorization_code.user_id, authorization_code.scope
        authorization_code.sudo().unlink()

        access_token, refresh_token = self._generate(client, user, scope, client_name)
        return {
            'access_token': access_token,
            'token_type': 'Bearer',
            'expires_in': ACCESS_TOKEN_TTL_SECONDS,
            'refresh_token': refresh_token,
            'scope': scope,
        }

    def _rotate(self, refresh_token, client) -> TokenGrantResult:
        oauth_token = self._retrieve_record_by_refresh_token(refresh_token, client)
        if not oauth_token:
            raise AccessDenied(self.env._("Invalid refresh token"))
        user, scope, name = oauth_token.user_id, oauth_token.scope, oauth_token.name
        oauth_token.sudo().unlink()

        new_access_token, new_refresh_token = self._generate(client, user, scope, name)

        return {
            'access_token': new_access_token,
            'token_type': 'Bearer',
            'expires_in': ACCESS_TOKEN_TTL_SECONDS,
            'refresh_token': new_refresh_token,
            'scope': scope,
        }

    def _generate(self, client, user, scope, name=None):
        client.resource_id._check_user_access(user)

        oauth_token = self.sudo().create({
            'name': name or client.client_name,
            'client_id': client.id,
            'user_id': user.id,
            'scope': scope,
        })
        access_token = self.env['oauth.access.token']._generate(oauth_token)
        refresh_token = self.env['oauth.refresh.token']._generate(oauth_token)
        return access_token, refresh_token

    @api.model
    def _retrieve_record_by_access_token(self, access_token, client):
        access_token_record = self.env['oauth.access.token']._retrieve_record(access_token)
        return access_token_record.oauth_token_id.sudo().filtered(
            lambda oauth_token: oauth_token.client_id.id == client.id
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
        # cascades to oauth.access.token and oauth.refresh.token
        self.unlink()
