# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class TrackTagCategory(models.Model):
    _name = "event.track.tag.category"
    _description = 'Event Track Tag Category'
    _order = "sequence"

    name = fields.Char("Name", required=True, translate=True)
    sequence = fields.Integer('Sequence', default=10)
    tag_ids = fields.One2many('event.track.tag', 'category_id', string="Tags")


class TrackTag(models.Model):
    _inherit = "event.track.tag"
    _order = "category_id, sequence, name"

    sequence = fields.Integer('Sequence', default=10)
    category_id = fields.Many2one('event.track.tag.category', string="Category", ondelete="set null")
