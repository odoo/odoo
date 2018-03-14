# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, fields, models
from odoo.exceptions import AccessDenied


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def _default_website(self):
        return self.env['website'].search([], limit=1)

    # FIXME: Set website_id to ondelete='cascade' in master
    website_id = fields.Many2one('website', string="website", default=_default_website, required=True)
    website_name = fields.Char('Website Name', related='website_id.name')
    language_ids = fields.Many2many(related='website_id.language_ids', relation='res.lang')
    language_count = fields.Integer(string='Number of languages', compute='_compute_language_count', readonly=True)
    website_default_lang_id = fields.Many2one(
        string='Default language', related='website_id.default_lang_id',
        relation='res.lang', required=True,
        oldname='default_lang_id')
    website_default_lang_code = fields.Char(
        'Default language code', related='website_id.default_lang_code',
        oldname='default_lang_code')
    google_analytics_key = fields.Char('Google Analytics Key', related='website_id.google_analytics_key')
    google_management_client_id = fields.Char('Google Client ID', related='website_id.google_management_client_id')
    google_management_client_secret = fields.Char('Google Client Secret', related='website_id.google_management_client_secret')

    cdn_activated = fields.Boolean('Use a Content Delivery Network (CDN)', related='website_id.cdn_activated')
    cdn_url = fields.Char(related='website_id.cdn_url')
    cdn_filters = fields.Text(related='website_id.cdn_filters')
    module_website_version = fields.Boolean("A/B Testing")
    module_website_links = fields.Boolean(string="Link Trackers")

    favicon = fields.Binary('Favicon', related='website_id.favicon')
    # Set as global config parameter since methods using it are not website-aware. To be changed
    # when multi-website is implemented
    google_maps_api_key = fields.Char(string='Google Maps API Key', config_parameter='google_maps_api_key', default='')
    has_google_analytics = fields.Boolean("Google Analytics", config_parameter='website.has_google_analytics')
    has_google_analytics_dashboard = fields.Boolean("Google Analytics in Dashboard", config_parameter='website.has_google_analytics_dashboard')
    has_google_maps = fields.Boolean("Google Maps", config_parameter='website.has_google_maps')
    auth_signup_uninvited = fields.Selection([
        ('b2b', 'On invitation (B2B)'),
        ('b2c', 'Free sign up (B2C)'),
    ], string='Customer Account', default='b2b', config_parameter='auth_signup.invitation_scope')

    @api.onchange('has_google_analytics')
    def onchange_has_google_analytics(self):
        if not self.has_google_analytics:
            self.has_google_analytics_dashboard = False
        if not self.has_google_analytics:
            self.google_analytics_key = False

    @api.onchange('has_google_analytics_dashboard')
    def onchange_has_google_analytics_dashboard(self):
        if not self.has_google_analytics_dashboard:
            self.google_management_client_id = False
            self.google_management_client_secret = False

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
        if not self.user_has_groups('website.group_website_designer'):
            raise AccessDenied()
        super(ResConfigSettings, self).set_values()

    @api.multi
    def open_template_user(self):
        action = self.env.ref('base.action_res_users').read()[0]
        action['res_id'] = literal_eval(self.env['ir.config_parameter'].sudo().get_param('auth_signup.template_user_id', 'False'))
        action['views'] = [[self.env.ref('base.view_users_form').id, 'form']]
        return action
