from __future__ import annotations

import contextlib
import errno
import logging
import os
import random
import select
import selectors
import signal
import socket
import threading
import time
from collections import deque
from typing import TYPE_CHECKING, Any, override

import psutil
import psycopg

if os.name == "posix":
    import fcntl
    import resource

try:
    from setproctitle import setproctitle
except ImportError:

    def setproctitle(x: str) -> None:
        return None


from odoo.db import PoolError
from odoo.libs.debug_log import DebugLog
from odoo.libs.worker_thread import as_worker_thread, current_worker_thread
from odoo.modules.registry import Registry

from ._cron import (
    CRON_LISTENER,
    CRON_POLL_INTERVAL_S,
    JOB_LISTENER,
    STREAM_HEARTBEAT_S,
    STREAM_LISTENER,
    CronListener,
    CronSchedule,
    ListenerKind,
    sweep_database,
    wait_for_notifies,
)
from ._env import get_env_int
from ._limits import describe_thread_work, empty_pipe, get_memory_over_soft_limit
from ._transport import (
    Outcome,
    ServerIdentity,
    TransportLimits,
    serve_prefork_connection,
)
from .settings import current

if TYPE_CHECKING:
    from .server import PreforkServer

_logger = logging.getLogger("odoo.service.server")
_debug = DebugLog(__name__)


class CpuTimeLimitExceeded(Exception):
    pass


WORKER_READY = b"R"

RECYCLE_CODES: dict[bytes, str] = {
    b"Q": "request_max",
    b"M": "memory_soft",
    b"C": "cpu_limit",
    b"A": "max_age",
    b"P": "parent_changed",
    b"S": "stalled",
}
"""Why a worker stopped, as one byte on the pipe its heartbeats already use.

Every one of these exits 0, deliberately -- a policy recycle is not a crash
and must not arm the respawn back-off -- and that is exactly why the master
could not tell them apart: `odoo_worker_exits_total` counted all six, plus
an ordinary clean exit, as `clean`.  A deployment leaking memory recycled a
worker every few minutes and the metric that exists to show it read flat.
"""

_RECYCLE_BYTES: dict[str, bytes] = {v: k for k, v in RECYCLE_CODES.items()}


_EPOLLEXCLUSIVE = getattr(select, "EPOLLEXCLUSIVE", 0)


def watch_accept(selector: selectors.BaseSelector, sock: socket.socket) -> bool:
    key = selector.register(sock, selectors.EVENT_READ)
    epoll = getattr(selector, "_selector", None)
    if not _EPOLLEXCLUSIVE or not isinstance(epoll, select.epoll):
        return False
    # Every worker sleeps on this one inherited socket; without EPOLLEXCLUSIVE
    # each connection wakes all of them and all but one accept EAGAIN.  The
    # flag is refused by EPOLL_CTL_MOD, so the fd is registered again.
    epoll.unregister(key.fd)
    epoll.register(key.fd, select.EPOLLIN | _EPOLLEXCLUSIVE)
    return True


