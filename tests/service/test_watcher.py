import os
import pathlib
import shutil
import time
from unittest.mock import MagicMock, patch

import psycopg
import pytest

from odoo.service import _watcher
from odoo.service import settings as server_settings

from .conftest import fake_pg_cursor, requires_inotify


@pytest.fixture(scope="module")
def srv():
    return _watcher


class TestFSWatcherBase:
    @pytest.fixture
    def watcher(self, srv):
        return srv.FSWatcherBase()

    @pytest.fixture(autouse=True)
    def _reload_enabled(self):
        import odoo.tools

        with odoo.tools.config.patch(dev_mode=["reload"]):
            yield

    def test_valid_py_triggers_restart(self, watcher, tmp_path):
        py = tmp_path / "good.py"
        py.write_text("x = 1 + 1\n")
        with (
            patch("odoo.service._process_state.server_phoenix", False),
            patch("odoo.service._watcher.restart") as mock_restart,
        ):
            result = watcher.on_file_changed(str(py))
        mock_restart.assert_called_once()
        assert result is True

    def test_second_change_does_not_trigger_a_second_restart(self, watcher, tmp_path):
        a, b = tmp_path / "a.py", tmp_path / "b.py"
        a.write_text("x = 1\n")
        b.write_text("y = 2\n")
        with (
            patch("odoo.service._process_state.server_phoenix", False),
            patch("odoo.service._watcher.restart") as mock_restart,
        ):
            first = watcher.on_file_changed(str(a))
            second = watcher.on_file_changed(str(b))
        assert first is True
        assert second is None
        mock_restart.assert_called_once()

    def test_syntax_error_suppresses_restart(self, watcher, tmp_path):
        bad = tmp_path / "bad.py"
        bad.write_text("def (\n")
        with patch("odoo.service._watcher.restart") as mock_restart:
            result = watcher.on_file_changed(str(bad))
        mock_restart.assert_not_called()
        assert result is None

    def test_missing_file_suppresses_restart(self, watcher, tmp_path):
        with patch("odoo.service._watcher.restart") as mock_restart:
            result = watcher.on_file_changed(str(tmp_path / "ghost.py"))
        mock_restart.assert_not_called()
        assert result is None

    def test_non_py_file_is_ignored(self, watcher, tmp_path):
        txt = tmp_path / "config.yaml"
        txt.write_text("key: value")
        with patch("odoo.service._watcher.restart") as mock_restart:
            result = watcher.on_file_changed(str(txt))
        mock_restart.assert_not_called()
        assert result is None

    def test_hidden_tilde_py_file_is_ignored(self, watcher, tmp_path):
        hidden = tmp_path / ".~mymodule.py"
        hidden.write_text("pass\n")
        with patch("odoo.service._watcher.restart") as mock_restart:
            result = watcher.on_file_changed(str(hidden))
        mock_restart.assert_not_called()
        assert result is None

    def test_server_phoenix_skips_restart(self, watcher, tmp_path):
        py = tmp_path / "ok.py"
        py.write_text("pass\n")
        with (
            patch("odoo.service._process_state.server_phoenix", True),
            patch("odoo.service._watcher.restart") as mock_restart,
        ):
            result = watcher.on_file_changed(str(py))
        mock_restart.assert_not_called()
        assert result is None

    def test_a_windows_asset_path_is_recognised_and_invalidated(self, watcher):
        # On Windows the watchdog backend reports native backslash paths; a
        # POSIX-only "/static/" check would miss them and --dev=assets would
        # silently ignore every asset edit there.
        win_path = r"c:\odoo\addons\web\static\src\x.js"
        with (
            patch.object(_watcher.os, "sep", "\\"),
            patch("odoo.service._watcher.current") as current,
            patch.object(watcher, "on_asset_file_changed") as on_asset,
        ):
            current.return_value.dev_mode = ["assets"]
            result = watcher.on_file_changed(win_path)
        on_asset.assert_called_once_with(win_path)
        assert result is None


