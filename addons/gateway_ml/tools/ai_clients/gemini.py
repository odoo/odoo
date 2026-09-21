from .base import BaseAIClient
from odoo.addons.integration.tools.exceptions import CommError

_GENERATION_CONFIG_KEYS = {
    "temperature": "temperature",
    "max_tokens": "maxOutputTokens",
    "top_p": "topP",
}

_TRUNCATED = ("MAX_TOKENS",)


class GeminiClient(BaseAIClient):
    ENDPOINT_CODE = "gemini"

    MAX_TEMPERATURE = 2.0

    def generate_content(
        self,
        contents,
        model=None,
        generation_config=None,
        safety_settings=None,
        system_instruction=None,
        **kwargs,
    ):
        model = self._resolve_model(model)
        if isinstance(contents, str):
            contents = [{"parts": [{"text": contents}]}]
        payload = {"contents": contents, **kwargs}
        if generation_config:
            payload["generationConfig"] = generation_config
        if safety_settings:
            payload["safetySettings"] = safety_settings
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        response = self._client.post(f"/models/{model}:generateContent", json=payload)
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
        parts = [
            {"text": prompt},
            *(
                {"inline_data": {"mime_type": mimetype, "data": data}}
                for data, mimetype in images
            ),
        ]
        return self._complete(
            [{"role": "user", "parts": parts}],
            model,
            system_instruction=system or None,
            response_schema=response_schema,
            **kwargs,
        )

    def _complete(self, contents, model, response_schema=None, **kwargs):
        model = self._resolve_model(model)
        generation_config = {
            wire: kwargs.pop(name)
            for name, wire in _GENERATION_CONFIG_KEYS.items()
            if name in kwargs
        }
        if response_schema is not None:
            generation_config["responseMimeType"] = "application/json"
            generation_config["responseJsonSchema"] = response_schema
        self._check_params(
            model=model,
            temperature=generation_config.get("temperature"),
            max_tokens=generation_config.get("maxOutputTokens"),
        )
        result = self.generate_content(
            contents,
            model=model,
            generation_config=generation_config or None,
            **kwargs,
        )
        return self._read_text(result)

    @staticmethod
    def _read_text(result):
        candidates = result.get("candidates") or []
        if not candidates:
            feedback = result.get("promptFeedback") or {}
            raise CommError(
                f"Gemini returned no candidates "
                f"(blockReason={feedback.get('blockReason')})",
            )
        candidate = candidates[0]
        finish = candidate.get("finishReason")
        text = "".join(
            part.get("text") or ""
            for part in (candidate.get("content") or {}).get("parts") or []
            if not part.get("thought")
        )
        if finish in _TRUNCATED:
            raise CommError(f"Gemini truncated its answer (finishReason={finish})")
        if not text:
            raise CommError(f"Gemini returned no text (finishReason={finish})")
        return text
