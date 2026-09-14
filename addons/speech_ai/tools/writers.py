from __future__ import annotations

import logging
from typing import Any

from odoo.libs.documents import TEXT, BaseWriter, register_writer

from .selection import SYNTHESIS_KIND, pick_model, run
from odoo.addons.gateway_ml.tools.ai_clients import AI_CLIENT_REGISTRY
from odoo.addons.gateway_ml.tools.vendor_catalog import PROVIDERS

_logger = logging.getLogger(__name__)


def written_by(vendor: str) -> frozenset[str]:
    for spec in PROVIDERS.values():
        if spec.get("speech_service") == vendor:
            return frozenset(spec.get("speech_mimetypes") or {})
    client = AI_CLIENT_REGISTRY.get(vendor)
    return frozenset(getattr(client, "SPEECH_ENCODINGS", None) or ())


def _vendors() -> frozenset[str]:
    named = {
        spec["speech_service"] for spec in PROVIDERS.values() if spec.get("speech")
    }
    return frozenset(named | set(AI_CLIENT_REGISTRY))


def _written_mimetypes() -> frozenset[str]:
    spoken: set[str] = set()
    for vendor in _vendors():
        spoken |= written_by(vendor)
    return frozenset(spoken)


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
            vendor for vendor in _vendors() if self.mimetype in written_by(vendor)
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
            model,
            lambda client, ai_model: _speak(
                client, ai_model, str(value), options, self.mimetype
            ),
            log_metadata={"feature": "speech.synthesis"},
        )


def _speak(
    client: Any, ai_model: Any, text: str, options: dict, mimetype: str
) -> bytes:
    speaker = getattr(client, "synthesize", None)
    if speaker is None:
        raise NotImplementedError(f"{type(client).__name__} does not speak")
    return speaker(
        text,
        voice=options.get("voice"),
        mimetype=mimetype,
        model=ai_model.code,
    )


for _mimetype in sorted(_written_mimetypes()):
    register_writer(AiSpeech(_mimetype))
