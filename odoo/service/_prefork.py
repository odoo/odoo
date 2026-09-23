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
from typing import Any, override

import psutil

from odoo import db
from odoo.libs import backoff
from odoo.libs.debug_log import DebugLog
from odoo.modules.registry import Registry
from odoo.tools.cache import log_ormcache_stats
from odoo.tools.misc import dumpstacks, stripped_sys_argv

from . import _process_state
from ._base_server import CommonServer
from ._census import WorkerCensus
from ._cron import LISTENER_KINDS
from ._env import INHERITED_SOCKET_FD, INHERITED_WEBSOCKET_FD, get_env_float
from ._limits import empty_pipe, get_graceful_stop_timeout
from ._listener import acquire_listener
from ._reload import GenerationHandoff
from ._sdnotify import Watchdog, notify, notify_ready
from ._worker import (
    RECYCLE_CODES,
    WORKER_READY,
    Worker,
    WorkerCron,
    WorkerHTTP,
    WorkerJob,
    WorkerStream,
)
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


def _read_process_title(pid: int) -> str:
    # The worker titles itself with the request or database it is on
    # (`Worker.setproctitle`); this is the one thing the master can still
    # read of a child it is about to kill.
    try:
        title = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return ""
    words = title.replace(b"\0", b" ").decode(errors="replace").strip()
    # Without the setproctitle package the cmdline is argv, which says
    # nothing about the request.
    return words.removeprefix("odoo: ") if words.startswith("odoo: ") else ""


_EXIT_OUTCOMES = (
    "clean",
    "terminated",
    "timeout",
    "crash",
    *RECYCLE_CODES.values(),
)


