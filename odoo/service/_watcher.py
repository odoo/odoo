from __future__ import annotations

import errno
import logging
import os
import threading
from contextlib import suppress
from pathlib import Path

from odoo.libs.debug_log import DebugLog

import odoo.addons
from . import _process_state
from .lifecycle import restart
from .settings import current

if os.name == "posix":
    try:
        import inotify
        from inotify.adapters import Inotify, TerminalEventException
        from inotify.adapters import InotifyTrees as _InotifyTrees
        from inotify.constants import (
            IN_CREATE,
            IN_MODIFY,
            IN_MOVED_TO,
        )

        INOTIFY_LISTEN_EVENTS = IN_MODIFY | IN_CREATE | IN_MOVED_TO
    except ImportError:
        inotify = None  # type: ignore[assignment]
else:
    inotify = None  # type: ignore[assignment]

if not inotify:
    try:
        import watchdog
        from watchdog.events import (
            FileCreatedEvent,
            FileModifiedEvent,
            FileMovedEvent,
        )
        from watchdog.observers import Observer
    except ImportError:
        watchdog = None  # type: ignore[assignment]
else:
    watchdog = None  # type: ignore[assignment]

_logger = logging.getLogger("odoo.service.server")
_debug = DebugLog(__name__)

_OBSERVER_JOIN_TIMEOUT_S = 5.0

_WATCHER_JOIN_TIMEOUT_S = 5.0


ASSET_SUFFIXES = (".js", ".xml", ".scss", ".css")

OVERFLOW_WD = -1

OVERFLOW_PATH = "<inotify-overflow>"

ASSET_BURST_PATH = "<asset-burst>"


INOTIFY_SYSCTL_DIR = Path("/proc/sys/fs/inotify")

INOTIFY_LIMITS = ("max_user_instances", "max_user_watches")


def get_inotify_limit_diagnosis(exc: BaseException) -> str:
    if getattr(exc, "errno", None) != errno.ENOSPC:
        return ""
    limits = []
    for name in INOTIFY_LIMITS:
        try:
            value = (INOTIFY_SYSCTL_DIR / name).read_text().strip()
        except OSError:
            value = "unreadable"
        limits.append(f"fs.inotify.{name}={value}")
    return (
        "inotify is out of capacity (ENOSPC — not disk space). One of these is "
        f"at its cap: {', '.join(limits)}. Instances are consumed one per "
        "watcher; watches are consumed per directory. Both budgets are shared "
        "across this user's servers, tests and editor. Check their watch scope "
        "and resource ownership before increasing host limits."
    )


