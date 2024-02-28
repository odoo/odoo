# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Channel(models.Model):
    _inherit = 'slide.channel'

    forum_id = fields.Many2one('forum.forum', 'Course Forum', copy=False)
    forum_total_posts = fields.Integer('Number of active forum posts', related="forum_id.total_posts")

    _sql_constraints = [
        ('forum_uniq', 'unique (forum_id)', "Only one course per forum!"),
    ]

    def action_redirect_to_forum(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("website_forum.action_forum_post")
        action['view_mode'] = 'tree'
        action['context'] = {
            'create': False
        }
        action['domain'] = [('forum_id', '=', self.forum_id.id)]

        return action

    @api.model_create_multi
    def create(self, vals_list):
        channels = super(Channel, self.with_context(mail_create_nosubscribe=True)).create(vals_list)
        channels.forum_id.privacy = False
        return channels

    def write(self, vals):
        old_forum = self.forum_id

        res = super(Channel, self).write(vals)
        if 'forum_id' in vals:
            self.forum_id.privacy = False
            if old_forum != self.forum_id:
                old_forum.write({
                    'privacy': 'private',
                    'authorized_group_id': self.env.ref('website_slides.group_website_slides_officer').id,
                })
        return res
