# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Channel(models.Model):
    _inherit = 'slide.channel'

    forum_id = fields.Many2one('forum.forum', 'Course Forum')
    forum_total_posts = fields.Integer('Number of active forum posts', related="forum_id.total_posts")

    _sql_constraints = [
        ('forum_uniq', 'unique (forum_id)', "Only one course per forum!"),
    ]

    def action_redirect_to_forum(self):
        self.ensure_one()
        action = self.env.ref('website_forum.action_forum_post').read()[0]
        action['view_mode'] = 'tree'
        action['context'] = {
            'create': False
        }
        action['domain'] = [('forum_id', '=', self.forum_id.id)]

        return action
