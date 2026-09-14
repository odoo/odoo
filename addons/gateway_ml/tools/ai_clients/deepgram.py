import logging

from ..wire_formats import Cues
from .base import BaseAIClient
from odoo.addons.integration.tools.exceptions import CommError

_logger = logging.getLogger(__name__)

SYNTHESIZE_TIMEOUT = 60


class DeepgramClient(BaseAIClient):
    ENDPOINT_CODE = "deepgram"

    FALLBACK_MODEL = "nova-3"

    TTS_VOICES = {
        "aura-2-amalthea-en": "Female",
        "aura-2-andromeda-en": "Female",
        "aura-2-asteria-en": "Female",
        "aura-2-athena-en": "Female",
        "aura-2-aurora-en": "Female",
        "aura-2-callista-en": "Female",
        "aura-2-cora-en": "Female",
        "aura-2-cordelia-en": "Female",
        "aura-2-delia-en": "Female",
        "aura-2-electra-en": "Female",
        "aura-2-harmonia-en": "Female",
        "aura-2-helena-en": "Female",
        "aura-2-hera-en": "Female",
        "aura-2-iris-en": "Female",
        "aura-2-janus-en": "Female",
        "aura-2-juno-en": "Female",
        "aura-2-luna-en": "Female",
        "aura-2-minerva-en": "Female",
        "aura-2-ophelia-en": "Female",
        "aura-2-pandora-en": "Female",
        "aura-2-phoebe-en": "Female",
        "aura-2-selene-en": "Female",
        "aura-2-thalia-en": "Female",
        "aura-2-theia-en": "Female",
        "aura-2-vesta-en": "Female",
        "aura-2-apollo-en": "Male",
        "aura-2-arcas-en": "Male",
        "aura-2-aries-en": "Male",
        "aura-2-atlas-en": "Male",
        "aura-2-draco-en": "Male",
        "aura-2-hermes-en": "Male",
        "aura-2-hyperion-en": "Male",
        "aura-2-jupiter-en": "Male",
        "aura-2-mars-en": "Male",
        "aura-2-neptune-en": "Male",
        "aura-2-odysseus-en": "Male",
        "aura-2-orion-en": "Male",
        "aura-2-orpheus-en": "Male",
        "aura-2-pluto-en": "Male",
        "aura-2-saturn-en": "Male",
        "aura-2-zeus-en": "Male",
        "aura-2-celeste-es": "Female, Spanish",
        "aura-2-estrella-es": "Female, Spanish",
        "aura-2-nestor-es": "Male, Spanish",
    }

    _PASSTHROUGH_PARAMS = ("model", "language", "alternatives")

    _BOOLEAN_PARAMS = (
        "paragraphs",
        "utterances",
        "detect_entities",
        "sentiment",
        "intents",
        "detect_language",
        "profanity_filter",
        "numerals",
        "multichannel",
        "smart_format",
        "filler_words",
    )

    _LIST_PARAMS = ("search", "redact", "replace")

    _SUMMARIZE_VALUES = {True: "true", False: "false", "v2": "v2", "true": "true"}

    _KEYTERM_FAMILIES = ("nova-3", "flux")

    def _prepare_transcription_params(self, **kwargs):
        params = {}

        for name in self._PASSTHROUGH_PARAMS:
            if name in kwargs:
                params[name] = kwargs[name]

        if kwargs.get("punctuate", True):
            params["punctuate"] = "true"

        for name in self._BOOLEAN_PARAMS:
            if kwargs.get(name):
                params[name] = "true"

        for name in self._LIST_PARAMS:
            if kwargs.get(name) and isinstance(kwargs[name], list):
                params[name] = kwargs[name]

        if "timestamps" in kwargs:
            params["timestamps"] = "true" if kwargs["timestamps"] else "false"

        if kwargs.get("diarize"):
            params["diarize"] = "true"
            if "diarize_version" in kwargs:
                params["diarize_version"] = kwargs["diarize_version"]

        if kwargs.get("topics") or kwargs.get("detect_topics"):
            params["topics"] = "true"

        if kwargs.get("summarize"):
            value = kwargs["summarize"]
            resolved = self._SUMMARIZE_VALUES.get(value)
            if resolved is None:
                _logger.warning(
                    "Invalid summarize value: %s. Expected True, False, 'v2', or 'true'",
                    value,
                )
                resolved = "true"
            params["summarize"] = resolved

        params.update(self._prepare_keyword_params(**kwargs))

        return params

    def _prepare_keyword_params(self, **kwargs):
        model_name = kwargs.get("model", "nova-3").lower()
        name = (
            "keyterm"
            if any(family in model_name for family in self._KEYTERM_FAMILIES)
            else "keywords"
        )
        value = kwargs.get(name)
        if isinstance(value, str):
            value = [value] if value else []
        return {name: value} if isinstance(value, list) and value else {}

    DEFAULT_VOICE = "aura-2-asteria-en"

    def transcribe_file(self, audio_data, mimetype=None, model=None, **kwargs):
        model = self._resolve_model(model)
        self._check_params(model=model)
        if not mimetype:
            _logger.warning(
                "No mimetype given for a Deepgram upload; sending "
                "application/octet-stream and letting Deepgram sniff it",
            )
        response = self._client.post(
            "/listen",
            data=audio_data,
            params=self._prepare_transcription_params(model=model, **kwargs),
            headers={"Content-Type": mimetype or "application/octet-stream"},
        )
        return self._get_response_body(response)

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
        **kwargs,
    ):
        options = {"utterances": True, "diarize": speakers, **kwargs}
        return self._read_cues(
            self._transcribe_audio(
                audio_bytes, mimetype, language, vocabulary, model, options
            )
        )

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
        result = self._transcribe_audio(
            audio_bytes, mimetype, language, vocabulary, model, {}
        )
        channels = (result or {}).get("results", {}).get("channels") or []
        alternatives = channels[0].get("alternatives") if channels else None
        return (alternatives[0].get("transcript") or "").strip() if alternatives else ""

    def _transcribe_audio(
        self, audio_bytes, mimetype, language, vocabulary, model, options
    ):
        if not audio_bytes:
            raise CommError("Deepgram was given no audio to send")
        model = self._resolve_model(model)
        options = {"smart_format": True, **options}
        if language:
            options["language"] = language
        if vocabulary:
            options["keyterm"] = options["keywords"] = list(vocabulary)
        return self.transcribe_file(
            audio_bytes, mimetype=mimetype, model=model, **options
        )

    SPEECH_ENCODINGS = {
        "audio/mpeg": {"encoding": "mp3"},
        "audio/ogg": {"encoding": "opus"},
        "audio/flac": {"encoding": "flac"},
        "audio/aac": {"encoding": "aac"},
        "audio/wav": {"encoding": "linear16", "container": "wav"},
    }

    def synthesize(self, text, voice=None, mimetype="audio/mpeg", model=None, **kwargs):
        if not (text or "").strip():
            raise CommError("Deepgram was given no text to speak")
        encoding = self.SPEECH_ENCODINGS.get(mimetype)
        if encoding is None:
            raise CommError(f"Deepgram does not write {mimetype!r}")

        if voice and voice not in self.TTS_VOICES:
            _logger.info(
                "Voice %r is not a Deepgram voice; speaking with %r instead",
                voice,
                model or self.DEFAULT_VOICE,
            )
            voice = None
        voice = voice or model or self.DEFAULT_VOICE

        params = {"model": voice, **encoding}
        if kwargs.get("sample_rate"):
            params["sample_rate"] = kwargs["sample_rate"]

        try:
            response = self._client.post(
                "/speak",
                json={"text": text},
                params=params,
                raw=True,
                timeout=kwargs.get("timeout") or SYNTHESIZE_TIMEOUT,
            )
        except CommError:
            raise
        except Exception as e:
            raise CommError(f"Deepgram synthesis failed: {e!s}") from e

        audio = getattr(response, "content", None)
        if not audio:
            raise CommError("Deepgram returned no audio")
        return audio

    @staticmethod
    def _read_cues(result):
        result = result or {}
        duration = (result.get("metadata") or {}).get("duration") or 0.0
        spans = []
        for utterance in result.get("results", {}).get("utterances", []) or []:
            text = (utterance.get("transcript") or "").strip()
            if not text:
                continue
            speaker = utterance.get("speaker")
            spans.append(
                {
                    "start": float(utterance.get("start") or 0.0),
                    "end": float(utterance.get("end") or 0.0),
                    "text": text,
                    "speaker": f"Speaker {speaker}" if speaker is not None else "",
                    "speaker_index": speaker,
                    "confidence": float(utterance.get("confidence") or 0.0),
                }
            )
        if spans:
            return Cues(spans, duration)
        channels = result.get("results", {}).get("channels") or []
        alternatives = channels[0].get("alternatives") if channels else None
        transcript = (
            (alternatives[0].get("transcript") or "").strip() if alternatives else ""
        )
        if not transcript:
            raise CommError("Deepgram returned no usable transcript")
        return Cues(
            [{"start": 0.0, "end": float(duration), "text": transcript, "speaker": ""}],
            duration,
        )
