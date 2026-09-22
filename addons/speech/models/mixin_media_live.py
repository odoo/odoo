from __future__ import annotations

import base64
import binascii
import typing

from odoo import fields, models
from odoo.exceptions import UserError

if typing.TYPE_CHECKING:
    from odoo.addons.base.models.ir_attachment import IrAttachment
    from odoo.addons.media.models.media_segment import MediaSegment

LIVE_CHUNK_PRIORITY = 1
LIVE_NOTIFICATION = "speech.live"


class MixinMediaLive(models.AbstractModel):
    _name = "mixin.media.live"
    _inherit = ["mixin.media.timeline"]
    _description = "Live capture onto a media timeline"

    is_live = fields.Boolean(
        string="Live capture in progress",
        copy=False,
    )
    live_chunk_count = fields.Integer(
        copy=False,
        readonly=True,
    )
    live_elapsed_s = fields.Float(
        string="Live elapsed (s)",
        copy=False,
        readonly=True,
    )

    def action_start_live(self) -> bool:
        for record in self:
            record._check_live_can_start()
            record._drop_live_chunks()
            record.write(
                {"is_live": True, "live_chunk_count": 0, "live_elapsed_s": 0.0}
            )
            record._live_publish({"event": "started"})
        return True

    def action_stop_live(self) -> bool:
        for record in self.filtered("is_live"):
            record._live_publish({"event": "stopped"})
        self.write({"is_live": False})
        return True

    def _check_live_can_start(self) -> None:
        pass

    def _live_channel_name(self) -> str:
        self.check_singleton()
        return f"{LIVE_NOTIFICATION}/{self._name}/{self.id}"

    def _live_publish(self, payload: dict) -> None:
        self.check_singleton()
        self.env["bus.bus"]._sendone(
            (self, "live"),
            LIVE_NOTIFICATION,
            {"model": self._name, "id": self.id, **payload},
        )

    def _drop_live_chunks(self) -> None:
        self.check_singleton()
        self.segment_ids.filtered("live").sudo().unlink()

    def _decode_live_audio(self, audio_b64: str) -> bytes:
        try:
            return base64.b64decode(audio_b64 or "", validate=True)
        except (TypeError, ValueError, binascii.Error) as error:
            raise UserError(self.env._("The audio is not valid base64.")) from error

    def _ingest_live_chunk(
        self,
        audio: bytes,
        start_s: float,
        duration_s: float = 0.0,
        mimetype: str = "audio/wav",
    ) -> MediaSegment:
        self.check_singleton()
        if not self.is_live:
            raise UserError(self.env._("No live session is running here."))
        if not audio:
            raise UserError(self.env._("The chunk holds no audio."))
        start_ms = int(start_s * 1000)
        end_ms = start_ms + max(int(duration_s * 1000), 1)
        attachment = (
            self.env["ir.attachment"]
            .sudo()
            .create(
                {
                    "name": f"{self._name}-{self.id}-live-{start_ms:010d}",
                    "raw": audio,
                    "mimetype": mimetype,
                    "res_model": self._name,
                    "res_id": self.id,
                }
            )
        )
        if not attachment.can_transcribe:
            raise UserError(
                self.env._(
                    "No speech engine may hear this: the data policy of "
                    "%(company)s allows no vendor, and no local engine is installed.",
                    company=(attachment.company_id or self.env.company).name,
                )
            )
        segment = self.sudo()._add_media_segment(attachment, start_ms, end_ms)
        segment.live = True
        attachment._transcribe_later(priority=LIVE_CHUNK_PRIORITY)
        self.write(
            {
                "live_chunk_count": self.live_chunk_count + 1,
                "live_elapsed_s": max(self.live_elapsed_s, end_ms / 1000),
            }
        )
        return segment

    def _live_segment(self, attachment: IrAttachment) -> MediaSegment:
        return self.segment_ids.filtered(
            lambda segment: segment.live and segment.attachment_id == attachment
        )

    def _on_media_transcribed(self, attachment: IrAttachment) -> None:
        super()._on_media_transcribed(attachment)
        segment = self._live_segment(attachment)
        if not segment:
            return
        self._live_publish(
            {
                "event": "chunk",
                "segment_id": segment.id,
                "start_s": segment.start_ms / 1000,
                "elapsed_s": self.live_elapsed_s,
                "text": attachment.transcript_text or "",
                "chunks": self.live_chunk_count,
            }
        )
        self._on_live_chunk_transcribed(segment)

    def _on_media_transcription_failed(self, attachment: IrAttachment) -> None:
        super()._on_media_transcription_failed(attachment)
        segment = self._live_segment(attachment)
        if segment:
            self._live_publish(
                {
                    "event": "chunk",
                    "segment_id": segment.id,
                    "start_s": segment.start_ms / 1000,
                    "elapsed_s": self.live_elapsed_s,
                    "text": "",
                    "error": attachment.transcript_error or "",
                    "chunks": self.live_chunk_count,
                }
            )

    def _on_live_chunk_transcribed(self, segment: MediaSegment) -> None:
        pass
