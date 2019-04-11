# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SurveyStage(models.Model):
    _name = 'survey.stage'
    _description = 'Survey Stage'
    _order = 'sequence,id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=1, required=True)
    fold = fields.Boolean(string="Folded in kanban view")

    state = fields.Selection(
        string="State",
        selection=[
                ('draft', 'Draft'),
                ('open', 'In Progress'),
                ('closed', 'Closed'),
        ], default='draft', required=True,
    )

    _sql_constraints = [
        ('positive_sequence', 'CHECK(sequence >= 0)', 'Sequence number MUST be a natural')
    ]
