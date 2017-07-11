# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class WebsiteConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    website_slide_google_app_key = fields.Char(string='Google Doc Key')

    @api.model
    def get_values(self):
        res = super(WebsiteConfigSettings, self).get_values()
        res.update(
            website_slide_google_app_key=self.env['ir.config_parameter'].sudo().get_param('website_slides.google_app_key'),
        )
        return res

    @api.multi
    def set_values(self):
        super(WebsiteConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('website_slides.google_app_key', self.website_slide_google_app_key)
