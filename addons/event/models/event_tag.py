# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from random import randint

from odoo import api, fields, models


class EventTagCategory(models.Model):
    _name = "event.tag.category"
    _description = "Event Tag Category"
    _order = "sequence"

    name = fields.Char("Name", required=True, translate=True)
    sequence = fields.Integer('Sequence', default=0)
    tag_ids = fields.One2many('event.tag', 'category_id', string="Tags")

class EventTag(models.Model):
    _name = "event.tag"
    _description = "Event Tag"
    _order = "sequence"

    def _default_color(self):
        return randint(1, 11)

    name = fields.Char("Name", required=True, translate=True)
    sequence = fields.Integer('Sequence', default=0)
    category_id = fields.Many2one("event.tag.category", string="Category", required=True, ondelete='cascade')
    color = fields.Integer(
        string='Color Index', default=lambda self: self._default_color(),
        help='Tag color. No color means no display in kanban or front-end, to distinguish internal tags from public categorization tags.')

    def name_get(self):
        return [(tag.id, "%s: %s" % (tag.category_id.name, tag.name)) for tag in self]