class FSWatcherBase:
    _BURST_FLUSH_S = 0.2

    _needs_burst_timer = True

    def __init__(self) -> None:
        self._burst_lock = threading.Lock()
        self._assets_dirty = False
        self._burst_active = False
        self._burst_timer: threading.Timer | None = None
        self._reload_triggered = False
        # Prefork keeps this process as its supervisor across reloads. Threaded
        # mode replaces the process, so its watcher still stops after one edit.
        self._reload_in_place = bool(current().workers)

    @staticmethod
    def get_watch_paths() -> list[str]:
        roots = list(odoo.addons.__path__)
        if "reload" in current().dev_mode:
            _debug.pipeline("watcher.paths_resolved", mode="reload", paths=len(roots))
            return roots
        paths = []
        for root in roots:
            root_path = Path(root)
            if not root_path.is_dir():
                continue
            for addon in sorted(root_path.iterdir()):
                tree = addon / "static"
                if tree.is_dir():
                    paths.append(str(tree))
        _debug.pipeline(
            "watcher.paths_resolved", mode="assets", roots=len(roots), paths=len(paths)
        )
        return paths

    def _signal_asset_change(self, path: str) -> None:
        from odoo import db as odoo_db
        from odoo.orm.runtime.registry import Registry

        databases = set(Registry.registries.snapshot) | set(current().db_name or ())
        _debug.lifecycle(
            "watcher.assets_signalled", path=path, databases=len(databases)
        )
        for db_name in databases:
            try:
                with _debug.perf("watcher.assets_invalidated", db=db_name):
                    with odoo_db.db_connect(db_name).cursor() as cr:
                        cr.execute("INSERT INTO orm_signaling_assets DEFAULT VALUES")
            except Exception:
                _logger.warning(
                    "assets watch: could not invalidate %s for %s",
                    db_name,
                    path,
                    exc_info=True,
                )
                _debug.logic("watcher.invalidate_failed", db=db_name, path=path)

    def on_asset_file_changed(self, path: str) -> None:
        with self._burst_lock:
            self._assets_dirty = True
            leading = not self._burst_active
            if leading:
                self._burst_active = True
        if leading:
            _debug.logic("watcher.burst_started", path=path)
            self._flush_asset_invalidation()
        if _debug.logic.enabled and not leading:
            _debug.logic("watcher.burst_joined", path=path)
        self._arm_burst_flush()

    def _flush_asset_invalidation(self) -> None:
        with self._burst_lock:
            if not self._assets_dirty:
                return
            self._assets_dirty = False
        _debug.pipeline("watcher.burst_flushed")
        self._signal_asset_change(ASSET_BURST_PATH)

    def _end_burst(self) -> None:
        self._cancel_burst_flush()
        self._flush_asset_invalidation()
        with self._burst_lock:
            self._burst_active = False
        _debug.lifecycle("watcher.burst_ended")

    def _arm_burst_flush(self) -> None:
        if not self._needs_burst_timer:
            return
        with self._burst_lock:
            if self._burst_timer is not None:
                self._burst_timer.cancel()
            timer = threading.Timer(self._BURST_FLUSH_S, self._end_burst)
            timer.daemon = True
            self._burst_timer = timer
        timer.start()

    def _cancel_burst_flush(self) -> None:
        with self._burst_lock:
            timer, self._burst_timer = self._burst_timer, None
        if timer is not None:
            timer.cancel()

    def on_file_changed(self, path: str) -> bool | None:
        dev_mode = current().dev_mode
        if path.endswith(ASSET_SUFFIXES) and "/static/" in path:
            _debug.logic(
                "watcher.asset_changed", path=path, handled="assets" in dev_mode
            )
            if "assets" in dev_mode:
                self.on_asset_file_changed(path)
            return None
        if self._reload_triggered:
            _debug.logic("watcher.change_ignored", path=path, reason="reload_pending")
            return None
        if "reload" not in dev_mode:
            _debug.logic("watcher.change_ignored", path=path, reason="reload_off")
            return None
        if _debug.logic.enabled and (
            not path.endswith(".py") or Path(path).name.startswith(".~")
        ):
            _debug.logic("watcher.change_ignored", path=path, reason="not_python")
        if path.endswith(".py") and not Path(path).name.startswith(".~"):
            try:
                source = Path(path).read_bytes() + b"\n"
                compile(source, path, "exec")
            except OSError:
                _logger.error(
                    "autoreload: python code change detected, IOError for %s",
                    path,
                )
                _debug.logic("watcher.python_unreadable", path=path)
            except SyntaxError:
                _logger.error(
                    "autoreload: python code change detected, SyntaxError in %s",
                    path,
                )
                _debug.logic("watcher.python_syntax_error", path=path)
            else:
                if _debug.logic.enabled and not (
                    self._reload_in_place or not _process_state.server_phoenix
                ):
                    _debug.logic(
                        "watcher.change_ignored", path=path, reason="phoenix_pending"
                    )
                if self._reload_in_place or not _process_state.server_phoenix:
                    self._reload_triggered = not self._reload_in_place
                    _logger.info(
                        "autoreload: python code updated, autoreload activated"
                    )
                    _debug.lifecycle(
                        "watcher.reload_triggered",
                        path=path,
                        in_place=self._reload_in_place,
                    )
                    restart()
                    return not self._reload_in_place
        return None


class FSWatcherWatchdog(FSWatcherBase):
    def __init__(self) -> None:
        super().__init__()
        self.observer = Observer()
        paths = self.get_watch_paths()
        _logger.info("Watching %d folder(s) for changes", len(paths))
        for path in paths:
            self.observer.schedule(self, path, recursive=True)
        _debug.lifecycle("watcher.scheduled", backend="watchdog", paths=len(paths))

    def dispatch(self, event) -> None:
        if isinstance(event, (FileCreatedEvent, FileModifiedEvent, FileMovedEvent)):
            if not event.is_directory:
                path = getattr(event, "dest_path", "") or event.src_path
                _debug.pipeline(
                    "watcher.event",
                    backend="watchdog",
                    kind=type(event).__name__,
                    path=path,
                )
                self.on_file_changed(path)

    def start(self) -> None:
        self.observer.start()
        _logger.info("AutoReload watcher running with watchdog")
        _debug.lifecycle("watcher.started", backend="watchdog")

    def stop(self) -> None:
        self._end_burst()
        self.observer.stop()
        if self.observer.ident is not None:
            self.observer.join(timeout=_OBSERVER_JOIN_TIMEOUT_S)
        if self.observer.is_alive():
            _logger.warning(
                "autoreload: watchdog observer did not stop within %.0fs; "
                "continuing shutdown without it",
                _OBSERVER_JOIN_TIMEOUT_S,
            )
        _debug.lifecycle(
            "watcher.stopped", backend="watchdog", joined=not self.observer.is_alive()
        )


