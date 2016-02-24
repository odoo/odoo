# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.import copy
from odoo import fields, models

class WebsiteConfigSettings(models.TransientModel):
    _name = 'website.config.settings'
    _inherit = 'res.config.settings'

    def default_website(self):
        return self.env['website'].search([], limit=1).id

    website_id = fields.Many2one('website', string="website", default=default_website, required=True)
    website_name = fields.Char(related='website_id.name')

    language_ids = fields.Many2many(related='website_id.language_ids', relation='res.lang')
    default_lang_id = fields.Many2one(related='website_id.default_lang_id', relation='res.lang')
    default_lang_code = fields.Char(related='website_id.default_lang_code')
    google_analytics_key = fields.Char(related='website_id.google_analytics_key')

    social_twitter = fields.Char(related='website_id.social_twitter')
    social_facebook = fields.Char(related='website_id.social_facebook')
    social_github = fields.Char(related='website_id.social_github')
    social_linkedin = fields.Char(related='website_id.social_linkedin')
    social_youtube = fields.Char(related='website_id.social_youtube')
    social_googleplus = fields.Char(related='website_id.social_googleplus')
    compress_html = fields.Boolean(related='website_id.compress_html', string='Compress rendered HTML for a better Google PageSpeed result')
    cdn_activated = fields.Boolean(related='website_id.cdn_activated', string='Use a Content Delivery Network (CDN)')
    cdn_url = fields.Char(related='website_id.cdn_url')
    cdn_filters = fields.Text(related='website_id.cdn_filters')
    module_website_form_editor = fields.Boolean("Form builde = create and customize forms")
    module_website_version = fields.Boolean("A/B testing and versioning")
    favicon = fields.Binary(related='website_id.favicon', string="Favicon")
