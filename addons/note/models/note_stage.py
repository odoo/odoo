# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models

class NoteStage(models.Model):
    """ Category of Note """
    _name = "note.stage"
    _description = "Note Stage"
    _order = 'sequence asc'

    name = fields.Char(string='Stage Name', translate=True, required=True)
    sequence = fields.Integer(help="Used to order the note stages", default=1)
    fold = fields.Boolean(string='Folded by Default', default=0)
