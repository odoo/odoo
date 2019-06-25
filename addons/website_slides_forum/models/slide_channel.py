# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Channel(models.Model):
    _inherit = 'slide.channel'

    forum_id = fields.Many2one('forum.forum', 'Course Forum')

    _sql_constraints = [
        ('forum_uniq', 'unique (forum_id)', "Only one forum per slide channel!"),
    ]
