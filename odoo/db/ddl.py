import re as _re
from typing import Any

from psycopg import sql as _sql

from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


def iter_sql_code_ranges(query: str) -> list[tuple[int, int]]:
    ranges = []
    i, n = 0, len(query)
    start = 0
    while i < n:
        c = query[i]
        if c in ("'", '"'):
            if i > start:
                ranges.append((start, i))
            quote = c
            i += 1
            while i < n:
                if query[i] == quote:
                    if i + 1 < n and query[i + 1] == quote:
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            start = i
            continue
        if c == "-" and query[i : i + 2] == "--":
            if i > start:
                ranges.append((start, i))
            nl = query.find("\n", i)
            i = n if nl == -1 else nl
            start = i
            continue
        if c == "/" and query[i : i + 2] == "/*":
            if i > start:
                ranges.append((start, i))
            end_comment = query.find("*/", i + 2)
            i = n if end_comment == -1 else end_comment + 2
            start = i
            continue
        i += 1
    if start < n:
        ranges.append((start, n))
    return ranges


def get_value_marker_positions(query: str) -> list[int]:
    out = []
    for start, end in iter_sql_code_ranges(query):
        i = start
        while i < end - 1:
            if query[i] == "%":
                if query[i + 1] == "s":
                    out.append(i)
                i += 2
            else:
                i += 1
    return out


_DDL_KEYWORDS: tuple[str, ...] = (
    "CREATE",
    "ALTER",
    "DROP",
    "COMMENT",
    "GRANT",
    "REVOKE",
    "DO",
)
_COMMENT_PREFIXES: frozenset[str] = frozenset(("--", "/*"))

_RE_DDL = _re.compile(
    r"^\s*(?:(?:--[^\n]*\n|/\*.*?\*/)\s*)*"
    r"(" + "|".join(_DDL_KEYWORDS) + r")\b",
    _re.IGNORECASE | _re.DOTALL,
)
_DDL_PREFIXES: frozenset[str] = (
    frozenset(kw[:2] for kw in _DDL_KEYWORDS) | _COMMENT_PREFIXES
)

_SCHEMA_CHANGING_DDL: frozenset[str] = frozenset({"CREATE", "ALTER", "DROP", "DO"})


_RE_CREATE_SEQUENCE = _re.compile(
    r"^\s*(?:(?:--[^\n]*\n|/\*.*?\*/)\s*)*"
    r"CREATE\s+(?:(?:TEMP|TEMPORARY|UNLOGGED)\s+)?SEQUENCE\b",
    _re.IGNORECASE | _re.DOTALL,
)

_RE_ROLLBACK_TO_SAVEPOINT = _re.compile(
    r"^\s*(?:(?:--[^\n]*\n|/\*.*?\*/)\s*)*" r"ROLLBACK\s+TO\b",
    _re.IGNORECASE | _re.DOTALL,
)
_ROLLBACK_PREFIXES: frozenset[str] = frozenset(("RO",)) | _COMMENT_PREFIXES


def classify_statement(qs: str) -> tuple[str | None, bool]:
    head = qs[:64].lstrip()
    if len(head) < 3 and len(qs) > 64:
        head = qs.lstrip()
    c = head[:2].upper()
    if c in _DDL_PREFIXES:
        m = _RE_DDL.match(qs)
        if m is not None:
            return m.group(1).upper(), False
        if c in _COMMENT_PREFIXES:
            return None, _RE_ROLLBACK_TO_SAVEPOINT.match(qs) is not None
        return None, False
    if c == "SE":
        return ("SET", False) if head[2:3] in ("T", "t") else (None, False)
    if c in _ROLLBACK_PREFIXES:
        return None, _RE_ROLLBACK_TO_SAVEPOINT.match(qs) is not None
    return None, False


def _get_ddl_keyword(qs: str) -> str | None:
    return classify_statement(qs)[0]


def _is_schema_changing_statement(qs: str, leading: str | None) -> bool:
    if leading not in _SCHEMA_CHANGING_DDL:
        return False
    return leading != "CREATE" or _RE_CREATE_SEQUENCE.match(qs) is None


def _has_schema_changing_statement(qs: str, leading: str | None) -> bool:
    if _is_schema_changing_statement(qs, leading):
        return True
    if ";" not in qs:
        return False
    parts = qs.split(";")[1:]
    later = any(
        _is_schema_changing_statement(part, _get_ddl_keyword(part)) for part in parts
    )
    _debug.logic(
        "ddl.multi_statement_scanned",
        leading=leading,
        statements=len(parts) + 1,
        schema_changing_later=later,
    )
    return later


_DICT_MARKER_RE = _re.compile(r"%(?:%|\(([^)]+)\)s)")


def _is_within_code_ranges(start: int, end: int, ranges: list[tuple[int, int]]) -> bool:
    return any(r_start <= start and end <= r_end for r_start, r_end in ranges)


def _inline_ddl_params(qs: str, params: tuple | list | dict, ctx: Any) -> str:
    if isinstance(params, dict):
        code_ranges = iter_sql_code_ranges(qs)
        referenced = {
            m.group(1)
            for m in _DICT_MARKER_RE.finditer(qs)
            if m.group(1) is not None
            and _is_within_code_ranges(m.start(), m.end(), code_ranges)
        }
        missing = referenced - params.keys()
        if missing:
            _debug.logic(
                "ddl.params_refused",
                mode="named",
                referenced=len(referenced),
                missing=len(missing),
            )
            raise ValueError(
                "DDL parameter mismatch: marker(s) "
                + ", ".join(f"%({n})s" for n in sorted(missing))
                + f" have no matching key in params {sorted(params)}"
            )

        def _replace_named_marker(m: _re.Match) -> str:
            name = m.group(1)
            if name is None:
                return "%"
            if not _is_within_code_ranges(m.start(), m.end(), code_ranges):
                return m.group(0)
            return _sql.quote(params[name], ctx)

        _debug.logic("ddl.params_inlined", mode="named", referenced=len(referenced))
        return _DICT_MARKER_RE.sub(_replace_named_marker, qs)
    markers = get_value_marker_positions(qs)
    if len(markers) != len(params):
        _debug.logic(
            "ddl.params_refused",
            mode="positional",
            markers=len(markers),
            params=len(params),
        )
        raise ValueError(
            f"DDL parameter count mismatch: {len(markers)} '%s' "
            f"marker(s) but {len(params)} param(s)"
        )
    out, prev = [], 0
    for pos, value in zip(markers, params, strict=True):
        out.append(qs[prev:pos].replace("%%", "%"))
        out.append(_sql.quote(value, ctx))
        prev = pos + 2
    out.append(qs[prev:].replace("%%", "%"))
    _debug.logic("ddl.params_inlined", mode="positional", markers=len(markers))
    return "".join(out)
