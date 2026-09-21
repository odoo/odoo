from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

from odoo.addons.gateway_ml.tools.router import MlRequest, get_router

_logger = logging.getLogger(__name__)

TRANSCRIPTION_KIND = "audio"
TRANSCRIPTION_CAPABILITIES = {"has_timestamps": True}
TRANSCRIPTION_PURPOSE = "speech.transcription"
SYNTHESIS_KIND = "speech"
SYNTHESIS_PURPOSE = "speech.synthesis"


def company_id_of(env: Any, options: dict) -> int:
    return (options.get("company") or env.company).id


def pick_model(
    env: Any,
    kind: str,
    *,
    company_id: int,
    purpose: str,
    optimize_for: str = "balanced",
    provider_code: str | Iterable[str] | None = None,
    required_capabilities: dict | None = None,
) -> Any:
    model = get_router(env).select_model(
        kind,
        company_id=company_id,
        purpose=purpose,
        optimize_for=optimize_for,
        provider_code=provider_code,
        required_capabilities=required_capabilities,
    )
    if not model:
        _logger.info(
            "No %s model may serve %s in company %s: none has a usable credential, "
            "or the company's policy names none of their vendors",
            kind,
            purpose,
            company_id,
        )
    return model


def run(
    env: Any,
    operation: str,
    model: Any,
    *,
    company_id: int,
    purpose: str,
    **request: Any,
) -> Any:
    return get_router(env).run(
        operation,
        MlRequest(purpose=purpose, **request),
        model=model,
        company_id=company_id,
    )
