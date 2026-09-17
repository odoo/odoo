from __future__ import annotations

import errno
import logging
import os
import threading
from collections.abc import Iterator
from pathlib import Path

from odoo.libs import inotify as _inotify_lib
from odoo.libs.debug_log import DebugLog

import odoo.addons
from . import _process_state
from .lifecycle import restart
from .settings import current

inotify = _inotify_lib if _inotify_lib.AVAILABLE else None

INOTIFY_LISTEN_EVENTS = (
    _inotify_lib.IN_MODIFY
    | _inotify_lib.IN_CREATE
    | _inotify_lib.IN_MOVED_TO
    | _inotify_lib.IN_DELETE
    | _inotify_lib.IN_ISDIR
)

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

_UNWATCHED_DIRS = frozenset({"__pycache__", ".git", "node_modules", "i18n"})
"""Directory names no reload or asset event can come from.

`__pycache__` is the loud one: every import writes a .pyc there, so a watched
tree reports its own module loads. `static` joins the set when --dev has no
`assets`, since only a .py edit is acted on then.
"""


def get_unwatched_dirs() -> frozenset[str]:
    if "assets" in current().dev_mode:
        return _UNWATCHED_DIRS
    return _UNWATCHED_DIRS | {"static"}


def iter_watch_dirs(root: str | os.PathLike[str]) -> Iterator[str]:
    unwatched = get_unwatched_dirs()
    stack = [os.fspath(root)]
    while stack:
        directory = stack.pop()
        yield directory
        try:
            with os.scandir(directory) as entries:
                children = [
                    entry.path
                    for entry in entries
                    if entry.is_dir(follow_symlinks=False)
                    and entry.name not in unwatched
                ]
        except OSError:
            continue
        stack.extend(reversed(children))


def iter_python_watch_dirs(root: str | os.PathLike[str]) -> Iterator[str]:
    # A reload-only watcher acts on `.py` edits alone, so a directory whose
    # subtree holds no Python file can only ever report noise: views/, data/,
    # security/, i18n/ and the like are two fifths of an addons tree, and
    # every one of them was an inotify watch taken from a budget the editor
    # and every other dev server on the box share.  The root is watched
    # regardless, so a module created under it is seen and armed.
    unwatched = get_unwatched_dirs()
    root = os.fspath(root)
    parent_of: dict[str, str] = {}
    holds_python: dict[str, bool] = {}
    order: list[str] = []
    stack = [root]
    while stack:
        directory = stack.pop()
        order.append(directory)
        holds = False
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    if entry.is_dir(follow_symlinks=False):
                        if entry.name not in unwatched:
                            parent_of[entry.path] = directory
                            stack.append(entry.path)
                    elif entry.name.endswith(".py"):
                        holds = True
        except OSError:
            pass
        holds_python[directory] = holds
    for directory in reversed(order):
        if holds_python[directory] and directory in parent_of:
            holds_python[parent_of[directory]] = True
    for directory in order:
        if directory == root or holds_python[directory]:
            yield directory


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
            was_active, self._burst_active = self._burst_active, False
        if _debug.lifecycle.enabled and was_active:
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
        # The watchdog backend on Windows reports native backslash paths;
        # a POSIX-only separator here would silently ignore every asset
        # edit under --dev=assets there.
        posix_path = path.replace(os.sep, "/")
        if path.endswith(ASSET_SUFFIXES) and "/static/" in posix_path:
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


class FSWatcherInotify(FSWatcherBase):
    _needs_burst_timer = False

    def __init__(self, block_duration_s: float = 0.5) -> None:
        super().__init__()
        self.started = False
        self.thread: threading.Thread | None = None
        self.watcher: _inotify_lib.Inotify | None = None
        self.block_duration_s = block_duration_s
        self._python_only = "assets" not in current().dev_mode
        paths = self.get_watch_paths()
        _logger.info("Watching %d folder(s) for changes", len(paths))
        self._arm_watcher(paths)

    _python_only = False
    """Whether only Python-bearing subtrees are armed: a reload-only watcher
    acts on `.py` edits alone, while `--dev=assets` needs every static tree."""

    def _iter_root(self, root: str) -> Iterator[str]:
        if self._python_only:
            return iter_python_watch_dirs(root)
        return iter_watch_dirs(root)

    def _arm_watcher(self, paths: list[str]) -> None:
        self.roots = paths
        watcher = _inotify_lib.Inotify()
        try:
            for root in paths:
                for directory in self._iter_root(root):
                    watcher.add_watch(directory, INOTIFY_LISTEN_EVENTS)
        except Exception as exc:
            watcher.close()
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
        self.watcher = watcher
        _debug.lifecycle(
            "watcher.inotify_armed",
            roots=len(paths),
            watches=len(watcher.watched),
            block_s=self.block_duration_s,
        )

    def _sync_watches_after_overflow(self) -> None:
        _logger.warning(
            "autoreload: inotify queue overflowed — events were lost; "
            "re-arming watches and dropping the asset caches"
        )
        for root in self.roots:
            if not Path(root).is_dir():
                continue
            for directory in self._iter_root(root):
                self._watch_directory(Path(directory))
        _debug.pipeline("watcher.overflow_resynced", roots=len(self.roots))
        self.on_asset_file_changed(OVERFLOW_PATH)

    def _watch_directory(self, directory: Path) -> None:
        watcher = self.watcher
        if watcher is None:
            _debug.logic(
                "watcher.watch_skipped", path=str(directory), reason="released"
            )
            return
        try:
            watcher.add_watch(directory, INOTIFY_LISTEN_EVENTS)
        except Exception as exc:
            _logger.warning(
                "autoreload: cannot watch %s; edits below it will not be seen. %s",
                directory,
                get_inotify_limit_diagnosis(exc) or "See the traceback for the cause.",
                exc_info=True,
            )
            _debug.logic(
                "watcher.watch_failed", path=str(directory), error=type(exc).__name__
            )

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
        while self.started:
            try:
                events = watcher.read(self.block_duration_s)
            except _inotify_lib.QueueOverflow:
                _debug.logic("watcher.queue_overflow")
                self._sync_watches_after_overflow()
                continue
            for event in events:
                if not event.is_dir:
                    if event.is_deletion:
                        continue
                    _debug.pipeline(
                        "watcher.event",
                        backend="inotify",
                        mask=event.mask,
                        path=event.full_path,
                    )
                    if self.on_file_changed(event.full_path):
                        return
                elif event.is_creation and self._handle_created_directory(event):
                    return
            self._end_burst()

    def _handle_created_directory(self, event: _inotify_lib.Event) -> bool:
        if event.name in get_unwatched_dirs():
            return False
        created_dir = Path(event.full_path)
        _debug.pipeline("watcher.directory_created", path=str(created_dir))
        for directory in iter_watch_dirs(created_dir):
            self._watch_directory(Path(directory))
            try:
                entries = list(Path(directory).iterdir())
            except OSError:
                # The directory vanished between the CREATE event and this
                # scan (git checkout/stash, mkdtemp and editors do that).  An
                # unhandled error here propagates through _run() and kills
                # the watcher thread for the rest of the session — nothing
                # restarts it.
                _debug.logic("watcher.created_dir_vanished", path=directory)
                continue
            for entry in entries:
                if entry.is_file() and self.on_file_changed(str(entry)):
                    return True
        return False

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
        watcher, self.watcher = self.watcher, None
        if watcher is not None:
            watcher.close()
            _debug.lifecycle("watcher.released", backend="inotify")
