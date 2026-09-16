from unittest.mock import MagicMock, patch

import pytest

import odoo
import odoo.tools
from odoo.service import _factory, _process_state
from odoo.service import settings as server_settings
from odoo.service.settings import ServerSettings, installed


@pytest.fixture
def start(monkeypatch):
    def _run(
        *,
        evented=False,
        workers=0,
        dev_mode=(),
        inotify=True,
        watchdog=False,
        watcher_raises=None,
        watcher_start_raises=None,
        watcher_stop_raises=None,
        phoenix=False,
        run_returns=0,
        run_raises=None,
        watcher_owner=True,
    ):
        classes = {
            name: MagicMock(name=name)
            for name in ("WebsocketServer", "PreforkServer", "ThreadedServer")
        }
        for cls in classes.values():
            cls.return_value.is_reload_watcher_owner = watcher_owner
            cls.return_value.run = MagicMock(
                side_effect=run_raises, return_value=run_returns
            )
        made_watchers = []

        def _watcher_factory(name):
            def _make():
                if watcher_raises is not None:
                    raise watcher_raises
                w = MagicMock(name=name)
                w.start.side_effect = watcher_start_raises
                w.stop.side_effect = watcher_stop_raises
                made_watchers.append((name, w))
                return w

            return _make

        cfg = {
            **dict(odoo.tools.config.options),
            "workers": workers,
            "max_cron_threads": 0,
            "job_workers": 0,
            "http_enable": True,
            "dev_mode": list(dev_mode),
            "test_enable": False,
        }
        monkeypatch.setattr(_process_state, "server", None, raising=False)
        monkeypatch.setattr(_process_state, "server_phoenix", phoenix, raising=False)
        with (
            patch.multiple(_factory, **classes),
            patch.object(_factory, "load_server_wide_modules"),
            installed(ServerSettings.from_config(cfg)),
            patch.object(_factory, "_limit_malloc_arenas") as arenas,
            patch.object(_factory, "_warn_on_connection_budget"),
            patch.object(_factory, "inotify", inotify or None),
            patch.object(_factory, "watchdog", watchdog or None),
            patch.object(_factory, "FSWatcherInotify", _watcher_factory("inotify")),
            patch.object(_factory, "FSWatcherWatchdog", _watcher_factory("watchdog")),
            patch.object(_factory, "_reexec_server") as reexec,
        ):
            monkeypatch.setattr(odoo, "evented", evented, raising=False)
            try:
                rc = _factory.start(["db"], stop=False)
            except Exception as exc:
                rc = exc
        return rc, classes, made_watchers, arenas, reexec

    return _run


class TestServerSelection:
    def test_evented_gets_the_websocket_server(self, start):
        _, classes, _, arenas, _ = start(evented=True, workers=4)
        classes["WebsocketServer"].assert_called_once()
        assert not classes["PreforkServer"].called, (
            "`--workers` is meaningless under gevent; choosing prefork there "
            "forks a longpolling server into worker processes"
        )
        assert not arenas.called

    def test_workers_gets_the_prefork_server(self, start):
        _, classes, _, arenas, _ = start(workers=4)
        classes["PreforkServer"].assert_called_once()
        assert not classes["ThreadedServer"].called
        assert not arenas.called, (
            "the malloc arena cap is a per-process tuning for the threaded "
            "server; a prefork master forks before it would matter"
        )

    def test_no_workers_gets_the_threaded_server_and_caps_arenas(self, start):
        _, classes, _, arenas, _ = start(workers=0)
        classes["ThreadedServer"].assert_called_once()
        arenas.assert_called_once()

    def test_the_chosen_server_is_published_as_the_module_global(self, start):
        start(workers=0)
        assert _process_state.server is not None, (
            "`restart()` and the signal handlers reach the running server "
            "through this name; leaving it None makes SIGHUP a no-op"
        )


