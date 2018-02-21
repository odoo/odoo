# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class BaseConfigSettings(models.TransientModel):
    _inherit = 'base.config.settings'

    @api.model
    def get_uri(self):
        return "%s/auth_oauth/signin" % (self.env['ir.config_parameter'].get_param('web.base.url'))

    def _compute_server_uri(self):
        uri = self.get_uri()
        for setting in self:
            setting.server_uri_google = uri

    auth_oauth_google_enabled = fields.Boolean(string='Allow users to sign in with Google')
    auth_oauth_google_client_id = fields.Char(string='Client ID')
    server_uri_google = fields.Char(compute='_compute_server_uri', string='Server uri')
    auth_oauth_tutorial_enabled = fields.Boolean(string='Show tutorial')

    @api.model
    def default_get(self, fields):
        settings = super(BaseConfigSettings, self).default_get(fields)
        settings.update(self.get_oauth_providers(fields))
        return settings

    @api.model
    def get_oauth_providers(self, fields):
        google_provider = self.env.ref('auth_oauth.provider_google', False)
        return {
            'auth_oauth_google_enabled': google_provider.enabled,
            'auth_oauth_google_client_id': google_provider.client_id,
            'server_uri_google': self.get_uri()
        }

    @api.multi
    def set_oauth_providers(self):
        self.ensure_one()
        google_provider = self.env.ref('auth_oauth.provider_google', False)
        rg = {
            'enabled': self.auth_oauth_google_enabled,
            'client_id': self.auth_oauth_google_client_id,
        }
        google_provider.write(rg)
