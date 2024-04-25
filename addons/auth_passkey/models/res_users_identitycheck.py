from odoo import api, fields, _
from odoo.http import request
from odoo.addons.base.models.res_users import CheckIdentity


class CheckIdentityPasskeys(CheckIdentity):
    _inherit = 'res.users.identitycheck'

    auth_method = fields.Selection(selection_add=[('passkey', 'Passkey')])

    @api.model
    def _get_default_auth_method(self):
        if self.env.user.auth_passkey_key_ids:
            return 'passkey'
        else:
            return super()._get_default_auth_method()

    def _check_identity(self, *args):
        self.ensure_one()
        if self.auth_method == 'passkey':
            assert self.env['auth.passkey.key']._get_passkey_by_credential_id(args[0]['id']).create_uid == self.env.user
            challenge = request.session.pop('webauthn_challenge')
            self.env['auth.passkey.key']._verify_auth(args[0], challenge)
        else:
            super()._check_identity(self, *args)

    def action_use_password(self):
        self.ensure_one()
        self.auth_method = 'password'
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.users.identitycheck',
            'res_id': self.id,
            'name': _('Security Control'),
            'target': 'new',
            'views': [(False, 'form')],
        }
