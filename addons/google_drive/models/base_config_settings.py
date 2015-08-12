# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class BaseConfigSettings(models.TransientModel):
    _inherit = "base.config.settings"

    google_drive_authorization_code = fields.Char(string='Authorization Code',
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param('google_drive_authorization_code'))
    google_drive_uri = fields.Char(compute='_compute_drive_uri', string='URI', help="The URL to generate the authorization code from Google")

    # TODO: Currently, there is no way to calculate the correct dependencies as it is actully depended on the *data*
    # of the `key` field's value(i.e. google_drive_client_id, google_redirect_uri) of the model `ir.config_parameter`.
    @api.depends('google_drive_authorization_code')
    def _compute_drive_uri(self):
        google_drive_uri = self.env['google.service']._get_google_token_uri('drive', scope=self.env['google.drive.config'].get_google_scope())
        for config in self:
            config.google_drive_uri = google_drive_uri

    @api.multi
    def set_google_authorization_code(self):
        self.ensure_one()
        ICP = self.env['ir.config_parameter']
        if self.google_drive_authorization_code != ICP.get_param('google_drive_authorization_code'):
            refresh_token = self.env['google.service'].generate_refresh_token('drive', self.google_drive_authorization_code)
            ICP.set_param('google_drive_authorization_code', self.google_drive_authorization_code, groups=['base.group_system'])
            ICP.set_param('google_drive_refresh_token', refresh_token, groups=['base.group_system'])
