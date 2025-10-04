# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    turnstile_site_key = fields.Char("CF Site Key", config_parameter='cf.turnstile_site_key', groups='base.group_system')
    turnstile_secret_key = fields.Char("CF Secret Key", config_parameter='cf.turnstile_secret_key', groups='base.group_system')
