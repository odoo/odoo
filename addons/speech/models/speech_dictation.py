from __future__ import annotations

from typing import Any

from odoo import api, fields, models

DICTATION_PURPOSE = "speech.transcription.dictation"
DICTATION_RETENTION_DAYS = 7


class SpeechDictation(models.Model):
    _name = "speech.dictation"
    _inherit = ["mixin.media.live"]
    _description = "Dictation"
    _order = "id desc"

    user_id = fields.Many2one(
        comodel_name="res.users",
        default=lambda self: self.env.user,
        index=True,
        readonly=True,
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        readonly=True,
        required=True,
    )
    res_model = fields.Char(
        string="Dictated into",
        readonly=True,
    )
    res_id = fields.Many2oneReference(
        model_field="res_model",
        readonly=True,
    )
    language = fields.Char(readonly=True)
    prompt = fields.Text(
        readonly=True,
        help="What the speaker is expected to talk about: names and terms the "
        "engine should recognise.",
    )

    @api.model
    def start_dictation(
        self,
        res_model: str | None = None,
        res_id: int | None = None,
        language: str | None = None,
        prompt: str | None = None,
    ) -> dict[str, Any]:
        if res_model and res_id:
            self.env[res_model].browse(res_id).check_access("read")
        dictation = self.create(
            {
                "res_model": res_model if res_id else False,
                "res_id": res_id or False,
                "language": language or False,
                "prompt": prompt or False,
            }
        )
        dictation.action_start_live()
        return {"id": dictation.id, "channel": dictation._live_channel_name()}

    def push_chunk(
        self,
        audio: str,
        start_s: float,
        duration_s: float = 0.0,
        mimetype: str = "audio/wav",
    ) -> int:
        self.check_singleton()
        segment = self._ingest_live_chunk(
            self._decode_live_audio(audio),
            float(start_s),
            float(duration_s),
            mimetype,
        )
        return segment.id

    def _media_transcription_options(self) -> dict:
        self.check_singleton()
        return {
            "purpose": DICTATION_PURPOSE,
            "language": self.language or None,
            "prompt": self.prompt or None,
        }

    def _media_retention_days(self) -> int:
        return DICTATION_RETENTION_DAYS
