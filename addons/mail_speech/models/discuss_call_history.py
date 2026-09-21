from __future__ import annotations

import typing

from odoo import fields, models

if typing.TYPE_CHECKING:
    from odoo.addons.base.models.ir_attachment import IrAttachment


class DiscussCallHistory(models.Model):
    _name = "discuss.call.history"
    _inherit = ["discuss.call.history", "mixin.media.timeline"]

    recorder_session_id = fields.Many2one(
        comodel_name="discuss.channel.rtc.session",
        copy=False,
        readonly=True,
        ondelete="set null",
        help="The participant whose browser is recording this call; leaving the "
        "call releases it.",
    )
    recording_offset_ms = fields.Integer(
        copy=False,
        readonly=True,
        help="Where the current recording starts in this call's timeline: the "
        "recorder counts from zero, the timeline does not.",
    )

    def _on_media_fully_transcribed(self) -> None:
        super()._on_media_fully_transcribed()
        for history in self:
            history.channel_id._bus_send(
                "discuss.call.history/transcribed",
                {"id": history.id, "transcript": history.media_transcript},
            )

    def _on_media_transcribed(self, attachment: IrAttachment) -> None:
        super()._on_media_transcribed(attachment)
        for history in self:
            history.channel_id._bus_send(
                "discuss.call.history/segment_transcribed",
                {"id": history.id, "attachment_id": attachment.id},
            )