class Worker:
    _CPU_LIMIT_JOIN_GRACE_S = 1.0

    _CANCEL_GRACE_S = 5.0
    """How long the main thread waits for the work thread to return after
    cancelling its queries before it ends the worker itself."""

    _listener_ready = True
    """Whether the last `sleep()` was woken by a watched fd other than its own
    wakeup pipe.  True until a first `sleep()` says otherwise, so a direct
    `process_work()` still does its work."""

    _polls_wakeup_pipe = True
    """Whether `start()` opens the selector `sleep()` waits on.  The cron
    worker waits on its listener's selector instead, with the wakeup pipe
    registered there."""

    _selector: selectors.BaseSelector | None = None

    pid: int | None = None
    """The child's pid: set by the master after `fork()` and by the child in
    `start()`; None on an object no process has yet become."""

    recycled_for: str | None = None
    """Which policy stopped this worker, as the master read it off the pipe."""

    def __init__(self, multi: PreforkServer) -> None:
        self.multi = multi
        self.watchdog_time = time.monotonic()
        self.watchdog_pipe = multi.open_pipe()
        try:
            self.wakeup_pipe = multi.open_pipe()
        except BaseException:
            for fd in self.watchdog_pipe:
                with contextlib.suppress(OSError):
                    os.close(fd)
            raise
        self.watchdog_timeout: float | None = multi.timeout
        self.ppid = os.getpid()
        self.alive = True
        self.ready = False
        self.request_max = multi.limit_request
        self.request_count = 0
        self.logger = _logger.getChild(self.__class__.__name__)
        _debug.lifecycle(
            "worker.created",
            kind=self.__class__.__name__,
            watchdog_timeout=self.watchdog_timeout,
            request_max=self.request_max,
        )

    def setproctitle(self, title: str = "") -> None:
        setproctitle(f"odoo: {self.__class__.__name__} {self.pid} {title}")

    @property
    def pipe_fds(self) -> tuple[int, int, int, int]:
        return (*self.watchdog_pipe, *self.wakeup_pipe)

    def close(self) -> None:
        _debug.lifecycle(
            "worker.closed",
            kind=self.__class__.__name__,
            pid=self.pid,
            requests=self.request_count,
        )
        for fd in self.pipe_fds:
            with contextlib.suppress(OSError):
                os.close(fd)

    def signal_handler(self, sig: int, frame: Any) -> None:
        self.alive = False

    def signal_time_expired_handler(self, sig: int, frame: Any) -> None:
        raise CpuTimeLimitExceeded(
            f"CPU time limit ({current().limit_time_cpu}s) exceeded"
        )

    @property
    def selector(self) -> selectors.BaseSelector:
        if self._selector is None:
            raise RuntimeError(f"{type(self).__name__} polls before start()")
        return self._selector

    def sleep(self) -> None:
        ready = self.selector.select(timeout=self.multi.beat)
        self._listener_ready = any(key.fd != self.wakeup_pipe[0] for key, _ in ready)
        empty_pipe(self.wakeup_pipe[0])

    def check_limits(self) -> None:
        Registry._evict_idle_registries()
        if self.ppid != os.getppid():
            self.logger.info("Parent changed")
            self.stop_for("parent_changed")
        if self.request_max > 0 and self.request_count >= self.request_max:
            self.logger.info("Max request (%s) reached.", self.request_count)
            self.stop_for("request_max")
        settings = current()
        memory = get_memory_over_soft_limit(
            self._process_handle, settings.limit_memory_soft
        )
        if memory is not None:
            self.logger.info("RSS memory soft-limit reached: %s bytes.", memory)
            self.stop_for("memory_soft")

        limit_time_cpu = settings.limit_time_cpu
        if limit_time_cpu > 0:
            r = resource.getrusage(resource.RUSAGE_SELF)
            cpu_time = r.ru_utime + r.ru_stime
            _soft, hard = resource.getrlimit(resource.RLIMIT_CPU)
            soft = int(cpu_time + limit_time_cpu)
            if hard != resource.RLIM_INFINITY and soft > hard:
                soft = hard
            resource.setrlimit(resource.RLIMIT_CPU, (soft, hard))
            _debug.perf.count(
                "worker.cpu_sampled",
                kind=self.__class__.__name__,
                pid=self.pid,
                cpu_s=cpu_time,
                soft_limit=soft,
                requests=self.request_count,
            )

    def stop_for(self, reason: str) -> None:
        """Stop, and put the reason on the wire before the exit reaches the
        master, which otherwise sees only the exit code every policy shares."""
        self.alive = False
        code = _RECYCLE_BYTES.get(reason)
        _debug.lifecycle(
            "worker.recycle",
            kind=self.__class__.__name__,
            pid=self.pid,
            reason=reason,
        )
        if code is not None:
            with contextlib.suppress(OSError):
                os.write(self.watchdog_pipe[1], code)

    def process_work(self) -> None:
        pass

    def start(self) -> None:
        self.pid = os.getpid()
        self.setproctitle()
        self.logger.info("Alive")
        _debug.lifecycle(
            "worker.start",
            kind=self.__class__.__name__,
            pid=self.pid,
            ppid=self.ppid,
            request_max=self.request_max,
        )
        random.seed()
        self._process_handle = psutil.Process(self.pid)
        if self.multi.socket:
            flags = fcntl.fcntl(self.multi.socket, fcntl.F_GETFD) | fcntl.FD_CLOEXEC
            fcntl.fcntl(self.multi.socket, fcntl.F_SETFD, flags)
            self.multi.socket.setblocking(False)

        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGXCPU, self.signal_time_expired_handler)

        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.signal(signal.SIGHUP, signal.SIG_DFL)
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)
        signal.signal(signal.SIGTTIN, signal.SIG_DFL)
        signal.signal(signal.SIGTTOU, signal.SIG_DFL)

        signal.set_wakeup_fd(self.wakeup_pipe[1])
        if self._polls_wakeup_pipe:
            self._selector = selectors.DefaultSelector()
            self._selector.register(self.wakeup_pipe[0], selectors.EVENT_READ)

    def stop(self) -> None:
        if self._selector is not None:
            self._selector.close()

    def run(self) -> None:
        self.start()
        self._runloop_exc: BaseException | None = None
        t = threading.Thread(
            name=f"Worker {self.__class__.__name__} ({self.pid}) workthread",
            target=self._run_work_loop,
            daemon=True,
        )
        t.start()
        try:
            stuck = self._supervise_work_thread(t)
            if self._runloop_exc is not None:
                raise SystemExit(1)
            if stuck:
                doing = describe_thread_work(t)
                self.logger.warning(
                    "Work did not return %.0fs after its queries were cancelled%s; "
                    "recycling worker. request_count: %s",
                    self._CANCEL_GRACE_S,
                    f" ({doing})" if doing else "",
                    self.request_count,
                )
            else:
                self.logger.info(
                    "Exiting cleanly. request_count: %s, registry count: %s.",
                    self.request_count,
                    len(Registry.registries),
                )
        except CpuTimeLimitExceeded:
            # The kernel keeps sending SIGXCPU once a second while the process
            # stays over the soft limit; the first one is the verdict, and a
            # second raise would escape this handler as a crash.
            signal.signal(signal.SIGXCPU, signal.SIG_IGN)
            self.logger.warning(
                "CPU time limit (%ss) exceeded; recycling worker.",
                current().limit_time_cpu,
            )
            self.stop_for("cpu_limit")
            t.join(timeout=self._CPU_LIMIT_JOIN_GRACE_S)
            if t.is_alive():
                self.logger.warning(
                    "Work thread still running %.1fs after CPU-limit stop; "
                    "exiting anyway.",
                    self._CPU_LIMIT_JOIN_GRACE_S,
                )
        finally:
            _debug.lifecycle(
                "worker.exit",
                kind=self.__class__.__name__,
                pid=self.pid,
                requests=self.request_count,
                failed=self._runloop_exc is not None,
            )
            self.stop()

    def _supervise_work_thread(self, work: threading.Thread) -> bool:
        # The main thread has nothing to do but wait, so it is the worker's
        # own budget monitor: a unit of work over `watchdog_timeout` has its
        # queries cancelled here, from inside the process.  Work still stuck
        # after the grace -- a stall in Python, not in a query -- ends the
        # worker itself, a clean exit the master replaces at once instead of
        # a SIGKILL a full timeout later.
        #
        # The master's clock is fed the whole way through: it last heard from
        # the work thread before the accept, up to a beat before the work
        # began, so left alone it ran out first in three of eight measured
        # phases, once before the budget itself had elapsed.  Fed from here,
        # its SIGKILL is reached only when this thread stops feeding it: the
        # grace ran out (the worker exits on its own) or the process is wedged.
        worker = as_worker_thread(work)
        cancelled_for: float | None = None
        grace_until = 0.0
        while work.is_alive():
            work.join(timeout=min(self.multi.beat, 1.0))
            budget = self.watchdog_timeout
            started = getattr(worker, "start_time", None)
            if not budget or not started:
                continue
            now = time.monotonic()
            if cancelled_for != started and now - started > budget:
                cancelled_for = started
                grace_until = now + self._CANCEL_GRACE_S
                self._cancel_work_thread_queries(work, now - started, budget)
            elif cancelled_for == started and now >= grace_until:
                self.stop_for("stalled")
                return True
            self.multi.ping_pipe(self.watchdog_pipe)
        return False

    def _cancel_work_thread_queries(
        self, work: threading.Thread, elapsed: float, budget: float
    ) -> None:
        from odoo import db

        try:
            cancelled = db.cancel_queries_of(work.name)
        except Exception as exc:
            _debug.logic("worker.cancel_failed", pid=self.pid, error=type(exc).__name__)
            cancelled = 0
        doing = describe_thread_work(work)
        self.logger.warning(
            "Work over its %ss budget (%.1fs)%s: cancelled %d running quer%s; "
            "recycling this worker if it does not return",
            budget,
            elapsed,
            f" while {doing}" if doing else "",
            cancelled,
            "y" if cancelled == 1 else "ies",
        )
        _debug.logic(
            "worker.over_limit",
            kind=self.__class__.__name__,
            pid=self.pid,
            elapsed_s=elapsed,
            limit_s=budget,
            doing=doing,
            cancelled=cancelled,
        )

    def _run_work_loop(self) -> None:
        try:
            signal.pthread_sigmask(
                signal.SIG_BLOCK,
                {
                    signal.SIGXCPU,
                    signal.SIGINT,
                    signal.SIGQUIT,
                    signal.SIGUSR1,
                    signal.SIGUSR2,
                },
            )
            # Readiness means the work thread actually started. A heartbeat
            # during listener reconnect or main-thread setup cannot prove it.
            os.write(self.watchdog_pipe[1], WORKER_READY)
            _debug.lifecycle("worker.ready", kind=self.__class__.__name__, pid=self.pid)
            worker = current_worker_thread()
            while self.alive:
                self.check_limits()
                self.multi.ping_pipe(self.watchdog_pipe)
                self.sleep()
                if not self.alive:
                    break
                worker.start_time = time.monotonic()
                try:
                    self.process_work()
                finally:
                    worker.start_time = None
        except BaseException as exc:
            self.logger.exception("Exception occurred, exiting...")
            _debug.logic(
                "worker.loop_failed",
                kind=self.__class__.__name__,
                pid=self.pid,
                error=type(exc).__name__,
            )
            self._runloop_exc = exc