def _get_exit_outcome(
    status: int, *, policy_kill: bool, recycled_for: str | None = None
) -> str:
    if os.WIFEXITED(status):
        if os.WEXITSTATUS(status) != 0:
            return "crash"
        # Every policy recycle exits 0 on purpose, so the exit code alone
        # cannot tell a leak-driven recycle from a healthy retirement.
        return recycled_for or "clean"
    if policy_kill:
        return "timeout"
    if os.WIFSIGNALED(status) and os.WTERMSIG(status) == signal.SIGTERM:
        return "terminated"
    return "crash"


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
                "stream": len(self.workers_stream),
            },
            "worker_population": self.population,
            "worker_generation": self.generation,
            "worker_exits": dict(self._exits),
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
        self.listener_timeouts: dict[str, float | None] = {
            kind.name: kind.real_time_budget(settings) or None
            for kind in LISTENER_KINDS
        }
        """What the master's watchdog allows each sweep loop, by kind.

        One mapping rather than a `cron_timeout` and a `job_timeout`: each
        worker asks its own `ListenerKind` for the same budget, so a pair of
        attributes could only restate it and, being one line apart, could
        restate it wrongly.
        """
        self.beat: float = SUPERVISION_BEAT_S
        self.pipe: tuple[int, int] | None = None
        self.socket: socket.socket | None = None
        self.websocket_socket: socket.socket | None = None
        self.workers_http: dict[int, WorkerHTTP] = {}
        self.workers_cron: dict[int, WorkerCron] = {}
        self.workers_job: dict[int, WorkerJob] = {}
        self.workers_stream: dict[int, WorkerStream] = {}
        self.workers: dict[int, Worker] = {}
        self._killed_workers: dict[int, Worker] = {}
        # Worker exits since start by outcome, for the census and /metrics:
        # a crash loop reads as a rising `crash` next to a flat `clean`.
        self._exits: dict[str, int] = dict.fromkeys(_EXIT_OUTCOMES, 0)
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
        self.handoff = GenerationHandoff(self)
        self.is_reload_watcher_owner = not self.handoff.is_supervised
        _debug.lifecycle(
            "prefork.created",
            population=self.population,
            timeout=self.timeout,
            listener_timeouts=self.listener_timeouts,
            limit_request=self.limit_request,
            reload_supervisor=self.handoff.supervisor,
            reload_ready_fd=self.handoff.awaits_ready,
        )

    def open_pipe(self) -> tuple[int, int]:
        return os.pipe2(os.O_NONBLOCK | os.O_CLOEXEC)

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
        keep = set(new_worker.pipe_fds)
        for sibling in self.workers.values():
            for fd in sibling.pipe_fds:
                if fd not in keep:
                    with contextlib.suppress(OSError):
                        os.close(fd)
        for fd in self.pipe or ():
            if fd not in keep:
                with contextlib.suppress(OSError):
                    os.close(fd)
        self._close_watchdog_selector()
        self.handoff.close_in_child()
        # The websocket listener is the evented child's, handed over at its
        # spawn; a forked worker holding a copy would keep the port bound
        # past this master's death.
        if self.websocket_socket is not None:
            self.websocket_socket.close()
            self.websocket_socket = None
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
        env = dict(os.environ)
        pass_fds: list[int] = []
        if self.websocket_socket is not None:
            env[INHERITED_SOCKET_FD] = str(self.websocket_socket.fileno())
            pass_fds.append(self.websocket_socket.fileno())
        try:
            popen = subprocess.Popen(cmd, env=env, pass_fds=pass_fds)
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
            self.workers_stream.pop(pid, None)
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
            if sig in (signal.SIGTTIN, signal.SIGTTOU):
                self.handoff.forward(sig)
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
        if self.handoff.record_exit(pid, status):
            return
        policy_kill = False
        recycled_for: str | None = None
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
            # A reason written just before the exit may still be in the pipe.
            self._read_worker_pipe(worker.watchdog_pipe[0], worker)
            recycled_for = worker.recycled_for
            # The watchdog's SIGKILL of a worker that had reported ready is a
            # policy the master applied to one long request, not a crash to
            # back off from; the same kill on a worker that never got there
            # is a worker that hangs at boot, which is what the back-off is for.
            policy_kill = killed_by_master and bool(worker.ready)
        outcome = _get_exit_outcome(
            status, policy_kill=policy_kill, recycled_for=recycled_for
        )
        self._exits[outcome] += 1
        _debug.lifecycle(
            "prefork.worker_exited",
            kind=name,
            pid=pid,
            lifetime_s=lifetime,
            status=status,
            outcome=outcome,
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
        crashed_by_signal = outcome == "crash" and not exited_nonzero
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
                doing = _read_process_title(pid)
                self.logger.error(
                    "%s (%s) timeout after %ss%s",
                    worker.__class__.__name__,
                    pid,
                    worker.watchdog_timeout,
                    f" while {doing}" if doing else "",
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
            or len(self.workers_stream) < self.settings.stream_workers
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
                stream=len(self.workers_stream),
                stream_workers=self.settings.stream_workers,
                long_polling=self.long_polling_pid is not None,
                http_enable=self.settings.http_enable,
            )

        def check_registries() -> None:
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
        while len(self.workers_stream) < self.settings.stream_workers and not (
            self._is_respawn_held(WorkerStream.__name__)
        ):
            check_registries()
            if self.spawn_worker(WorkerStream, self.workers_stream) is None:
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
                self._read_worker_pipe(fd, fds[fd])
            else:
                empty_pipe(fd)

    @staticmethod
    def _read_worker_pipe(fd: int, worker: Worker) -> None:
        """Drain a worker's heartbeats, and keep what they say.

        The bytes are a beat (`.`), the one-off readiness mark, and the reason
        a worker is about to stop.  The last has to survive being read after
        the child is already gone, which is why it is taken here and again
        when the exit is accounted for.
        """
        with contextlib.suppress(BlockingIOError, OSError):
            while data := os.read(fd, 4096):
                if WORKER_READY in data:
                    if not worker.ready:
                        _debug.lifecycle("prefork.worker_ready", pid=worker.pid)
                    worker.ready = True
                for code, reason in RECYCLE_CODES.items():
                    if code in data:
                        worker.recycled_for = reason
                        _debug.lifecycle(
                            "prefork.worker_recycling", pid=worker.pid, reason=reason
                        )

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
            self.socket, _ = acquire_listener(
                self.interface,
                self.port,
                backlog=8 * self.population,
                activated=self.settings.http_socket_activation,
                logger=self.logger,
            )
            # The websocket port is the master's too: the evented child
            # adopts it, so its restarts and this master's reloads leave the
            # port bound and the connections that arrive meanwhile queued.
            self.websocket_socket, _ = acquire_listener(
                self.interface,
                self.settings.gevent_port,
                backlog=socket.SOMAXCONN,
                what="Websocket",
                inherited_fd=INHERITED_WEBSOCKET_FD,
                activated=self.settings.websocket_socket_activation,
                activated_fd=SD_LISTEN_FDS_START + 1,
                logger=self.logger,
            )

    def describe_capacity(self) -> str:
        settings = self.settings
        if not settings.http_enable:
            http = "no HTTP"
        else:
            http = (
                f"HTTP {self.interface}:{self.port} ({self.population} workers), "
                f"websocket {self.interface}:{settings.gevent_port}"
            )
        return (
            f"{http}, {settings.max_cron_threads} cron worker(s), "
            f"{settings.job_workers} job worker(s), "
            f"{settings.stream_workers} stream worker(s); limit_request {self.limit_request}, "
            f"limit_time_cpu {settings.limit_time_cpu}s"
        )

    @property
    def shutdown_requested(self) -> bool:
        return any(sig in (signal.SIGINT, signal.SIGTERM) for sig in self.queue)

    def supervise_once(self) -> None:
        # One supervision pass without the beat's sleep: queued heartbeats
        # first, then deadlines, then capacity.
        self.sleep(timeout=0)
        self.reap_exited_workers()
        self.kill_timed_out_workers()
        self.spawn_missing_workers()
        self._publish_census()

    def reload(self) -> bool:
        return self.handoff.promote()

    def retire_own_generation(self) -> None:
        self.stop_workers_gracefully()
        self.beat = SUPERVISION_BEAT_S

    def _is_fully_staffed(self) -> bool:
        if len(self.workers_http) < self.population and self.settings.http_enable:
            return False
        if len(self.workers_cron) < self.settings.max_cron_threads:
            return False
        if len(self.workers_job) < self.settings.job_workers:
            return False
        if len(self.workers_stream) < self.settings.stream_workers:
            return False
        return all(worker.ready for worker in self.workers.values())

    def _notify_reload_ready(self) -> None:
        if not self.handoff.awaits_ready:
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
        if self._is_fully_staffed():
            self.handoff.report_ready()

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

    @override
    def stop(self, graceful: bool = True) -> None:
        _debug.lifecycle(
            "prefork.stop",
            graceful=graceful,
            workers=len(self.workers),
            replacement=self.handoff.replacement is not None,
        )
        if not self.handoff.is_supervised:
            notify("STOPPING=1")
        self.handoff.stop()
        for sock in (self.socket, self.websocket_socket):
            if sock is not None:
                sock.close()
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
        speaks = not self.handoff.is_supervised
        self.log_ready()
        if speaks:
            notify_ready()
        watchdog = Watchdog() if speaks else None
        while True:
            try:
                if watchdog is not None:
                    watchdog.beat()
                self.apply_pending_signals()
                self.reap_exited_workers()
                if self.handoff.replacement is not None:
                    code = self.handoff.replacement.poll()
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
                    self.handoff.request()
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
