"""Checks on the commit message that need no judgement: the odoo-git header shape,
line widths, ASCII, the ticket trailer, and the absence of invented or bot-generated
references.
"""

import re
from pathlib import Path

from rewardkit import criterion

MESSAGE = Path("/logs/verifier/commit_message.txt")
TICKET = "opw-6425088"
HEADER_RE = re.compile(r"\[FIX\] snailmail: \S.*")
REFERENCE_RE = re.compile(r"\b(?:opw|task|runbot)-\d+\b|\bFixes #\d+", re.IGNORECASE)
BOT_METADATA = ("closes odoo/", "Part-of:", "Signed-off-by:", "X-original-commit:", "Related: odoo/", "Forward-port-of")


def _message() -> str:
    return MESSAGE.read_text() if MESSAGE.exists() else ""


def _parts() -> tuple[str, list[str]]:
    lines = _message().rstrip("\n").split("\n")
    header = lines[0] if lines else ""
    body = lines[2:] if len(lines) > 2 and lines[1] == "" else lines[1:]
    return header, body


def _paragraphs(lines: list[str]) -> list[list[str]]:
    paragraphs, current = [], []
    for line in lines:
        if line.strip():
            current.append(line)
        elif current:
            paragraphs.append(current)
            current = []
    if current:
        paragraphs.append(current)
    return paragraphs


def _result(score: float, reasoning: str) -> dict:
    return {"score": score, "reasoning": reasoning}


@criterion
def header_shape(workspace: Path) -> dict:
    header, _ = _parts()
    ok = bool(HEADER_RE.fullmatch(header)) and not header.endswith(".")
    return _result(1.0 if ok else 0.0, f"header: {header!r}" + ("" if ok else " (expected '[FIX] snailmail: <summary>' without a trailing period)"))


@criterion
def header_length(workspace: Path) -> dict:
    header, _ = _parts()
    n = len(header)
    score = 1.0 if n <= 72 else 0.5 if n <= 80 else 0.0
    return _result(score, f"header is {n} characters (full marks up to 72, half up to 80)")


@criterion
def body_present(workspace: Path) -> dict:
    _, body = _parts()
    content = [line for line in body if line.strip() and not REFERENCE_RE.fullmatch(line.strip())]
    score = min(len(content) / 6, 1.0)
    return _result(score, f"{len(content)} non-empty body lines besides trailers (full marks from 6)")


@criterion
def body_wrapped(workspace: Path) -> dict:
    _, body = _parts()
    widths = [len(line) for line in body]
    longest = max(widths, default=0)
    score = 1.0 if longest <= 72 else 0.5 if longest <= 80 else 0.0
    return _result(score, f"longest body line is {longest} characters (full marks up to 72, half up to 80)")


@criterion
def ascii_only(workspace: Path) -> dict:
    msg = _message()
    bad = sorted({c for c in msg if not c.isascii()})
    return _result(1.0 if not bad else 0.0, "ASCII only" if not bad else f"non-ASCII characters: {bad}")


@criterion
def ticket_trailer(workspace: Path) -> dict:
    _, body = _parts()
    paragraphs = _paragraphs(body)
    last = [line.strip().lower() for line in paragraphs[-1]] if paragraphs else []
    anywhere = TICKET in _message().lower()
    if TICKET in last:
        return _result(1.0, f"{TICKET} is a trailer in the last paragraph")
    if anywhere:
        return _result(0.5, f"{TICKET} is mentioned but not as a trailer in the last paragraph")
    return _result(0.0, f"{TICKET} is missing; the ticket was given in the instruction")


@criterion
def no_invented_references(workspace: Path) -> dict:
    refs = sorted({m.lower() for m in REFERENCE_RE.findall(_message())})
    extra = [r for r in refs if r != TICKET]
    return _result(1.0 if not extra else 0.0, "no reference beyond the ticket" if not extra else f"references not given in the instruction: {extra}")


@criterion
def no_bot_metadata(workspace: Path) -> dict:
    msg = _message()
    found = [m for m in BOT_METADATA if m.lower() in msg.lower()]
    return _result(1.0 if not found else 0.0, "no merge-bot or forward-port metadata" if not found else f"metadata the bots add was written by hand: {found}")
