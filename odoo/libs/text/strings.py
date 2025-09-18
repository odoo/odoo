"""String manipulation utilities.

Pure Python text helpers with no Odoo dependencies.
"""

__all__ = ["get_flag", "human_size", "mod10r", "remove_accents", "str2bool"]

import typing
import unicodedata


def remove_accents(input_str: str) -> str:
    """Replace accented latin letters by an ASCII equivalent.

    Suboptimal-but-better-than-nothing way to replace accented
    latin letters by an ASCII equivalent. Will obviously change the
    meaning of input_str and work only for some cases.

    :param input_str: String with potential accented characters
    :returns: String with accents removed
    """
    if not input_str:
        return input_str
    nkfd_form = unicodedata.normalize("NFKD", input_str)
    return "".join(c for c in nkfd_form if not unicodedata.combining(c))


def human_size(sz: float | str) -> str | typing.Literal[False]:
    """Return the size in a human readable format.

    :param sz: Size in bytes (can be int, float, or string)
    :returns: Human readable size string like "1.23 Mb", or False if sz is falsy
    """
    if not sz:
        return False
    units = ("bytes", "Kb", "Mb", "Gb", "Tb")
    if isinstance(sz, str):
        sz = len(sz)
    s, i = float(sz), 0
    while s >= 1024 and i < len(units) - 1:
        s /= 1024
        i += 1
    return f"{s:0.2f} {units[i]}"


def str2bool(s: str, default: bool | None = None) -> bool:
    """Convert a string to a boolean value.

    Accepts common boolean string representations:
    - True: 'y', 'yes', '1', 'true', 't', 'on'
    - False: 'n', 'no', '0', 'false', 'f', 'off'

    :param s: String to convert
    :param default: Default value if string is not recognized
    :returns: Boolean value
    :raises ValueError: If string is not recognized and no default provided

    Example::

        >>> str2bool('yes')
        True
        >>> str2bool('0')
        False
        >>> str2bool('maybe', default=False)
        False
    """
    import warnings

    # allow this (for now?) because it's used for get_param
    if type(s) is bool:
        return s  # type: ignore

    if not isinstance(s, str):
        warnings.warn(
            f"Passed a non-str to `str2bool`: {s}",
            DeprecationWarning,
            stacklevel=2,
        )
        if default is None:
            raise ValueError("Use 0/1/yes/no/true/false/on/off")
        return bool(default)

    s = s.lower()
    if s in ("y", "yes", "1", "true", "t", "on"):
        return True
    if s in ("n", "no", "0", "false", "f", "off"):
        return False
    if default is None:
        raise ValueError("Use 0/1/yes/no/true/false/on/off")
    return bool(default)


def mod10r(number: str) -> str:
    """Compute the recursive mod10 check digit for a number.

    Used for Swiss payment slips (BVR/ESR) and similar applications.

    :param number: Account or invoice number
    :returns: The same number completed with the recursive mod10 key

    Example::

        >>> mod10r('123456')
        '1234566'
    """
    codec = [0, 9, 4, 6, 8, 2, 7, 1, 3, 5]
    report = 0
    result = ""
    for digit in number:
        result += digit
        if digit.isdigit():
            report = codec[(int(digit) + report) % 10]
    return result + str((10 - report) % 10)


def get_flag(country_code: str) -> str:
    """Get the emoji representing the flag linked to the country code.

    This emoji is composed of the two regional indicator emoji of the country code.

    :param country_code: Two-letter country code (e.g., 'US', 'MX', 'FR')
    :returns: The flag emoji for the given country

    Example::

        >>> get_flag('US')
        '🇺🇸'
        >>> get_flag('MX')
        '🇲🇽'
    """
    return "".join(chr(int(f"1f1{ord(c)+165:02x}", base=16)) for c in country_code)