class TestWatcherSelection:
    def test_no_dev_mode_starts_no_watcher(self, start):
        _, _, watchers, _, _ = start(dev_mode=())
        assert watchers == []

    @pytest.mark.parametrize("mode", ["reload", "assets"])
    def test_either_dev_mode_starts_one(self, start, mode):
        _, _, watchers, _, _ = start(dev_mode=(mode,))
        assert [name for name, _ in watchers] == ["inotify"]

    def test_watchdog_is_the_fallback_when_inotify_is_absent(self, start):
        _, _, watchers, _, _ = start(dev_mode=("reload",), inotify=False, watchdog=True)
        assert [name for name, _ in watchers] == ["watchdog"]

    def test_evented_never_watches(self, start):
        _, _, watchers, _, _ = start(evented=True, dev_mode=("reload",))
        assert watchers == [], (
            "the gevent server is the longpolling process; reloading it on a "
            "source edit would drop every open websocket"
        )

    def test_replacement_does_not_duplicate_the_supervisors_watcher(self, start):
        _, _, watchers, _, _ = start(
            dev_mode=("reload",), workers=2, watcher_owner=False
        )
        assert watchers == []

    def test_neither_backend_warns_and_serves_anyway(self, start, caplog):
        rc, _, watchers, _, _ = start(
            dev_mode=("reload",), inotify=False, watchdog=False
        )
        assert watchers == []
        assert rc == 0, "no watcher is a degraded mode, not a boot failure"
        assert "autoreload is disabled" in caplog.text.lower()

    def test_the_assets_warning_names_the_workaround(self, start, caplog):
        start(dev_mode=("assets",), inotify=False, watchdog=False)
        assert "--dev=xml" in caplog.text, (
            "with --dev=assets and no watcher the sources are silently stale; "
            "the message has to say what to use instead"
        )

    def test_a_watcher_that_cannot_start_does_not_stop_the_server(self, start, caplog):
        rc, classes, _watchers, _, _ = start(
            dev_mode=("reload",), watcher_raises=OSError("inotify watch limit")
        )
        assert rc == 0
        classes["ThreadedServer"].return_value.run.assert_called_once()
        assert "NOT picked up" in caplog.text


class TestShutdownAndPhoenix:
    def test_start_and_cleanup_failures_do_not_prevent_serving(self, start, caplog):
        rc, classes, watchers, _, _ = start(
            dev_mode=("reload",),
            watcher_start_raises=RuntimeError("watch start failed"),
            watcher_stop_raises=RuntimeError("watch cleanup failed"),
        )
        assert rc == 0
        watchers[0][1].stop.assert_called_once()
        classes["ThreadedServer"].return_value.run.assert_called_once()
        assert "watch start failed" in caplog.text
        assert "watch cleanup failed" in caplog.text

    def test_failed_watcher_start_is_cleaned_up_before_serving(self, start):
        rc, classes, watchers, _, _ = start(
            dev_mode=("reload",),
            watcher_start_raises=RuntimeError("thread start failed"),
        )
        assert rc == 0
        watchers[0][1].stop.assert_called_once()
        classes["ThreadedServer"].return_value.run.assert_called_once()

    def test_watcher_cleanup_does_not_mask_the_server_failure(self, start, caplog):
        original = RuntimeError("bind failed")
        rc, _, _, _, _ = start(
            dev_mode=("reload",),
            run_raises=original,
            watcher_stop_raises=RuntimeError("observer cleanup failed"),
        )
        assert rc is original
        assert "observer cleanup failed" in caplog.text

    def test_watcher_cleanup_preserves_the_server_exit_status(self, start, caplog):
        rc, _, _, _, _ = start(
            dev_mode=("reload",),
            run_returns=7,
            watcher_stop_raises=RuntimeError("observer cleanup failed"),
        )
        assert rc == 7
        assert "observer cleanup failed" in caplog.text

    def test_the_watcher_is_stopped_even_when_run_raises(self, start):
        rc, _, watchers, _, _ = start(
            dev_mode=("reload",), run_raises=RuntimeError("bind failed")
        )
        assert isinstance(rc, RuntimeError)
        assert watchers, "a watcher was created"
        (
            watchers[0][1].stop.assert_called_once(),
            (
                "an inotify watcher left running holds its watch descriptors for "
                "the life of the process"
            ),
        )

    def test_a_phoenix_stop_re_execs(self, start):
        _, _, _, _, reexec = start(phoenix=True)
        (
            reexec.assert_called_once(),
            (
                "the phoenix flag is how a reload says 'I stopped serving so the "
                "new binary can'; not re-execing there just exits"
            ),
        )

    def test_an_ordinary_stop_does_not(self, start):
        _, _, _, _, reexec = start(phoenix=False)
        assert not reexec.called

    def test_a_none_return_becomes_a_zero_exit(self, start):
        rc, _, _, _, _ = start(run_returns=None)
        assert rc == 0, "None is 'served and was signalled', which is success"

    def test_a_failing_preload_code_survives(self, start):
        rc, _, _, _, _ = start(run_returns=3)
        assert rc == 3


