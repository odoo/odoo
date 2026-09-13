from __future__ import annotations

import base64
import logging
from typing import Any

from odoo.libs.debug_log import DebugLog
from odoo.libs.filesystem import guess_mimetype

from .formats import mimetype_for
from .guess import decode, is_text_like
from .readers import (
    BARCODES,
    CHEAP,
    CHILDREN,
    CUES,
    DATA,
    IMAGES,
    REPRESENTATIONS,
    ROWS,
    TEXT,
    TREE,
    get_readers,
)
from .writers import get_known_writer_names, get_writers

__all__ = [
    "DEFAULT_READ_UP_TO",
    "TEXT_MAX_CHARS",
    "Document",
    "get_essential_mimetype",
]

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

TEXT_MAX_CHARS = 60_000

# media families: their bytes may decode under some codec and pass the
# text-likeness sieve when short (a PNG header did), but carry no words
_OPAQUE_MIMETYPE_FAMILIES = ("image/", "audio/", "video/", "font/", "model/")

DEFAULT_READ_UP_TO = CHEAP

_DEFAULT_MIMETYPES = {
    ROWS: mimetype_for("csv"),
    TEXT: "text/plain",
    TREE: mimetype_for("xml"),
    DATA: mimetype_for("json"),
    CUES: mimetype_for("vtt"),
}


def get_essential_mimetype(mimetype: str) -> str:
    return mimetype.split(";", 1)[0].strip().lower()


def _clamp(text: str, name: str, limit: int = TEXT_MAX_CHARS) -> str:
    if limit <= 0 or len(text) <= limit:
        return text
    _debug.logic("document.text_clamped", chars=len(text), limit=limit)
    _logger.warning(
        "%r yields %d characters of text; using the first %d and dropping %d",
        name,
        len(text),
        limit,
        len(text) - limit,
    )
    return text[:limit]


