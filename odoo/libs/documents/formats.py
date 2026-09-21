from __future__ import annotations

from dataclasses import dataclass, field

from .representations import CUES, DATA, IMAGES, REPRESENTATIONS, ROWS, TEXT, TREE

__all__ = [
    "RECORDING_EXTENSIONS",
    "RECORDING_MIMETYPES",
    "Format",
    "canonical_mimetypes",
    "extension_for",
    "get_format",
    "get_format_of_extension",
    "get_known_formats",
    "mimetype_for",
    "mimetypes_for",
    "register_extension",
    "register_format",
]


@dataclass(frozen=True, slots=True)
class Format:
    mimetype: str
    extension: str
    representation: str
    accepts: frozenset[str] = field(default_factory=frozenset)
    label: str = ""

    @property
    def mimetypes(self) -> frozenset[str]:
        return frozenset({self.mimetype, *self.accepts})

    def __repr__(self) -> str:
        return f"<Format {self.extension} {self.mimetype}>"


_FORMATS: list[Format] = []
_BY_MIMETYPE: dict[str, Format] = {}
_BY_EXTENSION: dict[str, Format] = {}
_BY_ALIAS: dict[str, Format] = {}


def register_format(fmt: Format) -> Format:
    if not fmt.mimetype:
        raise ValueError(f"{fmt!r} must name a mimetype")
    if not fmt.extension:
        raise ValueError(f"Format {fmt.mimetype!r} must name an extension")
    if fmt.representation not in REPRESENTATIONS:
        raise ValueError(
            f"Format {fmt.mimetype!r} claims unknown representation "
            f"{fmt.representation!r}; expected one of {', '.join(REPRESENTATIONS)}"
        )
    mimetype = fmt.mimetype.lower()
    extension = fmt.extension.lower().lstrip(".")
    if mimetype in _BY_MIMETYPE:
        raise ValueError(f"{mimetype!r} is already registered")
    if extension in _BY_EXTENSION:
        raise ValueError(f"{extension!r} is already registered")
    _FORMATS.append(fmt)
    _BY_MIMETYPE[mimetype] = fmt
    _BY_EXTENSION[extension] = fmt
    for alias in fmt.accepts:
        _BY_ALIAS.setdefault(alias.lower(), fmt)
    return fmt


def register_extension(extension: str, mimetype: str) -> Format:
    extension = (extension or "").lower().lstrip(".")
    fmt = _BY_MIMETYPE.get((mimetype or "").lower())
    if fmt is None:
        raise ValueError(f"No format is registered for {mimetype!r}")
    if not extension:
        raise ValueError(f"An extension for {mimetype!r} cannot be empty")
    registered = _BY_EXTENSION.get(extension)
    if registered is not None and registered is not fmt:
        raise ValueError(
            f"{extension!r} already means {registered.mimetype!r}, not {mimetype!r}"
        )
    _BY_EXTENSION[extension] = fmt
    return fmt


def get_format(mimetype: str) -> Format | None:
    mimetype = (mimetype or "").lower()
    return _BY_MIMETYPE.get(mimetype) or _BY_ALIAS.get(mimetype)


def get_format_of_extension(extension: str) -> Format | None:
    return _BY_EXTENSION.get((extension or "").lower().lstrip("."))


def mimetype_for(extension: str) -> str:
    fmt = get_format_of_extension(extension)
    return fmt.mimetype if fmt else ""


def extension_for(mimetype: str) -> str:
    fmt = _BY_MIMETYPE.get((mimetype or "").lower())
    return fmt.extension if fmt else ""


def mimetypes_for(*extensions: str) -> frozenset[str]:
    claimed: set[str] = set()
    for fmt in _get_formats_of_extensions(extensions):
        claimed |= fmt.mimetypes
    return frozenset(claimed)


def canonical_mimetypes(*extensions: str) -> frozenset[str]:
    return frozenset(fmt.mimetype for fmt in _get_formats_of_extensions(extensions))


def _get_formats_of_extensions(extensions: tuple[str, ...]) -> tuple[Format, ...]:
    found = []
    for extension in extensions:
        fmt = get_format_of_extension(extension)
        if fmt is None:
            raise ValueError(f"No format is registered under {extension!r}")
        found.append(fmt)
    return tuple(found)


def get_known_formats() -> tuple[Format, ...]:
    return tuple(_FORMATS)


