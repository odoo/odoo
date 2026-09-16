from __future__ import annotations

import contextlib
import errno
import logging
import os
import selectors
import signal
import socket
import subprocess
import sys
import time
from collections import deque
from pathlib import Path
from typing import Any

import psutil

if os.name == "posix":
    import fcntl

from odoo import db
from odoo.libs import backoff
from odoo.libs.debug_log import DebugLog
from odoo.modules.registry import Registry
from odoo.tools.cache import log_ormcache_stats
from odoo.tools.misc import dumpstacks, stripped_sys_argv

from . import _process_state
from ._base_server import CommonServer
from ._census import WorkerCensus
from ._env import IS_POSIX, get_env_float
from ._limits import empty_pipe, get_graceful_stop_timeout
from ._sdnotify import Watchdog, notify, notify_ready, notify_reloading
from ._worker import Worker, WorkerCron, WorkerHTTP, WorkerJob
from .lifecycle import preload_registries
from .settings import SD_LISTEN_FDS_START

_logger = logging.getLogger("odoo.service.server")
_debug = DebugLog(__name__)

WORKER_MIN_HEALTHY_LIFETIME_S = 30.0
WORKER_RESPAWN_BACKOFF_CAP_S = 30.0

EVENTED_STOP_TIMEOUT_S = 5.0

SUPERVISION_BEAT_S = 4.0
"""How long the master sleeps between supervision passes; `stop_workers_gracefully`
shortens it while draining and `reload` restores it."""

RELOAD_TIMEOUT_S = 60.0
"""How long a reload waits for the replacement to preload and report ready.

Measured 2026-09-15 on a 217-module database: the candidate answers in
2.7 s, so this is a bound on a hung candidate, not a budget the preload
spends.  The old generation keeps serving throughout the wait, and a
deployment whose preload genuinely needs longer raises `ODOO_RELOAD_TIMEOUT`.
"""


class RespawnHold:
    """How long one population's respawn waits after consecutive early deaths."""

    __slots__ = ("fast_deaths", "not_before")

    def __init__(self) -> None:
        self.fast_deaths = 0
        self.not_before = 0.0

    def record(self, now: float) -> float:
        self.fast_deaths += 1
        delay = backoff.get_bound(
            self.fast_deaths, base=2, cap=WORKER_RESPAWN_BACKOFF_CAP_S
        )
        self.not_before = now + delay
        return delay

    def clear(self) -> None:
        self.fast_deaths = 0
        self.not_before = 0.0

    def remaining(self, now: float) -> float:
        return max(self.not_before - now, 0.0)


SPAWN_HOLD = "*"
"""The hold a failed fork or pipe arms: process-wide, so it gates every kind."""

LONG_POLLING_KIND = "Long-polling (evented) subprocess"


