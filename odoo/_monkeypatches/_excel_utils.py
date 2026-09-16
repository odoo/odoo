import re
from collections.abc import Iterable
from typing import Final

_INVALID_EXCEL_CHARS_RE: Final[re.Pattern[str]] = re.compile(r"[\[\]:*?/\\]")
_MAX_SHEET_NAME_LENGTH: Final[int] = 31
_MAX_DEDUP_SUFFIX: Final[int] = 1000


class SheetNameCollisionError(ValueError):
    pass


def normalize_excel_sheet_name(name: str, taken: Iterable[str] = ()) -> str:
    if not name:
        return name
    name = _INVALID_EXCEL_CHARS_RE.sub("", name).strip().strip("'").strip()
    name = name[:_MAX_SHEET_NAME_LENGTH].rstrip().rstrip("'").rstrip()
    if not name:
        return name

    lowered = {existing.lower() for existing in taken}
    if name.lower() not in lowered:
        return name

    for suffix_n in range(2, _MAX_DEDUP_SUFFIX):
        suffix = f"~{suffix_n}"
        stem = name[: _MAX_SHEET_NAME_LENGTH - len(suffix)].rstrip("'")
        candidate = f"{stem}{suffix}"
        if candidate.lower() not in lowered:
            return candidate
    msg = (
        f"cannot fit a unique worksheet name for {name!r}: every ~2..~"
        f"{_MAX_DEDUP_SUFFIX - 1} variant is taken"
    )
    raise SheetNameCollisionError(msg)
