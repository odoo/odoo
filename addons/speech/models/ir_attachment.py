from __future__ import annotations

import logging
from typing import Any, Self

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.libs.documents import EXPENSIVE, Cue, Document, cues_as_text, extension_for

from ..tools.engines import (
    DEFAULT_SPEECH_MIMETYPE,
    bare,
    can_transcribe,
    engine_error,
    synthesis_engines,
    transcription_engines,
)

_logger = logging.getLogger(__name__)

JOB_CHANNEL = "speech"

STATES = [
    ("none", "Not transcribed"),
    ("queued", "Queued"),
    ("running", "Transcribing"),
    ("done", "Transcribed"),
    ("failed", "Failed"),
]


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    speech_state = fields.Selection(
        selection=STATES,
        default="none",
        index="btree_not_null",
        copy=False,
        readonly=True,
    )
    speech_cues = fields.Json(
        copy=False,
        readonly=True,
        help="What is said in this recording, with the moment each phrase "
        "starts and ends.",
    )
    speech_language = fields.Char(
        copy=False,
        readonly=True,
    )
    speech_engine = fields.Char(
        copy=False,
        readonly=True,
    )
    speech_error = fields.Text(
        copy=False,
        readonly=True,
    )
    speech_transcript = fields.Text(compute="_compute_speech_transcript")
    can_transcribe = fields.Boolean(compute="_compute_can_transcribe")

    @api.depends("speech_cues")
    def _compute_speech_transcript(self) -> None:
        for attachment in self:
            attachment.speech_transcript = cues_as_text(attachment._speech_cues())

    @api.depends("mimetype")
    def _compute_can_transcribe(self) -> None:
        readable = {
            mimetype: can_transcribe(mimetype, self.env)
            for mimetype in set(self.mapped("mimetype"))
        }
        for attachment in self:
            attachment.can_transcribe = readable.get(attachment.mimetype, False)

    def _speech_cues(self) -> list[Cue]:
        self.check_singleton()
        return [
            Cue(
                start=cue.get("start", 0.0),
                end=cue.get("end", 0.0),
                text=cue.get("text", ""),
                speaker=cue.get("speaker", ""),
            )
            for cue in self.speech_cues or []
        ]

    def _speech_vtt(self) -> str:
        self.check_singleton()
        cues = self._speech_cues()
        return Document.of(cues=cues).data.decode() if cues else ""

    def action_transcribe(self) -> bool:
        spoken = self.filtered("can_transcribe")
        if not spoken:
            raise UserError(
                self.env._(
                    "Nothing here can be transcribed: either the file is not a "
                    "recording, or no speech engine is installed."
                )
            )
        for attachment in spoken:
            attachment._transcribe_later()
        return True

    def _transcribe_later(self, language: str | None = None) -> Any:
        self.check_singleton()
        job = self.delayed(
            channel=JOB_CHANNEL,
            identity_key=f"speech.transcribe.{self.id}",
            name=f"Transcribe {self.name or self.id}",
        )._job_transcribe(language=language)
        self.sudo().write({"speech_state": "queued", "speech_error": False})
        return job

    @api.job(channel=JOB_CHANNEL, max_retries=1)
    def _job_transcribe(self, language: str | None = None) -> None:
        self.check_singleton()
        self._transcribe(language=language)

    def _transcribe(self, language: str | None = None) -> list[Cue] | None:
        self.check_singleton()
        mimetype = self.mimetype or ""
        if not can_transcribe(mimetype, self.env):
            raise UserError(
                self.env._(
                    "No speech engine reads %(mimetype)s.", mimetype=mimetype or "?"
                )
            )
        self.sudo().write({"speech_state": "running"})
        try:
            cues, engine = self._speech_read(language)
        except Exception as error:
            # Recorded and not re-raised: an exception would roll back the very
            # write that says why this failed. Retrying a transient vendor
            # error is the orchestrator's fallback chain, one layer down.
            _logger.warning(
                "Could not transcribe attachment %s: %s", self.id, error, exc_info=True
            )
            self.sudo().write({"speech_state": "failed", "speech_error": str(error)})
            self._speech_notify_owner(transcribed=False)
            return None
        self.sudo().write(
            {
                "speech_state": "done",
                "speech_cues": [
                    {
                        "start": cue.start,
                        "end": cue.end,
                        "text": cue.text,
                        "speaker": cue.speaker,
                    }
                    for cue in cues
                ],
                "speech_engine": engine,
                "speech_language": language or self.speech_language,
                "speech_error": False,
            }
        )
        self._speech_index(cues)
        self._speech_notify_owner(transcribed=True)
        return cues

    def _speech_read(self, language: str | None = None) -> tuple[list[Cue], str]:
        self.check_singleton()
        document = self._speech_document(language=language)
        cues = document.cues
        failure = engine_error(document)
        if failure:
            raise UserError(failure)
        engine = next(iter(transcription_engines(document.mimetype, self.env)), None)
        return cues, engine.name if engine else ""

    def _speech_document(self, language: str | None = None, **options: Any) -> Document:
        self.check_singleton()
        raw = self.sudo().raw
        if not raw:
            raise UserError(self.env._("This attachment holds no data to transcribe."))
        return Document(
            raw,
            bare(self.mimetype or ""),
            self.name or "",
            env=self.env,
            read_up_to=EXPENSIVE,
            language=language or self.speech_language or None,
            **options,
        )

    def _speech_index(self, cues: list[Cue]) -> None:
        self.check_singleton()
        text = cues_as_text(cues)
        if not text:
            return
        limit = self._get_index_max_chars()
        indexed = text[:limit] if limit > 0 else text
        # Written in SQL because `_check_contents` strips `index_content` from
        # every create and write: the column is derived from the bytes, and a
        # recording's words cannot be derived from them without a network call.
        self.env.cr.execute(
            "UPDATE ir_attachment SET index_content = %s WHERE id = %s",
            (indexed, self.id),
        )
        self.invalidate_recordset(["index_content"])

    def _speech_notify_owner(self, transcribed: bool) -> None:
        self.check_singleton()
        segments = (
            self.env["media.segment"].sudo().search([("attachment_id", "=", self.id)])
        )
        for segment in segments:
            owner = segment._owner()
            if owner is None:
                continue
            if transcribed:
                done = getattr(owner, "_on_media_transcribed", None)
                if done is None:
                    continue
                done(self)
                if owner.transcription_state == "done":
                    owner._on_media_fully_transcribed()
            else:
                failed = getattr(owner, "_on_media_transcription_failed", None)
                if failed is not None:
                    failed(self)

    @api.model
    def _speech_synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
        language: str | None = None,
        mimetype: str = DEFAULT_SPEECH_MIMETYPE,
        name: str | None = None,
        res_model: str | None = None,
        res_id: int | None = None,
        **options: Any,
    ) -> Self:
        if not (text or "").strip():
            raise UserError(self.env._("There is nothing to read aloud."))
        engines = synthesis_engines(mimetype, self.env)
        if not engines:
            raise UserError(
                self.env._("No speech engine writes %(mimetype)s.", mimetype=mimetype)
            )
        # The engine is chosen here rather than left to `Document.of`, which
        # takes the first writer claiming the mimetype and cannot see that an
        # engine holds no credential. With two installed, that is the
        # difference between speaking and a vendor error.
        audio = engines[0].write(
            text,
            env=self.env,
            voice=voice,
            language=language,
            **options,
        )
        return self.create(
            {
                "name": name or self._speech_filename(mimetype),
                "raw": audio,
                "mimetype": mimetype,
                "res_model": res_model,
                "res_id": res_id,
            }
        )

    @api.model
    def _speech_filename(self, mimetype: str) -> str:
        extension = extension_for(mimetype) or mimetype.rsplit("/", 1)[-1]
        stamp = fields.Datetime.now().strftime("%Y-%m-%d-%H%M%S")
        return f"Speech-{stamp}.{extension}"
