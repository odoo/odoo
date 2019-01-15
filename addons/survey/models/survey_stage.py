# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SurveyStage(models.Model):
    _name = 'survey.stage'
    _description = 'Survey Stage'
    _order = 'sequence,id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=1)
    closed = fields.Boolean(help="If closed, people won't be able to answer to surveys in this column.")
    fold = fields.Boolean(string="Folded in kanban view")

    _sql_constraints = [
        ('positive_sequence', 'CHECK(sequence >= 0)', 'Sequence number MUST be a natural')
    ]
