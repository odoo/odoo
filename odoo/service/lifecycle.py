from __future__ import annotations

import contextlib
import logging
import os
import platform
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

from odoo import api, db
from odoo.libs import gc
from odoo.libs.debug_log import DebugLog
from odoo.libs.filesystem import osutil
from odoo.libs.worker_thread import current_worker_thread
from odoo.modules.module import load_odoo_module
from odoo.modules.registry import Registry
from odoo.release import nt_service_name
from odoo.tools import profiler
from odoo.tools.misc import stripped_sys_argv

from . import _process_state
from ._env import IS_POSIX, IS_WINDOWS, get_env_float, get_env_int
from .settings import current

if TYPE_CHECKING:
    from odoo.tests.result import OdooTestResult

_logger = logging.getLogger("odoo.service.server")
_debug = DebugLog(__name__)


def load_server_wide_modules() -> None:
    with gc.disabling_gc():
        with _debug.perf(
            "service.server_wide_modules_loaded",
            modules=len(current().server_wide_modules),
        ):
            _load_server_wide_modules()


def _load_server_wide_modules() -> None:
    for m in current().server_wide_modules:
        try:
            with _debug.perf("service.server_wide_module_loaded", module=m):
                load_odoo_module(m)
        except Exception:
            _debug.logic("service.server_wide_module_failed", module=m)
            msg = ""
            if m == "web":
                msg = """
    The `web` module is provided by the addons found in the `odoo-web` project.
    Maybe you forgot to add those addons in your addons_path configuration."""
            _logger.exception("Failed to load server-wide module `%s`.%s", m, msg)


def _reexec_server() -> None:
    if osutil.is_running_as_nt_service(nt_service_name):
        rc = subprocess.call(  # noqa: S602  fixed literal, no user input
            f"net stop {nt_service_name} && net start {nt_service_name}",
            shell=True,
        )
        if rc == 0:
            _debug.lifecycle("service.nt_service_restarted", service=nt_service_name)
            return
        _logger.warning(
            "Service restart via the SCM failed (exit %s); "
            "falling back to an in-place re-exec",
            rc,
        )
        _debug.logic("service.nt_service_restart_failed", rc=rc)
    exe = Path(sys.executable).name
    args = stripped_sys_argv()
    if not args or args[0] not in (sys.executable, exe):
        args.insert(0, sys.executable)
    _debug.lifecycle("service.reexec", pid=os.getpid(), argv=len(args))
    os.execve(sys.executable, args, os.environ)  # noqa: S606  re-exec of ourselves IS the restart


def _find_assertion_report(dbname: str) -> OdooTestResult | None:
    from odoo.tests.result import assertion_report

    return assertion_report(dbname)


def _get_assertion_report(dbname: str) -> OdooTestResult:
    report = _find_assertion_report(dbname)
    if report is None:
        raise RuntimeError(
            f"no assertion report for {dbname!r}: test_enable is off in the "
            f"live config while the service settings say tests run"
        )
    return report


def _run_post_install_tests(registry: Registry, update_module: bool) -> int:
    from odoo.db.utils import update_planner_stats
    from odoo.tests import loader

    try:
        with _debug.perf(
            "service.planner_stats_updated", db=getattr(registry, "db_name", None)
        ) as span:
            with registry.cursor() as cr:
                updated = update_planner_stats(cr)
            span.set(tables=updated)
        if updated:
            _logger.info("Set planner statistics for %d zero-stat tables", updated)
    except Exception:
        _logger.warning(
            "Planner-stats update failed; tests may run slower", exc_info=True
        )
        _debug.logic(
            "service.planner_stats_failed", db=getattr(registry, "db_name", None)
        )

    t0 = time.time()
    t0_sql = db.sql_counter
    module_names = (
        registry.updated_modules if update_module else sorted(registry.loaded_modules)
    )

    _logger.info("Starting post tests")
    report = _get_assertion_report(registry.db_name)
    tests_before = report.testsRun
    post_install_suite = loader.prepare_suite(module_names, "post_install")
    prepared = post_install_suite.countTestCases()
    _debug.pipeline(
        "service.post_install_tests.prepared",
        modules=len(module_names),
        tests=prepared,
        update_module=update_module,
    )
    if post_install_suite.has_http_case():
        with _debug.perf("service.post_install_tests.assets_pregenerated"):
            with registry.cursor() as cr:
                env = api.Environment(cr, api.SUPERUSER_ID, {})
                env["ir.qweb"]._pregenerate_assets_bundles()  # type: ignore[attr-defined]

    result = loader.run_suite(
        post_install_suite,
        global_report=report,
    )
    report.update(result)
    _logger.info(
        "%d post-tests in %.2fs, %s queries",
        report.testsRun - tests_before,
        time.time() - t0,
        db.sql_counter - t0_sql,
    )
    _debug.pipeline(
        "service.post_install_tests.ran",
        tests=report.testsRun - tests_before,
        seconds=time.time() - t0,
        queries=db.sql_counter - t0_sql,
    )
    report.log_stats()
    if _debug.logic.enabled and prepared and not result.testsRun:
        _debug.logic("service.post_install_tests.none_ran", prepared=prepared)
    return prepared if prepared and not result.testsRun else 0


