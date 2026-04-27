# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    linkedin_use_own_account = fields.Boolean("Use your own LinkedIn Account",
        config_parameter='social.linkedin_use_own_account',
        help="""Check this if you want to use your personal LinkedIn Developer Account instead of the provided one.""")
    linkedin_app_id = fields.Char("App ID", config_parameter='social.linkedin_app_id',
        compute='_compute_linkedin_app_id', inverse='_inverse_linkedin_app_id')
    linkedin_client_secret = fields.Char("App Secret", config_parameter='social.linkedin_client_secret',
        compute='_compute_linkedin_client_secret', inverse='_inverse_linkedin_client_secret')

    @api.onchange('linkedin_use_own_account')
    def _onchange_linkedin_use_own_account(self):
        if not self.linkedin_use_own_account:
            self.linkedin_app_id = None
            self.linkedin_client_secret = None

    @api.depends('linkedin_use_own_account')
    def _compute_linkedin_app_id(self):
        user_is_manager = self.env.user.has_group('social.group_social_manager')
        linkedin_app_id = self.env['ir.config_parameter'].sudo().get_param('social.linkedin_app_id')
        for setting in self:
            setting.linkedin_app_id = linkedin_app_id if user_is_manager else None

    def _inverse_linkedin_app_id(self):
        user_is_manager = self.env.user.has_group('social.group_social_manager')
        for setting in self:
            if user_is_manager:
                self.env['ir.config_parameter'].sudo().set_param(
                    'social.linkedin_app_id', setting.linkedin_app_id)

    @api.depends('linkedin_use_own_account')
    def _compute_linkedin_client_secret(self):
        user_is_manager = self.env.user.has_group('social.group_social_manager')
        linkedin_client_secret = self.env['ir.config_parameter'].sudo().get_param('social.linkedin_client_secret')
        for setting in self:
            setting.linkedin_client_secret = linkedin_client_secret if user_is_manager else None

    def _inverse_linkedin_client_secret(self):
        user_is_manager = self.env.user.has_group('social.group_social_manager')
        for setting in self:
            if user_is_manager:
                self.env['ir.config_parameter'].sudo().set_param(
                    'social.linkedin_client_secret',
                    setting.linkedin_client_secret)
