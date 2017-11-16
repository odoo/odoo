# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    website_slide_google_app_key = fields.Char(string='Google Doc Key', config_parameter='website_slides.google_app_key')
