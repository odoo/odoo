# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from random import randint

from odoo import fields, models


class TrackTag(models.Model):
    _name = "event.track.tag"
    _description = 'Event Track Tag'
    _order = "category_id, sequence, name"

    def _default_color(self):
        return randint(1, 11)

    name = fields.Char('Tag Name', required=True)
    track_ids = fields.Many2many('event.track', string='Tracks')
    color = fields.Integer(
        string='Color Index', default=lambda self: self._default_color(),
        help="Note that colorless tags won't be available on the website.")
    sequence = fields.Integer('Sequence', default=10)
    category_id = fields.Many2one('event.track.tag.category', string="Category", ondelete="set null")

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]
