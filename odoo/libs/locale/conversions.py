import re

import babel

__all__ = [
    "posix_to_ldml",
    "py_to_js_locale",
]


_XPG_LOCALE_RE = re.compile(
    r"""^
    ([a-z]+)      # language
    (_[A-Z\d]+)?  # maybe _territory
    # no support for .codeset (we don't use that in Odoo)
    (@.+)?        # maybe @modifier
    $""",
    re.VERBOSE,
)


def py_to_js_locale(locale: str) -> str:
    match_ = _XPG_LOCALE_RE.match(locale)
    if not match_:
        return locale
    language, territory, modifier = match_.groups()
    subtags = [language]
    if modifier == "@Cyrl":
        subtags.append("Cyrl")
    elif modifier == "@latin":
        subtags.append("Latn")
    if territory:
        subtags.append(territory.removeprefix("_"))
    return "-".join(subtags)


_POSIX_TO_LDML = {
    "a": "E",
    "A": "EEEE",
    "b": "MMM",
    "B": "MMMM",
    "d": "dd",
    "-d": "d",
    "e": "d",
    "H": "HH",
    "I": "hh",
    "j": "DDD",
    "m": "MM",
    "-m": "M",
    "M": "mm",
    "p": "a",
    "S": "ss",
    "U": "w",
    "w": "e",
    "W": "w",
    "y": "yy",
    "Y": "yyyy",
}


def _quote_ldml_literal(text: str) -> str:
    escaped = text.replace("'", "''")
    return escaped if text and not text.strip("'") else f"'{escaped}'"


def posix_to_ldml(fmt: str, locale: babel.Locale) -> str:
    buf: list[str] = []
    pc = False
    minus = False
    quoted: list[str] = []

    for c in fmt:
        if not pc and (c.isalpha() or c == "'"):
            quoted.append(c)
            continue
        if quoted:
            buf.append(_quote_ldml_literal("".join(quoted)))
            quoted = []

        if pc:
            if c == "-":
                minus = True
                continue
            directive = f"-{c}" if minus else c
            minus = False
            pc = False
            if c == "%":
                buf.append("%")
            elif c == "x":
                buf.append(locale.date_formats["short"].pattern)
            elif c == "X":
                buf.append(locale.time_formats["medium"].pattern)
            elif (ldml := _POSIX_TO_LDML.get(directive)) is not None:
                buf.append(ldml)
            else:
                raise ValueError(
                    f"Unsupported strftime directive '%{directive}' in {fmt!r}"
                )
        elif c == "%":
            pc = True
        else:
            buf.append(c)

    if quoted:
        buf.append(_quote_ldml_literal("".join(quoted)))

    if pc:
        buf.append("%")

    return "".join(buf)
