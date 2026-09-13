from __future__ import annotations

from odoo import fields, models


class DocumentsDocument(models.Model):
    _inherit = "document.document"

    speech_state = fields.Selection(
        related="attachment_id.speech_state",
        string="Transcription",
    )
    speech_transcript = fields.Text(
        related="attachment_id.speech_transcript",
        string="Transcript",
    )
    can_transcribe = fields.Boolean(related="attachment_id.can_transcribe")

    def action_transcribe(self) -> bool:
        return self.attachment_id.action_transcribe()

    def _speech_vtt(self) -> str:
        self.check_singleton()
        return self.attachment_id._speech_vtt()
