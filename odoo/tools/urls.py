import re
import typing
import urllib.parse
from collections.abc import Iterable, Mapping

import urllib3

__all__ = ['urljoin']

QueryType: typing.TypeAlias = Mapping[str, str | list[str] | None] | Iterable[tuple[str, str | list[str] | None]]


def _contains_dot_segments(path: str | bytes) -> bool:
    # most servers decode url before doing dot segment resolutions
    decoded_path = urllib.parse.unquote(path, errors='strict')
    return any(seg in ('.', '..') for seg in decoded_path.split('/'))


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


class Url(urllib3.util.Url):
    """URL datastructure from urllib3, with some additional utility methods, to reduce imports
    needed when manipulating URLs.
    """

    def decode_query(self) -> dict[str, list[str]]:
        """Decode and return the URL's query."""
        return parse_query(self.query)

    def join(self, path: str) -> "Url":
        """Join the current url with a given path, using `urljoin`."""
        return parse_url(urljoin(self.url, path))


def parse_url(url: str | None) -> Url:
    """Parse a string into an Url object."""
    if not url:
        return Url()
    # Use `.__class__ = Url`?
    return Url(*urllib3.util.parse_url(url))


def _normalize_query(query: QueryType):
    """Normalize a query-like object into a list of key-value pair.

    :param query: Parsed query to normalize. Accepts parse_qs an parse_qsl output.
    :yield: normalized key-value pair
    """  # noqa: DOC402 (does not support sphinx style yields)
    if isinstance(query, Mapping):
        query = iter(query.items())

    for key, value in query:
        if isinstance(value, list):
            for val in value:
                if val is not None:
                    yield key, str(val)
        elif value is not None:
            yield key, str(value)


@typing.overload
def parse_query(qs: str | None, **kwargs) -> dict[str, list[str]]: ...
@typing.overload
def parse_query(qs: bytes, **kwargs) -> dict[bytes, list[bytes]]: ...
def parse_query(qs: str | bytes | None, **kwargs) -> dict[str | bytes, list[str | bytes]]:
    """Parse an URL's query using Urllib. Extra keyword arguments are passed to Urllib"""
    return urllib.parse.parse_qs(qs, **kwargs)


@typing.overload
def parse_query_list(qs: str | None, **kwargs) -> list[tuple[str, str]]: ...
@typing.overload
def parse_query_list(qs: bytes, **kwargs) -> list[tuple[bytes, bytes]]: ...
def parse_query_list(qs: str | bytes | None, **kwargs) -> list[tuple[str | bytes, str | bytes]]:
    """Parse an URL's query using Urllib. Extra keyword arguments are passed to Urllib"""
    return urllib.parse.parse_qsl(qs, **kwargs)


def quote(string: str, safe: str | Iterable[int] = "/", **kwargs) -> str:
    """Quote unsafe characters into %xx"""
    return urllib.parse.quote(string, safe=safe, **kwargs)


def quote_plus(string: str, safe: str | Iterable[int] = "", **kwargs) -> str:
    """Like quote(), but also replace spaces with plus signs"""
    return urllib.parse.quote_plus(string, safe=safe, **kwargs)


def unquote(string: str, encoding: str = "utf-8", errors: str = "replace") -> str:
    """Replace %xx escapes by their single-character equivalent"""
    return urllib.parse.unquote(string, encoding=encoding, errors=errors)


def unquote_plus(string: str, encoding: str = "utf-8", errors: str = "replace") -> str:
    """Like unquote(), but also replace plus signs by spaces"""
    return urllib.parse.unquote_plus(string, encoding=encoding, errors=errors)


def urlencode(query: QueryType, *, safe: str = "", **kwargs) -> str:
    """Encode a dict or sequence of two-element tuples into a URL query string.

    The query is first normalized to a list of key-value, allowing round-tripping both
    `parse_query` and `parse_query_list`, as well as supporting iterators, which is not supported
    by `urllib.parse.urlencode`.
    """
    return urllib.parse.urlencode(list(_normalize_query(query)), safe=safe, **kwargs)
