from __future__ import annotations

import contextlib
import logging
import socket
import sys
import threading
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from enum import Enum
from http import HTTPStatus
from typing import Any

from werkzeug.urls import uri_to_iri

from odoo.libs.debug_log import DebugLog
from odoo.libs.http1 import (
    LAST_CHUNK,
    BodyLimits,
    BodyReader,
    BufferedSource,
    ChunkedReader,
    Framing,
    HeadLimits,
    LengthReader,
    ProtocolError,
    RequestHead,
    ResponseHead,
    encode_chunk,
    find_head,
    parse_request_head,
    prepare_response_head,
)
from odoo.libs.worker_thread import current_worker_thread
from odoo.logutils import root_handler_uses_colors

from ._env import get_env_float, get_env_int
from .settings import current

_logger = logging.getLogger("odoo.service.server")
_access_logger = logging.getLogger("odoo.service.http.access")
_debug = DebugLog(__name__)

WSGIApp = Callable[[dict[str, Any], Callable[..., Any]], Iterable[bytes]]

REQUEST_THREAD_PREFIX = "odoo.service.http.request."
_SEND_SLICE = 65536
_PEER_GONE = (BrokenPipeError, ConnectionResetError, ConnectionAbortedError)
_CONTROL_CHARS = str.maketrans(
    {c: rf"\x{c:02x}" for c in [*range(0x20), *range(0x7F, 0xA0)]} | {ord("\\"): r"\\"}
)
_MONTHS = (
    "",
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)
_ANSI = {
    "bold": "1",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "magenta": "35",
    "cyan": "36",
}


def get_http_socket_timeout() -> float:
    return get_env_float("ODOO_HTTP_SOCKET_TIMEOUT", 2.0, minimum=0.1, logger=_logger)


@dataclass(frozen=True, slots=True)
class TransportLimits:
    socket_timeout: float
    keepalive_timeout: float
    head_timeout: float
    drain_bytes: int
    drain_seconds: float
    linger_seconds: float
    max_idle_connections: int
    head: HeadLimits = field(default_factory=HeadLimits)
    body: BodyLimits = field(default_factory=BodyLimits)

    @classmethod
    def from_environment(cls) -> TransportLimits:
        timeout = get_http_socket_timeout()
        if current().test_enable:
            timeout = max(timeout, 5.0)
        limits = cls(
            socket_timeout=timeout,
            keepalive_timeout=get_env_float(
                "ODOO_HTTP_KEEPALIVE_TIMEOUT", 75.0, minimum=0.0, logger=_logger
            ),
            head_timeout=get_env_float(
                "ODOO_HTTP_HEAD_TIMEOUT", 10.0, minimum=0.1, logger=_logger
            ),
            drain_bytes=get_env_int(
                "ODOO_HTTP_DRAIN_BYTES", 1 << 20, minimum=0, logger=_logger
            ),
            drain_seconds=1.0,
            linger_seconds=2.0,
            max_idle_connections=get_env_int(
                "ODOO_HTTP_MAX_IDLE_CONNECTIONS", 4096, minimum=0, logger=_logger
            ),
        )
        _debug.lifecycle(
            "httpd.limits_resolved",
            socket_timeout=limits.socket_timeout,
            keepalive_timeout=limits.keepalive_timeout,
            head_timeout=limits.head_timeout,
            drain_bytes=limits.drain_bytes,
            max_idle_connections=limits.max_idle_connections,
            test_enable=current().test_enable,
        )
        return limits


class Outcome(Enum):
    PERSIST = "persist"
    CLOSE = "close"
    UPGRADED = "upgraded"


class Connection:
    __slots__ = (
        "addr",
        "closed",
        "deadline",
        "head_started",
        "idle_since",
        "ready_at",
        "requests",
        "sock",
        "source",
    )

    def __init__(self, sock: socket.socket, addr: Any) -> None:
        self.sock = sock
        self.addr = addr if isinstance(addr, tuple) else ("<local>", 0)
        self.source = BufferedSource(sock.recv)
        self.deadline = 0.0
        self.head_started = False
        self.idle_since = time.monotonic()
        self.ready_at = self.idle_since
        self.requests = 0
        self.closed = False

    def send(self, data: bytes) -> None:
        if len(data) <= _SEND_SLICE:
            self.sock.sendall(data)
            return
        view = memoryview(data)
        for offset in range(0, len(view), _SEND_SLICE):
            self.sock.sendall(view[offset : offset + _SEND_SLICE])

    def close(self, *, linger: float = 0.0) -> None:
        if self.closed:
            return
        self.closed = True
        _debug.lifecycle(
            "httpd.connection_closed",
            peer=self.addr[0],
            requests=self.requests,
            linger=linger,
            buffered=len(self.source.buffer),
        )
        with contextlib.suppress(OSError):
            self.sock.shutdown(socket.SHUT_WR)
        if linger > 0:
            deadline = time.monotonic() + linger
            with contextlib.suppress(OSError):
                self.sock.settimeout(linger)
                while time.monotonic() < deadline and self.sock.recv(65536):
                    pass
        with contextlib.suppress(OSError):
            self.sock.close()


