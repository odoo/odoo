from __future__ import annotations

from typing import Any

from odoo.libs.documents import (
    ANY,
    CUES,
    RECORDING_MIMETYPES,
    TEXT,
    get_essential_mimetype,
    get_readers,
    get_writers,
)

DEFAULT_SPEECH_MIMETYPE = "audio/mpeg"


def is_recording(mimetype: str) -> bool:
    return get_essential_mimetype(mimetype or "") in RECORDING_MIMETYPES


def _is_usable(engine: Any, env: Any, purpose: str | None) -> bool:
    declared = getattr(engine, "available", None)
    return True if declared is None else bool(declared(env, purpose=purpose))


def transcription_engines(
    mimetype: str, env: Any = None, purpose: str | None = None
) -> tuple[Any, ...]:
    return tuple(
        reader
        for reader in get_readers(get_essential_mimetype(mimetype or ""), CUES)
        if ANY not in reader.mimetypes
        and (env is None or _is_usable(reader, env, purpose))
    )


def synthesis_engines(
    mimetype: str, env: Any = None, purpose: str | None = None
) -> tuple[Any, ...]:
    return tuple(
        writer
        for writer in get_writers(get_essential_mimetype(mimetype or ""), TEXT)
        if writer.mimetype != ANY and (env is None or _is_usable(writer, env, purpose))
    )


def can_transcribe(mimetype: str, env: Any = None, purpose: str | None = None) -> bool:
    return is_recording(mimetype) and bool(
        transcription_engines(mimetype, env, purpose)
    )


def can_synthesize(
    mimetype: str = DEFAULT_SPEECH_MIMETYPE,
    env: Any = None,
    purpose: str | None = None,
) -> bool:
    return bool(synthesis_engines(mimetype, env, purpose))


ENGINE_ERROR = "speech_engine_error"


def record_engine_error(document: Any, error: BaseException) -> None:
    document.options[ENGINE_ERROR] = str(error) or type(error).__name__


def engine_error(document: Any) -> str:
    return document.options.get(ENGINE_ERROR) or ""
