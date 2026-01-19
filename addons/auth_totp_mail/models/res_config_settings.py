# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    auth_totp_enforce = fields.Boolean(
        string="Enforce two-factor authentication",
    )
    auth_totp_policy = fields.Selection([
        ('employee_required', 'Employees only'),
        ('all_required', 'All users')
    ],
        string="Two-factor authentication enforcing policy",
        config_parameter='auth_totp.policy',
    )
    auth_totp_grace_days = fields.Integer(
        string='2FA enforcing grace days',
        help="Allow for new users to have a grace period before enforcing 2FA",
        config_parameter='auth_totp.mfa_grace_days',
    )

    @api.onchange('auth_totp_enforce')
    def _onchange_auth_totp_enforce(self):
        if self.auth_totp_enforce:
            self.auth_totp_policy = self.auth_totp_policy or 'employee_required'
        else:
            self.auth_totp_policy = False

    @api.model
    def get_values(self):
        res = super().get_values()
        res['auth_totp_enforce'] = bool(self.env['ir.config_parameter'].sudo().get_str('auth_totp.policy'))
        return res
