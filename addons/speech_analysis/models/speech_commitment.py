from odoo import fields, models


class SpeechCommitment(models.Model):
    _name = "speech.commitment"
    _inherit = ["mixin.speech.finding"]
    _description = "Spoken Commitment"

    due_date = fields.Date()
    done = fields.Boolean(default=False)
