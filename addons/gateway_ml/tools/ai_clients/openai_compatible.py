import logging

from ..vendor_catalog import (
    SYNTHESIZE_TIMEOUT,
    TRANSCRIBE_TIMEOUT,
    audio_mimetype,
    get_openai_content,
    get_whisper_form,
    read_openai_content,
    read_whisper_segments,
    read_whisper_transcript,
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

            spec = self._catalog_spec() or {}
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                spec.get("max_tokens_param", "max_tokens"): max_tokens,
                **(spec.get("extra") or {}),
                **kwargs,
            }

            response = self._client.post("/chat/completions", json=payload)
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
        spec = self._catalog_spec()
        if not spec or not spec.get("vision"):
            raise CommError(
                f"{type(self).__name__} reads no images: the catalog describes "
                f"no vision capability for {self.ENDPOINT_CODE!r}",
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
            model=model or spec.get("vision_model"),
            **kwargs,
        )

        content, problem = read_openai_content(result)
        if problem:
            raise CommError(
                f"{type(self).__name__} returned no usable answer for the "
                f"image: {problem}",
            )
        return content

    def transcribe(self, audio_bytes, filename, language=None, prompt=None, model=None):
        body = self._post_whisper(
            audio_bytes, filename, None, language, prompt, model, "text"
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
        model=None,
    ):
        spec = self._audio_spec()
        body = self._post_whisper(
            audio_bytes,
            filename,
            mimetype,
            language,
            prompt,
            model or spec.get("cues_model"),
            "verbose_json",
        )
        spans, problem = read_whisper_segments(body)
        if problem:
            raise CommError(
                f"{type(self).__name__} returned no usable transcript: {problem}",
            )
        return spans

    def _post_whisper(
        self, audio_bytes, filename, mimetype, language, prompt, model, response_format
    ):
        spec = self._audio_spec()
        if not audio_bytes:
            raise CommError(f"{type(self).__name__} was given no audio to send")
        filename = filename or "audio"
        try:
            response = self._client.post(
                spec["audio_path"],
                files={
                    "file": (
                        filename,
                        audio_bytes,
                        mimetype or audio_mimetype(filename),
                    )
                },
                data=get_whisper_form(
                    model or spec["audio_model"],
                    language=language,
                    prompt=prompt,
                    response_format=response_format,
                ),
                timeout=spec.get("audio_timeout") or TRANSCRIBE_TIMEOUT,
            )
        except CommError:
            raise
        except Exception as e:
            raise CommError(
                f"{type(self).__name__} transcription failed: {e!s}",
            ) from e
        return response.get("body") if isinstance(response, dict) else response

    def _audio_spec(self):
        spec = self._catalog_spec()
        if not spec or not spec.get("audio"):
            raise CommError(
                f"{type(self).__name__} has no transcription endpoint: the "
                f"catalog describes no audio wire for {self.ENDPOINT_CODE!r}",
            )
        if spec["audio"] != "whisper":
            raise CommError(
                f"{self.ENDPOINT_CODE!r} transcribes over the "
                f"{spec['audio']!r} wire, which this client does not speak",
            )
        if spec.get("audio_service") != self.ENDPOINT_CODE:
            raise CommError(
                f"{self.ENDPOINT_CODE!r} serves audio on "
                f"{spec['audio_service']!r}; build a client for that endpoint",
            )
        return spec

    def synthesize(self, text, voice=None, mimetype="audio/mpeg", model=None, **kwargs):
        spec = self._catalog_spec()
        if not spec or not spec.get("speech"):
            raise CommError(
                f"{type(self).__name__} has no synthesis endpoint: the catalog "
                f"describes no speech wire for {self.ENDPOINT_CODE!r}",
            )
        if spec.get("speech_service") != self.ENDPOINT_CODE:
            raise CommError(
                f"{self.ENDPOINT_CODE!r} serves speech on "
                f"{spec['speech_service']!r}; build a client for that endpoint",
            )
        response_format = (spec.get("speech_mimetypes") or {}).get(mimetype)
        if not response_format:
            raise CommError(
                f"{self.ENDPOINT_CODE!r} does not write {mimetype!r}",
            )
        if not (text or "").strip():
            raise CommError(f"{type(self).__name__} was given no text to speak")

        body = {
            "model": model or spec["speech_model"],
            "input": text,
            "voice": voice or spec.get("speech_voice"),
            "response_format": response_format,
        }
        if kwargs.get("speed"):
            body["speed"] = kwargs["speed"]
        if kwargs.get("instructions"):
            body["instructions"] = kwargs["instructions"]

        try:
            response = self._client.post(
                spec["speech_path"],
                json=body,
                raw=True,
                timeout=spec.get("speech_timeout") or SYNTHESIZE_TIMEOUT,
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
        extra = (self._catalog_spec() or {}).get("extra") or {}
        return self._stream_lines(
            "/chat/completions",
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
