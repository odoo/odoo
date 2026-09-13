from odoo import fields, models


# Each line links a goal definition to a target value.  When the challenge
# starts, one ``gamification.goal`` record per participant is generated from
# each line.
class GamificationChallengeLine(models.Model):
    """Predefined goal template within a challenge."""

    _name = "gamification.challenge.line"
    _description = "Gamification generic goal for challenge"
    _order = "sequence, id"

    challenge_id = fields.Many2one(
        "gamification.challenge",
        required=True,
        index=True,
        ondelete="cascade",
    )
    definition_id = fields.Many2one(
        "gamification.goal.definition",
        string="Goal Definition",
        required=True,
        ondelete="cascade",
    )

    sequence = fields.Integer(default=1)
    target_goal = fields.Float("Target Value to Reach", required=True)

    name = fields.Char("Name", related="definition_id.name", readonly=True)
    condition = fields.Selection(
        string="Condition", related="definition_id.condition", readonly=True
    )
    definition_suffix = fields.Char(
        "Unit", related="definition_id.suffix", readonly=True
    )
    definition_monetary = fields.Boolean(
        "Monetary", related="definition_id.monetary", readonly=True
    )
    definition_full_suffix = fields.Char(
        "Suffix", related="definition_id.full_suffix", readonly=True
    )
