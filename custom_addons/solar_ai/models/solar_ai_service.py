import json
import logging
from datetime import datetime

import httpx

from odoo import models

_logger = logging.getLogger(__name__)

CLASSIFICATION_SYSTEM_PROMPT = """You are a document classifier for solar energy installation projects.
Given document text, classify it into one of the following types and return JSON:
{"document_type_code": "<code>", "confidence": <0.0-1.0>, "extracted_summary": "<brief summary>"}

Document type codes:
- bill_electricity: electricity consumption bill
- roof_measurement: roof measurement or survey report
- site_plan_bti: site plan, BTI (Bureau of Technical Inventory) scheme
- topographic_survey: topographic survey map
- client_brief: client requirements or technical brief
- equipment_spec: equipment datasheet or specification
- single_line_diagram: electrical single-line or wiring diagram
- permit: building or grid connection permit
- handover_act: handover or acceptance act
- commissioning_report: commissioning or testing report
- structural_calculation: structural engineering calculation
- grid_connection_agreement: grid connection agreement
- unknown: none of the above

Respond with ONLY the JSON object, no markdown fences."""


class SolarAiService(models.AbstractModel):
    _name = "solar.ai.service"
    _description = "Solar AI LLM Service (OpenRouter)"

    def _get_config(self, key, default=None):
        return (
            self.env["ir.config_parameter"].sudo().get_param(f"solar_ai.{key}", default)
        )

    def _build_headers(self):
        api_key = self._get_config("openrouter_api_key")
        if not api_key:
            return None
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://isolar.ua",
            "X-Title": "iSolar Odoo",
        }

    def chat(self, messages, model=None, tools=None, timeout=30):
        """Send a chat completion request to OpenRouter.

        Returns {'content': str, 'usage': dict, 'elapsed_ms': int} or error dict.
        """
        headers = self._build_headers()
        if not headers:
            _logger.warning(
                "solar_ai: no OpenRouter API key configured — skipping LLM call"
            )
            return {"content": "", "usage": {}}

        base_url = self._get_config(
            "openrouter_base_url", "https://openrouter.ai/api/v1"
        )
        model = model or self._get_config(
            "default_model", "anthropic/claude-sonnet-4-5"
        )

        payload = {"model": model, "messages": messages}
        if tools:
            payload["tools"] = tools

        started_at = datetime.now()
        try:
            resp = httpx.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=timeout,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _logger.error(
                "solar_ai: OpenRouter HTTP error %s: %s",
                exc.response.status_code,
                exc.response.text[:300],
            )
            return {"content": "", "usage": {}, "error": str(exc)}
        except httpx.RequestError as exc:
            _logger.error("solar_ai: OpenRouter request error: %s", exc)
            return {"content": "", "usage": {}, "error": str(exc)}

        data = resp.json()
        elapsed_ms = int((datetime.now() - started_at).total_seconds() * 1000)
        _logger.info(
            "solar_ai: LLM call complete in %dms (model=%s)", elapsed_ms, model
        )

        return {
            "content": data["choices"][0]["message"]["content"],
            "usage": data.get("usage", {}),
            "elapsed_ms": elapsed_ms,
        }

    def classify_document_text(self, text, max_chars=4000):
        """Classify document text, return dict with 'document_type_code' and 'confidence'."""
        truncated = text[:max_chars] if len(text) > max_chars else text
        messages = [
            {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
            {"role": "user", "content": truncated},
        ]
        result = self.chat(messages)
        try:
            return json.loads(result["content"])
        except (json.JSONDecodeError, KeyError):
            return {"document_type_code": "unknown", "confidence": 0.0}
