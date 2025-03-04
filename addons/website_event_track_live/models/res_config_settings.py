# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    youtube_live_stream_enable = fields.Boolean("Enable YouTube Live Scheduling", compute='_compute_youtube_live_stream_enable')
    youtube_oauth_client_id = fields.Char("YouTube OAuth Client ID",
        compute='_compute_youtube_oauth_client_id', inverse='_inverse_youtube_oauth_client_id')
    youtube_oauth_client_secret = fields.Char("YouTube OAuth Client Secret",
        compute='_compute_youtube_oauth_client_secret', inverse='_inverse_youtube_oauth_client_secret')

    @api.depends('module_website_event_track_live')
    def _compute_youtube_live_stream_enable(self):
        for record in self:
            record.youtube_live_stream_enable = record.module_website_event_track_live

    @api.depends('youtube_live_stream_enable')
    def _compute_youtube_oauth_client_id(self):
        for record in self:
            if self.env.user.has_group('event.group_event_manager') and record.youtube_live_stream_enable:
                record.youtube_oauth_client_id = self.env['ir.config_parameter'].sudo().get_param('event.youtube_oauth_client_id')
            else:
                record.youtube_oauth_client_id = None

    def _inverse_youtube_oauth_client_id(self):
        for record in self:
            if self.env.user.has_group('event.group_event_manager') and record.youtube_live_stream_enable:
                self.env['ir.config_parameter'].sudo().set_param('event.youtube_oauth_client_id', record.youtube_oauth_client_id)
            elif self.env.user.has_group('event.group_event_manager'):
                self.env['ir.config_parameter'].sudo().set_param('event.youtube_oauth_client_id', '')

    @api.depends('youtube_live_stream_enable')
    def _compute_youtube_oauth_client_secret(self):
        for record in self:
            if self.env.user.has_group('event.group_event_manager') and record.youtube_live_stream_enable:
                record.youtube_oauth_client_secret = self.env['ir.config_parameter'].sudo().get_param('event.youtube_oauth_client_secret')
            else:
                record.youtube_oauth_client_secret = None

    def _inverse_youtube_oauth_client_secret(self):
        for record in self:
            if self.env.user.has_group('event.group_event_manager') and record.youtube_live_stream_enable:
                self.env['ir.config_parameter'].sudo().set_param('event.youtube_oauth_client_secret', record.youtube_oauth_client_secret)
            elif self.env.user.has_group('event.group_event_manager'):
                self.env['ir.config_parameter'].sudo().set_param('social.youtube_oauth_client_secret', '')
