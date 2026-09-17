from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class UserFolder:
    MY = "MY"
    COMPANY = "COMPANY"
    SHARED = "SHARED"
    RECENT = "RECENT"
    TRASH = "TRASH"
    FOLDER = "FOLDER"

    WRITABLE_ROOTS = frozenset({MY, COMPANY})
    VIRTUAL_ROOTS = frozenset({MY, COMPANY, SHARED, RECENT, TRASH})

    __slots__ = ("folder_id", "kind")

    def __init__(self, kind: str, folder_id: int | None = None) -> None:
        self.kind = kind
        self.folder_id = folder_id

    @classmethod
    def parse(cls, value: object) -> UserFolder | None:
        if value is None or value is False or value == "":
            return None
        if isinstance(value, bool):
            _debug.logic("user_folder_parse_failed", reason="bool")
            raise ValueError(f"Unexpected user_folder_id value {value!r}")
        if isinstance(value, int):
            return cls(cls.FOLDER, value)
        if not isinstance(value, str):
            _debug.logic(
                "user_folder_parse_failed", reason="type", type=type(value).__name__
            )
            raise ValueError(f"Unexpected user_folder_id value {value!r}")
        if value in cls.VIRTUAL_ROOTS:
            return cls(value)
        if value.isnumeric():
            return cls(cls.FOLDER, int(value))
        _debug.logic("user_folder_parse_failed", reason="unknown", value=value)
        raise ValueError(f"Unknown searched value {value}")

    @property
    def is_folder(self) -> bool:
        return self.kind == self.FOLDER

    @property
    def is_writable_root(self) -> bool:
        return self.kind in self.WRITABLE_ROOTS

    def __str__(self) -> str:
        return str(self.folder_id) if self.is_folder else self.kind

    def __repr__(self) -> str:
        return f"UserFolder({self!s})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, UserFolder):
            return (self.kind, self.folder_id) == (other.kind, other.folder_id)
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.kind, self.folder_id))


INLINE_RENDERED_MIMETYPES = frozenset(
    {
        "application/javascript",
        "application/json",
        "text/css",
        "text/html",
        "text/plain",
        "image/bmp",
        "image/gif",
        "image/jpeg",
        "image/png",
        "image/svg+xml",
        "image/tiff",
        "image/webp",
        "image/x-icon",
        "audio/aac",
        "audio/flac",
        "audio/mp4",
        "audio/mpeg",
        "audio/ogg",
        "audio/opus",
        "audio/wav",
        "audio/webm",
        "audio/x-m4a",
        "audio/x-wav",
        "video/mp4",
        "video/ogg",
        "video/quicktime",
        "video/webm",
        "video/x-matroska",
    }
)


def is_mimetype_inline_rendered(mimetype: str) -> bool:
    mimetype = (mimetype or "").split(";")[0].strip().lower()
    return mimetype.startswith("application/pdf") or (
        mimetype in INLINE_RENDERED_MIMETYPES
    )


def is_mimetype_textual(mimetype: str) -> bool:
    maintype, _, subtype = (mimetype or "").partition("/")
    return maintype == "text" or (
        maintype == "application" and subtype in {"documents-email", "json", "xml"}
    )
