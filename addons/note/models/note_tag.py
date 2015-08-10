# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models

class NoteTag(models.Model):
    _name = "note.tag"
    _description = "Note Tag"

    name = fields.Char(string='Tag Name', required=True)
