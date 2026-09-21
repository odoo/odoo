from __future__ import annotations

import typing

from odoo import api, fields, models

from ..tools.engines import can_transcribe

if typing.TYPE_CHECKING:
    from odoo.addons.base.models.ir_attachment import IrAttachment


class MixinMediaTimeline(models.AbstractModel):
    _inherit = "mixin.media.timeline"

    media_transcript = fields.Text(compute="_compute_media_transcript")
    transcription_state = fields.Selection(
        selection=[
            ("none", "Not transcribed"),
            ("queued", "Queued"),
            ("running", "Transcribing"),
            ("done", "Transcribed"),
            ("failed", "Failed"),
        ],
        compute="_compute_transcription_state",
    )

    @api.depends("segment_ids.attachment_id.speech_cues")
    def _compute_media_transcript(self) -> None:
        for record in self:
            spoken = [
                segment.attachment_id.speech_transcript
                for segment in record.segment_ids.sorted("start_ms")
            ]
            record.media_transcript = "\n".join(part for part in spoken if part)

    @api.depends("segment_ids.attachment_id.speech_state")
    def _compute_transcription_state(self) -> None:
        for record in self:
            states = set(record.segment_ids.attachment_id.mapped("speech_state"))
            if "running" in states:
                record.transcription_state = "running"
            elif "queued" in states:
                record.transcription_state = "queued"
            elif "failed" in states:
                record.transcription_state = "failed"
            elif states and states == {"done"}:
                record.transcription_state = "done"
            else:
                record.transcription_state = "none"

    def action_transcribe_media(self) -> bool:
        for record in self:
            for segment in record.segment_ids:
                if can_transcribe(segment.attachment_id.mimetype or "", self.env):
                    segment.attachment_id._transcribe_later()
        return True

    def _on_media_transcribed(self, attachment: IrAttachment) -> None:
        pass

    def _on_media_transcription_failed(self, attachment: IrAttachment) -> None:
        pass

    def _on_media_fully_transcribed(self) -> None:
        pass
