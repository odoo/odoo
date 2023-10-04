# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class Users(models.Model):
    """ Update of res.users class
        - add a preference about username for livechat purpose
    """
    _inherit = 'res.users'

    livechat_username = fields.Char(string='Livechat Username', compute='_compute_livechat_username', inverse='_inverse_livechat_username', store=False)
    livechat_lang_ids = fields.Many2many('res.lang', string='Livechat Languages', compute='_compute_livechat_lang_ids', inverse='_inverse_livechat_lang_ids', store=False)
    has_access_livechat = fields.Boolean(compute='_compute_has_access_livechat', string='Has access to Livechat', store=False, readonly=True)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['livechat_username', 'livechat_lang_ids', 'has_access_livechat']

    @api.depends('res_users_settings_id.livechat_username')
    def _compute_livechat_username(self):
        for user in self:
            user.livechat_username = user.res_users_settings_id.livechat_username

    def _inverse_livechat_username(self):
        for user in self:
            if not user.res_users_settings_id:
                self.env['res.users.settings']._find_or_create_for_user(user)
            user.res_users_settings_id.livechat_username = user.livechat_username

    @api.depends('res_users_settings_id.livechat_lang_ids')
    def _compute_livechat_lang_ids(self):
        for user in self:
            user.livechat_lang_ids = user.res_users_settings_id.livechat_lang_ids

    def _inverse_livechat_lang_ids(self):
        for user in self:
            if not user.res_users_settings_id:
                self.env['res.users.settings']._find_or_create_for_user(user)
            user.res_users_settings_id.livechat_lang_ids = user.livechat_lang_ids

    def _compute_has_access_livechat(self):
        for user in self:
            user.has_access_livechat = user.has_group('im_livechat.im_livechat_group_user')
