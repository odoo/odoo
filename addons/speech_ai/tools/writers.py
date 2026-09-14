from __future__ import annotations

import logging
from typing import Any

from odoo.libs.documents import TEXT, BaseWriter, register_writer

from .selection import SYNTHESIS_KIND, pick_model, run

_logger = logging.getLogger(__name__)


SPEECH_MIMETYPES = frozenset(
    {"audio/aac", "audio/flac", "audio/mpeg", "audio/ogg", "audio/wav"}
)


def _speech_operations(env: Any) -> Any:
    return (
        env["gateway.ml.provider.service"]
        .sudo()
        .search([("operation", "=", "synthesize")])
    )


def written_by(env: Any, vendor: str) -> frozenset[str]:
    return frozenset(
        mimetype
        for operation in _speech_operations(env)
        if operation.service_id.code == vendor
        for mimetype in (operation.formats or {})
    )


def _vendors(env: Any) -> frozenset[str]:
    return frozenset(_speech_operations(env).mapped("service_id.code"))


class AiSpeech(BaseWriter):
    """Words as audio, spoken by whichever engine a key is held for."""

    name = "ai_speech"
    mimetype = ""
    consumes = TEXT

    def __init__(self, mimetype: str) -> None:
        self.name = f"ai_speech_{mimetype.rsplit('/', 1)[-1]}"
        self.mimetype = mimetype

    def available(self, env: Any) -> bool:
        return bool(self._pick_model(env))

    def _pick_model(self, env: Any) -> Any:
        writing = [
            vendor
            for vendor in _vendors(env)
            if self.mimetype in written_by(env, vendor)
        ]
        return pick_model(env, SYNTHESIS_KIND, provider_code=writing)

    def write(self, value: Any, **options: Any) -> bytes:
        env = options.get("env")
        if env is None:
            raise ValueError(
                "Speech synthesis needs an environment: pass env= to write audio"
            )
        model = self._pick_model(env)
        if not model:
            raise ValueError("No speech model is configured with a usable credential")
        return run(
            env,
            "synthesize",
            model,
            log_metadata={"feature": "speech.synthesis"},
            text=str(value),
            voice=options.get("voice"),
            mimetype=self.mimetype,
        ).audio


for _mimetype in sorted(SPEECH_MIMETYPES):
    register_writer(AiSpeech(_mimetype))
