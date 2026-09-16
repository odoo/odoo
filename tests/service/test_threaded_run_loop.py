import contextlib
import socket
import threading
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import psycopg
import pytest

from odoo.db import PoolError
from odoo.service import _cron, _limits, _threaded
from odoo.service import settings as server_settings

from .conftest import threaded_server


class _Stop(SystemExit):
    pass


@pytest.fixture
def server():
    srv = threaded_server()
    srv.logger = MagicMock()
    srv.quit_signals_received = 0
    srv.limit_reached_time = None
    srv.limits_reached_threads = set()
    srv._overrun_start_times = {}
    srv._stop_after_init = False
    return srv


@pytest.fixture
def listen(server):
    def _run(outcomes, *, max_age=0.001):
        backoffs = []
        connect = MagicMock(side_effect=[*outcomes, _Stop()])
        with (
            patch.object(_cron.db, "db_connect", connect),
            patch.object(
                _cron,
                "backoff",
                SimpleNamespace(
                    get_bound=lambda attempt, **kw: backoffs.append(attempt) or 0
                ),
            ),
            server_settings.override(limit_time_worker_cron=max_age),
            patch.object(_cron, "arm_cron_listen"),
            patch.object(_cron, "drain_cron_notifies", return_value=set()),
            patch.object(_cron, "get_cron_databases", return_value=[]),
            patch.object(_cron, "CRON_NOTIFY_JITTER_MAX_S", 0),
            patch.object(_threaded, "CRON_POLL_INTERVAL_S", 0),
            pytest.raises(SystemExit),
        ):
            _threaded.ThreadedServer._run_listener_thread(
                server,
                0,
                channel="ch",
                process_jobs=MagicMock(),
                label="cron",
                max_age=max_age,
            )
        return backoffs, connect, server.logger.getChild.return_value

    return _run


@pytest.fixture
def healthy():
    left, right = socket.socketpair()
    conn = MagicMock()
    conn.cursor.return_value.connection = left
    try:
        yield conn
    finally:
        left.close()
        right.close()


class TestCronReconnectBackoff:
    def test_repeated_outages_escalate_the_wait(self, listen):
        backoffs, _, log = listen([psycopg.OperationalError("down")] * 4)
        assert backoffs == [1, 2, 3, 4], (
            "each failed reconnect must raise the attempt count handed to "
            "backoff.bound; a flat count is a hot loop against a database "
            "that is down"
        )
        assert log.warning.call_count == 4
        assert not log.critical.called, (
            "a database being down is expected operations, not a bug in the "
            "server; CRITICAL here is what trains operators to ignore it"
        )

    def test_a_pool_error_backs_off_the_same_way(self, listen):
        backoffs, _, log = listen([PoolError("no connection budget")] * 2)
        assert backoffs == [1, 2]
        assert log.warning.call_count == 2 and not log.critical.called, (
            "PoolError is the local equivalent of an outage. Both arms back "
            "off, so the log level is the only thing that separates them — and "
            "falling through to the catch-all reports exhaustion of our own "
            "connection budget as an uncaught server fault"
        )

    def test_an_unexpected_error_also_backs_off_rather_than_spinning(self, listen):
        backoffs, _, log = listen([ValueError("something else")] * 3)
        assert backoffs == [1, 2, 3], (
            "the catch-all exists so an unforeseen fault cannot turn the cron "
            "listener into a busy loop"
        )
        assert log.critical.call_count == 3, (
            "and an unforeseen fault IS reported as one, unlike an outage"
        )

    def test_a_successful_pass_resets_the_escalation(self, listen, healthy):
        backoffs, _, _log = listen(
            [
                psycopg.OperationalError("down"),
                psycopg.OperationalError("down"),
                healthy,
                psycopg.OperationalError("down again"),
            ]
        )
        assert backoffs == [1, 2, 1], (
            f"the wait did not reset after the connection came back: {backoffs}. "
            f"A database that flaps every few minutes would keep escalating "
            f"until it was being retried once an hour"
        )

    def test_system_exit_is_re_raised_and_not_retried(self, listen):
        backoffs, connect, _ = listen([])
        assert backoffs == [], "SystemExit must not be treated as an outage"
        assert connect.call_count == 1, "and must not be retried"


