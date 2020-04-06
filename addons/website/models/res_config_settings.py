# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def _default_website(self):
        return self.env['website'].search([('company_id', '=', self.env.company.id)], limit=1)

    website_id = fields.Many2one('website', string="website",
                                 default=_default_website, ondelete='cascade')
    website_name = fields.Char('Website Name', related='website_id.name', readonly=False)
    website_domain = fields.Char('Website Domain', related='website_id.domain', readonly=False)
    website_country_group_ids = fields.Many2many(related='website_id.country_group_ids', readonly=False)
    website_company_id = fields.Many2one(related='website_id.company_id', string='Website Company', readonly=False)
    website_logo = fields.Binary(related='website_id.logo', readonly=False)
    language_ids = fields.Many2many(related='website_id.language_ids', relation='res.lang', readonly=False)
    website_language_count = fields.Integer(string='Number of languages', compute='_compute_website_language_count', readonly=True)
    website_default_lang_id = fields.Many2one(string='Default language', related='website_id.default_lang_id',
                                              readonly=False, relation='res.lang')
    website_default_lang_code = fields.Char('Default language code', related='website_id.default_lang_id.code', readonly=False)
    specific_user_account = fields.Boolean(related='website_id.specific_user_account', readonly=False,
                                           help='Are newly created user accounts website specific')

    google_analytics_key = fields.Char('Google Analytics Key', compute="_compute_google_analytics_key", store=True, readonly=False)
    google_management_client_id = fields.Char('Google Client ID', compute="_compute_google_management_client_id", store=True, readonly=False)
    google_management_client_secret = fields.Char('Google Client Secret', compute="_compute_google_management_client_secret", store=True, readonly=False)

    @api.depends('website_id')
    def _compute_google_analytics_key(self):
        self.google_analytics_key = self.website_id.google_analytics_key

    @api.depends('website_id')
    def _compute_google_management_client_id(self):
        self.google_management_client_id = self.website_id.google_management_client_id

    @api.depends('website_id')
    def _compute_google_management_client_secret(self):
        self.google_management_client_secret = self.website_id.google_management_client_secret

    cdn_activated = fields.Boolean(related='website_id.cdn_activated', readonly=False)
    cdn_url = fields.Char(related='website_id.cdn_url', readonly=False)
    cdn_filters = fields.Text(related='website_id.cdn_filters', readonly=False)
    module_website_version = fields.Boolean("A/B Testing")
    module_website_links = fields.Boolean("Link Trackers")
    auth_signup_uninvited = fields.Selection(compute="_compute_auth_signup",
        inverse="_set_auth_signup")

    social_twitter = fields.Char(compute="_compute_social_twitter", store=True, readonly=False)
    social_facebook = fields.Char(compute="_compute_social_facebook", store=True, readonly=False)
    social_github = fields.Char(compute="_compute_social_github", store=True, readonly=False)
    social_linkedin = fields.Char(compute="_compute_social_linkedin", store=True, readonly=False)
    social_youtube = fields.Char(compute="_compute_social_youtube", store=True, readonly=False)
    social_instagram = fields.Char(compute="_compute_social_instagram", store=True, readonly=False)

    @api.depends('website_id')
    def _compute_social_twitter(self):
        self.social_twitter = self.website_id.social_twitter

    @api.depends('website_id')
    def _compute_social_facebook(self):
        self.social_facebook = self.website_id.social_facebook

    @api.depends('website_id')
    def _compute_social_github(self):
        self.social_github = self.website_id.social_github

    @api.depends('website_id')
    def _compute_social_linkedin(self):
        self.social_linkedin = self.website_id.social_linkedin

    @api.depends('website_id')
    def _compute_social_youtube(self):
        self.social_youtube = self.website_id.social_youtube

    @api.depends('website_id')
    def _compute_social_instagram(self):
        self.social_instagram = self.website_id.social_instagram

    @api.depends('website_id', 'social_twitter', 'social_facebook', 'social_github', 'social_linkedin', 'social_youtube', 'social_instagram')
    def _compute_has_social_network(self):
        self.has_social_network = self.social_twitter or self.social_facebook or self.social_github \
            or self.social_linkedin or self.social_youtube or self.social_instagram

    has_social_network = fields.Boolean("Configure Social Network", compute='_compute_has_social_network', store=True, readonly=False)

    favicon = fields.Binary('Favicon', related='website_id.favicon', readonly=False)
    social_default_image = fields.Binary('Default Social Share Image', related='website_id.social_default_image', readonly=False)

    google_maps_api_key = fields.Char(compute="_compute_google_maps_api_key", store=True, readonly=False)
    group_multi_website = fields.Boolean("Multi-website", implied_group="website.group_multi_website")

    @api.depends('website_id')
    def _compute_google_maps_api_key(self):
        self.google_maps_api_key = self.website_id.google_maps_api_key

    @api.depends('website_id.auth_signup_uninvited')
    def _compute_auth_signup(self):
        for config in self:
            config.auth_signup_uninvited = config.website_id.auth_signup_uninvited

    def _set_auth_signup(self):
        for config in self:
            config.website_id.auth_signup_uninvited = config.auth_signup_uninvited

    @api.depends('website_id')
    def _compute_has_google_analytics(self):
        self.has_google_analytics = bool(self.google_analytics_key)

    @api.depends('website_id')
    def _compute_has_google_analytics_dashboard(self):
        self.has_google_analytics_dashboard = bool(self.google_management_client_id)

    @api.depends('website_id')
    def _compute_has_google_maps(self):
        self.has_google_maps = bool(self.google_maps_api_key)

    has_google_analytics = fields.Boolean("Google Analytics", compute='_compute_has_google_analytics', store=True, readonly=False)
    has_google_analytics_dashboard = fields.Boolean("Google Analytics Dashboard", compute='_compute_has_google_analytics_dashboard', store=True, readonly=False)
    has_google_maps = fields.Boolean("Google Maps", compute='_compute_has_google_maps', store=True, readonly=False)

    @api.onchange('language_ids')
    def _onchange_language_ids(self):
        # If current default language is removed from language_ids
        # update the website_default_lang_id
        language_ids = self.language_ids._origin
        if not language_ids:
            self.website_default_lang_id = False
        elif self.website_default_lang_id not in language_ids:
            self.website_default_lang_id = language_ids[0]

    @api.depends('language_ids')
    def _compute_website_language_count(self):
        for config in self:
            config.website_language_count = len(self.language_ids)

    def set_values(self):
        super().set_values()
        if not self.has_social_network:
            self.social_twitter = ''
            self.social_facebook = ''
            self.social_github = ''
            self.social_linkedin = ''
            self.social_youtube = ''
            self.social_instagram = ''
        self.website_id.social_twitter = self.social_twitter
        self.website_id.social_facebook = self.social_facebook
        self.website_id.social_github = self.social_github
        self.website_id.social_linkedin = self.social_linkedin
        self.website_id.social_youtube = self.social_youtube
        self.website_id.social_instagram = self.social_instagram

        if not self.has_google_analytics:
            self.has_google_analytics_dashboard = False
            self.google_analytics_key = False
        self.website_id.has_google_analytics_dashboard = self.has_google_analytics_dashboard
        self.website_id.google_analytics_key = self.google_analytics_key

        if not self.has_google_maps:
            self.google_maps_api_key = False
        self.website_id.google_maps_api_key = self.google_maps_api_key

        if not self.has_google_analytics_dashboard:
            self.google_management_client_id = False
            self.google_management_client_secret = False
        self.website_id.google_management_client_id = self.google_management_client_id
        self.website_id.google_management_client_secret = self.google_management_client_secret
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
            'view_mode': 'form',
            'view_id': self.env.ref('website.view_website_form').id,
            'res_model': 'website',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': False,
        }
