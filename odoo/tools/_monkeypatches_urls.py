from __future__ import annotations

import os
import sys
import re
import typing as t
import warnings
from werkzeug.datastructures import iter_multi_items
from werkzeug.urls import _decode_idna

import operator

def _check_str_tuple(value: t.Tuple[t.AnyStr, ...]) -> None:
    """Ensure tuple items are all strings or all bytes."""
    if not value:
        return

    item_type = str if isinstance(value[0], str) else bytes

    if any(not isinstance(item, item_type) for item in value):
        raise TypeError(f"Cannot mix str and bytes arguments (got {value!r})")


def _make_encode_wrapper(reference: t.AnyStr) -> t.Callable[[str], t.AnyStr]:
    """Create a function that will be called with a string argument. If
    the reference is bytes, values will be encoded to bytes.
    """
    if isinstance(reference, str):
        return lambda x: x

    return operator.methodcaller("encode", "latin1")

_default_encoding = sys.getdefaultencoding()

def _to_str(
    x: t.Optional[t.Any],
    charset: t.Optional[str] = _default_encoding,
    errors: str = "strict",
    allow_none_charset: bool = False,
):
    if x is None or isinstance(x, str):
        return x

    if not isinstance(x, (bytes, bytearray)):
        return str(x)

    if charset is None:
        if allow_none_charset:
            return x

    return x.decode(charset, errors)  # type: ignore



if t.TYPE_CHECKING:
    from werkzeug import datastructures as ds

# A regular expression for what a valid schema looks like
_scheme_re = re.compile(r"^[a-zA-Z0-9+-.]+$")

# Characters that are safe in any part of an URL.
_always_safe_chars = (
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    "-._~"
    "$!'()*+,;"  # RFC3986 sub-delims set, not including query string delimiters &=
)
_always_safe = frozenset(_always_safe_chars.encode("ascii"))

_hexdigits = "0123456789ABCDEFabcdef"
_hextobyte = {
    f"{a}{b}".encode("ascii"): int(f"{a}{b}", 16)
    for a in _hexdigits
    for b in _hexdigits
}
_bytetohex = [f"%{char:02X}".encode("ascii") for char in range(256)]


class _URLTuple(t.NamedTuple):
    scheme: str
    netloc: str
    path: str
    query: str
    fragment: str


