from __future__ import annotations

import typing
from collections import defaultdict

from odoo import fields, models
from odoo.libs.documents import Document, format_offset, parse_offset

from ..tools.schema import DOCUMENT_TYPE

if typing.TYPE_CHECKING:
    from odoo.addons.extract.tools import ExtractionResult

FINDINGS = ("speech.commitment", "speech.question", "speech.moment")


class MixinSpeechAnalysis(models.AbstractModel):
    _name = "mixin.speech.analysis"
    _inherit = ["mixin.media.timeline", "mixin.extract"]
    _description = "Speech Analysis"
    _extract_document_type = DOCUMENT_TYPE

    analysis_summary = fields.Text(
        copy=False,
        readonly=True,
    )
    analysis_topics = fields.Text(
        copy=False,
        readonly=True,
    )
    commitment_ids = fields.One2many(
        comodel_name="speech.commitment",
        inverse_name="res_id",
        string="Commitments",
        domain=lambda self: [("res_model", "=", self._name)],
    )
    question_ids = fields.One2many(
        comodel_name="speech.question",
        inverse_name="res_id",
        string="Questions",
        domain=lambda self: [("res_model", "=", self._name)],
    )
    moment_ids = fields.One2many(
        comodel_name="speech.moment",
        inverse_name="res_id",
        string="Moments",
        domain=lambda self: [("res_model", "=", self._name)],
    )

    def _speech_analysis_ready(self) -> bool:
        return True

    def _on_media_fully_transcribed(self) -> None:
        super()._on_media_fully_transcribed()
        for record in self:
            if record._speech_analysis_ready() and record.timeline_transcript:
                record._extract_later()

    def action_analyse_speech(self) -> bool:
        return self.action_extract_later()

    def _get_extract_source(self) -> Document | None:
        self.check_singleton()
        text, _voices = self._analysis_transcript()
        if not text:
            return None
        options = {}
        if "company_id" in self._fields and self.company_id:
            options["company"] = self.company_id
        return Document(
            text.encode(), "text/plain", f"{self.display_name}.txt", **options
        )

    def _analysis_transcript(self) -> tuple[str, dict[str, models.Model]]:
        self.check_singleton()
        segments = self.segment_ids.sorted("start_ms")
        several = len(segments) > 1
        lines = []
        voices = defaultdict(lambda: self.env["speech.speaker"])
        for index, segment in enumerate(segments, 1):
            attachment = segment.attachment_id
            by_label = {speaker.label: speaker for speaker in attachment.speaker_ids}
            for cue in attachment.transcript_cues or []:
                words = (cue.get("text") or "").strip()
                if not words:
                    continue
                label = cue.get("speaker") or ""
                speaker = by_label.get(label)
                shown = _shown(speaker, label, index if several else 0)
                if speaker:
                    voices[shown] |= speaker
                at = segment.start_ms / 1000 + (cue.get("start") or 0.0)
                lines.append(
                    f"[{format_offset(at)}] {shown}: {words}"
                    if shown
                    else f"[{format_offset(at)}] {words}"
                )
        return "\n".join(lines), dict(voices)

    def _update_from_extraction(self, result: ExtractionResult) -> None:
        self.check_singleton()
        values = result.flat()
        _text, voices = self._analysis_transcript()
        self.write(
            {
                "analysis_summary": values.get("summary") or False,
                "analysis_topics": "\n".join(
                    row["name"] for row in values.get("topics") or []
                )
                or False,
            }
        )
        for model in FINDINGS:
            self.env[model]._of(self).unlink()
        self._create_findings(values, voices)
        self._rate_speakers(values.get("speakers") or [], voices)

    def _create_findings(self, values: dict, voices: dict[str, models.Model]) -> None:
        owner = {"res_model": self._name, "res_id": self.id}

        def found(row: dict, speaker_key: str) -> dict:
            return {
                **owner,
                "at_s": parse_offset(row.get("at")) or 0.0,
                "speaker_id": voices.get(
                    row.get(speaker_key) or "", self.env["speech.speaker"]
                )[:1].id,
            }

        self.env["speech.commitment"].create(
            [
                {
                    **found(row, "who"),
                    "name": row["what"],
                    "due_date": row.get("due") or False,
                }
                for row in values.get("commitments") or []
            ]
        )
        self.env["speech.question"].create(
            [
                {
                    **found(row, "asked_by"),
                    "name": row["question"],
                    "answered": bool(row.get("answered")),
                    "answer": row.get("answer") or False,
                }
                for row in values.get("questions") or []
            ]
        )
        self.env["speech.moment"].create(
            [
                {
                    **found(row, "speaker"),
                    "name": row["quote"],
                    "kind": row["kind"],
                }
                for row in values.get("moments") or []
            ]
        )

    def _rate_speakers(self, rows: list[dict], voices: dict[str, models.Model]) -> None:
        self.timeline_speaker_ids.sudo().write(
            {
                "sentiment": False,
                "engagement": False,
                "interruptions": 0,
                "questions_asked": 0,
            }
        )
        for row in rows:
            speakers = voices.get(row["speaker"])
            if not speakers:
                continue
            speakers.sudo().write(
                {
                    "sentiment": row.get("sentiment") or False,
                    "engagement": row.get("engagement") or False,
                    "interruptions": row.get("interruptions") or 0,
                    "questions_asked": row.get("questions_asked") or 0,
                }
            )


def _shown(speaker: models.Model | None, label: str, segment: int) -> str:
    if speaker and speaker.partner_id:
        return speaker.partner_id.name
    if speaker and speaker.name and speaker.name != label:
        return speaker.name
    if label and segment:
        return f"{label}/{segment}"
    return label
