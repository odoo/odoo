import requests

from odoo import fields, models, _
from odoo.exceptions import UserError

from odoo.addons.l10n_be_codabox.const import get_error_msg


class L10nBeCodaBoxChangePasswordWizard(models.TransientModel):
    _name = 'l10n_be_codabox.change.password.wizard'
    _description = 'CodaBox Change Password Wizard'
    _check_company_auto = True

    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    current_fidu_password = fields.Char(
        string='Current password',
        help='This is the password you have received from Odoo the first time you connected to CodaBox.',
    )
    new_fidu_password = fields.Char(
        string='New Password',
        help='This is the password you want to set for the Codabox connection.',
    )
    confirm_fidu_password = fields.Char(
        string='Confirm New Password',
        help='Please confirm the new password you want to set for the Codabox connection.',
    )

    def l10n_be_codabox_change_password(self):
        self.ensure_one()
        if self.new_fidu_password != self.confirm_fidu_password:
            raise UserError(_('The new password and its confirmation do not match.'))
        params = self.company_id._l10n_be_codabox_get_iap_common_params()
        params["current_fidu_password"] = self.current_fidu_password
        params["new_fidu_password"] = self.new_fidu_password
        try:
            self.company_id._l10_be_codabox_call_iap_route("change_password", params)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise UserError(get_error_msg({"type": "error_connecting_iap"})) from None
        finally:
            self.current_fidu_password = False
            self.new_fidu_password = False
            self.confirm_fidu_password = False
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'title': _('Success'),
                'message': _('Password successfully changed.'),
                'next': {
                    'type': 'ir.actions.act_window_close'
                },
            }
        }
