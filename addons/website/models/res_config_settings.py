# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

from werkzeug import urls


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def _default_website(self):
        return self.env['website'].search([('company_id', '=', self.env.company.id)], limit=1)

    website_id = fields.Many2one(
        'website',
        string="website",
        default=_default_website, ondelete='cascade')
    website_name = fields.Char(
        'Website Name',
        related='website_id.name',
        readonly=False)
    website_domain = fields.Char(
        'Website Domain',
        related='website_id.domain',
        readonly=False)
    website_homepage_url = fields.Char(
        related='website_id.homepage_url', readonly=False)
    website_company_id = fields.Many2one(
        related='website_id.company_id',
        string='Website Company',
        readonly=False)
    website_logo = fields.Binary(
        related='website_id.logo',
        readonly=False)
    language_ids = fields.Many2many(
        related='website_id.language_ids',
        relation='res.lang',
        readonly=False)
    website_language_count = fields.Integer(
        string='Number of languages',
        related='website_id.language_count',
        readonly=True)
    website_default_lang_id = fields.Many2one(
        string='Default language',
        related='website_id.default_lang_id',
        readonly=False)
    website_default_lang_code = fields.Char(
        'Default language code',
        related='website_id.default_lang_id.code',
        readonly=False)
    shared_user_account = fields.Boolean(
        string="Shared Customer Accounts",
        compute='_compute_shared_user_account',
        inverse='_inverse_shared_user_account')
    website_cookies_bar = fields.Boolean(
        related='website_id.cookies_bar',
        readonly=False)
    google_analytics_key = fields.Char(
        'Google Analytics Key',
        related='website_id.google_analytics_key',
        readonly=False)
    google_search_console = fields.Char(
        'Google Search Console',
        related='website_id.google_search_console',
        readonly=False)
    plausible_shared_key = fields.Char(
        'Plausible auth Key',
        related='website_id.plausible_shared_key',
        readonly=False)
    plausible_site = fields.Char(
        'Plausible Site (e.g. domain.com)',
        related='website_id.plausible_site',
        readonly=False)
    cdn_activated = fields.Boolean(
        related='website_id.cdn_activated',
        readonly=False)
    cdn_url = fields.Char(
        related='website_id.cdn_url',
        readonly=False)
    cdn_filters = fields.Text(
        related='website_id.cdn_filters',
        readonly=False)
    auth_signup_uninvited = fields.Selection(
        compute="_compute_auth_signup_uninvited",
        inverse="_inverse_auth_signup_uninvited",
        # Remove any default value and let the compute handle it
        config_parameter=False, default=None)

    favicon = fields.Binary(
        'Favicon',
        related='website_id.favicon',
        readonly=False)
    social_default_image = fields.Binary(
        'Default Social Share Image',
        related='website_id.social_default_image',
        readonly=False)

    group_multi_website = fields.Boolean(
        "Multi-website",
        implied_group="website.group_multi_website")
    has_google_analytics = fields.Boolean(
        "Google Analytics",
        compute='_compute_has_google_analytics',
        inverse='_inverse_has_google_analytics')
    has_google_search_console = fields.Boolean(
        "Console Google Search",
        compute='_compute_has_google_search_console',
        inverse='_inverse_has_google_search_console')
    has_default_share_image = fields.Boolean(
        "Use a image by default for sharing",
        compute='_compute_has_default_share_image',
        inverse='_inverse_has_default_share_image')
    has_plausible_shared_key = fields.Boolean(
        "Plausible Analytics",
        compute='_compute_has_plausible_shared_key',
        inverse='_inverse_has_plausible_shared_key')
    module_website_livechat = fields.Boolean()
    module_marketing_automation = fields.Boolean()

    @api.depends('website_id')
    def _compute_shared_user_account(self):
        for config in self:
            config.shared_user_account = not config.website_id.specific_user_account

    @api.onchange('plausible_shared_key')
    def _onchange_shared_key(self):
        for config in self:
            value = config.plausible_shared_key
            if value and value.startswith('http'):
                try:
                    url = urls.url_parse(value)
                    config.plausible_shared_key = urls.url_decode(url.query).get('auth', '')
                    config.plausible_site = url.path.split('/')[-1]
                except Exception:  # noqa
                    pass

    def _inverse_shared_user_account(self):
        for config in self:
            config.website_id.specific_user_account = not config.shared_user_account

    @api.depends('website_id.auth_signup_uninvited')
    def _compute_auth_signup_uninvited(self):
        for config in self:
            # Default to `b2b` in case no website is set to avoid not being
            # able to save.
            config.auth_signup_uninvited = config.website_id.auth_signup_uninvited or 'b2b'

    def _inverse_auth_signup_uninvited(self):
        for config in self:
            config.website_id.auth_signup_uninvited = config.auth_signup_uninvited

    @api.depends('website_id')
    def _compute_has_plausible_shared_key(self):
        for config in self:
            config.has_plausible_shared_key = bool(config.plausible_shared_key)

    def _inverse_has_plausible_shared_key(self):
        for config in self:
            if config.has_plausible_shared_key:
                continue
            config.plausible_shared_key = False
            config.plausible_site = False

    @api.depends('website_id')
    def _compute_has_google_analytics(self):
        for config in self:
            config.has_google_analytics = bool(config.google_analytics_key)

    def _inverse_has_google_analytics(self):
        for config in self:
            if config.has_google_analytics:
                continue
            config.google_analytics_key = False

    @api.depends('website_id')
    def _compute_has_google_search_console(self):
        for config in self:
            config.has_google_search_console = bool(config.google_search_console)

    def _inverse_has_google_search_console(self):
        for config in self:
            if not config.has_google_search_console:
                config.google_search_console = False

    @api.depends('website_id')
    def _compute_has_default_share_image(self):
        for config in self:
            config.has_default_share_image = bool(config.social_default_image)

    def _inverse_has_default_share_image(self):
        for config in self:
            if not config.has_default_share_image:
                config.social_default_image = False

    @api.onchange('language_ids')
    def _onchange_language_ids(self):
        # If current default language is removed from language_ids
        # update the website_default_lang_id
        language_ids = self.language_ids._origin
        if not language_ids:
            self.website_default_lang_id = False
        elif self.website_default_lang_id not in language_ids:
            self.website_default_lang_id = language_ids[0]

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
        self.website_id._force()
        return {
            'name': _("Robots.txt"),
            'view_mode': 'form',
            'res_model': 'website.robots',
            'type': 'ir.actions.act_window',
            "views": [[False, "form"]],
            'target': 'new',
        }

    def action_ping_sitemap(self):
        if not self.website_id.domain:
            raise UserError(_("You haven't defined your domain"))

        return {
            'type': 'ir.actions.act_url',
            'url': 'http://www.google.com/ping?sitemap=%s/sitemap.xml' % self.website_id.domain,
            'target': 'new',
        }