@pytest.fixture
def run_server(server):
    def _run(*, stop, preload_rc=0, start=None, loop=None):
        calls = []
        server.start = MagicMock(
            side_effect=start or (lambda **kw: calls.append(("start", kw)))
        )
        server.stop = MagicMock(side_effect=lambda: calls.append(("stop", {})))
        server.spawn_cron_threads = MagicMock(
            side_effect=lambda: calls.append(("cron", {}))
        )
        server.spawn_job_threads = MagicMock(
            side_effect=lambda: calls.append(("job", {}))
        )
        server.check_limits = MagicMock(
            side_effect=loop or (lambda: setattr(server, "quit_signals_received", 1))
        )
        server.reload = MagicMock(side_effect=lambda: calls.append(("reload", {})))
        with (
            patch.object(_threaded, "preload_registries", return_value=preload_rc),
            server_settings.override(test_enable=False),
            patch.object(_threaded, "LIMIT_MONITOR_INTERVAL_S", 0),
        ):
            rc = _threaded.ThreadedServer.run(server, ["db"], stop=stop)
        return rc, [name for name, _ in calls]

    return _run


class TestRunStopAfterInit:
    def test_it_returns_the_preload_code(self, run_server):
        rc, _ = run_server(stop=True, preload_rc=3)
        assert rc == 3, (
            "--stop-after-init is how a test run reports failure; swallowing "
            "the code makes a red suite exit 0"
        )

    def test_it_does_not_start_serving(self, run_server):
        _, calls = run_server(stop=True)
        assert "cron" not in calls and "job" not in calls, calls

    def test_it_still_stops(self, run_server):
        _, calls = run_server(stop=True)
        assert calls[-1] == "stop"


class TestRunServing:
    def test_failed_preload_stops_without_starting_background_work(self, run_server):
        rc, calls = run_server(stop=False, preload_rc=3)
        assert rc == 3
        assert calls == ["start", "stop"]

    def test_it_spawns_cron_and_job_workers_before_the_loop(self, run_server):
        _, calls = run_server(stop=False)
        assert calls[:3] == ["start", "cron", "job"], calls

    def test_the_loop_ends_on_a_quit_signal(self, run_server):
        _, calls = run_server(stop=False)
        assert calls[-1] == "stop"

    def test_a_keyboard_interrupt_is_a_clean_exit(self, run_server):
        rc, calls = run_server(
            stop=False, loop=MagicMock(side_effect=KeyboardInterrupt)
        )
        assert rc is None
        assert calls[-1] == "stop", "Ctrl-C must still run the shutdown path"

    def test_stop_runs_even_when_start_raises(self, run_server):
        with pytest.raises(RuntimeError, match="port in use"):
            run_server(
                stop=False, start=MagicMock(side_effect=RuntimeError("port in use"))
            )


