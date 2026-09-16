from __future__ import annotations

import contextlib
import logging
import os
import random
import signal
import threading
import time
from typing import Any

import psutil
import psycopg

from odoo import db
from odoo.db import PoolError
from odoo.libs.debug_log import DebugLog
from odoo.libs.worker_thread import as_worker_thread, current_worker_thread
from odoo.modules.registry import Registry
from odoo.tools.cache import log_ormcache_stats
from odoo.tools.misc import dumpstacks

from . import _process_state
from ._base_server import SIGHUP_AVAILABLE, CommonServer
from ._cron import (
    CRON_NOTIFY_JITTER_MAX_S,
    CRON_POLL_INTERVAL_S,
    CRON_TRIGGER_CHANNEL,
    JOB_QUEUE_CHANNEL,
    CronListener,
    CronSchedule,
    ReconnectBackoff,
    drain_swept_database,
)
from ._env import IS_POSIX, IS_WINDOWS
from ._limits import describe_thread_work, get_graceful_stop_timeout
from ._sdnotify import Watchdog, notify, notify_ready, notify_reloading
from .httpd import ThreadedHTTPServer
from .lifecycle import preload_registries, restart

_logger = logging.getLogger("odoo.service.server")
_debug = DebugLog(__name__)

_RECYCLE_MAX_AGE = "get_max_age"
_RECYCLE_CONN_LOST = "connection_lost"
_RECYCLE_STOP = "stop"

LISTENER_JOIN_TIMEOUT_S = 1.0
"""The least `stop()` waits for the cron and job threads to close their
listener sessions once the HTTP drain has spent the graceful-stop bound; a
thread mid-job gets the rest of that bound, as a prefork cron worker does."""

LIMIT_MONITOR_INTERVAL_S = 5.0

LIMIT_GRACE_PERIOD_S = 60.0
"""How long a thread over its limit may wait for other requests to finish.

Its own constant.  This borrowed the cron poll interval, which has nothing to
do with how long to let in-flight HTTP requests drain; the two shared a number
and so could not be tuned apart.
"""

_TIME_LIMITED_THREAD_TYPES = ("http", "cron", "job")
"""Thread kinds `check_limits` may recycle the server for.

"websocket" is deliberately absent.  `bus/websocket.py` re-labels the request
thread the moment it starts serving frames, and a websocket is long-lived by
design -- left in this list it would trip `limit_time_real` and reload the
server under every connected client.
"""

_REPORTED_THREAD_TYPES = (*_TIME_LIMITED_THREAD_TYPES, "websocket")
"""Thread kinds `get_metrics()` counts, which is a different question.

An operator running --workers 0 wants to see the websocket threads precisely
because they are long-lived: they hold a thread and a connection each, and
they were invisible while the two lists were one.
"""

_SIGXCPU_EXIT_CODE = 128 + getattr(signal, "SIGXCPU", 24)


def _get_http_server_metrics(httpd: ThreadedHTTPServer | None) -> dict[str, Any]:
    by_type: dict[str, int] = {}
    for thread in threading.enumerate():
        kind = getattr(thread, "type", None)
        if kind in _REPORTED_THREAD_TYPES:
            by_type[kind] = by_type.get(kind, 0) + 1
    return {
        "threads": {k: by_type.get(k, 0) for k in _REPORTED_THREAD_TYPES},
        "http_threads_max": httpd.max_http_threads if httpd else 0,
    }


_CONSOLE_EVENT_SIGNALS = {
    0: signal.SIGINT,  # CTRL_C_EVENT
    1: signal.SIGINT,  # CTRL_BREAK_EVENT
    2: signal.SIGTERM,  # CTRL_CLOSE_EVENT
    5: signal.SIGTERM,  # CTRL_LOGOFF_EVENT
    6: signal.SIGTERM,  # CTRL_SHUTDOWN_EVENT
}


