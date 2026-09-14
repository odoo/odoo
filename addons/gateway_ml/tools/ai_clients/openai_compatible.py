import logging

from ..wire_formats import (
    Cues,
    audio_mimetype,
    get_openai_content,
    get_whisper_form,
    read_openai_content,
    read_whisper_segments,
    read_whisper_transcript,
    vocabulary_prompt,
)
from .base import BaseAIClient
from odoo.addons.integration.tools.exceptions import CommError

_logger = logging.getLogger(__name__)


class OpenAICompatibleClient(BaseAIClient):
    MAX_TEMPERATURE = 2.0

    def chat_completion(
        self,
        messages,
        model=None,
        temperature=1.0,
        max_tokens=4096,
        **kwargs,
    ):
        model = self._resolve_model(model)
        try:
            self._check_params(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            shape = self._request_shape(model)
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                shape.max_tokens_param or "max_tokens": max_tokens,
                **(shape.request_extra or {}),
                **kwargs,
            }

            response = self._client.post(self._chat_path(), json=payload)
            return self._get_response_body(response)

        except ValueError, CommError:
            raise
        except Exception as e:
            raise CommError(
                f"{type(self).__name__} chat completion failed: {e!s}",
            ) from e

    def simple_completion(self, prompt, model=None, **kwargs):
        result = self.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            **kwargs,
        )
        content, problem = read_openai_content(result)
        if problem:
            _logger.error(
                "%s returned no usable content: %s. Response: %s",
                type(self).__name__,
                problem,
                result,
            )
            raise CommError(
                f"{type(self).__name__} returned no usable content: {problem}",
            )
        return content

    def vision_completion(
        self,
        prompt,
        image_data,
        media_type="image/jpeg",
        model=None,
        **kwargs,
    ):
        if not self._provider().has_vision:
            raise CommError(
                f"{type(self).__name__} reads no images: no active model of "
                f"{self.ENDPOINT_CODE!r} reads images",
            )
        if not image_data:
            raise CommError(f"{type(self).__name__} was given no image to send")

        messages = [
            {
                "role": "user",
                "content": get_openai_content(prompt, [(image_data, media_type)]),
            }
        ]
        result = self.chat_completion(
            messages=messages,
            model=model or self._vision_model(),
            **kwargs,
        )

        content, problem = read_openai_content(result)
        if problem:
            raise CommError(
                f"{type(self).__name__} returned no usable answer for the "
                f"image: {problem}",
            )
        return content

    def transcribe(
        self,
        audio_bytes,
        filename=None,
        mimetype=None,
        language=None,
        prompt=None,
        vocabulary=(),
        model=None,
    ):
        body = self._post_whisper(
            audio_bytes,
            filename,
            mimetype,
            language,
            prompt or vocabulary_prompt(vocabulary),
            model,
            "text",
        )
        text, problem = read_whisper_transcript(body)
        if problem:
            raise CommError(
                f"{type(self).__name__} returned no usable transcript: {problem}",
            )
        return text

    def transcribe_cues(
        self,
        audio_bytes,
        filename=None,
        mimetype=None,
        language=None,
        prompt=None,
        vocabulary=(),
        speakers=False,
        model=None,
    ):
        timed = self._audio_operation("transcribe_timed")
        body = self._post_whisper(
            audio_bytes,
            filename,
            mimetype,
            language,
            prompt or vocabulary_prompt(vocabulary),
            model or timed.model_id.code,
            "verbose_json",
            operation=timed,
        )
        spans, problem = read_whisper_segments(body)
        if problem:
            raise CommError(
                f"{type(self).__name__} returned no usable transcript: {problem}",
            )
        return Cues(spans, body.get("duration") if isinstance(body, dict) else 0.0)

    def _post_whisper(
        self,
        audio_bytes,
        filename,
        mimetype,
        language,
        prompt,
        model,
        response_format,
        operation=None,
    ):
        operation = operation or self._audio_operation("transcribe")
        model = model or operation.model_id.code
        row = self._get_model_rows().get(model)
        if not audio_bytes:
            raise CommError(f"{type(self).__name__} was given no audio to send")
        filename = filename or "audio"
        try:
            response = self._client.post(
                operation.path,
                files={
                    "file": (
                        filename,
                        audio_bytes,
                        mimetype or audio_mimetype(filename),
                    )
                },
                data=get_whisper_form(
                    model,
                    language=language,
                    prompt=prompt,
                    response_format=response_format,
                    untimed=(not row.has_timestamps) if row else None,
                    language_key=row.language_form_key if row else None,
                ),
                timeout=operation.timeout or None,
            )
        except CommError:
            raise
        except Exception as e:
            raise CommError(
                f"{type(self).__name__} transcription failed: {e!s}",
            ) from e
        return response.get("body") if isinstance(response, dict) else response

    def _audio_operation(self, operation):
        row = self._operation(operation) or (
            self._operation("transcribe") if operation == "transcribe_timed" else None
        )
        if not row:
            raise CommError(
                f"{type(self).__name__} has no transcription endpoint: "
                f"{self.ENDPOINT_CODE!r} offers no {operation} operation",
            )
        if row.wire != "openai_compatible":
            raise CommError(
                f"{self.ENDPOINT_CODE!r} transcribes over the {row.wire!r} wire, "
                f"which this client does not speak",
            )
        if row.service_id.code != self.ENDPOINT_CODE:
            raise CommError(
                f"{self.ENDPOINT_CODE!r} serves audio on {row.service_id.code!r}; "
                f"build a client for that endpoint",
            )
        return row

    def _chat_path(self):
        return self._operation("chat").path or "/chat/completions"

    def _vision_model(self):
        vision = self._provider().model_ids.filtered(
            lambda row: row.active and row.kind == "vision"
        )
        return vision[:1].code or None

    def synthesize(self, text, voice=None, mimetype="audio/mpeg", model=None, **kwargs):
        speech = self._operation("synthesize")
        if not speech:
            raise CommError(
                f"{type(self).__name__} has no synthesis endpoint: "
                f"{self.ENDPOINT_CODE!r} offers no synthesize operation",
            )
        if speech.service_id.code != self.ENDPOINT_CODE:
            raise CommError(
                f"{self.ENDPOINT_CODE!r} serves speech on {speech.service_id.code!r}; "
                f"build a client for that endpoint",
            )
        response_format = (speech.formats or {}).get(mimetype)
        if not response_format:
            raise CommError(
                f"{self.ENDPOINT_CODE!r} does not write {mimetype!r}",
            )
        if not (text or "").strip():
            raise CommError(f"{type(self).__name__} was given no text to speak")

        body = {
            "model": model or speech.model_id.code,
            "input": text,
            "voice": voice or speech.voice,
            "response_format": response_format,
        }
        if kwargs.get("speed"):
            body["speed"] = kwargs["speed"]
        if kwargs.get("instructions"):
            body["instructions"] = kwargs["instructions"]

        try:
            response = self._client.post(
                speech.path,
                json=body,
                raw=True,
                timeout=speech.timeout or None,
            )
        except CommError:
            raise
        except Exception as e:
            raise CommError(
                f"{type(self).__name__} synthesis failed: {e!s}",
            ) from e

        audio = getattr(response, "content", None)
        if not audio:
            raise CommError(f"{type(self).__name__} returned no audio")
        return audio

    def streaming_completion(self, messages, model=None, **kwargs):
        model = self._resolve_model(model)
        self._check_params(model=model, temperature=kwargs.get("temperature"))
        extra = self._request_shape(model).request_extra or {}
        return self._stream_lines(
            self._chat_path(),
            {"model": model, "messages": messages, "stream": True, **extra, **kwargs},
        )

    def get_usage(self, response):
        usage = response.get("usage") or {}
        return {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "model": response.get("model", "unknown"),
        }
