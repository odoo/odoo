from __future__ import annotations

import ast
import functools
import re
from collections.abc import Sequence
from typing import Any, Protocol

__all__ = [
    "LocaleConventions",
    "format_number",
    "intersperse",
]


class LocaleConventions(Protocol):
    @property
    def decimal_point(self) -> str: ...

    @property
    def grouping(self) -> str: ...

    @property
    def thousands_sep(self) -> str: ...


@functools.lru_cache(maxsize=128)
def _parse_grouping(grouping: str) -> tuple[int, ...]:
    # a language stores its grouping as a Python literal: "[3,0]", or "3"
    try:
        value = ast.literal_eval(grouping)
    except SyntaxError, ValueError:
        value = None
    if isinstance(value, int) and not isinstance(value, bool):
        return (value,)
    if isinstance(value, list | tuple) and all(
        isinstance(count, int) and not isinstance(count, bool) for count in value
    ):
        return tuple(value)
    msg = f"a grouping is a list of digit counts such as [3,0], got {grouping!r}"
    raise ValueError(msg)


def _split(l: str, counts: Sequence[int]) -> list[str]:
    res = []
    saved_count = len(l)
    for count in counts:
        if not l:
            break
        if count == -1:
            break
        if count == 0:
            while l:
                res.append(l[:saved_count])
                l = l[saved_count:]
            break
        res.append(l[:count])
        l = l[count:]
        saved_count = count
    if l:
        res.append(l)
    return res


intersperse_pat = re.compile(r"([^0-9]*)([^ ]*)(.*)")


def intersperse(
    string: str, counts: Sequence[int], separator: str = ""
) -> tuple[str, int]:
    matched = intersperse_pat.match(string)
    assert matched is not None, f"intersperse_pat failed on {string!r}"
    left, rest, right = matched.groups()

    def reverse(s: str) -> str:
        return s[::-1]

    splits = _split(reverse(rest), counts)
    res = separator.join(reverse(s) for s in reversed(splits))
    return left + res + right, max(len(splits) - 1, 0)


_FLOATING = frozenset("eEfFgG")
_INTEGRAL = frozenset("diu")

_CONVERSION_RE = re.compile(
    r"%(?:%|[-+ #0']*(?:\d+|\*)?(?:\.(?:\d+|\*))?[hlL]?([diouxXeEfFgGcrsab]))"
)


def _get_conversion_match(spec: str) -> re.Match[str] | None:
    return next(
        (match for match in _CONVERSION_RE.finditer(spec) if match[1] is not None),
        None,
    )


def format_number(
    spec: str,
    value: Any,
    lang_data: LocaleConventions,
    grouping: bool = False,
) -> str:
    if not spec or spec[0] != "%":
        raise ValueError(
            "format_number() must be given exactly one %char format specifier"
        )

    formatted = spec % value
    match = _get_conversion_match(spec)
    if match is None:
        return formatted
    conversion = match[1]

    head = spec[: match.start()] % ()
    tail = spec[match.end() :] % ()
    number = formatted[len(head) : len(formatted) - len(tail) or None]

    decimal_point = lang_data.decimal_point
    if grouping:
        lang_grouping, thousands_sep = (
            lang_data.grouping,
            lang_data.thousands_sep or "",
        )
        eval_lang_grouping = _parse_grouping(lang_grouping)

        if conversion in _FLOATING:
            parts = number.split(".")
            scientific = conversion in "eE" or (
                conversion in "gG" and ("e" in number or "E" in number)
            )
            if not scientific:
                parts[0] = intersperse(parts[0], eval_lang_grouping, thousands_sep)[0]

            number = decimal_point.join(parts)

        elif conversion in _INTEGRAL:
            number = intersperse(number, eval_lang_grouping, thousands_sep)[0]

    elif conversion in _FLOATING and "." in number:
        number = number.replace(".", decimal_point)

    return head + number + tail
