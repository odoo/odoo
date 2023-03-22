# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class Users(models.Model):
    _inherit = 'res.users'

    create_date = fields.Datetime('Create Date', readonly=True, index=True)
    forum_waiting_posts_count = fields.Integer(
        'Waiting post', compute="_compute_forum_waiting_posts_count")

    def _compute_forum_waiting_posts_count(self):
        if not self.ids:
            self.forum_waiting_posts_count = 0
            return
        read_group_res = self.env['forum.post']._read_group(
            [('create_uid', 'in', self.ids), ('state', '=', 'pending'), ('parent_id', '=', False)],
            ['create_uid'],
            ['create_uid'],
        )
        mapping = {
            res_group['create_uid'][0]: res_group['create_uid_count']
            for res_group in read_group_res
        }
        for user in self:
            user.forum_waiting_posts_count = mapping.get(user.id, 0)

    # Wrapper for call_kw with inherits
    def open_website_url(self):
        return self.mapped('partner_id').open_website_url()

    def get_gamification_redirection_data(self):
        res = super().get_gamification_redirection_data()
        res.append({
            'label': _('See our Forum'),
            'url': '/forum',
        })
        return res