class BaseURL(_URLTuple):
    """Superclass of :py:class:`URL` and :py:class:`BytesURL`.

    .. deprecated:: 2.3
        Will be removed in Werkzeug 2.4. Use the ``urllib.parse`` library instead.
    """

    __slots__ = ()
    _at: str
    _colon: str
    _lbracket: str
    _rbracket: str

    def __new__(cls, *args: t.Any, **kwargs: t.Any) -> BaseURL:
        return super().__new__(cls, *args, **kwargs)

    def __str__(self) -> str:
        return self.to_url()

    def replace(self, **kwargs: t.Any) -> BaseURL:
        """Return an URL with the same values, except for those parameters
        given new values by whichever keyword arguments are specified."""
        return self._replace(**kwargs)

    @property
    def host(self) -> str | None:
        """The host part of the URL if available, otherwise `None`.  The
        host is either the hostname or the IP address mentioned in the
        URL.  It will not contain the port.
        """
        return self._split_host()[0]

    @property
    def ascii_host(self) -> str | None:
        """Works exactly like :attr:`host` but will return a result that
        is restricted to ASCII.  If it finds a netloc that is not ASCII
        it will attempt to idna decode it.  This is useful for socket
        operations when the URL might include internationalized characters.
        """
        rv = self.host
        if rv is not None and isinstance(rv, str):
            try:
                rv = rv.encode("idna").decode("ascii")
            except UnicodeError:
                pass
        return rv

    @property
    def port(self) -> int | None:
        """The port in the URL as an integer if it was present, `None`
        otherwise.  This does not fill in default ports.
        """
        try:
            rv = int(_to_str(self._split_host()[1]))
            if 0 <= rv <= 65535:
                return rv
        except (ValueError, TypeError):
            pass
        return None

    @property
    def auth(self) -> str | None:
        """The authentication part in the URL if available, `None`
        otherwise.
        """
        return self._split_netloc()[0]

    @property
    def username(self) -> str | None:
        """The username if it was part of the URL, `None` otherwise.
        This undergoes URL decoding and will always be a string.
        """
        rv = self._split_auth()[0]
        if rv is not None:
            return _url_unquote_legacy(rv)
        return None

    @property
    def raw_username(self) -> str | None:
        """The username if it was part of the URL, `None` otherwise.
        Unlike :attr:`username` this one is not being decoded.
        """
        return self._split_auth()[0]

    @property
    def password(self) -> str | None:
        """The password if it was part of the URL, `None` otherwise.
        This undergoes URL decoding and will always be a string.
        """
        rv = self._split_auth()[1]
        if rv is not None:
            return _url_unquote_legacy(rv)
        return None

    @property
    def raw_password(self) -> str | None:
        """The password if it was part of the URL, `None` otherwise.
        Unlike :attr:`password` this one is not being decoded.
        """
        return self._split_auth()[1]

    def decode_query(self, *args: t.Any, **kwargs: t.Any) -> ds.MultiDict[str, str]:
        """Decodes the query part of the URL.  Ths is a shortcut for
        calling :func:`url_decode` on the query argument.  The arguments and
        keyword arguments are forwarded to :func:`url_decode` unchanged.
        """
        return url_decode(self.query, *args, **kwargs)

    def join(self, *args: t.Any, **kwargs: t.Any) -> BaseURL:
        """Joins this URL with another one.  This is just a convenience
        function for calling into :meth:`url_join` and then parsing the
        return value again.
        """
        return url_parse(url_join(self, *args, **kwargs))

    def to_url(self) -> str:
        """Returns a URL string or bytes depending on the type of the
        information stored.  This is just a convenience function
        for calling :meth:`url_unparse` for this URL.
        """
        return url_unparse(self)

    def encode_netloc(self) -> str:
        """Encodes the netloc part to an ASCII safe URL as bytes."""
        rv = self.ascii_host or ""
        if ":" in rv:
            rv = f"[{rv}]"
        port = self.port
        if port is not None:
            rv = f"{rv}:{port}"
        auth = ":".join(
            filter(
                None,
                [
                    url_quote(self.raw_username or "", "utf-8", "strict", "/:%"),
                    url_quote(self.raw_password or "", "utf-8", "strict", "/:%"),
                ],
            )
        )
        if auth:
            rv = f"{auth}@{rv}"
        return rv

    def decode_netloc(self) -> str:
        """Decodes the netloc part into a string."""
        host = self.host or ""

        if isinstance(host, bytes):
            host = host.decode()

        rv = _decode_idna(host)

        if ":" in rv:
            rv = f"[{rv}]"
        port = self.port
        if port is not None:
            rv = f"{rv}:{port}"
        auth = ":".join(
            filter(
                None,
                [
                    _url_unquote_legacy(self.raw_username or "", "/:%@"),
                    _url_unquote_legacy(self.raw_password or "", "/:%@"),
                ],
            )
        )
        if auth:
            rv = f"{auth}@{rv}"
        return rv

    def get_file_location(
        self, pathformat: str | None = None
    ) -> tuple[str | None, str | None]:
        """Returns a tuple with the location of the file in the form
        ``(server, location)``.  If the netloc is empty in the URL or
        points to localhost, it's represented as ``None``.

        The `pathformat` by default is autodetection but needs to be set
        when working with URLs of a specific system.  The supported values
        are ``'windows'`` when working with Windows or DOS paths and
        ``'posix'`` when working with posix paths.

        If the URL does not point to a local file, the server and location
        are both represented as ``None``.

        :param pathformat: The expected format of the path component.
                           Currently ``'windows'`` and ``'posix'`` are
                           supported.  Defaults to ``None`` which is
                           autodetect.
        """
        if self.scheme != "file":
            return None, None

        path = url_unquote(self.path)
        host = self.netloc or None

        if pathformat is None:
            if os.name == "nt":
                pathformat = "windows"
            else:
                pathformat = "posix"

        if pathformat == "windows":
            if path[:1] == "/" and path[1:2].isalpha() and path[2:3] in "|:":
                path = f"{path[1:2]}:{path[3:]}"
            windows_share = path[:3] in ("\\" * 3, "/" * 3)
            import ntpath

            path = ntpath.normpath(path)
            # Windows shared drives are represented as ``\\host\\directory``.
            # That results in a URL like ``file://///host/directory``, and a
            # path like ``///host/directory``. We need to special-case this
            # because the path contains the hostname.
            if windows_share and host is None:
                parts = path.lstrip("\\").split("\\", 1)
                if len(parts) == 2:
                    host, path = parts
                else:
                    host = parts[0]
                    path = ""
        elif pathformat == "posix":
            import posixpath

            path = posixpath.normpath(path)
        else:
            raise TypeError(f"Invalid path format {pathformat!r}")

        if host in ("127.0.0.1", "::1", "localhost"):
            host = None

        return host, path

    def _split_netloc(self) -> tuple[str | None, str]:
        if self._at in self.netloc:
            auth, _, netloc = self.netloc.partition(self._at)
            return auth, netloc
        return None, self.netloc

    def _split_auth(self) -> tuple[str | None, str | None]:
        auth = self._split_netloc()[0]
        if not auth:
            return None, None
        if self._colon not in auth:
            return auth, None

        username, _, password = auth.partition(self._colon)
        return username, password

    def _split_host(self) -> tuple[str | None, str | None]:
        rv = self._split_netloc()[1]
        if not rv:
            return None, None

        if not rv.startswith(self._lbracket):
            if self._colon in rv:
                host, _, port = rv.partition(self._colon)
                return host, port
            return rv, None

        idx = rv.find(self._rbracket)
        if idx < 0:
            return rv, None

        host = rv[1:idx]
        rest = rv[idx + 1 :]
        if rest.startswith(self._colon):
            return host, rest[1:]
        return host, None


