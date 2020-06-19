# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


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

    name = fields.Char("Name", required=True, translate=True)
    sequence = fields.Integer('Sequence', default=0)
    category_id = fields.Many2one("event.tag.category", string="Category", required=True, ondelete='cascade')

    def name_get(self):
        return [(tag.id, _("%s: %s" % (tag.category_id.name, tag.name))) for tag in self]