class TestTheReadyLineNamesTheDeploymentShape:
    def _said(self, server):
        server.log_ready()
        call = server.logger.info.call_args
        return call.args[0] % call.args[1:]

    def test_threaded(self):
        from .conftest import threaded_server

        with server_settings.override(
            workers=0,
            http_interface="127.0.0.1",
            http_port=8069,
            max_cron_threads=2,
            job_workers=1,
            limit_time_real=120,
            limit_time_real_cron=300,
            limit_memory_soft=1024 * 1024 * 1024,
            db_maxconn=32,
        ):
            server = threaded_server(httpd=MagicMock(max_http_threads=14))
            said = self._said(server)
        assert said == (
            "Ready: threaded, pid %d; HTTP 127.0.0.1:8069 (14 threads), 2 cron "
            "thread(s), 1 job thread(s); limit_time_real 120s, cron 300s, job 300s; "
            "limit_memory_soft 1024 MiB; db_maxconn 32" % server.pid
        )

    def test_prefork(self):
        from .conftest import prefork_server

        with server_settings.override(
            workers=4,
            http_interface="127.0.0.1",
            http_port=8069,
            gevent_port=8072,
            max_cron_threads=2,
            job_workers=0,
            limit_request=1000,
            limit_time_cpu=60,
            limit_time_real=120,
            limit_memory_soft=2048 * 1024 * 1024,
            db_maxconn=64,
        ):
            server = prefork_server(population=4)
            said = self._said(server)
        assert said == (
            "Ready: prefork, pid %d; HTTP 127.0.0.1:8069 (4 workers), websocket "
            "127.0.0.1:8072, 2 cron worker(s), 0 job worker(s); limit_request 1000, "
            "limit_time_cpu 60s; limit_time_real 120s, cron 120s, job 120s; "
            "limit_memory_soft 2048 MiB; db_maxconn 64" % server.pid
        )

    def test_no_http_says_so(self):
        from .conftest import prefork_server

        with server_settings.override(http_enable=False, workers=2):
            server = prefork_server()
            said = self._said(server)
        assert "no HTTP" in said and "websocket" not in said


class TestReadinessFollowsThePreload:
    def test_no_server_is_not_ready(self):
        with patch.object(_process_state, "server", None):
            assert _process_state.is_ready() is False

    def test_a_registered_server_is_ready_once_nothing_preloads(self):
        with (
            patch.object(_process_state, "server", MagicMock()),
            patch.object(_process_state, "preloading", set()),
        ):
            assert _process_state.is_ready() is True
            with _process_state.preloading_database("prod"):
                assert _process_state.is_ready() is False
                with _process_state.preloading_database("other"):
                    assert _process_state.preloading == {"prod", "other"}
                assert _process_state.is_ready() is False
            assert _process_state.is_ready() is True

    def test_a_failed_preload_does_not_stay_pending(self):
        with patch.object(_process_state, "preloading", set()):
            with pytest.raises(RuntimeError), _process_state.preloading_database("x"):
                raise RuntimeError("load failed")
            assert not _process_state.preloading

    def test_preload_registries_marks_the_database_while_it_loads(self):
        from odoo.service import lifecycle

        seen = []

        def new(dbname, **kwargs):
            seen.append(set(_process_state.preloading))
            return MagicMock()

        with (
            patch.object(_process_state, "preloading", set()),
            patch.object(lifecycle.Registry, "new", side_effect=new),
            patch.object(lifecycle, "_limit_resident_registries"),
            server_settings.override(test_enable=False, db_name=("a",)),
        ):
            lifecycle.preload_registries(["a"])
        assert seen == [{"a"}]
        assert not _process_state.preloading

    def test_a_test_run_serves_its_client_mid_load_so_it_does_not_gate(self):
        from odoo.service import lifecycle

        seen = []

        def new(dbname, **kwargs):
            seen.append(set(_process_state.preloading))
            return MagicMock()

        with (
            patch.object(_process_state, "preloading", set()),
            patch.object(lifecycle.Registry, "new", side_effect=new),
            patch.object(lifecycle, "_limit_resident_registries"),
            patch.object(lifecycle, "_run_post_install_tests", return_value=0),
            patch.object(lifecycle, "_get_test_run_rc", return_value=0),
            patch.object(lifecycle, "_get_assertion_report"),
            server_settings.override(test_enable=True, db_name=("a",)),
        ):
            lifecycle.preload_registries(["a"])
        assert seen == [set()]