class WorkerHTTP(Worker):
    identity: ServerIdentity | None = None

    def __init__(self, multi: PreforkServer) -> None:
        super().__init__(multi)

        self.limits = TransportLimits.from_environment()
        self.sock_timeout = self.limits.socket_timeout

    def process_request(self, client: socket.socket, addr: tuple[str, int]) -> None:
        outcome = Outcome.CLOSE
        try:
            client.setblocking(True)
            client.settimeout(self.sock_timeout)
            client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            flags = fcntl.fcntl(client, fcntl.F_GETFD) | fcntl.FD_CLOEXEC
            fcntl.fcntl(client, fcntl.F_SETFD, flags)
            identity = self.identity or self._get_identity(client)
            with contextlib.suppress(BrokenPipeError):
                with _debug.perf(
                    "worker.http.request",
                    pid=self.pid,
                    peer=addr[0] if isinstance(addr, tuple) else None,
                    request=self.request_count + 1,
                    request_max=self.request_max,
                ):
                    outcome = serve_prefork_connection(
                        client, addr, self.multi.app, identity, self.limits
                    )
        finally:
            # An upgrade handed the socket to its own thread; every other
            # way out, including an exception before serving, closes it here.
            if outcome is not Outcome.UPGRADED:
                with contextlib.suppress(OSError):
                    client.close()
        self.request_count += 1

    def _get_identity(self, sock: socket.socket) -> ServerIdentity:
        name, port = sock.getsockname()[:2]
        return ServerIdentity(
            name,
            port,
            multithread=False,
            multiprocess=True,
            exposes_socket=False,
            on_request=self.setproctitle,
        )

    def process_work(self) -> None:
        # A beat that timed out has nothing to accept; only a wake on the
        # listening socket does, and losing that one to a sibling is the race.
        if self.multi.socket is None or not self._listener_ready:
            return
        try:
            client, addr = self.multi.socket.accept()
            self.process_request(client, addr)
        except OSError as e:
            if e.errno not in (errno.EAGAIN, errno.ECONNABORTED):
                _debug.logic(
                    "worker.http.accept_failed",
                    pid=self.pid,
                    errno=e.errno,
                    error=type(e).__name__,
                )
                raise
            _debug.logic(
                "worker.http.accept_lost",
                pid=self.pid,
                reason="raced" if e.errno == errno.EAGAIN else "aborted",
            )

    def start(self) -> None:
        Worker.start(self)
        exclusive = False
        if self.multi.socket is not None:
            self.identity = self._get_identity(self.multi.socket)
            exclusive = watch_accept(self.selector, self.multi.socket)
        _debug.lifecycle(
            "worker.http.serving",
            pid=self.pid,
            socket=self.multi.socket is not None,
            exclusive_accept=exclusive,
            sock_timeout=self.sock_timeout,
        )