class URL(BaseURL):
    """Represents a parsed URL.  This behaves like a regular tuple but
    also has some extra attributes that give further insight into the
    URL.

    .. deprecated:: 2.3
        Will be removed in Werkzeug 2.4. Use the ``urllib.parse`` library instead.
    """

    __slots__ = ()
    _at = "@"
    _colon = ":"
    _lbracket = "["
    _rbracket = "]"

    def encode(self, charset: str = "utf-8", errors: str = "replace") -> BytesURL:
        """Encodes the URL to a tuple made out of bytes.  The charset is
        only being used for the path, query and fragment.
        """
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", "'werkzeug", DeprecationWarning)
            return BytesURL(
                self.scheme.encode("ascii"),
                self.encode_netloc(),
                self.path.encode(charset, errors),
                self.query.encode(charset, errors),
                self.fragment.encode(charset, errors),
            )


class BytesURL(BaseURL):
    """Represents a parsed URL in bytes.

    .. deprecated:: 2.3
        Will be removed in Werkzeug 2.4. Use the ``urllib.parse`` library instead.
    """

    __slots__ = ()
    _at = b"@"  # type: ignore
    _colon = b":"  # type: ignore
    _lbracket = b"["  # type: ignore
    _rbracket = b"]"  # type: ignore

    def __str__(self) -> str:
        return self.to_url().decode("utf-8", "replace")  # type: ignore

    def encode_netloc(self) -> bytes:  # type: ignore
        """Returns the netloc unchanged as bytes."""
        return self.netloc  # type: ignore

    def decode(self, charset: str = "utf-8", errors: str = "replace") -> URL:
        """Decodes the URL to a tuple made out of strings.  The charset is
        only being used for the path, query and fragment.
        """
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", "'werkzeug", DeprecationWarning)
            return URL(
                self.scheme.decode("ascii"),  # type: ignore
                self.decode_netloc(),
                self.path.decode(charset, errors),  # type: ignore
                self.query.decode(charset, errors),  # type: ignore
                self.fragment.decode(charset, errors),  # type: ignore
            )


_unquote_maps: dict[frozenset[int], dict[bytes, int]] = {frozenset(): _hextobyte}


