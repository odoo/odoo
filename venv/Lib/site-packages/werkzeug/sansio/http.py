import re
import typing as t
from datetime import datetime

from .._internal import _cookie_parse_impl
from .._internal import _dt_as_utc
from .._internal import _to_str
from ..http import generate_etag
from ..http import parse_date
from ..http import parse_etags
from ..http import parse_if_range_header
from ..http import unquote_etag

_etag_re = re.compile(r'([Ww]/)?(?:"(.*?)"|(.*?))(?:\s*,\s*|$)')


def is_resource_modified(
    http_range: t.Optional[str] = None,
    http_if_range: t.Optional[str] = None,
    http_if_modified_since: t.Optional[str] = None,
    http_if_none_match: t.Optional[str] = None,
    http_if_match: t.Optional[str] = None,
    etag: t.Optional[str] = None,
    data: t.Optional[bytes] = None,
    last_modified: t.Optional[t.Union[datetime, str]] = None,
    ignore_if_range: bool = True,
) -> bool:
    """Convenience method for conditional requests.
    :param http_range: Range HTTP header
    :param http_if_range: If-Range HTTP header
    :param http_if_modified_since: If-Modified-Since HTTP header
    :param http_if_none_match: If-None-Match HTTP header
    :param http_if_match: If-Match HTTP header
    :param etag: the etag for the response for comparison.
    :param data: or alternatively the data of the response to automatically
                 generate an etag using :func:`generate_etag`.
    :param last_modified: an optional date of the last modification.
    :param ignore_if_range: If `False`, `If-Range` header will be taken into
                            account.
    :return: `True` if the resource was modified, otherwise `False`.

    .. versionadded:: 2.2
    """
    if etag is None and data is not None:
        etag = generate_etag(data)
    elif data is not None:
        raise TypeError("both data and etag given")

    unmodified = False
    if isinstance(last_modified, str):
        last_modified = parse_date(last_modified)

    # HTTP doesn't use microsecond, remove it to avoid false positive
    # comparisons. Mark naive datetimes as UTC.
    if last_modified is not None:
        last_modified = _dt_as_utc(last_modified.replace(microsecond=0))

    if_range = None
    if not ignore_if_range and http_range is not None:
        # https://tools.ietf.org/html/rfc7233#section-3.2
        # A server MUST ignore an If-Range header field received in a request
        # that does not contain a Range header field.
        if_range = parse_if_range_header(http_if_range)

    if if_range is not None and if_range.date is not None:
        modified_since: t.Optional[datetime] = if_range.date
    else:
        modified_since = parse_date(http_if_modified_since)

    if modified_since and last_modified and last_modified <= modified_since:
        unmodified = True

    if etag:
        etag, _ = unquote_etag(etag)
        etag = t.cast(str, etag)

        if if_range is not None and if_range.etag is not None:
            unmodified = parse_etags(if_range.etag).contains(etag)
        else:
            if_none_match = parse_etags(http_if_none_match)
            if if_none_match:
                # https://tools.ietf.org/html/rfc7232#section-3.2
                # "A recipient MUST use the weak comparison function when comparing
                # entity-tags for If-None-Match"
                unmodified = if_none_match.contains_weak(etag)

            # https://tools.ietf.org/html/rfc7232#section-3.1
            # "Origin server MUST use the strong comparison function when
            # comparing entity-tags for If-Match"
            if_match = parse_etags(http_if_match)
            if if_match:
                unmodified = not if_match.is_strong(etag)

    return not unmodified


def parse_cookie(
    cookie: t.Union[bytes, str, None] = "",
    charset: str = "utf-8",
    errors: str = "replace",
    cls: t.Optional[t.Type["ds.MultiDict"]] = None,
) -> "ds.MultiDict[str, str]":
    """Parse a cookie from a string.

    The same key can be provided multiple times, the values are stored
    in-order. The default :class:`MultiDict` will have the first value
    first, and all values can be retrieved with
    :meth:`MultiDict.getlist`.

    :param cookie: The cookie header as a string.
    :param charset: The charset for the cookie values.
    :param errors: The error behavior for the charset decoding.
    :param cls: A dict-like class to store the parsed cookies in.
        Defaults to :class:`MultiDict`.

    .. versionadded:: 2.2
    """
    # PEP 3333 sends headers through the environ as latin1 decoded
    # strings. Encode strings back to bytes for parsing.
    if isinstance(cookie, str):
        cookie = cookie.encode("latin1", "replace")

    if cls is None:
        cls = ds.MultiDict

    def _parse_pairs() -> t.Iterator[t.Tuple[str, str]]:
        for key, val in _cookie_parse_impl(cookie):  # type: ignore
            key_str = _to_str(key, charset, errors, allow_none_charset=True)

            if not key_str:
                continue

            val_str = _to_str(val, charset, errors, allow_none_charset=True)
            yield key_str, val_str

    return cls(_parse_pairs())


# circular dependencies
from .. import datastructures as ds
