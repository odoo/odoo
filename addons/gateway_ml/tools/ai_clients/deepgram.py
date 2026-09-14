import logging
from collections import Counter
from urllib.parse import urlencode

from .base import BaseAIClient
from odoo.addons.integration.tools.exceptions import CommError

_logger = logging.getLogger(__name__)

SYNTHESIZE_TIMEOUT = 60


class DeepgramClient(BaseAIClient):
    ENDPOINT_CODE = "deepgram"

    FALLBACK_MODEL = "nova-3"

    MODELS = {
        "nova-3": "Latest and most accurate model (2025) - 54.2% WER reduction",
        "nova-3-general": "Nova-3 general purpose variant",
        "nova-3-medical": "Nova-3 medical transcription variant",
        "flux-general-en": "Conversational voice agent model (English-only, uses /v2/listen)",
        "nova-2": "Previous generation accurate model",
        "nova": "Fast and accurate general-purpose model",
        "enhanced": "Improved version of base model",
        "base": "Standard model for general transcription",
        "whisper": "OpenAI Whisper model via Deepgram",
    }

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

    LANGUAGES = [
        "en",
        "en-US",
        "en-GB",
        "en-AU",
        "en-NZ",
        "en-IN",
        "es",
        "es-419",
        "es-ES",
        "fr",
        "fr-CA",
        "de",
        "it",
        "pt",
        "pt-BR",
        "nl",
        "pl",
        "ru",
        "tr",
        "uk",
        "ja",
        "ko",
        "zh",
        "zh-CN",
        "zh-TW",
        "hi",
        "id",
        "ms",
        "th",
        "vi",
        "ar",
        "he",
        "sv",
        "da",
        "no",
        "fi",
    ]

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

    def _warn_unknown_model(self, model):
        if model not in self.MODELS:
            _logger.warning(
                "Model %r is not in Deepgram's known models %s; sending it anyway",
                model,
                list(self.MODELS),
            )

    def transcribe_url(self, audio_url, model=None, **kwargs):
        model = self._resolve_model(model)
        self._warn_unknown_model(model)
        response = self._client.post(
            "/listen",
            json={"url": audio_url},
            params=self._prepare_transcription_params(model=model, **kwargs),
        )
        return self._get_response_body(response)

    def transcribe_file(self, audio_data, mimetype=None, model=None, **kwargs):
        model = self._resolve_model(model)
        self._warn_unknown_model(model)
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
        model=None,
        **kwargs,
    ):
        del filename, prompt
        if not audio_bytes:
            raise CommError("Deepgram was given no audio to send")
        options = {"utterances": True, "smart_format": True, **kwargs}
        if language:
            options["language"] = language
        result = self.transcribe_file(
            audio_bytes, mimetype=mimetype, model=model, **options
        )
        return self._read_cues(result)

    def transcribe_with_diarization(self, audio_url, model=None, **kwargs):
        return self.transcribe_url(
            audio_url, model=model, **{**kwargs, "diarize": True, "utterances": True}
        )

    def transcribe_with_intelligence(
        self,
        audio_url,
        model=None,
        summarize=True,
        topics=True,
        sentiment=True,
        detect_entities=True,
        intents=True,
        **kwargs,
    ):
        return self.transcribe_url(
            audio_url,
            model=model,
            summarize=summarize,
            topics=topics,
            sentiment=sentiment,
            detect_entities=detect_entities,
            intents=intents,
            **kwargs,
        )

    def transcribe_multilingual(self, audio_url, model=None, **kwargs):
        return self.transcribe_url(
            audio_url, model=model, **{**kwargs, "detect_language": True}
        )

    _PII_REDACTIONS = ("pci", "ssn", "numbers", "email", "phone_number", "name")

    def transcribe_with_redaction(
        self,
        audio_url,
        redact_pii=True,
        model=None,
        **kwargs,
    ):
        if redact_pii:
            kwargs["redact"] = list(self._PII_REDACTIONS)
        return self.transcribe_url(audio_url, model=model, **kwargs)

    def transcribe_with_search(self, audio_url, search_terms, model=None, **kwargs):
        return self.transcribe_url(
            audio_url, model=model, **{**kwargs, "search": search_terms}
        )

    def transcribe_with_keywords(self, audio_url, keywords, model=None, **kwargs):
        return self.transcribe_url(
            audio_url,
            model=model,
            **{**kwargs, "keyterm": keywords, "keywords": keywords},
        )

    def streaming_transcribe(self, model=None, **kwargs):
        model = self._resolve_model(model)
        params = self._prepare_transcription_params(model=model, **kwargs)
        if kwargs.get("interim_results"):
            params["interim_results"] = "true"
        if kwargs.get("endpointing"):
            params["endpointing"] = kwargs["endpointing"]
        if kwargs.get("vad_events"):
            params["vad_events"] = "true"
        return {
            "websocket_url": "wss://api.deepgram.com/v1/listen?"
            + urlencode(params, doseq=True),
            "params": params,
            "connection_type": "websocket",
            "protocol": "wss",
        }

    SPEECH_ENCODINGS = {
        "audio/mpeg": {"encoding": "mp3"},
        "audio/ogg": {"encoding": "opus"},
        "audio/flac": {"encoding": "flac"},
        "audio/aac": {"encoding": "aac"},
        "audio/wav": {"encoding": "linear16", "container": "wav"},
    }

    def text_to_speech(self, text, voice=DEFAULT_VOICE, model=None, **kwargs):
        return self.synthesize(text, voice=voice, model=model, **kwargs)

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
        spans = []
        for utterance in (result or {}).get("results", {}).get("utterances", []) or []:
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
                }
            )
        if spans:
            return spans
        channels = (result or {}).get("results", {}).get("channels") or []
        alternatives = channels[0].get("alternatives") if channels else None
        transcript = (
            (alternatives[0].get("transcript") or "").strip() if alternatives else ""
        )
        if not transcript:
            raise CommError("Deepgram returned no usable transcript")
        return [{"start": 0.0, "end": 0.0, "text": transcript, "speaker": ""}]

    def analyze_audio(self, audio_url, model=None, **kwargs):
        result = self.transcribe_with_intelligence(
            audio_url, model=model, diarize=True, **kwargs
        )
        results = result.get("results") or {}
        channels = results.get("channels") or []
        if not channels:
            return {"error": "No transcription data available"}
        alternatives = channels[0].get("alternatives") or []
        if not alternatives:
            return {"error": "No transcription alternatives"}

        return {
            "transcript": alternatives[0].get("transcript", ""),
            **self._get_insights(result),
            "overall_sentiment": self._get_overall_sentiment(result),
            "speaker_count": len(
                {u.get("speaker") for u in results.get("utterances") or []}
            ),
            "duration": (result.get("metadata") or {}).get("duration", 0),
            "language": channels[0].get("detected_language", "unknown"),
            "raw_result": result,
        }

    def transcribe_conversation(
        self,
        audio_url,
        model=None,
        extract_insights=True,
        **kwargs,
    ):
        result = self.transcribe_with_intelligence(
            audio_url, model=model, diarize=True, **kwargs
        )
        results = result.get("results") or {}
        sentiments = self._get_sentiment_segments(result)
        turns = [
            {
                "speaker": utterance.get("speaker", 0),
                "text": utterance.get("transcript", ""),
                "start": utterance.get("start", 0),
                "end": utterance.get("end", 0),
                "confidence": utterance.get("confidence", 0),
                "sentiment": self._get_sentiment_for_timerange(
                    sentiments, utterance.get("start", 0), utterance.get("end", 0)
                ),
            }
            for utterance in results.get("utterances") or []
        ]
        conversation = {
            "turns": turns,
            "speaker_count": len({turn["speaker"] for turn in turns}),
            "duration": (result.get("metadata") or {}).get("duration", 0),
        }
        if extract_insights:
            conversation.update(self._get_insights(result))
        return conversation

    @staticmethod
    def _get_insights(result):
        results = result.get("results") or {}
        return {
            "summary": (results.get("summary") or {}).get("short", ""),
            "topics": [
                segment.get("topic")
                for segment in (results.get("topics") or {}).get("segments") or []
            ],
            "entities": results.get("entities") or [],
            "intents": results.get("intents") or {},
        }

    @staticmethod
    def _get_sentiment_segments(result):
        results = result.get("results") or {}
        return (results.get("sentiments") or {}).get("segments") or []

    def _get_overall_sentiment(self, result):
        sentiments = self._get_sentiment_segments(result)
        if not sentiments:
            return "neutral"
        counts = Counter(segment.get("sentiment") for segment in sentiments)
        for label in ("positive", "negative"):
            if counts[label] / len(sentiments) > 0.6:
                return label
        return "neutral"

    def _get_sentiment_for_timerange(self, sentiments, start, end):
        overlapping = Counter(
            segment.get("sentiment", "neutral")
            for segment in sentiments
            if segment.get("start", 0) <= end and segment.get("end", 0) >= start
        )
        return overlapping.most_common(1)[0][0] if overlapping else "neutral"

    def get_usage(self, result):
        metadata = result.get("metadata") or {}
        return {
            "duration": metadata.get("duration", 0),
            "channels": metadata.get("channels", 1),
            "model_uuid": metadata.get("model_uuid", ""),
            "model_name": (metadata.get("model_info") or {}).get("name", ""),
            "request_id": metadata.get("request_id", ""),
        }

    def get_available_models(self):
        return self.MODELS.copy()

    def get_available_voices(self):
        return self.TTS_VOICES.copy()

    def get_supported_languages(self):
        return self.LANGUAGES.copy()


def get_deepgram_client(env, company_id=None):
    return DeepgramClient(env, company_id)
