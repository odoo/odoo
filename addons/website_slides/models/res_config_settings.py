# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    website_slide_google_app_key = fields.Char(related='website_id.website_slide_google_app_key', readonly=False)
    module_website_sale_slides = fields.Boolean(string="Sell on eCommerce")
    module_website_slides_forum = fields.Boolean(string="Forum")
    module_website_slides_survey = fields.Boolean(string="Certifications")
    module_mass_mailing_slides = fields.Boolean(string="Mailing")
