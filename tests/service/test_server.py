import contextlib
import errno
import fcntl
import logging
import os
import signal
import socket
import threading
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import psutil
import psycopg
import pytest

from odoo.service import (
    _base_server,
    _limits,
    _prefork,
    _process_state,
    _reload,
    _threaded,
)
from odoo.service import settings as server_settings
from odoo.tools import SQL

from .conftest import build_worker, common_server, threaded_server
from .conftest import websocket_server as build_websocket_server


@pytest.fixture(scope="module")
def srv():
    import odoo.service.server as mod

    return mod


def stamp_rpc_model_method(monkeypatch, value=""):
    monkeypatch.setattr(
        threading.current_thread(), "rpc_model_method", value, raising=False
    )


@pytest.fixture
def multi(worker_multi):
    worker_multi.cron_timeout = None
    worker_multi.limit_request = 100
    return worker_multi


@pytest.fixture
def worker_cron(srv, multi):
    wc = srv.WorkerCron(multi)
    wc.pid = os.getpid()
    cursor = MagicMock()
    shared_cnx = MagicMock()
    cursor._cnx = shared_cnx
    cursor.connection = shared_cnx
    wc.listener._cursor = cursor
    wc.listener._selector = MagicMock()
    return wc


@pytest.fixture
def prefork_server(srv):
    with server_settings.override(workers=4):
        return srv.PreforkServer(None)


class TestEmptyPipe:
    def test_drains_all_data(self):
        r, w = os.pipe()
        try:
            os.set_blocking(r, False)
            os.write(w, b"hello world")
            _limits.empty_pipe(r)
            with pytest.raises(BlockingIOError):
                os.read(r, 1)
        finally:
            os.close(r)
            os.close(w)

    def test_already_empty_does_not_raise(self):
        r, w = os.pipe()
        try:
            os.set_blocking(r, False)
            _limits.empty_pipe(r)
        finally:
            os.close(r)
            os.close(w)

    def test_drains_multiple_bytes(self):
        r, w = os.pipe()
        try:
            os.set_blocking(r, False)
            os.write(w, b"a" * 512)
            _limits.empty_pipe(r)
            with pytest.raises(BlockingIOError):
                os.read(r, 1)
        finally:
            os.close(r)
            os.close(w)


class TestWebsocketServerWatchdogSurvivesErrors:
    def test_transient_failure_does_not_retire_the_watchdog(self, srv):
        server = build_websocket_server(
            logger=logging.getLogger("test.evented.watchdog")
        )
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) == 1:
                raise psutil.NoSuchProcess(1234)

        class _StopLoop(Exception):
            pass

        def fake_sleep(_beat):
            if len(calls) >= 2:
                raise _StopLoop

        with (
            patch.object(server, "check_limits", flaky),
            patch.object(_threaded.time, "sleep", fake_sleep),
            patch.object(os, "getppid", return_value=1),
        ):
            with pytest.raises(_StopLoop):
                server.run_watchdog(beat=0)
        assert len(calls) == 2, "watchdog stopped checking after one failure"


class TestPreforkServerProcessSignals:
    def test_sigint_raises_keyboard_interrupt(self, prefork_server):
        prefork_server.queue.append(signal.SIGINT)
        with pytest.raises(KeyboardInterrupt):
            prefork_server.apply_pending_signals()

    def test_sigterm_raises_keyboard_interrupt(self, prefork_server):
        prefork_server.queue.append(signal.SIGTERM)
        with pytest.raises(KeyboardInterrupt):
            prefork_server.apply_pending_signals()

    def test_sighup_sets_phoenix_flag_and_raises(self, prefork_server):
        prefork_server.queue.append(signal.SIGHUP)
        with patch.object(_process_state, "server_phoenix", False):
            with pytest.raises(KeyboardInterrupt):
                prefork_server.apply_pending_signals()
            assert _process_state.server_phoenix is True

    def test_sigttin_increments_population(self, prefork_server):
        prefork_server.queue.append(signal.SIGTTIN)
        prefork_server.apply_pending_signals()
        assert prefork_server.population == 5

    def test_sigttou_decrements_population(self, prefork_server):
        prefork_server.queue.append(signal.SIGTTOU)
        prefork_server.apply_pending_signals()
        assert prefork_server.population == 3

    def test_multiple_signals_processed_in_order(self, prefork_server):
        prefork_server.queue.append(signal.SIGTTIN)
        prefork_server.queue.append(signal.SIGTTOU)
        prefork_server.apply_pending_signals()
        assert prefork_server.population == 4

    def test_empty_queue_is_noop(self, prefork_server):
        prefork_server.apply_pending_signals()
        assert prefork_server.population == 4


class TestCronListenerConnect:
    def _mock_db(self, *, in_recovery: bool):
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (in_recovery,)
        conn.cursor.return_value = cursor
        return conn, cursor

    def _connect(self, worker_cron, in_recovery):
        conn, cursor = self._mock_db(in_recovery=in_recovery)
        with (
            patch(
                "odoo.service._cron.db.db_connect", return_value=conn
            ) as mock_connect,
            patch(
                "odoo.service._cron.selectors.DefaultSelector",
                return_value=MagicMock(),
            ),
        ):
            worker_cron.listener.connect()
        return conn, cursor, mock_connect

    def _executed(self, cursor):
        return [
            query.code if isinstance(query, SQL) else query
            for query in (c.args[0] for c in cursor.execute.call_args_list)
        ]

    def test_executes_listen_when_not_in_recovery(self, worker_cron):
        _, cursor, _ = self._connect(worker_cron, in_recovery=False)
        assert 'LISTEN "cron_trigger"' in self._executed(cursor)

    def test_skips_listen_in_recovery_mode(self, worker_cron):
        _, cursor, _ = self._connect(worker_cron, in_recovery=True)
        assert 'LISTEN "cron_trigger"' not in self._executed(cursor)

    def test_commits_after_listen(self, worker_cron):
        _, cursor, _ = self._connect(worker_cron, in_recovery=False)
        cursor.commit.assert_called_once()

    def test_holds_the_cursor_it_opened(self, worker_cron):
        _, cursor, _ = self._connect(worker_cron, in_recovery=False)
        assert worker_cron.listener._cursor is cursor
        assert worker_cron.listener.connected

    def test_connects_to_postgres_database(self, worker_cron):
        _, _, mock_connect = self._connect(worker_cron, in_recovery=False)
        mock_connect.assert_called_once_with("postgres")

    def test_connect_replaces_the_previous_pair_as_a_unit(self, worker_cron):
        old_cursor = worker_cron.listener._cursor
        old_selector = worker_cron.listener._selector
        _, cursor, _ = self._connect(worker_cron, in_recovery=False)
        assert worker_cron.listener._cursor is cursor
        old_cursor.close.assert_called_once()
        old_selector.close.assert_called_once()


class TestWorkerCronSleepWatchdog:
    def _select_timeout(self, worker_cron):
        worker_cron.db_queue.clear()
        worker_cron.schedule._list_databases = list
        worker_cron.schedule.get_due_databases([])
        with (
            patch("odoo.service._worker.time.sleep"),
            patch("odoo.service._worker.empty_pipe"),
        ):
            worker_cron.sleep()
        return worker_cron.listener._selector.select.call_args.kwargs["timeout"]

    def test_idle_sleep_capped_below_tight_watchdog(self, worker_cron):
        worker_cron.watchdog_timeout = 30
        timeout = self._select_timeout(worker_cron)
        assert timeout <= 15, timeout

    def test_idle_sleep_uncapped_when_watchdog_disabled(self, worker_cron):
        worker_cron.watchdog_timeout = None
        timeout = self._select_timeout(worker_cron)
        assert 59 <= timeout <= 60, timeout

    def test_default_watchdog_does_not_shorten_idle_sleep_below_interval(
        self, worker_cron
    ):
        worker_cron.watchdog_timeout = 120
        timeout = self._select_timeout(worker_cron)
        assert 59 <= timeout <= 60, timeout


class TestWorkerCronProcessWorkReconnect:
    def test_operational_error_triggers_reconnect(self, worker_cron):
        worker_cron.listener._cursor.connection.notifies.side_effect = (
            psycopg.OperationalError("SSL connection has been closed unexpectedly")
        )
        with (
            patch("odoo.service._cron.get_cron_databases", return_value=["testdb"]),
            patch.object(worker_cron.listener, "connect") as mock_reconnect,
        ):
            worker_cron.process_work()
        mock_reconnect.assert_called_once()

    def test_operational_error_returns_early(self, worker_cron):
        worker_cron.listener._cursor.connection.notifies.side_effect = (
            psycopg.OperationalError("SSL")
        )
        with (
            patch("odoo.service._cron.get_cron_databases", return_value=["db1"]),
            patch.object(worker_cron.listener, "connect"),
        ):
            worker_cron.process_work()
        assert len(worker_cron.db_queue) == 0
        assert worker_cron.db_count == 0

    def test_operational_error_releases_the_cursor_and_not_the_connection(
        self, worker_cron
    ):
        """This pinned `["cnx", "cursor"]` until 2026-08-30.  Both halves were wrong.

        The ORDER was wrong: `BaseCursor._close` rolls back before releasing,
        so with the connection closed first that rollback raises and the cursor
        logs it at ERROR with a traceback -- which the `suppress(Exception)` at
        the call site hid as an exception but not as a log.  A real prefork
        SIGTERM printed two, one per cron/job worker.

        The second close was wrong AT ALL: `_close` ends in
        `pool.give_back(...)`, so the connection is the pool's by then.  For
        `postgres` the pool has already closed it; for a pooled DSN it is being
        held open for the next borrower and closing it costs them a reconnect.

        The order was never argued for -- it arrived in `138282fe3ea`, a bulk
        characterisation suite that described the code rather than justifying
        it.  The one argument FOR connection-first (rolling back on a half-dead
        socket might block) was measured and does not hold: with the backend
        terminated server-side, cursor-only took 0.15ms and logged nothing.
        """
        old_cnx = worker_cron.listener._cursor.connection
        old_cursor = worker_cron.listener._cursor
        call_order = []
        old_cnx.close.side_effect = lambda: call_order.append("cnx")
        old_cursor.close.side_effect = lambda: call_order.append("cursor")
        old_cnx.notifies.side_effect = psycopg.OperationalError("SSL")

        with (
            patch("odoo.service._cron.get_cron_databases", return_value=[]),
            patch.object(worker_cron.listener, "connect"),
        ):
            worker_cron.process_work()

        assert call_order == ["cursor"]

    def test_close_error_on_broken_connection_is_suppressed(self, worker_cron):
        cursor = worker_cron.listener._cursor
        cursor.connection.notifies.side_effect = psycopg.OperationalError("SSL")
        cursor.connection.close.side_effect = Exception("already closed")
        cursor.close.side_effect = Exception("already closed")

        with (
            patch("odoo.service._cron.get_cron_databases", return_value=["db1"]),
            patch.object(worker_cron.listener, "connect") as mock_reconnect,
        ):
            worker_cron.process_work()

        mock_reconnect.assert_called_once()

    def test_reconnect_failure_does_not_propagate(self, worker_cron):
        worker_cron.listener._cursor.connection.notifies.side_effect = (
            psycopg.OperationalError("SSL")
        )
        with (
            patch("odoo.service._cron.get_cron_databases", return_value=["db1"]),
            patch.object(
                worker_cron.listener,
                "connect",
                side_effect=psycopg.OperationalError("postgres still unreachable"),
            ),
            patch("odoo.service._worker.time.sleep"),
        ):
            worker_cron.process_work()
        assert worker_cron.listener._backoff.attempts == 1

    def test_reconnect_attempts_escalate_across_cycles(self, worker_cron):
        """Cycle 1 loses the connection mid-drain; every later cycle finds the
        listener disconnected and keeps paying an escalating backoff."""
        worker_cron.listener._cursor.connection.notifies.side_effect = (
            psycopg.OperationalError("SSL")
        )
        per_cycle_sleeps: list[list[float]] = []
        current_cycle_sleeps: list[float] = []
        with (
            patch("odoo.service._cron.get_cron_databases", return_value=["db1"]),
            patch.object(
                worker_cron.listener,
                "connect",
                side_effect=Exception("PG down"),
            ),
            patch(
                "odoo.service._worker.time.sleep",
                side_effect=lambda s: current_cycle_sleeps.append(s),  # noqa: PLW0108
            ),
        ):
            for _ in range(7):
                current_cycle_sleeps = []
                worker_cron.process_work()
                per_cycle_sleeps.append(current_cycle_sleeps)
        cycle_totals = [sum(c) for c in per_cycle_sleeps]
        assert cycle_totals == [2, 4, 8, 16, 32, 60, 60]
        max_chunk = worker_cron.multi.beat / 2
        for cycle in per_cycle_sleeps:
            for chunk in cycle:
                assert chunk <= max_chunk + 1e-6, (
                    f"chunk {chunk} exceeds master.beat/2 = {max_chunk}"
                )


