# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.model
    def get_uri(self):
        return "%s/auth_oauth/signin" % (self.env['ir.config_parameter'].get_param('web.base.url'))

    auth_oauth_google_enabled = fields.Boolean(string='Allow users to sign in with Google')
    auth_oauth_google_client_id = fields.Char(string='Client ID')
    server_uri_google = fields.Char(string='Server uri')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        google_provider = self.env.ref('auth_oauth.provider_google', False)
        google_provider and res.update(
            auth_oauth_google_enabled=google_provider.enabled,
            auth_oauth_google_client_id=google_provider.client_id,
            server_uri_google=self.get_uri(),
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        google_provider = self.env.ref('auth_oauth.provider_google', False)
        google_provider and google_provider.write({
            'enabled': self.auth_oauth_google_enabled,
            'client_id': self.auth_oauth_google_client_id,
        })