@pytest.mark.parametrize("phoenix", [False, True])
def test_prefork_watcher_keeps_accepting_source_edits(tmp_path, phoenix):
    source = tmp_path / "source.py"
    source.write_text("value = 1\n")
    with (
        server_settings.override(workers=2, dev_mode=("reload",)),
        patch("odoo.service._process_state.server_phoenix", phoenix),
        patch.object(_watcher, "restart") as restart,
    ):
        watcher = _watcher.FSWatcherBase()
        assert not watcher.on_file_changed(str(source))
        source.write_text("value = 2\n")
        assert not watcher.on_file_changed(str(source))
    assert restart.call_count == 2


@requires_inotify
def test_failed_watch_thread_start_releases_inotify(tmp_path, monkeypatch):
    monkeypatch.setattr(
        _watcher.FSWatcherBase, "get_watch_paths", staticmethod(lambda: [str(tmp_path)])
    )
    watcher = _watcher.FSWatcherInotify()
    descriptors = watcher.watcher.descriptors()
    try:
        with patch.object(
            _watcher.threading.Thread,
            "start",
            side_effect=RuntimeError("thread exhausted"),
        ):
            with pytest.raises(RuntimeError, match="thread exhausted"):
                watcher.start()
        assert not watcher.started
        assert watcher.thread is None
        for fd in descriptors:
            with pytest.raises(OSError):
                os.fstat(fd)
    finally:
        # Let the pre-fix control release its never-started thread too.
        if watcher.thread is not None and watcher.thread.ident is None:
            watcher.thread = None
        watcher.stop()


def test_watchdog_cleanup_accepts_an_observer_that_never_started(monkeypatch):
    class Observer(_watcher.threading.Thread):
        def stop(self):
            pass

    monkeypatch.setattr(_watcher, "Observer", Observer, raising=False)
    monkeypatch.setattr(_watcher.FSWatcherBase, "get_watch_paths", staticmethod(list))
    watcher = _watcher.FSWatcherWatchdog()
    watcher.stop()
    assert watcher.observer.ident is None
    assert not watcher.observer.is_alive()


class TestFSWatcherAssetInvalidation:
    @pytest.fixture
    def invalidate(self, srv):
        def _run(*, registries=(), configured=(), failing=()):
            import odoo.db
            import odoo.orm.runtime.registry as registry_mod

            statements = []

            def db_connect(db_name):
                if db_name in failing:
                    raise psycopg.OperationalError(f"{db_name} is unreachable")
                cursor = fake_pg_cursor(
                    execute=lambda sql, *a: statements.append((db_name, sql))
                )
                handle = MagicMock()
                handle.cursor.return_value = cursor
                return handle

            fake_registry = MagicMock()
            fake_registry.registries.snapshot = list(registries)
            watcher = srv.FSWatcherBase()
            with (
                patch.object(odoo.db, "db_connect", db_connect),
                patch.object(registry_mod, "Registry", fake_registry),
                server_settings.override(db_name=tuple(configured)),
            ):
                watcher.on_asset_file_changed("/src/some_bundle.js")
            return statements

        return _run

    def test_signals_loaded_and_configured_databases(self, invalidate):
        statements = invalidate(registries=["loaded"], configured=["configured"])
        assert {db for db, _ in statements} == {"loaded", "configured"}

    def test_each_database_is_signalled_once(self, invalidate):
        statements = invalidate(registries=["shared"], configured=["shared"])
        assert len(statements) == 1

    def test_the_statement_is_the_assets_signal(self, invalidate):
        statements = invalidate(registries=["db1"])
        assert "orm_signaling_assets" in statements[0][1]

    def test_an_unreachable_database_does_not_stop_the_others(self, invalidate):
        statements = invalidate(
            registries=["alpha", "broken", "omega"], failing=["broken"]
        )
        assert {db for db, _ in statements} == {"alpha", "omega"}

    def test_a_total_outage_is_swallowed_not_raised(self, invalidate):
        assert invalidate(registries=["a", "b"], failing=["a", "b"]) == []


