from __future__ import annotations

import io
import re
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from email.utils import formatdate
from enum import Enum
from http import HTTPStatus
from urllib.parse import unquote_to_bytes

__all__ = [
    "LAST_CHUNK",
    "BodyError",
    "BodyLimits",
    "BodyReader",
    "BufferedSource",
    "ChunkedReader",
    "Framing",
    "HeadLimits",
    "LengthReader",
    "ProtocolError",
    "RequestHead",
    "ResponseHead",
    "encode_chunk",
    "find_head",
    "http_date",
    "parse_request_head",
    "prepare_response_head",
]

LAST_CHUNK = b"0\r\n\r\n"

_TOKEN = re.compile(rb"[!#$%&'*+\-.^_`|~0-9A-Za-z]+\Z")
_HEAD_END = re.compile(rb"\r?\n\r?\n")
_MAX_LEADING_EMPTY_BYTES = 8
_VERSION = re.compile(rb"HTTP/([0-9])\.([0-9])\Z")
_FORBIDDEN_IN_VALUE = re.compile(rb"[\x00-\x08\x0a-\x1f\x7f]")
_FORBIDDEN_IN_TARGET = re.compile(rb"[\x00-\x20\x7f]")
_FORBIDDEN_IN_HOST = re.compile(rb"[\x00-\x20\x7f/?#@\\]")
_CONTENT_LENGTH = re.compile(rb"[0-9]{1,19}\Z")
_ABSOLUTE_FORM = re.compile(rb"(https?)://([^/?#]*)(.*)\Z", re.IGNORECASE)
_CHUNK_SIZE = re.compile(rb"([0-9A-Fa-f]{1,16})[ \t]*(;[^\r\n]*)?\Z")

