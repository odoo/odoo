# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    recaptcha_public_key = fields.Char("Site Key", config_parameter='recaptcha_public_key', groups='base.group_system')
    recaptcha_private_key = fields.Char("Secret Key", config_parameter='recaptcha_private_key', groups='base.group_system')
    recaptcha_min_score = fields.Float(
        "Minimum score",
        config_parameter='recaptcha_min_score',
        groups='base.group_system',
        default="0.5",
        help="Should be between 0.0 and 1.0.\n1.0 is very likely a good interaction, 0.0 is very likely a bot"
    )
