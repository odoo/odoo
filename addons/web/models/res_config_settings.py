# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    web_app_name = fields.Char('Web App Name', config_parameter='web.web_app_name')
    web_app_short_name = fields.Char('Web App Short Name', config_parameter='web.web_app_short_name')
    web_app_background_color = fields.Char('Web App Background Color', config_parameter='web.web_app_background_color')
    web_app_theme_color = fields.Char('Web App Theme Color', config_parameter='web.web_app_theme_color')
