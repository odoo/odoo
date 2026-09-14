import base64
import json
import logging

from odoo.exceptions import UserError

from .json_payload import strip_json_fence
from .wire_formats import (
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


class ProviderAssistant:
    def __init__(self, provider, model=None, company_id=None):
        self._provider = provider.sudo() if provider else provider
        self._env = provider.env if provider is not None else None
        self._company_id = company_id
        self._chat = self._operation("chat")
        self._audio = self._operation("transcribe")
        code = getattr(model, "code", model) or ""
        self._model = code.strip() or self._chat.model_id.code or ""

    def _operation(self, name):
        if not self._provider:
            return self._env["gateway.ml.provider.service"] if self._env else None
        return self._provider.service_ids.filtered(lambda row: row.operation == name)[
            :1
        ]

    @property
    def label(self):
        return self._provider.name if self._provider else "unset"

    @property
    def model(self):
        return self._model

    @property
    def configured(self):
        return bool(
            self._provider
            and self._chat
            and self._model
            and self._has_connection(self._chat.service_id)
        )

    @property
    def supports_audio(self):
        return bool(self._provider and self._audio)

    @property
    def supports_vision(self):
        return bool(self._provider and self._shape(self._model).has_vision)

    def _has_connection(self, service):
        if service.auth_type == "none":
            return True
        connection = self._env["integration.connection"]._resolve(
            service, company=self._company_id or self._env.company.id
        )
        return bool(connection.credential_id)

    def _shape(self, model_code):
        rows = self._provider.model_ids.filtered(lambda row: row.code == model_code)
        return rows[:1] or self._chat.model_id

    def _token_budget(self, max_tokens):
        return max(max_tokens, self._shape(self._model).min_max_tokens or 0)

    def chat_json(self, system, user, max_tokens, temperature, images=None):
        if not self.configured:
            return None
        usable = self._usable_images(images)
        if self._chat.wire == "anthropic_messages":
            wire_body = {
                "system": system,
                "messages": [
                    {"role": "user", "content": get_anthropic_content(user, usable)}
                ],
            }
            reader = read_anthropic_content
        else:
            wire_body = {
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": get_openai_content(user, usable)},
                ],
                "response_format": {"type": "json_object"},
            }
            reader = read_openai_content
        shape = self._shape(self._model)
        body = {
            "model": self._model,
            **wire_body,
            shape.max_tokens_param or "max_tokens": self._token_budget(max_tokens),
            **({"temperature": temperature} if shape.sampling_params else {}),
            **(shape.request_extra or {}),
        }
        payload = self._post_json(self._chat, self._chat.path, body)
        if payload is None:
            return None
        return self._usable_text(reader(payload))

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
        if not self._has_connection(self._audio.service_id):
            return None
        if self._audio.wire == "gemini_native":
            return self._transcribe_inline(audio_bytes, filename, language, prompt)
        return self._transcribe_whisper(audio_bytes, filename, language, prompt)

    def _transcribe_whisper(self, audio_bytes, filename, language, prompt):
        model = self._audio.model_id
        transcript = self._post(
            self._audio,
            self._audio.path,
            files={"file": (filename, audio_bytes, audio_mimetype(filename))},
            data=get_whisper_form(
                model.code,
                language=language,
                prompt=prompt,
                untimed=not model.has_timestamps,
                language_key=model.language_form_key,
            ),
        )
        text, problem = read_whisper_transcript(transcript)
        if problem:
            _logger.warning("%s transcription unusable: %s", self.label, problem)
            return None
        return text

    def _transcribe_inline(self, audio_bytes, filename, language, prompt):
        instruction = (
            "Transcribe literalmente el audio"
            + (f" en idioma '{language}'" if language else "")
            + ". Responde SOLO con la transcripción, sin comillas ni comentarios."
        )
        if prompt:
            instruction += f" Contexto de vocabulario: {prompt}"
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
            self._audio,
            self._audio.path.format(model=self._audio.model_id.code),
            body,
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

    def _post(self, operation, path, **kwargs):
        try:
            client = get_api_client(
                self._env,
                operation.service_id.code,
                company_id=self._company_id,
            )
            response = client.post(
                path,
                timeout=operation.timeout or None,
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

    def _post_json(self, operation, path, body):
        payload = self._post(operation, path, json=body)
        if payload is not None and not isinstance(payload, dict):
            _logger.warning("%s returned a non-JSON body", self.label)
            return None
        return payload
