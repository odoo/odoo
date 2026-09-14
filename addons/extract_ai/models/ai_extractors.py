from __future__ import annotations

import base64
import logging
from typing import Any

from .prompt import prepare_prompt
from odoo.addons.extract.tools import (
    GENERATIVE,
    BaseExtractor,
    known_schemas,
)
from odoo.addons.extract.tools.schema import get_schema
from odoo.addons.gateway_ml.tools import MlRequest, get_router, parse_json_response

_logger = logging.getLogger(__name__)

TEMPERATURE = 0.1


class _AiExtractor(BaseExtractor):
    cost = GENERATIVE
    optimize_for = "cost"

    @property
    def doc_types(self) -> tuple[str, ...]:
        return known_schemas()

    def _get_model(self, env, doc_type: str):
        raise NotImplementedError

    def _request(self, source, prompt: str) -> MlRequest:
        raise NotImplementedError

    def extract(
        self,
        source,
        doc_type: str,
        wanted: tuple[str, ...],
        env: Any = None,
    ) -> dict[str, Any] | None:
        if env is None:
            _logger.debug("%s needs an environment for the company's keys", self.name)
            return None

        model = self._get_model(env, doc_type)
        if not model:
            _logger.info(
                "%s: no model available for %s in this company", self.name, doc_type
            )
            return None

        prompt = prepare_prompt(get_schema(doc_type), wanted)
        try:
            result = get_router(env).run(
                "chat",
                self._request(source, prompt),
                model=model,
                log_metadata={"origin_model": "document.extract"},
                company_id=env.company.id,
            )
            return parse_json_response(result.text, env, expect=(dict,))
        except Exception:
            _logger.exception(
                "%s could not read %r; the cascade continues without it",
                self.name,
                source.name or source.mimetype,
            )
            return None


class LlmTextExtractor(_AiExtractor):
    name = "llm_text"
    needs = ("text",)
    confidence = 0.5

    def _get_model(self, env, doc_type):
        return get_router(env).select_model(
            "chat",
            optimize_for=self.optimize_for,
            company_id=env.company.id,
        )

    def _request(self, source, prompt):
        return MlRequest(
            prompt=f"{prompt}\n\nDocument text:\n{source.text}",
            temperature=TEMPERATURE,
        )


class LlmVisionExtractor(_AiExtractor):
    name = "llm_vision"
    needs = ("images",)
    confidence = 0.45

    def _get_model(self, env, doc_type):
        return get_router(env).select_model(
            ("chat", "vision"),
            use_case_tags=["vision", "ocr"],
            required_capabilities={"has_vision": True},
            optimize_for=self.optimize_for,
            company_id=env.company.id,
        )

    def _request(self, source, prompt):
        page = source.images[0]
        return MlRequest(
            prompt=prompt,
            images=((base64.b64encode(page).decode("utf-8"), _media_type(page)),),
            temperature=TEMPERATURE,
        )


def _media_type(image: bytes) -> str:
    if image.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if image[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if image.startswith(b"RIFF") and b"WEBP" in image[:16]:
        return "image/webp"
    if image.startswith(b"BM"):
        return "image/bmp"
    raise ValueError("The rendered page is not an image this reader can send.")
