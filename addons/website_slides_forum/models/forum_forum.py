# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ForumForum(models.Model):
    _inherit = 'forum.forum'

    slide_channel_ids = fields.One2many('slide.channel', 'forum_id', 'Courses', help="Edit the course linked to this forum on the course form.")
    slide_channel_id = fields.Many2one('slide.channel', 'Course', compute='_compute_slide_channel_id', store=True)
    visibility = fields.Selection(related='slide_channel_id.visibility', help="Forum linked to a Course, the visibility is the one applied on the course.")
    image_1920 = fields.Image('Image', compute='_compute_image_1920', store=True, readonly=False)

    @api.depends('slide_channel_ids')
    def _compute_slide_channel_id(self):
        for forum in self:
            if forum.slide_channel_ids:
                forum.slide_channel_id = forum.slide_channel_ids[0]
            else:
                forum.slide_channel_id = None

    @api.depends('slide_channel_id', 'slide_channel_id.image_1920')
    def _compute_image_1920(self):
        for forum in self.filtered(lambda f: not f.image_1920 and f.slide_channel_id.image_1920):
            forum.image_1920 = forum.slide_channel_id.image_1920
