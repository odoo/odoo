from odoo import fields, models


class SpeechSpeaker(models.Model):
    _inherit = "speech.speaker"

    sentiment = fields.Selection(
        selection=[
            ("positive", "Positive"),
            ("neutral", "Neutral"),
            ("negative", "Negative"),
        ],
    )
    engagement = fields.Selection(
        selection=[
            ("high", "High"),
            ("medium", "Medium"),
            ("low", "Low"),
        ],
    )
    interruptions = fields.Integer()
    questions_asked = fields.Integer()