class TestWorkerCronStartGracefulShutdown:
    def test_start_stops_retrying_when_alive_cleared(self, worker_cron):
        worker_cron._selector = MagicMock()
        worker_cron.multi.socket = None
        sleep_calls = []

        def stop_after_first(secs):
            sleep_calls.append(secs)
            worker_cron.alive = False
            if len(sleep_calls) > 1:
                raise AssertionError(
                    "start() kept retrying PG after alive was cleared "
                    "(boot-time connect loop ignores graceful stop)"
                )

        with (
            patch.object(
                worker_cron.listener,
                "connect",
                side_effect=Exception("PG unreachable"),
            ),
            patch.object(
                worker_cron,
                "_sleep_with_watchdog",
                side_effect=stop_after_first,
            ),
            patch("odoo.service._worker.Worker.start"),
            patch("odoo.service._worker.os.nice"),
        ):
            worker_cron.start()

        assert sleep_calls == [2]
        assert worker_cron.alive is False

    def test_sleep_with_watchdog_breaks_when_alive_cleared(self, worker_cron):
        slept = []

        def fake_sleep(chunk):
            slept.append(chunk)
            worker_cron.alive = False

        with patch("odoo.service._worker.time.sleep", side_effect=fake_sleep):
            worker_cron._sleep_with_watchdog(60)

        assert slept == [worker_cron.multi.beat / 2]
        assert sum(slept) < 60


class TestWorkerCronProcessWorkScheduling:
    @pytest.fixture
    def mock_ir_cron(self):
        mock_module = MagicMock()
        with patch.dict(
            "sys.modules", {"odoo.addons.base.models.ir_cron": mock_module}
        ):
            yield mock_module.IrCron

    def test_no_databases_returns_immediately(self, worker_cron):
        worker_cron.listener._cursor.connection.notifies.return_value = iter([])
        with patch("odoo.service._cron.get_cron_databases", return_value=[]):
            worker_cron.process_work()
        assert len(worker_cron.db_queue) == 0
        assert worker_cron.db_count == 0

    def test_all_databases_queued_on_first_call(self, worker_cron, mock_ir_cron):
        worker_cron.listener._cursor.connection.notifies.return_value = iter([])
        with (
            patch(
                "odoo.service._cron.get_cron_databases",
                return_value=["db1", "db2", "db3"],
            ),
            patch("odoo.service._cron.db"),
        ):
            worker_cron.process_work()
        assert worker_cron.db_count == 3
        assert len(worker_cron.db_queue) == 2

    def test_notified_database_placed_first_in_queue(self, worker_cron, mock_ir_cron):
        notif = MagicMock()
        notif.channel = "cron_trigger"
        notif.payload = "urgent_db"
        worker_cron.listener._cursor.connection.notifies.return_value = iter([notif])

        with (
            patch(
                "odoo.service._cron.get_cron_databases",
                return_value=["slow_db", "urgent_db"],
            ),
            patch("odoo.service._cron.db"),
        ):
            worker_cron.process_work()

        assert "slow_db" in worker_cron.db_queue
        assert "urgent_db" not in worker_cron.db_queue

    def test_notified_db_not_in_db_list_is_ignored(self, worker_cron, mock_ir_cron):
        notif = MagicMock()
        notif.channel = "cron_trigger"
        notif.payload = "unknown_db"
        worker_cron.listener._cursor.connection.notifies.return_value = iter([notif])

        with (
            patch("odoo.service._cron.get_cron_databases", return_value=["real_db"]),
            patch("odoo.service._cron.db"),
        ):
            worker_cron.process_work()

        all_dbs = list(worker_cron.db_queue) + [
            mock_ir_cron._process_jobs.call_args[0][0]
        ]
        assert "unknown_db" not in all_dbs

    def test_existing_queue_skips_notification_polling(self, worker_cron, mock_ir_cron):
        worker_cron.db_queue.append("pending_db")
        worker_cron.db_count = 1

        with patch("odoo.service._cron.db"):
            worker_cron.process_work()

        worker_cron.listener._cursor.connection.notifies.assert_not_called()

    def test_request_count_incremented(self, worker_cron, mock_ir_cron):
        worker_cron.listener._cursor.connection.notifies.return_value = iter([])
        with (
            patch("odoo.service._cron.get_cron_databases", return_value=["db1"]),
            patch("odoo.service._cron.db"),
        ):
            worker_cron.process_work()
        assert worker_cron.request_count == 1


class TestWorkerStopReleasesResources:
    def test_selector_is_closed(self, bare_worker):
        bare_worker._selector = MagicMock()
        bare_worker.stop()
        bare_worker._selector.close.assert_called_once_with()

    def test_stop_before_start_does_not_raise(self, srv, multi):
        w = build_worker(srv.Worker, multi)
        w.stop()

    def test_cron_worker_closes_the_selector_and_the_cursor_only(self, worker_cron):
        """The connection is the pool's, not ours.

        `Cursor._close` ends in `pool.give_back(...)`.  For `postgres`, a
        maintenance database, that closes the connection itself; for a pooled
        DSN it holds it open for the next borrower.  So a second close here is
        dead in the first case and destroys a live pooled connection in the
        second.  This asserted the opposite until 2026-08-30.
        """
        selector = worker_cron.listener._selector
        cursor = worker_cron.listener._cursor
        worker_cron.stop()
        selector.close.assert_called_once_with()
        cursor.close.assert_called_once_with()
        cursor.connection.close.assert_not_called()

    def test_a_failing_cursor_close_does_not_escape(self, worker_cron):
        worker_cron.listener._cursor.close.side_effect = psycopg.OperationalError(
            "gone"
        )
        worker_cron.stop()


class TestWorkerCronCheckLimits:
    def test_worker_stays_alive_within_limit(self, srv, worker_cron):
        worker_cron.alive_time = time.monotonic()
        with (
            server_settings.override(limit_time_worker_cron=3600),
            patch.object(srv.Worker, "check_limits"),
        ):
            worker_cron.check_limits()
        assert worker_cron.alive is True

    def test_worker_dies_when_age_exceeded(self, srv, worker_cron):
        worker_cron.alive_time = time.monotonic() - 99_999
        with (
            server_settings.override(limit_time_worker_cron=60),
            patch.object(srv.Worker, "check_limits"),
        ):
            worker_cron.check_limits()
        assert worker_cron.alive is False

    def test_zero_limit_never_expires(self, srv, worker_cron):
        worker_cron.alive_time = time.monotonic() - 99_999
        with (
            server_settings.override(limit_time_worker_cron=0),
            patch.object(srv.Worker, "check_limits"),
        ):
            worker_cron.check_limits()
        assert worker_cron.alive is True

    def test_negative_limit_never_expires(self, srv, worker_cron):
        worker_cron.alive_time = time.monotonic() - 99_999
        with (
            server_settings.override(limit_time_worker_cron=-1),
            patch.object(srv.Worker, "check_limits"),
        ):
            worker_cron.check_limits()
        assert worker_cron.alive is True


_WORKER_CONFIG = {"limit_memory_soft": 0, "limit_time_cpu": 60}
_RESOURCE_ATTRS = {"ru_utime": 0.0, "ru_stime": 0.0}


def _resource_stub():
    mock_resource = MagicMock()
    mock_resource.getrusage.return_value.ru_utime = 0.0
    mock_resource.getrusage.return_value.ru_stime = 0.0
    mock_resource.getrlimit.return_value = (0, 9999)
    mock_resource.RLIMIT_CPU = 0
    mock_resource.RUSAGE_SELF = 0
    return mock_resource


@contextlib.contextmanager
def worker_check_limits_env(memory_bytes=0, config_override=None):
    cfg = {**_WORKER_CONFIG, **(config_override or {})}
    mock_resource = _resource_stub()
    mock_memory_info = MagicMock(return_value=memory_bytes)
    with (
        server_settings.override(**cfg),
        patch("odoo.service._limits.get_memory_rss", mock_memory_info),
        patch("odoo.service._worker.resource", mock_resource),
    ):
        yield SimpleNamespace(resource=mock_resource, get_memory_rss=mock_memory_info)


@pytest.fixture
def bare_worker(srv, multi):
    return build_worker(
        srv.Worker,
        multi,
        ppid=os.getppid(),
        pid=os.getpid(),
        _process_handle=MagicMock(),
    )


class TestWorkerCheckLimits:
    def test_healthy_worker_stays_alive(self, bare_worker):
        with worker_check_limits_env():
            bare_worker.check_limits()
        assert bare_worker.alive is True

    def test_parent_changed_sets_alive_false(self, bare_worker):
        bare_worker.ppid = 99999
        with worker_check_limits_env():
            bare_worker.check_limits()
        assert bare_worker.alive is False

    def test_request_max_reached_sets_alive_false(self, bare_worker):
        bare_worker.request_count = 100
        bare_worker.request_max = 100
        with worker_check_limits_env():
            bare_worker.check_limits()
        assert bare_worker.alive is False

    def test_request_max_zero_means_unlimited(self, bare_worker):
        bare_worker.request_count = 0
        bare_worker.request_max = 0
        with worker_check_limits_env():
            bare_worker.check_limits()
        assert bare_worker.alive is True

    def test_memory_soft_exceeded_sets_alive_false(self, bare_worker):
        with worker_check_limits_env(
            memory_bytes=500,
            config_override={"limit_memory_soft": 100},
        ):
            bare_worker.check_limits()
        assert bare_worker.alive is False

    def test_cpu_rlimit_set_to_usage_plus_limit(self, bare_worker):
        with worker_check_limits_env(config_override={"limit_time_cpu": 30}) as env:
            env.resource.getrusage.return_value.ru_utime = 5.0
            env.resource.getrusage.return_value.ru_stime = 3.0
            env.resource.getrlimit.return_value = (0, 9999)
            bare_worker.check_limits()
        env.resource.setrlimit.assert_called_once_with(0, (38, 9999))

    def test_cpu_rlimit_not_armed_when_disabled(self, bare_worker):
        with worker_check_limits_env(config_override={"limit_time_cpu": 0}) as env:
            env.resource.getrusage.return_value.ru_utime = 8.0
            env.resource.getrusage.return_value.ru_stime = 0.0
            bare_worker.check_limits()
        env.resource.setrlimit.assert_not_called()
        assert bare_worker.alive is True

    def test_rss_not_read_when_soft_limit_disabled(self, bare_worker):
        with worker_check_limits_env(config_override={"limit_memory_soft": 0}) as env:
            bare_worker.check_limits()
        env.get_memory_rss.assert_not_called()
        assert bare_worker.alive is True

    def test_rss_read_when_soft_limit_enabled(self, bare_worker):
        with worker_check_limits_env(
            memory_bytes=50, config_override={"limit_memory_soft": 100}
        ) as env:
            bare_worker.check_limits()
        env.get_memory_rss.assert_called_once()
        assert bare_worker.alive is True


