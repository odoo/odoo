from odoo import fields, models


class MediaSegment(models.Model):
    _inherit = "media.segment"

    transcript_state = fields.Selection(
        related="attachment_id.transcript_state",
        string="Transcription",
    )
    transcript_cues = fields.Json(related="attachment_id.transcript_cues")