class ThreadedServer(CommonServer):
    flavor = "threaded"

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self.quit_signals_received = 0

        self.httpd: ThreadedHTTPServer | None = None
        self.limits_reached_threads: set[threading.Thread] = set()
        self._overrun_start_times: dict[threading.Thread, float] = {}
        self._cancelled_overruns: dict[threading.Thread, float] = {}
        self._overruns_cancelled = 0
        self.limit_reached_time: float | None = None
        self._stop_after_init = False
        self._listener_threads: list[threading.Thread] = []
        self._listener_stop = threading.Event()
        self._listener_stop_pipe: tuple[int, int] | None = None

    def get_metrics(self) -> dict[str, Any]:
        return {
            **_get_http_server_metrics(self.httpd),
            "limits_reached_threads": len(self.limits_reached_threads),
            "overruns_cancelled": self._overruns_cancelled,
        }

    def describe_capacity(self) -> str:
        settings = self.settings
        http = (
            f"HTTP {self.interface}:{self.port} ({self.httpd.max_http_threads} threads)"
            if self.httpd is not None
            else "no HTTP"
        )
        return (
            f"{http}, {settings.max_cron_threads} cron thread(s), "
            f"{settings.job_workers} job thread(s)"
        )

    def signal_handler(self, sig: int, frame: Any) -> None:
        if sig in [signal.SIGINT, signal.SIGTERM]:
            self.quit_signals_received += 1
            if self.quit_signals_received > 1:
                os.write(2, b"Forced shutdown.\n")
                os._exit(0)
            raise KeyboardInterrupt
        if hasattr(signal, "SIGXCPU") and sig == signal.SIGXCPU:
            os.write(2, b"CPU time limit exceeded! Shutting down immediately\n")
            os._exit(_SIGXCPU_EXIT_CODE)
        elif SIGHUP_AVAILABLE and sig == signal.SIGHUP:
            if self.quit_signals_received:
                return
            _process_state.set_phoenix(True)
            self.quit_signals_received += 1
            raise KeyboardInterrupt

    def _handle_console_event(self, event: int) -> bool:
        # A Windows console event is not a signal number: CTRL_C_EVENT is 0
        # and CTRL_CLOSE_EVENT happens to be 2, SIGINT's value, which is the
        # only reason the old `signal_handler(event, None)` ever stopped
        # anything.  Handled means True, so the console does not go on to
        # terminate the process before `stop()` runs.
        sig = _CONSOLE_EVENT_SIGNALS.get(event)
        if sig is None:
            return False
        self.signal_handler(sig, None)
        return True

    def check_limits(self) -> None:
        Registry._evict_idle_registries()
        memory_over_limit = self.get_memory_over_soft_limit() is not None

        now = time.monotonic()
        settings = self.settings
        watched = 0  # debuglog
        longest_s = 0.0  # debuglog
        for thread in threading.enumerate():
            thread_type = getattr(thread, "type", None)
            if thread_type not in _TIME_LIMITED_THREAD_TYPES:
                continue
            start_time = getattr(thread, "start_time", None)
            if not start_time:
                continue
            elapsed = now - start_time
            watched += 1  # debuglog
            longest_s = max(longest_s, elapsed)  # debuglog
            budget = settings.get_real_time_budget(thread_type)
            if budget <= 0 or elapsed <= budget:
                continue
            doing = describe_thread_work(thread)
            if self._cancelled_overruns.get(thread) != start_time:
                # First verdict on this unit of work: cancel what it is
                # running in PostgreSQL and give it one monitor pass to
                # return.  Most overruns are one query, and the client gets
                # an error instead of the whole server reloading under
                # everyone.
                self._cancelled_overruns[thread] = start_time
                self._overruns_cancelled += 1
                cancelled = self._cancel_thread_queries(thread)
                self.logger.warning(
                    "Thread %s real time limit (%.1f/%ds) reached%s; cancelled "
                    "%d running quer%s, reloading if it does not return",
                    thread,
                    elapsed,
                    budget,
                    f" while {doing}" if doing else "",
                    cancelled,
                    "y" if cancelled == 1 else "ies",
                )
                _debug.logic(
                    "server.thread_over_limit",
                    thread=thread.name,
                    type=thread_type,
                    elapsed_s=elapsed,
                    limit_s=budget,
                    doing=doing,
                    cancelled=cancelled,
                )
                continue
            if thread in self.limits_reached_threads:
                continue
            self.logger.warning(
                "Thread %s is still on the same work %.1fs after its queries were "
                "cancelled%s; reloading",
                thread,
                elapsed,
                f" ({doing})" if doing else "",
            )
            _debug.logic(
                "server.thread_stuck_after_cancel",
                thread=thread.name,
                type=thread_type,
                elapsed_s=elapsed,
            )
            self.limits_reached_threads.add(thread)
            self._overrun_start_times[thread] = start_time
        # The verdict stands for the unit of work it was given on: the end of
        # that request, sweep or job clears it, as does the thread's exit.
        for thread in list(self._cancelled_overruns):
            if not thread.is_alive() or self._overrun_work_finished(
                thread, self._cancelled_overruns[thread]
            ):
                del self._cancelled_overruns[thread]
        for thread in list(self.limits_reached_threads):
            if not thread.is_alive() or self._overrun_work_finished(
                thread, self._overrun_start_times.get(thread)
            ):
                self.limits_reached_threads.remove(thread)
                self._overrun_start_times.pop(thread, None)
                _debug.lifecycle(
                    "server.thread_overrun_cleared",
                    thread=thread.name,
                    alive=thread.is_alive(),
                    pending=len(self.limits_reached_threads),
                )
        if _debug.perf.enabled and watched:
            _debug.perf.count(
                "server.threads_sampled",
                watched=watched,
                longest_s=longest_s,
                over_limit=len(self.limits_reached_threads),
                memory_over_limit=memory_over_limit,
            )
        if self.limits_reached_threads or memory_over_limit:
            _debug.logic(
                "server.limits_reached",
                threads=len(self.limits_reached_threads),
                memory_over_limit=memory_over_limit,
                since_s=0.0
                if not self.limit_reached_time
                else now - self.limit_reached_time,
            )
            self.limit_reached_time = self.limit_reached_time or now
        else:
            self.limit_reached_time = None

    @staticmethod
    def _overrun_work_finished(thread: threading.Thread, started: float | None) -> bool:
        return getattr(thread, "start_time", None) != started

    def _cancel_thread_queries(self, thread: threading.Thread) -> int:
        try:
            return db.cancel_queries_of(thread.name)
        except Exception as exc:
            self.logger.warning(
                "Could not cancel the queries of %s", thread.name, exc_info=True
            )
            _debug.logic(
                "server.cancel_failed", thread=thread.name, error=type(exc).__name__
            )
            return 0

    def run_cron_thread(self, number: int) -> None:
        from odoo.addons.base.models.ir_cron import IrCron

        self._run_listener_thread(
            number,
            channel=CRON_TRIGGER_CHANNEL,
            process_jobs=IrCron._process_jobs,
            label="cron",
            max_age=self.settings.limit_time_worker_cron,
        )

    def run_job_thread(self, number: int) -> None:
        from odoo.addons.base.models.ir_job import IrJob

        self._run_listener_thread(
            number,
            channel=JOB_QUEUE_CHANNEL,
            process_jobs=IrJob._process_jobs,
            label="job",
            max_age=self.settings.job_max_age,
        )

    def _run_due_jobs(
        self,
        db_names: list[str],
        process_jobs: Any,
        cron_logger: logging.Logger,
    ) -> None:
        release = len(db_names) > 1
        _debug.pipeline(
            "server.jobs_sweep",
            databases=len(db_names),
            release=release,
            kind=getattr(process_jobs, "__qualname__", None),
        )
        thread = current_worker_thread()
        for db_name in db_names:
            thread.start_time = time.monotonic()
            try:
                with _debug.perf(
                    "server.process_jobs",
                    db=db_name,
                    kind=getattr(process_jobs, "__qualname__", None),
                ):
                    process_jobs(db_name)
            except Exception:
                cron_logger.warning(
                    "Uncaught error for database %s", db_name, exc_info=True
                )
                _debug.logic("server.jobs_failed", db=db_name)
            finally:
                thread.start_time = None
                if release:
                    drain_swept_database(db_name)

    def _poll_cron_channel(
        self,
        listener: CronListener,
        number: int,
        process_jobs: Any,
        cron_logger: logging.Logger,
        max_age: int,
    ) -> str:
        schedule = CronSchedule()
        alive_time = time.monotonic()
        first_pass = True
        _debug.lifecycle(
            "server.cron.polling",
            number=number,
            max_age=max_age,
            poll_interval_s=CRON_POLL_INTERVAL_S + number,
        )
        while max_age <= 0 or (time.monotonic() - alive_time) <= max_age:
            woken = listener.wait(0 if first_pass else CRON_POLL_INTERVAL_S + number)
            first_pass = False
            if self._listener_stop.is_set():
                return _RECYCLE_STOP
            if woken:
                time.sleep(random.uniform(0, CRON_NOTIFY_JITTER_MAX_S))
            try:
                notified = listener.drain()
            except Exception as exc:
                if listener.connection_lost:
                    _debug.logic("server.cron.connection_lost", number=number)
                    return _RECYCLE_CONN_LOST
                _debug.logic(
                    "server.cron.drain_failed", number=number, error=type(exc).__name__
                )
                raise

            db_names = schedule.get_due_databases(notified)
            if _debug.pipeline.enabled and notified:
                _debug.pipeline(
                    "server.cron.notified",
                    number=number,
                    notified=len(notified),
                    due=len(db_names),
                )
            if not db_names:
                continue

            cron_logger.debug("polling for jobs (notified: %s)", notified)
            self._run_due_jobs(db_names, process_jobs, cron_logger)
        return _RECYCLE_MAX_AGE

    def _run_listener_thread(
        self,
        number: int,
        *,
        channel: str,
        process_jobs: Any,
        label: str,
        max_age: int,
    ) -> None:
        cron_logger = self.logger.getChild(f"{label}{number}")
        cron_logger.info("Alive")
        _debug.lifecycle(
            "server.cron.thread_started",
            label=label,
            number=number,
            channel=channel,
            max_age=max_age,
            thread=threading.current_thread().name,
        )

        backoff = ReconnectBackoff(cron_logger)
        listener = CronListener(
            channel, cron_logger, extra_read_fd=self._get_listener_stop_fd()
        )
        while not self._listener_stop.is_set():
            try:
                listener.connect()
                reason = self._poll_cron_channel(
                    listener, number, process_jobs, cron_logger, max_age
                )
                backoff.reset()
                _debug.lifecycle(
                    "server.cron.listener_recycled",
                    label=label,
                    number=number,
                    reason=reason,
                    max_age=max_age,
                )
                if reason == _RECYCLE_CONN_LOST:
                    cron_logger.warning("Postgres connection lost, reconnecting...")
                elif reason == _RECYCLE_MAX_AGE:
                    cron_logger.info(
                        "Max age (%ss) reached, recycling pg connection",
                        max_age,
                    )
            except SystemExit:
                raise
            except (psycopg.OperationalError, PoolError) as exc:
                _debug.logic(
                    "server.cron.listener_failed",
                    label=label,
                    number=number,
                    error=type(exc).__name__,
                    kind="pg_unavailable",
                )
                backoff.wait_after_failure(
                    "Postgres unavailable", exc, self._listener_stop.wait
                )
            except Exception as exc:
                cron_logger.critical("Uncaught error in cron main loop", exc_info=True)
                _debug.logic(
                    "server.cron.listener_failed",
                    label=label,
                    number=number,
                    error=type(exc).__name__,
                    kind="uncaught",
                )
                backoff.wait_after_failure(
                    "Cron main loop", exc, self._listener_stop.wait
                )
            finally:
                listener.close()
        _debug.lifecycle("server.cron.thread_stopped", label=label, number=number)

    def _get_listener_stop_fd(self) -> int:
        # One pipe wakes every listener out of its LISTEN wait when the server
        # stops, so each closes its own session instead of leaving it to the
        # kernel at exit.
        if self._listener_stop_pipe is None:
            self._listener_stop_pipe = os.pipe2(os.O_NONBLOCK | os.O_CLOEXEC)
        return self._listener_stop_pipe[0]

    def _stop_listener_threads(self, deadline: float) -> None:
        self._listener_stop.set()
        if self._listener_stop_pipe is not None:
            with contextlib.suppress(OSError):
                os.write(self._listener_stop_pipe[1], b".")
        floor = time.monotonic() + LISTENER_JOIN_TIMEOUT_S
        deadline = max(deadline, floor)
        # A thread the limit monitor already flagged over its budget is what
        # this reload is leaving behind; it gets the floor, not the bound.
        waited = [
            t
            for t in self._listener_threads
            if t.is_alive() and t not in self.limits_reached_threads
        ]
        if waited and deadline - time.monotonic() > LISTENER_JOIN_TIMEOUT_S:
            self.logger.info(
                "Waiting up to %.0fs for %d listener thread(s) to finish their job",
                deadline - time.monotonic(),
                len(waited),
            )
        for thread in self._listener_threads:
            until = deadline if thread in waited else floor
            thread.join(max(until - time.monotonic(), 0))
        alive = [t.name for t in self._listener_threads if t.is_alive()]
        if alive:
            self.logger.warning(
                "%d listener thread(s) still mid-job at shutdown, left to the "
                "process exit (ODOO_GRACEFUL_STOP_TIMEOUT): %s",
                len(alive),
                ", ".join(alive),
            )
        _debug.lifecycle(
            "server.threaded.listeners_stopped",
            threads=len(self._listener_threads),
            alive=len(alive),
        )
        pipe, self._listener_stop_pipe = self._listener_stop_pipe, None
        for fd in pipe or ():
            with contextlib.suppress(OSError):
                os.close(fd)

    def spawn_cron_threads(self) -> None:
        for i in range(self.settings.max_cron_threads):
            t = threading.Thread(
                target=self.run_cron_thread,
                args=(i,),
                name=f"odoo.service.cron.cron{i}",
                daemon=True,
            )
            as_worker_thread(t).type = "cron"
            self._listener_threads.append(t)
            t.start()
        _debug.lifecycle(
            "server.threads_spawned", kind="cron", count=self.settings.max_cron_threads
        )

    def spawn_job_threads(self) -> None:
        for i in range(self.settings.job_workers):
            t = threading.Thread(
                target=self.run_job_thread,
                args=(i,),
                name=f"odoo.service.job.job{i}",
                daemon=True,
            )
            as_worker_thread(t).type = "job"
            self._listener_threads.append(t)
            t.start()
        _debug.lifecycle(
            "server.threads_spawned", kind="job", count=self.settings.job_workers
        )

    def spawn_http_server(self) -> None:
        try:
            self.httpd = ThreadedHTTPServer(self.interface, self.port, self.app)
        except SystemExit:
            self.logger.critical(
                "Failed to bind the HTTP server to %s:%s -- the address is "
                "unavailable (already in use, or not permitted). Nothing will "
                "be served; see the message on stderr for the OS-level cause.",
                self.interface,
                self.port,
            )
            _debug.logic(
                "server.httpd_bind_failed", interface=self.interface, port=self.port
            )
            raise
        threading.Thread(
            target=self.httpd.serve_forever,
            name="odoo.service.httpd",
            daemon=True,
        ).start()
        _debug.lifecycle(
            "server.httpd_spawned",
            interface=self.interface,
            port=self.port,
            max_http_threads=getattr(self.httpd, "max_http_threads", None),
        )

    def start(self, stop: bool = False) -> None:
        self.logger.debug("Setting signal handlers")
        if IS_POSIX:
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
            signal.signal(signal.SIGHUP, self.signal_handler)
            signal.signal(signal.SIGXCPU, self.signal_handler)
            signal.signal(signal.SIGQUIT, dumpstacks)
            signal.signal(signal.SIGUSR1, log_ormcache_stats)
            signal.signal(signal.SIGUSR2, log_ormcache_stats)
        elif IS_WINDOWS:
            import win32api

            win32api.SetConsoleCtrlHandler(self._handle_console_event, 1)

        settings = self.settings
        if IS_POSIX and settings.limit_time_cpu > 0:
            self.logger.info(
                "limit_time_cpu=%ss is not enforced with workers=0: the CPU "
                "budget is armed per worker process (RLIMIT_CPU in "
                "odoo.service._worker), and a threaded server has none. Use "
                "limit_time_real, which this server does enforce per thread.",
                settings.limit_time_cpu,
            )

        serve_http = settings.http_enable and (settings.test_enable or not stop)
        _debug.lifecycle("server.threaded.start", http=serve_http, stop_after_init=stop)
        if serve_http:
            self.spawn_http_server()

    def stop(self) -> None:
        _debug.lifecycle(
            "server.threaded.stop",
            phoenix=_process_state.server_phoenix,
            stop_after_init=self._stop_after_init,
        )
        if _process_state.server_phoenix:
            self.logger.info("Initiating server reload")
            notify_reloading()
        elif self._stop_after_init:
            self.logger.info("Initialization done, shutting down")
        else:
            self.logger.info("Initiating shutdown")
            notify("STOPPING=1")
            self.logger.info(
                "Hit CTRL-C again or send a second signal to force the shutdown."
            )

        # One graceful-stop bound covers the HTTP drain and the listener
        # threads together, as the prefork master gives all its workers one.
        # Listeners are told first so their sessions close while the HTTP
        # drain runs; they are joined after it, for whatever is left.
        timeout = get_graceful_stop_timeout(self.logger)
        deadline = time.monotonic() + timeout
        self._listener_stop.set()
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.drain(timeout, stuck=self._count_stuck_http_threads())
            if _process_state.server_phoenix and IS_POSIX:
                self.httpd.bequeath_listener()
            self.httpd.server_close()

        super().stop()
        self._stop_listener_threads(deadline)

        db.close_all()

        current_process = psutil.Process()
        children = current_process.children(recursive=False)
        if _debug.logic.enabled and children:
            _debug.logic("server.threaded.children_alive", children=len(children))
        for child in children:
            self.logger.info(
                "A child process was found, pid is %s, process may hang", child
            )

        self.logger.debug("--")
        logging.shutdown()

    def _count_stuck_http_threads(self) -> int:
        # A thread over its time limit is what a reload is leaving behind, so
        # the drain does not wait for it.
        return sum(
            1
            for thread in self.limits_reached_threads
            if thread.is_alive() and getattr(thread, "type", None) == "http"
        )

    def run(self, preload: list[str] | None = None, stop: bool = False) -> int | None:
        rc: int | None = None
        self._stop_after_init = stop
        try:
            self.start(stop=stop)
            rc = preload_registries(preload)
            _debug.pipeline(
                "server.threaded.preloaded",
                rc=rc,
                stop=stop,
                databases=len(preload or ()),
            )

            if stop:
                if self.settings.test_enable:
                    self._log_test_reports()
                return rc

            if rc:
                return rc

            self.spawn_cron_threads()
            self.spawn_job_threads()
            self.log_ready()
            notify_ready()
            watchdog = Watchdog()

            while self.quit_signals_received == 0:
                watchdog.beat()
                self.check_limits()
                if self.limit_reached_time:
                    has_other_valid_requests = self._has_other_http_requests()
                    if (
                        not has_other_valid_requests
                        or (time.monotonic() - self.limit_reached_time)
                        > LIMIT_GRACE_PERIOD_S
                    ):
                        self.logger.info(
                            "Dumping stacktrace of limit exceeding threads before reloading"
                        )
                        _debug.logic(
                            "server.threaded.reload_for_limits",
                            other_requests=has_other_valid_requests,
                            since_s=time.monotonic() - self.limit_reached_time,
                            threads=len(self.limits_reached_threads),
                        )
                        dumpstacks(
                            thread_idents={
                                thread.ident
                                for thread in self.limits_reached_threads
                                if thread.ident is not None
                            }
                        )
                        self.reload()
                    else:
                        _debug.logic(
                            "server.threaded.reload_deferred",
                            since_s=time.monotonic() - self.limit_reached_time,
                            grace_s=LIMIT_GRACE_PERIOD_S,
                            threads=len(self.limits_reached_threads),
                        )
                        time.sleep(watchdog.bound(1))
                else:
                    time.sleep(watchdog.bound(LIMIT_MONITOR_INTERVAL_S))
        except KeyboardInterrupt:
            pass
        finally:
            _debug.lifecycle(
                "server.threaded.run_finished",
                rc=rc,
                stop=stop,
                quit_signals=self.quit_signals_received,
                phoenix=_process_state.server_phoenix,
            )
            self.stop()
        return rc if stop else None

    def _log_test_reports(self) -> None:
        from odoo.tests.result import _logger as logger
        from odoo.tests.result import assertion_report

        with Registry.registries._lock:
            for db_name in Registry.registries:
                report = assertion_report(db_name)
                if report is None:
                    continue
                if not report.wasSuccessful():
                    log = logger.error
                elif not report.testsRun:
                    log = logger.warning
                else:
                    log = logger.info
                log("%s when loading database %r", report, db_name)
                _debug.pipeline(
                    "server.threaded.test_report",
                    db=db_name,
                    tests_run=report.testsRun,
                    successful=report.wasSuccessful(),
                )

    def _has_other_http_requests(self) -> bool:
        return any(
            t not in self.limits_reached_threads
            for t in threading.enumerate()
            if getattr(t, "type", None) == "http"
        )

    def reload(self) -> None:
        _debug.lifecycle("server.threaded.reload", pid=self.pid)
        restart()


