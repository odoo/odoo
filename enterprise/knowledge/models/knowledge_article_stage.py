# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class KnowledgeStage(models.Model):
    _name = "knowledge.article.stage"
    _description = "Knowledge Stage"
    _order = 'parent_id, sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=1)
    fold = fields.Boolean("Folded in kanban view")
    parent_id = fields.Many2one("knowledge.article", string="Owner Article",
        required=True, ondelete="cascade", help="Stages are shared among a"
        "common parent and its children articles."
    )
