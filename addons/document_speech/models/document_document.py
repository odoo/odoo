from __future__ import annotations

from odoo import fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class DocumentsDocument(models.Model):
    _inherit = "document.document"

    transcript_state = fields.Selection(
        related="attachment_id.transcript_state",
        string="Transcription",
    )
    transcript_text = fields.Text(
        related="attachment_id.transcript_text",
        string="Transcript",
    )
    can_transcribe = fields.Boolean(related="attachment_id.can_transcribe")

    def action_transcribe(self) -> bool:
        _debug.lifecycle(
            "transcribe_requested", documents=self, state=self.transcript_state
        )
        return self.attachment_id.action_transcribe()

    def _transcript_vtt(self) -> str:
        self.check_singleton()
        return self.attachment_id._transcript_vtt()