class TestIdleRegistryEvictionRunsOnEveryPulse:
    """registry_idle_timeout was inert in the steady state it exists for: the
    evictor's only production caller was Registry._new_finalize, so a server
    with a stable database set never evicted after boot. Every flavour's
    periodic pulse sweeps it now; the timeout<=0 no-op guard lives in the
    method itself."""

    def test_worker_check_limits_sweeps(self, bare_worker):
        with (
            worker_check_limits_env(),
            patch("odoo.service._worker.Registry._evict_idle_registries") as evict,
        ):
            bare_worker.check_limits()
        evict.assert_called_once_with()

    def test_threaded_check_limits_sweeps(self, srv):
        ts = threaded_server()
        ts.logger = MagicMock()
        ts.limits_reached_threads = set()
        ts._overrun_start_times = {}
        ts.limit_reached_time = None
        with (
            patch.object(
                srv.ThreadedServer, "get_memory_over_soft_limit", return_value=None
            ),
            patch("odoo.service._threaded.Registry._evict_idle_registries") as evict,
        ):
            ts.check_limits()
        evict.assert_called_once_with()

    def test_evented_check_limits_sweeps(self, srv):
        es = build_websocket_server()
        with (
            patch.object(
                srv.WebsocketServer, "get_memory_over_soft_limit", return_value=None
            ),
            patch("odoo.service._threaded.Registry._evict_idle_registries") as evict,
        ):
            es.check_limits()
        evict.assert_called_once_with()


class TestWorkerRunFaultExit:
    def _make_worker(self, srv, multi):
        w = build_worker(srv.Worker, multi, pid=os.getpid())
        w.start = MagicMock()
        w.stop = MagicMock()
        w.check_limits = MagicMock()
        w.sleep = MagicMock()
        return w

    def test_work_fault_propagates_as_systemexit_1(self, srv, multi):
        w = self._make_worker(srv, multi)
        w.process_work = MagicMock(side_effect=ValueError("boom"))
        with pytest.raises(SystemExit) as exc_info:
            w.run()
        assert exc_info.value.code == 1
        w.stop.assert_called_once()
        logged = " ".join(str(c) for c in w.logger.info.call_args_list)
        assert "Exiting cleanly" not in logged, "crash mislabeled as clean exit"

    def test_clean_exit_returns_none_and_logs(self, srv, multi):
        w = self._make_worker(srv, multi)

        def stop_loop():
            w.alive = False

        w.process_work = MagicMock(side_effect=stop_loop)
        result = w.run()
        assert result is None
        logged = " ".join(str(c) for c in w.logger.info.call_args_list)
        assert "Exiting cleanly" in logged
        w.stop.assert_called_once()


class TestCommonServerCallbacks:
    @pytest.fixture(autouse=True)
    def _restore_callbacks(self, srv):
        original = list(_base_server._on_stop_hooks)
        yield
        _base_server._on_stop_hooks[:] = original

    def test_on_stop_appends_callback(self, srv):
        cb = MagicMock()
        srv.CommonServer.register_on_stop_hook(cb)
        assert cb in _base_server._on_stop_hooks

    def test_stop_calls_all_registered_callbacks(self, srv):
        server = common_server()
        cb1, cb2 = MagicMock(), MagicMock()
        _base_server._on_stop_hooks.extend([cb1, cb2])
        server.stop()
        cb1.assert_called_once()
        cb2.assert_called_once()

    def test_stop_continues_after_callback_exception(self, srv):
        server = common_server()
        cb1 = MagicMock(side_effect=RuntimeError("boom"))
        cb1.__name__ = "cb1"
        cb2 = MagicMock()
        cb2.__name__ = "cb2"
        _base_server._on_stop_hooks.extend([cb1, cb2])
        server.stop()
        cb2.assert_called_once()

    def test_stop_survives_partial_hook_without_name(self, srv):
        import functools

        server = common_server()

        def _boom(_tag):
            raise RuntimeError("cleanup failed")

        raising_partial = functools.partial(_boom, "x")
        assert not hasattr(raising_partial, "__name__")
        later = MagicMock()
        later.__name__ = "later"
        _base_server._on_stop_hooks.extend([raising_partial, later])

        server.stop()

        server.logger.warning.assert_called_once()
        later.assert_called_once()


class TestPreforkProcessZombie:
    def test_normal_exit_pops_worker(self, prefork_server):
        prefork_server.remove_worker = MagicMock()
        with patch("os.waitpid", side_effect=[(1234, 0), (0, 0)]):
            prefork_server.reap_exited_workers()
        prefork_server.remove_worker.assert_called_once_with(1234)

    def test_exit_code_3_does_not_raise(self, prefork_server):
        prefork_server.remove_worker = MagicMock()
        with patch("os.waitpid", side_effect=[(5678, 3 << 8), (0, 0)]):
            prefork_server.reap_exited_workers()
        prefork_server.remove_worker.assert_called_once_with(5678)

    def test_echild_breaks_loop_cleanly(self, prefork_server):
        prefork_server.remove_worker = MagicMock()
        with patch("os.waitpid", side_effect=OSError(errno.ECHILD, "no children")):
            prefork_server.reap_exited_workers()
        prefork_server.remove_worker.assert_not_called()

    def test_other_oserror_propagates(self, prefork_server):
        with patch("os.waitpid", side_effect=OSError(errno.EINTR, "interrupted")):
            with pytest.raises(OSError):
                prefork_server.reap_exited_workers()


class TestLongPollingPopenReconciliation:
    def test_reconcile_sets_returncode_and_clears_ref(self, prefork_server):
        popen = MagicMock()
        popen.returncode = None
        prefork_server.long_polling_popen = popen
        prefork_server._reconcile_long_polling_popen(0)
        assert popen.returncode == 0
        assert prefork_server.long_polling_popen is None

    def test_reconcile_uses_sigkill_sentinel_when_code_unknown(self, prefork_server):
        popen = MagicMock()
        popen.returncode = None
        prefork_server.long_polling_popen = popen
        prefork_server._reconcile_long_polling_popen(None)
        assert popen.returncode == -signal.SIGKILL

    def test_reconcile_is_noop_without_a_handle(self, prefork_server):
        prefork_server.long_polling_popen = None
        prefork_server._reconcile_long_polling_popen(0)

    def test_note_worker_exit_reconciles_the_handle(self, prefork_server):
        popen = MagicMock()
        popen.returncode = None
        prefork_server.long_polling_pid = 9999
        prefork_server.long_polling_popen = popen
        prefork_server.long_polling_spawn_time = time.monotonic()
        prefork_server._record_worker_exit(9999, 0)
        assert popen.returncode == 0
        assert prefork_server.long_polling_popen is None

    def test_real_popen_no_resourcewarning_after_reconcile(self, prefork_server):
        import gc
        import subprocess
        import sys
        import warnings

        popen = subprocess.Popen([sys.executable, "-c", "pass"])
        _pid, status = os.waitpid(popen.pid, 0)
        prefork_server.long_polling_popen = popen
        prefork_server._reconcile_long_polling_popen(os.waitstatus_to_exitcode(status))
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ResourceWarning)
            del popen
            gc.collect()
        leaked = [w for w in caught if issubclass(w.category, ResourceWarning)]
        assert not leaked, (
            f"the reaped Popen still warns, so it was never reconciled: "
            f"{[str(w.message) for w in leaked]}"
        )


class TestWorkerExitsAreCountedByOutcome:
    @staticmethod
    def _exit(prefork_server, pid, status, *, ready=True, killed=False, age_s=60.0):
        w = MagicMock()
        w.__class__.__name__ = "WorkerHTTP"
        w.spawn_time = time.monotonic() - age_s
        w.ready = ready
        if killed:
            prefork_server._killed_workers[pid] = w
        else:
            prefork_server.workers[pid] = w
        prefork_server._record_worker_exit(pid, status)

    @pytest.mark.parametrize(
        ("status", "kwargs", "outcome"),
        [
            (0, {}, "clean"),
            (3 << 8, {}, "crash"),
            (signal.SIGSEGV, {}, "crash"),
            (signal.SIGTERM, {}, "terminated"),
            (signal.SIGKILL, {"killed": True, "ready": True}, "timeout"),
            (signal.SIGKILL, {"killed": True, "ready": False}, "crash"),
        ],
    )
    def test_each_exit_lands_in_one_bucket(
        self, prefork_server, status, kwargs, outcome
    ):
        self._exit(prefork_server, 100, status, **kwargs)
        counts = prefork_server._get_census()["worker_exits"]
        assert counts[outcome] == 1
        assert sum(counts.values()) == 1

    def test_the_count_survives_the_healthy_lifetime_short_cut(self, prefork_server):
        self._exit(prefork_server, 1, 1 << 8, age_s=0.0)
        self._exit(prefork_server, 2, 1 << 8, age_s=600.0)
        assert prefork_server._get_census()["worker_exits"]["crash"] == 2

    def test_a_generation_exit_is_not_a_worker_exit(self, prefork_server):
        prefork_server.handoff.replacement = MagicMock(pid=777)
        prefork_server._record_worker_exit(777, 0)
        assert sum(prefork_server._get_census()["worker_exits"].values()) == 0