if inotify:

    class _OwnedInotify(Inotify):
        def __init__(self, **kwargs):
            try:
                super().__init__(**kwargs)
            except BaseException:
                self.close()
                raise

        def close(self) -> None:
            epoll = getattr(self, "_Inotify__epoll", None)
            fd = getattr(self, "_Inotify__inotify_fd", None)
            self._Inotify__epoll = None
            self._Inotify__inotify_fd = None
            try:
                if epoll is not None:
                    epoll.close()
            finally:
                if fd is not None:
                    os.close(fd)

        def __del__(self):
            with suppress(Exception):
                self.close()

    class InotifyTrees(_InotifyTrees):
        def __init__(self, paths, mask, block_duration_s):
            self._mask = (
                mask
                | inotify.constants.IN_ISDIR
                | inotify.constants.IN_CREATE
                | inotify.constants.IN_DELETE
            )
            self._i = _OwnedInotify(block_duration_s=block_duration_s)
            try:
                self._load_trees(paths)
            except BaseException:
                self.close()
                raise

        def close(self) -> None:
            self._i.close()


class _InotifyInternals:
    def __init__(self, trees: InotifyTrees) -> None:
        self._trees = trees

    @property
    def _inotify(self):
        return self._trees._i

    @property
    def mask(self) -> int:
        return self._trees._mask

    def register_path(self, wd: int, path: str) -> None:
        self._inotify._Inotify__watches_r[wd] = path

    def add_watch(self, path: str):
        return self._inotify.add_watch(path, self.mask)

    def remove_watch_superficially(self, path: str) -> None:
        self._inotify.remove_watch(path, superficial=True)

    def get_descriptors(self) -> tuple[int, ...]:
        inot = self._inotify
        fds = [inot._Inotify__inotify_fd]
        epoll = getattr(inot, "_Inotify__epoll", None)
        if epoll is not None:
            fds.append(epoll.fileno())
        return tuple(fds)

    def set_cloexec(self) -> None:
        for fd in self.get_descriptors():
            try:
                os.set_inheritable(fd, False)
            except OSError:
                _logger.debug(
                    "autoreload: could not set FD_CLOEXEC on fd %d", fd, exc_info=True
                )


