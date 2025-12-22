# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import contextlib
import warnings

LOG_NOTSET = 'notset'
LOG_DEBUG = 'debug'
LOG_INFO = 'info'
LOG_WARNING = 'warn'
LOG_ERROR = 'error'
LOG_CRITICAL = 'critical'

# TODO get_encodings, ustr and exception_to_unicode were originally from tools.misc.
# There are here until we refactor tools so that this module doesn't depends on tools.

def get_encodings(hint_encoding='utf-8'):
    warnings.warn(
        "Deprecated since Odoo 18. Mostly nonsensical as the "
        "second/third encoding it yields is latin-1 which always succeeds...",
        stacklevel=2,
        category=DeprecationWarning,
    )
    fallbacks = {
        'latin1': 'latin9',
        'iso-8859-1': 'iso8859-15',
        'iso-8859-8-i': 'iso8859-8',
        'cp1252': '1252',
    }
    if hint_encoding:
        yield hint_encoding
        if hint_encoding.lower() in fallbacks:
            yield fallbacks[hint_encoding.lower()]

    # some defaults (also taking care of pure ASCII)
    for charset in ['utf8','latin1']:
        if not hint_encoding or (charset.lower() != hint_encoding.lower()):
            yield charset

    from locale import getpreferredencoding
    prefenc = getpreferredencoding()
    if prefenc and prefenc.lower() != 'utf-8':
        yield prefenc
        prefenc = fallbacks.get(prefenc.lower())
        if prefenc:
            yield prefenc

def ustr(value, hint_encoding='utf-8', errors='strict'):
    """This method is similar to the builtin `unicode`, except
    that it may try multiple encodings to find one that works
    for decoding `value`, and defaults to 'utf-8' first.

    :param value: the value to convert
    :param hint_encoding: an optional encoding that was detected
        upstream and should be tried first to decode ``value``.
    :param str errors: optional `errors` flag to pass to the unicode
        built-in to indicate how illegal character values should be
        treated when converting a string: 'strict', 'ignore' or 'replace'
        (see ``unicode()`` constructor).
        Passing anything other than 'strict' means that the first
        encoding tried will be used, even if it's not the correct
        one to use, so be careful! Ignored if value is not a string/unicode.
    :raise: UnicodeError if value cannot be coerced to unicode
    :return: unicode string representing the given value
    """
    warnings.warn(
        "Deprecated since Odoo 18: ustr() is a garbage bag of weirdo fallbacks "
        "which mostly don't do anything as\n"
        "- the first attempt will always work if errors is not `strict`\n"
        "- if utf8 fails it moves on to latin-1 which always works\n"
        "- and it always tries hint-encoding twice",
        stacklevel=2,
        category=DeprecationWarning,
    )
    # We use direct type comparison instead of `isinstance`
    # as much as possible, in order to make the most common
    # cases faster (isinstance/issubclass are significantly slower)
    ttype = type(value)

    if ttype is str:
        return value

    # special short-circuit for str, as we still needs to support
    # str subclasses such as `odoo.tools.unquote`
    if ttype is bytes or issubclass(ttype, bytes):

        # try hint_encoding first, avoids call to get_encoding()
        # for the most common case
        with contextlib.suppress(Exception):
            return value.decode(hint_encoding, errors=errors)

        # rare: no luck with hint_encoding, attempt other ones
        for ln in get_encodings(hint_encoding):
            with contextlib.suppress(Exception):
                return value.decode(ln, errors=errors)

    if isinstance(value, Exception):
        return exception_to_unicode(value)

    # fallback for non-string values
    try:
        return str(value)
    except Exception as e:
        raise UnicodeError(f'unable to convert {value!r}') from e


def exception_to_unicode(e):
    if getattr(e, 'args', ()):
        return "\n".join(map(str, e.args))
    try:
        return str(e)
    except Exception:
        return "Unknown message"