class TestPreforkRespawnBackoff:
    @staticmethod
    def _worker(prefork_server, pid, *, age_s):
        w = MagicMock()
        w.__class__.__name__ = "WorkerHTTP"
        w.spawn_time = time.monotonic() - age_s
        prefork_server.workers[pid] = w
        return w

    def test_young_crash_arms_exponential_backoff(self, prefork_server):
        self._worker(prefork_server, 1234, age_s=0.0)
        before = time.monotonic()
        prefork_server._record_worker_exit(1234, 1 << 8)
        assert prefork_server._get_respawn_hold("WorkerHTTP").fast_deaths == 1
        assert prefork_server._get_respawn_hold("WorkerHTTP").not_before > before
        self._worker(prefork_server, 1235, age_s=0.0)
        prefork_server._record_worker_exit(1235, 1 << 8)
        assert prefork_server._get_respawn_hold("WorkerHTTP").fast_deaths == 2

    def test_backoff_capped(self, prefork_server):
        prefork_server._get_respawn_hold("WorkerHTTP").fast_deaths = 20
        self._worker(prefork_server, 1, age_s=0.0)
        t = time.monotonic()
        prefork_server._record_worker_exit(1, 1 << 8)
        assert (
            prefork_server._get_respawn_hold("WorkerHTTP").not_before - t
            <= _prefork.WORKER_RESPAWN_BACKOFF_CAP_S + 0.5
        )

    def test_healthy_exit_clears_throttle(self, prefork_server):
        prefork_server._get_respawn_hold("WorkerHTTP").fast_deaths = 3
        prefork_server._get_respawn_hold("WorkerHTTP").not_before = (
            time.monotonic() + 100
        )
        self._worker(
            prefork_server, 42, age_s=_prefork.WORKER_MIN_HEALTHY_LIFETIME_S + 5
        )
        prefork_server._record_worker_exit(42, 1 << 8)
        assert prefork_server._get_respawn_hold("WorkerHTTP").fast_deaths == 0
        assert prefork_server._get_respawn_hold("WorkerHTTP").not_before == 0.0

    def test_clean_young_exit_neither_arms_nor_clears(self, prefork_server):
        prefork_server._get_respawn_hold("WorkerHTTP").fast_deaths = 2
        prefork_server._get_respawn_hold("WorkerHTTP").not_before = 555.0
        self._worker(prefork_server, 7, age_s=1.0)
        prefork_server._record_worker_exit(7, 0)
        assert prefork_server._get_respawn_hold("WorkerHTTP").fast_deaths == 2
        assert prefork_server._get_respawn_hold("WorkerHTTP").not_before == 555.0

    def test_external_sigkill_young_worker_arms_backoff(self, prefork_server):
        prefork_server._get_respawn_hold("WorkerHTTP").fast_deaths = 0
        before = time.monotonic()
        self._worker(prefork_server, 8, age_s=1.0)
        prefork_server._record_worker_exit(8, signal.SIGKILL)
        assert prefork_server._get_respawn_hold("WorkerHTTP").fast_deaths == 1
        assert prefork_server._get_respawn_hold("WorkerHTTP").not_before > before

    def test_the_watchdogs_sigkill_of_a_ready_worker_is_not_a_crash(
        self, prefork_server
    ):
        """Measured 2026-09-15 with --limit-time-real 3 and a 20 s request:
        the timed-out worker's SIGKILL armed the back-off, and the next
        request found no worker at all for the length of it."""
        prefork_server._get_respawn_hold("WorkerHTTP").fast_deaths = 0
        w = self._worker(prefork_server, 9, age_s=1.0)
        w.ready = True
        with patch.object(_prefork.os, "kill"):
            prefork_server.kill_worker(9, signal.SIGKILL)
        assert 9 in prefork_server._killed_workers
        prefork_server._record_worker_exit(9, signal.SIGKILL)
        assert prefork_server._get_respawn_hold("WorkerHTTP").fast_deaths == 0
        assert prefork_server._get_respawn_hold("WorkerHTTP").not_before == 0.0
        assert 9 not in prefork_server._killed_workers
        w.close.assert_called_once()

    def test_sigterm_killed_young_worker_not_counted(self, prefork_server):
        prefork_server._get_respawn_hold("WorkerHTTP").fast_deaths = 0
        self._worker(prefork_server, 81, age_s=1.0)
        prefork_server._record_worker_exit(81, signal.SIGTERM)
        assert prefork_server._get_respawn_hold("WorkerHTTP").fast_deaths == 0

    def test_segfault_young_worker_arms_backoff(self, prefork_server):
        prefork_server._get_respawn_hold("WorkerHTTP").fast_deaths = 0
        before = time.monotonic()
        self._worker(prefork_server, 82, age_s=0.0)
        prefork_server._record_worker_exit(82, signal.SIGSEGV)
        assert prefork_server._get_respawn_hold("WorkerHTTP").fast_deaths == 1
        assert prefork_server._get_respawn_hold("WorkerHTTP").not_before > before

    def test_unknown_pid_ignored(self, prefork_server):
        prefork_server._get_respawn_hold("WorkerHTTP").fast_deaths = 1
        prefork_server._record_worker_exit(99999, 1 << 8)
        assert prefork_server._get_respawn_hold("WorkerHTTP").fast_deaths == 1

    def test_long_polling_young_crash_arms_backoff(self, prefork_server):
        prefork_server.long_polling_pid = 4321
        prefork_server.long_polling_spawn_time = time.monotonic() - 1.0
        before = time.monotonic()
        prefork_server._record_worker_exit(4321, 1 << 8)
        assert (
            prefork_server._get_respawn_hold(_prefork.LONG_POLLING_KIND).fast_deaths
            == 1
        )
        assert (
            prefork_server._get_respawn_hold(_prefork.LONG_POLLING_KIND).not_before
            > before
        )

    def test_long_polling_clean_young_exit_neither_arms_nor_clears(
        self, prefork_server
    ):
        prefork_server._get_respawn_hold(_prefork.LONG_POLLING_KIND).fast_deaths = 2
        prefork_server.long_polling_pid = 4321
        prefork_server.long_polling_spawn_time = time.monotonic() - 1.0
        prefork_server._record_worker_exit(4321, 0)
        assert (
            prefork_server._get_respawn_hold(_prefork.LONG_POLLING_KIND).fast_deaths
            == 2
        )

    def test_long_polling_healthy_lifetime_clears_throttle(self, prefork_server):
        prefork_server._get_respawn_hold(_prefork.LONG_POLLING_KIND).fast_deaths = 3
        prefork_server._get_respawn_hold(_prefork.LONG_POLLING_KIND).not_before = (
            time.monotonic() + 100
        )
        prefork_server.long_polling_pid = 4321
        prefork_server.long_polling_spawn_time = (
            time.monotonic() - _prefork.WORKER_MIN_HEALTHY_LIFETIME_S - 5
        )
        prefork_server._record_worker_exit(4321, 1 << 8)
        assert (
            prefork_server._get_respawn_hold(_prefork.LONG_POLLING_KIND).fast_deaths
            == 0
        )
        assert (
            prefork_server._get_respawn_hold(_prefork.LONG_POLLING_KIND).not_before
            == 0.0
        )

    def test_spawn_missing_workers_skips_during_backoff(self, prefork_server):
        prefork_server._get_respawn_hold(_prefork.SPAWN_HOLD).not_before = (
            time.monotonic() + 100
        )
        prefork_server.spawn_worker = MagicMock()
        prefork_server.spawn_long_polling_process = MagicMock()
        prefork_server.spawn_missing_workers()
        prefork_server.spawn_worker.assert_not_called()
        prefork_server.spawn_long_polling_process.assert_not_called()

    def test_fork_oserror_returns_none_and_releases_pipes(
        self, prefork_server, monkeypatch
    ):
        prefork_server.generation = 0
        fake_worker = MagicMock()
        klass = MagicMock(return_value=fake_worker)
        monkeypatch.setattr(os, "fork", MagicMock(side_effect=OSError("EAGAIN")))
        before = time.monotonic()
        result = prefork_server.spawn_worker(klass, {})
        assert result is None
        fake_worker.close.assert_called_once()
        assert prefork_server.workers == {}
        assert prefork_server._get_respawn_hold(_prefork.SPAWN_HOLD).fast_deaths == 1
        assert prefork_server._get_respawn_hold(_prefork.SPAWN_HOLD).not_before > before

    def test_repeated_fork_failures_grow_the_backoff(self, prefork_server, monkeypatch):
        prefork_server.generation = 0
        klass = MagicMock(return_value=MagicMock())
        monkeypatch.setattr(os, "fork", MagicMock(side_effect=OSError("EMFILE")))
        prefork_server.spawn_worker(klass, {})
        first_hold = (
            prefork_server._get_respawn_hold(_prefork.SPAWN_HOLD).not_before
            - time.monotonic()
        )
        prefork_server.spawn_worker(klass, {})
        second_hold = (
            prefork_server._get_respawn_hold(_prefork.SPAWN_HOLD).not_before
            - time.monotonic()
        )
        assert prefork_server._get_respawn_hold(_prefork.SPAWN_HOLD).fast_deaths == 2
        assert second_hold > first_hold

    def test_fork_failure_hold_is_capped(self, prefork_server, monkeypatch):
        prefork_server.generation = 0
        prefork_server._get_respawn_hold(_prefork.SPAWN_HOLD).fast_deaths = 20
        klass = MagicMock(return_value=MagicMock())
        monkeypatch.setattr(os, "fork", MagicMock(side_effect=OSError("EMFILE")))
        t = time.monotonic()
        prefork_server.spawn_worker(klass, {})
        assert (
            prefork_server._get_respawn_hold(_prefork.SPAWN_HOLD).not_before - t
            <= _prefork.WORKER_RESPAWN_BACKOFF_CAP_S + 0.5
        )

    def test_long_polling_spawn_oserror_does_not_propagate(
        self, prefork_server, monkeypatch
    ):
        prefork_server.long_polling_pid = None
        monkeypatch.setattr(
            _prefork.subprocess,
            "Popen",
            MagicMock(side_effect=OSError("EAGAIN")),
        )
        before = time.monotonic()
        prefork_server.spawn_long_polling_process()
        assert prefork_server.long_polling_pid is None
        assert prefork_server._get_respawn_hold(_prefork.SPAWN_HOLD).fast_deaths == 1
        assert prefork_server._get_respawn_hold(_prefork.SPAWN_HOLD).not_before > before


class TestTheWebsocketPortIsTheMastersToo:
    def test_the_evented_child_is_handed_the_masters_listener(
        self, prefork_server, monkeypatch
    ):
        prefork_server.long_polling_pid = None
        prefork_server.websocket_socket = MagicMock(fileno=lambda: 42)
        popen = MagicMock(return_value=MagicMock(pid=555))
        monkeypatch.setattr(_prefork.subprocess, "Popen", popen)
        prefork_server.spawn_long_polling_process()
        kwargs = popen.call_args.kwargs
        assert kwargs["pass_fds"] == [42]
        assert kwargs["env"]["ODOO_HTTP_SOCKET_FD"] == "42", (
            "the child adopts it as its own http listener, under the name every "
            "ThreadedHTTPServer looks for"
        )
        assert "ODOO_HTTP_SOCKET_FD" not in os.environ

    def test_the_reload_candidate_is_handed_both_listeners(
        self, prefork_server, monkeypatch
    ):
        prefork_server.socket = MagicMock(fileno=lambda: 7)
        prefork_server.websocket_socket = MagicMock(fileno=lambda: 8)
        popen = MagicMock()
        monkeypatch.setattr(_reload.subprocess, "Popen", popen)
        monkeypatch.setattr(_reload, "stripped_sys_argv", lambda: ["odoo-bin"])
        prefork_server.handoff._spawn_candidate(9)
        kwargs = popen.call_args.kwargs
        assert sorted(kwargs["pass_fds"]) == [7, 8, 9]
        assert kwargs["env"]["ODOO_HTTP_SOCKET_FD"] == "7"
        assert kwargs["env"]["ODOO_WEBSOCKET_SOCKET_FD"] == "8"

    @pytest.mark.parametrize(
        "inherited_listener", [(socket.AF_INET, ("127.0.0.1", 0))], indirect=True
    )
    def test_a_two_socket_unit_hands_the_master_the_websocket_port(
        self, prefork_server, inherited_listener, monkeypatch
    ):
        expected = inherited_listener.getsockname()
        saved_fd4 = os.dup(4)
        try:
            os.dup2(inherited_listener.fileno(), 4, inheritable=True)
            prefork_server.interface, prefork_server.port = "127.0.0.1", 0
            prefork_server.open_pipe = MagicMock(return_value=(0, 0))
            with (
                server_settings.override(
                    http_enable=True,
                    http_socket_activation=False,
                    websocket_socket_activation=True,
                    gevent_port=0,
                ),
                patch.object(signal, "signal"),
            ):
                prefork_server.start()
            try:
                assert prefork_server.websocket_socket.getsockname() == expected
                assert not os.get_inheritable(4)
            finally:
                prefork_server.websocket_socket.detach()
                prefork_server.socket.close()
        finally:
            os.dup2(saved_fd4, 4)
            os.close(saved_fd4)

    def test_stop_closes_both_listeners(self, prefork_server):
        prefork_server.socket = MagicMock()
        prefork_server.websocket_socket = MagicMock()
        with (
            patch.object(_prefork.CommonServer, "stop"),
            patch.object(prefork_server, "stop_workers_gracefully"),
            patch.object(prefork_server, "_close_watchdog_selector"),
        ):
            prefork_server.stop()
        prefork_server.socket.close.assert_called_once_with()
        prefork_server.websocket_socket.close.assert_called_once_with()


class TestPreforkGracefulStopEscalation:
    def test_escalates_to_sigkill_after_deadline(self, prefork_server, monkeypatch):
        prefork_server.pid = os.getpid()
        prefork_server.long_polling_pid = None
        wedged = MagicMock()
        wedged.watchdog_timeout = None
        prefork_server.workers = {321: wedged}
        prefork_server.kill_worker = MagicMock()
        prefork_server.apply_pending_signals = MagicMock()
        prefork_server.kill_timed_out_workers = MagicMock()
        prefork_server.sleep = MagicMock()

        killed: list[tuple[int, int]] = []

        def fake_zombie():
            if killed:
                prefork_server.workers.pop(321, None)

        prefork_server.reap_exited_workers = MagicMock(side_effect=fake_zombie)
        monkeypatch.setattr(os, "kill", lambda pid, sig: killed.append((pid, sig)))
        monkeypatch.setattr(_limits, "GRACEFUL_STOP_TIMEOUT_S", 0.0)

        prefork_server.stop_workers_gracefully()

        assert (321, signal.SIGKILL) in killed
        assert not prefork_server.workers

    def test_stop_timeout_env_override(self, monkeypatch):
        logger = MagicMock()
        monkeypatch.setenv("ODOO_GRACEFUL_STOP_TIMEOUT", "300")
        assert _limits.get_graceful_stop_timeout(logger) == 300.0
        monkeypatch.setenv("ODOO_GRACEFUL_STOP_TIMEOUT", "0")
        assert _limits.get_graceful_stop_timeout(logger) == 1.0
        monkeypatch.setenv("ODOO_GRACEFUL_STOP_TIMEOUT", "garbage")
        assert (
            _limits.get_graceful_stop_timeout(logger) == _limits.GRACEFUL_STOP_TIMEOUT_S
        )
        monkeypatch.delenv("ODOO_GRACEFUL_STOP_TIMEOUT")
        assert (
            _limits.get_graceful_stop_timeout(logger) == _limits.GRACEFUL_STOP_TIMEOUT_S
        )


