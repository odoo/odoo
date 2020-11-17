# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from random import randint

from odoo import fields, models


class SlideChannelTagGroup(models.Model):
    _name = 'slide.channel.tag.group'
    _description = 'Channel/Course Groups'
    _inherit = 'website.published.mixin'
    _order = 'sequence asc'

    name = fields.Char('Group Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=10, index=True, required=True)
    tag_ids = fields.One2many('slide.channel.tag', 'group_id', string='Tags')

    def _default_is_published(self):
        return True


class SlideChannelTag(models.Model):
    _name = 'slide.channel.tag'
    _description = 'Channel/Course Tag'
    _order = 'group_sequence asc, sequence asc'

    name = fields.Char('Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=10, index=True, required=True)
    group_id = fields.Many2one('slide.channel.tag.group', string='Group', index=True, required=True)
    group_sequence = fields.Integer(
        'Group sequence', related='group_id.sequence',
        index=True, readonly=True, store=True)
    channel_ids = fields.Many2many('slide.channel', 'slide_channel_tag_rel', 'tag_id', 'channel_id', string='Channels')
    color = fields.Integer(
        string='Color Index', default=lambda self: randint(1, 11),
        help="Tag color used in both backend and website. No color means no display in kanban or front-end, to distinguish internal tags from public categorization tags")