def _style(message: str, *styles: str) -> str:
    if not root_handler_uses_colors():
        return message
    codes = ";".join(_ANSI[s] for s in styles)
    return f"\x1b[{codes}m{message}\x1b[0m"


def get_access_log_level(raw_path: str) -> int:
    # The settings read is the expensive half; only a static path needs it.
    if "/static/" in raw_path and not current().dev_mode:
        return logging.DEBUG
    return logging.INFO


def log_access(
    conn: Connection,
    request_line: str,
    raw_path: str,
    status: int,
    size: int | str,
    *,
    level: int | None = None,
) -> None:
    if level is None:
        level = get_access_log_level(raw_path)
    if not _access_logger.isEnabledFor(level):
        return
    message = request_line
    if fragment := getattr(current_worker_thread(), "rpc_model_method", ""):
        target, _, protocol = request_line.rpartition(" ")
        if target and protocol.startswith("HTTP/"):
            message = f"{target}#{fragment} {protocol}"
        else:
            message = f"{request_line}#{fragment}"
    message = message.translate(_CONTROL_CHARS)
    if level == logging.INFO:
        if status < 200:
            message = _style(message, "bold")
        elif status == 304:
            message = _style(message, "cyan")
        elif 300 <= status < 400:
            message = _style(message, "green")
        elif status == 404:
            message = _style(message, "yellow")
        elif 400 <= status < 500:
            message = _style(message, "bold", "red")
        elif status >= 500:
            message = _style(message, "bold", "magenta")
    now = time.localtime()
    stamp = (
        f"{now.tm_mday:02d}/{_MONTHS[now.tm_mon]}/{now.tm_year:04d} "
        f"{now.tm_hour:02d}:{now.tm_min:02d}:{now.tm_sec:02d}"
    )
    # Record args are werkzeug's (request line, status, size): access-log filters
    # match on args[0], and an IPv6 zone id carries a literal %.
    address = str(conn.addr[0]).replace("%", "%%")
    template = address + " - - [" + stamp + '] "%s" %s %s'
    _access_logger.log(level, template, message, status, size)


def _reset_request_attributes() -> None:
    worker = current_worker_thread()
    worker.rpc_model_method = ""
    worker.request_line = ""
    for attr in ("query_count", "request_id"):
        if hasattr(worker, attr):
            delattr(worker, attr)


@dataclass(frozen=True, slots=True)
class ServerIdentity:
    name: str
    port: int
    multithread: bool
    multiprocess: bool
    exposes_socket: bool
    on_request: Callable[[str], None] | None = None
    """Told the request line as each exchange starts, and "" as it ends.  A
    prefork worker puts it in its process title, where the master's timeout
    log and `ps` can read it; a threaded server needs nothing, the thread
    carries it."""


def prepare_wsgi_environ(
    head: RequestHead,
    conn: Connection,
    reader: BodyReader,
    identity: ServerIdentity,
) -> dict[str, Any]:
    environ: dict[str, Any] = {
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": "http",
        "wsgi.input": reader,
        "wsgi.errors": sys.stderr,
        "wsgi.multithread": identity.multithread,
        "wsgi.multiprocess": identity.multiprocess,
        "wsgi.run_once": False,
        "SERVER_SOFTWARE": "Odoo",
        "REQUEST_METHOD": head.method,
        "SCRIPT_NAME": "",
        "PATH_INFO": head.path,
        "QUERY_STRING": head.query,
        "REQUEST_URI": head.target,
        "RAW_URI": head.target,
        "REMOTE_ADDR": conn.addr[0],
        "REMOTE_PORT": str(conn.addr[1]),
        "SERVER_NAME": identity.name,
        "SERVER_PORT": str(identity.port),
        "SERVER_PROTOCOL": head.protocol,
    }
    for name, value in head.headers:
        if "_" in name:
            continue
        key = name.upper().replace("-", "_")
        if key == "CONTENT_LENGTH":
            if head.chunked:
                continue
        elif key != "CONTENT_TYPE":
            key = f"HTTP_{key}"
            if key in environ:
                value = f"{environ[key]},{value}"
        environ[key] = value
    if identity.exposes_socket:
        environ["odoo.socket"] = conn.sock
    if head.host is not None:
        environ["HTTP_HOST"] = head.host
    if head.chunked:
        environ["wsgi.input_terminated"] = True
    return environ


