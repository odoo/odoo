import codecs
import io
import json
import logging
import mimetypes
import re
import zipfile
from collections.abc import Callable
from typing import Literal, NamedTuple

from odoo.libs.debug_log import DebugLog

_utf8_incremental_decoder = codecs.getincrementaldecoder("utf-8")

__all__ = [
    "MIMETYPE_HEAD_SIZE",
    "UNKNOWN_MIMETYPE",
    "_olecf_mimetypes",
    "fix_filename_extension",
    "get_extension",
    "guess_mimetype",
]

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)
_logger_guess_mimetype = _logger.getChild("guess_mimetype")
MIMETYPE_HEAD_SIZE = 2048
UNKNOWN_MIMETYPE = "application/octet-stream"


_ooxml_dirs = {
    "word/": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "ppt/": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "xl/": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def _get_ooxml_mimetype(data: bytes) -> str | Literal[False]:
    with io.BytesIO(data) as f, zipfile.ZipFile(f) as z:
        filenames = z.namelist()
        if "[Content_Types].xml" not in filenames:
            return False

        for dirname, mime in _ooxml_dirs.items():
            if any(entry.startswith(dirname) for entry in filenames):
                return mime

        return False


_mime_validator = re.compile(
    r"""
    [\w-]+ # type-name
    / # subtype separator
    [\w-]+ # registration facet or subtype
    (?:\.[\w-]+)* # optional faceted name
    (?:\+[\w-]+)? # optional structured syntax specifier
""",
    re.VERBOSE,
)


def _get_open_container_mimetype(data: bytes) -> str | Literal[False]:
    with io.BytesIO(data) as f, zipfile.ZipFile(f) as z:
        if "mimetype" not in z.namelist():
            return False

        with z.open("mimetype") as mimetype_file:
            try:
                declared = mimetype_file.read(256).decode("ascii")
            except UnicodeDecodeError:
                return False
        matched = _mime_validator.fullmatch(declared)
        return matched[0] if matched else False


_old_ms_office_mimetypes = {
    ".doc": "application/msword",
    ".xls": "application/vnd.ms-excel",
    ".ppt": "application/vnd.ms-powerpoint",
}
_olecf_mimetypes = ("application/x-ole-storage", "application/CDFV2")

_olecf_streams = (
    ("WordDocument".encode("utf-16-le"), "application/msword"),
    ("Workbook".encode("utf-16-le"), "application/vnd.ms-excel"),
    ("Book".encode("utf-16-le"), "application/vnd.ms-excel"),
    ("PowerPoint Document".encode("utf-16-le"), "application/vnd.ms-powerpoint"),
)
_ppt_pattern = re.compile(
    rb"""
    \x00\x6e\x1e\xf0
  | \x0f\x00\xe8\x03
  | \xa0\x46\x1d\xf0
  | \xfd\xff\xff\xff(\x0e|\x1c|\x43)\x00\x00\x00
""",
    re.VERBOSE,
)


_OLECF_SCAN_LIMIT = 1 << 16


def _get_olecf_mimetype(data: bytes) -> str | Literal[False]:
    offset = 0x200
    head = data[:_OLECF_SCAN_LIMIT]
    if data.startswith(b"\xec\xa5\xc1\x00", offset):
        return "application/msword"
    elif b"Microsoft Excel" in head:
        return "application/vnd.ms-excel"
    elif _ppt_pattern.match(data, offset):
        return "application/vnd.ms-powerpoint"
    for stream, mimetype in _olecf_streams:
        if stream in head:
            return mimetype
    return False


def _get_svg_mimetype(data: bytes) -> str | None:
    if b"<svg" in data and b"/svg" in data:
        return "image/svg+xml"
    return None


def _get_webp_mimetype(data: bytes) -> str | None:
    if data[8:15] == b"WEBPVP8":
        return "image/webp"
    return None


class _Entry(NamedTuple):
    mimetype: str
    signatures: list[bytes]
    discriminants: list[Callable[[bytes], str | bool | None]]


_mime_mappings = (
    _Entry("application/pdf", [b"%PDF"], []),
    _Entry(
        "image/jpeg",
        [
            b"\xff\xd8\xff\xe0",
            b"\xff\xd8\xff\xe2",
            b"\xff\xd8\xff\xe3",
            b"\xff\xd8\xff\xe1",
            b"\xff\xd8\xff\xdb",
        ],
        [],
    ),
    _Entry("image/png", [b"\x89PNG\r\n\x1a\n"], []),
    _Entry("image/gif", [b"GIF87a", b"GIF89a"], []),
    _Entry("image/bmp", [b"BM"], []),
    _Entry(
        "text/xml",
        [b"<"],
        [
            _get_svg_mimetype,
        ],
    ),
    _Entry("image/x-icon", [b"\x00\x00\x01\x00"], []),
    _Entry(
        "image/webp",
        [b"RIFF"],
        [
            _get_webp_mimetype,
        ],
    ),
    _Entry(
        "application/msword",
        [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", b"\x0d\x44\x4f\x43"],
        [_get_olecf_mimetype],
    ),
    _Entry(
        "application/zip",
        [b"PK\x03\x04"],
        [_get_ooxml_mimetype, _get_open_container_mimetype],
    ),
)


def _guess_mimetype_by_signature(
    bin_data: bytes, default: str = UNKNOWN_MIMETYPE
) -> str:
    for entry in _mime_mappings:
        for signature in entry.signatures:
            if bin_data.startswith(signature):
                for discriminant in entry.discriminants:
                    try:
                        guess = discriminant(bin_data)
                        if isinstance(guess, str):
                            return guess
                    except Exception:
                        _logger_guess_mimetype.warning(
                            "Sub-checker '%s' of type '%s' failed",
                            discriminant.__name__,
                            entry.mimetype,
                            exc_info=True,
                        )
                return entry.mimetype
    try:
        head = _utf8_incremental_decoder().decode(bin_data[:1024], final=False)
    except ValueError:
        return default
    if head and all(c >= " " or c in "\t\n\r" for c in head):
        return "text/plain"
    return default


try:
    import magic
except ImportError:
    magic = None


_UNPLACED = frozenset(
    {"", UNKNOWN_MIMETYPE, "text/plain", "application/x-empty", "binary/octet-stream"}
)


def _parses_as_xml(data: bytes) -> bool:
    try:
        from lxml import etree

        etree.fromstring(
            data,
            parser=etree.XMLParser(resolve_entities=False, decompress=False),
        )
    except Exception:
        return False
    return True


def _parses_as_json(data: bytes) -> bool:
    try:
        json.loads(data)
    except Exception:
        return False
    return True


def _resolve_structured_text_mimetype(data: bytes) -> str | None:
    head = data.lstrip()[:1]
    if head == b"<" and _parses_as_xml(data):
        return "application/xml"
    if head in (b"{", b"[") and _parses_as_json(data):
        return "application/json"
    return None


def guess_mimetype(
    bin_data: bytes | bytearray,
    default: str = UNKNOWN_MIMETYPE,
    *,
    declared: str = "",
) -> str:
    if isinstance(bin_data, bytearray):
        bin_data = bytes(bin_data)
    elif not isinstance(bin_data, bytes):
        msg = "`bin_data` must be bytes or bytearray"
        raise TypeError(msg)
    declared = (declared or "").lower()
    if declared and declared not in _UNPLACED:
        _debug.logic("mimetype.guessed", source="declared", mimetype=declared)
        return declared
    mimetype = _probe_mimetype(bin_data, default)
    if mimetype.lower() not in _UNPLACED:
        _debug.logic(
            "mimetype.guessed",
            source="probe",
            mimetype=mimetype,
            declared=declared or None,
            size=len(bin_data),
        )
        return mimetype
    resolved = _resolve_structured_text_mimetype(bin_data)
    _debug.logic(
        "mimetype.guessed",
        source="structured_text" if resolved else "fallback",
        mimetype=resolved or mimetype or UNKNOWN_MIMETYPE,
        probed=mimetype,
        declared=declared or None,
        size=len(bin_data),
    )
    return resolved or mimetype or UNKNOWN_MIMETYPE


def _probe_mimetype(bin_data: bytes, default: str) -> str:
    if magic is not None:
        mimetype = magic.from_buffer(bin_data[:MIMETYPE_HEAD_SIZE], mime=True)
    else:
        mimetype = UNKNOWN_MIMETYPE
    if mimetype == UNKNOWN_MIMETYPE:
        mimetype = _guess_mimetype_by_signature(bin_data, default)
        _debug.logic(
            "mimetype.probed_by_signature",
            magic=magic is not None,
            mimetype=mimetype,
            size=len(bin_data),
        )
    if mimetype in _olecf_mimetypes:
        try:
            if msoffice_mimetype := _get_olecf_mimetype(bin_data):
                return msoffice_mimetype
        except Exception:
            _logger_guess_mimetype.warning(
                "Sub-checker '_get_olecf_mimetype' of type '%s' failed",
                mimetype,
                exc_info=True,
            )
    if mimetype == "application/zip":
        try:
            if msoffice_mimetype := _get_ooxml_mimetype(bin_data):
                return msoffice_mimetype
        except zipfile.BadZipFile:
            pass
        except Exception:
            _logger_guess_mimetype.warning(
                "Sub-checker '_get_ooxml_mimetype' of type '%s' failed",
                mimetype,
                exc_info=True,
            )
    return mimetype


_extension_pattern = re.compile(r"\w+")


def get_extension(filename: str) -> str:
    _stem, dot, ext = filename.lstrip(".").rpartition(".")
    if not dot or not _extension_pattern.fullmatch(ext):
        return ""

    if len(ext) <= 4:
        return f".{ext}".lower()

    guessed_mimetype, _guessed_encoding = mimetypes.guess_type(filename)
    if guessed_mimetype:
        return mimetypes.guess_extension(guessed_mimetype) or f".{ext}".lower()

    return ""


def fix_filename_extension(filename: str, mimetype: str) -> str:
    extension_mimetype = mimetypes.guess_type(filename)[0]
    if extension_mimetype == mimetype:
        return filename

    extension = get_extension(filename)
    if mimetype in _olecf_mimetypes and extension in _old_ms_office_mimetypes:
        return filename

    if mimetype == "application/zip" and extension in {
        ".docx",
        ".xlsx",
        ".pptx",
    }:
        return filename

    if guessed_extension := mimetypes.guess_extension(mimetype):
        _debug.logic(
            "mimetype.extension_fixed",
            extension=extension or None,
            mimetype=mimetype,
            added=guessed_extension,
        )
        _logger.warning(
            "File %r has an invalid extension for mimetype %r, adding %r",
            filename,
            mimetype,
            guessed_extension,
        )
        return filename + guessed_extension

    _debug.logic(
        "mimetype.extension_unknown", extension=extension or None, mimetype=mimetype
    )
    _logger.warning(
        "File %r has an unknown extension for mimetype %r", filename, mimetype
    )
    return filename
