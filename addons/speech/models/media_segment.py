from odoo import fields, models


class MediaSegment(models.Model):
    _inherit = "media.segment"

    transcription_state = fields.Selection(
        related="attachment_id.speech_state",
        string="Transcription",
    )
    speech_cues = fields.Json(related="attachment_id.speech_cues")