class TestPreforkInitTimeout:
    @staticmethod
    def _make(srv, **overrides):
        cfg = {
            "http_interface": "",
            "http_port": 8069,
            "workers": 2,
            "limit_time_real": 120,
            "limit_request": 100,
            "limit_time_real_cron": -1,
            "limit_time_real_job": -1,
            **overrides,
        }
        with (
            server_settings.override(**cfg),
        ):
            return srv.PreforkServer(MagicMock())

    def test_limit_time_real_zero_disables_http_watchdog(self, srv):
        s = self._make(srv, limit_time_real=0)
        assert s.timeout is None
        assert s.cron_timeout is None

    def test_default_limit_time_real_kept(self, srv):
        s = self._make(srv, limit_time_real=120)
        assert s.timeout == 120
        assert s.cron_timeout == 120

    def test_any_negative_cron_limit_inherits_limit_time_real(self, srv):
        s = self._make(srv, limit_time_real_cron=-5)
        assert s.cron_timeout == 120

    def test_negative_cron_limit_with_no_real_limit_disables_watchdog(self, srv):
        s = self._make(srv, limit_time_real=0, limit_time_real_cron=-5)
        assert s.cron_timeout is None

    def test_positive_cron_limit_kept(self, srv):
        s = self._make(srv, limit_time_real_cron=30)
        assert s.cron_timeout == 30

    def test_zero_cron_limit_disables_the_cron_watchdog_alone(self, srv):
        s = self._make(srv, limit_time_real_cron=0)
        assert s.cron_timeout is None, "--limit-time-real-cron=0 means no limit"
        assert s.timeout == 120, "and it must not disarm the http watchdog"


class TestStopLongPolling:
    def test_no_pid_is_noop(self, prefork_server):
        with patch.object(_prefork.os, "kill") as kill:
            prefork_server._stop_long_polling()
        kill.assert_not_called()

    def test_graceful_sigterm_no_escalation(self, prefork_server):
        prefork_server.long_polling_pid = 4321
        proc = MagicMock()
        with (
            patch.object(_prefork.psutil, "Process", return_value=proc),
            patch.object(_prefork.os, "kill") as kill,
        ):
            prefork_server._stop_long_polling()
        kill.assert_called_once_with(4321, signal.SIGTERM)
        proc.wait.assert_called_once()
        assert prefork_server.long_polling_pid is None

    def test_escalates_to_sigkill_on_timeout(self, prefork_server):
        prefork_server.long_polling_pid = 4321
        proc = MagicMock()
        proc.wait.side_effect = [psutil.TimeoutExpired(5), None]
        with (
            patch.object(_prefork.psutil, "Process", return_value=proc),
            patch.object(_prefork.os, "kill") as kill,
        ):
            prefork_server._stop_long_polling()
        assert [c.args for c in kill.call_args_list] == [
            (4321, signal.SIGTERM),
            (4321, signal.SIGKILL),
        ]
        assert prefork_server.long_polling_pid is None

    def test_already_dead_child(self, prefork_server):
        prefork_server.long_polling_pid = 4321
        with (
            patch.object(
                _prefork.psutil, "Process", side_effect=psutil.NoSuchProcess(4321)
            ),
            patch.object(_prefork.os, "kill") as kill,
        ):
            prefork_server._stop_long_polling()
        kill.assert_not_called()
        assert prefork_server.long_polling_pid is None

    def test_esrch_on_sigterm_still_waits_for_reap(self, prefork_server):
        prefork_server.long_polling_pid = 4321
        proc = MagicMock()
        with (
            patch.object(_prefork.psutil, "Process", return_value=proc),
            patch.object(_prefork.os, "kill", side_effect=ProcessLookupError),
        ):
            prefork_server._stop_long_polling()
        proc.wait.assert_called_once()


class TestPreforkProcessTimeout:
    def test_kills_timed_out_worker(self, prefork_server):
        stale = MagicMock()
        stale.watchdog_timeout = 30
        stale.watchdog_time = time.monotonic() - 60
        prefork_server.workers = {9999: stale}
        prefork_server.kill_worker = MagicMock()
        prefork_server.kill_timed_out_workers()
        prefork_server.kill_worker.assert_called_once_with(9999, signal.SIGKILL)

    def test_leaves_healthy_worker_alone(self, prefork_server):
        healthy = MagicMock()
        healthy.watchdog_timeout = 30
        healthy.watchdog_time = time.monotonic()
        prefork_server.workers = {1111: healthy}
        prefork_server.kill_worker = MagicMock()
        prefork_server.kill_timed_out_workers()
        prefork_server.kill_worker.assert_not_called()

    def test_none_watchdog_timeout_never_kills(self, prefork_server):
        w = MagicMock()
        w.watchdog_timeout = None
        w.watchdog_time = time.monotonic() - 99999
        prefork_server.workers = {2222: w}
        prefork_server.kill_worker = MagicMock()
        prefork_server.kill_timed_out_workers()
        prefork_server.kill_worker.assert_not_called()


class TestPreforkWorkerPop:
    @staticmethod
    def _register(prefork_server, pid, kind="workers_http"):
        worker = MagicMock()
        prefork_server.workers[pid] = worker
        getattr(prefork_server, kind)[pid] = worker
        return worker

    def test_the_worker_is_closed_so_its_pipes_are_released(self, prefork_server):
        worker = self._register(prefork_server, 1234)
        prefork_server.remove_worker(1234)
        worker.close.assert_called_once_with()

    def test_every_registry_forgets_the_pid(self, prefork_server):
        for kind in ("workers_http", "workers_cron", "workers_job"):
            self._register(prefork_server, 7, kind=kind)
            prefork_server.remove_worker(7)
            assert 7 not in prefork_server.workers, kind
            assert 7 not in getattr(prefork_server, kind), kind

    def test_a_worker_of_one_kind_does_not_disturb_the_others(self, prefork_server):
        self._register(prefork_server, 1, kind="workers_http")
        self._register(prefork_server, 2, kind="workers_cron")
        prefork_server.remove_worker(1)
        assert list(prefork_server.workers) == [2]
        assert list(prefork_server.workers_cron) == [2]
        assert prefork_server.workers_http == {}

    def test_the_evented_child_clears_long_polling_pid(self, prefork_server):
        prefork_server.long_polling_pid = 4321
        prefork_server.remove_worker(4321)
        assert prefork_server.long_polling_pid is None

    def test_an_unknown_pid_is_a_noop(self, prefork_server):
        worker = self._register(prefork_server, 1234)
        prefork_server.remove_worker(9999)
        assert 1234 in prefork_server.workers
        worker.close.assert_not_called()

    def test_popping_twice_does_not_raise(self, prefork_server):
        self._register(prefork_server, 1234)
        prefork_server.remove_worker(1234)
        prefork_server.remove_worker(1234)


class TestPreforkWorkerKill:
    def test_sends_signal(self, prefork_server):
        prefork_server.remove_worker = MagicMock()
        with patch("os.kill") as mock_kill:
            prefork_server.kill_worker(1234, signal.SIGTERM)
        mock_kill.assert_called_once_with(1234, signal.SIGTERM)

    def test_sigkill_also_pops_worker(self, prefork_server):
        prefork_server.remove_worker = MagicMock()
        with patch("os.kill"):
            prefork_server.kill_worker(1234, signal.SIGKILL)
        prefork_server.remove_worker.assert_called_once_with(1234)

    def test_sigterm_does_not_pop_worker(self, prefork_server):
        prefork_server.remove_worker = MagicMock()
        with patch("os.kill"):
            prefork_server.kill_worker(1234, signal.SIGTERM)
        prefork_server.remove_worker.assert_not_called()

    def test_esrch_cleans_up_stale_entry(self, prefork_server):
        prefork_server.remove_worker = MagicMock()
        with patch("os.kill", side_effect=OSError(errno.ESRCH, "no such process")):
            prefork_server.kill_worker(1234, signal.SIGTERM)
        prefork_server.remove_worker.assert_called_once_with(1234)


@pytest.fixture
def tserver(srv):
    s = threaded_server()
    s._process_handle = MagicMock()
    return s


@pytest.fixture
def no_db_cancel():
    with patch("odoo.service._threaded.db.cancel_queries_of", return_value=1) as c:
        yield c


