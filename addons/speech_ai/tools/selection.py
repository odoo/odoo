from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

from odoo.addons.gateway_ml.tools.ai_orchestrator import get_ai_orchestrator

_logger = logging.getLogger(__name__)

TRANSCRIPTION_KIND = "audio"
TRANSCRIPTION_CAPABILITIES = {"has_timestamps": True}
SYNTHESIS_KIND = "speech"


def pick_model(
    env: Any,
    kind: str,
    optimize_for: str = "balanced",
    provider_code: str | Iterable[str] | None = None,
    required_capabilities: dict | None = None,
) -> Any:
    model = get_ai_orchestrator(env).select_model(
        kind=kind,
        optimize_for=optimize_for,
        provider_code=provider_code,
        required_capabilities=required_capabilities,
    )
    if not model:
        _logger.info(
            "No %s model is configured with a usable credential for %s; speech "
            "stays unavailable rather than failing at a vendor call",
            kind,
            "any vendor" if provider_code is None else provider_code,
        )
    return model


def run(env: Any, model: Any, request_func: Any, log_metadata: dict | None = None):
    return get_ai_orchestrator(env).execute_with_fallback(
        model, request_func, log_metadata=log_metadata
    )