class FSWatcherInotify(FSWatcherBase):
    _needs_burst_timer = False

    def __init__(self) -> None:
        super().__init__()
        self.started = False
        self.thread: threading.Thread | None = None
        self.watcher: InotifyTrees | None = None
        self.internals: _InotifyInternals | None = None
        inotify.adapters._LOGGER.setLevel(logging.ERROR)
        paths = self.get_watch_paths()
        _logger.info("Watching %d folder(s) for changes", len(paths))
        self._arm_watcher(paths)

    def _arm_watcher(self, paths: list[str], block_duration_s: float = 0.5) -> None:
        self.roots = paths
        try:
            self.watcher = InotifyTrees(
                paths, mask=INOTIFY_LISTEN_EVENTS, block_duration_s=block_duration_s
            )
        except Exception as exc:
            diagnosis = get_inotify_limit_diagnosis(exc)
            _debug.logic(
                "watcher.inotify_arm_failed",
                roots=len(paths),
                enospc=bool(diagnosis),
                error=type(exc).__name__,
            )
            if not diagnosis:
                raise
            raise OSError(errno.ENOSPC, diagnosis) from exc
        self.internals = _InotifyInternals(self.watcher)
        self.internals.set_cloexec()
        self.internals.register_path(OVERFLOW_WD, OVERFLOW_PATH)
        _debug.lifecycle(
            "watcher.inotify_armed", roots=len(paths), block_s=block_duration_s
        )

    def _sync_watches_after_overflow(self) -> None:
        _logger.warning(
            "autoreload: inotify queue overflowed — events were lost; "
            "re-arming watches and dropping the asset caches"
        )
        for root in self.roots:
            root_path = Path(root)
            if not root_path.is_dir():
                continue
            self._watch_directory(root_path)
            for directory, _, _ in root_path.walk():
                self._watch_directory(directory)
        _debug.pipeline("watcher.overflow_resynced", roots=len(self.roots))
        self.on_asset_file_changed(OVERFLOW_PATH)

    def _watch_directory(self, directory: Path) -> None:
        path = str(directory)
        try:
            internals = self.internals
            if internals is None:
                _debug.logic("watcher.watch_skipped", path=path, reason="released")
                return
            if internals.add_watch(path) is not None:
                return
            try:
                internals.remove_watch_superficially(path)
            except Exception:
                _logger.debug("autoreload: stale watch purge for %s", path)
            _debug.logic("watcher.watch_readded", path=path)
            internals.add_watch(path)
        except Exception as exc:
            _logger.warning(
                "autoreload: cannot watch %s; edits below it will not be seen. %s",
                directory,
                get_inotify_limit_diagnosis(exc) or "See the traceback for the cause.",
                exc_info=True,
            )
            _debug.logic("watcher.watch_failed", path=path, error=type(exc).__name__)

    def run(self) -> None:
        try:
            self._run()
        finally:
            _debug.lifecycle(
                "watcher.loop_exited",
                backend="inotify",
                reload_triggered=self._reload_triggered,
                stopped=not self.started,
            )
            self.started = False
            self._release_watcher()

    def _run(self) -> None:
        _logger.info("AutoReload watcher running with inotify")
        _debug.lifecycle("watcher.started", backend="inotify")
        watcher = self.watcher
        if watcher is None:
            return
        dir_creation_events = {"IN_MOVED_TO", "IN_CREATE"}
        while self.started:
            try:
                for event in watcher.event_gen(timeout_s=0, yield_nones=False):
                    _, type_names, path, filename = event
                    if "IN_ISDIR" not in type_names:
                        if "IN_DELETE" not in type_names:
                            full_path = str(Path(path, filename))
                            _debug.pipeline(
                                "watcher.event",
                                backend="inotify",
                                kind=",".join(type_names),
                                path=full_path,
                            )
                            if self.on_file_changed(full_path):
                                return
                    elif dir_creation_events.intersection(type_names):
                        created_dir = Path(path, filename)
                        _debug.pipeline(
                            "watcher.directory_created", path=str(created_dir)
                        )
                        for root, _, files in created_dir.walk():
                            self._watch_directory(root)
                            for file in files:
                                if self.on_file_changed(str(root / file)):
                                    return
            except TerminalEventException as exc:
                if str(exc) != "IN_Q_OVERFLOW":
                    raise
                _debug.logic("watcher.queue_overflow")
                self._sync_watches_after_overflow()
            self._end_burst()

    def start(self) -> None:
        self.started = True
        self.thread = threading.Thread(
            target=self.run, name="odoo.service.autoreload.watcher"
        )
        self.thread.daemon = True
        _debug.lifecycle(
            "watcher.thread_starting",
            backend="inotify",
            thread=getattr(self.thread, "name", None),
        )
        try:
            self.thread.start()
        except BaseException:
            _debug.logic("watcher.thread_start_failed")
            self.started = False
            self.thread = None
            self._release_watcher()
            raise

    def stop(self) -> None:
        self.started = False
        self._end_burst()
        if self.thread is not None:
            self.thread.join(timeout=_WATCHER_JOIN_TIMEOUT_S)
            if self.thread.is_alive():
                _logger.warning(
                    "autoreload: inotify watch thread did not stop within %.0fs; "
                    "continuing shutdown without it",
                    _WATCHER_JOIN_TIMEOUT_S,
                )
                _debug.lifecycle("watcher.stopped", backend="inotify", joined=False)
                self.thread = None
                return
            self.thread = None
        self._release_watcher()
        _debug.lifecycle("watcher.stopped", backend="inotify", joined=True)

    def _release_watcher(self) -> None:
        watcher = getattr(self, "watcher", None)
        self.internals = None
        self.watcher = None
        if watcher is not None:
            watcher.close()
            _debug.lifecycle("watcher.released", backend="inotify")