class TestRunLimitReached:
    def _drive(self, server, others, *, aged=False):
        now = time.monotonic()
        server.limit_reached_time = (now - 3600) if aged else now
        server._has_other_http_requests = MagicMock(return_value=others)
        calls = []
        server.start = MagicMock()
        server.stop = MagicMock()
        server.spawn_cron_threads = MagicMock()
        server.spawn_job_threads = MagicMock()
        passes = iter(range(1))
        server.check_limits = MagicMock(
            side_effect=lambda: (
                next(passes, None) is None
                and setattr(server, "quit_signals_received", 1)
            )
        )
        server.reload = MagicMock(
            side_effect=lambda: (
                calls.append("reload"),
                setattr(server, "quit_signals_received", 1),
            )
        )
        with (
            patch.object(_threaded, "preload_registries", return_value=0),
            server_settings.override(test_enable=False),
            patch.object(_threaded, "dumpstacks") as dump,
            patch.object(_threaded, "LIMIT_MONITOR_INTERVAL_S", 0),
            patch.object(_threaded, "CRON_POLL_INTERVAL_S", 60),
        ):
            _threaded.ThreadedServer.run(server, ["db"], stop=False)
        return calls, dump

    def test_with_no_other_requests_it_reloads_at_once(self, server):
        calls, dump = self._drive(server, others=False)
        assert calls == ["reload"], (
            "the limit was reached and nothing else is in flight, so there is "
            "nothing to wait for — the reload is due now, not in CRON_POLL_INTERVAL_S"
        )
        dump.assert_called_once()

    def test_with_other_requests_in_flight_it_waits_instead(self, server):
        calls, dump = self._drive(server, others=True)
        assert calls == [], (
            "reloading while another request is being served drops it; the "
            "server waits out CRON_POLL_INTERVAL_S first"
        )
        dump.assert_not_called()

    def test_but_it_does_not_wait_forever_for_them(self, server):
        calls, _ = self._drive(server, others=True, aged=True)
        assert calls == ["reload"], (
            "past CRON_POLL_INTERVAL_S the reload happens regardless — otherwise one "
            "long-lived request pins a worker over its memory limit indefinitely"
        )

    def test_the_dump_names_only_the_offending_threads(self, server):
        thread = MagicMock(ident=4242)
        server.limits_reached_threads = {thread}
        _, dump = self._drive(server, others=False)
        assert dump.call_args.kwargs["thread_idents"] == {4242}, (
            "dumping every thread buries the one that exceeded the limit"
        )


@pytest.fixture
def report_run(server):
    def _make_report(*, successful, tests_run):
        report = MagicMock()
        report.wasSuccessful.return_value = successful
        report.testsRun = tests_run
        return report

    def _run(reports):
        registries = {name: _make_report(**kwargs) for name, kwargs in reports.items()}
        registry_cls = MagicMock()
        registry_cls.registries.__iter__.return_value = iter(list(registries))
        registry_cls.registries._lock = contextlib.nullcontext()
        logger = MagicMock()
        server.start = MagicMock()
        server.stop = MagicMock()
        with (
            patch.object(_threaded, "preload_registries", return_value=1),
            server_settings.override(test_enable=True),
            patch.object(_threaded, "Registry", registry_cls),
            patch.dict(
                "sys.modules",
                {
                    "odoo.tests.result": MagicMock(
                        _logger=logger, assertion_report=registries.__getitem__
                    )
                },
            ),
        ):
            rc = _threaded.ThreadedServer.run(server, ["db"], stop=True)
        levels = {
            name: level
            for level in ("error", "warning", "info")
            for call in getattr(logger, level).call_args_list
            for name in [call.args[2]]
        }
        return rc, levels

    return _run


class TestStopAfterInitReportLevel:
    def test_a_failing_suite_is_reported_at_error(self, report_run):
        _, levels = report_run({"db": {"successful": False, "tests_run": 12}})
        assert levels == {"db": "error"}

    def test_a_suite_that_ran_nothing_is_reported_at_warning(self, report_run):
        _, levels = report_run({"db": {"successful": True, "tests_run": 0}})
        assert levels == {"db": "warning"}, (
            "zero tests is not success — it is a tag selector that matched "
            "nothing, and it must not read the same as a passing run"
        )

    def test_a_passing_suite_is_reported_at_info(self, report_run):
        _, levels = report_run({"db": {"successful": True, "tests_run": 12}})
        assert levels == {"db": "info"}

    def test_each_database_is_judged_on_its_own(self, report_run):
        _, levels = report_run(
            {
                "good": {"successful": True, "tests_run": 5},
                "bad": {"successful": False, "tests_run": 5},
                "empty": {"successful": True, "tests_run": 0},
            }
        )
        assert levels == {"good": "info", "bad": "error", "empty": "warning"}, (
            "one failing database must not downgrade the others, nor they it"
        )

    def test_the_preload_code_is_still_what_is_returned(self, report_run):
        rc, _ = report_run({"db": {"successful": False, "tests_run": 1}})
        assert rc == 1, "the exit status comes from the preload, not the log level"


