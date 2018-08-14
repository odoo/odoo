# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    clearbit_api_key = fields.Char("Clearbit API Key", config_parameter='clearbit.api_key')