_RESPONSE_TOKEN = re.compile(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+\Z")
_RESPONSE_FORBIDDEN_IN_VALUE = re.compile(r"[\x00-\x08\x0a-\x1f\x7f]")
_RESPONSE_STATUS = re.compile(r"([1-5][0-9]{2})(?: ([^\x00-\x08\x0a-\x1f\x7f]*))?\Z")
_RESPONSE_CONTENT_LENGTH = re.compile(r"[0-9]{1,19}\Z")
_FRAMING_HEADERS = frozenset({"connection", "keep-alive", "transfer-encoding"})


class ProtocolError(Exception):
    def __init__(self, status: HTTPStatus, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


class BodyError(OSError):
    pass


@dataclass(frozen=True, slots=True)
class HeadLimits:
    max_head_bytes: int = 65536
    max_header_count: int = 100


@dataclass(frozen=True, slots=True)
class RequestHead:
    method: str
    target: str
    version: tuple[int, int]
    headers: tuple[tuple[str, str], ...]
    path: str
    query: str
    host: str | None
    content_length: int | None
    chunked: bool
    keep_alive: bool
    expect_continue: bool
    must_close: bool

    @property
    def protocol(self) -> str:
        return f"HTTP/{self.version[0]}.{self.version[1]}"

    @property
    def has_body(self) -> bool:
        return self.chunked or bool(self.content_length)


def find_head(
    buffer: bytes | bytearray, limits: HeadLimits, scanned: int = 0
) -> tuple[int, int] | None:
    # RFC 9112 2.2 asks only that a stray CRLF before the request line be ignored.
    # Skipping them without bound let one connection stream blank lines that never
    # counted against the head limit and were rescanned on every read.
    start = 0
    size = len(buffer)
    while (
        start < size and start <= _MAX_LEADING_EMPTY_BYTES and buffer[start] in b"\r\n"
    ):
        start += 1
    if start > _MAX_LEADING_EMPTY_BYTES:
        raise _bad("too many empty lines before the request line")
    # A blank line is at most four bytes, so one completed by new data starts at
    # most three bytes before what the previous call had already scanned.
    match = _HEAD_END.search(buffer, max(start, scanned - 3))
    if match is None:
        if size - start > limits.max_head_bytes:
            raise ProtocolError(
                HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE,
                "request head exceeds the size limit",
            )
        return None
    if match.start() - start > limits.max_head_bytes:
        raise ProtocolError(
            HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE,
            "request head exceeds the size limit",
        )
    return start, match.end()


def _bad(detail: str) -> ProtocolError:
    return ProtocolError(HTTPStatus.BAD_REQUEST, detail)


def _split_lines(raw: bytes) -> list[bytes]:
    out = []
    for line in raw.split(b"\n"):
        stripped = line.removesuffix(b"\r")
        if b"\r" in stripped:
            raise _bad("bare CR in request head")
        out.append(stripped)
    while out and not out[-1]:
        out.pop()
    return out


def _parse_version(version: bytes) -> tuple[int, int]:
    match = _VERSION.match(version)
    if match is None:
        raise _bad("malformed HTTP version")
    major, minor = int(match.group(1)), int(match.group(2))
    if major != 1:
        raise ProtocolError(
            HTTPStatus.HTTP_VERSION_NOT_SUPPORTED, "only HTTP/1.x is supported"
        )
    return (1, 1) if minor >= 1 else (1, 0)


def _parse_fields(lines: list[bytes], limits: HeadLimits) -> list[tuple[str, str]]:
    if len(lines) > limits.max_header_count:
        raise ProtocolError(
            HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE, "too many header fields"
        )
    fields = []
    for line in lines:
        if line[:1] in (b" ", b"\t"):
            raise _bad("obsolete line folding")
        name, sep, value = line.partition(b":")
        if not sep or not _TOKEN.match(name):
            raise _bad("malformed header field name")
        value = value.strip(b" \t")
        if _FORBIDDEN_IN_VALUE.search(value):
            raise _bad("control character in header field value")
        fields.append((name.decode("ascii"), value.decode("latin-1")))
    return fields


def _values(fields: list[tuple[str, str]], name: str) -> list[str]:
    return [value for key, value in fields if key.lower() == name]


def _tokens(values: list[str]) -> list[str]:
    return [token.strip().lower() for value in values for token in value.split(",")]


def _parse_content_length(values: list[str]) -> int | None:
    if not values:
        return None
    lengths = {token.strip() for value in values for token in value.split(",")}
    if len(lengths) != 1:
        raise _bad("conflicting Content-Length values")
    (length,) = lengths
    if not _CONTENT_LENGTH.match(length.encode("latin-1")):
        raise _bad("malformed Content-Length")
    return int(length)


def _parse_transfer_coding(values: list[str], version: tuple[int, int]) -> bool:
    if not values:
        return False
    codings = _tokens(values)
    if version == (1, 0):
        raise _bad("Transfer-Encoding in an HTTP/1.0 request")
    if "" in codings or codings[-1] != "chunked" or codings.count("chunked") > 1:
        raise _bad("chunked must be the final transfer coding, applied once")
    if len(codings) > 1:
        raise ProtocolError(HTTPStatus.NOT_IMPLEMENTED, "unsupported transfer coding")
    return True


def _check_host(host: str) -> str:
    if _FORBIDDEN_IN_HOST.search(host.encode("latin-1")):
        raise _bad("malformed Host")
    return host


def _split_target(method: bytes, target: bytes) -> tuple[bytes, bytes, str | None]:
    if target.startswith(b"/"):
        authority = None
        rest = target
    elif (absolute := _ABSOLUTE_FORM.match(target)) is not None:
        authority = _check_host(absolute.group(2).decode("latin-1"))
        rest = absolute.group(3) or b"/"
    elif target == b"*" and method == b"OPTIONS":
        return b"*", b"", None
    elif method == b"CONNECT":
        raise ProtocolError(HTTPStatus.NOT_IMPLEMENTED, "CONNECT is not supported")
    else:
        raise _bad("unsupported request-target form")
    rest = rest.partition(b"#")[0]
    path, _, query = rest.partition(b"?")
    if path.startswith(b"//"):
        path = b"/" + path.lstrip(b"/")
    return path, query, authority


def _parse_expectation(values: list[str], version: tuple[int, int]) -> bool:
    if not values:
        return False
    if set(_tokens(values)) != {"100-continue"}:
        raise ProtocolError(HTTPStatus.EXPECTATION_FAILED, "unsupported expectation")
    return version == (1, 1)


def parse_request_head(raw: bytes, limits: HeadLimits) -> RequestHead:
    lines = _split_lines(raw)
    if not lines:
        raise _bad("empty request head")
    parts = lines[0].split(b" ")
    if len(parts) != 3:
        raise _bad("malformed request line")
    method, target, version_bytes = parts
    if not _TOKEN.match(method):
        raise _bad("malformed method")
    if not target or _FORBIDDEN_IN_TARGET.search(target):
        raise _bad("malformed request-target")
    version = _parse_version(version_bytes)
    fields = _parse_fields(lines[1:], limits)

    hosts = _values(fields, "host")
    if len(hosts) > 1 or (version == (1, 1) and not hosts):
        raise _bad("an HTTP/1.1 request needs exactly one Host")
    path, query, authority = _split_target(method, target)
    if authority is not None:
        host: str | None = authority
    else:
        host = _check_host(hosts[0]) if hosts else None

    content_length = _parse_content_length(_values(fields, "content-length"))
    chunked = _parse_transfer_coding(_values(fields, "transfer-encoding"), version)
    must_close = chunked and content_length is not None
    if chunked:
        content_length = None

    connection = _tokens(_values(fields, "connection"))
    return RequestHead(
        method=method.decode("ascii"),
        target=target.decode("latin-1"),
        version=version,
        headers=tuple(fields),
        path=unquote_to_bytes(path).decode("latin-1"),
        query=query.decode("latin-1"),
        host=host,
        content_length=content_length,
        chunked=chunked,
        keep_alive=version == (1, 1) and "close" not in connection,
        expect_continue=_parse_expectation(_values(fields, "expect"), version),
        must_close=must_close,
    )


class BufferedSource:
    __slots__ = ("buffer", "eof", "recv")

    def __init__(
        self, recv: Callable[[int], bytes], buffer: bytearray | None = None
    ) -> None:
        self.recv = recv
        self.buffer = buffer if buffer is not None else bytearray()
        self.eof = False

    def receive_into_buffer(self, size: int = 65536) -> bool:
        if self.eof:
            return False
        data = self.recv(size)
        if not data:
            self.eof = True
            return False
        self.buffer += data
        return True

    def take_line(self, limit: int) -> bytes:
        while True:
            end = self.buffer.find(b"\n")
            if end >= 0:
                line = bytes(self.buffer[: end + 1])
                del self.buffer[: end + 1]
                return line
            if len(self.buffer) > limit:
                raise BodyError("chunk framing line too long")
            if not self.receive_into_buffer():
                raise BodyError("connection closed inside a chunked body")


@dataclass(frozen=True, slots=True)
class BodyLimits:
    max_chunk_line: int = 4096
    max_trailer_bytes: int = 16384


class _BodyReader(io.RawIOBase):
    def __init__(
        self, source: BufferedSource, on_first_read: Callable[[], None] | None
    ) -> None:
        super().__init__()
        self._source = source
        self._on_first_read = on_first_read
        self.bytes_read = 0

    @property
    def exhausted(self) -> bool:
        raise NotImplementedError

    def _ready(self, most: int) -> int:
        raise NotImplementedError

    def _consume(self, size: int) -> bytes:
        raise NotImplementedError

    def readable(self) -> bool:
        return True

    def _available(self, most: int) -> int:
        if self._on_first_read is not None:
            callback, self._on_first_read = self._on_first_read, None
            callback()
        return self._ready(most)

    def readinto(self, buffer: memoryview | bytearray) -> int:  # type: ignore[override]
        view = memoryview(buffer).cast("B")
        data = self.read(len(view))
        view[: len(data)] = data
        return len(data)

    def read(self, size: int | None = -1) -> bytes:
        if size is None or size < 0:
            return self.readall()
        if size == 0:
            return b""
        ready = self._available(size)
        return self._consume(ready) if ready else b""

    def readall(self) -> bytes:
        chunks = []
        while data := self.read(65536):
            chunks.append(data)
        return b"".join(chunks)

    def readline(self, size: int | None = -1) -> bytes:
        limit = size if size is not None and size >= 0 else None
        out = bytearray()
        while limit is None or len(out) < limit:
            ready = self._available(65536 if limit is None else limit - len(out))
            if not ready:
                break
            newline = self._source.buffer.find(b"\n", 0, ready)
            out += self._consume(newline + 1 if newline >= 0 else ready)
            if newline >= 0:
                break
        return bytes(out)

    def __iter__(self) -> Iterator[bytes]:
        while line := self.readline():
            yield line

    def drain(self, max_bytes: int, deadline: float) -> bool:
        discarded = 0
        while not self.exhausted:
            if discarded > max_bytes or time.monotonic() > deadline:
                return False
            discarded += len(self.read(65536))
        return True


class LengthReader(_BodyReader):
    def __init__(
        self,
        source: BufferedSource,
        length: int,
        on_first_read: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(source, on_first_read)
        self._remaining = length

    @property
    def exhausted(self) -> bool:
        return self._remaining <= 0

    def _ready(self, most: int) -> int:
        if self._remaining <= 0:
            return 0
        if not self._source.buffer and not self._source.receive_into_buffer():
            raise BodyError("connection closed before the declared Content-Length")
        return min(most, self._remaining, len(self._source.buffer))

    def _consume(self, size: int) -> bytes:
        data = bytes(self._source.buffer[:size])
        del self._source.buffer[:size]
        self._remaining -= size
        self.bytes_read += size
        return data


class ChunkedReader(_BodyReader):
    def __init__(
        self,
        source: BufferedSource,
        limits: BodyLimits,
        on_first_read: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(source, on_first_read)
        self._limits = limits
        self._chunk_left = 0
        self._done = False

    @property
    def exhausted(self) -> bool:
        return self._done

    def _line(self) -> bytes:
        line = self._source.take_line(self._limits.max_chunk_line)
        if not line.endswith(b"\r\n"):
            raise BodyError("chunked framing requires CRLF")
        return line[:-2]

    def _read_trailers(self) -> None:
        consumed = 0
        while line := self._line():
            consumed += len(line) + 2
            if consumed > self._limits.max_trailer_bytes:
                raise BodyError("chunked trailer section too large")

    def _ready(self, most: int) -> int:
        if self._done:
            return 0
        if self._chunk_left == 0:
            match = _CHUNK_SIZE.match(self._line())
            if match is None:
                raise BodyError("malformed chunk size")
            self._chunk_left = int(match.group(1), 16)
            if self._chunk_left == 0:
                self._read_trailers()
                self._done = True
                return 0
        if not self._source.buffer and not self._source.receive_into_buffer():
            raise BodyError("connection closed inside a chunk")
        return min(most, self._chunk_left, len(self._source.buffer))

    def _consume(self, size: int) -> bytes:
        data = bytes(self._source.buffer[:size])
        del self._source.buffer[:size]
        self._chunk_left -= size
        self.bytes_read += size
        if self._chunk_left == 0 and self._line():
            raise BodyError("chunk data longer than its declared size")
        return data


BodyReader = LengthReader | ChunkedReader


class Framing(Enum):
    NONE = "none"
    LENGTH = "length"
    CHUNKED = "chunked"
    CLOSE = "close"


@dataclass(frozen=True, slots=True)
class ResponseHead:
    code: int
    data: bytes
    framing: Framing
    content_length: int | None
    keep_alive: bool


class _DateCache:
    __slots__ = ("_second", "_value")

    def __init__(self) -> None:
        self._second = -1
        self._value = ""

    def __call__(self) -> str:
        now = int(time.time())
        if now != self._second:
            self._value = formatdate(now, usegmt=True)
            self._second = now
        return self._value


http_date = _DateCache()


def encode_chunk(data: bytes) -> bytes:
    return b"%x\r\n%s\r\n" % (len(data), data) if data else b""


def prepare_response_head(
    status: str,
    headers: list[tuple[str, str]],
    *,
    method: str,
    version: tuple[int, int],
    keep_alive: bool,
) -> ResponseHead:
    match = _RESPONSE_STATUS.match(status)
    if match is None:
        raise ValueError(f"invalid WSGI status {status!r}")
    code = int(match.group(1))
    upgrade = code == 101
    lines = [f"HTTP/1.1 {status}"]
    content_length: int | None = None
    has_date = False
    for name, value in headers:
        if not _RESPONSE_TOKEN.match(name) or _RESPONSE_FORBIDDEN_IN_VALUE.search(
            value
        ):
            raise ValueError(f"invalid response header {name!r}")
        folded = name.lower()
        if folded in _FRAMING_HEADERS and not upgrade:
            if folded == "connection" and "close" in value.lower():
                keep_alive = False
            continue
        if folded == "content-length":
            if not _RESPONSE_CONTENT_LENGTH.match(value) or (
                content_length is not None and int(value) != content_length
            ):
                raise ValueError(f"invalid Content-Length {value!r}")
            if content_length is not None:
                continue
            content_length = int(value)
        elif folded == "date":
            has_date = True
        lines.append(f"{name}: {value}")
    if not has_date:
        lines.append(f"Date: {http_date()}")

    if upgrade:
        framing = Framing.NONE
        keep_alive = False
    elif method == "HEAD" or code < 200 or code in (204, 304):
        framing = Framing.NONE
    elif content_length is not None:
        framing = Framing.LENGTH
    elif version == (1, 1):
        framing = Framing.CHUNKED
        lines.append("Transfer-Encoding: chunked")
    else:
        framing = Framing.CLOSE
        keep_alive = False
    if version != (1, 1):
        keep_alive = False
    if not keep_alive and version == (1, 1) and not upgrade:
        lines.append("Connection: close")
    lines.append("\r\n")
    return ResponseHead(
        code=code,
        data="\r\n".join(lines).encode("latin-1"),
        framing=framing,
        content_length=content_length,
        keep_alive=keep_alive,
    )