def _get_test_run_rc(dbname: str, report: OdooTestResult, unrun: int) -> int:
    _debug.pipeline(
        "service.preload_reported",
        db=dbname,
        tests_run=report.testsRun,
        unrun=unrun,
        successful=report.wasSuccessful(),
    )
    if not report.wasSuccessful():
        _debug.logic("service.preload_rc", db=dbname, reason="tests_failed")
        return 1
    if unrun:
        _debug.logic("service.preload_rc", db=dbname, reason="unrun", unrun=unrun)
        _logger.error(
            "post_install prepared %d tests for database %r and ran none of "
            "them: every class was skipped before its first test started "
            "(--no-http against HttpCase-only classes?), yet the run would "
            "otherwise have reported success.",
            unrun,
            dbname,
        )
        return 1
    if not report.testsRun and (spec := _get_narrowing_test_spec()):
        _debug.logic("service.preload_rc", db=dbname, reason="no_test_matched")
        _logger.error(
            "--test-tags %r matched no test at all: nothing ran, yet the run "
            "would otherwise have reported success.",
            spec,
        )
        return 1
    return 0


def _get_narrowing_test_spec() -> str:
    tags = current().test_tags.strip()
    spec = "" if tags in {"", "+standard"} else tags
    _debug.logic("service.test_spec", tags=tags, narrowing=bool(spec))
    return spec