class TestHasOtherHttpRequests:
    def _ask(self, over_limit, threads):
        srv = threaded_server()
        srv.limits_reached_threads = set(over_limit)
        with patch.object(_threaded.threading, "enumerate", return_value=threads):
            return srv._has_other_http_requests()

    def _thread(self, kind):
        t = MagicMock()
        t.type = kind
        return t

    def test_an_unrelated_http_request_counts(self):
        other = self._thread("http")
        assert self._ask([], [other]) is True

    def test_the_over_limit_thread_does_not_count_itself(self):
        culprit = self._thread("http")
        assert self._ask([culprit], [culprit]) is False, (
            "the thread that blew the limit is the reason for the reload; "
            "counting it as work in flight makes the server wait for itself"
        )

    def test_cron_and_job_threads_are_not_http_requests(self):
        assert self._ask([], [self._thread("cron"), self._thread("job")]) is False

    def test_a_thread_with_no_type_is_not_an_http_request(self):
        bare = MagicMock(spec=[])
        assert self._ask([], [bare]) is False, (
            "getattr(t, 'type', None) — a plain library thread has no `type`, "
            "and treating it as a request holds off every reload"
        )


class TestAnOverLimitThreadIsNamedByItsWork:
    def _thread(self, kind, **attrs):
        # A real thread's attribute surface: an unset attribute is absent,
        # not a truthy mock, and the object is hashable for the ledgers.
        thread = threading.Thread(name=f"fake.{kind}")
        thread.type = kind
        for name, value in attrs.items():
            setattr(thread, name, value)
        return thread

    def test_an_http_thread_by_its_url_and_rpc_target(self):
        t = self._thread(
            "http",
            url="http://h/web/dataset/call_kw",
            rpc_model_method="res.partner.read",
        )
        assert _limits.describe_thread_work(t) == (
            "serving http://h/web/dataset/call_kw (res.partner.read)"
        )

    def test_the_request_id_rides_along_for_the_join(self):
        t = self._thread("http", url="http://h/web/login", request_id="req-42")
        assert _limits.describe_thread_work(t) == (
            "serving http://h/web/login, request req-42"
        )

    def test_an_http_thread_before_the_http_layer_stamped_it(self):
        t = self._thread("http", url="", rpc_model_method="")
        assert _limits.describe_thread_work(t) == ""

    def test_a_cron_thread_by_the_database_it_sweeps(self):
        assert _limits.describe_thread_work(self._thread("cron", dbname="prod")) == (
            "sweeping prod"
        )
        assert _limits.describe_thread_work(self._thread("job", dbname=None)) == ""

    def test_the_warning_carries_it(self, server, caplog):
        import logging
        import time

        thread = self._thread(
            "cron",
            dbname="prod",
            start_time=time.monotonic() - 500,
            is_alive=lambda: True,
        )
        server.logger = logging.getLogger("odoo.service.server.test")
        with (
            server_settings.override(limit_time_real=120, limit_time_real_cron=60),
            patch.object(_threaded.threading, "enumerate", return_value=[thread]),
            patch.object(_threaded.Registry, "_evict_idle_registries"),
            patch.object(server, "get_memory_over_soft_limit", return_value=None),
            caplog.at_level(logging.WARNING, logger=server.logger.name),
        ):
            server.check_limits()
        assert any("while sweeping prod" in r.getMessage() for r in caplog.records)
