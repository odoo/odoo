# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


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
    website_cookies_bar = fields.Boolean(related='website_id.cookies_bar', readonly=False)

    google_analytics_key = fields.Char('Google Analytics Key', related='website_id.google_analytics_key', readonly=False)
    google_management_client_id = fields.Char('Google Client ID', related='website_id.google_management_client_id', readonly=False)
    google_management_client_secret = fields.Char('Google Client Secret', related='website_id.google_management_client_secret', readonly=False)
    google_search_console = fields.Char('Google Search Console', related='website_id.google_search_console', readonly=False)

    cdn_activated = fields.Boolean(related='website_id.cdn_activated', readonly=False)
    cdn_url = fields.Char(related='website_id.cdn_url', readonly=False)
    cdn_filters = fields.Text(related='website_id.cdn_filters', readonly=False)
    auth_signup_uninvited = fields.Selection(compute="_compute_auth_signup", inverse="_set_auth_signup")

    social_twitter = fields.Char(related='website_id.social_twitter', readonly=False)
    social_facebook = fields.Char(related='website_id.social_facebook', readonly=False)
    social_github = fields.Char(related='website_id.social_github', readonly=False)
    social_linkedin = fields.Char(related='website_id.social_linkedin', readonly=False)
    social_youtube = fields.Char(related='website_id.social_youtube', readonly=False)
    social_instagram = fields.Char(related='website_id.social_instagram', readonly=False)

    @api.depends('website_id', 'social_twitter', 'social_facebook', 'social_github', 'social_linkedin', 'social_youtube', 'social_instagram')
    def has_social_network(self):
        self.has_social_network = self.social_twitter or self.social_facebook or self.social_github \
            or self.social_linkedin or self.social_youtube or self.social_instagram

    def inverse_has_social_network(self):
        if not self.has_social_network:
            self.social_twitter = ''
            self.social_facebook = ''
            self.social_github = ''
            self.social_linkedin = ''
            self.social_youtube = ''
            self.social_instagram = ''

    has_social_network = fields.Boolean("Configure Social Network", compute=has_social_network, inverse=inverse_has_social_network)

    favicon = fields.Binary('Favicon', related='website_id.favicon', readonly=False)
    social_default_image = fields.Binary('Default Social Share Image', related='website_id.social_default_image', readonly=False)

    google_maps_api_key = fields.Char(related='website_id.google_maps_api_key', readonly=False)
    group_multi_website = fields.Boolean("Multi-website", implied_group="website.group_multi_website")

    @api.depends('website_id.auth_signup_uninvited')
    def _compute_auth_signup(self):
        for config in self:
            config.auth_signup_uninvited = config.website_id.auth_signup_uninvited

    def _set_auth_signup(self):
        for config in self:
            config.website_id.auth_signup_uninvited = config.auth_signup_uninvited

    @api.depends('website_id')
    def has_google_analytics(self):
        self.has_google_analytics = bool(self.google_analytics_key)

    @api.depends('website_id')
    def has_google_analytics_dashboard(self):
        self.has_google_analytics_dashboard = bool(self.google_management_client_id)

    @api.depends('website_id')
    def has_google_maps(self):
        self.has_google_maps = bool(self.google_maps_api_key)

    @api.depends('website_id')
    def has_default_share_image(self):
        self.has_default_share_image = bool(self.social_default_image)

    @api.depends('website_id')
    def has_google_search_console(self):
        self.has_google_search_console = bool(self.google_search_console)

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

    def inverse_has_google_search_console(self):
        if not self.has_google_search_console:
            self.google_search_console = False

    def inverse_has_default_share_image(self):
        if not self.has_default_share_image:
            self.social_default_image = False

    has_google_analytics = fields.Boolean("Google Analytics", compute=has_google_analytics, inverse=inverse_has_google_analytics)
    has_google_analytics_dashboard = fields.Boolean("Google Analytics Dashboard", compute=has_google_analytics_dashboard, inverse=inverse_has_google_analytics_dashboard)
    has_google_maps = fields.Boolean("Google Maps", compute=has_google_maps, inverse=inverse_has_google_maps)
    has_google_search_console = fields.Boolean("Console Google Search", compute=has_google_search_console, inverse=inverse_has_google_search_console)
    has_default_share_image = fields.Boolean("Use a image by default for sharing", compute=has_default_share_image, inverse=inverse_has_default_share_image)

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
        super(ResConfigSettings, self).set_values()

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
            'view_id': self.env.ref('website.view_website_form_view_themes_modal').id,
            'res_model': 'website',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': False,
        }

    def action_open_robots(self):
        return {
            'name': _("Robots.txt"),
            'view_mode': 'form',
            'res_model': 'website.robots',
            'type': 'ir.actions.act_window',
            "views": [[False, "form"]],
            'target': 'new',
        }

    def action_ping_sitemap(self):
        if not self.website_id._get_http_domain():
            raise UserError(_("You haven't defined your domain"))

        return {
            'type': 'ir.actions.act_url',
            'url': 'http://www.google.com/ping?sitemap=%s/sitemap.xml' % self.website_id._get_http_domain(),
            'target': 'new',
        }

    def install_theme_on_current_website(self):
        self.website_id._force()
        action = self.env.ref('website.theme_install_kanban_action').read()[0]
        action['target'] = 'main'
        return action
