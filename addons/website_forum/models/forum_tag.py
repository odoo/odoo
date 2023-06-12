# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class Tags(models.Model):
    _name = "forum.tag"
    _description = "Forum Tag"
    _inherit = ['mail.thread', 'website.seo.metadata']

    name = fields.Char('Name', required=True)
    forum_id = fields.Many2one('forum.forum', string='Forum', required=True)
    post_ids = fields.Many2many(
        'forum.post', 'forum_tag_rel', 'forum_tag_id', 'forum_id',
        string='Posts', domain=[('state', '=', 'active')])
    posts_count = fields.Integer('Number of Posts', compute='_compute_posts_count', store=True)

    _sql_constraints = [
        ('name_uniq', 'unique (name, forum_id)', "Tag name already exists!"),
    ]

    @api.depends("post_ids", "post_ids.tag_ids", "post_ids.state", "post_ids.active")
    def _compute_posts_count(self):
        for tag in self:
            tag.posts_count = len(tag.post_ids)  # state filter is in field domain

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            forum = self.env['forum.forum'].browse(vals.get('forum_id'))
            if self.env.user.karma < forum.karma_tag_create and not self.env.is_admin():
                raise AccessError(_('%d karma required to create a new Tag.', forum.karma_tag_create))
        return super(Tags, self.with_context(mail_create_nolog=True, mail_create_nosubscribe=True)).create(vals_list)