@requires_inotify
class TestFSWatcherInotifyRewatch:
    @pytest.fixture
    def watcher(self, tmp_path):
        from odoo.service import _watcher as w

        root = tmp_path / "watched"
        root.mkdir()
        seen = []
        obj = w.FSWatcherInotify.__new__(w.FSWatcherInotify)
        w.FSWatcherBase.__init__(obj)
        obj.started = False
        obj.thread = None
        obj.block_duration_s = 0.05
        obj._arm_watcher([str(root)])
        obj.on_file_changed = seen.append
        obj.start()
        try:
            yield obj, seen, root
        finally:
            obj.stop()

    @staticmethod
    def _wait_for(predicate, timeout=10.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return True
            time.sleep(0.05)
        return False

    @staticmethod
    def _staging_tree(tmp_path):
        staging = tmp_path / "staging"
        (staging / "utils" / "dnd").mkdir(parents=True)
        (staging / "top.js").write_text("export const T = 1;\n")
        (staging / "utils" / "mid.js").write_text("export const M = 1;\n")
        (staging / "utils" / "dnd" / "leaf.js").write_text("export const L = 1;\n")
        return staging

    def test_nested_directory_of_a_moved_subtree_is_watched(self, watcher, tmp_path):
        obj, _seen, root = watcher
        staging = self._staging_tree(tmp_path)
        moved = root / "moved_subtree"
        staging.rename(moved)

        watches = lambda: obj.watcher.watched  # noqa: E731
        assert self._wait_for(lambda: str(moved) in watches()), (
            "subtree root was never watched"
        )
        for nested in (moved / "utils", moved / "utils" / "dnd"):
            assert self._wait_for(lambda n=nested: str(n) in watches()), (
                f"nested directory {nested} of a moved subtree was never watched"
            )

    def test_edit_below_the_first_level_of_a_moved_subtree_is_seen(
        self, watcher, tmp_path
    ):
        _obj, seen, root = watcher
        staging = self._staging_tree(tmp_path)
        moved = root / "moved_subtree"
        staging.rename(moved)

        leaf = moved / "utils" / "dnd" / "leaf.js"
        assert self._wait_for(lambda: str(leaf) in seen), "initial walk missed the leaf"
        seen.clear()

        leaf.write_text("export const L = 2;\n")
        assert self._wait_for(lambda: str(leaf) in seen), (
            f"edit below the first level of a moved subtree went unseen; saw {seen}"
        )

    def test_directory_recreated_at_a_reaped_path_is_rearmed(self, watcher, tmp_path):
        obj, seen, root = watcher
        sub = root / "toggled"
        sub.mkdir()
        assert self._wait_for(lambda: str(sub) in obj.watcher.watched), (
            "directory was never watched on first creation"
        )

        shutil.rmtree(sub)
        sub.mkdir()

        barrier = root / "_barrier.js"
        barrier.write_text("export const B = 1;\n")
        assert self._wait_for(lambda: str(barrier) in seen), "run loop never caught up"
        seen.clear()

        target = sub / "after_recreate.js"
        target.write_text("export const D = 1;\n")
        assert self._wait_for(lambda: str(target) in seen), (
            f"edit in a recreated directory went unseen; saw {seen}"
        )

    def test_run_resyncs_on_overflow_and_lets_other_faults_out(self):
        from odoo.libs.inotify import QueueOverflow
        from odoo.service import _watcher as w

        def _watcher_raising(exc):
            class _W:
                def close(self):
                    pass

                def read(self, timeout_s):
                    raise exc

            return _W()

        obj = w.FSWatcherInotify.__new__(w.FSWatcherInotify)
        w.FSWatcherBase.__init__(obj)
        obj.block_duration_s = 0.05
        obj.started = True
        obj.watcher = _watcher_raising(QueueOverflow())
        calls = []

        def _sync_watches_after_overflow():
            calls.append(1)
            obj.started = False

        obj._sync_watches_after_overflow = _sync_watches_after_overflow
        obj.run()
        assert calls == [1], "overflow did not trigger a resync"

        obj.started = True
        obj.watcher = _watcher_raising(RuntimeError("unmounted"))
        with pytest.raises(RuntimeError, match="unmounted"):
            obj.run()

    def test_asset_burst_signals_twice_not_once_per_file(self, watcher):
        obj, _seen, _root = watcher
        from odoo.service._watcher import FSWatcherBase

        inserts = []
        with patch.object(
            FSWatcherBase,
            "_signal_asset_change",
            lambda self, path: inserts.append(path),
        ):
            for i in range(50):
                obj.on_asset_file_changed(f"/x/f{i}.js")
            assert len(inserts) == 1, "leading edge did not fire exactly once"
            obj._end_burst()
            assert len(inserts) == 2, "trailing flush did not fire"
            obj._end_burst()
            assert len(inserts) == 2, "idle with nothing pending still signalled"

    def test_edit_after_the_leading_edge_is_still_signalled(self, watcher):
        obj, _seen, _root = watcher
        from odoo.service._watcher import FSWatcherBase

        inserts = []
        with patch.object(
            FSWatcherBase,
            "_signal_asset_change",
            lambda self, path: inserts.append(path),
        ):
            obj.on_asset_file_changed("/x/first.js")
            assert len(inserts) == 1
            obj.on_asset_file_changed("/x/second.js")
            assert len(inserts) == 1, "should be pending, not immediate"
            obj._end_burst()
            assert len(inserts) == 2, "the later edit was never signalled"

    def test_a_single_edit_still_signals_immediately(self, watcher):
        obj, _seen, _root = watcher
        from odoo.service._watcher import FSWatcherBase

        inserts = []
        with patch.object(
            FSWatcherBase,
            "_signal_asset_change",
            lambda self, path: inserts.append(path),
        ):
            obj.on_asset_file_changed("/x/only.js")
            assert len(inserts) == 1, "single edit was deferred to the idle tick"


class TestBothBackendsWatchTheSameTree:
    def _paths(self, dev_mode):
        import odoo.tools
        from odoo.service._watcher import FSWatcherBase

        with patch.dict(odoo.tools.config.options, {"dev_mode": dev_mode}):
            return FSWatcherBase.get_watch_paths()

    def test_reload_mode_watches_the_addons_roots(self):
        import odoo.addons

        assert self._paths(["reload"]) == list(odoo.addons.__path__)
        assert self._paths(["reload", "assets"]) == list(odoo.addons.__path__)

    def test_assets_only_mode_watches_whole_static_trees(self):
        paths = self._paths(["assets"])
        assert paths, "no addon exposes a static tree; the test proved nothing"
        assert all(p.endswith("/static") for p in paths)

    def test_both_backends_read_the_same_function(self):
        from odoo.service import _watcher as w

        assert not hasattr(w, "inotify_watch_paths"), (
            "the per-backend tree calculation is back"
        )
        source = pathlib.Path(w.__file__).read_text(encoding="utf-8")
        assert source.count("self.get_watch_paths()") == 2
        assert "odoo.addons.__path__" not in source.split("class FSWatcherWatchdog")[1]


class TestBothBackendsCoalesceAssetBursts:
    DBS = ("db1", "db2", "db3")

    def _count_transactions(self, cls, files, monkeypatch):
        import odoo.db
        import odoo.tools
        from odoo.orm.runtime.registry import Registry
        from odoo.service import _watcher as w

        opened = []

        class _Cursor:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def execute(self, *args):
                pass

        class _Connection:
            def cursor(self):
                opened.append(1)
                return _Cursor()

        monkeypatch.setattr(odoo.db, "db_connect", lambda name: _Connection())
        monkeypatch.setitem(odoo.tools.config.options, "db_name", list(self.DBS))
        monkeypatch.setattr(
            type(Registry.registries), "snapshot", property(lambda self: {})
        )

        obj = cls.__new__(cls)
        w.FSWatcherBase.__init__(obj)
        obj._needs_burst_timer = False
        for i in range(files):
            obj.on_asset_file_changed(f"/addon/static/src/f{i}.js")
        obj._end_burst()
        return len(opened)

    @pytest.mark.parametrize("backend", ["FSWatcherWatchdog", "FSWatcherInotify"])
    def test_a_burst_costs_two_flushes_per_database_not_one_per_file(
        self, backend, monkeypatch
    ):
        from odoo.service import _watcher as w

        cls = getattr(w, backend)
        count = self._count_transactions(cls, 20, monkeypatch)
        assert count == 2 * len(self.DBS)
        assert count < 20 * len(self.DBS)

    def test_the_watchdog_backend_arms_a_timer_for_its_trailing_edge(self):
        from odoo.service import _watcher as w

        assert w.FSWatcherWatchdog._needs_burst_timer is True
        assert w.FSWatcherInotify._needs_burst_timer is False

    def test_the_timer_fires_the_trailing_flush(self, monkeypatch):
        from odoo.service import _watcher as w

        flushed = []
        obj = w.FSWatcherWatchdog.__new__(w.FSWatcherWatchdog)
        w.FSWatcherBase.__init__(obj)
        monkeypatch.setattr(obj, "_BURST_FLUSH_S", 0.01)
        monkeypatch.setattr(
            w.FSWatcherBase, "_signal_asset_change", lambda self, p: flushed.append(p)
        )
        obj.on_asset_file_changed("/addon/static/src/a.js")
        assert len(flushed) == 1, "leading edge did not fire"
        obj.on_asset_file_changed("/addon/static/src/b.js")
        deadline = time.monotonic() + 2.0
        while len(flushed) < 2 and time.monotonic() < deadline:
            time.sleep(0.01)
        assert len(flushed) == 2, "the timer never emitted the trailing flush"


class TestWatcherWiring:
    def test_the_watchdog_observer_schedules_recursively(self, srv):
        scheduled = []

        class _Observer:
            def schedule(self, handler, path, recursive):
                scheduled.append((path, recursive))

        with patch.object(srv, "Observer", _Observer, create=True):
            srv.FSWatcherWatchdog()

        assert scheduled, "no path was scheduled"
        assert all(recursive for _, recursive in scheduled), scheduled

    def test_the_inotify_thread_is_a_daemon(self, srv):
        watcher = object.__new__(srv.FSWatcherInotify)
        watcher.started = False
        watcher.thread = None
        made = []

        class _Thread:
            def __init__(self, **kwargs):
                self.daemon = False
                made.append(self)

            def start(self):
                pass

        with patch.object(srv.threading, "Thread", _Thread):
            watcher.start()

        assert made and made[0].daemon is True

    def test_start_arms_the_loop_and_stop_disarms_it(self, srv):
        watcher = object.__new__(srv.FSWatcherInotify)
        srv.FSWatcherBase.__init__(watcher)
        watcher.started = False
        watcher.thread = None

        with patch.object(srv.threading, "Thread", MagicMock()):
            watcher.start()
        assert watcher.started is True

        watcher.thread = MagicMock()
        watcher.watcher = MagicMock()
        watcher.stop()
        assert watcher.started is False
        assert watcher.thread is None

    def test_the_event_loop_blocks_for_its_block_duration(self, srv):
        watcher = object.__new__(srv.FSWatcherInotify)
        srv.FSWatcherBase.__init__(watcher)
        watcher.started = True
        watcher.block_duration_s = 0.25
        seen = []

        def read(timeout_s):
            seen.append(timeout_s)
            watcher.started = False
            return []

        watcher.watcher = MagicMock(read=read)
        watcher.run()

        assert seen == [0.25]


class TestInotifyWatchDirectory:
    @staticmethod
    def _watcher(srv, add_watch):
        w = object.__new__(srv.FSWatcherInotify)
        w.watcher = MagicMock()
        w.watcher.add_watch.side_effect = add_watch
        return w

    def test_a_directory_is_watched_with_the_listen_mask(self, srv, tmp_path):
        w = self._watcher(srv, [7])
        w._watch_directory(tmp_path)
        w.watcher.add_watch.assert_called_once_with(tmp_path, srv.INOTIFY_LISTEN_EVENTS)

    def test_a_failure_to_watch_is_logged_and_swallowed(self, srv, tmp_path, caplog):
        import logging

        w = self._watcher(srv, [OSError("ENOSPC: inotify limit reached")])
        with caplog.at_level(logging.WARNING, logger="odoo.service._watcher"):
            w._watch_directory(tmp_path)
        assert any(r.levelno >= logging.WARNING for r in caplog.records)

    def test_a_released_watcher_ignores_the_request(self, srv, tmp_path):
        w = object.__new__(srv.FSWatcherInotify)
        w.watcher = None
        w._watch_directory(tmp_path)