def _unquote_to_bytes(string: str | bytes, unsafe: str | bytes = "") -> bytes:
    if isinstance(string, str):
        string = string.encode("utf-8")

    if isinstance(unsafe, str):
        unsafe = unsafe.encode("utf-8")

    unsafe = frozenset(bytearray(unsafe))
    groups = iter(string.split(b"%"))
    result = bytearray(next(groups, b""))

    try:
        hex_to_byte = _unquote_maps[unsafe]
    except KeyError:
        hex_to_byte = _unquote_maps[unsafe] = {
            h: b for h, b in _hextobyte.items() if b not in unsafe
        }

    for group in groups:
        code = group[:2]

        if code in hex_to_byte:
            result.append(hex_to_byte[code])
            result.extend(group[2:])
        else:
            result.append(37)  # %
            result.extend(group)

    return bytes(result)


def _url_encode_impl(
    obj: t.Mapping[str, str] | t.Iterable[tuple[str, str]],
    charset: str,
    sort: bool,
    key: t.Callable[[tuple[str, str]], t.Any] | None,
) -> t.Iterator[str]:
    from werkzeug.datastructures import iter_multi_items

    iterable: t.Iterable[tuple[str, str]] = iter_multi_items(obj)

    if sort:
        iterable = sorted(iterable, key=key)

    for key_str, value_str in iterable:
        if value_str is None:
            continue

        if not isinstance(key_str, bytes):
            key_bytes = str(key_str).encode(charset)
        else:
            key_bytes = key_str

        if not isinstance(value_str, bytes):
            value_bytes = str(value_str).encode(charset)
        else:
            value_bytes = value_str

        yield f"{_fast_url_quote_plus(key_bytes)}={_fast_url_quote_plus(value_bytes)}"


def _url_unquote_legacy(value: str, unsafe: str = "") -> str:
    try:
        return url_unquote(value, charset="utf-8", errors="strict", unsafe=unsafe)
    except UnicodeError:
        return url_unquote(value, charset="latin1", unsafe=unsafe)


def url_parse(
    url: str, scheme: str | None = None, allow_fragments: bool = True
) -> BaseURL:
    """Parses a URL from a string into a :class:`URL` tuple.  If the URL
    is lacking a scheme it can be provided as second argument. Otherwise,
    it is ignored.  Optionally fragments can be stripped from the URL
    by setting `allow_fragments` to `False`.

    The inverse of this function is :func:`url_unparse`.

    :param url: the URL to parse.
    :param scheme: the default schema to use if the URL is schemaless.
    :param allow_fragments: if set to `False` a fragment will be removed
                            from the URL.

    .. deprecated:: 2.3
        Will be removed in Werkzeug 2.4. Use ``urllib.parse.urlsplit`` instead.
    """
    s = _make_encode_wrapper(url)
    is_text_based = isinstance(url, str)

    if scheme is None:
        scheme = s("")
    netloc = query = fragment = s("")
    i = url.find(s(":"))
    if i > 0 and _scheme_re.match(_to_str(url[:i], errors="replace")):
        # make sure "iri" is not actually a port number (in which case
        # "scheme" is really part of the path)
        rest = url[i + 1 :]
        if not rest or any(c not in s("0123456789") for c in rest):
            # not a port number
            scheme, url = url[:i].lower(), rest

    if url[:2] == s("//"):
        delim = len(url)
        for c in s("/?#"):
            wdelim = url.find(c, 2)
            if wdelim >= 0:
                delim = min(delim, wdelim)
        netloc, url = url[2:delim], url[delim:]
        if (s("[") in netloc and s("]") not in netloc) or (
            s("]") in netloc and s("[") not in netloc
        ):
            raise ValueError("Invalid IPv6 URL")

    if allow_fragments and s("#") in url:
        url, fragment = url.split(s("#"), 1)
    if s("?") in url:
        url, query = url.split(s("?"), 1)

    result_type = URL if is_text_based else BytesURL

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", "'werkzeug", DeprecationWarning)
        return result_type(scheme, netloc, url, query, fragment)