class TestThreadedServerProcessLimit:
    @staticmethod
    @contextlib.contextmanager
    def _env(memory=0, config_override=None, threads=()):
        cfg = {
            "limit_memory_soft": 0,
            "limit_time_real": 60,
            "limit_time_real_cron": 0,
            "limit_time_real_job": -1,
            **(config_override or {}),
        }
        with (
            patch("odoo.service._limits.get_memory_rss", return_value=memory),
            server_settings.override(**cfg),
            patch("threading.enumerate", return_value=list(threads)),
        ):
            yield

    def test_memory_soft_exceeded_sets_limit_reached_time(self, tserver):
        import threading

        with self._env(
            memory=2000, config_override={"limit_memory_soft": 1000}, threads=[]
        ):
            tserver.check_limits()
        assert tserver.limit_reached_time is not None
        assert threading.current_thread() not in tserver.limits_reached_threads

    def test_transient_memory_spike_does_not_latch_reload(self, tserver):
        cfg = {"limit_memory_soft": 1000}

        def tick(mem):
            with (
                patch("odoo.service._limits.get_memory_rss", return_value=mem),
                server_settings.override(**cfg),
                patch("threading.enumerate", return_value=[]),
            ):
                tserver.check_limits()

        tick(2000)
        assert tserver.limit_reached_time is not None
        tick(100)
        assert tserver.limit_reached_time is None
        assert not tserver.limits_reached_threads

    def test_thread_real_time_exceeded_cancels_then_adds_thread(
        self, tserver, no_db_cancel
    ):
        """The first verdict cancels the thread's queries; only a thread still
        on the same work at the next pass asks for the reload."""
        mock_thread = MagicMock()
        mock_thread.daemon = False
        mock_thread.type = "http"
        mock_thread.name = "odoo.service.http.request.1"
        mock_thread.start_time = time.monotonic() - 9999
        mock_thread.is_alive.return_value = True

        with self._env(config_override={"limit_time_real": 60}, threads=[mock_thread]):
            tserver.check_limits()
            no_db_cancel.assert_called_once_with("odoo.service.http.request.1")
            assert mock_thread not in tserver.limits_reached_threads
            assert tserver.limit_reached_time is None
            tserver.check_limits()
        assert no_db_cancel.call_count == 1
        assert mock_thread in tserver.limits_reached_threads
        assert tserver.limit_reached_time is not None

    def test_a_cancelled_thread_that_moves_on_is_not_reloaded_for(
        self, tserver, no_db_cancel
    ):
        mock_thread = MagicMock()
        mock_thread.type = "cron"
        mock_thread.name = "odoo.service.cron.cron0"
        mock_thread.start_time = time.monotonic() - 9999
        mock_thread.is_alive.return_value = True
        cfg = {"limit_time_real": 3600, "limit_time_real_cron": 60}
        with self._env(config_override=cfg, threads=[mock_thread]):
            tserver.check_limits()
            mock_thread.start_time = time.monotonic()  # the next sweep
            tserver.check_limits()
        assert mock_thread not in tserver.limits_reached_threads
        assert not tserver._cancelled_overruns
        assert no_db_cancel.call_count == 1

    def test_a_failed_cancel_still_reloads_on_the_next_pass(self, tserver):
        mock_thread = MagicMock()
        mock_thread.type = "http"
        mock_thread.name = "odoo.service.http.request.2"
        mock_thread.start_time = time.monotonic() - 9999
        mock_thread.is_alive.return_value = True
        with (
            self._env(config_override={"limit_time_real": 60}, threads=[mock_thread]),
            patch(
                "odoo.service._threaded.db.cancel_queries_of",
                side_effect=RuntimeError("pool gone"),
            ),
        ):
            tserver.check_limits()
            tserver.check_limits()
        assert mock_thread in tserver.limits_reached_threads

    def test_cron_thread_uses_cron_time_limit(self, tserver, no_db_cancel):
        mock_thread = MagicMock()
        mock_thread.daemon = False
        mock_thread.type = "cron"
        mock_thread.start_time = time.monotonic() - 120
        mock_thread.is_alive.return_value = True

        with self._env(
            config_override={"limit_time_real": 3600, "limit_time_real_cron": 60},
            threads=[mock_thread],
        ):
            tserver.check_limits()
            tserver.check_limits()
        assert mock_thread in tserver.limits_reached_threads

    def test_zero_cron_limit_does_not_fall_back_to_the_http_limit(self, tserver):
        mock_thread = MagicMock()
        mock_thread.daemon = False
        mock_thread.type = "cron"
        mock_thread.start_time = time.monotonic() - 9999
        mock_thread.is_alive.return_value = True

        with self._env(
            config_override={"limit_time_real": 60, "limit_time_real_cron": 0},
            threads=[mock_thread],
        ):
            tserver.check_limits()
        assert mock_thread not in tserver.limits_reached_threads, (
            "--limit-time-real-cron=0 is documented as 'no limit' and PreforkServer "
            "honours it; the threaded watchdog must not kill the thread at "
            "limit_time_real instead"
        )

    def test_dead_thread_pruned_from_limits_reached(self, tserver):
        dead = MagicMock()
        dead.is_alive.return_value = False
        tserver.limits_reached_threads.add(dead)

        with self._env(threads=[]):
            tserver.check_limits()
        assert dead not in tserver.limits_reached_threads

    def test_limit_reached_time_set_and_cleared(self, tserver, no_db_cancel):
        mock_thread = MagicMock()
        mock_thread.daemon = False
        mock_thread.type = "http"
        mock_thread.start_time = time.monotonic() - 9999
        mock_thread.is_alive.return_value = True

        with self._env(config_override={"limit_time_real": 60}, threads=[mock_thread]):
            tserver.check_limits()
            tserver.check_limits()
        assert tserver.limit_reached_time is not None

        tserver.limits_reached_threads.clear()
        mock_thread.start_time = None
        with self._env(config_override={"limit_time_real": 60}, threads=[mock_thread]):
            tserver.check_limits()
        assert tserver.limit_reached_time is None

    def test_websocket_thread_not_counted(self, tserver):
        mock_thread = MagicMock()
        mock_thread.daemon = False
        mock_thread.type = "websocket"
        mock_thread.start_time = time.monotonic() - 9999
        mock_thread.is_alive.return_value = True

        with self._env(config_override={"limit_time_real": 1}, threads=[mock_thread]):
            tserver.check_limits()
        assert mock_thread not in tserver.limits_reached_threads

    def test_single_monotonic_call_per_invocation(self, tserver):
        threads = []
        for _ in range(5):
            t = MagicMock()
            t.daemon = False
            t.type = "http"
            t.start_time = time.monotonic() - 9999
            t.is_alive.return_value = True
            threads.append(t)

        original_monotonic = time.monotonic

        with (
            self._env(config_override={"limit_time_real": 1}, threads=threads),
            patch("odoo.service._threaded.time") as mock_time,
        ):
            mock_time.monotonic.side_effect = original_monotonic
            tserver.check_limits()

        assert mock_time.monotonic.call_count <= 2


@pytest.fixture
def inherited_listener(request):
    family, addr = request.param
    sock = socket.socket(family, socket.SOCK_STREAM)
    sock.bind(addr)
    sock.listen(1)
    try:
        yield sock
    finally:
        sock.close()


def _adopt_inherited_fd(fd, *, via_env, interface):
    server = _prefork.PreforkServer(None)
    server.logger = MagicMock()
    server.interface, server.port, server.population = interface, 0, 2
    server.open_pipe = MagicMock(return_value=(0, 0))
    env = {"ODOO_HTTP_SOCKET_FD": str(fd)} if via_env else {}
    with (
        server_settings.override(
            http_enable=True, http_socket_activation=not via_env, gevent_port=0
        ),
        patch.object(signal, "signal"),
        patch.dict(os.environ, env, clear=False),
    ):
        if not via_env:
            os.environ.pop("ODOO_HTTP_SOCKET_FD", None)
        server.start()
    server.websocket_socket.close()
    return server.socket


V6 = pytest.param((socket.AF_INET6, ("::1", 0)), id="ipv6")
V4 = pytest.param((socket.AF_INET, ("127.0.0.1", 0)), id="ipv4")


class TestInheritedListenSocketKeepsItsFamily:
    @pytest.mark.parametrize("inherited_listener", [V6, V4], indirect=True)
    def test_reload_handoff_preserves_the_family(self, inherited_listener):
        expected = inherited_listener.getsockname()
        adopted = _adopt_inherited_fd(
            inherited_listener.fileno(),
            via_env=True,
            interface=expected[0],
        )
        try:
            assert adopted.family == inherited_listener.family
            assert adopted.getsockname() == expected
        finally:
            adopted.detach()

    @pytest.mark.parametrize("inherited_listener", [V6, V4], indirect=True)
    def test_socket_activation_preserves_the_family(self, inherited_listener):
        expected = inherited_listener.getsockname()
        saved_fd3 = os.dup(3)
        try:
            os.dup2(inherited_listener.fileno(), 3, inheritable=True)
            adopted = _adopt_inherited_fd(3, via_env=False, interface=expected[0])
            try:
                assert adopted.family == inherited_listener.family
                assert adopted.getsockname() == expected
            finally:
                adopted.detach()
        finally:
            os.dup2(saved_fd3, 3)
            os.close(saved_fd3)

    @pytest.mark.parametrize("inherited_listener", [V6], indirect=True)
    def test_the_adopted_socket_is_cloexec(self, inherited_listener):
        adopted = _adopt_inherited_fd(
            inherited_listener.fileno(), via_env=True, interface="::1"
        )
        try:
            flags = fcntl.fcntl(adopted.fileno(), fcntl.F_GETFD)
            assert flags & fcntl.FD_CLOEXEC
        finally:
            adopted.detach()


class TestOnStopFuncsModuleLevel:
    @pytest.fixture(autouse=True)
    def _restore(self, srv):
        original_module = list(_base_server._on_stop_hooks)
        yield
        _base_server._on_stop_hooks[:] = original_module

    def test_module_level_list_exists(self):
        assert hasattr(_base_server, "_on_stop_hooks")
        assert isinstance(_base_server._on_stop_hooks, list)

    def test_class_attr_intentionally_absent(self, srv):
        assert not hasattr(srv.CommonServer, "_on_stop_funcs")

    def test_on_stop_appends_to_module_list(self, srv):
        cb = MagicMock()
        srv.CommonServer.register_on_stop_hook(cb)
        assert cb in _base_server._on_stop_hooks

    def test_on_stop_is_idempotent(self, srv):
        cb = MagicMock()
        before = len(_base_server._on_stop_hooks)
        srv.CommonServer.register_on_stop_hook(cb)
        srv.CommonServer.register_on_stop_hook(cb)
        assert len(_base_server._on_stop_hooks) == before + 1

        instance = common_server()
        instance.stop()
        cb.assert_called_once()


class TestStopWorkersGracefullyDictRace:
    def test_pop_during_iteration_does_not_raise(self, prefork_server):
        prefork_server.workers = {1: MagicMock(), 2: MagicMock(), 3: MagicMock()}
        prefork_server.workers_http = {}
        prefork_server.workers_cron = {}
        prefork_server.long_polling_pid = None
        prefork_server.beat = 0.1
        prefork_server.pid = os.getpid()

        original_workers = prefork_server.workers

        def fake_kill(pid, sig):
            if pid == 2:
                original_workers.pop(2, None)

        prefork_server.kill_worker = fake_kill

        with (
            patch.object(
                prefork_server, "apply_pending_signals", side_effect=KeyboardInterrupt
            ),
            patch.object(prefork_server, "reap_exited_workers"),
            patch.object(prefork_server, "sleep"),
            patch.object(prefork_server, "kill_timed_out_workers"),
        ):
            prefork_server.stop_workers_gracefully()

        assert 2 not in prefork_server.workers


class TestMemoryLogStrings:
    @staticmethod
    def _only_message(logger_mock):
        calls = logger_mock.info.call_args_list + logger_mock.warning.call_args_list
        memory_calls = [c for c in calls if "soft-limit" in str(c.args[0])]
        assert len(memory_calls) == 1, f"expected one soft-limit log, got {calls!r}"
        return memory_calls[0].args[0]

    def test_worker_check_limits_reports_RSS(self, bare_worker):
        with worker_check_limits_env(
            memory_bytes=500, config_override={"limit_memory_soft": 100}
        ):
            bare_worker.check_limits()

        message = self._only_message(bare_worker.logger)
        assert "RSS" in message
        assert "irtual" not in message and "VMS" not in message

    def test_event_server_process_limits_reports_RSS(self, websocket_server):
        websocket_server.ppid = os.getppid()
        websocket_server._process_handle = MagicMock()
        cfg = {"limit_memory_soft_gevent": 100, "limit_memory_soft": 0}
        with (
            server_settings.override(**cfg),
            patch("odoo.service._limits.get_memory_rss", return_value=500),
            patch.object(_threaded.os, "kill"),
        ):
            websocket_server.check_limits()

        message = self._only_message(websocket_server.logger)
        assert "RSS" in message
        assert "irtual" not in message and "VMS" not in message

    def test_memory_info_returns_rss(self):
        proc = MagicMock()
        proc.memory_info.return_value = MagicMock(rss=111, vms=999)
        assert _limits.get_memory_rss(proc) == 111
        assert _limits.get_memory_rss(proc) != 999

    def test_reads_rss_off_a_real_psutil_process(self):
        # Unmocked on purpose: the helper binds to psutil's memory_info(),
        # and a rename that sweeps that call breaks every server flavour at
        # startup while every mocked test stays green (2176e0fd942 did).
        import psutil

        assert _limits.get_memory_rss(psutil.Process()) > 0


@pytest.fixture
def websocket_server(srv):
    obj = build_websocket_server(port=0)
    obj.httpd = None
    obj.pid = os.getpid()
    return obj


