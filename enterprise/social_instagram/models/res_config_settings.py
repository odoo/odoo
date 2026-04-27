# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    instagram_use_own_account = fields.Boolean("Use your own Instagram Account", config_parameter='social.instagram_use_own_account',
        help="""Check this if you want to use your personal Instagram Developer Account instead of the provided one.""")
    instagram_app_id = fields.Char("Instagram App ID",
        compute='_compute_instagram_app_id', inverse='_inverse_instagram_app_id')
    instagram_client_secret = fields.Char("Instagram App Secret",
        compute='_compute_instagram_client_secret', inverse='_inverse_instagram_client_secret')

    @api.depends('instagram_use_own_account')
    def _compute_instagram_app_id(self):
        for record in self:
            if record._instagram_use_and_check_own_account():
                record.instagram_app_id = self.env['ir.config_parameter'].sudo().get_param('social.instagram_app_id')
            else:
                record.instagram_app_id = None

    def _inverse_instagram_app_id(self):
        for record in self:
            if record._instagram_use_and_check_own_account():
                self.env['ir.config_parameter'].sudo().set_param('social.instagram_app_id', record.instagram_app_id)
            elif self.env.user.has_group('social.group_social_manager'):
                self.env['ir.config_parameter'].sudo().set_param('social.instagram_app_id', '')

    @api.depends('instagram_use_own_account')
    def _compute_instagram_client_secret(self):
        for record in self:
            if record._instagram_use_and_check_own_account():
                record.instagram_client_secret = self.env['ir.config_parameter'].sudo().get_param('social.instagram_client_secret')
            else:
                record.instagram_client_secret = None

    def _inverse_instagram_client_secret(self):
        for record in self:
            if record._instagram_use_and_check_own_account():
                self.env['ir.config_parameter'].sudo().set_param('social.instagram_client_secret', record.instagram_client_secret)
            elif self.env.user.has_group('social.group_social_manager'):
                self.env['ir.config_parameter'].sudo().set_param('social.instagram_client_secret', '')

    def _instagram_use_and_check_own_account(self):
        return self.env.user.has_group('social.group_social_manager') and self.instagram_use_own_account
