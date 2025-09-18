"""Locale format conversion utilities.

Pure Python locale helpers with no Odoo dependencies.
"""

import re

import babel

# Regex for parsing XPG (POSIX) locale format
# XPG syntax: language[_territory][.codeset][@modifier]
# https://www.gnu.org/software/libc/manual/html_node/Locale-Names.html
XPG_LOCALE_RE = re.compile(
    r"""^
    ([a-z]+)      # language
    (_[A-Z\d]+)?  # maybe _territory
    # no support for .codeset (we don't use that in Odoo)
    (@.+)?        # maybe @modifier
    $""",
    re.VERBOSE,
)


def py_to_js_locale(locale: str) -> str:
    """Convert a locale from Python (XPG) to JavaScript (BCP 47) format.

    Most of the time the conversion is simply to replace _ with -.
    Example: fr_BE -> fr-BE

    Exception: Serbian can be written in both Latin and Cyrillic scripts
    interchangeably, therefore its locale includes a special modifier
    to indicate which script to use.
    Example: sr@latin -> sr-Latn

    BCP 47 (JS):
        language[-extlang][-script][-region][-variant][-extension][-privateuse]
        https://www.ietf.org/rfc/rfc5646.txt
    XPG syntax (Python):
        language[_territory][.codeset][@modifier]
        https://www.gnu.org/software/libc/manual/html_node/Locale-Names.html

    :param locale: The locale formatted for use on the Python-side.
    :return: The locale formatted for use on the JavaScript-side.
    """
    match_ = XPG_LOCALE_RE.match(locale)
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


# Mapping from POSIX strftime format codes to LDML (Unicode) date format patterns
# Used by posix_to_ldml() to convert date format strings
POSIX_TO_LDML = {
    "a": "E",
    "A": "EEEE",
    "b": "MMM",
    "B": "MMMM",
    #'c': '',
    "d": "dd",
    "-d": "d",
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
    # Timezone handling is problematic, see comments in original code
    #'z': 'Z',
    #'Z': 'z',
}


def posix_to_ldml(fmt: str, locale: babel.Locale) -> str:
    """Convert a POSIX/strftime pattern into an LDML date format pattern.

    LDML (Locale Data Markup Language) is the Unicode standard for locale data,
    used by libraries like Babel and ICU. This function converts C-style strftime
    format strings to LDML patterns.

    :param fmt: non-extended C89/C90 strftime pattern
    :param locale: babel locale used for locale-specific conversions (e.g. %x and %X)
    :return: LDML date format pattern

    Example::

        >>> from babel import Locale
        >>> posix_to_ldml('%Y-%m-%d', Locale.parse('en_US'))
        'yyyy-MM-dd'
    """
    buf = []
    pc = False
    minus = False
    quoted = []

    for c in fmt:
        # LDML date format patterns uses letters, so letters must be quoted
        if not pc and c.isalpha():
            quoted.append(c if c != "'" else "''")
            continue
        if quoted:
            buf.extend(("'", "".join(quoted), "'"))
            quoted = []

        if pc:
            if c == "%":  # escaped percent
                buf.append("%")
            elif c == "x":  # date format, short seems to match
                buf.append(locale.date_formats["short"].pattern)
            elif c == "X":  # time format, seems to include seconds. short does not
                buf.append(locale.time_formats["medium"].pattern)
            elif c == "-":
                minus = True
                continue
            else:  # look up format char in static mapping
                if minus:
                    c = "-" + c
                    minus = False
                buf.append(POSIX_TO_LDML[c])
            pc = False
        elif c == "%":
            pc = True
        else:
            buf.append(c)

    # flush anything remaining in quoted buffer
    if quoted:
        buf.extend(("'", "".join(quoted), "'"))

    return "".join(buf)