_BUILTIN_FORMATS = (
    (
        "text/csv",
        "csv",
        ROWS,
        {"text/plain", "application/csv"},
        "Comma-separated values",
    ),
    ("application/xml", "xml", TREE, {"text/xml", "application/xhtml+xml"}, "XML"),
    ("application/json", "json", DATA, {"text/json"}, "JSON"),
    ("text/vtt", "vtt", CUES, (), "WebVTT"),
    ("application/x-subrip", "srt", CUES, {"application/x-srt", "text/srt"}, "SubRip"),
    ("application/pdf", "pdf", TEXT, (), "PDF"),
    ("image/png", "png", IMAGES, (), "PNG image"),
    ("image/jpeg", "jpg", IMAGES, {"image/jpg", "image/jpe"}, "JPEG image"),
    ("image/webp", "webp", IMAGES, (), "WebP image"),
    ("image/gif", "gif", IMAGES, (), "GIF image"),
    ("image/bmp", "bmp", IMAGES, (), "Bitmap image"),
    ("image/svg+xml", "svg", TREE, (), "SVG image"),
    (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xlsx",
        ROWS,
        {"application/vnd.ms-excel.sheet.macroenabled.12"},
        "Excel workbook",
    ),
    ("application/vnd.ms-excel", "xls", ROWS, (), "Excel 97-2003 workbook"),
    (
        "application/vnd.oasis.opendocument.spreadsheet",
        "ods",
        ROWS,
        (),
        "OpenDocument spreadsheet",
    ),
    (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "docx",
        TEXT,
        (),
        "Word document",
    ),
    (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "pptx",
        TEXT,
        (),
        "PowerPoint presentation",
    ),
    ("application/vnd.oasis.opendocument.text", "odt", TEXT, (), "OpenDocument text"),
    (
        "application/vnd.oasis.opendocument.presentation",
        "odp",
        TEXT,
        (),
        "OpenDocument presentation",
    ),
    (
        "application/vnd.oasis.opendocument.graphics",
        "odg",
        TEXT,
        (),
        "OpenDocument graphics",
    ),
    ("application/msword", "doc", TEXT, (), "Word 97-2003 document"),
    (
        "application/vnd.ms-powerpoint",
        "ppt",
        TEXT,
        (),
        "PowerPoint 97-2003 presentation",
    ),
)
_BUILTIN_RECORDING_FORMATS = (
    ("audio/mpeg", "mp3", {"audio/mp3", "audio/x-mpeg"}, "MP3 audio"),
    ("audio/ogg", "ogg", {"audio/opus", "audio/vorbis"}, "Ogg audio"),
    ("audio/wav", "wav", {"audio/x-wav", "audio/wave"}, "WAV audio"),
    ("audio/webm", "weba", (), "WebM audio"),
    ("audio/mp4", "m4a", {"audio/x-m4a"}, "MPEG-4 audio"),
    ("audio/flac", "flac", {"audio/x-flac"}, "FLAC audio"),
    ("audio/aac", "aac", (), "AAC audio"),
    ("video/webm", "webm", (), "WebM video"),
    ("video/mp4", "mp4", (), "MPEG-4 video"),
    ("video/quicktime", "mov", (), "QuickTime video"),
    ("video/x-matroska", "mkv", (), "Matroska video"),
    ("video/mpeg", "mpeg", (), "MPEG video"),
    ("video/ogg", "ogv", (), "Ogg video"),
)
RECORDING_EXTENSIONS = tuple(
    extension for _, extension, _, _ in _BUILTIN_RECORDING_FORMATS
)
_BUILTIN_EXTENSION_ALIASES = (("jpeg", "image/jpeg"),)

for _mimetype, _extension, _representation, _accepts, _label in _BUILTIN_FORMATS:
    register_format(
        Format(
            mimetype=_mimetype,
            extension=_extension,
            representation=_representation,
            accepts=frozenset(_accepts),
            label=_label,
        )
    )
for _mimetype, _extension, _accepts, _label in _BUILTIN_RECORDING_FORMATS:
    register_format(
        Format(
            mimetype=_mimetype,
            extension=_extension,
            representation=CUES,
            accepts=frozenset(_accepts),
            label=_label,
        )
    )
for _extension, _mimetype in _BUILTIN_EXTENSION_ALIASES:
    register_extension(_extension, _mimetype)

RECORDING_MIMETYPES = mimetypes_for(*RECORDING_EXTENSIONS)