class WebsocketServer(CommonServer):
    # `evented` is the `odoo-bin evented` subcommand, the `odoo.evented` flag
    # and the metric label; the name says what the process is: the
    # websocket port, on threads.  Gevent left the fork with the http rewrite.
    flavor = "evented"
    port_setting = "gevent_port"

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self.httpd: ThreadedHTTPServer | None = None
        self.ppid = os.getppid()

    def get_memory_soft_limit(self) -> int:
        return self.settings.limit_memory_soft_gevent or self.settings.limit_memory_soft

    def describe_capacity(self) -> str:
        threads = self.httpd.max_http_threads if self.httpd is not None else 0
        return f"websocket {self.interface}:{self.port} ({threads} threads)"

    def get_metrics(self) -> dict[str, Any]:
        # The same pool as the threaded server, on the websocket port: an
        # operator wants its long-lived websocket threads counted too.
        return _get_http_server_metrics(self.httpd)

    def check_limits(self) -> None:
        Registry._evict_idle_registries()
        should_restart = False
        new_ppid = os.getppid()
        if self.ppid != new_ppid:
            self.logger.warning("Parent changed: %s -> %s", self.ppid, new_ppid)
            should_restart = True
        memory_over_limit = self.get_memory_over_soft_limit() is not None
        if memory_over_limit:
            should_restart = True
        if should_restart:
            _debug.lifecycle(
                "server.evented.restart_requested",
                pid=self.pid,
                parent_changed=self.ppid != new_ppid,
                memory_over_limit=memory_over_limit,
            )
            os.kill(self.pid, signal.SIGTERM)

    def run_watchdog(self, beat: int = 4) -> None:
        self.ppid = os.getppid()
        _debug.lifecycle("server.evented.watchdog_started", ppid=self.ppid, beat=beat)
        while True:
            try:
                self.check_limits()
            except Exception as exc:
                self.logger.warning(
                    "Evented watchdog check failed; retrying in %ss",
                    beat,
                    exc_info=True,
                )
                _debug.logic("server.evented.watchdog_failed", error=type(exc).__name__)
            time.sleep(beat)

    def _quit_signal_handler(self, sig: int, frame: Any) -> None:
        raise KeyboardInterrupt

    def start(self) -> None:
        if IS_POSIX:
            signal.signal(signal.SIGINT, self._quit_signal_handler)
            signal.signal(signal.SIGTERM, self._quit_signal_handler)
            signal.signal(signal.SIGQUIT, dumpstacks)
            signal.signal(signal.SIGUSR1, log_ormcache_stats)
            signal.signal(signal.SIGUSR2, log_ormcache_stats)

        try:
            self.httpd = ThreadedHTTPServer(
                self.interface, self.port, self.app, announce=False
            )
            self.logger.info(
                "Evented/WebSocket service running on %s:%s",
                self.interface,
                self.port,
            )
            _debug.lifecycle(
                "server.evented.start", interface=self.interface, port=self.port
            )
            if IS_POSIX:
                # The watchdog asks for a restart with a SIGTERM to this
                # process; started here, that signal can only land inside
                # `serve_forever()`, where it is a clean stop.
                threading.Thread(
                    target=self.run_watchdog,
                    daemon=True,
                    name="odoo.service.evented.watchdog",
                ).start()
            self.httpd.serve_forever()
        except SystemExit:
            raise
        except KeyboardInterrupt:
            pass
        except BaseException as exc:
            self.logger.critical("Uncaught error in main loop", exc_info=True)
            _debug.logic("server.evented.main_loop_failed", error=type(exc).__name__)
            raise SystemExit(1) from exc
        self.logger.info("Evented/WebSocket service stopped")
        _debug.lifecycle("server.evented.stopped", pid=self.pid)

    def stop(self) -> None:
        _debug.lifecycle("server.evented.stop", httpd=self.httpd is not None)
        if self.httpd:
            self.httpd.drain(get_graceful_stop_timeout(self.logger))
            self.httpd.server_close()
        super().stop()

    def run(self, preload: list[str] | None = None, stop: bool = False) -> int | None:
        # `preload` is the master's db_name list, which its argv hands every
        # subprocess; this server loads registries on demand, so it is not a
        # mistake to report.
        _debug.pipeline(
            "server.evented.run", preload=len(preload or ()), stop=stop, pid=self.pid
        )
        if stop:
            self.logger.warning(
                "Ignoring --stop-after-init: the evented server has no "
                "initialisation phase to stop after, and will serve until "
                "signalled."
            )
        try:
            self.start()
        finally:
            self.stop()
        return None
