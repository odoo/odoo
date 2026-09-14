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

    def simple_completion(self, prompt, model=None, **kwargs):
        return self._complete([{"role": "user", "content": prompt}], model, **kwargs)

    def streaming_completion(self, messages, model=None, **kwargs):
        model = self._resolve_model(model)
        self._check_params(model=model, temperature=kwargs.get("temperature"))
        return self._stream_lines(
            "/messages", self._prepare_payload(model, messages, stream=True, **kwargs)
        )

    def vision_completion(
        self,
        prompt,
        image_data,
        media_type="image/jpeg",
        model=None,
        **kwargs,
    ):
        content = get_anthropic_content(prompt, [(image_data, media_type)])
        return self._complete([{"role": "user", "content": content}], model, **kwargs)

    def pdf_completion(self, prompt, pdf_data, model=None, **kwargs):
        return self._complete(
            self._prepare_pdf_messages(prompt, pdf_data), model, **kwargs
        )

    def pdf_with_caching(self, prompt, pdf_data, cache_pdf=True, model=None, **kwargs):
        return self._complete(
            self._prepare_pdf_messages(prompt, pdf_data, cache=cache_pdf),
            model,
            **kwargs,
        )

    def structured_output(
        self,
        prompt,
        schema,
        tool_name="extract_data",
        tool_description="Extract structured data",
        model=None,
        **kwargs,
    ):
        return self._get_forced_tool_input(
            [{"role": "user", "content": prompt}],
            tool_name,
            tool_description,
            schema,
            model,
            **kwargs,
        )

    def vision_structured_output(
        self,
        prompt,
        image_data,
        schema,
        media_type="image/jpeg",
        model=None,
        **kwargs,
    ):
        content = get_anthropic_content(prompt, [(image_data, media_type)])
        return self._get_forced_tool_input(
            [{"role": "user", "content": content}],
            "extract_from_image",
            "Extract structured data from image",
            schema,
            model,
            **kwargs,
        )

    def pdf_structured_output(self, prompt, pdf_data, schema, model=None, **kwargs):
        return self._get_forced_tool_input(
            self._prepare_pdf_messages(prompt, pdf_data),
            "extract_from_pdf",
            "Extract structured data from PDF document",
            schema,
            model,
            **kwargs,
        )

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

    @staticmethod
    def _prepare_pdf_messages(prompt, pdf_data, cache=False):
        document = {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": pdf_data,
            },
        }
        if cache:
            document["cache_control"] = {"type": "ephemeral"}
        return [
            {"role": "user", "content": [{"type": "text", "text": prompt}, document]}
        ]

    def get_usage(self, response):
        usage = response.get("usage") or {}
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
            "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
            "model": response.get("model", "unknown"),
        }

    def create_cacheable_content(self, text, cache=True, ttl=None):
        content = {"type": "text", "text": text}
        if cache:
            content["cache_control"] = {
                "type": "ephemeral",
                **({"ttl": ttl} if ttl else {}),
            }
        return content

    def create_cached_system_prompt(self, guidelines, cache_guidelines=True):
        return [self.create_cacheable_content(guidelines, cache=cache_guidelines)]

    def tool_conversation(
        self,
        user_message,
        tools,
        tool_executor,
        max_turns=5,
        model=None,
        **kwargs,
    ):
        model = self._resolve_model(model)
        messages = [{"role": "user", "content": user_message}]
        response = {}

        for _turn in range(max_turns):
            response = self.create_message(
                messages=messages, tools=tools, model=model, **kwargs
            )
            if response.get("stop_reason") != "tool_use":
                return response

            assistant_content = response.get("content") or []
            tool_results = []
            for block in assistant_content:
                if block.get("type") != "tool_use":
                    continue
                try:
                    result = {
                        "content": str(tool_executor(block["name"], block["input"]))
                    }
                except Exception as e:
                    result = {"content": f"Error: {e!s}", "is_error": True}
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.get("id"), **result}
                )

            messages.append({"role": "assistant", "content": assistant_content})
            messages.append({"role": "user", "content": tool_results})

        return {
            "error": "Max tool use turns reached",
            "messages": messages,
            "last_response": response,
        }


def get_claude_client(env, company_id=None):
    return ClaudeClient(env, company_id)
