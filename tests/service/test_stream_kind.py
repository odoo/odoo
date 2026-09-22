from __future__ import annotations

import contextlib
import threading
from unittest.mock import MagicMock, patch

import pytest

from odoo.service import _stream, _threaded, _worker
from odoo.service import settings as server_settings
from odoo.service._cron import (
    CRON_LISTENER,
    LISTENER_KINDS,
    STREAM_HEARTBEAT_S,
    STREAM_LISTENER,
    CronSchedule,
)

from .conftest import threaded_server


class _StopHarness(BaseException):
    pass


@pytest.fixture
def listen_server(monkeypatch):
    monkeypatch.setattr(threading.current_thread(), "start_time", None, raising=False)
    server = threaded_server()
    server.logger = MagicMock()
    return server


class TestTheKind:
    def test_it_is_the_third_kind_and_sweeps_on_a_heartbeat(self):
        assert STREAM_LISTENER in LISTENER_KINDS
        assert STREAM_LISTENER.heartbeat == STREAM_HEARTBEAT_S
        assert CRON_LISTENER.heartbeat is None
        assert STREAM_LISTENER.population_setting == "stream_workers"
        assert STREAM_LISTENER.max_age_setting == "limit_time_worker_stream"

    def test_every_known_database_is_due_on_every_pass(self):
        schedule = CronSchedule()
        with patch.object(
            schedule, "reset_known_databases", return_value=["a", "b"]
        ) as relist:
            assert STREAM_LISTENER.due_databases(schedule, set()) == ["a", "b"]
            assert STREAM_LISTENER.due_databases(schedule, {"a"}) == ["a", "b"]
        assert relist.call_count == 2, "the heartbeat re-lists, notified or not"

    def test_the_cron_kind_still_reads_its_schedule(self):
        schedule = CronSchedule()
        with (
            patch.object(schedule, "get_due_databases", return_value=["b"]) as due,
            patch.object(schedule, "reset_known_databases") as relist,
        ):
            assert CRON_LISTENER.due_databases(schedule, {"b"}) == ["b"]
        due.assert_called_once_with({"b"})
        relist.assert_not_called()

    def test_the_step_resolves_to_the_service_module(self):
        assert STREAM_LISTENER.process_jobs() is _stream.process_streams

    def test_the_stream_worker_is_never_recycled_by_default(self):
        with server_settings.override(limit_time_worker_cron=301):
            assert STREAM_LISTENER.max_age() == 0, "its connections outlive a sweep"
        with server_settings.override(limit_time_worker_stream=17):
            assert STREAM_LISTENER.max_age() == 17

    def test_the_budget_is_the_cron_s(self):
        with server_settings.override(limit_time_real=120, limit_time_real_cron=90):
            assert STREAM_LISTENER.real_time_budget() == 90


class TestTheThreadedSweep:
    def _select_timeouts(self, listen_server, iterations, kind):
        seen = []

        class _Sel:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def register(self, *a, **kw):
                pass

            def select(self, timeout=None):
                seen.append(timeout)
                if len(seen) >= iterations:
                    raise _StopHarness
                return []

        with (
            patch("odoo.service._cron.db.db_connect"),
            patch("odoo.service._cron.arm_cron_listen", return_value=True),
            patch("odoo.service._cron.drain_cron_notifies", return_value=set()),
            patch("odoo.service._cron.get_cron_databases", return_value=["db1"]),
            patch("odoo.service._cron.selectors.DefaultSelector", _Sel),
            server_settings.override(db_name=["db1"]),
            patch("odoo.service._threaded.time.sleep", lambda _s: None),
        ):
            with pytest.raises(_StopHarness):
                listen_server._run_listener_thread(
                    0,
                    channel=kind.channel,
                    process_jobs=MagicMock(),
                    label=kind.name,
                    max_age=0,
                    kind=kind,
                )
        return seen

    def test_the_stream_thread_waits_one_heartbeat_between_passes(self, listen_server):
        timeouts = self._select_timeouts(listen_server, 3, STREAM_LISTENER)
        assert timeouts[0] == 0, "first pass sweeps at once"
        assert timeouts[1:] == [STREAM_HEARTBEAT_S, STREAM_HEARTBEAT_S]

    def test_the_cron_thread_keeps_its_own_interval(self, listen_server):
        timeouts = self._select_timeouts(listen_server, 2, CRON_LISTENER)
        assert timeouts[1] == _threaded.CRON_POLL_INTERVAL_S


class TestTheWorker:
    def test_stopping_closes_what_the_process_holds(self):
        worker = _worker.WorkerStream.__new__(_worker.WorkerStream)
        with (
            patch.object(_worker.WorkerCron, "stop") as stop,
            patch.object(_stream, "shutdown") as shutdown,
        ):
            worker.stop()
        shutdown.assert_called_once()
        stop.assert_called_once()

    def test_the_threaded_stop_closes_them_too(self):
        with (
            patch.object(_stream, "shutdown") as shutdown,
            patch.object(
                _threaded.ThreadedServer, "_count_stuck_http_threads", return_value=0
            ),
        ):
            server = threaded_server()
            server.logger = MagicMock()
            server.httpd = None
            server._listener_threads = []
            with (
                patch.object(server, "_join_listener_threads", create=True),
                contextlib.suppress(Exception),
            ):
                server.stop()
        shutdown.assert_called_once()


class TestTheStep:
    def test_a_database_without_the_model_is_left_alone(self):
        runtime = _stream.StreamRuntime()
        registry = MagicMock()
        registry.__contains__ = lambda self, name: False
        with (
            patch.object(_stream, "Registry", return_value=registry),
            patch.object(_stream, "RUNTIME", runtime),
            patch.object(_stream, "working_on_database"),
        ):
            _stream.process_streams("plain_db")
        assert not runtime.leads("plain_db")

    def test_a_database_that_lost_the_model_releases_its_lease(self):
        runtime = _stream.StreamRuntime()
        runtime._leases["gone_db"] = MagicMock()
        closed = []
        runtime.hold("gone_db", 7, lambda: closed.append(7))
        registry = MagicMock()
        registry.__contains__ = lambda self, name: False
        with (
            patch.object(_stream, "Registry", return_value=registry),
            patch.object(_stream, "RUNTIME", runtime),
            patch.object(_stream, "working_on_database"),
        ):
            _stream.process_streams("gone_db")
        assert closed == [7]
        assert not runtime.leads("gone_db")

    def test_a_led_database_is_reconciled_through_its_model(self):
        runtime = _stream.StreamRuntime()
        model = MagicMock()
        registry = MagicMock()
        registry.__contains__ = lambda self, name: name == _stream.STREAM_MODEL
        registry.__getitem__ = lambda self, name: model
        with (
            patch.object(_stream, "Registry", return_value=registry),
            patch.object(_stream, "RUNTIME", runtime),
            patch.object(_stream, "working_on_database"),
            patch.object(runtime, "lease", return_value=True),
        ):
            _stream.process_streams("led_db")
        model._reconcile.assert_called_once_with("led_db", runtime)

    def test_a_database_led_elsewhere_is_not_reconciled(self):
        runtime = _stream.StreamRuntime()
        model = MagicMock()
        registry = MagicMock()
        registry.__contains__ = lambda self, name: name == _stream.STREAM_MODEL
        registry.__getitem__ = lambda self, name: model
        with (
            patch.object(_stream, "Registry", return_value=registry),
            patch.object(_stream, "RUNTIME", runtime),
            patch.object(_stream, "working_on_database"),
            patch.object(runtime, "lease", return_value=False),
        ):
            _stream.process_streams("other_db")
        model._reconcile.assert_not_called()
