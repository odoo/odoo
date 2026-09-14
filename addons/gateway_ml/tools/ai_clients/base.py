import logging

from ..json_payload import parse_json_response
from odoo.addons.integration.tools.api_client import get_api_client
from odoo.addons.integration.tools.exceptions import CommError

_logger = logging.getLogger(__name__)

_JSON_INSTRUCTION = "\n\nReturn your response as valid JSON."


class BaseAIClient:
    ENDPOINT_CODE = None

    FALLBACK_MODEL = None

    VALID_MODELS = ()

    _default_model = None

    _model_rows = None

    _provider_row = None

    MIN_TEMPERATURE = 0.0
    MAX_TEMPERATURE = 1.0
    MAX_TOKENS_LIMIT = 8192

    def __init__(self, env, company_id=None, endpoint_code=None):
        if endpoint_code:
            self.ENDPOINT_CODE = endpoint_code
        if not self.ENDPOINT_CODE:
            raise NotImplementedError(
                f"{type(self).__name__} must declare ENDPOINT_CODE",
            )
        self.env = env
        self.company_id = company_id
        self._client = get_api_client(env, self.ENDPOINT_CODE, company_id)

    def simple_completion(self, prompt, model=None, **kwargs):
        raise NotImplementedError(
            f"{type(self).__name__} must implement simple_completion",
        )

    def json_completion(self, prompt, model=None, **kwargs):
        if "json" not in prompt.lower():
            prompt = f"{prompt}{_JSON_INSTRUCTION}"
        text = self.simple_completion(prompt, model=model, **kwargs)
        return parse_json_response(text, env=self.env)

    def _resolve_model(self, model=None):
        if model:
            return model
        return (
            self._provider_default_model()
            or self._operation_default_model()
            or self.FALLBACK_MODEL
        )

    def _operation_default_model(self):
        return self._operation("chat").model_id.code or None

    def _provider(self):
        if self._provider_row is None:
            self._provider_row = (
                self.env["gateway.ml.provider"]
                .sudo()
                .search([("endpoint_id.code", "=", self.ENDPOINT_CODE)], limit=1)
            )
        return self._provider_row

    def _operation(self, operation):
        return self._provider().service_ids.filtered(
            lambda row: row.operation == operation
        )[:1]

    def _request_shape(self, model):
        return self._get_model_rows().get(model) or self._operation("chat").model_id

    def _provider_default_model(self):
        if self._default_model is None:
            provider = (
                self.env["gateway.ml.provider"]
                .sudo()
                .search([("endpoint_id.code", "=", self.ENDPOINT_CODE)], limit=1)
            )
            self._default_model = (
                provider.default_model_id.filtered("active").code or ""
            )
        return self._default_model

    def _get_response_body(self, response):
        if not isinstance(response, dict):
            raise CommError(
                f"{type(self).__name__}: expected a response dict, got "
                f"{type(response).__name__}",
            )
        body = response.get("body")
        if not isinstance(body, dict):
            preview = (response.get("text") or "")[:200]
            _logger.error(
                "%s response carried no JSON object body: %s",
                type(self).__name__,
                preview,
            )
            raise CommError(
                f"{type(self).__name__}: expected a JSON object body, got "
                f"{type(body).__name__}: {preview}",
            )
        return body

    def _stream_lines(self, path, payload):
        response = self._client.post(path, json=payload, stream=True, raw=True)
        for line in response.iter_lines():
            if not line:
                continue
            try:
                yield line.decode("utf-8")
            except UnicodeDecodeError as error:
                _logger.warning(
                    "%s skipped an undecodable stream chunk: %s",
                    type(self).__name__,
                    error,
                )

    def _get_model_rows(self):
        if self._model_rows is None:
            rows = (
                self.env["gateway.ml.model"]
                .sudo()
                .search([("provider_id.endpoint_id.code", "=", self.ENDPOINT_CODE)])
            )
            self._model_rows = {row.code: row for row in rows}
        return self._model_rows

    def _check_params(self, model=None, temperature=None, max_tokens=None):
        rows = self._get_model_rows()
        known = set(rows) | set(self.VALID_MODELS)
        if model is not None and known and model not in known:
            _logger.warning(
                "Model %r is described by no gateway.ml.model row of %s. Sending it "
                "anyway; the API will reject it if it does not exist.",
                model,
                self.ENDPOINT_CODE,
            )

        if temperature is not None:
            if not isinstance(temperature, (int, float)) or isinstance(
                temperature, bool
            ):
                raise ValueError(
                    f"Temperature must be numeric, got {type(temperature).__name__}",
                )
            if not (self.MIN_TEMPERATURE <= temperature <= self.MAX_TEMPERATURE):
                raise ValueError(
                    f"Temperature must be between {self.MIN_TEMPERATURE} and "
                    f"{self.MAX_TEMPERATURE}, got {temperature}",
                )

        if max_tokens is not None:
            if (
                not isinstance(max_tokens, int)
                or isinstance(max_tokens, bool)
                or max_tokens <= 0
            ):
                raise ValueError(
                    f"max_tokens must be a positive integer, got {max_tokens!r}",
                )
            limit = (
                rows[model].max_output_tokens if model in rows else 0
            ) or self.MAX_TOKENS_LIMIT
            if max_tokens > limit:
                _logger.warning(
                    "max_tokens (%s) exceeds the %s output cap of %s (%s)",
                    max_tokens,
                    model or self.ENDPOINT_CODE,
                    limit,
                    "its gateway.ml.model row"
                    if model in rows
                    else "the client default",
                )
