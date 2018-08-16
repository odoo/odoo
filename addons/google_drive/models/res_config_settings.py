# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    google_drive_authorization_code = fields.Char(string='Authorization Code', config_parameter='google_drive_authorization_code')
    google_drive_uri = fields.Char(compute='_compute_drive_uri', string='URI', help="The URL to generate the authorization code from Google")

    @api.depends('google_drive_authorization_code')
    def _compute_drive_uri(self):
        google_drive_uri = self.env['google.service']._get_google_token_uri('drive', scope=self.env['google.drive.config'].get_google_scope())
        for config in self:
            config.google_drive_uri = google_drive_uri

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        params = self.env['ir.config_parameter'].sudo()
        authorization_code = self.google_drive_authorization_code
        refresh_token = False
        if authorization_code and authorization_code != params.get_param('google_drive_authorization_code'):
            refresh_token = self.env['google.service'].generate_refresh_token('drive', authorization_code)
        params.set_param('google_drive_refresh_token', refresh_token)
