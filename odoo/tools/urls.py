import re
import urllib.parse

__all__ = ['urljoin']


def _contains_dot_segments(path: str | bytes) -> bool:
    # most servers decode url before doing dot segment resolutions
    decoded_path = urllib.parse.unquote(path, errors='strict')
    return any(seg in ('.', '..') for seg in decoded_path.split('/'))


def sanitize_url(value):
    """Sanitize the URL to ensure it has a scheme and doesn't end with /.
    """

    # Spaces must be encoded "%20", trim those that aren't as they
    # likely come from copy/paste mistakes.
    value = value.strip()
    url = urllib.parse.urlsplit(value)

    # Enforce https when the scheme is missing
    if not url.scheme:

        # IPv6 must be enclosed in []
        netloc, _, path = value.partition('/')
        if netloc.count(':') >= 2 and not netloc.startswith('['):
            value = f'[{netloc}]'
            if path:
                value += f'/{path}'

        value = 'https://' + value
        url = urllib.parse.urlsplit(value)

    # Prefer "example.com" over "example.com/". Some naive code do
    # ``domain + path`` instead of ``urljoin(domain, path)``, the
    # former leads to bad double slashes in the concatenated URL.
    if url.path and url.path.strip() == '/':
        url = url._replace(path='')
    # For consistency, do the same for queries and fragments.
    if url.query and url.query.strip() == '?':
        url = url._replace(query='')
    if url.fragment and url.fragment.strip() == '#':
        url = url._replace(fragment='')

    return urllib.parse.urlunsplit(url)


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
