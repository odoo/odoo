# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, fields, models
from odoo.exceptions import AccessDenied


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def _default_website(self):
        return self.env['website'].search([], limit=1)

    website_id = fields.Many2one('website', string="website",
                                 default=_default_website, ondelete='cascade')
    website_name = fields.Char('Website Name', related='website_id.name', readonly=False)
    website_domain = fields.Char('Website Domain', related='website_id.domain', readonly=False)
    website_country_group_ids = fields.Many2many(related='website_id.country_group_ids', readonly=False)
    website_company_id = fields.Many2one(related='website_id.company_id', string='Website Company', readonly=False)
    language_ids = fields.Many2many(related='website_id.language_ids', relation='res.lang', readonly=False)
    language_count = fields.Integer(string='Number of languages', compute='_compute_language_count', readonly=True)
    website_default_lang_id = fields.Many2one(
        string='Default language', related='website_id.default_lang_id', readonly=False,
        relation='res.lang', required=True,
        oldname='default_lang_id')
    website_default_lang_code = fields.Char(
        'Default language code', related='website_id.default_lang_code', readonly=False,
        oldname='default_lang_code')
    specific_user_account = fields.Boolean(related='website_id.specific_user_account', readonly=False,
                                           help='Are newly created user accounts website specific')

    google_analytics_key = fields.Char('Google Analytics Key', related='website_id.google_analytics_key', readonly=False)
    google_management_client_id = fields.Char('Google Client ID', related='website_id.google_management_client_id', readonly=False)
    google_management_client_secret = fields.Char('Google Client Secret', related='website_id.google_management_client_secret', readonly=False)

    cdn_activated = fields.Boolean(related='website_id.cdn_activated', readonly=False)
    cdn_url = fields.Char(related='website_id.cdn_url', readonly=False)
    cdn_filters = fields.Text(related='website_id.cdn_filters', readonly=False)
    module_website_version = fields.Boolean("A/B Testing")
    module_website_links = fields.Boolean("Link Trackers")
    auth_signup_uninvited = fields.Selection("Customer Account", related='website_id.auth_signup_uninvited', readonly=False)

    social_twitter = fields.Char(related='website_id.social_twitter', readonly=False)
    social_facebook = fields.Char(related='website_id.social_facebook', readonly=False)
    social_github = fields.Char(related='website_id.social_github', readonly=False)
    social_linkedin = fields.Char(related='website_id.social_linkedin', readonly=False)
    social_youtube = fields.Char(related='website_id.social_youtube', readonly=False)
    social_googleplus = fields.Char(related='website_id.social_googleplus', readonly=False)
    social_instagram = fields.Char(related='website_id.social_instagram', readonly=False)

    @api.depends('website_id', 'social_twitter', 'social_facebook', 'social_github', 'social_linkedin', 'social_youtube', 'social_googleplus', 'social_instagram')
    def has_social_network(self):
        self.has_social_network = self.social_twitter or self.social_facebook or self.social_github \
            or self.social_linkedin or self.social_youtube or self.social_googleplus or self.social_instagram

    def inverse_has_social_network(self):
        if not self.has_social_network:
            self.social_twitter = ''
            self.social_facebook = ''
            self.social_github = ''
            self.social_linkedin = ''
            self.social_youtube = ''
            self.social_googleplus = ''
            self.social_instagram = ''

    has_social_network = fields.Boolean("Configure Social Network", compute=has_social_network, inverse=inverse_has_social_network)

    favicon = fields.Binary('Favicon', related='website_id.favicon', readonly=False)
    social_default_image = fields.Binary('Default Social Share Image', related='website_id.social_default_image', readonly=False)

    google_maps_api_key = fields.Char(related='website_id.google_maps_api_key', readonly=False)
    group_multi_website = fields.Boolean("Multi-website", implied_group="website.group_multi_website")

    @api.depends('website_id')
    def has_google_analytics(self):
        self.has_google_analytics = bool(self.google_analytics_key)

    @api.depends('website_id')
    def has_google_analytics_dashboard(self):
        self.has_google_analytics_dashboard = bool(self.google_management_client_id)

    @api.depends('website_id')
    def has_google_maps(self):
        self.has_google_maps = bool(self.google_maps_api_key)

    def inverse_has_google_analytics(self):
        if not self.has_google_analytics:
            self.has_google_analytics_dashboard = False
            self.google_analytics_key = False

    def inverse_has_google_maps(self):
        if not self.has_google_maps:
            self.google_maps_api_key = False

    def inverse_has_google_analytics_dashboard(self):
        if not self.has_google_analytics_dashboard:
            self.google_management_client_id = False
            self.google_management_client_secret = False

    has_google_analytics = fields.Boolean("Google Analytics", compute=has_google_analytics, inverse=inverse_has_google_analytics)
    has_google_analytics_dashboard = fields.Boolean("Google Analytics Dashboard", compute=has_google_analytics_dashboard, inverse=inverse_has_google_analytics_dashboard)
    has_google_maps = fields.Boolean("Google Maps", compute=has_google_maps, inverse=inverse_has_google_maps)

    @api.onchange('language_ids')
    def _onchange_language_ids(self):
        # If current default language is removed from language_ids
        # update the website_default_lang_id
        if self.language_ids and self.website_default_lang_id not in self.language_ids:
            self.website_default_lang_id = self.language_ids[0]

    @api.depends('language_ids')
    def _compute_language_count(self):
        for config in self:
            config.language_count = len(self.language_ids)

    def set_values(self):
        super(ResConfigSettings, self).set_values()

    @api.multi
    def open_template_user(self):
        action = self.env.ref('base.action_res_users').read()[0]
        action['res_id'] = literal_eval(self.env['ir.config_parameter'].sudo().get_param('base.template_portal_user_id', 'False'))
        action['views'] = [[self.env.ref('base.view_users_form').id, 'form']]
        return action

    def website_go_to(self):
        self.website_id._force()
        return {
            'type': 'ir.actions.act_url',
            'url': '/',
            'target': 'self',
        }

    def action_website_create_new(self):
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('website.view_website_form').id,
            'res_model': 'website',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': False,
        }