def _limit_resident_registries(dbnames: list[str]) -> None:
    registries_size = get_env_int(
        "ODOO_REGISTRY_LRU_SIZE", 0, minimum=0, logger=_logger
    )
    source = "env"  # debuglog
    if not registries_size:
        if IS_POSIX:
            avgsz = 15 * 1024 * 1024
            configured_soft_limit = current().limit_memory_soft
            limit_memory_soft = (
                configured_soft_limit
                if configured_soft_limit > 0
                else (2048 * 1024 * 1024)
            )
            registries_size = (limit_memory_soft // avgsz) or 1
            source = "memory_soft"  # debuglog
        if len(dbnames) > max(registries_size, Registry.registries.count):
            registries_size = len(dbnames)
            source = "preload_count"  # debuglog
    if registries_size:
        Registry.registries.count = registries_size
        _debug.logic("service.registry_lru_sized", size=registries_size, source=source)

    idle_timeout = get_env_int(
        "ODOO_REGISTRY_MAX_IDLE_TIMEOUT", 0, minimum=0, logger=_logger
    )
    if not idle_timeout:
        idle_timeout = current().registry_idle_timeout
    if idle_timeout > 0:
        Registry.idle_timeout = idle_timeout
        _logger.info("Idle registries are dropped after %ds", idle_timeout)
    _debug.logic(
        "service.registry_limits",
        lru_size=Registry.registries.count,
        idle_timeout=getattr(Registry, "idle_timeout", None),
        databases=len(dbnames),
    )


def _get_preload_profiler(dbname: str) -> contextlib.AbstractContextManager:
    if not os.environ.get("ODOO_PROFILE_PRELOAD"):
        return contextlib.nullcontext()
    interval = get_env_float("ODOO_PROFILE_PRELOAD_INTERVAL", 0.1, logger=_logger)
    collectors: list[str | profiler.Collector] = [
        profiler.PeriodicCollector(interval=interval)
    ]
    if os.environ.get("ODOO_PROFILE_PRELOAD_SQL"):
        collectors.append("sql")
    _debug.logic(
        "service.preload_profiled",
        db=dbname,
        interval=interval,
        collectors=len(collectors),
    )
    return profiler.Profiler(db=dbname, collectors=collectors)


def preload_registries(dbnames: list[str] | None) -> int:
    dbnames = dbnames or []
    rc = 0

    _limit_resident_registries(dbnames)

    for dbname in dbnames:
        try:
            with _get_preload_profiler(dbname):
                current_worker_thread().dbname = dbname
                settings = current()
                update_module = settings.update_module

                with _debug.perf(
                    "service.preload_registry",
                    db=dbname,
                    update_module=update_module,
                    init=len(settings.init),
                    update=len(settings.update),
                ):
                    # Under --test-enable the server exists to serve the test
                    # client mid-load, so the load does not gate readiness.
                    marking = (
                        contextlib.nullcontext()
                        if settings.test_enable
                        else _process_state.preloading_database(dbname)
                    )
                    with marking, Registry._lock:
                        registry = Registry.new(
                            dbname,
                            update_module=update_module,
                            install_modules=settings.init,
                            upgrade_modules=settings.update,
                            reinit_modules=settings.reinit,
                        )

                if settings.test_enable:
                    with _debug.perf("service.post_install_tests", db=dbname) as span:
                        unrun = _run_post_install_tests(registry, update_module)
                        span.set(unrun=unrun)
                    rc += _get_test_run_rc(dbname, _get_assertion_report(dbname), unrun)
        except Exception as exc:
            _logger.critical(
                "Failed to initialize database `%s`.", dbname, exc_info=True
            )
            if (report := _find_assertion_report(dbname)) is not None:
                report.record_abort(f"{type(exc).__name__}: {exc}")
            _debug.logic("service.preload_failed", db=dbname)
            return -1
    return rc


def _limit_malloc_arenas() -> None:
    gil_disabled = hasattr(sys, "_is_gil_enabled") and not sys._is_gil_enabled()
    if gil_disabled or not (
        platform.system() == "Linux"
        and sys.maxsize > 2**32
        and "MALLOC_ARENA_MAX" not in os.environ
    ):
        _debug.logic(
            "service.malloc_arenas_skipped",
            gil_disabled=gil_disabled,
            env_set="MALLOC_ARENA_MAX" in os.environ,
            system=platform.system(),
        )
        return
    try:
        import ctypes

        libc = ctypes.CDLL("libc.so.6")
        M_ARENA_MAX = -8
        ok = libc.mallopt(ctypes.c_int(M_ARENA_MAX), ctypes.c_int(2)) == 1
    except Exception:
        ok = False
    _debug.logic("service.malloc_arenas_limited", ok=ok)
    if not ok:
        _logger.warning("Could not set ARENA_MAX through mallopt()")


def _get_connection_budget_demand() -> tuple[int, int]:
    settings = current()
    maxconn = settings.db_maxconn
    if not settings.workers:
        return 1, maxconn
    children = settings.workers + settings.max_cron_threads + settings.job_workers
    demand = children * maxconn
    processes = children
    if settings.http_enable:
        processes += 1
        demand += settings.db_maxconn_gevent or maxconn
    return processes, demand


def _warn_on_connection_budget() -> None:
    import odoo

    if odoo.evented:
        return
    try:
        processes, demand = _get_connection_budget_demand()
        configured_port = current().db_port
        with contextlib.closing(db.db_connect("postgres").cursor()) as cr:
            cr.execute("SHOW max_connections")
            server_max = int(cr.fetchscalar())
            cr.execute("SHOW superuser_reserved_connections")
            reserved = int(cr.fetchscalar())
            cr.execute("SELECT inet_server_port()")
            server_port = cr.fetchscalar()
    except Exception:
        _logger.debug("Could not check the connection budget", exc_info=True)
        _debug.logic("service.connection_budget_unchecked")
        return

    _debug.logic(
        "service.connection_budget",
        processes=processes,
        demand=demand,
        server_max=server_max,
        reserved=reserved,
        configured_port=configured_port,
        server_port=server_port,
    )
    if server_port and configured_port and int(configured_port) != int(server_port):
        _debug.logic(
            "service.connection_budget_pooler",
            configured_port=configured_port,
            server_port=server_port,
        )
        _logger.info(
            "Connection budget not checked: connected to port %s but the server "
            "reports port %s, so a connection pooler is in between and its "
            "client limit -- not max_connections=%d -- is what bounds this "
            "deployment. Size db_maxconn x %d process(es) against the pooler.",
            configured_port,
            server_port,
            server_max,
            processes,
        )
        return

    headroom = server_max - reserved
    if demand <= headroom:
        return
    _debug.logic(
        "service.connection_budget_exceeded",
        demand=demand,
        headroom=headroom,
        processes=processes,
        suggested_maxconn=max(headroom // processes, 1),
    )
    _logger.warning(
        "Connection budget exceeds the primary: %d process(es) x db_maxconn may "
        "check out %d connections, but PostgreSQL allows %d (max_connections=%d "
        "minus superuser_reserved_connections=%d). Under load this surfaces as "
        "'FATAL: sorry, too many clients already'. Lower db_maxconn to %d or "
        "less, reduce the worker count, or raise max_connections. A read replica "
        "is budgeted separately and is not included in this figure.",
        processes,
        demand,
        headroom,
        server_max,
        reserved,
        max(headroom // processes, 1),
    )


DESCRIPTOR_HEADROOM = 128
"""Descriptors a process needs beside the ones the budget counts: log files,
pipes, the listening and wake sockets, the inotify instance, the terminal."""


def _get_descriptor_budget_demand() -> int:
    # The largest single process this configuration runs.  Threaded: every
    # HTTP slot and every parked idle connection is a socket, each cron and
    # job thread holds a listener session, and the pool holds db_maxconn.
    # Prefork: a worker holds db_maxconn and one client; the evented child
    # is the threaded shape on its own port.  Workers inherit the limit, so
    # the per-process maximum is what has to fit.
    from ._transport import TransportLimits
    from .httpd import compute_http_thread_limit

    settings = current()
    threads, _ = compute_http_thread_limit(settings)
    http = threads + TransportLimits.from_environment().max_idle_connections
    listeners = settings.max_cron_threads + settings.job_workers
    if settings.workers:
        worker = settings.db_maxconn + 1
        evented = (settings.db_maxconn_gevent or settings.db_maxconn) + http
        return max(worker, evented) + DESCRIPTOR_HEADROOM
    return settings.db_maxconn + http + listeners + DESCRIPTOR_HEADROOM


def _ensure_descriptor_budget() -> None:
    if not IS_POSIX:
        return
    import resource

    demand = _get_descriptor_budget_demand()
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    _debug.logic("service.descriptor_budget", demand=demand, soft=soft, hard=hard)
    if soft == resource.RLIM_INFINITY or soft >= demand:
        return
    if hard == resource.RLIM_INFINITY or hard >= demand:
        # The hard limit is the operator's ceiling; the soft one is ours to
        # spend, as nginx and PostgreSQL raise theirs.
        try:
            resource.setrlimit(resource.RLIMIT_NOFILE, (hard, hard))
        except ValueError, OSError:
            _logger.warning(
                "Could not raise the open-file limit from %d to %d", soft, hard
            )
            _debug.logic("service.descriptor_budget_raise_failed", soft=soft, hard=hard)
            return
        _logger.info(
            "Open-file limit raised from %d to %d: this configuration may hold "
            "%d descriptors at once",
            soft,
            hard,
            demand,
        )
        _debug.lifecycle("service.descriptor_budget_raised", soft=soft, hard=hard)
        return
    _debug.logic("service.descriptor_budget_exceeded", demand=demand, hard=hard)
    _logger.warning(
        "Open-file limit is %d but this configuration may hold %d descriptors at "
        "once (db_maxconn, the HTTP thread and idle-connection budgets, the "
        "listener sessions). Under load this surfaces as 'Too many open files' "
        "on accept(). Raise LimitNOFILE= on the unit (or ulimit -n), or lower "
        "db_maxconn / ODOO_HTTP_MAX_IDLE_CONNECTIONS.",
        hard,
        demand,
    )


__all__ = (
    "load_server_wide_modules",
    "preload_registries",
    "restart",
)


def restart() -> None:
    server = _process_state.server
    if server is None:
        _logger.warning(
            "restart() called before server.start() assigned the server; ignoring"
        )
        _debug.logic("service.restart_ignored", reason="no_server")
        return
    _debug.lifecycle("service.restart_requested", pid=server.pid, windows=IS_WINDOWS)
    if IS_WINDOWS:
        threading.Thread(target=_reexec_server).start()
    else:
        import signal

        os.kill(server.pid, signal.SIGHUP)
