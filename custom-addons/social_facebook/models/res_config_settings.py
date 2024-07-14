# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    facebook_use_own_account = fields.Boolean("Use your own Facebook Account", config_parameter='social.facebook_use_own_account',
        help="""Check this if you want to use your personal Facebook Developer Account instead of the provided one.""")
    facebook_app_id = fields.Char("Facebook App ID",
        compute='_compute_facebook_app_id', inverse='_inverse_facebook_app_id')
    facebook_client_secret = fields.Char("Facebook App Secret",
        compute='_compute_facebook_client_secret', inverse='_inverse_facebook_client_secret')

    @api.onchange('facebook_use_own_account')
    def _onchange_facebook_use_own_account(self):
        if not self.facebook_use_own_account:
            self.facebook_app_id = False
            self.facebook_client_secret = False

    @api.depends('facebook_use_own_account')
    def _compute_facebook_app_id(self):
        for record in self:
            if self.env.user.has_group('social.group_social_manager'):
                record.facebook_app_id = self.env['ir.config_parameter'].sudo().get_param('social.facebook_app_id')
            else:
                record.facebook_app_id = None

    def _inverse_facebook_app_id(self):
        for record in self:
            if self.env.user.has_group('social.group_social_manager'):
                self.env['ir.config_parameter'].sudo().set_param('social.facebook_app_id', record.facebook_app_id)

    @api.depends('facebook_use_own_account')
    def _compute_facebook_client_secret(self):
        for record in self:
            if self.env.user.has_group('social.group_social_manager'):
                record.facebook_client_secret = self.env['ir.config_parameter'].sudo().get_param('social.facebook_client_secret')
            else:
                record.facebook_client_secret = None

    def _inverse_facebook_client_secret(self):
        for record in self:
            if self.env.user.has_group('social.group_social_manager'):
                self.env['ir.config_parameter'].sudo().set_param('social.facebook_client_secret', record.facebook_client_secret)
