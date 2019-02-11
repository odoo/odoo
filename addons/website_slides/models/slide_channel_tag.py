# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SlideChannelTagGroup(models.Model):
    _name = 'slide.channel.tag.group'
    _description = 'Channel/Course tags'
    _order = 'sequence asc'

    name = fields.Char('Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=10, index=True, required=True)
    tag_ids = fields.One2many('slide.channel.tag', 'group_id', string='Tags')
    website_published = fields.Boolean(
        'Menu entry', default=True,
        help='Makes a menu entry in main navigation of Slides, allowing to filter on its tags directly from main navigation.')


class SlideChannelTag(models.Model):
    _name = 'slide.channel.tag'
    _description = 'Channel/Course tags'
    _order = 'group_sequence asc, sequence asc'

    name = fields.Char('Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=10, index=True, required=True)
    group_id = fields.Many2one('slide.channel.tag.group', string='Group', index=True, required=True)
    group_sequence = fields.Integer(
        'Group sequence', related='group_id.sequence',
        index=True, readonly=True, store=True)
    channel_ids = fields.Many2many('slide.channel.tag', 'slide_channel_tag_rel', 'tag_id', 'channel_id', string='Channels')