class PreforkServer(CommonServer):
    flavor = "prefork"

    def get_metrics(self) -> dict[str, Any]:
        if os.getpid() != self.pid:
            return self._census.read()
        return self._get_census()

    def _get_census(self) -> dict[str, Any]:
        return {
            "workers": {
                "http": len(self.workers_http),
                "cron": len(self.workers_cron),
                "job": len(self.workers_job),
            },
            "worker_population": self.population,
            "worker_generation": self.generation,
            "long_polling_alive": self.long_polling_pid is not None,
        }

    def _publish_census(self) -> None:
        # Runs inside run()'s loop, where a raise takes the master down: the
        # metrics are best effort, the supervision is not.
        try:
            self._census.publish(self._get_census)
        except Exception:
            self.logger.debug("Could not publish the worker census", exc_info=True)
            _debug.logic("prefork.census_unpublishable")

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        settings = self.settings
        self.population = settings.workers
        self.timeout = settings.get_real_time_budget("http") or None
        self.limit_request = settings.limit_request
        self.cron_timeout = settings.get_real_time_budget("cron") or None
        self.job_timeout = settings.get_real_time_budget("job") or None
        self.beat: float = SUPERVISION_BEAT_S
        self.pipe: tuple[int, int] | None = None
        self.socket: socket.socket | None = None
        self.workers_http: dict[int, WorkerHTTP] = {}
        self.workers_cron: dict[int, WorkerCron] = {}
        self.workers_job: dict[int, WorkerJob] = {}
        self.workers: dict[int, Worker] = {}
        self._killed_workers: dict[int, Worker] = {}
        self._retiring_workers: set[int] = set()
        self.generation = 0
        self.queue: deque[int] = deque()
        self.long_polling_pid: int | None = None
        self.long_polling_popen: subprocess.Popen | None = None
        self.long_polling_spawn_time = 0.0
        # One hold per population, so a crash loop in one kind does not delay
        # the replacements of another; the spawn hold gates them all.
        self._respawn_holds: dict[str, RespawnHold] = {}
        self._selector: selectors.BaseSelector | None = None
        self._watched: dict[int, Worker] = {}
        self._census = WorkerCensus(self.pid)
        self._replacement: subprocess.Popen | None = None
        self._candidate: subprocess.Popen | None = None
        self._reload_reader: tuple[int, selectors.BaseSelector] | None = None
        self._reload_supervisor = int(os.environ.pop("ODOO_RELOAD_SUPERVISOR_PID", "0"))
        self.is_reload_watcher_owner = not self._reload_supervisor
        self._ready_fd = os.environ.pop("ODOO_RELOAD_READY_FD", None)
        _debug.lifecycle(
            "prefork.created",
            population=self.population,
            timeout=self.timeout,
            cron_timeout=self.cron_timeout,
            job_timeout=self.job_timeout,
            limit_request=self.limit_request,
            reload_supervisor=self._reload_supervisor,
            reload_ready_fd=self._ready_fd is not None,
        )

    def open_pipe(self) -> tuple[int, int]:
        return os.pipe2(os.O_NONBLOCK | os.O_CLOEXEC)

    def _set_socket_cloexec(self) -> None:
        if not IS_POSIX or self.socket is None:
            return
        fd = self.socket.fileno()
        flags = fcntl.fcntl(fd, fcntl.F_GETFD) | fcntl.FD_CLOEXEC
        fcntl.fcntl(fd, fcntl.F_SETFD, flags)

    def ping_pipe(self, pipe: tuple[int, int]) -> None:
        try:
            os.write(pipe[1], b".")
        except OSError as e:
            if e.errno not in [errno.EAGAIN, errno.EINTR]:
                raise

    def signal_handler(self, sig: int, frame: Any) -> None:
        if sig in (signal.SIGCHLD, signal.SIGHUP) and sig in self.queue:
            return
        self.queue.append(sig)
        if self.pipe is not None:
            self.ping_pipe(self.pipe)

    def _close_inherited_pipe_fds_in_child(self, new_worker: Worker) -> None:
        keep = {
            new_worker.watchdog_pipe[0],
            new_worker.watchdog_pipe[1],
            new_worker.wakeup_pipe[0],
            new_worker.wakeup_pipe[1],
        }
        for sibling in self.workers.values():
            for fd in (
                sibling.watchdog_pipe[0],
                sibling.watchdog_pipe[1],
                sibling.wakeup_pipe[0],
                sibling.wakeup_pipe[1],
            ):
                if fd not in keep:
                    with contextlib.suppress(OSError):
                        os.close(fd)
        for fd in self.pipe or ():
            if fd not in keep:
                with contextlib.suppress(OSError):
                    os.close(fd)
        self._close_watchdog_selector()
        if self._reload_reader is not None:
            fd, selector = self._reload_reader
            os.close(fd)
            selector.close()
            self._reload_reader = None
        if self._ready_fd is not None:
            os.close(int(self._ready_fd))
            self._ready_fd = None
        _debug.lifecycle(
            "prefork.child_fds_closed",
            kind=new_worker.__class__.__name__,
            pid=os.getpid(),
            siblings=len(self.workers),
        )

    def _get_respawn_hold(self, kind: str) -> RespawnHold:
        hold = self._respawn_holds.get(kind)
        if hold is None:
            hold = self._respawn_holds[kind] = RespawnHold()
        return hold

    def _get_respawn_hold_remaining(self, kind: str) -> float:
        now = time.monotonic()
        return max(
            self._get_respawn_hold(SPAWN_HOLD).remaining(now),
            self._get_respawn_hold(kind).remaining(now),
        )

    def _record_spawn_failure(self) -> None:
        hold = self._get_respawn_hold(SPAWN_HOLD)
        delay = hold.record(time.monotonic())
        self.logger.warning(
            "worker spawn failed before fork (attempt %d); holding respawn for %.0fs",
            hold.fast_deaths,
            delay,
        )
        _debug.logic(
            "prefork.spawn_failed",
            attempt=hold.fast_deaths,
            backoff_s=delay,
        )

    def spawn_worker(self, klass: type, workers_registry: dict) -> Worker | None:
        worker = None
        try:
            worker = klass(self)
            pid = os.fork()
        except OSError as exc:
            if worker is not None:
                worker.close()
            self.logger.debug(
                "worker spawn failed (pipe/fork); skipping, will retry",
                exc_info=True,
            )
            _debug.logic(
                "prefork.fork_failed",
                kind=getattr(klass, "__name__", None),
                stage="fork" if worker is not None else "pipe",
                errno=exc.errno,
                workers=len(self.workers),
            )
            self._record_spawn_failure()
            return None
        if pid != 0:
            self.generation += 1
            worker.pid = pid
            worker.spawn_time = time.monotonic()
            self.workers[pid] = worker
            workers_registry[pid] = worker
            _debug.lifecycle(
                "prefork.worker_spawned",
                kind=klass.__name__,
                pid=pid,
                generation=self.generation,
                workers=len(self.workers),
            )
            return worker
        else:
            for _sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
                with contextlib.suppress(OSError, ValueError):
                    signal.signal(_sig, signal.SIG_DFL)
            for _sig in (signal.SIGCHLD, signal.SIGTTIN, signal.SIGTTOU):
                with contextlib.suppress(OSError, ValueError):
                    signal.signal(_sig, signal.SIG_IGN)
            self._close_inherited_pipe_fds_in_child(worker)
            exit_code = 0
            try:
                worker.run()
            except SystemExit as exc:
                if isinstance(exc.code, int):
                    exit_code = exc.code
                else:
                    exit_code = 0 if exc.code is None else 1
            except BaseException as exc:
                self.logger.critical(
                    "Worker %s (%d): uncaught error, exiting...",
                    worker.__class__.__name__,
                    os.getpid(),
                    exc_info=exc,
                )
                _debug.logic(
                    "prefork.child_uncaught",
                    kind=worker.__class__.__name__,
                    pid=os.getpid(),
                    error=type(exc).__name__,
                )
                exit_code = 1
            _debug.lifecycle(
                "prefork.child_exiting",
                kind=worker.__class__.__name__,
                pid=os.getpid(),
                exit_code=exit_code,
            )
            os._exit(exit_code)

    def spawn_long_polling_process(self) -> None:
        nargs = stripped_sys_argv()
        cmd = [sys.executable, sys.argv[0], "evented"] + nargs[1:]
        try:
            popen = subprocess.Popen(cmd)
        except OSError:
            self.logger.debug(
                "long-polling subprocess spawn failed; will retry",
                exc_info=True,
            )
            _debug.logic("prefork.long_polling_spawn_failed")
            self._record_spawn_failure()
            return
        self.long_polling_pid = popen.pid
        self.long_polling_popen = popen
        self.long_polling_spawn_time = time.monotonic()
        _debug.lifecycle("prefork.long_polling_spawned", pid=popen.pid)

    def _reconcile_long_polling_popen(self, returncode: int | None) -> None:
        popen = self.long_polling_popen
        self.long_polling_popen = None
        if popen is not None and popen.returncode is None:
            popen.returncode = returncode if returncode is not None else -signal.SIGKILL
            _debug.lifecycle(
                "prefork.long_polling_reconciled",
                pid=popen.pid,
                returncode=popen.returncode,
                assumed_killed=returncode is None,
            )

    def remove_worker(self, pid: int) -> None:
        self._retiring_workers.discard(pid)
        if pid == self.long_polling_pid:
            self.long_polling_pid = None
            _debug.lifecycle("prefork.long_polling_unregistered", pid=pid)
        if pid in self.workers:
            self.logger.debug("worker (%s) unregistered", pid)
            _debug.lifecycle(
                "prefork.worker_unregistered",
                kind=self.workers[pid].__class__.__name__,
                pid=pid,
                workers=len(self.workers) - 1,
            )
            self.workers_http.pop(pid, None)
            self.workers_cron.pop(pid, None)
            self.workers_job.pop(pid, None)
            self.workers.pop(pid).close()

    def _record_killed_worker(self, pid: int) -> None:
        worker = self.workers.get(pid)
        if worker is not None:
            self._killed_workers[pid] = worker

    def kill_worker(self, pid: int, sig: int) -> None:
        _debug.lifecycle("prefork.worker_signalled", pid=pid, sig=sig)
        try:
            os.kill(pid, sig)
            if sig == signal.SIGKILL:
                self._record_killed_worker(pid)
                self.remove_worker(pid)
        except OSError as e:
            if e.errno == errno.ESRCH:
                _debug.logic("prefork.worker_vanished", pid=pid, sig=sig)
                self._record_killed_worker(pid)
                self.remove_worker(pid)

    def apply_pending_signals(self, *, draining: bool = False) -> None:
        if draining:
            # Leave reload and scaling requests in order for the next serving
            # generation. Shutdown takes priority and must reach the outer loop.
            for sig in tuple(self.queue):
                if sig in (signal.SIGINT, signal.SIGTERM):
                    self.queue.remove(sig)
                    self.queue.appendleft(sig)
                    _debug.logic("prefork.shutdown_during_drain", sig=sig)
                    raise KeyboardInterrupt
            return
        while self.queue:
            sig = self.queue.popleft()
            _debug.pipeline(
                "prefork.signal_applied",
                sig=sig,
                queued=len(self.queue),
                population=self.population,
            )
            if sig in [signal.SIGINT, signal.SIGTERM]:
                raise KeyboardInterrupt
            if sig == signal.SIGHUP:
                _process_state.set_phoenix(True)
                raise KeyboardInterrupt
            if self._replacement is not None and sig in (
                signal.SIGTTIN,
                signal.SIGTTOU,
            ):
                self._replacement.send_signal(sig)
            if sig == signal.SIGTTIN:
                self.population += 1
                _debug.lifecycle(
                    "prefork.population_changed", population=self.population
                )
            elif sig == signal.SIGTTOU:
                self.population = max(self.population - 1, 0)
                _debug.lifecycle(
                    "prefork.population_changed", population=self.population
                )

    def reap_exited_workers(self) -> None:
        reaped = 0  # debuglog
        while True:
            try:
                wpid, status = os.waitpid(-1, os.WNOHANG)
                if not wpid:
                    break
                reaped += 1  # debuglog
                self._record_worker_exit(wpid, status)
                self.remove_worker(wpid)
            except OSError as e:
                if e.errno == errno.ECHILD:
                    break
                _debug.logic("prefork.reap_failed", errno=e.errno, reaped=reaped)
                raise
        if _debug.pipeline.enabled and reaped:
            _debug.pipeline("prefork.reaped", exited=reaped, workers=len(self.workers))

    def _record_worker_exit(self, pid: int, status: int) -> None:
        for process in (self._candidate, self._replacement):
            if process is not None and process.pid == pid:
                process.returncode = os.waitstatus_to_exitcode(status)
                _debug.lifecycle(
                    "prefork.generation_exited",
                    pid=pid,
                    returncode=process.returncode,
                    candidate=process is self._candidate,
                )
                return
        policy_kill = False
        if pid == self.long_polling_pid:
            name = LONG_POLLING_KIND
            lifetime = time.monotonic() - self.long_polling_spawn_time
            self._reconcile_long_polling_popen(os.waitstatus_to_exitcode(status))
        else:
            killed_by_master = pid in self._killed_workers
            worker = self.workers.get(pid) or self._killed_workers.pop(pid, None)
            if worker is None:
                _debug.logic("prefork.unknown_child_exited", pid=pid, status=status)
                return
            name = worker.__class__.__name__
            lifetime = time.monotonic() - getattr(worker, "spawn_time", 0.0)
            # The watchdog's SIGKILL of a worker that had reported ready is a
            # policy the master applied to one long request, not a crash to
            # back off from; the same kill on a worker that never got there
            # is a worker that hangs at boot, which is what the back-off is for.
            policy_kill = killed_by_master and bool(worker.ready)
        _debug.lifecycle(
            "prefork.worker_exited",
            kind=name,
            pid=pid,
            lifetime_s=lifetime,
            status=status,
        )
        hold = self._get_respawn_hold(name)
        if lifetime >= WORKER_MIN_HEALTHY_LIFETIME_S:
            if _debug.logic.enabled and hold.fast_deaths:
                _debug.logic(
                    "prefork.fast_death_backoff_cleared",
                    kind=name,
                    pid=pid,
                    fast_deaths=hold.fast_deaths,
                )
            hold.clear()
            # A child that lived proves the process can still fork one.
            self._get_respawn_hold(SPAWN_HOLD).clear()
            return
        exited_nonzero = os.WIFEXITED(status) and os.WEXITSTATUS(status) != 0
        crashed_by_signal = (
            os.WIFSIGNALED(status)
            and os.WTERMSIG(status) != signal.SIGTERM
            and not policy_kill
        )
        _debug.logic(
            "prefork.early_exit",
            kind=name,
            pid=pid,
            lifetime_s=lifetime,
            exited_nonzero=exited_nonzero,
            crashed_by_signal=crashed_by_signal,
            policy_kill=policy_kill,
        )
        if exited_nonzero or crashed_by_signal:
            delay = hold.record(time.monotonic())
            _debug.logic(
                "prefork.fast_death_backoff",
                kind=name,
                fast_deaths=hold.fast_deaths,
                backoff_s=delay,
            )
            cause = (
                f"exit {os.WEXITSTATUS(status)}"
                if exited_nonzero
                else f"signal {os.WTERMSIG(status)}"
            )
            self.logger.warning(
                "%s (%s) died after %.1fs (%s); holding respawn for %.0fs "
                "(%d consecutive early crashes)",
                name,
                pid,
                lifetime,
                cause,
                delay,
                hold.fast_deaths,
            )

    def kill_timed_out_workers(self) -> None:
        now = time.monotonic()
        for pid, worker in list(self.workers.items()):
            if (
                worker.watchdog_timeout is not None
                and (now - worker.watchdog_time) >= worker.watchdog_timeout
            ):
                self.logger.error(
                    "%s (%s) timeout after %ss",
                    worker.__class__.__name__,
                    pid,
                    worker.watchdog_timeout,
                )
                _debug.lifecycle(
                    "prefork.worker_timed_out",
                    kind=worker.__class__.__name__,
                    pid=pid,
                    timeout=worker.watchdog_timeout,
                    silent_s=now - worker.watchdog_time,
                )
                self.kill_worker(pid, signal.SIGKILL)

    def _is_respawn_held(self, kind: str) -> bool:
        remaining = self._get_respawn_hold_remaining(kind)
        if remaining <= 0:
            return False
        _debug.logic(
            "prefork.respawn_held",
            kind=kind,
            remaining_s=remaining,
            fast_deaths=self._get_respawn_hold(kind).fast_deaths,
        )
        return True

    def spawn_missing_workers(self) -> None:
        self._retire_excess_workers()
        registries = Registry.registries.snapshot
        checked = False
        if _debug.pipeline.enabled and (
            len(self.workers_http) - len(self._retiring_workers) < self.population
            or len(self.workers_cron) < self.settings.max_cron_threads
            or len(self.workers_job) < self.settings.job_workers
            or (self.settings.http_enable and not self.long_polling_pid)
        ):
            _debug.pipeline(
                "prefork.spawn_cycle",
                http=len(self.workers_http),
                retiring=len(self._retiring_workers),
                population=self.population,
                cron=len(self.workers_cron),
                max_cron_threads=self.settings.max_cron_threads,
                job=len(self.workers_job),
                job_workers=self.settings.job_workers,
                long_polling=self.long_polling_pid is not None,
                http_enable=self.settings.http_enable,
            )

        def check_registries():
            nonlocal checked
            if checked or not registries:
                return

            checked = True
            _debug.pipeline("prefork.registries_checked", databases=len(registries))
            for db_name, registry in registries.items():
                try:
                    with registry.cursor() as cr:
                        registry.check_signaling(cr)
                except Exception:
                    _logger.warning(
                        "Could not check signaling for database %r during worker "
                        "spawn; skipping this cycle.",
                        db_name,
                        exc_info=True,
                    )
                    _debug.logic("prefork.signaling_check_failed", db=db_name)
            db.close_all()

        if self.settings.http_enable:
            while len(self.workers_http) - len(
                self._retiring_workers
            ) < self.population and not self._is_respawn_held(WorkerHTTP.__name__):
                check_registries()
                if self.spawn_worker(WorkerHTTP, self.workers_http) is None:
                    return
            if not self.long_polling_pid and not self._is_respawn_held(
                LONG_POLLING_KIND
            ):
                check_registries()
                self.spawn_long_polling_process()
        while len(self.workers_cron) < self.settings.max_cron_threads and not (
            self._is_respawn_held(WorkerCron.__name__)
        ):
            check_registries()
            if self.spawn_worker(WorkerCron, self.workers_cron) is None:
                return
        while len(self.workers_job) < self.settings.job_workers and not (
            self._is_respawn_held(WorkerJob.__name__)
        ):
            check_registries()
            if self.spawn_worker(WorkerJob, self.workers_job) is None:
                return

    def _retire_excess_workers(self) -> None:
        """Drain excess HTTP workers once, retaining watchdog/reaping ownership."""
        active = [pid for pid in self.workers_http if pid not in self._retiring_workers]
        for pid in active[: max(0, len(active) - self.population)]:
            self._retiring_workers.add(pid)
            _debug.lifecycle(
                "prefork.worker_retiring",
                pid=pid,
                active=len(active),
                population=self.population,
            )
            self.kill_worker(pid, signal.SIGINT)

    def _close_watchdog_selector(self) -> None:
        sel, self._selector = self._selector, None
        self._watched = {}
        if sel is not None:
            with contextlib.suppress(Exception):
                sel.close()

    def _get_watchdog_selector(
        self,
    ) -> tuple[selectors.BaseSelector, dict[int, Worker]]:
        fds = {w.watchdog_pipe[0]: w for w in self.workers.values()}
        sel = self._selector
        if sel is None:
            sel = self._selector = selectors.DefaultSelector()
            self._watched = {}
        watched = self._watched
        unregistered = 0  # debuglog
        registered = 0  # debuglog
        for fd, owner in list(watched.items()):
            if fds.get(fd) is owner:
                continue
            del watched[fd]
            unregistered += 1  # debuglog
            with contextlib.suppress(KeyError, ValueError, OSError):
                sel.unregister(fd)
        for fd, owner in fds.items():
            if fd in watched:
                continue
            with contextlib.suppress(KeyError, ValueError, OSError):
                sel.register(fd, selectors.EVENT_READ)
                watched[fd] = owner
                registered += 1  # debuglog
        if self.pipe is not None and self.pipe[0] not in sel.get_map():
            with contextlib.suppress(KeyError, ValueError, OSError):
                sel.register(self.pipe[0], selectors.EVENT_READ)
        if _debug.lifecycle.enabled and (registered or unregistered):
            _debug.lifecycle(
                "prefork.watchdog_rewatched",
                registered=registered,
                unregistered=unregistered,
                watched=len(watched),
            )
        return sel, fds

    def sleep(self, timeout: float | None = None) -> None:
        sel, fds = self._get_watchdog_selector()
        ready = sel.select(self.beat if timeout is None else timeout)
        for key, _ in ready:
            fd = key.fd
            if fd in fds:
                fds[fd].watchdog_time = time.monotonic()
                with contextlib.suppress(BlockingIOError):
                    while data := os.read(fd, 4096):
                        if b"R" in data:
                            fds[fd].ready = True
                            _debug.lifecycle("prefork.worker_ready", pid=fds[fd].pid)
            else:
                empty_pipe(fd)

    def start(self) -> None:
        self.pipe = self.open_pipe()
        self._census.remove_stale()
        _debug.lifecycle(
            "prefork.start",
            pid=self.pid,
            population=self.population,
            http_enable=self.settings.http_enable,
            max_cron_threads=self.settings.max_cron_threads,
            job_workers=self.settings.job_workers,
        )
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGHUP, self.signal_handler)
        signal.signal(signal.SIGCHLD, self.signal_handler)
        signal.signal(signal.SIGTTIN, self.signal_handler)
        signal.signal(signal.SIGTTOU, self.signal_handler)
        signal.signal(signal.SIGQUIT, dumpstacks)
        signal.signal(signal.SIGUSR1, log_ormcache_stats)
        signal.signal(signal.SIGUSR2, log_ormcache_stats)

        if self.settings.http_enable:
            inherited_fd = os.environ.pop("ODOO_HTTP_SOCKET_FD", None)
            if inherited_fd:
                self.socket = socket.socket(fileno=int(inherited_fd))
                self._set_socket_cloexec()
                _debug.lifecycle(
                    "prefork.socket_bound", source="inherited", fd=int(inherited_fd)
                )
                self.logger.info(
                    "HTTP service serving %s:%s on the listening "
                    "socket inherited from the server this one replaced; the "
                    "port was never closed",
                    self.interface,
                    self.port,
                )
            elif self.settings.http_socket_activation:
                self.socket = socket.socket(fileno=SD_LISTEN_FDS_START)
                self._set_socket_cloexec()
                _debug.lifecycle("prefork.socket_bound", source="socket_activation")
                self.logger.info("HTTP service running through socket activation")
            else:
                family = socket.AF_INET
                if ":" in self.interface:
                    family = socket.AF_INET6
                self.socket = socket.socket(family, socket.SOCK_STREAM)
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.socket.setblocking(False)
                self.socket.bind((self.interface, self.port))
                self.socket.listen(8 * self.population)
                _debug.lifecycle(
                    "prefork.socket_bound",
                    source="bind",
                    interface=self.interface,
                    port=self.port,
                    backlog=8 * self.population,
                )
                self.logger.info(
                    "HTTP service running on %s:%s",
                    self.interface,
                    self.port,
                )

    def _spawn_candidate(self, ready_fd: int) -> subprocess.Popen:
        env = dict(os.environ)
        env["ODOO_RELOAD_SUPERVISOR_PID"] = str(self.pid)
        env["ODOO_RELOAD_READY_FD"] = str(ready_fd)
        pass_fds = [ready_fd]
        if self.socket is not None:
            env["ODOO_HTTP_SOCKET_FD"] = str(self.socket.fileno())
            pass_fds.append(self.socket.fileno())
        args = stripped_sys_argv()
        if not args or args[0] not in (sys.executable, Path(sys.executable).name):
            args.insert(0, sys.executable)
        return subprocess.Popen(
            args, env=env, pass_fds=pass_fds, start_new_session=True
        )

    def _await_candidate(
        self, candidate: subprocess.Popen, read_fd: int, timeout: float
    ) -> bool:
        deadline = time.monotonic() + timeout
        with selectors.DefaultSelector() as selector:
            self._reload_reader = (read_fd, selector)
            selector.register(read_fd, selectors.EVENT_READ)
            while time.monotonic() < deadline:
                # Shutdown must not wait for a stuck preload's deadline.
                if any(sig in (signal.SIGINT, signal.SIGTERM) for sig in self.queue):
                    _debug.logic(
                        "prefork.reload.aborted",
                        reason="shutdown_requested",
                        pid=candidate.pid,
                    )
                    return False
                if self._replacement is None:
                    # The first generation still depends on this master
                    # while the candidate preloads. Read queued heartbeats
                    # before enforcing deadlines or recovering capacity.
                    self.sleep(timeout=0)
                    self.reap_exited_workers()
                    self.kill_timed_out_workers()
                    self.spawn_missing_workers()
                    self._publish_census()
                if selector.select(min(0.1, max(0, deadline - time.monotonic()))):
                    promoted = os.read(read_fd, 1) == b"1"
                    _debug.pipeline(
                        "prefork.reload.candidate_answered",
                        pid=candidate.pid,
                        promoted=promoted,
                        waited_s=timeout - (deadline - time.monotonic()),
                    )
                    return promoted and candidate.poll() is None
                if candidate.poll() is not None:
                    return False
        return False

    def reload(self) -> bool:
        """Promote a fresh generation only after its preload and worker startup.

        The original master remains the supervisor across every reload. A
        replacement asks it to reload, avoiding chains of proxy masters and
        keeping the service manager's PID valid after a failed replacement.
        """
        self.logger.info("Reloading server")
        read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
        try:
            self._candidate = self._spawn_candidate(write_fd)
            os.close(write_fd)
            write_fd = -1
            timeout = get_env_float(
                "ODOO_RELOAD_TIMEOUT", RELOAD_TIMEOUT_S, minimum=1.0, logger=self.logger
            )
            _debug.pipeline(
                "prefork.reload.candidate_spawned",
                pid=self._candidate.pid,
                timeout=timeout,
            )
            if not self._await_candidate(self._candidate, read_fd, timeout):
                if any(sig in (signal.SIGINT, signal.SIGTERM) for sig in self.queue):
                    reason = "shutdown_requested"
                    cause = "a shutdown was requested"
                elif self._candidate.poll() is not None:
                    reason = "candidate_exited"
                    cause = (
                        f"the replacement exited with {self._candidate.returncode} "
                        f"before it was ready"
                    )
                else:
                    reason = "timed_out"
                    cause = (
                        f"the replacement was not ready after {timeout:.0f}s "
                        f"(ODOO_RELOAD_TIMEOUT)"
                    )
                self.logger.error("Reload aborted: %s; keeping current workers", cause)
                _debug.logic(
                    "prefork.reload.aborted",
                    reason=reason,
                    returncode=self._candidate.returncode,
                    timeout=timeout,
                )
                return False
            self.logger.info("New server has started")
            _debug.lifecycle(
                "prefork.reload.promoted",
                pid=self._candidate.pid,
                replaced_previous=self._replacement is not None,
            )
            if self._replacement is not None:
                self._stop_generation(self._replacement)
            else:
                self.stop_workers_gracefully()
                self.beat = SUPERVISION_BEAT_S
            self._replacement = self._candidate
            self._candidate = None
            return True
        finally:
            self._reload_reader = None
            os.close(read_fd)
            if write_fd >= 0:
                os.close(write_fd)
            if self._candidate is not None:
                _debug.logic(
                    "prefork.reload.candidate_discarded", pid=self._candidate.pid
                )
                self._stop_generation(self._candidate, graceful=False)
                self._candidate = None

    def _stop_generation(
        self, process: subprocess.Popen, *, graceful: bool = True
    ) -> None:
        """Bound generation shutdown, including its evented subprocess."""
        if not graceful:
            # An unready candidate may be stuck in preload and unable to handle
            # queued signals. Do not pause the healthy generation to drain it.
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            _debug.lifecycle(
                "prefork.generation_stopped", pid=process.pid, graceful=False
            )
            return
        with contextlib.suppress(ProcessLookupError):
            process.terminate()
        try:
            process.wait(timeout=get_graceful_stop_timeout(self.logger) + 10)
        except subprocess.TimeoutExpired:
            self.logger.warning(
                "Generation %s did not stop; killing its process group", process.pid
            )
            _debug.logic("prefork.generation_kill_escalated", pid=process.pid)
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        finally:
            # A crashed master can exit before stopping its descendants.
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            _debug.lifecycle(
                "prefork.generation_stopped",
                pid=process.pid,
                graceful=True,
                returncode=process.returncode,
            )

    def _notify_reload_ready(self) -> None:
        if self._ready_fd is None:
            return
        if _debug.logic.enabled:
            _debug.logic(
                "prefork.reload_readiness",
                http=len(self.workers_http),
                population=self.population,
                cron=len(self.workers_cron),
                job=len(self.workers_job),
                ready=sum(1 for worker in self.workers.values() if worker.ready),
                workers=len(self.workers),
            )
        if len(self.workers_http) < self.population and self.settings.http_enable:
            return
        if len(self.workers_cron) < self.settings.max_cron_threads:
            return
        if len(self.workers_job) < self.settings.job_workers:
            return
        if not all(worker.ready for worker in self.workers.values()):
            return
        fd, self._ready_fd = int(self._ready_fd), None
        try:
            os.write(fd, b"1")
        finally:
            os.close(fd)
        _debug.lifecycle(
            "prefork.reload_ready_signalled",
            supervisor=self._reload_supervisor,
            workers=len(self.workers),
        )

    def _stop_long_polling(self) -> None:
        pid = self.long_polling_pid
        if pid is None:
            return
        self.long_polling_pid = None
        try:
            proc = psutil.Process(pid)
        except psutil.NoSuchProcess:
            _debug.logic("prefork.long_polling_already_gone", pid=pid)
            self._reconcile_long_polling_popen(None)
            return
        timeout_s = get_env_float(
            "ODOO_EVENTED_STOP_TIMEOUT",
            EVENTED_STOP_TIMEOUT_S,
            minimum=0.0,
            logger=self.logger,
        )
        _debug.lifecycle("prefork.long_polling_signalled", pid=pid, timeout=timeout_s)
        with contextlib.suppress(ProcessLookupError):
            os.kill(pid, signal.SIGTERM)
        code: int | None = None
        try:
            code = proc.wait(timeout=timeout_s)
        except psutil.TimeoutExpired:
            self.logger.warning(
                "Evented subprocess (%s) still alive %.0fs after SIGTERM; "
                "sending SIGKILL",
                pid,
                timeout_s,
            )
            _debug.logic("prefork.long_polling_kill_escalated", pid=pid)
            with contextlib.suppress(ProcessLookupError):
                os.kill(pid, signal.SIGKILL)
            with contextlib.suppress(psutil.TimeoutExpired):
                code = proc.wait(timeout=5)
        finally:
            self._reconcile_long_polling_popen(code)
            _debug.lifecycle("prefork.long_polling_stopped", pid=pid, returncode=code)

    def stop_workers_gracefully(self) -> None:
        self.logger.info("Stopping workers gracefully")

        self._stop_long_polling()

        for pid in list(self.workers):
            self.kill_worker(pid, signal.SIGINT)

        self.beat = 0.1
        stop_timeout = get_graceful_stop_timeout(self.logger)
        deadline = time.monotonic() + stop_timeout
        escalated = False
        _debug.pipeline(
            "prefork.stop.workers_signalled",
            workers=len(self.workers),
            timeout=stop_timeout,
            phoenix=_process_state.server_phoenix,
        )
        while self.workers:
            try:
                # Reload also drains workers here. Its outer supervisor loop
                # must observe shutdown even when this nested loop handles it.
                self.apply_pending_signals(draining=True)
            except KeyboardInterrupt:
                self.logger.info("Forced shutdown.")
                _debug.logic("prefork.stop.forced", workers=len(self.workers))
                break

            self.reap_exited_workers()

            if not escalated and time.monotonic() >= deadline:
                escalated = True
                self.logger.warning(
                    "Workers still alive %.0fs after SIGINT; escalating to SIGKILL: %s",
                    stop_timeout,
                    list(self.workers),
                )
                _debug.logic("prefork.stop.escalated", workers=len(self.workers))
                for pid in list(self.workers):
                    with contextlib.suppress(ProcessLookupError):
                        os.kill(pid, signal.SIGKILL)

            self.sleep()
            self.kill_timed_out_workers()

        _debug.pipeline(
            "prefork.stop.workers_drained",
            workers=len(self.workers),
            escalated=escalated,
            seconds=time.monotonic() - (deadline - stop_timeout),
        )

    def stop(self, graceful: bool = True) -> None:
        _debug.lifecycle(
            "prefork.stop",
            graceful=graceful,
            workers=len(self.workers),
            replacement=self._replacement is not None,
        )
        if not self._reload_supervisor:
            notify("STOPPING=1")
        if self._replacement is not None:
            self._stop_generation(self._replacement)
            self._replacement = None
        if self._ready_fd is not None:
            os.close(int(self._ready_fd))
            self._ready_fd = None
        if self.socket:
            self.socket.close()
        try:
            super().stop()
        except Exception as exc:
            self.logger.warning("Exception while running stop hooks", exc_info=True)
            _debug.logic("prefork.stop_hooks_failed", error=type(exc).__name__)
        if graceful:
            self.stop_workers_gracefully()
        else:
            self.logger.info("Stopping forcefully")
            self._stop_long_polling()
        for pid in list(self.workers):
            self.kill_worker(pid, signal.SIGTERM)
        self._close_watchdog_selector()
        self._census.discard()
        pipe, self.pipe = self.pipe, None
        for fd in pipe or ():
            with contextlib.suppress(OSError):
                os.close(fd)
        _debug.lifecycle(
            "prefork.stopped",
            graceful=graceful,
            workers=len(self.workers),
            phoenix=_process_state.server_phoenix,
        )

    def _handle_reload_request(self) -> None:
        # A SIGHUP reached this master.  A replacement generation asks the
        # original supervisor to do the reload, so the chain never grows.
        _process_state.set_phoenix(False)
        _debug.lifecycle("prefork.reload_requested", supervisor=self._reload_supervisor)
        if self._reload_supervisor:
            os.kill(self._reload_supervisor, signal.SIGHUP)
            return
        notify_reloading()
        try:
            self.reload()
        except Exception as exc:
            self.logger.exception("Reload failed; keeping current generation")
            _debug.logic("prefork.reload.failed", error=type(exc).__name__)
        finally:
            # Serving again either way: on the new generation, or still on
            # the one that was never stopped.
            notify_ready()

    def run(self, preload: list[str] | None = None, stop: bool = False) -> int | None:
        try:
            self.start()
            rc = preload_registries(preload)
        except BaseException as exc:
            _debug.logic("prefork.start_failed", error=type(exc).__name__)
            self.stop(False)
            raise

        _debug.pipeline(
            "prefork.preloaded", rc=rc, stop=stop, databases=len(preload or ())
        )
        if stop or rc:
            self.stop()
            return rc

        db.close_all()

        self.logger.debug("starting")
        # Only the process systemd started talks to it: a replacement
        # generation reports through its supervisor's promotion instead.
        speaks = not self._reload_supervisor
        if speaks:
            notify_ready()
        watchdog = Watchdog() if speaks else None
        while True:
            try:
                if watchdog is not None:
                    watchdog.beat()
                self.apply_pending_signals()
                self.reap_exited_workers()
                if self._replacement is not None:
                    code = self._replacement.poll()
                    if code is not None:
                        _debug.logic("prefork.replacement_exited", returncode=code)
                        self.stop()
                        return code if code >= 0 else 128 - code
                    time.sleep(self.beat)
                    continue
                self.kill_timed_out_workers()
                self.spawn_missing_workers()
                self._notify_reload_ready()
                self._publish_census()
                self.sleep()
            except KeyboardInterrupt:
                if _process_state.server_phoenix:
                    self._handle_reload_request()
                    continue
                self.logger.debug("clean stop")
                self.stop()
                break
            except SystemExit:
                raise
            except BaseException as exc:
                self.logger.critical(
                    "Uncaught error in main loop, exiting...", exc_info=exc
                )
                _debug.logic("prefork.main_loop_failed", error=type(exc).__name__)
                self.stop(False)
                return -1
        return None
