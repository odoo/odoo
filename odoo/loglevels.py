# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import sys

LOG_NOTSET = 'notset'
LOG_DEBUG = 'debug'
LOG_INFO = 'info'
LOG_WARNING = 'warn'
LOG_ERROR = 'error'
LOG_CRITICAL = 'critical'

# TODO get_encodings, ustr and exception_to_unicode were originally from tools.misc.
# There are here until we refactor tools so that this module doesn't depends on tools.

def get_encodings(hint_encoding='utf-8'):
    fallbacks = {
        'latin1': 'latin9',
        'iso-8859-1': 'iso8859-15',
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

    :param: value: the value to convert
    :param: hint_encoding: an optional encoding that was detecte
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
    # We use direct type comparison instead of `isinstance`
    # as much as possible, in order to make the most common
    # cases faster (isinstance/issubclass are significantly slower)
    ttype = type(value)

    if ttype is unicode:
        return value

    # special short-circuit for str, as we still needs to support
    # str subclasses such as `odoo.tools.unquote`
    if ttype is str or issubclass(ttype, str):

        # try hint_encoding first, avoids call to get_encoding()
        # for the most common case
        try:
            return unicode(value, hint_encoding, errors=errors)
        except Exception:
            pass

        # rare: no luck with hint_encoding, attempt other ones
        for ln in get_encodings(hint_encoding):
            try:
                return unicode(value, ln, errors=errors)
            except Exception:
                pass

    if isinstance(value, Exception):
        return exception_to_unicode(value)

    # fallback for non-string values
    try:
        return unicode(value)
    except Exception:
        raise UnicodeError('unable to convert %r' % (value,))


def exception_to_unicode(e):
    if hasattr(e, 'args'):
        return "\n".join((ustr(a) for a in e.args))
    try:
        return unicode(e)
    except Exception:
        return u"Unknown message"
