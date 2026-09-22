from __future__ import annotations

import logging
from typing import Any

from odoo.exceptions import UserError
from odoo.libs.documents import (
    CUES,
    EXPENSIVE,
    RECORDING_MIMETYPES,
    BaseReader,
    Cue,
    register_reader,
)
from odoo.tools import human_size

from .selection import (
    TRANSCRIPTION_CAPABILITIES,
    TRANSCRIPTION_KIND,
    TRANSCRIPTION_PURPOSE,
    company_id_of,
    pick_model,
    run,
)
from odoo.addons.gateway_ml.tools.router import get_router
from odoo.addons.speech.tools.engines import record_engine_error

_logger = logging.getLogger(__name__)


def _cue_of(span: dict) -> Cue:
    index = span.get("speaker_index")
    return Cue(
        start=float(span.get("start") or 0.0),
        end=float(span.get("end") or 0.0),
        text=(span.get("text") or "").strip(),
        speaker=f"SPEAKER_{index}" if index is not None else span.get("speaker") or "",
        confidence=float(span.get("confidence") or 0.0),
    )


class AiTranscription(BaseReader):
    """The words a recording holds, read by whichever engine a key is held for."""

    name = "ai_transcription"
    mimetypes = RECORDING_MIMETYPES
    yields = (CUES,)
    cost = EXPENSIVE

    def available(self, env: Any, purpose: str | None = None) -> bool:
        return bool(
            _pick_timed_model(env, env.company.id, purpose or TRANSCRIPTION_PURPOSE)
        )

    def read(self, document: Any) -> list[Cue]:
        env = document.options.get("env")
        if env is None:
            _logger.info(
                "%r reached the transcription reader with no environment; "
                "a caller that wants a recording read passes env=",
                document.name,
            )
            return []
        company_id = company_id_of(env, document.options)
        purpose = document.options.get("purpose") or TRANSCRIPTION_PURPOSE
        model = _pick_timed_model(env, company_id, purpose)
        if not model:
            return []
        language = document.options.get("language")
        prompt = document.options.get("prompt")
        company = env["res.company"].browse(company_id)
        try:
            _check_capacity(env, model, document, company_id, purpose)
            spans = run(
                env,
                "transcribe_timed",
                model,
                company_id=company_id,
                purpose=purpose,
                audio=document.data,
                filename=document.name or "audio",
                mimetype=document.mimetype or "",
                language=language,
                prompt=prompt or "",
                vocabulary=tuple(env["speech.vocabulary"]._keyterms(company)),
                speakers=True,
            ).cues
        except Exception as error:
            record_engine_error(document, error)
            raise
        return [
            _cue_of(span) for span in spans or [] if (span.get("text") or "").strip()
        ]


def _pick_timed_model(env: Any, company_id: int, purpose: str) -> Any:
    return pick_model(
        env,
        TRANSCRIPTION_KIND,
        company_id=company_id,
        purpose=purpose,
        required_capabilities=TRANSCRIPTION_CAPABILITIES,
    )


register_reader(AiTranscription())


def _check_capacity(env: Any, model: Any, document: Any, company_id: int, purpose: str):
    capacity = get_router(env).audio_capacity(
        model, company_id=company_id, purpose=purpose
    )
    if capacity and len(document.data) > capacity:
        raise UserError(
            env._(
                "The recording weighs %(size)s and %(vendor)s accepts at most "
                "%(capacity)s.",
                size=human_size(len(document.data)),
                vendor=model.provider_id.name,
                capacity=human_size(capacity),
            )
        )
