from odoo import fields, models


class GamificationChallenge(models.Model):
    _inherit = "gamification.challenge"

    challenge_category = fields.Selection(
        selection_add=[("forum", "Website / Forum")],
        ondelete={"forum": "set default"},
    )
