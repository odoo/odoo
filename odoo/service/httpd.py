from __future__ import annotations

import contextlib
import errno
import logging
import os
import selectors
import socket
import sys
import threading
import time
from collections import deque
from collections.abc import Callable
from typing import TYPE_CHECKING

from odoo.libs.debug_log import DebugLog
from odoo.libs.http1 import ProtocolError, find_head
from odoo.libs.worker_thread import as_worker_thread

from ._env import bequeath_socket, get_env_int, take_inherited_socket
from ._transport import (
    REQUEST_THREAD_PREFIX,
    Connection,
    Outcome,
    ServerIdentity,
    TransportLimits,
    WSGIApp,
    serve_one,
)
from .settings import SD_LISTEN_FDS_START, adopt_activated_socket, current

if TYPE_CHECKING:
    from .settings import ServerSettings

_logger = logging.getLogger("odoo.service.server")
_debug = DebugLog(__name__)

IDLE_THREAD_PREFIX = "odoo.service.http.idle."
_MAX_PIPELINED = 16
_ACCEPT_BACKOFF = 0.1
_RESOURCE_WARNING_INTERVAL = 60.0
_RESOURCE_ERRNOS = frozenset({errno.EMFILE, errno.ENFILE, errno.ENOBUFS, errno.ENOMEM})


def compute_http_thread_limit(settings: ServerSettings) -> tuple[int, int]:
    auto_limit = max(
        (settings.db_maxconn - settings.max_cron_threads - settings.job_workers) // 2, 1
    )
    limit = get_env_int("ODOO_MAX_HTTP_THREADS", auto_limit, minimum=0, logger=_logger)
    _debug.logic(
        "httpd.thread_limit",
        limit=limit,
        auto_limit=auto_limit,
        source="env" if limit != auto_limit else "db_maxconn",
        db_maxconn=settings.db_maxconn,
    )
    return limit, auto_limit


def announce_thread_budget(
    settings: ServerSettings, limit: int, auto_limit: int
) -> None:
    if not limit:
        _logger.info(
            "HTTP concurrency is unbounded (ODOO_MAX_HTTP_THREADS=0); "
            "in-flight requests are limited only by db_maxconn=%s",
            settings.db_maxconn,
        )
        return
    source = (
        "ODOO_MAX_HTTP_THREADS"
        if limit != auto_limit
        else "(db_maxconn %s - max_cron_threads %s - job_workers %s) // 2"
        % (settings.db_maxconn, settings.max_cron_threads, settings.job_workers)
    )
    log = _logger.warning if limit < 4 else _logger.info
    log(
        "At most %d HTTP request(s) will be served concurrently, from %s. "
        "Further requests wait in the connection queue; set "
        "ODOO_MAX_HTTP_THREADS to decouple this from the pool size.",
        limit,
        source,
    )