def _make_fast_url_quote(
    charset: str = "utf-8",
    errors: str = "strict",
    safe: str | bytes = "/:",
    unsafe: str | bytes = "",
) -> t.Callable[[bytes], str]:
    """Precompile the translation table for a URL encoding function.

    Unlike :func:`url_quote`, the generated function only takes the
    string to quote.

    :param charset: The charset to encode the result with.
    :param errors: How to handle encoding errors.
    :param safe: An optional sequence of safe characters to never encode.
    :param unsafe: An optional sequence of unsafe characters to always encode.
    """
    if isinstance(safe, str):
        safe = safe.encode(charset, errors)

    if isinstance(unsafe, str):
        unsafe = unsafe.encode(charset, errors)

    safe = (frozenset(bytearray(safe)) | _always_safe) - frozenset(bytearray(unsafe))
    table = [chr(c) if c in safe else f"%{c:02X}" for c in range(256)]

    def quote(string: bytes) -> str:
        return "".join([table[c] for c in string])

    return quote


_fast_url_quote = _make_fast_url_quote()
_fast_quote_plus = _make_fast_url_quote(safe=" ", unsafe="+")


def _fast_url_quote_plus(string: bytes) -> str:
    return _fast_quote_plus(string).replace(" ", "+")


def url_quote(
    string: str | bytes,
    charset: str = "utf-8",
    errors: str = "strict",
    safe: str | bytes = "/:",
    unsafe: str | bytes = "",
) -> str:
    """URL encode a single string with a given encoding.

    :param s: the string to quote.
    :param charset: the charset to be used.
    :param safe: an optional sequence of safe characters.
    :param unsafe: an optional sequence of unsafe characters.

    .. deprecated:: 2.3
        Will be removed in Werkzeug 2.4. Use ``urllib.parse.quote`` instead.

    .. versionadded:: 0.9.2
       The `unsafe` parameter was added.
    """

    if not isinstance(string, (str, bytes, bytearray)):
        string = str(string)
    if isinstance(string, str):
        string = string.encode(charset, errors)
    if isinstance(safe, str):
        safe = safe.encode(charset, errors)
    if isinstance(unsafe, str):
        unsafe = unsafe.encode(charset, errors)
    safe = (frozenset(bytearray(safe)) | _always_safe) - frozenset(bytearray(unsafe))
    rv = bytearray()
    for char in bytearray(string):
        if char in safe:
            rv.append(char)
        else:
            rv.extend(_bytetohex[char])
    return bytes(rv).decode(charset)


def url_quote_plus(
    string: str, charset: str = "utf-8", errors: str = "strict", safe: str = ""
) -> str:
    """URL encode a single string with the given encoding and convert
    whitespace to "+".

    :param s: The string to quote.
    :param charset: The charset to be used.
    :param safe: An optional sequence of safe characters.

    .. deprecated:: 2.3
        Will be removed in Werkzeug 2.4. Use ``urllib.parse.quote_plus`` instead.
    """

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", "'werkzeug", DeprecationWarning)
        return url_quote(string, charset, errors, safe + " ", "+").replace(" ", "+")


def url_unparse(components: tuple[str, str, str, str, str]) -> str:
    """The reverse operation to :meth:`url_parse`.  This accepts arbitrary
    as well as :class:`URL` tuples and returns a URL as a string.

    :param components: the parsed URL as tuple which should be converted
                       into a URL string.

    .. deprecated:: 2.3
        Will be removed in Werkzeug 2.4. Use ``urllib.parse.urlunsplit`` instead.
    """

    _check_str_tuple(components)
    scheme, netloc, path, query, fragment = components
    s = _make_encode_wrapper(scheme)
    url = s("")

    # We generally treat file:///x and file:/x the same which is also
    # what browsers seem to do.  This also allows us to ignore a schema
    # register for netloc utilization or having to differentiate between
    # empty and missing netloc.
    if netloc or (scheme and path.startswith(s("/"))):
        if path and path[:1] != s("/"):
            path = s("/") + path
        url = s("//") + (netloc or s("")) + path
    elif path:
        url += path
    if scheme:
        url = scheme + s(":") + url
    if query:
        url = url + s("?") + query
    if fragment:
        url = url + s("#") + fragment
    return url


