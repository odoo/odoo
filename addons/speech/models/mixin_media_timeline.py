from __future__ import annotations

import typing

from odoo import api, fields, models

from ..tools.engines import can_transcribe

if typing.TYPE_CHECKING:
    from .media_segment import MediaSegment
    from odoo.addons.base.models.ir_attachment import IrAttachment


class MixinMediaTimeline(models.AbstractModel):
    _name = "mixin.media.timeline"
    _description = "Media Timeline"

    segment_ids: MediaSegment = fields.One2many(
        comodel_name="media.segment",
        inverse_name="res_id",
        string="Media",
        domain=lambda self: [("res_model", "=", self._name)],
    )
    media_duration_ms = fields.Integer(compute="_compute_media_duration_ms")
    has_media = fields.Boolean(compute="_compute_has_media")
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

    @api.depends("segment_ids.end_ms", "segment_ids.start_ms")
    def _compute_media_duration_ms(self) -> None:
        for record in self:
            ends = record.segment_ids.mapped("end_ms")
            record.media_duration_ms = max(ends) if ends else 0

    @api.depends("segment_ids")
    def _compute_has_media(self) -> None:
        for record in self:
            record.has_media = bool(record.segment_ids)

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

    def _add_media_segment(
        self, attachment: IrAttachment, start_ms: int, end_ms: int
    ) -> MediaSegment:
        self.check_singleton()
        return self.env["media.segment"].create(
            {
                "res_model": self._name,
                "res_id": self.id,
                "attachment_id": attachment.id,
                "start_ms": start_ms,
                "end_ms": end_ms,
            }
        )

    def action_transcribe_media(self) -> bool:
        for record in self:
            for segment in record.segment_ids:
                if can_transcribe(segment.attachment_id.mimetype or ""):
                    segment.attachment_id._transcribe_later()
        return True

    def _on_media_transcribed(self, attachment: IrAttachment) -> None:
        pass

    def _on_media_transcription_failed(self, attachment: IrAttachment) -> None:
        pass

    def _on_media_fully_transcribed(self) -> None:
        pass

    @api.ondelete(at_uninstall=False)
    def _unlink_media_segments(self) -> None:
        self.env["media.segment"]._of(self).sudo().unlink()
