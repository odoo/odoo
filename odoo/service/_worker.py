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
from typing import TYPE_CHECKING, Any

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
from odoo.modules.registry import Registry

from ._cron import (
    CRON_NOTIFY_JITTER_MAX_S,
    CRON_POLL_INTERVAL_S,
    CRON_TRIGGER_CHANNEL,
    JOB_QUEUE_CHANNEL,
    CronListener,
    CronSchedule,
    drain_swept_database,
)
from ._env import get_env_int
from ._limits import empty_pipe, get_memory_over_soft_limit
from ._transport import (
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

    def __init__(self, multi: PreforkServer) -> None:
        self.multi = multi
        self.watchdog_time = time.monotonic()
        self.watchdog_pipe = multi.open_pipe()
        try:
            self.eintr_pipe = multi.open_pipe()
        except BaseException:
            for fd in self.watchdog_pipe:
                with contextlib.suppress(OSError):
                    os.close(fd)
            raise
        self.wakeup_fd_r, self.wakeup_fd_w = self.eintr_pipe
        self.watchdog_timeout: float | None = multi.timeout
        self.ppid = os.getpid()
        self.pid: int | None = None
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

    def close(self) -> None:
        _debug.lifecycle(
            "worker.closed",
            kind=self.__class__.__name__,
            pid=getattr(self, "pid", None),
            requests=getattr(self, "request_count", None),
        )
        for fd in (
            self.watchdog_pipe[0],
            self.watchdog_pipe[1],
            self.eintr_pipe[0],
            self.eintr_pipe[1],
        ):
            with contextlib.suppress(OSError):
                os.close(fd)

    def signal_handler(self, sig: int, frame: Any) -> None:
        self.alive = False

    def signal_time_expired_handler(self, sig: int, frame: Any) -> None:
        raise CpuTimeLimitExceeded(
            f"CPU time limit ({current().limit_time_cpu}s) exceeded"
        )

    def sleep(self) -> None:
        self._selector.select(timeout=self.multi.beat)
        empty_pipe(self.wakeup_fd_r)

    def check_limits(self) -> None:
        Registry._evict_idle_registries()
        if self.ppid != os.getppid():
            self.logger.info("Parent changed")
            _debug.lifecycle(
                "worker.recycle",
                kind=self.__class__.__name__,
                pid=self.pid,
                reason="parent_changed",
            )
            self.alive = False
        if self.request_max > 0 and self.request_count >= self.request_max:
            self.logger.info("Max request (%s) reached.", self.request_count)
            _debug.lifecycle(
                "worker.recycle",
                kind=self.__class__.__name__,
                pid=self.pid,
                reason="request_max",
                requests=self.request_count,
            )
            self.alive = False
        settings = current()
        memory = get_memory_over_soft_limit(
            self._process_handle, settings.limit_memory_soft
        )
        if memory is not None:
            self.logger.info("RSS memory soft-limit reached: %s bytes.", memory)
            _debug.lifecycle(
                "worker.recycle",
                kind=self.__class__.__name__,
                pid=self.pid,
                reason="memory_soft",
                rss=memory,
            )
            self.alive = False

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

        signal.set_wakeup_fd(self.wakeup_fd_w)
        self._selector = selectors.DefaultSelector()
        self._selector.register(self.wakeup_fd_r, selectors.EVENT_READ)

    def stop(self) -> None:
        if hasattr(self, "_selector"):
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
            t.join()
            if self._runloop_exc is not None:
                raise SystemExit(1)
            self.logger.info(
                "Exiting cleanly. request_count: %s, registry count: %s.",
                self.request_count,
                len(Registry.registries),
            )
        except CpuTimeLimitExceeded:
            self.logger.warning(
                "CPU time limit (%ss) exceeded; recycling worker.",
                current().limit_time_cpu,
            )
            _debug.lifecycle(
                "worker.recycle",
                kind=self.__class__.__name__,
                pid=self.pid,
                reason="cpu_limit",
                limit_s=current().limit_time_cpu,
            )
            self.alive = False
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
            os.write(self.watchdog_pipe[1], b"R")
            _debug.lifecycle("worker.ready", kind=self.__class__.__name__, pid=self.pid)
            while self.alive:
                self.check_limits()
                self.multi.ping_pipe(self.watchdog_pipe)
                self.sleep()
                if not self.alive:
                    break
                self.process_work()
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
                    pid=getattr(self, "pid", None),
                    peer=addr[0] if isinstance(addr, tuple) else None,
                    request=getattr(self, "request_count", 0) + 1,
                    request_max=getattr(self, "request_max", None),
                ):
                    serve_prefork_connection(
                        client, addr, self.multi.app, identity, self.limits
                    )
        finally:
            with contextlib.suppress(OSError):
                client.close()
        self.request_count += 1

    def _get_identity(self, sock: socket.socket) -> ServerIdentity:
        name, port = sock.getsockname()[:2]
        return ServerIdentity(
            name, port, multithread=False, multiprocess=True, exposes_socket=False
        )

    def process_work(self) -> None:
        if self.multi.socket is None:
            return
        try:
            client, addr = self.multi.socket.accept()
            self.process_request(client, addr)
        except OSError as e:
            if e.errno not in (errno.EAGAIN, errno.ECONNABORTED):
                _debug.logic(
                    "worker.http.accept_failed",
                    pid=getattr(self, "pid", None),
                    errno=e.errno,
                    error=type(e).__name__,
                )
                raise
            _debug.logic(
                "worker.http.accept_lost",
                pid=getattr(self, "pid", None),
                reason="raced" if e.errno == errno.EAGAIN else "aborted",
            )

    def start(self) -> None:
        Worker.start(self)
        exclusive = False
        if self.multi.socket is not None:
            self.identity = self._get_identity(self.multi.socket)
            exclusive = watch_accept(self._selector, self.multi.socket)
        _debug.lifecycle(
            "worker.http.serving",
            pid=self.pid,
            socket=self.multi.socket is not None,
            exclusive_accept=exclusive,
            sock_timeout=self.sock_timeout,
        )


