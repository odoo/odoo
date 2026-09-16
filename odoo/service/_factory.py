from __future__ import annotations

import logging
from typing import Any

from odoo.libs.debug_log import DebugLog

from . import _process_state
from ._base_server import CommonServer
from ._prefork import PreforkServer
from ._process_state import set_server
from ._threaded import ThreadedServer, WebsocketServer
from ._watcher import (
    FSWatcherInotify,
    FSWatcherWatchdog,
    inotify,
    watchdog,
)
from .lifecycle import (
    _ensure_descriptor_budget,
    _limit_malloc_arenas,
    _reexec_server,
    _warn_on_connection_budget,
    load_server_wide_modules,
    preload_registries,
    restart,
)
from .settings import ServerSettings, current

_logger = logging.getLogger("odoo.service.server")
_debug = DebugLog(__name__)

__all__ = (
    "load_server_wide_modules",
    "preload_registries",
    "restart",
    "start",
)


def _wrap_app_in_debugger(app: Any, settings: ServerSettings) -> Any:
    if "werkzeug" not in settings.dev_mode:
        _debug.logic("server.debugger_skipped", dev_mode=list(settings.dev_mode))
        return app

    from werkzeug.debug import DebuggedApplication

    import odoo.http.application

    if settings.workers:
        _logger.warning(
            "--dev=werkzeug with workers > 0: each worker prints its own "
            "debugger PIN and only the worker that served the request accepts "
            "it. Use --workers 0."
        )
    _logger.warning(
        "--dev=werkzeug is on: unhandled errors render an interactive "
        "traceback with a code console. Never expose this port."
    )
    odoo.http.application.debugger_attached = True
    _debug.lifecycle("server.debugger_attached", workers=settings.workers)
    return DebuggedApplication(app, evalex=True)


def _prepare_server(app: Any, settings: ServerSettings) -> CommonServer:
    import odoo

    if odoo.evented:
        _debug.logic("server.flavor_chosen", flavor="evented")
        return WebsocketServer(app)
    if settings.workers:
        if settings.test_enable:
            _logger.warning("Unit testing in workers mode could fail; use --workers 0.")
        _debug.logic(
            "server.flavor_chosen",
            flavor="prefork",
            workers=settings.workers,
            test_enable=settings.test_enable,
        )
        return PreforkServer(app)
    _limit_malloc_arenas()
    _debug.logic("server.flavor_chosen", flavor="threaded")
    return ThreadedServer(app)


def start(preload: list[str] | None = None, stop: bool = False) -> int:
    _debug.pipeline("server.start", preload=len(preload or ()), stop=stop)
    return _run_configured_server(current(), preload, stop)


def _stop_watcher(watcher: FSWatcherInotify | FSWatcherWatchdog) -> None:
    try:
        watcher.stop()
    except Exception:
        _logger.warning("Could not stop the file watcher", exc_info=True)
        _debug.logic("server.watcher_stop_failed", kind=type(watcher).__name__)
    _debug.lifecycle("server.watcher_stopped", kind=type(watcher).__name__)


def _start_watcher(
    settings: ServerSettings, server: CommonServer
) -> FSWatcherInotify | FSWatcherWatchdog | None:
    import odoo

    if not (
        {"reload", "assets"} & set(settings.dev_mode)
        and not odoo.evented
        and server.is_reload_watcher_owner
    ):
        return None
    if not (inotify or watchdog):
        # inotify is the kernel's own on Linux; anywhere else the watchdog
        # package is the only backend, and it is a dev requirement.
        _debug.logic(
            "server.watcher_unavailable",
            module="watchdog",
            assets="assets" in settings.dev_mode,
        )
        _logger.warning(
            "'%s' module not installed. Code autoreload is disabled%s",
            "watchdog",
            (
                " — with --dev=assets and no watcher, edited asset sources "
                "are NOT picked up; use --dev=xml instead"
                if "assets" in settings.dev_mode
                else ""
            ),
        )
        return None
    watcher = None
    try:
        watcher = FSWatcherInotify() if inotify else FSWatcherWatchdog()
        watcher.start()
    except Exception as exc:
        _debug.logic(
            "server.watcher_start_failed",
            kind="inotify" if inotify else "watchdog",
            error=type(exc).__name__,
        )
        if watcher is not None:
            _stop_watcher(watcher)
        _logger.warning(
            "Could not start the file watcher — the server runs without "
            "it, so source edits are NOT picked up. On Linux this is "
            "usually fs.inotify.max_user_watches being exhausted "
            "(shared with your editor); raise it, or run fewer servers.",
            exc_info=True,
        )
        return None
    _debug.lifecycle(
        "server.watcher_started",
        kind=type(watcher).__name__,
        dev_mode=list(settings.dev_mode),
    )
    return watcher


def _run_configured_server(
    settings: ServerSettings, preload: list[str] | None, stop: bool
) -> int:
    load_server_wide_modules()
    import odoo.http

    app = _wrap_app_in_debugger(odoo.http.root, settings)
    server = _prepare_server(app, settings)
    set_server(server)

    _warn_on_connection_budget()
    _ensure_descriptor_budget()

    watcher = _start_watcher(settings, server)

    _debug.pipeline(
        "server.running",
        flavor=server.flavor,
        watcher=type(watcher).__name__ if watcher is not None else None,
        preload=len(preload or ()),
        stop=stop,
    )
    try:
        rc = server.run(preload, stop)
    finally:
        if watcher is not None:
            _stop_watcher(watcher)
    _debug.pipeline(
        "server.run_finished",
        flavor=server.flavor,
        rc=rc,
        phoenix=_process_state.server_phoenix,
    )
    if _process_state.server_phoenix:
        _reexec_server()

    return rc or 0
