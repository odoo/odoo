from odoo import api, fields, _
from odoo.exceptions import UserError, AccessDenied
from odoo.addons.base.models.res_users import CheckIdentity


class CheckIdentityPasskeys(CheckIdentity):
    _inherit = 'res.users.identitycheck'

    auth_method = fields.Selection(selection_add=[('webauthn', 'Passkey')])

    @api.model
    def _get_default_auth_method(self):
        if self.env.user.auth_passkey_key_ids:
            return 'webauthn'
        else:
            return super()._get_default_auth_method()

    def _check_identity(self):
        if self.auth_method == 'webauthn':
            try:
                credential = {
                    'webauthn_response': self.password,
                    'type': 'webauthn',
                }
                self.create_uid._check_credentials(credential, {'interactive': True})
            except AccessDenied:
                raise UserError(_("Incorrect Passkey. Please provide a valid passkey or use a different authentication method."))
        else:
            super()._check_identity()

    def action_use_password(self):
        self.ensure_one()
        self.auth_method = 'password'
        self.password = ''
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.users.identitycheck',
            'res_id': self.id,
            'name': _('Security Control'),
            'target': 'new',
            'views': [(False, 'form')],
        }
