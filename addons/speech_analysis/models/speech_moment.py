from odoo import fields, models


class SpeechMoment(models.Model):
    _name = "speech.moment"
    _inherit = ["mixin.speech.finding"]
    _description = "Spoken Moment"

    kind = fields.Selection(
        selection=[
            ("decision", "Decision"),
            ("agreement", "Agreement"),
            ("objection", "Objection"),
            ("concern", "Concern"),
            ("risk", "Risk"),
            ("complaint", "Complaint"),
            ("praise", "Praise"),
            ("next_step", "Next step"),
            ("fact", "Fact"),
            ("highlight", "Highlight"),
        ],
        required=True,
    )
