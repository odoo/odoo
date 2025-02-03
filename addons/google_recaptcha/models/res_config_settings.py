# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.tools.misc import str2bool


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_recaptcha = fields.Boolean("Enable reCAPTCHA", config_parameter='enable_recaptcha', groups='base.group_system')
    recaptcha_public_key = fields.Char("Site Key", config_parameter='recaptcha_public_key', groups='base.group_system')
    recaptcha_private_key = fields.Char("Secret Key", config_parameter='recaptcha_private_key', groups='base.group_system')
    recaptcha_min_score = fields.Float(
        "Minimum score",
        config_parameter='recaptcha_min_score',
        groups='base.group_system',
        default="0.7",
        help="By default, should be one of 0.1, 0.3, 0.7, 0.9.\n1.0 is very likely a good interaction, 0.0 is very likely a bot"
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        icp = self.env['ir.config_parameter'].sudo()
        res['enable_recaptcha'] = str2bool(icp.get_param('enable_recaptcha', default=True))
        return res

    def set_values(self):
        super().set_values()
        icp = self.env['ir.config_parameter'].sudo()
        icp.set_param("enable_recaptcha", str(self.enable_recaptcha))