class WorkerPool:
    def __init__(
        self,
        limit: int | None,
        target: Callable[[Connection], None],
        on_unsaturated: Callable[[], None] | None = None,
    ) -> None:
        self.limit = limit
        self._target = target
        self._on_unsaturated = on_unsaturated
        self._jobs: deque[Connection] = deque()
        self._cond = threading.Condition()
        self._threads = 0
        self._idle = 0
        self._busy = 0
        self._closed = False
        self.idle_timeout = 60.0

    @property
    def busy(self) -> int:
        return self._busy

    @property
    def saturated(self) -> bool:
        return self.limit is not None and len(self._jobs) >= self.limit

    def submit(self, conn: Connection) -> bool:
        with self._cond:
            if self._closed:
                _debug.logic("httpd.submit_refused", reason="closed")
                return False
            self._jobs.append(conn)
            if self._idle > len(self._jobs) - 1:
                self._cond.notify()
                return True
            if self.limit is not None and self._threads >= self.limit:
                _debug.logic(
                    "httpd.submit_queued",
                    queued=len(self._jobs),
                    threads=self._threads,
                    busy=self._busy,
                    limit=self.limit,
                )
                return True
            thread = threading.Thread(target=self._run, daemon=True)
            try:
                thread.start()
            except RuntimeError as exc:
                self._jobs.pop()
                _debug.logic(
                    "httpd.submit_refused",
                    reason="thread_start_failed",
                    threads=self._threads,
                    error=type(exc).__name__,
                )
                return False
            self._threads += 1
            _debug.lifecycle(
                "httpd.worker_thread_started",
                threads=self._threads,
                idle=self._idle,
                queued=len(self._jobs),
                limit=self.limit,
            )
            return True

    def _next(self) -> Connection | None:
        with self._cond:
            while not self._jobs:
                if self._closed:
                    self._threads -= 1
                    _debug.lifecycle(
                        "httpd.worker_thread_retired",
                        reason="closed",
                        threads=self._threads,
                    )
                    return None
                self._idle += 1
                woke = self._cond.wait(self.idle_timeout)
                self._idle -= 1
                if not woke and not self._jobs:
                    self._threads -= 1
                    _debug.lifecycle(
                        "httpd.worker_thread_retired",
                        reason="idle_timeout",
                        idle_timeout=self.idle_timeout,
                        threads=self._threads,
                    )
                    return None
            self._busy += 1
            conn = self._jobs.popleft()
            crossed = self.limit is not None and len(self._jobs) == self.limit - 1
        if crossed and self._on_unsaturated is not None:
            _debug.pipeline("httpd.pool_unsaturated", limit=self.limit, busy=self._busy)
            self._on_unsaturated()
        return conn

    def _run(self) -> None:
        me = threading.current_thread()
        idle_name = f"{IDLE_THREAD_PREFIX}{me.ident}"
        busy_name = f"{REQUEST_THREAD_PREFIX}{me.ident}"
        me.name = idle_name
        worker = as_worker_thread(me)
        while (conn := self._next()) is not None:
            me.name = busy_name
            worker.type = "http"
            worker.start_time = time.monotonic()
            if _debug.perf.enabled:
                _debug.perf.count(
                    "httpd.dispatch",
                    queue_ms=(worker.start_time - getattr(conn, "ready_at", 0.0))
                    * 1000.0,
                    request_on_connection=getattr(conn, "requests", 0) + 1,
                    busy=self._busy,
                )
            try:
                self._target(conn)
            except Exception as exc:
                _logger.exception("unhandled error in HTTP worker")
                _debug.logic(
                    "httpd.worker_failed",
                    error=type(exc).__name__,
                    requests=getattr(conn, "requests", None),
                )
                conn.close()
            finally:
                worker.type = "http_idle"
                worker.start_time = None
                me.name = idle_name
                with self._cond:
                    self._busy -= 1

    def close(self) -> list[Connection]:
        with self._cond:
            self._closed = True
            pending = list(self._jobs)
            self._jobs.clear()
            self._cond.notify_all()
            _debug.lifecycle(
                "httpd.pool_closed",
                pending=len(pending),
                threads=self._threads,
                busy=self._busy,
            )
        return pending


_THREAD_EXHAUSTION_RESPONSE = b"HTTP/1.1 503 Service Unavailable\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"


