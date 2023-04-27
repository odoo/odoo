# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Users(models.Model):
    _inherit = 'res.users'

    create_date = fields.Datetime('Create Date', readonly=True, index=True)
    forum_waiting_posts_count = fields.Integer('Waiting post', compute="_get_user_waiting_post")

    def _get_user_waiting_post(self):
        for user in self:
            Post = self.env['forum.post']
            domain = [('parent_id', '=', False), ('state', '=', 'pending'), ('create_uid', '=', user.id)]
            user.forum_waiting_posts_count = Post.search_count(domain)

    # Wrapper for call_kw with inherits
    def open_website_url(self):
        return self.mapped('partner_id').open_website_url()

    def get_gamification_redirection_data(self):
        res = super(Users, self).get_gamification_redirection_data()
        res.append({
            'url': '/forum',
            'label': 'See our Forum'
        })
        return res
