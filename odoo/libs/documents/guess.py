from __future__ import annotations

import codecs

try:
    import chardet
except ImportError:
    chardet = None


__all__ = [
    "decode",
    "guess_encoding",
]
_ENCODING_CHUNK = 1 << 16

_ENCODING_SAMPLE_MAX = 1 << 18

_BOM_MAP = {
    "utf-16le": codecs.BOM_UTF16_LE,
    "utf-16be": codecs.BOM_UTF16_BE,
    "utf-32le": codecs.BOM_UTF32_LE,
    "utf-32be": codecs.BOM_UTF32_BE,
}


def _first_non_ascii_chunk(data: bytes) -> int:
    for start in range(0, len(data), _ENCODING_CHUNK):
        if not data[start : start + _ENCODING_CHUNK].isascii():
            return start
    return 0


def _is_valid_utf8(data: bytes) -> bool:
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def guess_encoding(data: bytes) -> str | None:
    # UTF-8 validates itself: a multibyte sequence that decodes strictly is
    # UTF-8 for any practical purpose, while chardet's probers, fed a short
    # Spanish sentence, answered johab
    if not data.isascii() and _is_valid_utf8(data):
        return "utf-8-sig" if data.startswith(codecs.BOM_UTF8) else "utf-8"
    if chardet is None:
        return None
    detector = chardet.UniversalDetector()
    # the probers learn nothing from plain ASCII, so the sample starts at the
    # chunk holding the first byte that is not; an all-ASCII buffer (which may
    # still be ISO-2022 escapes) keeps the head window
    sample_start = max(0, _first_non_ascii_chunk(data) - _ENCODING_CHUNK)
    sample_end = min(len(data), sample_start + _ENCODING_SAMPLE_MAX)
    for start in range(sample_start, sample_end, _ENCODING_CHUNK):
        detector.feed(data[start : start + _ENCODING_CHUNK])
        if detector.done:
            break
    detector.close()
    encoding = detector.result["encoding"]
    if not encoding:
        return None
    encoding = encoding.lower()
    bom = _BOM_MAP.get(encoding)
    if bom and data.startswith(bom):
        encoding = encoding[:-2]
    try:
        codecs.lookup(encoding)
    except LookupError:
        return None
    return encoding


def decode(data: bytes, encoding: str = "") -> str:
    name = encoding or guess_encoding(data)
    if not name:
        raise UnicodeDecodeError(
            "undetermined", data, 0, len(data), "the encoding could not be guessed"
        )
    return data.decode(name)


def is_text_like(text: str) -> bool:
    if not text:
        return False
    if "\x00" in text:
        return False
    control = sum(1 for c in text[:4096] if c < " " and c not in "\t\n\r\f\v")
    return control <= len(text[:4096]) // 20