class WorkerCron(Worker):
    kind: ListenerKind = CRON_LISTENER
    _polls_wakeup_pipe = False

    def __init__(self, multi: PreforkServer) -> None:
        super().__init__(multi)
        self.alive_time = time.monotonic()
        self.watchdog_timeout = self.kind.real_time_budget() or None
        self.db_queue: deque[str] = deque()
        self.db_count: int = 0
        self.schedule = CronSchedule()
        self.listener = CronListener(
            self.listen_channel, self.logger, extra_read_fd=self.wakeup_pipe[0]
        )

    @property
    def listen_channel(self) -> str:
        return self.kind.channel

    def _sleep_with_watchdog(self, total_seconds: float) -> None:
        tick = max(self.multi.beat / 2, 0.5)
        remaining = total_seconds
        _debug.logic(
            "worker.cron.sleeping_with_watchdog",
            kind=self.__class__.__name__,
            pid=self.pid,
            seconds=total_seconds,
            tick=tick,
        )
        while remaining > 0 and self.alive:
            self.multi.ping_pipe(self.watchdog_pipe)
            chunk = min(tick, remaining)
            time.sleep(chunk)
            remaining -= chunk

    def _run_jobs_for_database(self, db_name: str) -> None:
        self.kind.process_jobs()(db_name)

    def sleep(self) -> None:
        if not self.db_queue:
            if self.listener.backing_off:
                _debug.logic(
                    "worker.cron.sleep_skipped",
                    kind=self.__class__.__name__,
                    pid=self.pid,
                    reason="backing_off",
                )
                return

            interval = self.schedule.polling_delay
            if self.watchdog_timeout:
                interval = min(interval, max(self.watchdog_timeout / 2, 1))

            _debug.logic(
                "worker.cron.waiting",
                kind=self.__class__.__name__,
                pid=self.pid,
                interval_s=interval,
                polling_delay_s=self.schedule.polling_delay,
                watchdog_timeout=self.watchdog_timeout,
            )
            wait_for_notifies(self.listener, interval)
            empty_pipe(self.wakeup_pipe[0])

    def get_max_age(self) -> int:
        return self.kind.max_age()

    @override
    def check_limits(self) -> None:
        super().check_limits()

        max_age = self.get_max_age()
        if max_age > 0 and (time.monotonic() - self.alive_time) > max_age:
            self.logger.info("Max age (%ss) reached.", max_age)
            self.stop_for("max_age")

    def process_work(self) -> None:
        self.logger.debug("polling for jobs")

        if not self.db_queue:
            if not self.listener.connected:
                _debug.logic("worker.cron.reconnecting", reason="disconnected")
                self.listener.reconnect_after_failure(
                    "Reconnect to postgres", self._sleep_with_watchdog
                )
                return
            try:
                notified = self.listener.drain()
            except psycopg.OperationalError, PoolError:
                self.logger.warning("Lost postgres connection, reconnecting...")
                _debug.logic("worker.cron.reconnecting", reason="connection_lost")
                self.listener.reconnect_after_failure(
                    "Reconnect to postgres", self._sleep_with_watchdog
                )
                return
            self.db_queue.extend(self.schedule.get_due_databases(notified))
            self.db_count = len(self.db_queue)
            _debug.pipeline(
                "worker.cron.queue_filled",
                kind=self.__class__.__name__,
                pid=self.pid,
                notified=len(notified),
                queued=self.db_count,
            )
            if not self.db_count:
                return

        db_name = self.db_queue.popleft()
        self.setproctitle(db_name)
        _debug.pipeline(
            "worker.cron.sweep",
            kind=self.__class__.__name__,
            db=db_name,
            queued=len(self.db_queue),
            db_count=self.db_count,
        )

        sweep_database(
            db_name,
            self._run_jobs_for_database,
            self.logger,
            release=self.db_count > 1,
        )

        self.request_count += 1
        if (
            self.request_max > 0
            and self.request_count >= self.request_max
            and self.request_max < self.db_count
        ):
            self.logger.error(
                "There are more databases to process than allowed "
                "by the `limit_request` configuration variable: %s more.",
                self.db_count - self.request_max,
            )
            _debug.logic(
                "worker.cron.limit_request_short",
                kind=self.__class__.__name__,
                pid=self.pid,
                request_max=self.request_max,
                db_count=self.db_count,
                unswept=self.db_count - self.request_max,
            )

    def start(self) -> None:
        os.nice(10)
        Worker.start(self)
        if self.multi.socket:
            self.multi.socket.close()
        # Spread the sweeps of sibling cron workers, as the threaded server
        # does with its thread number; the pid is the child's only here.
        self.schedule.refresh_interval = CRON_POLL_INTERVAL_S + os.getpid() % 10
        registries_size = get_env_int(
            "ODOO_REGISTRY_LRU_SIZE_CRON", 0, minimum=0, logger=self.logger
        )
        if registries_size > 0:
            Registry.registries.count = registries_size
            _debug.lifecycle("worker.cron.registry_lru", size=registries_size)
        _debug.lifecycle(
            "worker.cron.started",
            kind=self.__class__.__name__,
            pid=self.pid,
            channel=self.listen_channel,
            max_age=self.get_max_age(),
            watchdog_timeout=self.watchdog_timeout,
            socket_closed=self.multi.socket is not None,
        )

        while self.alive:
            if self.listener.reconnect_after_failure(
                "WorkerCron initial PG connect", self._sleep_with_watchdog
            ):
                _debug.lifecycle(
                    "worker.cron.connected",
                    kind=self.__class__.__name__,
                    pid=self.pid,
                    channel=self.listen_channel,
                )
                break

    @override
    def stop(self) -> None:
        super().stop()
        self.listener.close()
        _debug.lifecycle(
            "worker.cron.stopped",
            kind=self.__class__.__name__,
            pid=self.pid,
            swept=self.request_count,
            queued=len(self.db_queue),
        )