class TestWebsocketServerGracefulStop:
    @pytest.fixture(autouse=True)
    def _restore_callbacks(self, srv):
        original = list(_base_server._on_stop_hooks)
        yield
        _base_server._on_stop_hooks[:] = original

    @pytest.mark.parametrize("sig", [signal.SIGINT, signal.SIGTERM])
    def test_quit_handler_raises_keyboard_interrupt(self, websocket_server, sig):
        with pytest.raises(KeyboardInterrupt):
            websocket_server._quit_signal_handler(sig, None)

    @pytest.mark.skipif(os.name != "posix", reason="POSIX signal handlers")
    def test_start_installs_sigint_and_sigterm(self, websocket_server):
        with (
            patch.object(signal, "signal") as mock_signal,
            patch.object(_threaded, "ThreadedHTTPServer", return_value=MagicMock()),
            patch.object(threading, "Thread"),
        ):
            websocket_server.start()

        wired = {
            c.args[0]: c.args[1]
            for c in mock_signal.call_args_list
            if c.args[0] in (signal.SIGINT, signal.SIGTERM)
        }
        assert signal.SIGINT in wired, "SIGINT handler not installed"
        assert signal.SIGTERM in wired, "SIGTERM handler not installed"
        assert wired[signal.SIGINT] == websocket_server._quit_signal_handler
        assert wired[signal.SIGTERM] == websocket_server._quit_signal_handler

    @pytest.mark.skipif(os.name != "posix", reason="POSIX signal handlers")
    def test_the_watchdog_starts_only_once_the_server_is_serving(
        self, websocket_server
    ):
        """Measured 2026-09-15 under a memory limit the process was already
        over at boot: the watchdog's SIGTERM landed while `start()` was still
        creating the HTTP server, the KeyboardInterrupt escaped `run()` as an
        uncaught traceback, and the master counted the evented child as
        crashed by signal and backed off -- HTTP workers included."""
        order = []
        httpd = MagicMock()
        httpd.serve_forever.side_effect = lambda: order.append("serve")

        class _Thread:
            def __init__(self, **kwargs):
                self.target = kwargs["target"]

            def start(self):
                order.append(("watchdog", self.target.__name__))

        with (
            patch.object(signal, "signal"),
            patch.object(
                _threaded,
                "ThreadedHTTPServer",
                side_effect=lambda *a, **k: (order.append("httpd"), httpd)[1],
            ),
            patch.object(threading, "Thread", _Thread),
        ):
            websocket_server.start()
        assert order == ["httpd", ("watchdog", "run_watchdog"), "serve"]
        assert websocket_server.httpd is httpd

    def test_stop_tolerates_unstarted_httpd_and_runs_hooks(self, srv, websocket_server):
        sentinel = MagicMock()
        sentinel.__name__ = "sentinel"
        srv.CommonServer.register_on_stop_hook(sentinel)
        websocket_server.httpd = None
        websocket_server.stop()
        sentinel.assert_called_once()

    def test_run_runs_stop_even_when_start_raises(self, srv, websocket_server):
        sentinel = MagicMock()
        sentinel.__name__ = "sentinel"
        srv.CommonServer.register_on_stop_hook(sentinel)
        websocket_server.httpd = MagicMock()
        with patch.object(websocket_server, "start", side_effect=RuntimeError("boom")):
            with pytest.raises(RuntimeError, match="boom"):
                websocket_server.run()
        sentinel.assert_called_once()
        websocket_server.httpd.server_close.assert_called_once()
        websocket_server.httpd.shutdown.assert_not_called()

    def test_stop_completes_if_serve_forever_never_started(self, websocket_server):
        websocket_server.httpd = _threaded.ThreadedHTTPServer(
            "127.0.0.1", 0, lambda e, s: []
        )
        try:
            done = threading.Event()
            threading.Thread(
                target=lambda: (websocket_server.stop(), done.set()), daemon=True
            ).start()
            assert done.wait(5), (
                "stop() hung on a never-started serve loop (shutdown deadlock)"
            )
        finally:
            websocket_server.httpd.server_close()

    def test_stop_after_completed_serve_loop_double_close_ok(self, websocket_server):
        websocket_server.httpd = _threaded.ThreadedHTTPServer(
            "127.0.0.1", 0, lambda e, s: []
        )
        t = threading.Thread(target=websocket_server.httpd.serve_forever, daemon=True)
        t.start()
        websocket_server.httpd.shutdown()
        t.join(5)
        assert not t.is_alive()
        websocket_server.stop()


class TestProcessLimitRealTimeLog:
    def test_overrun_logs_fractional_seconds(self, srv):
        ts = threaded_server()
        ts.logger = MagicMock()
        ts.limits_reached_threads = set()
        ts._overrun_start_times = {}
        ts.limit_reached_time = None
        ts._process_handle = MagicMock()

        fake_thread = MagicMock()
        fake_thread.type = "http"
        fake_thread.start_time = time.monotonic() - 12.7
        fake_thread.is_alive.return_value = True

        cfg = {
            "limit_memory_soft": 0,
            "limit_time_real": 1,
            "limit_time_real_cron": 0,
        }
        with (
            server_settings.override(**cfg),
            patch.object(_limits, "get_memory_rss", return_value=0),
            patch.object(threading, "enumerate", return_value=[fake_thread]),
        ):
            ts.check_limits()

        ts.logger.warning.assert_called_once()
        fmt = ts.logger.warning.call_args.args[0]
        assert "%.1f" in fmt, "elapsed time must use %.1f (not %d, which floors)"
        assert "virtual" not in fmt, "wall time must not be mislabeled 'virtual'"
        rendered = fmt % ts.logger.warning.call_args.args[1:]
        assert "12.7" in rendered, f"fractional seconds must survive; got {rendered!r}"


class _StopHarness(BaseException):
    pass


@pytest.fixture
def listen_server(srv, monkeypatch):
    monkeypatch.setattr(threading.current_thread(), "start_time", None, raising=False)
    s = threaded_server()
    s.logger = MagicMock()
    return s


def _drive_listen_thread(listen_server, process_jobs, *, sleeps_before_stop=2):
    calls = {"sleep": 0}

    def fake_sleep(_seconds):
        calls["sleep"] += 1
        if calls["sleep"] >= sleeps_before_stop:
            raise _StopHarness

    cfg = {"limit_time_worker_cron": 0, "db_name": ["db1"]}
    with (
        patch("odoo.service._cron.db.db_connect"),
        patch("odoo.service._cron.arm_cron_listen", return_value=True),
        patch("odoo.service._cron.drain_cron_notifies", return_value=set()),
        patch("odoo.service._cron.get_cron_databases", return_value=["db1"]) as db_list,
        patch("odoo.service._cron.selectors.DefaultSelector"),
        server_settings.override(**cfg),
        patch("odoo.service._threaded.time.sleep", fake_sleep),
    ):
        with pytest.raises(_StopHarness):
            listen_server._run_listener_thread(
                0,
                channel="cron_trigger",
                process_jobs=process_jobs,
                label="cron",
                max_age=0,
            )
        calls["full_scans"] = db_list.call_count
    return calls


class TestListenThreadUsesAMonotonicClock:
    def test_a_wall_clock_jump_does_not_retrigger_the_full_scan(
        self, listen_server, monkeypatch
    ):
        wall = iter(range(0, 10**9, 10**6))
        monkeypatch.setattr(time, "time", lambda: float(next(wall)))

        calls = _drive_listen_thread(
            listen_server, process_jobs=MagicMock(), sleeps_before_stop=4
        )

        assert calls["full_scans"] == 1, (
            f"the full scan ran {calls['full_scans']} times across "
            f"{calls['sleep']} polls; a wall-clock jump must not reschedule it "
            f"(CRON_POLL_INTERVAL_S is {_limits.CRON_POLL_INTERVAL_S}s and monotonic "
            f"advanced by milliseconds)"
        )


class TestListenThreadStartTimeBookkeeping:
    def test_start_time_cleared_after_successful_unit_of_work(self, listen_server):
        _drive_listen_thread(listen_server, MagicMock())
        assert getattr(threading.current_thread(), "start_time", None) is None

    def test_start_time_cleared_after_exception_in_unit_of_work(self, listen_server):
        def boom(_db):
            raise ValueError("cron job blew up")

        _drive_listen_thread(listen_server, boom)
        assert getattr(threading.current_thread(), "start_time", None) is None

    def test_start_time_cleared_when_base_exception_unwinds_the_thread(
        self, listen_server
    ):
        class Fatal(BaseException):
            pass

        def boom(_db):
            raise Fatal("not an Exception subclass")

        with pytest.raises(Fatal):
            _drive_listen_thread(listen_server, boom, sleeps_before_stop=3)
        assert getattr(threading.current_thread(), "start_time", None) is None


class TestListenThreadDoesNotSwallowUnwinds:
    @pytest.mark.parametrize("exc", [KeyboardInterrupt, SystemExit])
    def test_control_flow_exception_is_not_retried(self, listen_server, exc):
        def boom(_db):
            raise exc

        with pytest.raises(exc):
            _drive_listen_thread(listen_server, boom, sleeps_before_stop=3)

    def test_ordinary_exception_is_still_retried(self, listen_server):
        def boom(_db):
            raise ValueError("cron pass blew up")

        _drive_listen_thread(listen_server, boom, sleeps_before_stop=3)


class TestPreforkStopTerminatesSurvivors:
    @pytest.fixture
    def phoenix_server(self, prefork_server):
        prefork_server.socket = None
        prefork_server.workers = {4242: MagicMock()}
        return prefork_server

    def test_survivor_is_sigtermed_after_cut_short_reload_drain(
        self, srv, phoenix_server, monkeypatch
    ):
        monkeypatch.setattr(_process_state, "server_phoenix", True)
        monkeypatch.setattr(
            srv.PreforkServer, "stop_workers_gracefully", lambda self: None
        )
        killed = []
        monkeypatch.setattr(
            srv.PreforkServer,
            "kill_worker",
            lambda self, pid, sig: killed.append((pid, sig)),
        )

        phoenix_server.stop()

        assert killed == [(4242, signal.SIGTERM)], (
            "worker 4242 was left running after a cut-short reload drain"
        )

    def test_fully_drained_reload_kills_nothing(self, srv, phoenix_server, monkeypatch):
        monkeypatch.setattr(_process_state, "server_phoenix", True)

        def drained(self):
            self.workers.clear()

        monkeypatch.setattr(srv.PreforkServer, "stop_workers_gracefully", drained)
        killed = []
        monkeypatch.setattr(
            srv.PreforkServer,
            "kill_worker",
            lambda self, pid, sig: killed.append((pid, sig)),
        )

        phoenix_server.stop()

        assert killed == []


class TestPreforkStopRunsOnStopHooks:
    @pytest.fixture
    def hooked(self, srv, monkeypatch):
        from odoo.service import _base_server

        calls = []
        monkeypatch.setattr(_base_server, "_on_stop_hooks", [lambda: calls.append(1)])
        return calls

    def _phoenix(self, prefork_server):
        prefork_server.socket = None
        prefork_server.workers = {}
        return prefork_server

    def test_successful_reload_runs_the_hooks(
        self, srv, prefork_server, hooked, monkeypatch
    ):
        monkeypatch.setattr(_process_state, "server_phoenix", True)
        monkeypatch.setattr(
            srv.PreforkServer, "stop_workers_gracefully", lambda self: None
        )

        self._phoenix(prefork_server).stop()

        assert hooked == [1], (
            "on-stop hooks did not run on a prefork reload; the outgoing master "
            "exits leaving its subprocesses and bus connection behind"
        )

    def test_failed_reload_also_runs_the_hooks(
        self, srv, prefork_server, hooked, monkeypatch
    ):
        monkeypatch.setattr(_process_state, "server_phoenix", True)

        self._phoenix(prefork_server).stop()

        assert hooked == [1]

    def test_plain_shutdown_still_runs_them_once(
        self, srv, prefork_server, hooked, monkeypatch
    ):
        monkeypatch.setattr(_process_state, "server_phoenix", False)
        monkeypatch.setattr(
            srv.PreforkServer, "stop_workers_gracefully", lambda self: None
        )
        prefork_server.socket = None

        prefork_server.stop()

        assert hooked == [1]