class WorkerCron(Worker):
    listen_channel = CRON_TRIGGER_CHANNEL

    def __init__(self, multi: PreforkServer) -> None:
        super().__init__(multi)
        self.alive_time = time.monotonic()
        self.watchdog_timeout = multi.cron_timeout
        self.db_queue: deque[str] = deque()
        self.db_count: int = 0
        self.schedule = CronSchedule()
        self.listener = CronListener(
            self.listen_channel, self.logger, extra_read_fd=self.wakeup_fd_r
        )

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
        from odoo.addons.base.models.ir_cron import IrCron

        IrCron._process_jobs(db_name)

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

            interval: float = CRON_POLL_INTERVAL_S + os.getpid() % 10
            interval = min(interval, self.schedule.polling_delay)

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
            if self.listener.wait(interval):
                time.sleep(random.uniform(0, CRON_NOTIFY_JITTER_MAX_S))
            empty_pipe(self.wakeup_fd_r)

    def get_max_age(self) -> int:
        return current().limit_time_worker_cron

    def check_limits(self) -> None:
        super().check_limits()

        max_age = self.get_max_age()
        if max_age > 0 and (time.monotonic() - self.alive_time) > max_age:
            self.logger.info("Max age (%ss) reached.", max_age)
            _debug.lifecycle(
                "worker.recycle",
                kind=self.__class__.__name__,
                pid=self.pid,
                reason="max_age",
                max_age_s=max_age,
            )
            self.alive = False

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

        try:
            with _debug.perf(
                "worker.cron.process_jobs", kind=self.__class__.__name__, db=db_name
            ):
                self._run_jobs_for_database(db_name)
        except Exception:
            self.logger.warning(
                "Uncaught error while processing jobs for database %s",
                db_name,
                exc_info=True,
            )
            _debug.logic("worker.cron.jobs_failed", db=db_name)

        if self.db_count > 1:
            drain_swept_database(db_name)

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
        self._selector.close()
        del self._selector
        if self.multi.socket:
            self.multi.socket.close()
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

    def stop(self) -> None:
        super().stop()
        self.listener.close()
        _debug.lifecycle(
            "worker.cron.stopped",
            kind=self.__class__.__name__,
            pid=getattr(self, "pid", None),
            swept=getattr(self, "request_count", None),
            queued=len(getattr(self, "db_queue", ())),
        )


class WorkerJob(WorkerCron):
    listen_channel = JOB_QUEUE_CHANNEL

    def __init__(self, multi: PreforkServer) -> None:
        super().__init__(multi)
        self.watchdog_timeout = multi.job_timeout

    def get_max_age(self) -> int:
        return current().job_max_age

    def _run_jobs_for_database(self, db_name: str) -> None:
        from odoo.addons.base.models.ir_job import IrJob

        IrJob._process_jobs(db_name)
