# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

from werkzeug.urls import url_encode, url_join


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    google_drive_authorization_code = fields.Char(string='Authorization Code', config_parameter='google_drive_authorization_code')  # TODO remove in master
    google_drive_uri = fields.Char(compute='_compute_drive_uri', string='URI', help="The URL to generate the authorization code from Google")  # TODO remove in master
    is_google_drive_token_generated = fields.Boolean(string='Refresh Token Generated')

    @api.depends('google_drive_authorization_code')
    def _compute_drive_uri(self):
        self.google_drive_uri = False

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        refresh_token = self.env['ir.config_parameter'].sudo().get_param('google_drive_refresh_token', False)
        res.update(is_google_drive_token_generated=bool(refresh_token))
        return res

    def confirm_setup_token(self):  # TODO remove in master
        pass

    def action_setup_token(self):
        ConfigParam = self.env['ir.config_parameter'].sudo()
        base_url = ConfigParam.get_param('web.base.url')
        client_id = ConfigParam.get_param('google_drive_client_id')
        redirect_uri = url_join(base_url, '/google_drive/confirm')

        scope = self.env['google.drive.config'].get_google_scope()
        auth_url = 'https://accounts.google.com/o/oauth2/v2/auth?%s' % url_encode({
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'access_type': 'offline',
            'prompt': 'consent',
            'scope': scope,
        })

        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': auth_url,
        }
