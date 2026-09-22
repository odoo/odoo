from __future__ import annotations

import logging
from typing import Any, Self

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.libs.documents import (
    CUES,
    EXPENSIVE,
    Cue,
    Document,
    cues_as_text,
    extension_for,
)

from ..tools.engines import (
    DEFAULT_SPEECH_MIMETYPE,
    can_transcribe,
    engine_error,
    is_recording,
    synthesis_engines,
)

_logger = logging.getLogger(__name__)

JOB_CHANNEL = "speech"

TRANSCRIPT_STATES = [
    ("none", "Not transcribed"),
    ("queued", "Queued"),
    ("running", "Transcribing"),
    ("done", "Transcribed"),
    ("failed", "Failed"),
]


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    transcript_state = fields.Selection(
        selection=TRANSCRIPT_STATES,
        default="none",
        index="btree_not_null",
        copy=False,
        readonly=True,
    )
    transcript_cues = fields.Json(
        copy=False,
        readonly=True,
        help="What is said in this recording, with the moment each phrase "
        "starts and ends.",
    )
    transcript_language = fields.Char(
        copy=False,
        readonly=True,
    )
    transcript_engine = fields.Char(
        copy=False,
        readonly=True,
    )
    transcript_error = fields.Text(
        copy=False,
        readonly=True,
    )
    transcript_text = fields.Text(compute="_compute_transcript_text")
    can_transcribe = fields.Boolean(compute="_compute_can_transcribe")
    speaker_ids = fields.One2many(
        comodel_name="speech.speaker",
        inverse_name="attachment_id",
        string="Speakers",
    )

    @api.depends("transcript_cues")
    def _compute_transcript_text(self) -> None:
        for attachment in self:
            attachment.transcript_text = cues_as_text(attachment._transcript_cues())

    @api.depends("mimetype", "company_id")
    def _compute_can_transcribe(self) -> None:
        self.can_transcribe = False
        recordings = self.filtered(lambda a: is_recording(a.mimetype or ""))
        if not recordings:
            return
        purposes = recordings._transcript_purposes()
        readable = {}
        for attachment in recordings:
            company = attachment.company_id or self.env.company
            purpose = purposes.get(attachment.id)
            key = (attachment.mimetype, company, purpose)
            if key not in readable:
                readable[key] = can_transcribe(
                    attachment.mimetype or "",
                    self.with_company(company).env,
                    purpose,
                )
            attachment.can_transcribe = readable[key]

    def _transcript_purposes(self) -> dict[int, str | None]:
        segments = (
            self.env["media.segment"].sudo().search([("attachment_id", "in", self.ids)])
        )
        options_by_owner = {}
        purposes = {}
        for segment in segments:
            owner = segment._owner()
            if owner is None or not hasattr(owner, "_media_transcription_options"):
                continue
            key = (owner._name, owner.id)
            if key not in options_by_owner:
                options_by_owner[key] = owner._media_transcription_options()
            purposes[segment.attachment_id.id] = options_by_owner[key].get("purpose")
        return purposes

    def _transcript_cues(self) -> list[Cue]:
        self.check_singleton()
        return [
            Cue(
                start=cue.get("start", 0.0),
                end=cue.get("end", 0.0),
                text=cue.get("text", ""),
                speaker=cue.get("speaker", ""),
                confidence=cue.get("confidence", 0.0),
            )
            for cue in self.transcript_cues or []
        ]

    def _transcript_vtt(self) -> str:
        self.check_singleton()
        cues = self._transcript_cues()
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

    def _transcribe_later(
        self,
        language: str | None = None,
        priority: int | None = None,
        eta: Any = None,
    ) -> Any:
        self.check_singleton()
        identity_key = f"speech.transcribe.{self.id}"
        job = self.delayed(
            channel=JOB_CHANNEL,
            identity_key=identity_key,
            name=f"Transcribe {self.name or self.id}",
            priority=priority,
            eta=eta,
        )._job_transcribe(language=language)
        if eta is None:
            self.env["ir.job"].sudo().search(
                [("identity_key", "=", identity_key), ("state", "=", "scheduled")]
            ).write({"eta": False})
        self.sudo().write({"transcript_state": "queued", "transcript_error": False})
        return job

    @api.job(channel=JOB_CHANNEL, max_retries=1)
    def _job_transcribe(self, language: str | None = None) -> None:
        self.check_singleton()
        self._transcribe(language=language)

    def _transcribe(
        self, language: str | None = None, prompt: str | None = None
    ) -> list[Cue] | None:
        self.check_singleton()
        mimetype = self.mimetype or ""
        company = self.company_id or self.env.company
        purpose = self._transcript_owner_options().get("purpose")
        if not can_transcribe(mimetype, self.with_company(company).env, purpose):
            raise UserError(
                self.env._(
                    "No speech engine reads %(mimetype)s.", mimetype=mimetype or "?"
                )
            )
        self.sudo().write({"transcript_state": "running"})
        try:
            cues, engine = self._read_transcript(language, prompt)
        except Exception as error:
            _logger.warning(
                "Could not transcribe attachment %s: %s", self.id, error, exc_info=True
            )
            self.sudo().write(
                {"transcript_state": "failed", "transcript_error": str(error)}
            )
            self._notify_transcript_owner(transcribed=False)
            return None
        self.sudo().write(
            {
                "transcript_state": "done",
                "transcript_cues": [
                    {
                        "start": cue.start,
                        "end": cue.end,
                        "text": cue.text,
                        "speaker": cue.speaker,
                        "confidence": cue.confidence,
                    }
                    for cue in cues
                ],
                "transcript_engine": engine,
                "transcript_language": language or self.transcript_language,
                "transcript_error": False,
            }
        )
        self._index_transcript(cues)
        self.env["speech.speaker"]._sync_from_cues(self)
        self._notify_transcript_owner(transcribed=True)
        return cues

    def _read_transcript(
        self, language: str | None = None, prompt: str | None = None
    ) -> tuple[list[Cue], str]:
        self.check_singleton()
        document = self._transcript_document(language=language, prompt=prompt)
        cues = document.cues
        failure = engine_error(document)
        if failure and not cues:
            raise UserError(failure)
        return cues, document.read_by(CUES)

    def _transcript_document(
        self, language: str | None = None, **options: Any
    ) -> Document:
        self.check_singleton()
        owner_options = self._transcript_owner_options()
        document = self._as_document(
            read_up_to=EXPENSIVE,
            **{
                **owner_options,
                **{key: value for key, value in options.items() if value},
                "language": language
                or self.transcript_language
                or owner_options.get("language")
                or None,
            },
        )
        if document is None:
            raise UserError(self.env._("This attachment holds no data to transcribe."))
        return document

    def _transcript_owner_options(self) -> dict[str, Any]:
        self.check_singleton()
        segment = (
            self.env["media.segment"]
            .sudo()
            .search([("attachment_id", "=", self.id)], limit=1)
        )
        owner = segment._owner() if segment else None
        if owner is None or not hasattr(owner, "_media_transcription_options"):
            return {}
        return owner._media_transcription_options()

    def _index_transcript(self, cues: list[Cue]) -> None:
        self.check_singleton()
        text = cues_as_text(cues)
        if not text:
            return
        limit = self._get_index_max_chars()
        indexed = text[:limit] if limit > 0 else text
        self.env.cr.execute(
            "UPDATE ir_attachment SET index_content = %s WHERE id = %s",
            (indexed, self.id),
        )
        self.invalidate_recordset(["index_content"])

    def _notify_transcript_owner(self, transcribed: bool) -> None:
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
                if owner.timeline_transcript_state == "done":
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
