# coding: utf-8

"""
Functions to convert unicode IRIs into ASCII byte string URIs and back. Exports
the following items:

 - iri_to_uri()
 - uri_to_iri()
"""

from __future__ import unicode_literals, division, absolute_import, print_function

from encodings import idna  # noqa
import codecs
import re
import sys

from ._errors import unwrap
from ._types import byte_cls, str_cls, type_name, bytes_to_list, int_types

if sys.version_info < (3,):
    from urlparse import urlsplit, urlunsplit
    from urllib import (
        quote as urlquote,
        unquote as unquote_to_bytes,
    )

else:
    from urllib.parse import (
        quote as urlquote,
        unquote_to_bytes,
        urlsplit,
        urlunsplit,
    )


def iri_to_uri(value, normalize=False):
    """
    Encodes a unicode IRI into an ASCII byte string URI

    :param value:
        A unicode string of an IRI

    :param normalize:
        A bool that controls URI normalization

    :return:
        A byte string of the ASCII-encoded URI
    """

    if not isinstance(value, str_cls):
        raise TypeError(unwrap(
            '''
            value must be a unicode string, not %s
            ''',
            type_name(value)
        ))

    scheme = None
    # Python 2.6 doesn't split properly is the URL doesn't start with http:// or https://
    if sys.version_info < (2, 7) and not value.startswith('http://') and not value.startswith('https://'):
        real_prefix = None
        prefix_match = re.match('^[^:]*://', value)
        if prefix_match:
            real_prefix = prefix_match.group(0)
            value = 'http://' + value[len(real_prefix):]
        parsed = urlsplit(value)
        if real_prefix:
            value = real_prefix + value[7:]
            scheme = _urlquote(real_prefix[:-3])
    else:
        parsed = urlsplit(value)

    if scheme is None:
        scheme = _urlquote(parsed.scheme)
    hostname = parsed.hostname
    if hostname is not None:
        hostname = hostname.encode('idna')
    # RFC 3986 allows userinfo to contain sub-delims
    username = _urlquote(parsed.username, safe='!$&\'()*+,;=')
    password = _urlquote(parsed.password, safe='!$&\'()*+,;=')
    port = parsed.port
    if port is not None:
        port = str_cls(port).encode('ascii')

    netloc = b''
    if username is not None:
        netloc += username
        if password:
            netloc += b':' + password
        netloc += b'@'
    if hostname is not None:
        netloc += hostname
    if port is not None:
        default_http = scheme == b'http' and port == b'80'
        default_https = scheme == b'https' and port == b'443'
        if not normalize or (not default_http and not default_https):
            netloc += b':' + port

    # RFC 3986 allows a path to contain sub-delims, plus "@" and ":"
    path = _urlquote(parsed.path, safe='/!$&\'()*+,;=@:')
    # RFC 3986 allows the query to contain sub-delims, plus "@", ":" , "/" and "?"
    query = _urlquote(parsed.query, safe='/?!$&\'()*+,;=@:')
    # RFC 3986 allows the fragment to contain sub-delims, plus "@", ":" , "/" and "?"
    fragment = _urlquote(parsed.fragment, safe='/?!$&\'()*+,;=@:')

    if normalize and query is None and fragment is None and path == b'/':
        path = None

    # Python 2.7 compat
    if path is None:
        path = ''

    output = urlunsplit((scheme, netloc, path, query, fragment))
    if isinstance(output, str_cls):
        output = output.encode('latin1')
    return output


def uri_to_iri(value):
    """
    Converts an ASCII URI byte string into a unicode IRI

    :param value:
        An ASCII-encoded byte string of the URI

    :return:
        A unicode string of the IRI
    """

    if not isinstance(value, byte_cls):
        raise TypeError(unwrap(
            '''
            value must be a byte string, not %s
            ''',
            type_name(value)
        ))

    parsed = urlsplit(value)

    scheme = parsed.scheme
    if scheme is not None:
        scheme = scheme.decode('ascii')

    username = _urlunquote(parsed.username, remap=[':', '@'])
    password = _urlunquote(parsed.password, remap=[':', '@'])
    hostname = parsed.hostname
    if hostname:
        hostname = hostname.decode('idna')
    port = parsed.port
    if port and not isinstance(port, int_types):
        port = port.decode('ascii')

    netloc = ''
    if username is not None:
        netloc += username
        if password:
            netloc += ':' + password
        netloc += '@'
    if hostname is not None:
        netloc += hostname
    if port is not None:
        netloc += ':' + str_cls(port)

    path = _urlunquote(parsed.path, remap=['/'], preserve=True)
    query = _urlunquote(parsed.query, remap=['&', '='], preserve=True)
    fragment = _urlunquote(parsed.fragment)

    return urlunsplit((scheme, netloc, path, query, fragment))


