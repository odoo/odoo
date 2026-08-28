import re
import urllib.parse

# IDNA2008. Beware of the standard library ``str.encode('idna')``: it is
# IDNA2003 and encodes e.g. ``faß.de`` to ``fass.de``, not ``xn--fa-hia.de``.
import idna
from urllib3.util import parse_url

__all__ = ['idna_encode', 'urljoin']


def _contains_dot_segments(path: str | bytes) -> bool:
    # most servers decode url before doing dot segment resolutions
    decoded_path = urllib.parse.unquote(path, errors='strict')
    return any(seg in ('.', '..') for seg in decoded_path.split('/'))


def idna_encode(url: str, with_port: bool = True) -> str:
    """
    Encode the host of ``url`` in the ASCII (punycode) form that is
    actually sent over DNS, using IDNA2008. Everything but the host and,
    optionally, the port is dropped.

    Encoding every domain the same way is what makes a Unicode domain and
    its punycode equivalent match each other.

    :param str url: An URL (``https://exämple.com/path``), a netloc
        (``exämple.com:443``) or a bare host name.
    :param bool with_port: Whether the port is kept in the returned value.
    :returns: The encoded ``host`` or ``host:port``.
    :raises ValueError: When there is no host at all or when it is not a
        valid domain name.

    Examples::

        >>> idna_encode('https://faß.de/hello')
        'xn--fa-hia.de'
        >>> idna_encode('https://faß.de:8069/hello')
        'xn--fa-hia.de:8069'
        >>> idna_encode('https://faß.de:8069/hello', with_port=False)
        'xn--fa-hia.de'
        >>> idna_encode('dü sseldorf.com')
        Traceback (most recent call last):
        ...
        urllib3.exceptions.LocationParseError: Failed to parse: //dü sseldorf.com
    """
    if not url:
        raise ValueError("The URL has no host")
    parsed = parse_url(url if '://' in url else f'//{url}')
    host = parsed.host
    if not host:
        raise ValueError("The URL has no host")
    # an IPv6 literal has nothing to encode
    if not host.startswith('['):
        # ``parse_url`` only encodes the hosts that are not ASCII already,
        # encoding again validates the ASCII ones too: a bogus ``xn--``
        # label, an underscore or an over-long label are rejected here.
        host = idna.encode(host, uts46=True).decode('ascii')
    if with_port and parsed.port:
        return f'{host}:{parsed.port}'
    return host


def urljoin(base: str, extra: str) -> str:
    """Join a trusted base URL with a relative URL safely.

    Unlike standard URL joins that follow RFC 3986 (e.g., `urllib.parse.urljoin`),
    this function enforces strict behavior that better aligns with developer
    expectations and guards against path traversals, unplanned redirects, and
    accidental host/scheme overrides.

    - Behaves similarly to `base + '/' + extra`
    - Keeps scheme and netloc from `base`, and raises an error if `extra` has them
    - Ignores any scheme/host in `extra`
    - Forbids `.` and `..` path traversal
    - merges path/query/fragment

    :param base: Trusted base URL or path.
    :type base: str
    :param extra: Relative URL (`path`, `?query`, `#frag`). No scheme & host allowed unless it matches `base`
    :type extra: str
    :returns: joined URL.
    :rtype: str
    :raises AssertionError: If inputs are not strings.
    :raises ValueError: `extra` contains dot-segments or is absolute URLs.

    Examples::

        >>> urljoin('https://api.example.com/v1/?bar=fiz', '/users/42?bar=bob')
        'https://api.example.com/v1/users/42?bar=bob'

        >>> urljoin('https://example.com/foo', 'http://8.8.8.8/foo')
        Traceback (most recent call last):
            ...
        ValueError: Extra URL must use same scheme and host as base, and begin with base path

        >>> urljoin('https://api.example.com/data/', '/?lang=fr')
        'https://api.example.com/data/?lang=fr'
    """
    assert isinstance(base, str), "Base URL must be a string"
    assert isinstance(extra, str), "Extra URL must be a string"

    b_scheme, b_netloc, path, _, _ = urllib.parse.urlsplit(base)
    e_scheme, e_netloc, e_path, e_query, e_fragment = urllib.parse.urlsplit(extra)

    if e_scheme or e_netloc:
        # allow absolute extra URL if it matches base
        if (e_scheme != b_scheme) or (e_netloc != b_netloc) or not e_path.startswith(path):
            raise ValueError("Extra URL must use same scheme and host as base, and begin with base path")

        e_path = e_path[len(path):]

    if e_path:
        # prevent urljoin("/", "\\example.com/") to resolve as absolute to "//example.com/" in a browser redirect
        # https://github.com/mozilla-firefox/firefox/blob/5e81b64f4ed88b610eb332e103744d68ee8b6c0d/netwerk/base/nsStandardURL.cpp#L2386-L2388
        e_path = e_path.lstrip('/\\\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f ')
        path = f'{path}/{e_path}'

    # normalize: foo//bar -> foo/bar
    path = re.sub(r'/+', '/', path)

    if _contains_dot_segments(path):
        raise ValueError("Dot segments are not allowed")

    return urllib.parse.urlunsplit((b_scheme, b_netloc, path, e_query, e_fragment))
