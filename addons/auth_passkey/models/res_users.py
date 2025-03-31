import json

from odoo import fields, models, _
from odoo.tools import SQL
from odoo.exceptions import AccessDenied
from odoo.modules.registry import Registry

from odoo.addons.base.models.res_users import check_identity
from .._vendor.webauthn.helpers.exceptions import InvalidAuthenticationResponse


class UsersPasskey(models.Model):
    _inherit = 'res.users'

    auth_passkey_key_ids = fields.One2many('auth.passkey.key', 'create_uid')

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['auth_passkey_key_ids']

    @check_identity
    def action_create_passkey(self):
        return {
            'name': _('Create Passkey'),
            'type': 'ir.actions.act_window',
            'res_model': 'auth.passkey.key.create',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'dialog_size': 'medium',
                'registration': self.env['auth.passkey.key']._start_registration(),
            }
        }

    @classmethod
    def _login(cls, db, credential, user_agent_env):
        if credential['type'] == 'webauthn':
            webauthn = json.loads(credential['webauthn_response'])
            with Registry(db).cursor() as cr:
                cr.execute(SQL("""
                    SELECT login
                      FROM auth_passkey_key key
                      JOIN res_users usr ON usr.id = key.create_uid
                     WHERE credential_identifier=%s
                """, webauthn['id']))
                res = cr.fetchone()
                if not res:
                    raise AccessDenied(_('Unknown passkey'))
                credential['login'] = res[0]
        return super()._login(db, credential, user_agent_env=user_agent_env)

    def _check_credentials(self, credential, env):
        if credential['type'] == 'webauthn':
            webauthn = json.loads(credential['webauthn_response'])
            passkey = self.env['auth.passkey.key'].sudo().search([
                ("create_uid", "=", self.env.user.id),
                ("credential_identifier", "=", webauthn['id']),
            ])
            if not passkey:
                raise AccessDenied(_('Unknown passkey'))
            try:
                new_sign_count = self.env['auth.passkey.key']._verify_auth(
                    webauthn,
                    passkey.public_key,
                    passkey.sign_count,
                )
            except InvalidAuthenticationResponse as e:
                raise AccessDenied(e.args[0]) from None
            passkey.sign_count = new_sign_count
            return {
                'uid': self.env.user.id,
                'auth_method': 'passkey',
                'mfa': 'skip',
            }
        else:
            return super()._check_credentials(credential, env)

    def _get_session_token_fields(self):
        return super()._get_session_token_fields() | {'auth_passkey_key_ids'}

    def _get_session_token_query_params(self):
        params = super()._get_session_token_query_params()
        params['select'] = SQL("%s, ARRAY_AGG(key.id ORDER BY key.id DESC)", params['select'])
        params['joins'] = SQL("%s LEFT JOIN auth_passkey_key key ON res_users.id = key.create_uid", params['joins'])
        return params
