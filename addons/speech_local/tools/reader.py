from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from odoo.libs.documents import (
    CUES,
    EXPENSIVE,
    RECORDING_MIMETYPES,
    BaseReader,
    Cue,
    register_reader,
)
from odoo.tools import config

from .engine import LocalEngine
from odoo.addons.media.tools.audio import decode_audio
from odoo.addons.speech.tools.engines import record_engine_error

_logger = logging.getLogger(__name__)

MODEL_DIR_PARAM = "speech_local.model_dir"

_ENGINES: dict[Path, LocalEngine] = {}
_REPORTED: set[Path] = set()


def model_dir(env: Any) -> Path:
    configured = env["ir.config_parameter"].sudo().get_param(MODEL_DIR_PARAM)
    if configured:
        return Path(configured)
    return Path(config["data_dir"]) / "models" / "speech_local"


def local_engine(env: Any) -> LocalEngine | None:
    if "speech_local" not in env.registry.loaded_modules:
        return None
    directory = model_dir(env)
    if directory in _ENGINES:
        return _ENGINES[directory]
    missing = LocalEngine.missing_files(directory)
    if missing:
        if directory not in _REPORTED:
            _REPORTED.add(directory)
            _logger.info(
                "No local transcription: %s lacks %s",
                directory,
                ", ".join(missing),
            )
        return None
    return _ENGINES.setdefault(directory, LocalEngine(directory))


class LocalTranscription(BaseReader):
    name = "local_transcription"
    mimetypes = RECORDING_MIMETYPES
    yields = (CUES,)
    cost = EXPENSIVE
    defers = True

    def available(self, env: Any) -> bool:
        return local_engine(env) is not None

    def read(self, document: Any) -> list[Cue] | None:
        env = document.options.get("env")
        if env is None:
            return None
        engine = local_engine(env)
        if engine is None:
            return None
        try:
            return engine.transcribe(
                decode_audio(document.data), document.options.get("language")
            )
        except Exception as error:
            record_engine_error(document, error)
            raise


register_reader(LocalTranscription())
