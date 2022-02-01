# -*- coding: utf-8 -*-
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

    @api.onchange('auth_totp_enforce')
    def _onchange_auth_totp_enforce(self):
        if self.auth_totp_enforce:
            self.auth_totp_policy = 'employee_required'
        else:
            self.auth_totp_policy = False

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res['auth_totp_enforce'] = bool(self.env['ir.config_parameter'].sudo().get_param('auth_totp.policy'))
        return res