def _iri_utf8_errors_handler(exc):
    """
    Error handler for decoding UTF-8 parts of a URI into an IRI. Leaves byte
    sequences encoded in %XX format, but as part of a unicode string.

    :param exc:
        The UnicodeDecodeError exception

    :return:
        A 2-element tuple of (replacement unicode string, integer index to
        resume at)
    """

    bytes_as_ints = bytes_to_list(exc.object[exc.start:exc.end])
    replacements = ['%%%02x' % num for num in bytes_as_ints]
    return (''.join(replacements), exc.end)


codecs.register_error('iriutf8', _iri_utf8_errors_handler)


def _urlquote(string, safe=''):
    """
    Quotes a unicode string for use in a URL

    :param string:
        A unicode string

    :param safe:
        A unicode string of character to not encode

    :return:
        None (if string is None) or an ASCII byte string of the quoted string
    """

    if string is None or string == '':
        return None

    # Anything already hex quoted is pulled out of the URL and unquoted if
    # possible
    escapes = []
    if re.search('%[0-9a-fA-F]{2}', string):
        # Try to unquote any percent values, restoring them if they are not
        # valid UTF-8. Also, requote any safe chars since encoded versions of
        # those are functionally different than the unquoted ones.
        def _try_unescape(match):
            byte_string = unquote_to_bytes(match.group(0))
            unicode_string = byte_string.decode('utf-8', 'iriutf8')
            for safe_char in list(safe):
                unicode_string = unicode_string.replace(safe_char, '%%%02x' % ord(safe_char))
            return unicode_string
        string = re.sub('(?:%[0-9a-fA-F]{2})+', _try_unescape, string)

        # Once we have the minimal set of hex quoted values, removed them from
        # the string so that they are not double quoted
        def _extract_escape(match):
            escapes.append(match.group(0).encode('ascii'))
            return '\x00'
        string = re.sub('%[0-9a-fA-F]{2}', _extract_escape, string)

    output = urlquote(string.encode('utf-8'), safe=safe.encode('utf-8'))
    if not isinstance(output, byte_cls):
        output = output.encode('ascii')

    # Restore the existing quoted values that we extracted
    if len(escapes) > 0:
        def _return_escape(_):
            return escapes.pop(0)
        output = re.sub(b'%00', _return_escape, output)

    return output


def _urlunquote(byte_string, remap=None, preserve=None):
    """
    Unquotes a URI portion from a byte string into unicode using UTF-8

    :param byte_string:
        A byte string of the data to unquote

    :param remap:
        A list of characters (as unicode) that should be re-mapped to a
        %XX encoding. This is used when characters are not valid in part of a
        URL.

    :param preserve:
        A bool - indicates that the chars to be remapped if they occur in
        non-hex form, should be preserved. E.g. / for URL path.

    :return:
        A unicode string
    """

    if byte_string is None:
        return byte_string

    if byte_string == b'':
        return ''

    if preserve:
        replacements = ['\x1A', '\x1C', '\x1D', '\x1E', '\x1F']
        preserve_unmap = {}
        for char in remap:
            replacement = replacements.pop(0)
            preserve_unmap[replacement] = char
            byte_string = byte_string.replace(char.encode('ascii'), replacement.encode('ascii'))

    byte_string = unquote_to_bytes(byte_string)

    if remap:
        for char in remap:
            byte_string = byte_string.replace(char.encode('ascii'), ('%%%02x' % ord(char)).encode('ascii'))

    output = byte_string.decode('utf-8', 'iriutf8')

    if preserve:
        for replacement, original in preserve_unmap.items():
            output = output.replace(replacement, original)

    return output
