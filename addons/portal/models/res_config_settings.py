# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    portal_allow_api_keys = fields.Boolean(
        string='Customer API Keys',
        config_parameter='portal.allow_api_keys',
    )
