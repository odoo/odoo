# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Forum(models.Model):
    _inherit = 'forum.forum'

    slide_channel_id = fields.Many2one('slide.channel', 'Course')