def url_unquote(
    s: str | bytes,
    charset: str = "utf-8",
    errors: str = "replace",
    unsafe: str = "",
) -> str:
    """URL decode a single string with a given encoding.  If the charset
    is set to `None` no decoding is performed and raw bytes are
    returned.

    :param s: the string to unquote.
    :param charset: the charset of the query string.  If set to `None`
        no decoding will take place.
    :param errors: the error handling for the charset decoding.

    .. deprecated:: 2.3
        Will be removed in Werkzeug 2.4. Use ``urllib.parse.unquote`` instead.
    """
    rv = _unquote_to_bytes(s, unsafe)
    if charset is None:
        return rv
    return rv.decode(charset, errors)


def url_unquote_plus(
    s: str | bytes, charset: str = "utf-8", errors: str = "replace"
) -> str:
    """URL decode a single string with the given `charset` and decode "+" to
    whitespace.

    Per default encoding errors are ignored.  If you want a different behavior
    you can set `errors` to ``'replace'`` or ``'strict'``.

    :param s: The string to unquote.
    :param charset: the charset of the query string.  If set to `None`
        no decoding will take place.
    :param errors: The error handling for the `charset` decoding.

    .. deprecated:: 2.3
        Will be removed in Werkzeug 2.4. Use ``urllib.parse.unquote_plus`` instead.
    """
    if isinstance(s, str):
        s = s.replace("+", " ")
    else:
        s = s.replace(b"+", b" ")

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", "'werkzeug", DeprecationWarning)
        return url_unquote(s, charset, errors)


def url_fix(s: str, charset: str = "utf-8") -> str:
    r"""Sometimes you get an URL by a user that just isn't a real URL because
    it contains unsafe characters like ' ' and so on. This function can fix
    some of the problems in a similar way browsers handle data entered by the
    user:

    >>> url_fix('http://de.wikipedia.org/wiki/Elf (Begriffskl\xe4rung)')
    'http://de.wikipedia.org/wiki/Elf%20(Begriffskl%C3%A4rung)'

    :param s: the string with the URL to fix.
    :param charset: The target charset for the URL if the url was given
        as a string.

    .. deprecated:: 2.3
        Will be removed in Werkzeug 2.4.
    """
    # First step is to switch to text processing and to convert
    # backslashes (which are invalid in URLs anyways) to slashes.  This is
    # consistent with what Chrome does.
    s = _to_str(s, charset, "replace").replace("\\", "/")

    # For the specific case that we look like a malformed windows URL
    # we want to fix this up manually:
    if s.startswith("file://") and s[7:8].isalpha() and s[8:10] in (":/", "|/"):
        s = f"file:///{s[7:]}"

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", "'werkzeug", DeprecationWarning)
        url = url_parse(s)
        path = url_quote(url.path, charset, safe="/%+$!*'(),")
        qs = url_quote_plus(url.query, charset, safe=":&%=+$!*'(),")
        anchor = url_quote_plus(url.fragment, charset, safe=":&%=+$!*'(),")
        return url_unparse((url.scheme, url.encode_netloc(), path, qs, anchor))


def url_decode(
    s: t.AnyStr,
    charset: str = "utf-8",
    include_empty: bool = True,
    errors: str = "replace",
    separator: str = "&",
    cls: type[ds.MultiDict] | None = None,
) -> ds.MultiDict[str, str]:
    """Parse a query string and return it as a :class:`MultiDict`.

    :param s: The query string to parse.
    :param charset: Decode bytes to string with this charset. If not
        given, bytes are returned as-is.
    :param include_empty: Include keys with empty values in the dict.
    :param errors: Error handling behavior when decoding bytes.
    :param separator: Separator character between pairs.
    :param cls: Container to hold result instead of :class:`MultiDict`.

    .. deprecated:: 2.3
        Will be removed in Werkzeug 2.4. Use ``urllib.parse.parse_qs`` instead.

    .. versionchanged:: 2.1
        The ``decode_keys`` parameter was removed.

    .. versionchanged:: 0.5
        In previous versions ";" and "&" could be used for url decoding.
        Now only "&" is supported. If you want to use ";", a different
        ``separator`` can be provided.

    .. versionchanged:: 0.5
        The ``cls`` parameter was added.
    """
    if cls is None:
        from werkzeug.datastructures import MultiDict  # noqa: F811

        cls = MultiDict
    if isinstance(s, str) and not isinstance(separator, str):
        separator = separator.decode(charset or "ascii")
    elif isinstance(s, bytes) and not isinstance(separator, bytes):
        separator = separator.encode(charset or "ascii")  # type: ignore
    return cls(
        _url_decode_impl(
            s.split(separator), charset, include_empty, errors  # type: ignore
        )
    )