class Exchange:
    __slots__ = (
        "bytes_sent",
        "conn",
        "head",
        "keep_alive",
        "reader",
        "response",
        "response_headers",
        "status",
        "upgraded",
    )

    def __init__(
        self, conn: Connection, head: RequestHead, *, keep_alive: bool
    ) -> None:
        self.conn = conn
        self.head = head
        self.keep_alive = keep_alive
        self.reader: BodyReader = LengthReader(conn.source, 0)
        self.status: str | None = None
        self.response_headers: list[tuple[str, str]] = []
        self.response: ResponseHead | None = None
        self.bytes_sent = 0
        self.upgraded = False

    def start_response(
        self,
        status: str,
        headers: list[tuple[str, str]],
        exc_info: Any = None,
    ) -> Callable[[bytes], None]:
        if exc_info is not None:
            try:
                if self.response is not None:
                    raise exc_info[1].with_traceback(exc_info[2])
                _debug.logic(
                    "httpd.start_response_replaced",
                    previous=self.status,
                    status=status,
                    error=getattr(exc_info[0], "__name__", None),
                )
            finally:
                exc_info = None
        elif self.status is not None:
            raise AssertionError("start_response called twice without exc_info")
        self.status = status
        self.response_headers = list(headers)
        return self.write

    def continue_upload(self) -> None:
        if self.response is None:
            _debug.pipeline("httpd.continue_sent", path=self.head.path)
            self.conn.send(b"HTTP/1.1 100 Continue\r\n\r\n")

    def _send_head(self, first: bytes) -> None:
        if self.status is None:
            raise AssertionError("write() before start_response")
        self.response = prepare_response_head(
            self.status,
            self.response_headers,
            method=self.head.method,
            version=self.head.version,
            keep_alive=self.keep_alive,
        )
        if self.response.code == 101:
            self.upgraded = True
            self.conn.sock.settimeout(None)
        _log_exchange(self)
        _debug.pipeline(
            "httpd.head_sent",
            status=self.response.code,
            framing=self.response.framing.name,
            content_length=self.response.content_length,
            keep_alive=self.response.keep_alive,
            upgraded=self.upgraded,
            first_bytes=len(first),
        )
        self.conn.send(self.response.data + self._frame(first))

    def _frame(self, data: bytes) -> bytes:
        response = self.response
        assert response is not None
        if not data or response.framing is Framing.NONE:
            return b""
        if response.framing is Framing.CHUNKED:
            self.bytes_sent += len(data)
            return encode_chunk(data)
        if response.framing is Framing.LENGTH:
            assert response.content_length is not None
            room = response.content_length - self.bytes_sent
            if len(data) > room:
                _logger.warning(
                    "%s %s wrote more than its Content-Length (%s); truncating",
                    self.head.method,
                    self.head.path,
                    response.content_length,
                )
                _debug.logic(
                    "httpd.content_length_overrun",
                    path=self.head.path,
                    content_length=response.content_length,
                    overrun=len(data) - room,
                )
                data = data[: max(room, 0)]
        self.bytes_sent += len(data)
        return data

    def write(self, data: bytes) -> None:
        if self.response is None:
            self._send_head(data)
        elif data := self._frame(data):
            self.conn.send(data)

    def finish(self) -> None:
        if self.response is None:
            self._send_head(b"")
        response = self.response
        assert response is not None
        if response.framing is Framing.CHUNKED:
            self.conn.send(LAST_CHUNK)

    @property
    def complete(self) -> bool:
        response = self.response
        if response is None:
            return False
        if response.framing is Framing.LENGTH:
            return self.bytes_sent == response.content_length
        return response.framing is not Framing.CLOSE


def _error_response(
    conn: Connection, status: HTTPStatus, detail: str, *, method: str = "GET"
) -> int:
    body = f"{status.value} {status.phrase}: {detail}\n".encode()
    head = prepare_response_head(
        f"{status.value} {status.phrase}",
        [
            ("Content-Type", "text/plain; charset=utf-8"),
            ("Content-Length", str(len(body))),
        ],
        method=method,
        version=(1, 1),
        keep_alive=False,
    )
    if method == "HEAD":
        body = b""
    _debug.pipeline(
        "httpd.error_response",
        status=status.value,
        peer=conn.addr[0],
        requests=conn.requests,
    )
    with contextlib.suppress(OSError):
        conn.send(head.data + body)
    return len(body)


