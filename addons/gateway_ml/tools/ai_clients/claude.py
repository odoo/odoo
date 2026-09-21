import json
import logging

from ..wire_formats import get_anthropic_content, read_anthropic_content
from .base import BaseAIClient
from odoo.addons.integration.tools.exceptions import CommError

_logger = logging.getLogger(__name__)


_SAMPLING_PARAMS = ("temperature", "top_p", "top_k")

_FORCED_TOOL_CHOICES = ("any", "tool")

_UNSUPPORTED_SCHEMA_KEYWORDS = frozenset(
    {
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "multipleOf",
        "minLength",
        "maxLength",
    }
)


def get_json_output_config(schema):
    return {"format": {"type": "json_schema", "schema": _close_schema(schema)}}


_SCHEMA_MAPS = ("properties", "patternProperties", "$defs", "definitions")

_SCHEMA_LISTS = ("anyOf", "allOf", "oneOf", "prefixItems")

_SCHEMA_CHILDREN = ("items", "not", "contains", "additionalProperties")


def _close_schema(schema):
    if not isinstance(schema, dict):
        return schema
    closed = {}
    for key, value in schema.items():
        if key in _UNSUPPORTED_SCHEMA_KEYWORDS:
            continue
        if key in _SCHEMA_MAPS and isinstance(value, dict):
            closed[key] = {name: _close_schema(child) for name, child in value.items()}
        elif (key in _SCHEMA_LISTS or key == "items") and isinstance(value, list):
            closed[key] = [_close_schema(child) for child in value]
        elif key in _SCHEMA_CHILDREN:
            closed[key] = _close_schema(value)
        else:
            closed[key] = value
    types = closed.get("type")
    if (
        "properties" in closed
        or types == "object"
        or (isinstance(types, list) and "object" in types)
    ):
        closed.setdefault("additionalProperties", False)
    return closed


class ClaudeClient(BaseAIClient):
    ENDPOINT_CODE = "claude"

    FALLBACK_MODEL = "claude-sonnet-5"

    MAX_TOKENS_LIMIT = 128000

    DEFAULT_MAX_TOKENS = 16000

    def _accepts_sampling(self, model):
        row = self._get_model_rows().get(model)
        return row.sampling_params if row else True

    def _accepts_forced_tool(self, model):
        row = self._get_model_rows().get(model)
        return row.forced_tool_choice if row else True

    def _extract_text_from_response(self, result):
        text, problem = read_anthropic_content(result)
        if problem:
            _logger.error(
                "Claude API returned no usable text content: %s. Response: %s",
                problem,
                result,
            )
            raise CommError(f"Claude API returned no usable text content: {problem}")
        return text

    def _prepare_payload(self, model, messages, **params):
        payload = {
            "model": model,
            "messages": messages,
            **{key: value for key, value in params.items() if value is not None},
        }
        if not self._accepts_sampling(model):
            dropped = [key for key in _SAMPLING_PARAMS if payload.pop(key, None)]
            if dropped:
                _logger.debug("%s takes no sampling; dropped %s", model, dropped)
        return payload

    def create_message(
        self,
        messages,
        model=None,
        max_tokens=DEFAULT_MAX_TOKENS,
        temperature=1.0,
        system=None,
        thinking=None,
        **kwargs,
    ):
        model = self._resolve_model(model)
        self._check_params(model=model, temperature=temperature, max_tokens=max_tokens)
        forced = (kwargs.get("tool_choice") or {}).get("type") in _FORCED_TOOL_CHOICES
        if forced and not self._accepts_forced_tool(model):
            raise ValueError(
                f"{model} rejects a forced tool_choice; ask for "
                f"output_config=get_json_output_config(schema) instead",
            )
        payload = self._prepare_payload(
            model,
            messages,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system or None,
            thinking=thinking or None,
            **kwargs,
        )
        _logger.debug(
            "Claude create_message request: model=%s, messages=%s",
            model,
            len(messages),
        )
        try:
            response = self._client.post("/messages", json=payload)
        except CommError:
            raise
        except Exception as e:
            _logger.exception("Unexpected error in Claude create_message")
            raise CommError(f"Claude create_message failed: {e!s}") from e
        return self._get_response_body(response)

    def complete(
        self,
        prompt,
        *,
        system="",
        images=(),
        response_schema=None,
        structured_output="prompted",
        model=None,
        **kwargs,
    ):
        messages = [{"role": "user", "content": get_anthropic_content(prompt, images)}]
        if system:
            kwargs["system"] = system
        if response_schema is None:
            return self._complete(messages, model, **kwargs)
        answer = self._get_forced_tool_input(
            messages,
            "respond",
            "Give the answer in this shape.",
            response_schema,
            model,
            **kwargs,
        )
        return json.dumps(answer, ensure_ascii=False)

    def _complete(self, messages, model, **kwargs):
        result = self.create_message(messages=messages, model=model, **kwargs)
        return self._extract_text_from_response(result)

    def _get_forced_tool_input(
        self, messages, tool_name, tool_description, schema, model, **kwargs
    ):
        model = self._resolve_model(model)
        if not self._accepts_forced_tool(model):
            return self._get_json_output(messages, schema, model, **kwargs)
        response = self.create_message(
            messages=messages,
            tools=[
                {
                    "name": tool_name,
                    "description": tool_description,
                    "input_schema": schema,
                },
            ],
            tool_choice={"type": "tool", "name": tool_name},
            model=model,
            **kwargs,
        )
        for block in response.get("content") or []:
            if block.get("type") == "tool_use" and block.get("name") == tool_name:
                return block.get("input") or {}
        raise CommError(
            f"Claude answered without calling {tool_name!r} "
            f"(stop_reason={response.get('stop_reason')})",
        )

    def _get_json_output(self, messages, schema, model, **kwargs):
        output_config = {
            **(kwargs.pop("output_config", None) or {}),
            **get_json_output_config(schema),
        }
        text = self._complete(messages, model, output_config=output_config, **kwargs)
        try:
            return json.loads(text)
        except json.JSONDecodeError as error:
            raise CommError(
                f"{model} answered a JSON schema request with text that is not "
                f"JSON: {error}",
            ) from error


def get_claude_client(env, company_id=None):
    return ClaudeClient(env, company_id)
