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

    def simple_completion(self, prompt, model=None, **kwargs):
        return self._complete(prompt, model, **kwargs)

    def chat_completion(self, messages, model=None, **kwargs):
        system = "\n\n".join(
            message["content"] for message in messages if message["role"] == "system"
        )
        contents = [
            {
                "role": "user" if message["role"] == "user" else "model",
                "parts": [{"text": message["content"]}],
            }
            for message in messages
            if message["role"] != "system"
        ]
        return self._complete(contents, model, system_instruction=system, **kwargs)

    def vision_completion(
        self,
        prompt,
        image_data,
        media_type="image/jpeg",
        model=None,
        **kwargs,
    ):
        return self.multimodal_completion(
            text=prompt,
            image_data=f"data:{media_type};base64,{image_data}",
            model=model,
            **kwargs,
        )

    def multimodal_completion(self, text, image_data=None, model=None, **kwargs):
        parts = [{"text": text}]
        if image_data:
            mime_type, data = "image/jpeg", image_data
            if image_data.startswith("data:"):
                header, data = image_data.split(",", 1)
                mime_type = header[len("data:") :].split(";", 1)[0]
            parts.append({"inline_data": {"mime_type": mime_type, "data": data}})
        return self._complete([{"parts": parts}], model, **kwargs)

    def streaming_completion(self, contents, model=None, **kwargs):
        model = self._resolve_model(model)
        if isinstance(contents, str):
            contents = [{"parts": [{"text": contents}]}]
        return self._stream_lines(
            f"/models/{model}:streamGenerateContent",
            {"contents": contents, **kwargs},
        )

    def _complete(self, contents, model, **kwargs):
        model = self._resolve_model(model)
        generation_config = {
            wire: kwargs.pop(name)
            for name, wire in _GENERATION_CONFIG_KEYS.items()
            if name in kwargs
        }
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