def _read_head(conn: Connection, limits: TransportLimits) -> tuple[int, int] | None:
    deadline = time.monotonic() + limits.head_timeout
    scanned = 0
    while (span := find_head(conn.source.buffer, limits.head, scanned)) is None:
        scanned = len(conn.source.buffer)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ProtocolError(
                HTTPStatus.REQUEST_TIMEOUT, "request head not received in time"
            )
        conn.sock.settimeout(min(limits.socket_timeout, remaining))
        try:
            if not conn.source.receive_into_buffer():
                return None
        except TimeoutError:
            # A pause inside the head is bounded by head_timeout, not by the
            # per-read socket timeout that governs a body or a response.
            continue
    conn.sock.settimeout(limits.socket_timeout)
    return span


def _first_line(buffer: bytearray) -> str:
    line = bytes(buffer[: buffer.find(b"\n")] if b"\n" in buffer else buffer[:200])
    return line.rstrip(b"\r").decode("latin-1")


def serve_one(
    conn: Connection,
    app: WSGIApp,
    identity: ServerIdentity,
    limits: TransportLimits,
    *,
    allow_keep_alive: bool,
) -> Outcome:
    try:
        span = _read_head(conn, limits)
        if span is None:
            _debug.logic(
                "httpd.peer_closed_before_head",
                peer=conn.addr[0],
                requests=conn.requests,
                buffered=len(conn.source.buffer),
            )
            return Outcome.CLOSE
        head = parse_request_head(
            bytes(conn.source.buffer[span[0] : span[1]]), limits.head
        )
    except ProtocolError as exc:
        _reset_request_attributes()
        line = _first_line(conn.source.buffer)
        size = _error_response(
            conn, exc.status, exc.detail, method=line.partition(" ")[0]
        )
        log_access(conn, line or "-", "", exc.status.value, size)
        _debug.logic("httpd.protocol_error", status=exc.status.value, detail=exc.detail)
        return Outcome.CLOSE
    except OSError as exc:
        _debug.logic(
            "httpd.head_read_failed",
            peer=conn.addr[0],
            requests=conn.requests,
            error=type(exc).__name__,
        )
        return Outcome.CLOSE
    del conn.source.buffer[: span[1]]
    conn.requests += 1
    _debug.pipeline(
        "httpd.request_parsed",
        method=head.method,
        path=head.path,
        protocol=head.protocol,
        chunked=head.chunked,
        content_length=head.content_length,
        expect_continue=head.expect_continue,
        keep_alive=head.keep_alive and allow_keep_alive and not head.must_close,
        request_on_connection=conn.requests,
        leftover=len(conn.source.buffer),
    )
    return _run_exchange(
        conn, head, app, identity, limits, allow_keep_alive=allow_keep_alive
    )


def _open_reader(
    conn: Connection,
    head: RequestHead,
    limits: TransportLimits,
    exchange: Exchange,
) -> BodyReader:
    on_first_read = exchange.continue_upload if head.expect_continue else None
    if head.chunked:
        return ChunkedReader(conn.source, limits.body, on_first_read)
    return LengthReader(conn.source, head.content_length or 0, on_first_read)


def _run_exchange(
    conn: Connection,
    head: RequestHead,
    app: WSGIApp,
    identity: ServerIdentity,
    limits: TransportLimits,
    *,
    allow_keep_alive: bool,
) -> Outcome:
    exchange = Exchange(
        conn,
        head,
        keep_alive=head.keep_alive and allow_keep_alive and not head.must_close,
    )
    exchange.reader = _open_reader(conn, head, limits, exchange)
    environ = prepare_wsgi_environ(head, conn, exchange.reader, identity)
    request_line = f"{head.method} {head.target}"
    current_worker_thread().request_line = request_line
    if identity.on_request is not None:
        identity.on_request(request_line)
    iterable: Iterable[bytes] | None = None
    try:
        iterable = app(environ, exchange.start_response)
        for data in iterable:
            if data:
                exchange.write(data)
        exchange.finish()
    except (TimeoutError, *_PEER_GONE) as exc:
        _debug.logic("httpd.peer_gone", error=type(exc).__name__, path=head.path)
        _close_iterable(iterable)
        return Outcome.CLOSE
    except Exception as exc:
        _logger.exception(
            "Exception happened during processing of request from %s", conn.addr
        )
        _debug.logic(
            "httpd.app_failed",
            path=head.path,
            error=type(exc).__name__,
            head_sent=exchange.response is not None,
            bytes_sent=exchange.bytes_sent,
        )
        if exchange.response is None:
            exchange.status = None
            size = _error_response(
                conn,
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "internal error",
                method=head.method,
            )
            log_access(
                conn,
                f"{head.method} {head.target} {head.protocol}",
                head.path,
                500,
                size,
            )
        _close_iterable(iterable)
        return Outcome.CLOSE
    if _debug.perf.enabled:
        _debug.perf.count(
            "httpd.exchange",
            ms=(time.monotonic() - conn.ready_at) * 1000.0,
            status=exchange.response.code if exchange.response else 0,
            request_on_connection=conn.requests,
            path=head.path,
            bytes_sent=exchange.bytes_sent,
            body_read=exchange.reader.exhausted,
        )
    if identity.on_request is not None:
        identity.on_request("")
    if exchange.upgraded:
        if _debug.logic.enabled and conn.source.buffer:
            _debug.logic(
                "httpd.upgrade_with_buffered_bytes",
                bytes=len(conn.source.buffer),
                path=head.path,
            )
        _hand_off_upgrade(conn, iterable)
        return Outcome.UPGRADED
    _close_iterable(iterable)
    return _settle(exchange, limits, allow_keep_alive=allow_keep_alive)


