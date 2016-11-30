# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class WebsiteConfigSettings(models.TransientModel):

    _name = 'website.config.settings'
    _inherit = 'res.config.settings'

    def _default_website(self):
        return self.env['website'].search([], limit=1)

    website_id = fields.Many2one('website', string="website", default=_default_website, required=True)
    website_name = fields.Char('Website Name', related='website_id.name')

    language_ids = fields.Many2many(related='website_id.language_ids', relation='res.lang')
    default_lang_id = fields.Many2one(string='Language', related='website_id.default_lang_id', relation='res.lang')
    default_lang_code = fields.Char('Default language code', related='website_id.default_lang_code')
    google_analytics_key = fields.Char('Analytics Key', related='website_id.google_analytics_key')
    google_management_client_id = fields.Char('Client ID', related='website_id.google_management_client_id')
    google_management_client_secret = fields.Char('Client Secret', related='website_id.google_management_client_secret')

    social_twitter = fields.Char("Twitter", related='website_id.social_twitter')
    social_facebook = fields.Char("Facebook", related='website_id.social_facebook')
    social_github = fields.Char("GitHub", related='website_id.social_github')
    social_linkedin = fields.Char("LinkedIn", related='website_id.social_linkedin')
    social_youtube = fields.Char("Youtube", related='website_id.social_youtube')
    social_googleplus = fields.Char("Google+", related='website_id.social_googleplus')
    cdn_activated = fields.Boolean('Content Delivery Network (CDN)', related='website_id.cdn_activated')
    cdn_url = fields.Char(related='website_id.cdn_url')
    cdn_filters = fields.Text(related='website_id.cdn_filters')

    module_website_form_editor = fields.Boolean("Form Builder")
    module_website_version = fields.Boolean("A/B Testing")
    module_website_twitter = fields.Boolean("Twitter Roller")
    module_website_blog = fields.Boolean("Blogs")
    module_website_livechat = fields.Boolean("Live Chat")
    module_website_forum = fields.Boolean("Forum")
    module_website_crm = fields.Boolean("Contact Form")
    module_website_slides = fields.Boolean("Slides")
    module_website_hr_recruitment = fields.Boolean("Jobs")
    module_website_sale = fields.Boolean("eCommerce")
    module_website_contract = fields.Boolean("Subscriptions")
    module_website_event_sale = fields.Boolean("Event Tickets")

    favicon = fields.Binary('Favicon', related='website_id.favicon')

    # Set as global config parameter since methods using it are not website-aware. To be changed
    # when multi-website is implemented
    google_maps_api_key = fields.Char(string='API Key')

    def set_google_maps_api_key(self):
        self.env['ir.config_parameter'].set_param(
            'google_maps_api_key', (self.google_maps_api_key or '').strip(), groups=['base.group_system'])

    def get_default_google_maps_api_key(self, fields):
        google_maps_api_key = self.env['ir.config_parameter'].get_param('google_maps_api_key', default='')
        return dict(google_maps_api_key=google_maps_api_key)