class ThreadedHTTPServer:
    def __init__(
        self, host: str, port: int, app: WSGIApp, *, announce: bool = True
    ) -> None:
        self.settings = current()
        self.app = app
        self.limits = TransportLimits.from_environment()
        self.max_http_threads, auto_limit = compute_http_thread_limit(self.settings)
        announce_thread_budget(self.settings, self.max_http_threads, auto_limit)
        self.socket, self.listener_outlives_exec = self._bind(
            host, port, announce=announce
        )
        self.server_address = self.socket.getsockname()[:2]
        self.server_name, self.server_port = (
            self.server_address[0],
            self.server_address[1],
        )
        self.identity = ServerIdentity(
            self.server_name,
            self.server_port,
            multithread=True,
            multiprocess=False,
            exposes_socket=True,
        )
        self._pool = WorkerPool(
            self.max_http_threads or None, self._serve_connection, self._wake
        )
        self._selector = selectors.DefaultSelector()
        self._wake_r, self._wake_w = socket.socketpair()
        self._wake_r.setblocking(False)
        self._wake_w.setblocking(False)
        self._returned: deque[Connection] = deque()
        self._returned_lock = threading.Lock()
        self._idle: dict[int, Connection] = {}
        self._shutdown = threading.Event()
        self._stopped = threading.Event()
        self._stopped.set()
        self._listening = False
        self._accept_paused_until = 0.0
        self._resource_warned_at = -_RESOURCE_WARNING_INTERVAL
        _debug.lifecycle(
            "httpd.server_created",
            host=host,
            port=self.server_port,
            max_http_threads=self.max_http_threads,
            outlives_exec=self.listener_outlives_exec,
        )

    @staticmethod
    def _bind(
        host: str, port: int, *, announce: bool = True
    ) -> tuple[socket.socket, bool]:
        if inherited := take_inherited_socket():
            inherited.setblocking(False)
            if announce:
                _logger.info(
                    "HTTP service serving %s:%s on the listening socket inherited "
                    "from the server this one replaced; the port was never closed",
                    *inherited.getsockname()[:2],
                )
            _debug.lifecycle("httpd.bound", source="inherited", fd=inherited.fileno())
            return inherited, True
        if current().http_socket_activation:
            sock = adopt_activated_socket(SD_LISTEN_FDS_START)
            if announce:
                _logger.info("HTTP service running through socket activation")
            sock.setblocking(False)
            _debug.lifecycle(
                "httpd.bound", source="socket_activation", fd=SD_LISTEN_FDS_START
            )
            return sock, True
        family = socket.AF_INET6 if ":" in host else socket.AF_INET
        sock = socket.socket(family, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError as exc:
            sock.close()
            _debug.logic(
                "httpd.bind_failed",
                host=host,
                port=port,
                errno=exc.errno,
                error=type(exc).__name__,
            )
            sys.stderr.write(
                f"{exc.strerror or exc}\nPort {port} is in use by another program. "
                "Either identify and stop that program, or start the server with a "
                "different port.\n"
            )
            raise SystemExit(1) from exc
        sock.listen(socket.SOMAXCONN)
        sock.setblocking(False)
        if announce:
            _logger.info("HTTP service running on %s:%s", *sock.getsockname()[:2])
        _debug.lifecycle(
            "httpd.bound",
            source="bind",
            family=family.name,
            host=host,
            port=sock.getsockname()[1],
            backlog=socket.SOMAXCONN,
        )
        return sock, False

    def _serve_connection(self, conn: Connection) -> None:
        served = 0  # debuglog
        capped = False  # debuglog
        for _ in range(_MAX_PIPELINED):
            outcome = serve_one(
                conn,
                self.app,
                self.identity,
                self.limits,
                allow_keep_alive=not self._shutdown.is_set(),
            )
            served += 1  # debuglog
            if outcome is Outcome.UPGRADED:
                _debug.pipeline(
                    "httpd.connection_upgraded", peer=conn.addr[0], served=served
                )
                return
            if outcome is Outcome.CLOSE:
                conn.close()
                return
            if not self._holds_complete_head(conn):
                break
            _debug.pipeline(
                "httpd.pipelined_request_served_inline",
                peer=conn.addr[0],
                served=served,
                buffered=len(conn.source.buffer),
            )
            conn.ready_at = time.monotonic()
            capped = served == _MAX_PIPELINED  # debuglog
        if _debug.logic.enabled and capped:
            _debug.logic(
                "httpd.pipeline_cap_reached",
                peer=conn.addr[0],
                served=served,
                cap=_MAX_PIPELINED,
            )
        with self._returned_lock:
            if self._stopped.is_set():
                _debug.logic(
                    "httpd.connection_closed_after_stop",
                    peer=conn.addr[0],
                    served=served,
                )
                conn.close()
                return
            self._returned.append(conn)
        _debug.pipeline(
            "httpd.connection_returned",
            peer=conn.addr[0],
            served=served,
            requests=conn.requests,
        )
        with contextlib.suppress(OSError):
            self._wake_w.send(b"\0")

    def _wake(self) -> None:
        with contextlib.suppress(OSError):
            self._wake_w.send(b"\0")

    def _dispatch(self, conn: Connection) -> None:
        self._selector.unregister(conn.sock)
        self._idle.pop(conn.sock.fileno(), None)
        self._submit(conn)

    def _submit(self, conn: Connection) -> None:
        conn.ready_at = time.monotonic()
        conn.sock.setblocking(True)
        conn.sock.settimeout(self.limits.socket_timeout)
        if not self._pool.submit(conn):
            _logger.warning(
                "could not start an HTTP worker thread; answering %s with 503",
                conn.addr,
            )
            _debug.logic(
                "httpd.thread_exhausted",
                peer=conn.addr[0],
                busy=self._pool.busy,
                limit=self.max_http_threads,
            )
            with contextlib.suppress(OSError):
                conn.sock.sendall(_THREAD_EXHAUSTION_RESPONSE)
            conn.close()

    def _park(self, conn: Connection, now: float) -> None:
        conn.sock.setblocking(False)
        conn.head_started = bool(conn.source.buffer.strip(b"\r\n"))
        conn.idle_since = now
        conn.deadline = now + (
            self.limits.head_timeout
            if conn.head_started
            else self.limits.keepalive_timeout
        )
        self._idle[conn.sock.fileno()] = conn
        self._selector.register(conn.sock, selectors.EVENT_READ, conn)
        _debug.pipeline(
            "httpd.parked",
            peer=conn.addr[0],
            requests=conn.requests,
            head_started=conn.head_started,
            timeout=conn.deadline - now,
            idle=len(self._idle),
        )
        if len(self._idle) > self.limits.max_idle_connections:
            _debug.logic(
                "httpd.idle_over_limit",
                idle=len(self._idle),
                limit=self.limits.max_idle_connections,
            )
            self._evict_oldest_idle()

    def _evict_oldest_idle(self) -> bool:
        # _idle is keyed in parking order, so the first entries are the oldest. A
        # connection idle between requests goes first because its client reconnects
        # without losing anything; after that the oldest goes, whether it never sent
        # a byte or is part way through a head, or a slowloris client could hold
        # every slot while each newcomer is closed before it can speak.
        victim = next(
            (c for c in self._idle.values() if c.requests and not c.head_started),
            None,
        )
        if victim is None:
            victim = next(iter(self._idle.values()), None)
        if victim is None:
            _debug.logic("httpd.idle_eviction_empty")
            return False
        _debug.logic(
            "httpd.idle_evicted",
            peer=victim.addr[0],
            requests=victim.requests,
            head_started=victim.head_started,
            idle_s=time.monotonic() - victim.idle_since,
            idle=len(self._idle),
        )
        self._drop(victim)
        return True

    def _drop(self, conn: Connection) -> None:
        with contextlib.suppress(KeyError, ValueError):
            self._selector.unregister(conn.sock)
        self._idle.pop(conn.sock.fileno(), None)
        conn.close()

    def _accept(self, now: float) -> None:
        accepted = 0  # debuglog
        for _ in range(256):
            try:
                sock, addr = self.socket.accept()
            except BlockingIOError, InterruptedError:
                if _debug.pipeline.enabled and accepted:
                    _debug.pipeline(
                        "httpd.accepted", connections=accepted, idle=len(self._idle)
                    )
                return
            except OSError as exc:
                _debug.logic(
                    "httpd.accept_failed",
                    error=type(exc).__name__,
                    errno=exc.errno,
                    accepted=accepted,
                )
                if exc.errno in _RESOURCE_ERRNOS:
                    self._accept_starved(exc, now)
                return
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            accepted += 1  # debuglog
            self._park(Connection(sock, addr), now)
        _debug.logic("httpd.accept_batch_full", connections=accepted)

    def _accept_starved(self, exc: OSError, now: float) -> None:
        if now - self._resource_warned_at >= _RESOURCE_WARNING_INTERVAL:
            self._resource_warned_at = now
            _logger.warning(
                "cannot accept HTTP connections (%s) with %d idle and %d busy;"
                " closing idle connections to make room",
                exc.strerror or exc,
                len(self._idle),
                self._pool.busy,
            )
        # The listener stays readable while accept fails, so without freeing a
        # descriptor or leaving the selector the loop would spin on it.
        evicted = self._evict_oldest_idle()
        if not evicted:
            self._accept_paused_until = now + _ACCEPT_BACKOFF
        _debug.logic(
            "httpd.accept_starved",
            errno=exc.errno,
            idle=len(self._idle),
            busy=self._pool.busy,
            evicted=evicted,
            paused_s=0.0 if evicted else _ACCEPT_BACKOFF,
        )

    def _readable(self, conn: Connection, now: float) -> None:
        try:
            data = conn.sock.recv(65536)
        except BlockingIOError, InterruptedError:
            return
        except OSError as exc:
            _debug.logic(
                "httpd.idle_dropped",
                reason="recv_failed",
                peer=conn.addr[0],
                requests=conn.requests,
                error=type(exc).__name__,
            )
            self._drop(conn)
            return
        if not data:
            _debug.logic(
                "httpd.idle_dropped",
                reason="peer_closed",
                peer=conn.addr[0],
                requests=conn.requests,
                head_started=conn.head_started,
                idle_s=now - conn.idle_since,
            )
            self._drop(conn)
            return
        scanned = len(conn.source.buffer)
        conn.source.buffer += data
        if not conn.head_started and conn.source.buffer.strip(b"\r\n"):
            conn.head_started = True
            conn.deadline = now + self.limits.head_timeout
        if self._holds_complete_head(conn, scanned):
            _debug.pipeline(
                "httpd.head_complete",
                peer=conn.addr[0],
                requests=conn.requests,
                buffered=len(conn.source.buffer),
                waited_ms=(now - conn.idle_since) * 1000.0,
            )
            self._dispatch(conn)

    def _expire(self, now: float) -> None:
        for conn in [c for c in self._idle.values() if c.deadline <= now]:
            _debug.logic(
                "httpd.idle_expired",
                peer=conn.addr[0],
                requests=conn.requests,
                head_started=conn.head_started,
                idle_s=now - conn.idle_since,
                buffered=len(conn.source.buffer),
            )
            if conn.head_started:
                with contextlib.suppress(OSError):
                    conn.sock.send(
                        b"HTTP/1.1 408 Request Timeout\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
                    )
            self._drop(conn)

    def _take_returned(self, now: float) -> None:
        with contextlib.suppress(OSError):
            while self._wake_r.recv(4096):
                pass
        with self._returned_lock:
            returned = list(self._returned)
            self._returned.clear()
        if _debug.pipeline.enabled and returned:
            _debug.pipeline(
                "httpd.returned_taken",
                connections=len(returned),
                shutdown=self._shutdown.is_set(),
            )
        for conn in returned:
            if self._shutdown.is_set():
                conn.close()
            elif self._holds_complete_head(conn):
                # A pipelined head the worker left behind at _MAX_PIPELINED: no
                # byte will ever wake the selector for it, so it goes back to
                # the pool now rather than parking until the head timeout.
                _debug.pipeline(
                    "httpd.returned_head_resubmitted",
                    peer=conn.addr[0],
                    requests=conn.requests,
                    buffered=len(conn.source.buffer),
                )
                self._submit(conn)
            else:
                self._park(conn, now)

    def _holds_complete_head(self, conn: Connection, scanned: int = 0) -> bool:
        try:
            return find_head(conn.source.buffer, self.limits.head, scanned) is not None
        except ProtocolError as exc:
            # A malformed head is complete for dispatch: serve_one answers it.
            _debug.logic(
                "httpd.head_malformed_while_idle",
                peer=conn.addr[0],
                status=exc.status.value,
                buffered=len(conn.source.buffer),
            )
            return True

    def _update_listening(self) -> None:
        want = (
            not self._pool.saturated
            and not self._shutdown.is_set()
            and time.monotonic() >= self._accept_paused_until
        )
        if want and not self._listening:
            self._selector.register(self.socket, selectors.EVENT_READ, None)
            self._listening = True
            _debug.logic("httpd.listening", listening=True, busy=self._pool.busy)
        elif not want and self._listening:
            self._selector.unregister(self.socket)
            self._listening = False
            _debug.logic(
                "httpd.listening",
                listening=False,
                saturated=self._pool.saturated,
                shutdown=self._shutdown.is_set(),
                accept_paused=time.monotonic() < self._accept_paused_until,
                busy=self._pool.busy,
            )

    def serve_forever(self) -> None:
        self._stopped.clear()
        self._selector.register(self._wake_r, selectors.EVENT_READ, self._wake_r)
        next_expiry = 0.0
        _debug.lifecycle(
            "httpd.serving",
            port=self.server_port,
            max_http_threads=self.max_http_threads,
            thread=threading.current_thread().name,
        )
        try:
            while not self._shutdown.is_set():
                self._update_listening()
                timeout = 0.5
                if not self._listening and self._accept_paused_until:
                    timeout = max(
                        0.0, min(timeout, self._accept_paused_until - time.monotonic())
                    )
                for key, _ in self._selector.select(timeout=timeout):
                    now = time.monotonic()
                    if key.data is None:
                        self._accept(now)
                    elif key.data is self._wake_r:
                        self._take_returned(now)
                    else:
                        self._readable(key.data, now)
                now = time.monotonic()
                if now >= next_expiry:
                    self._expire(now)
                    next_expiry = now + 0.5
        finally:
            idle = list(self._idle.values())
            for conn in idle:
                self._drop(conn)
            pending = self._pool.close()
            for conn in pending:
                conn.close()
            with self._returned_lock:
                returned = list(self._returned)
                self._returned.clear()
                self._stopped.set()
            for conn in returned:
                conn.close()
            _debug.lifecycle(
                "httpd.stopped",
                idle_closed=len(idle),
                pending_closed=len(pending),
                returned_closed=len(returned),
                busy=self._pool.busy,
            )

    def shutdown(self) -> None:
        _debug.lifecycle(
            "httpd.shutdown_requested",
            idle=len(self._idle),
            busy=self._pool.busy,
            serving=not self._stopped.is_set(),
        )
        self._shutdown.set()
        with contextlib.suppress(OSError):
            self._wake_w.send(b"\0")
        self._stopped.wait()

    def bequeath_listener(self) -> None:
        # A re-exec keeps this process, its pid and every inheritable fd:
        # the listener stays bound through the interpreter restart and the
        # connections that arrive meanwhile wait in its backlog.  A
        # socket-activated listener already survives as LISTEN_FDS.
        if self.listener_outlives_exec:
            return
        fd = bequeath_socket(self.socket, os.environ)
        self.listener_outlives_exec = True
        _debug.lifecycle("httpd.listener_bequeathed", port=self.server_port, fd=fd)

    def server_close(self) -> None:
        _debug.lifecycle("httpd.server_closed", port=self.server_port)
        with contextlib.suppress(OSError):
            self.socket.close()
        for sock in (self._wake_r, self._wake_w):
            with contextlib.suppress(OSError):
                sock.close()

    @property
    def busy_workers(self) -> int:
        return self._pool.busy

    def drain(self, timeout: float, *, stuck: int = 0) -> int:
        # `shutdown()` stopped the listener and every idle connection; the
        # pool's busy threads are answering real requests, and closing the
        # socket under them is what a stop used to do to their clients.  The
        # caller names how many of the busy threads it has given up on.
        def pending() -> int:
            return max(self._pool.busy - stuck, 0)

        busy = pending()
        if not busy:
            return 0
        deadline = time.monotonic() + timeout
        _logger.info(
            "Waiting up to %.0fs for %d in-flight request(s) to finish", timeout, busy
        )
        _debug.lifecycle("httpd.draining", busy=busy, stuck=stuck, timeout=timeout)
        while pending() and time.monotonic() < deadline:
            time.sleep(0.05)
        remaining = pending()
        if remaining:
            _logger.warning(
                "%d request(s) still running %.0fs after the stop signal; "
                "closing the listener under them (ODOO_GRACEFUL_STOP_TIMEOUT)",
                remaining,
                timeout,
            )
        _debug.lifecycle(
            "httpd.drained",
            remaining=remaining,
            seconds=time.monotonic() - (deadline - timeout),
        )
        return remaining
