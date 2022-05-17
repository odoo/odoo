# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    microsoft_api_client_id = fields.Char(
        string="Microsoft API Client ID",
        config_parameter='microsoft_api_client_id',
        default=''
    )
    microsoft_api_client_secret = fields.Char(
        string="Microsoft API Client Secret",
        config_parameter='microsoft_api_client_secret',
        default=''
    )
