from __future__ import annotations

import logging
from typing import Any

from odoo.libs.documents import CUES, EXPENSIVE, BaseReader, Cue, register_reader

from .selection import TRANSCRIPTION_CAPABILITIES, TRANSCRIPTION_KIND, pick_model, run
from odoo.addons.speech.tools.engines import SPOKEN_MIMETYPES, record_engine_error

_logger = logging.getLogger(__name__)


def _cue_of(span: dict) -> Cue:
    return Cue(
        start=float(span.get("start") or 0.0),
        end=float(span.get("end") or 0.0),
        text=(span.get("text") or "").strip(),
        speaker=span.get("speaker") or "",
    )


class AiTranscription(BaseReader):
    """The words a recording holds, read by whichever engine a key is held for."""

    name = "ai_transcription"
    mimetypes = SPOKEN_MIMETYPES
    yields = (CUES,)
    cost = EXPENSIVE

    def available(self, env: Any) -> bool:
        return bool(_pick_timed_model(env))

    def read(self, document: Any) -> list[Cue]:
        env = document.options.get("env")
        if env is None:
            _logger.info(
                "%r reached the transcription reader with no environment; "
                "a caller that wants a recording read passes env=",
                document.name,
            )
            return []
        model = _pick_timed_model(env)
        if not model:
            return []
        language = document.options.get("language")
        prompt = document.options.get("prompt")
        try:
            spans = run(
                env,
                "transcribe_timed",
                model,
                log_metadata={"feature": "speech.transcription"},
                audio=document.data,
                filename=document.name or "audio",
                mimetype=document.mimetype or "",
                language=language,
                prompt=prompt or "",
            ).cues
        except Exception as error:
            record_engine_error(document, error)
            raise
        return [
            _cue_of(span) for span in spans or [] if (span.get("text") or "").strip()
        ]


def _pick_timed_model(env: Any) -> Any:
    return pick_model(
        env, TRANSCRIPTION_KIND, required_capabilities=TRANSCRIPTION_CAPABILITIES
    )


register_reader(AiTranscription())
