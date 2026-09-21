from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

__all__ = [
    "Cue",
    "cues_as_text",
    "format_offset",
    "parse_srt",
    "parse_vtt",
    "render_srt",
    "render_vtt",
]

_STAMP = r"(?:(\d+):)?([0-5]?\d):([0-5]\d)[.,](\d{1,3})"
_ARROW = re.compile(rf"^\s*{_STAMP}\s*-->\s*{_STAMP}\s*(?:\s.*)?$")
_VOICE = re.compile(r"^<v(?:\.\S+)*\s+([^>]*)>(.*)$", re.DOTALL)
_TAG = re.compile(r"</?[a-zA-Z][^>]*>")
_NOTE = re.compile(r"^(?:NOTE|STYLE|REGION)\b")
_BLANK = re.compile(r"\n\s*\n+")
_NUMERIC = re.compile(r"&#(x[0-9a-fA-F]+|[0-9]+);")

_REFERENCES = {
    "&amp;": "&",
    "&lt;": "<",
    "&gt;": ">",
    "&nbsp;": "\u00a0",
    "&lrm;": "\u200e",
    "&rlm;": "\u200f",
}


@dataclass(frozen=True, slots=True)
class Cue:
    start: float
    end: float
    text: str
    speaker: str = ""
    confidence: float = 0.0


def _timestamp_to_seconds(
    hours: str | None, minutes: str, secs: str, fraction: str
) -> float:
    return (
        int(hours or 0) * 3600
        + int(minutes) * 60
        + int(secs)
        + int(fraction.ljust(3, "0")) / 1000
    )


def _seconds_to_timestamp(value: float, separator: str) -> str:
    value = max(value, 0.0)
    milliseconds = round(value * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{milliseconds:03d}"


def _iter_blocks(text: str) -> Iterator[list[str]]:
    block: list[str] = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if line.strip():
            block.append(line)
        elif block:
            yield block
            block = []
    if block:
        yield block


def _split_speaker(text: str) -> tuple[str, str]:
    match = _VOICE.match(text)
    if not match:
        return "", text
    return match.group(1).strip(), match.group(2)


def _decode_references(text: str) -> str:
    for reference, character in _REFERENCES.items():
        text = text.replace(reference, character)
    return _NUMERIC.sub(
        lambda m: chr(
            int(m.group(1)[1:], 16) if m.group(1)[0] in "xX" else int(m.group(1))
        ),
        text,
    )


def _strip_tags(text: str, references: bool) -> str:
    stripped = _TAG.sub("", text).strip()
    return _decode_references(stripped) if references else stripped


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _collapse_blank_lines(text: str) -> str:
    return _BLANK.sub("\n", text)


def _parse(text: str, references: bool) -> list[Cue]:
    cues: list[Cue] = []
    for block in _iter_blocks(text):
        if _NOTE.match(block[0]):
            continue
        for index, line in enumerate(block):
            match = _ARROW.match(line)
            if not match:
                continue
            start = _timestamp_to_seconds(*match.group(1, 2, 3, 4))
            end = _timestamp_to_seconds(*match.group(5, 6, 7, 8))
            body = "\n".join(block[index + 1 :])
            speaker, spoken = _split_speaker(body)
            spoken = _strip_tags(spoken, references)
            if spoken:
                cues.append(
                    Cue(
                        start,
                        end,
                        spoken,
                        _decode_references(speaker) if references else speaker,
                    )
                )
            break
    return cues


def parse_vtt(text: str) -> list[Cue]:
    return _parse(text, references=True)


def parse_srt(text: str) -> list[Cue]:
    return _parse(text, references=False)


def _render_vtt_cue_text(cue: Cue) -> str:
    text = _collapse_blank_lines(_escape(cue.text))
    if not cue.speaker:
        return text
    return f"<v {_escape(cue.speaker)}>{text}"


def _render_srt_cue_text(cue: Cue) -> str:
    text = _collapse_blank_lines(cue.text)
    return f"{cue.speaker}: {text}" if cue.speaker else text


def render_vtt(cues: Iterable[Cue]) -> str:
    blocks = [
        f"{_seconds_to_timestamp(cue.start, '.')} --> {_seconds_to_timestamp(cue.end, '.')}\n{_render_vtt_cue_text(cue)}"
        for cue in cues
    ]
    return "WEBVTT\n\n" + "\n\n".join(blocks) + "\n"


def render_srt(cues: Iterable[Cue]) -> str:
    blocks = [
        f"{number}\n{_seconds_to_timestamp(cue.start, ',')} --> {_seconds_to_timestamp(cue.end, ',')}\n{_render_srt_cue_text(cue)}"
        for number, cue in enumerate(cues, start=1)
    ]
    return "\n\n".join(blocks) + "\n"


def cues_as_text(cues: Iterable[Cue], *, speakers: bool = False) -> str:
    return "\n".join(
        f"{cue.speaker}: {cue.text}" if speakers and cue.speaker else cue.text
        for cue in cues
        if cue.text
    )


def format_offset(seconds: float) -> str:
    minutes, secs = divmod(int(max(seconds, 0.0)), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"