def url_decode_stream(
    stream: t.IO[bytes],
    charset: str = "utf-8",
    include_empty: bool = True,
    errors: str = "replace",
    separator: bytes = b"&",
    cls: type[ds.MultiDict] | None = None,
    limit: int | None = None,
) -> ds.MultiDict[str, str]:
    """Works like :func:`url_decode` but decodes a stream.  The behavior
    of stream and limit follows functions like
    :func:`~werkzeug.wsgi.make_line_iter`.  The generator of pairs is
    directly fed to the `cls` so you can consume the data while it's
    parsed.

    :param stream: a stream with the encoded querystring
    :param charset: the charset of the query string.  If set to `None`
        no decoding will take place.
    :param include_empty: Set to `False` if you don't want empty values to
                          appear in the dict.
    :param errors: the decoding error behavior.
    :param separator: the pair separator to be used, defaults to ``&``
    :param cls: an optional dict class to use.  If this is not specified
                       or `None` the default :class:`MultiDict` is used.
    :param limit: the content length of the URL data.  Not necessary if
                  a limited stream is provided.

    .. deprecated:: 2.3
        Will be removed in Werkzeug 2.4. Use ``urllib.parse.parse_qs`` instead.

    .. versionchanged:: 2.1
        The ``decode_keys`` and ``return_iterator`` parameters were removed.

    .. versionadded:: 0.8
    """

    from werkzeug.wsgi import make_chunk_iter

    pair_iter = make_chunk_iter(stream, separator, limit)
    decoder = _url_decode_impl(pair_iter, charset, include_empty, errors)

    if cls is None:
        from werkzeug.datastructures import MultiDict  # noqa: F811

        cls = MultiDict

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", "'make_chunk_iter", DeprecationWarning)
        return cls(decoder)


def _url_decode_impl(
    pair_iter: t.Iterable[t.AnyStr], charset: str, include_empty: bool, errors: str
) -> t.Iterator[tuple[str, str]]:
    for pair in pair_iter:
        if not pair:
            continue
        s = _make_encode_wrapper(pair)
        equal = s("=")
        if equal in pair:
            key, value = pair.split(equal, 1)
        else:
            if not include_empty:
                continue
            key = pair
            value = s("")
        yield (
            url_unquote_plus(key, charset, errors),
            url_unquote_plus(value, charset, errors),
        )


def url_encode(
    obj: t.Mapping[str, str] | t.Iterable[tuple[str, str]],
    charset: str = "utf-8",
    sort: bool = False,
    key: t.Callable[[tuple[str, str]], t.Any] | None = None,
    separator: str = "&",
) -> str:
    """URL encode a dict/`MultiDict`.  If a value is `None` it will not appear
    in the result string.  Per default only values are encoded into the target
    charset strings.

    :param obj: the object to encode into a query string.
    :param charset: the charset of the query string.
    :param sort: set to `True` if you want parameters to be sorted by `key`.
    :param separator: the separator to be used for the pairs.
    :param key: an optional function to be used for sorting.  For more details
                check out the :func:`sorted` documentation.

    .. deprecated:: 2.3
        Will be removed in Werkzeug 2.4. Use ``urllib.parse.urlencode`` instead.

    .. versionchanged:: 2.1
        The ``encode_keys`` parameter was removed.

    .. versionchanged:: 0.5
        Added the ``sort``, ``key``, and ``separator`` parameters.
    """
    separator = _to_str(separator, "ascii")
    return separator.join(_url_encode_impl(obj, charset, sort, key))


