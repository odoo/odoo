from __future__ import annotations

import typing

from odoo import api, fields, models

from ..tools.engines import can_transcribe
from .ir_attachment import TRANSCRIPT_STATES

if typing.TYPE_CHECKING:
    from odoo.addons.base.models.ir_attachment import IrAttachment


class MixinMediaTimeline(models.AbstractModel):
    _inherit = "mixin.media.timeline"

    timeline_transcript = fields.Text(compute="_compute_timeline_transcript")
    timeline_transcript_state = fields.Selection(
        selection=TRANSCRIPT_STATES,
        compute="_compute_timeline_transcript_state",
    )

    @api.depends("segment_ids.attachment_id.transcript_cues")
    def _compute_timeline_transcript(self) -> None:
        for record in self:
            spoken = [
                segment.attachment_id.transcript_text
                for segment in record.segment_ids.sorted("start_ms")
            ]
            record.timeline_transcript = "\n".join(part for part in spoken if part)

    @api.depends("segment_ids.attachment_id.transcript_state")
    def _compute_timeline_transcript_state(self) -> None:
        for record in self:
            states = set(record.segment_ids.attachment_id.mapped("transcript_state"))
            if "running" in states:
                record.timeline_transcript_state = "running"
            elif "queued" in states:
                record.timeline_transcript_state = "queued"
            elif "failed" in states:
                record.timeline_transcript_state = "failed"
            elif states and states == {"done"}:
                record.timeline_transcript_state = "done"
            else:
                record.timeline_transcript_state = "none"

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