class Document:
    def __init__(
        self,
        data: bytes,
        mimetype: str = "",
        name: str = "",
        **options: Any,
    ) -> None:
        if not data:
            raise ValueError("A document needs data.")
        self.data: bytes = data
        self.name: str = name
        self.mimetype: str = get_essential_mimetype(
            guess_mimetype(data, declared=mimetype)
        )
        self.options: dict[str, Any] = options
        self._derived: dict[str, Any] = {}
        self._derived_at: dict[str, int] = {}
        _debug.lifecycle(
            "document.created",
            mimetype=self.mimetype,
            declared=mimetype or None,
            size=len(data),
            named=bool(name),
            options=",".join(sorted(options)) or None,
        )

    @property
    def read_up_to(self) -> int:
        return self.options.get("read_up_to", DEFAULT_READ_UP_TO)

    @property
    def text_max_chars(self) -> int:
        return self.options.get("text_max_chars", TEXT_MAX_CHARS)

    @classmethod
    def of_bytes(
        cls, data: bytes | str, mimetype: str = "", name: str = "", **options: Any
    ) -> Document:
        if isinstance(data, str):
            raw = data.split(",", 1)[1] if data.startswith("data:") else data
            data = base64.b64decode(raw)
        return cls(data, mimetype, name, **options)

    @classmethod
    def of(
        cls,
        *,
        rows: Any = None,
        text: Any = None,
        tree: Any = None,
        data: Any = None,
        cues: Any = None,
        mimetype: str = "",
        name: str = "",
        **options: Any,
    ) -> Document:
        given = {
            ROWS: rows,
            TEXT: text,
            TREE: tree,
            DATA: data,
            CUES: cues,
        }
        named = [rep for rep, value in given.items() if value is not None]
        if len(named) != 1:
            raise ValueError(
                "A document is written from exactly one representation; got "
                f"{', '.join(named) if named else 'none'}"
            )
        representation = named[0]
        value = given[representation]
        mimetype = get_essential_mimetype(
            mimetype or _DEFAULT_MIMETYPES[representation]
        )
        writers = get_writers(mimetype, representation)
        _debug.logic(
            "document.writer_chosen",
            representation=representation,
            mimetype=mimetype,
            candidates=len(writers),
            writer=writers[0].name if writers else None,
        )
        if not writers:
            raise ValueError(
                f"Nothing writes {representation} as {mimetype!r}; "
                f"registered: {', '.join(get_known_writer_names()) or 'none'}"
            )
        with _debug.perf(
            "document.write", writer=writers[0].name, mimetype=mimetype
        ) as span:
            written = writers[0].write(value, **options)
            span.set(size=len(written))
        document = cls(written, mimetype, name, **options)
        document._derived[representation] = value
        return document

    @property
    def rows(self) -> list[list[Any]]:
        return self._derive(ROWS) or []

    @property
    def text(self) -> str:
        derived = self._derive(TEXT)
        if derived is None:
            if not get_readers(self.mimetype, TEXT):
                if self.mimetype.startswith(_OPAQUE_MIMETYPE_FAMILIES):
                    decoded = ""
                else:
                    try:
                        decoded = decode(self.data)
                    except UnicodeDecodeError as e:
                        _logger.info("Could not decode %r: %s", self.name, e)
                        decoded = ""
                derived = decoded if is_text_like(decoded) else ""
                self._derived[TEXT] = _clamp(derived, self.name, self.text_max_chars)
        return self._derived.get(TEXT) or ""

    @property
    def tree(self) -> Any:
        return self._derive(TREE)

    @property
    def data_dict(self) -> dict | list | None:
        return self._derive(DATA)

    @property
    def images(self) -> list[bytes]:
        return self._derive(IMAGES) or []

    @property
    def barcodes(self) -> list[str]:
        return self._derive(BARCODES) or []

    @property
    def children(self) -> list[Document]:
        return self._derive(CHILDREN) or []

    @property
    def cues(self) -> list[Any]:
        return self._derive(CUES) or []

    def _is_read(self, representation: str, value: Any) -> bool:
        if value is None:
            return False
        return True if representation == TREE else bool(value)

    def provides(self, representation: str) -> bool:
        if representation not in REPRESENTATIONS:
            raise ValueError(f"Unknown representation {representation!r}")
        cheap = [
            answer
            for reader in get_readers(self.mimetype, representation)
            if reader.cost <= self.read_up_to
            and (answer := reader.provides(self)) is not None
        ]
        if cheap:
            return any(cheap)
        if representation == TREE:
            return self.tree is not None
        return bool(
            getattr(self, "data_dict" if representation == DATA else representation)
        )

    def _derive(self, representation: str) -> Any:
        ceiling = self.read_up_to
        if representation in self._derived:
            cached = self._derived[representation]
            if self._is_read(representation, cached) or ceiling <= self._derived_at.get(
                representation, ceiling
            ):
                _debug.logic(
                    "document.derive.cached",
                    representation=representation,
                    mimetype=self.mimetype,
                    ceiling=ceiling,
                )
                return cached
        value = None
        clamp = representation == TEXT
        with _debug.perf(
            "document.derive",
            representation=representation,
            mimetype=self.mimetype,
            ceiling=ceiling,
        ) as span:
            tried = failed = skipped = 0  # debuglog
            winner = None  # debuglog
            for reader in get_readers(self.mimetype, representation):
                if reader.cost > ceiling:
                    skipped += 1  # debuglog
                    continue
                tried += 1  # debuglog
                try:
                    answer = reader.read(self)
                except Exception as e:
                    failed += 1  # debuglog
                    _debug.logic(
                        "document.reader_failed",
                        reader=reader.name,
                        representation=representation,
                        mimetype=self.mimetype,
                        error=type(e).__name__,
                    )
                    _logger.info(
                        "Reader %s could not derive %s from %r: %s",
                        reader.name,
                        representation,
                        self.name or self.mimetype,
                        e,
                    )
                    continue
                if answer is None:
                    continue
                read = self._is_read(representation, answer)
                if value is None or read:
                    value = answer
                    winner = reader.name  # debuglog
                if read:
                    break
            if clamp and value:
                value = _clamp(value, self.name, self.text_max_chars)
            span.set(
                tried=tried,
                failed=failed,
                skipped=skipped,
                reader=winner,
                read=self._is_read(representation, value),
            )
        self._derived[representation] = value
        self._derived_at[representation] = ceiling
        return value

    def __repr__(self) -> str:
        return f"<Document {self.name or '?'} {self.mimetype} {len(self.data)}B>"
