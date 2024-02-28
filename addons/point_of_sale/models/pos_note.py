# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class PosNote(models.Model):
    _name = 'pos.note'
    _description = 'PoS Note'

    name = fields.Char(required=True)
    sequence = fields.Integer('Sequence', default=1)

    _sql_constraints = [('name_unique', 'unique (name)', "A note with this name already exists")]
