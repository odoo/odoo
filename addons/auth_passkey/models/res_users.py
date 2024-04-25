from odoo import fields, models, _
from odoo.addons.base.models.res_users import check_identity


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
            'res_model': 'auth.passkey.key.name',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'dialog_size': 'medium',
            }
        }
