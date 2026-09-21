from odoo import fields, models


class SpeechQuestion(models.Model):
    _name = "speech.question"
    _inherit = ["mixin.speech.finding"]
    _description = "Spoken Question"

    answered = fields.Boolean(default=False)
    answer = fields.Text()