class TestListenThreadFirstPassIsImmediate:
    def _select_timeouts(self, listen_server, iterations):
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

        cfg = {"limit_time_worker_cron": 0, "db_name": ["db1"]}
        with (
            patch("odoo.service._cron.db.db_connect"),
            patch("odoo.service._cron.arm_cron_listen", return_value=True),
            patch("odoo.service._cron.drain_cron_notifies", return_value=set()),
            patch("odoo.service._cron.get_cron_databases", return_value=["db1"]),
            patch("odoo.service._cron.selectors.DefaultSelector", _Sel),
            server_settings.override(**cfg),
            patch("odoo.service._threaded.time.sleep", lambda _s: None),
        ):
            with pytest.raises(_StopHarness):
                listen_server._run_listener_thread(
                    0,
                    channel="cron_trigger",
                    process_jobs=MagicMock(),
                    label="cron",
                    max_age=0,
                )
        return seen

    def test_first_select_does_not_block(self, listen_server):
        assert self._select_timeouts(listen_server, 1)[0] == 0

    def test_subsequent_selects_use_the_steady_state_interval(self, listen_server):
        timeouts = self._select_timeouts(listen_server, 3)
        assert timeouts[0] == 0, "first pass must poll immediately"
        assert all(t == _threaded.CRON_POLL_INTERVAL_S + 0 for t in timeouts[1:]), (
            f"steady state must return to CRON_POLL_INTERVAL_S, got {timeouts}"
        )

    def test_first_pass_actually_processes_databases(self, listen_server):
        process_jobs = MagicMock()
        cfg = {"limit_time_worker_cron": 0, "db_name": ["db1"]}
        calls = {"n": 0}

        class _Sel:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def register(self, *a, **kw):
                pass

            def select(self, timeout=None):
                calls["n"] += 1
                if calls["n"] > 1:
                    raise _StopHarness
                return []

        with (
            patch("odoo.service._cron.db.db_connect"),
            patch("odoo.service._cron.arm_cron_listen", return_value=True),
            patch("odoo.service._cron.drain_cron_notifies", return_value=set()),
            patch("odoo.service._cron.get_cron_databases", return_value=["db1"]),
            patch("odoo.service._cron.selectors.DefaultSelector", _Sel),
            server_settings.override(**cfg),
            patch("odoo.service._threaded.time.sleep", lambda _s: None),
        ):
            with pytest.raises(_StopHarness):
                listen_server._run_listener_thread(
                    0,
                    channel="cron_trigger",
                    process_jobs=process_jobs,
                    label="cron",
                    max_age=0,
                )
        process_jobs.assert_called_once_with("db1")


class TestPreforkForcefulStopStopsLongPolling:
    def test_forceful_stop_stops_the_evented_child(
        self, srv, prefork_server, monkeypatch
    ):
        monkeypatch.setattr(_process_state, "server_phoenix", False)
        prefork_server.socket = None
        prefork_server.workers = {}
        called = []
        monkeypatch.setattr(
            srv.PreforkServer, "_stop_long_polling", lambda self: called.append(True)
        )

        prefork_server.stop(graceful=False)

        assert called == [True], "evented subprocess left running after forceful stop"

    def test_graceful_stop_still_stops_it_exactly_once(
        self, srv, prefork_server, monkeypatch
    ):
        monkeypatch.setattr(_process_state, "server_phoenix", False)
        prefork_server.socket = None
        prefork_server.workers = {}
        called = []
        monkeypatch.setattr(
            srv.PreforkServer, "_stop_long_polling", lambda self: called.append(True)
        )
        monkeypatch.setattr(
            srv.PreforkServer,
            "stop_workers_gracefully",
            lambda self: self._stop_long_polling(),
        )
        monkeypatch.setattr(srv.CommonServer, "stop", lambda self: None)

        prefork_server.stop(graceful=True)

        assert called == [True]


class TestWorkerCpuLimitHandoff:
    def test_grace_is_bounded_and_short(self, srv):
        assert 0 < srv.Worker._CPU_LIMIT_JOIN_GRACE_S <= 5.0

    def test_cpu_limit_clears_alive_and_joins_before_stop(self, srv, multi):
        w = srv.Worker(multi)
        w.pid = os.getpid()
        w.logger = MagicMock()
        order = []

        real_stop = srv.Worker.stop

        def traced_stop(self):
            order.append(("stop", self.alive))
            return real_stop(self)

        joined = []

        class _T:
            name = "workthread"

            def start(self):
                pass

            def join(self, timeout=None):
                joined.append(timeout)
                if len(joined) == 1:
                    raise srv.CpuTimeLimitExceeded("cpu")
                order.append(("join", timeout))

            def is_alive(self):
                return not joined

        with (
            patch.object(srv.Worker, "start", lambda self: None),
            patch.object(srv.Worker, "stop", traced_stop),
            patch("odoo.service._worker.threading.Thread", lambda **kw: _T()),
            server_settings.override(limit_time_cpu=1),
        ):
            w.run()

        assert ("join", srv.Worker._CPU_LIMIT_JOIN_GRACE_S) in order, (
            "work thread was not given a chance to wind down"
        )
        assert order.index(("join", srv.Worker._CPU_LIMIT_JOIN_GRACE_S)) < [
            o[0] for o in order
        ].index("stop"), "joined after stop() closed resources"
        assert ("stop", False) in order, "self.alive was not cleared before stop()"

    def test_a_second_sigxcpu_during_the_grace_join_is_not_a_crash(self, srv, multi):
        """Linux re-sends SIGXCPU every second past the soft limit.  Measured
        2026-09-15: the second one escaped `run()` as an uncaught error, the
        worker exited 1, and the master held the respawn as a crash."""
        w = srv.Worker(multi)
        w.pid = os.getpid()
        w.logger = MagicMock()
        installed = []

        class _T:
            def start(self):
                pass

            def join(self, timeout=None):
                if timeout is None:
                    raise srv.CpuTimeLimitExceeded("cpu")
                # A SIGXCPU landing during the grace join raises again unless
                # the handler was disarmed first.
                assert signal.getsignal(signal.SIGXCPU) is signal.SIG_IGN

            def is_alive(self):
                return False

        previous = signal.getsignal(signal.SIGXCPU)
        try:
            with (
                patch.object(srv.Worker, "start", lambda self: None),
                patch.object(srv.Worker, "stop", lambda self: installed.append("stop")),
                patch("odoo.service._worker.threading.Thread", lambda **kw: _T()),
                server_settings.override(limit_time_cpu=1),
            ):
                assert w.run() is None
        finally:
            signal.signal(signal.SIGXCPU, previous)
        assert installed == ["stop"]


class TestTheStartupLineNamesTheSocketItActuallyGot:
    """Three ways to get a listening socket, three different things to say.

    The message used to be picked before the branch that decides, so a master
    that inherited a socket across a SIGHUP reload announced the fresh-bind
    wording. On a live reload that is the only line an operator sees, and it
    claimed a rebind of a port that never closed.
    """

    @staticmethod
    def _start(*, env, socket_activation):
        server = _prefork.PreforkServer(None)
        server.logger = MagicMock()
        server.interface, server.port, server.population = "127.0.0.1", 0, 1
        server.open_pipe = MagicMock(return_value=(0, 0))
        server._census = MagicMock()
        with (
            server_settings.override(
                http_enable=True,
                http_socket_activation=socket_activation,
                gevent_port=0,
            ),
            patch.object(signal, "signal"),
            patch.object(_prefork.socket, "socket") as mock_sock,
            patch.object(_prefork, "adopt_activated_socket", return_value=MagicMock()),
            patch.object(
                _prefork,
                "take_inherited_socket",
                return_value=MagicMock() if env else None,
            ),
        ):
            server.start()
        said = " ".join(str(c.args[0]) for c in server.logger.info.call_args_list)
        return said, mock_sock

    def test_a_fresh_bind_says_so(self):
        said, _ = self._start(env={}, socket_activation=False)
        assert "running on %s:%s" in said
        assert "inherited" not in said

    def test_socket_activation_says_so(self):
        said, _ = self._start(env={}, socket_activation=True)
        assert "socket activation" in said

    def test_an_inherited_socket_says_so_and_not_the_bind_wording(self):
        said, _ = self._start(env={"ODOO_HTTP_SOCKET_FD": "7"}, socket_activation=False)
        assert "inherited" in said, (
            "a reload handoff still announces itself as a fresh bind"
        )
        assert "running on %s:%s" not in said


class TestAWatchdogKillOfAWorkerThatNeverGotReadyIsACrash:
    """`crashed_by_signal` is written for SIGKILL and was unreachable.

    Refined 2026-09-15: the kill counts only when the worker never reported
    ready -- a hang at boot.  A ready worker the watchdog kills over one long
    request is a policy the master applied, and `TestPreforkRespawnBackoff`
    pins that it does not damp the respawn.

    `kill_timed_out_workers` SIGKILLs a worker that stopped pinging, and
    `kill_worker` pops it so the watchdog cannot kill the same pid twice. But
    the exit is only *accounted* for later, when `reap_exited_workers` reaps it, and
    `_record_worker_exit` looked the worker up in `self.workers` to learn how
    long it lived — so after the pop it returned immediately, taking the whole
    crash branch with it.

    That branch excludes SIGTERM (the graceful stop) and nothing else, and the
    watchdog is the only sender of SIGKILL, so the case it exists for was the
    one case it could never see: a worker that hangs on every request was
    respawned at full rate forever, with no "died after Xs" line and no
    back-off.
    """

    @staticmethod
    def _young_worker(server, pid):
        worker = MagicMock()
        worker.__class__.__name__ = "WorkerHTTP"
        worker.spawn_time = time.monotonic() - 1.0
        worker.watchdog_timeout = 1
        worker.watchdog_time = time.monotonic() - 10
        worker.ready = False  # hung before its work thread ever started
        server.workers[pid] = worker
        return worker

    def test_the_watchdog_kill_arms_the_backoff(self, prefork_server):
        self._young_worker(prefork_server, 4242)
        with patch.object(_prefork.os, "kill"):
            prefork_server.kill_timed_out_workers()
        assert 4242 not in prefork_server.workers, "the pop still has to happen"
        prefork_server._record_worker_exit(4242, signal.SIGKILL)
        assert prefork_server._get_respawn_hold("WorkerHTTP").fast_deaths == 1
        assert prefork_server._get_respawn_hold("WorkerHTTP").not_before > 0, (
            "a worker the watchdog killed young must damp the respawn, which "
            "is the loop the back-off exists for"
        )

    def test_a_worker_that_lived_long_enough_resets_it(self, prefork_server):
        worker = self._young_worker(prefork_server, 4243)
        worker.spawn_time = time.monotonic() - 600
        prefork_server._get_respawn_hold("WorkerHTTP").fast_deaths = 3
        with patch.object(_prefork.os, "kill"):
            prefork_server.kill_timed_out_workers()
        prefork_server._record_worker_exit(4243, signal.SIGKILL)
        assert prefork_server._get_respawn_hold("WorkerHTTP").fast_deaths == 0

    def test_the_record_does_not_outlive_the_reap(self, prefork_server):
        self._young_worker(prefork_server, 4244)
        with patch.object(_prefork.os, "kill"):
            prefork_server.kill_timed_out_workers()
        assert prefork_server._killed_workers
        prefork_server._record_worker_exit(4244, signal.SIGKILL)
        assert not prefork_server._killed_workers, "kept a worker after its reap"


class TestTheMasterNamesWhatATimedOutWorkerWasDoing:
    def test_a_titled_worker_is_read_from_proc(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            _prefork.Path,
            "read_bytes",
            lambda self: b"odoo: WorkerHTTP 4242 GET /web/report/pdf\x00",
        )
        assert (
            _prefork._read_process_title(4242) == "WorkerHTTP 4242 GET /web/report/pdf"
        )

    def test_a_plain_argv_says_nothing(self, monkeypatch):
        monkeypatch.setattr(
            _prefork.Path,
            "read_bytes",
            lambda self: b"python\x00odoo-bin\x00-c\x00x.conf",
        )
        assert _prefork._read_process_title(4242) == ""

    def test_a_vanished_process_says_nothing(self):
        assert _prefork._read_process_title(2**22 + 12345) == ""

    def test_the_timeout_line_carries_it(self, prefork_server, monkeypatch):
        worker = MagicMock()
        worker.__class__.__name__ = "WorkerHTTP"
        worker.watchdog_timeout = 1
        worker.watchdog_time = time.monotonic() - 10
        prefork_server.workers[4242] = worker
        prefork_server.logger = MagicMock()
        monkeypatch.setattr(
            _prefork, "_read_process_title", lambda pid: "WorkerHTTP 4242 POST /x"
        )
        with patch.object(_prefork.os, "kill"):
            prefork_server.kill_timed_out_workers()
        said = str(prefork_server.logger.error.call_args)
        assert "while WorkerHTTP 4242 POST /x" in said