def _log_exchange(exchange: Exchange) -> None:
    head = exchange.head
    level = get_access_log_level(head.target)
    if not _access_logger.isEnabledFor(level):
        return
    try:
        iri = uri_to_iri(head.target)
    except ValueError:
        iri = head.target
    response = exchange.response
    assert response is not None
    size: int | str = "-"
    if response.content_length is not None and response.framing is Framing.LENGTH:
        size = response.content_length
    log_access(
        exchange.conn,
        f"{head.method} {iri} {head.protocol}",
        head.target,
        response.code,
        size,
        level=level,
    )


def _close_iterable(iterable: Iterable[bytes] | None) -> None:
    close = getattr(iterable, "close", None)
    if close is not None:
        try:
            close()
        except Exception:
            _logger.exception("error while closing the response iterable")


def _hand_off_upgrade(conn: Connection, iterable: Iterable[bytes] | None) -> None:
    def run() -> None:
        me = threading.current_thread()
        me.name = f"{REQUEST_THREAD_PREFIX}{me.ident}"
        _debug.lifecycle(
            "httpd.upgrade_thread_started", peer=conn.addr[0], thread=me.name
        )
        try:
            _close_iterable(iterable)
        finally:
            conn.close()
            _debug.lifecycle("httpd.upgrade_thread_finished", peer=conn.addr[0])

    threading.Thread(target=run, daemon=True).start()


def _settle(
    exchange: Exchange, limits: TransportLimits, *, allow_keep_alive: bool
) -> Outcome:
    response = exchange.response
    assert response is not None
    head = exchange.head
    persist = (
        allow_keep_alive
        and response.keep_alive
        and exchange.complete
        and not head.must_close
    )
    reader = exchange.reader
    if _debug.logic.enabled and not persist:
        _debug.logic(
            "httpd.connection_not_persisted",
            path=head.path,
            allow_keep_alive=allow_keep_alive,
            response_keep_alive=response.keep_alive,
            complete=exchange.complete,
            must_close=head.must_close,
        )
    if reader.exhausted:
        return Outcome.PERSIST if persist else Outcome.CLOSE
    drained = False
    if persist:
        try:
            drained = reader.drain(
                limits.drain_bytes, time.monotonic() + limits.drain_seconds
            )
        except OSError:
            drained = False
    _debug.logic("httpd.body_unread", drained=drained, persist=persist, path=head.path)
    if drained:
        return Outcome.PERSIST
    exchange.conn.close(linger=limits.linger_seconds)
    return Outcome.CLOSE


def serve_prefork_connection(
    sock: socket.socket,
    addr: Any,
    app: WSGIApp,
    identity: ServerIdentity,
    limits: TransportLimits,
) -> Outcome:
    conn = Connection(sock, addr)
    outcome = Outcome.CLOSE
    try:
        outcome = serve_one(conn, app, identity, limits, allow_keep_alive=False)
    finally:
        # An upgrade handed the socket to its own thread, which closes it.
        if outcome is not Outcome.UPGRADED:
            conn.close()
    return outcome


__all__ = (
    "REQUEST_THREAD_PREFIX",
    "Connection",
    "Exchange",
    "Outcome",
    "ServerIdentity",
    "TransportLimits",
    "WSGIApp",
    "find_head",
    "get_access_log_level",
    "get_http_socket_timeout",
    "log_access",
    "prepare_wsgi_environ",
    "serve_one",
    "serve_prefork_connection",
)
