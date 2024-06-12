# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ChallengeLine(models.Model):
    """Gamification challenge line

    Predefined goal for 'gamification_challenge'
    These are generic list of goals with only the target goal defined
    Should only be created for the gamification.challenge object
    """
    _name = 'gamification.challenge.line'
    _description = 'Gamification generic goal for challenge'
    _order = "sequence, id"

    challenge_id = fields.Many2one('gamification.challenge', string='Challenge', required=True, ondelete="cascade")
    definition_id = fields.Many2one('gamification.goal.definition', string='Goal Definition', required=True, ondelete="cascade")

    sequence = fields.Integer('Sequence', default=1)
    target_goal = fields.Float('Target Value to Reach', required=True)

    name = fields.Char("Name", related='definition_id.name', readonly=False)
    condition = fields.Selection(string="Condition", related='definition_id.condition', readonly=True)
    definition_suffix = fields.Char("Unit", related='definition_id.suffix', readonly=True)
    definition_monetary = fields.Boolean("Monetary", related='definition_id.monetary', readonly=True)
    definition_full_suffix = fields.Char("Suffix", related='definition_id.full_suffix', readonly=True)
