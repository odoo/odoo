# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    youtube_use_own_account = fields.Boolean("Use your own YouTube Account", config_parameter='social.youtube_use_own_account')
    youtube_oauth_client_id = fields.Char("YouTube OAuth Client ID",
        compute='_compute_youtube_oauth_client_id', inverse='_inverse_youtube_oauth_client_id')
    youtube_oauth_client_secret = fields.Char("YouTube OAuth Client Secret",
        compute='_compute_youtube_oauth_client_secret', inverse='_inverse_youtube_oauth_client_secret')

    @api.depends('youtube_use_own_account')
    def _compute_youtube_oauth_client_id(self):
        for record in self:
            if self.env.user.has_group('social.group_social_manager') and self.youtube_use_own_account:
                record.youtube_oauth_client_id = self.env['ir.config_parameter'].sudo().get_param('social.youtube_oauth_client_id')
            else:
                record.youtube_oauth_client_id = None

    def _inverse_youtube_oauth_client_id(self):
        for record in self:
            if self.env.user.has_group('social.group_social_manager') and self.youtube_use_own_account:
                self.env['ir.config_parameter'].sudo().set_param('social.youtube_oauth_client_id', record.youtube_oauth_client_id)
            elif self.env.user.has_group('social.group_social_manager'):
                self.env['ir.config_parameter'].sudo().set_param('social.youtube_oauth_client_id', '')

    @api.depends('youtube_use_own_account')
    def _compute_youtube_oauth_client_secret(self):
        for record in self:
            if self.env.user.has_group('social.group_social_manager') and self.youtube_use_own_account:
                record.youtube_oauth_client_secret = self.env['ir.config_parameter'].sudo().get_param('social.youtube_oauth_client_secret')
            else:
                record.youtube_oauth_client_secret = None

    def _inverse_youtube_oauth_client_secret(self):
        for record in self:
            if self.env.user.has_group('social.group_social_manager') and self.youtube_use_own_account:
                self.env['ir.config_parameter'].sudo().set_param('social.youtube_oauth_client_secret', record.youtube_oauth_client_secret)
            elif self.env.user.has_group('social.group_social_manager'):
                self.env['ir.config_parameter'].sudo().set_param('social.youtube_oauth_client_secret', '')
