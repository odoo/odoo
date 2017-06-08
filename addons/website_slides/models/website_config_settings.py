# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class website_config_settings(models.TransientModel):

    _inherit = "website.config.settings"

    website_slide_google_app_key = fields.Char(string='Google Doc Key')

    @api.model
    def get_default_website_slide_google_app_key(self, fields):
        website_slide_google_app_key = False
        if 'website_slide_google_app_key' in fields:
            website_slide_google_app_key = self.env['ir.config_parameter'].sudo().get_param('website_slides.google_app_key')
        return {
            'website_slide_google_app_key': website_slide_google_app_key
        }

    @api.multi
    def set_website_slide_google_app_key(self):
        for wizard in self:
            self.env['ir.config_parameter'].sudo().set_param('website_slides.google_app_key', wizard.website_slide_google_app_key)
