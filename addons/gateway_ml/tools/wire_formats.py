def get_openai_content(text, images):
    if not images:
        return text
    return [
        {"type": "text", "text": text},
        *(
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mimetype};base64,{data}"},
            }
            for data, mimetype in images
        ),
    ]


def get_anthropic_content(text, images):
    if not images:
        return text
    return [
        {"type": "text", "text": text},
        *(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mimetype,
                    "data": data,
                },
            }
            for data, mimetype in images
        ),
    ]


def read_openai_content(payload):
    if not isinstance(payload, dict):
        return "", f"expected a JSON object, got {type(payload).__name__}"
    try:
        choice = payload["choices"][0]
    except KeyError, IndexError, TypeError:
        return "", "response carried no choices"
    content = (choice.get("message") or {}).get("content") or ""
    finish = choice.get("finish_reason")
    if not content:
        return "", f"empty content (finish_reason={finish})"
    if finish == "length":
        return "", f"truncated at the token cap (finish_reason={finish})"
    return content, None


def read_anthropic_content(payload):
    if not isinstance(payload, dict):
        return "", f"expected a JSON object, got {type(payload).__name__}"
    blocks = payload.get("content")
    if not isinstance(blocks, list):
        return "", "response carried no content blocks"
    text = "".join(
        block.get("text") or ""
        for block in blocks
        if isinstance(block, dict) and block.get("type") == "text"
    )
    stop = payload.get("stop_reason")
    if not text:
        return "", f"no text blocks (stop_reason={stop})"
    if stop == "max_tokens":
        return "", f"truncated at the token cap (stop_reason={stop})"
    return text, None


# OpenAI's transcription guide documents `languages` for gpt-transcribe, and no
# segment timestamps; `json` is the one format every transcription model takes.
UNTIMED_TRANSCRIPTION_MODELS = frozenset({"gpt-transcribe"})


def get_whisper_form(
    audio_model,
    language=None,
    prompt=None,
    response_format="text",
    untimed=None,
    language_key=None,
):
    if untimed is None:
        untimed = audio_model in UNTIMED_TRANSCRIPTION_MODELS
    if untimed and response_format != "text":
        raise ValueError(
            f"{audio_model} returns no segment timestamps, so it cannot answer "
            f"{response_format!r}",
        )
    form = {
        "response_format": "json" if untimed else response_format,
        "model": audio_model,
    }
    if language:
        form[language_key or ("languages[]" if untimed else "language")] = language
    if prompt:
        form["prompt"] = prompt
    if response_format == "verbose_json":
        form["timestamp_granularities[]"] = "segment"
    return form


def read_whisper_segments(payload):
    if not isinstance(payload, dict):
        return None, f"expected a verbose transcript, got {type(payload).__name__}"
    segments = payload.get("segments")
    if segments is None:
        text = (payload.get("text") or "").strip()
        if not text:
            return None, "empty transcript"
        return [{"start": 0.0, "end": 0.0, "text": text, "speaker": ""}], None
    spans = [
        {
            "start": float(segment.get("start") or 0.0),
            "end": float(segment.get("end") or 0.0),
            "text": (segment.get("text") or "").strip(),
            "speaker": "",
        }
        for segment in segments
        if (segment.get("text") or "").strip()
    ]
    if not spans:
        return None, "empty transcript"
    return spans, None


def read_whisper_transcript(payload):
    if payload is None:
        return None, "no response"
    if isinstance(payload, dict) and isinstance(payload.get("text"), str):
        payload = payload["text"]
    if not isinstance(payload, str):
        return None, f"expected text, got {type(payload).__name__}"
    text = payload.strip()
    if not text:
        return None, "empty transcript"
    return text, None


def audio_mimetype(filename):
    lowered = (filename or "").lower()
    for suffix, mimetype in (
        (".mp3", "audio/mpeg"),
        (".m4a", "audio/mp4"),
        (".mp4", "audio/mp4"),
        (".wav", "audio/wav"),
        (".flac", "audio/flac"),
        (".webm", "audio/webm"),
    ):
        if lowered.endswith(suffix):
            return mimetype
    return "audio/ogg"


VOCABULARY_PROMPT_CHARS = 800


def vocabulary_prompt(vocabulary):
    return (
        ", ".join(term for term in vocabulary or () if term)[:VOCABULARY_PROMPT_CHARS]
        or None
    )


class Cues(list):
    def __init__(self, spans=(), duration=0.0):
        super().__init__(spans)
        self.duration = float(duration or 0.0) or max(
            (float(span.get("end") or 0.0) for span in self), default=0.0
        )