class WorkerJob(WorkerCron):
    """The same loop on the other channel.

    Everything that differs between the two is `kind`: the channel it
    listens on, when its connection is recycled, whose `_process_jobs` it
    calls and the real-time budget its master's watchdog allows it.
    """

    kind: ListenerKind = JOB_LISTENER


class WorkerStream(WorkerCron):
    """The sweep that reconciles a database's held-open connections.

    The connections live in this process between sweeps, so the loop wakes
    on the stream channel and on a fixed heartbeat rather than the cron
    schedule, sweeps every served database each time, and closes what it
    holds when it stops; the next leader reopens it within one heartbeat.
    """

    kind: ListenerKind = STREAM_LISTENER

    def sleep(self) -> None:
        if not self.db_queue:
            if self.listener.backing_off:
                return
            wait_for_notifies(self.listener, STREAM_HEARTBEAT_S)
            empty_pipe(self.wakeup_pipe[0])

    def process_work(self) -> None:
        if not self.db_queue:
            if not self.listener.connected:
                self.listener.reconnect_after_failure(
                    "Reconnect to postgres", self._sleep_with_watchdog
                )
                return
            try:
                self.listener.drain()
            except psycopg.OperationalError, PoolError:
                self.logger.warning("Lost postgres connection, reconnecting...")
                self.listener.reconnect_after_failure(
                    "Reconnect to postgres", self._sleep_with_watchdog
                )
                return
            self.db_queue.extend(self.schedule.reset_known_databases())
            self.db_count = len(self.db_queue)
            if not self.db_count:
                return
        db_name = self.db_queue.popleft()
        self.setproctitle(db_name)
        sweep_database(db_name, self._run_jobs_for_database, self.logger, release=False)

    @override
    def stop(self) -> None:
        from ._stream import shutdown

        shutdown()
        super().stop()
