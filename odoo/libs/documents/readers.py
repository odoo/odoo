from __future__ import annotations

import csv
import io
import json
from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from .formats import RECORDING_EXTENSIONS, mimetypes_for
from .representations import (
    ANY,
    BARCODES,
    CHEAP,
    CHILDREN,
    CUES,
    DATA,
    EXPENSIVE,
    FREE,
    IMAGES,
    REPRESENTATIONS,
    ROWS,
    TEXT,
    TREE,
)

__all__ = [
    "ANY",
    "BARCODES",
    "CHEAP",
    "CHILDREN",
    "CUES",
    "DATA",
    "EXPENSIVE",
    "FREE",
    "IMAGES",
    "REPRESENTATIONS",
    "ROWS",
    "TEXT",
    "TREE",
    "BaseReader",
    "get_known_reader_names",
    "get_readers",
    "reader_rank",
    "register_reader",
    "registered_readers",
    "unregister_reader",
]


@runtime_checkable
class Reader(Protocol):
    name: str
    mimetypes: frozenset[str]
    yields: tuple[str, ...]
    cost: int

    def read(self, document: Any) -> Any: ...


class BaseReader:
    name: str = ""
    mimetypes: frozenset[str] = frozenset()
    yields: tuple[str, ...] = ()
    cost: int = FREE
    defers: bool = False

    def read(self, document: Any) -> Any:
        raise NotImplementedError

    def applies_to(self, mimetype: str) -> bool:
        return ANY in self.mimetypes or mimetype in self.mimetypes

    def provides(self, document: Any) -> bool | None:
        _ = document
        return None

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.name}>"


_READERS: dict[str, list[BaseReader]] = {name: [] for name in REPRESENTATIONS}


def register_reader(reader: BaseReader) -> BaseReader:
    if not reader.name:
        raise ValueError(f"{reader!r} must name itself")
    if not reader.yields:
        raise ValueError(f"Reader {reader.name!r} yields no representation")
    unknown = set(reader.yields) - set(REPRESENTATIONS)
    if unknown:
        raise ValueError(
            f"Reader {reader.name!r} yields unknown representation(s) "
            f"{', '.join(sorted(unknown))}; expected one of "
            f"{', '.join(REPRESENTATIONS)}"
        )
    if not reader.mimetypes:
        raise ValueError(f"Reader {reader.name!r} accepts no mimetype")
    if not isinstance(getattr(reader, "cost", None), int):
        raise ValueError(f"Reader {reader.name!r} declares no cost")
    for representation in reader.yields:
        _READERS[representation].append(reader)
    return reader


def unregister_reader(reader: BaseReader) -> None:
    for readers in _READERS.values():
        while reader in readers:
            readers.remove(reader)


def get_readers(mimetype: str, representation: str) -> tuple[BaseReader, ...]:
    if representation not in _READERS:
        raise ValueError(f"Unknown representation {representation!r}")
    named, fallback = [], []
    for reader in _READERS[representation]:
        if ANY in reader.mimetypes:
            if reader.applies_to(mimetype):
                fallback.append(reader)
        elif reader.applies_to(mimetype):
            named.append(reader)
    return (*sorted(named, key=reader_rank), *sorted(fallback, key=reader_rank))


def reader_rank(reader: BaseReader) -> tuple[int, bool]:
    return (reader.cost, getattr(reader, "defers", False))


def registered_readers() -> tuple[BaseReader, ...]:
    seen: dict[int, BaseReader] = {}
    for readers in _READERS.values():
        for reader in readers:
            seen.setdefault(id(reader), reader)
    return tuple(seen.values())


def get_known_reader_names() -> tuple[str, ...]:
    seen: dict[str, None] = {}
    for readers in _READERS.values():
        for reader in readers:
            seen.setdefault(reader.name, None)
    return tuple(sorted(seen))


def _prepare_reader(
    name: str,
    mimetypes: frozenset[str],
    yields: tuple[str, ...],
    read: Callable[..., Any],
    cost: int = FREE,
) -> BaseReader:
    reader = BaseReader()
    reader.name = name
    reader.mimetypes = mimetypes
    reader.yields = yields
    reader.cost = cost
    reader.read = read  # type: ignore[method-assign]
    return reader


def _read_tree(document: Any) -> Any:
    from lxml import etree

    return etree.fromstring(
        document.data,
        parser=etree.XMLParser(
            remove_comments=True, resolve_entities=False, decompress=False
        ),
    )


def _read_data(document: Any) -> Any:
    return json.loads(document.data)


def _read_csv_rows(document: Any) -> list[list[str]]:
    from .guess import decode

    options = document.options
    separator = options.get("separator") or ","
    quoting = options.get("quoting") or '"'
    try:
        text = decode(document.data)
    except UnicodeDecodeError:
        return []
    reader = csv.reader(io.StringIO(text), delimiter=separator, quotechar=quoting)
    return [list(row) for row in reader]


def _read_vtt_cues(document: Any) -> Any:
    from .cues import parse_vtt
    from .guess import decode

    try:
        return parse_vtt(decode(document.data))
    except UnicodeDecodeError:
        return []


def _read_srt_cues(document: Any) -> Any:
    from .cues import parse_srt
    from .guess import decode

    try:
        return parse_srt(decode(document.data))
    except UnicodeDecodeError:
        return []


def _read_cued_text(document: Any) -> str:
    from .cues import cues_as_text

    return cues_as_text(document.cues, speakers=True)


register_reader(_prepare_reader("xml", mimetypes_for("xml"), (TREE,), _read_tree))
register_reader(_prepare_reader("json", mimetypes_for("json"), (DATA,), _read_data))
register_reader(_prepare_reader("csv", mimetypes_for("csv"), (ROWS,), _read_csv_rows))
register_reader(_prepare_reader("vtt", mimetypes_for("vtt"), (CUES,), _read_vtt_cues))
register_reader(_prepare_reader("srt", mimetypes_for("srt"), (CUES,), _read_srt_cues))
register_reader(
    _prepare_reader(
        "cued_text",
        mimetypes_for("vtt", "srt", *RECORDING_EXTENSIONS),
        (TEXT,),
        _read_cued_text,
    )
)