def url_encode_stream(
    obj: t.Mapping[str, str] | t.Iterable[tuple[str, str]],
    stream: t.IO[str] | None = None,
    charset: str = "utf-8",
    sort: bool = False,
    key: t.Callable[[tuple[str, str]], t.Any] | None = None,
    separator: str = "&",
) -> None:
    """Like :meth:`url_encode` but writes the results to a stream
    object.  If the stream is `None` a generator over all encoded
    pairs is returned.

    :param obj: the object to encode into a query string.
    :param stream: a stream to write the encoded object into or `None` if
                   an iterator over the encoded pairs should be returned.  In
                   that case the separator argument is ignored.
    :param charset: the charset of the query string.
    :param sort: set to `True` if you want parameters to be sorted by `key`.
    :param separator: the separator to be used for the pairs.
    :param key: an optional function to be used for sorting.  For more details
                check out the :func:`sorted` documentation.

    .. deprecated:: 2.3
        Will be removed in Werkzeug 2.4. Use ``urllib.parse.urlencode`` instead.

    .. versionchanged:: 2.1
        The ``encode_keys`` parameter was removed.

    .. versionadded:: 0.8
    """
    separator = _to_str(separator, "ascii")
    gen = _url_encode_impl(obj, charset, sort, key)
    if stream is None:
        return gen  # type: ignore
    for idx, chunk in enumerate(gen):
        if idx:
            stream.write(separator)
        stream.write(chunk)
    return None


def url_join(
    base: str | tuple[str, str, str, str, str],
    url: str | tuple[str, str, str, str, str],
    allow_fragments: bool = True,
) -> str:
    """Join a base URL and a possibly relative URL to form an absolute
    interpretation of the latter.

    :param base: the base URL for the join operation.
    :param url: the URL to join.
    :param allow_fragments: indicates whether fragments should be allowed.

    .. deprecated:: 2.3
        Will be removed in Werkzeug 2.4. Use ``urllib.parse.urljoin`` instead.
    """
    if isinstance(base, tuple):
        base = url_unparse(base)
    if isinstance(url, tuple):
        url = url_unparse(url)

    _check_str_tuple((base, url))
    s = _make_encode_wrapper(base)

    if not base:
        return url
    if not url:
        return base

    bscheme, bnetloc, bpath, bquery, bfragment = url_parse(
        base, allow_fragments=allow_fragments
    )
    scheme, netloc, path, query, fragment = url_parse(url, bscheme, allow_fragments)
    if scheme != bscheme:
        return url
    if netloc:
        return url_unparse((scheme, netloc, path, query, fragment))
    netloc = bnetloc

    if path[:1] == s("/"):
        segments = path.split(s("/"))
    elif not path:
        segments = bpath.split(s("/"))
        if not query:
            query = bquery
    else:
        segments = bpath.split(s("/"))[:-1] + path.split(s("/"))

    # If the rightmost part is "./" we want to keep the slash but
    # remove the dot.
    if segments[-1] == s("."):
        segments[-1] = s("")

    # Resolve ".." and "."
    segments = [segment for segment in segments if segment != s(".")]
    while True:
        i = 1
        n = len(segments) - 1
        while i < n:
            if segments[i] == s("..") and segments[i - 1] not in (s(""), s("..")):
                del segments[i - 1 : i + 1]
                break
            i += 1
        else:
            break

    # Remove trailing ".." if the URL is absolute
    unwanted_marker = [s(""), s("..")]
    while segments[:2] == unwanted_marker:
        del segments[1]

    path = s("/").join(segments)
    return url_unparse((scheme, netloc, path, query, fragment))


from werkzeug import urls
# see https://github.com/pallets/werkzeug/compare/2.3.0..3.0.0
# see https://github.com/pallets/werkzeug/blob/2.3.0/src/werkzeug/urls.py for replacement
urls.url_decode = url_decode
urls.url_encode = url_encode
urls.url_join = url_join
urls.url_parse = url_parse
urls.url_quote = url_quote
urls.url_quote_plus = url_quote_plus
urls.url_unquote_plus = url_unquote_plus
urls.url_unparse = url_unparse
urls.URL = URL
