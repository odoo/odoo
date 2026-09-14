import base64
import json
import logging

from odoo.exceptions import UserError

from .json_payload import strip_json_fence
from .vendor_catalog import (
    CHAT_TIMEOUT,
    PROVIDERS,
    TRANSCRIBE_TIMEOUT,
    audio_mimetype,
    get_anthropic_content,
    get_openai_content,
    get_whisper_form,
    read_anthropic_content,
    read_openai_content,
    read_whisper_transcript,
)
from odoo.addons.integration.tools import CommError, get_api_client

_logger = logging.getLogger(__name__)


class CatalogAIClient:
    def __init__(self, provider, api_key, model=None, env=None, credential_id=None):
        self._name = provider or ""
        self._spec = PROVIDERS.get(self._name) or {}
        self._api_key = (api_key or "").strip()
        self._model = (model or "").strip() or self._spec.get("chat_model") or ""
        self._env = env
        self._credential_id = credential_id

    @property
    def label(self):
        return self._spec.get("label") or self._name or "unset"

    @property
    def model(self):
        return self._model

    @property
    def configured(self):
        return bool(self._spec and self._api_key and self._model and self._env)

    @property
    def supports_audio(self):
        return bool(self._spec.get("audio"))

    @property
    def supports_vision(self):
        return bool(self._spec.get("vision"))

    @property
    def vision_model(self):
        return self._spec.get("vision_model") or self._model

    @property
    def _audio_timeout(self):
        return self._spec.get("audio_timeout") or TRANSCRIBE_TIMEOUT

    @property
    def _chat_timeout(self):
        return self._spec.get("chat_timeout") or CHAT_TIMEOUT

    def _token_budget(self, max_tokens):
        return max(max_tokens, self._spec.get("min_max_tokens") or 0)

    def chat_json(self, system, user, max_tokens, temperature, images=None):
        if not self.configured:
            return None
        usable = self._usable_images(images)
        if self._spec["wire"] == "anthropic":
            return self._chat_anthropic(system, user, max_tokens, temperature, usable)
        return self._chat_openai(system, user, max_tokens, temperature, usable)

    def _usable_images(self, images):
        if not images:
            return []
        if not self.supports_vision:
            _logger.warning(
                "%s cannot read images; dropping %d attachment(s) and answering "
                "from the text alone",
                self.label,
                len(images),
            )
            return []
        return list(images)

    def _chat_openai(self, system, user, max_tokens, temperature, images=()):
        return self._chat(
            {
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": get_openai_content(user, images)},
                ],
                "response_format": {"type": "json_object"},
            },
            max_tokens,
            temperature,
            images,
            read_openai_content,
        )

    def _chat_anthropic(self, system, user, max_tokens, temperature, images=()):
        return self._chat(
            {
                "system": system,
                "messages": [
                    {"role": "user", "content": get_anthropic_content(user, images)}
                ],
            },
            max_tokens,
            temperature,
            images,
            read_anthropic_content,
        )

    def _chat(self, wire_body, max_tokens, temperature, images, reader):
        body = {
            "model": self.vision_model if images else self._model,
            **wire_body,
            self._spec.get("max_tokens_param", "max_tokens"): self._token_budget(
                max_tokens
            ),
            "temperature": temperature,
            **(self._spec.get("extra") or {}),
        }
        payload = self._post_json(
            self._spec["chat_service"],
            self._spec["chat_path"],
            body,
            timeout=self._chat_timeout,
        )
        if payload is None:
            return None
        return self._usable_text(reader(payload))

    def _usable_text(self, read_result):
        text, problem = read_result
        if problem:
            _logger.warning(
                "%s returned no usable content: %s (model=%s); raise max_tokens "
                "or lower the reasoning effort",
                self.label,
                problem,
                self._model,
            )
            return None
        return strip_json_fence(text)

    def transcribe(self, audio_bytes, filename, language=None, prompt=None):
        if not self.configured or not self.supports_audio or not audio_bytes:
            return None
        if self._spec["audio"] == "gemini_inline":
            return self._transcribe_gemini(audio_bytes, filename, language, prompt)
        return self._transcribe_whisper(audio_bytes, filename, language, prompt)

    def _transcribe_whisper(self, audio_bytes, filename, language, prompt):
        transcript = self._post(
            self._spec["audio_service"],
            self._spec["audio_path"],
            self._audio_timeout,
            files={"file": (filename, audio_bytes, audio_mimetype(filename))},
            data=get_whisper_form(
                self._spec["audio_model"], language=language, prompt=prompt
            ),
        )
        text, problem = read_whisper_transcript(transcript)
        if problem:
            _logger.warning("%s transcription unusable: %s", self.label, problem)
            return None
        return text

    def _transcribe_gemini(self, audio_bytes, filename, language, prompt):
        instruction = (
            "Transcribe literalmente el audio"
            + (f" en idioma '{language}'" if language else "")
            + ". Responde SOLO con la transcripción, sin comillas ni comentarios."
        )
        if prompt:
            instruction += f" Contexto de vocabulario: {prompt}"
        model = self._spec["audio_model"]
        body = {
            "contents": [
                {
                    "parts": [
                        {"text": instruction},
                        {
                            "inline_data": {
                                "mime_type": audio_mimetype(filename),
                                "data": base64.b64encode(audio_bytes).decode(),
                            }
                        },
                    ]
                }
            ]
        }
        payload = self._post_json(
            self._spec["audio_service"],
            self._spec["audio_path"].format(model=model),
            body,
            timeout=self._audio_timeout,
        )
        if payload is None:
            return None
        try:
            parts = payload["candidates"][0]["content"]["parts"]
        except KeyError, IndexError, TypeError:
            _logger.warning(
                "%s transcription returned no candidates: %s",
                self.label,
                json.dumps(payload)[:300],
            )
            return None
        text = "".join(
            part.get("text") or ""
            for part in parts
            if isinstance(part, dict) and not part.get("thought")
        )
        return text.strip() or None

    def _auth_headers(self, endpoint_code):
        endpoint = (
            self._env["integration.service"]
            .sudo()
            .search([("code", "=", endpoint_code), ("active", "=", True)], limit=1)
        )
        if not endpoint:
            return {}
        return endpoint._api_key_headers(self._api_key)

    def _post(self, endpoint_code, path, timeout, **kwargs):
        try:
            headers = {
                "Content-Type": "application/json",
                **self._auth_headers(endpoint_code),
            }
            if "files" in kwargs:
                headers.pop("Content-Type", None)
            client = get_api_client(
                self._env,
                endpoint_code,
                credential_id=self._credential_id or None,
            )
            response = client.post(
                path,
                headers=headers,
                timeout=timeout,
                raise_for_status=False,
                skip_cache=True,
                **kwargs,
            )
        except CommError, UserError:
            _logger.exception("%s call failed", self.label)
            return None

        status = response.get("status_code")
        if status != 200:
            _logger.warning(
                "%s call failed (HTTP %s): %s",
                self.label,
                status,
                (response.get("text") or "")[:300],
            )
            return None
        return response.get("body")

    def _post_json(self, endpoint_code, path, body, timeout=CHAT_TIMEOUT):
        payload = self._post(endpoint_code, path, timeout, json=body)
        if payload is not None and not isinstance(payload, dict):
            _logger.warning("%s returned a non-JSON body", self.label)
            return None
        return payload
