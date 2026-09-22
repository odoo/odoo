from odoo import fields, models


class MediaSegment(models.Model):
    _inherit = "media.segment"

    transcript_state = fields.Selection(
        related="attachment_id.transcript_state",
        string="Transcription",
    )
    transcript_cues = fields.Json(related="attachment_id.transcript_cues")
    live = fields.Boolean(
        readonly=True,
        help="A chunk sent during a live capture, transcribed as soon as it arrives.",
    )
