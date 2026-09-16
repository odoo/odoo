import os
import re
from unittest.mock import MagicMock, patch

import pytest

from odoo.service import _process_state

from .conftest import common_server, prefork_server, threaded_server, websocket_server


@pytest.fixture(scope="module")
def mod():
    import odoo.service.metrics as m

    return m


@pytest.fixture
def pooled_db():
    from odoo import db

    assert hasattr(db, "get_pool_health"), (
        "odoo.db.get_pool_health is gone, but odoo/service/metrics.py still calls "
        "it while building the exposition — /metrics would raise"
    )
    return db


METRIC_NAME = re.compile(r"^[a-zA-Z_:][a-zA-Z0-9_:]*$")
SAMPLE = re.compile(
    r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(\{.*\})? (-?[0-9.eE+]+|NaN|\+Inf|-Inf)$"
)


def parse_exposition(text: str) -> tuple[dict[str, str], list[str]]:
    declared: dict[str, str] = {}
    sampled: set[str] = set()
    errors: list[str] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line:
            continue
        if line.startswith(("# HELP ", "# TYPE ")):
            name = line.split(" ", 3)[2]
            if not METRIC_NAME.match(name):
                errors.append(f"{lineno}: invalid metric name {name!r}")
            if line.startswith("# TYPE "):
                if name in declared:
                    errors.append(f"{lineno}: duplicate TYPE for {name}")
                if name in sampled:
                    errors.append(f"{lineno}: TYPE for {name} follows its samples")
                declared[name] = line.rsplit(" ", 1)[1]
            continue
        match = SAMPLE.match(line)
        if not match:
            errors.append(f"{lineno}: unparseable sample {line!r}")
            continue
        name, labels = match.group(1), match.group(2)
        sampled.add(name)
        base = name.removesuffix("_bucket").removesuffix("_sum").removesuffix("_count")
        if name not in declared and base not in declared:
            errors.append(f"{lineno}: sample {name} has no TYPE")
        errors.extend(
            f"{lineno}: invalid label name {key!r}"
            for key in re.findall(r'([^,{ ]+)="', labels or "")
            if not METRIC_NAME.match(key)
        )
    return declared, errors


class TestServiceMetrics:
    def test_no_server_yet_reports_flavor_none(self, mod):
        with patch.object(_process_state, "server", None):
            out = mod.get_service_metrics()
        assert out["flavor"] == "none"
        assert "registries" in out

    @staticmethod
    def _prefork(pid):
        """A real PreforkServer, since it is the one that answers now."""
        from odoo.service._census import WorkerCensus

        return prefork_server(
            workers={1: object(), 2: object()},
            workers_http={1: object(), 2: object()},
            workers_cron={3: object()},
            workers_job={},
            population=4,
            generation=17,
            _exits={"clean": 2, "crash": 1},
            long_polling_pid=999,
            pid=pid,
            _census=WorkerCensus(pid),
        )

    def test_prefork_reports_worker_counts(self, mod):
        server = self._prefork(os.getpid())

        with patch.object(_process_state, "server", server):
            out = mod.get_service_metrics()
        assert out["flavor"] == "prefork"
        assert out["workers"] == {"http": 2, "cron": 1, "job": 0}
        assert out["worker_population"] == 4
        assert out["worker_generation"] == 17
        assert out["worker_exits"] == {"clean": 2, "crash": 1}
        assert out["long_polling_alive"] is True

    def test_worker_exits_render_as_one_counter_family_by_outcome(self, mod):
        server = self._prefork(os.getpid())
        with patch.object(_process_state, "server", server):
            text = mod.render_prometheus_exposition()
        assert "# TYPE odoo_worker_exits_total counter" in text
        assert re.search(
            r'odoo_worker_exits_total\{[^}]*outcome="clean"[^}]*\} 2', text
        )
        assert re.search(
            r'odoo_worker_exits_total\{[^}]*outcome="crash"[^}]*\} 1', text
        )
        _, errors = parse_exposition(text)
        assert not errors, errors

    def test_forked_worker_omits_the_master_only_gauges(self, mod):
        server = self._prefork(os.getpid() + 1)

        with patch.object(_process_state, "server", server):
            out = mod.get_service_metrics()
        assert out["flavor"] == "prefork"
        for key in (
            "workers",
            "worker_population",
            "worker_generation",
            "worker_exits",
            "long_polling_alive",
        ):
            assert key not in out, f"{key} is master-only but a worker emitted it"

        with patch.object(_process_state, "server", server):
            text = mod.render_prometheus_exposition()
        for family in (
            "odoo_workers",
            "odoo_worker_population",
            "odoo_worker_generation",
            "odoo_worker_exits_total",
            "odoo_long_polling_alive",
        ):
            assert family not in text
        _, errors = parse_exposition(text)
        assert not errors, errors

    def test_threaded_reports_thread_counts_and_slot_ceiling(self, mod, monkeypatch):
        import threading

        server = threaded_server()
        server.httpd = MagicMock(max_http_threads=31)
        server.limits_reached_threads = set()
        server._overrun_start_times = {}

        monkeypatch.setattr(threading.current_thread(), "type", "http", raising=False)
        with patch.object(_process_state, "server", server):
            out = mod.get_service_metrics()

        assert out["flavor"] == "threaded"
        assert out["http_threads_max"] == 31
        assert out["threads"]["http"] >= 1
        assert out["overruns_cancelled"] == 0
        assert set(out["threads"]) == {"http", "cron", "job", "websocket"}, (
            "websocket threads are long-lived and hold a thread and a "
            "connection each; they are exempt from check_limits, not from "
            "being counted"
        )


class TestEveryServerAnswersForItself:
    """`get_service_metrics` asks the server; it no longer recognises one."""

    def test_threaded_counts_the_overruns_it_cancelled(self, mod):
        server = threaded_server()
        server.httpd = MagicMock(max_http_threads=31)
        server.limits_reached_threads = set()
        server._overrun_start_times = {}
        server._overruns_cancelled = 5
        with patch.object(_process_state, "server", server):
            text = mod.render_prometheus_exposition()
        assert "# TYPE odoo_overruns_cancelled_total counter" in text
        assert "odoo_overruns_cancelled_total{" in text
        _, errors = parse_exposition(text)
        assert not errors, errors

    def test_each_flavour_names_itself(self):
        from odoo.service._prefork import PreforkServer
        from odoo.service._threaded import ThreadedServer, WebsocketServer

        assert PreforkServer.flavor == "prefork"
        assert ThreadedServer.flavor == "threaded"
        assert WebsocketServer.flavor == "evented"

    def test_the_base_answers_unknown_rather_than_a_class_name(self):
        from odoo.service._base_server import CommonServer

        assert CommonServer.flavor == "unknown", (
            "a new flavour that forgets to set one should be visibly unnamed, "
            "not silently reported under its class name"
        )

    def test_a_flavour_that_declares_nothing_still_renders(self, mod):
        server = common_server()
        with patch.object(_process_state, "server", server):
            out = mod.get_service_metrics()
            text = mod.render_prometheus_exposition()
        assert out["flavor"] == "unknown"
        _, errors = parse_exposition(text)
        assert not errors, errors

    def test_the_evented_server_reports_its_pool_but_no_time_limits(self, mod):
        """It runs the same threaded HTTP server as --workers 0, so its
        threads are real; it has no limit monitor, so that count is not."""
        server = websocket_server()
        with patch.object(_process_state, "server", server):
            out = mod.get_service_metrics()
        assert out["flavor"] == "evented"
        assert set(out["threads"]) == {"http", "cron", "job", "websocket"}
        assert "http_threads_max" in out
        assert "limits_reached_threads" not in out, (
            "the evented server has no limit monitor; reporting its count as "
            "zero is a number an operator can act on and should not"
        )


class TestPrometheusExposition:
    def test_default_render_is_well_formed(self, mod):
        declared, errors = parse_exposition(mod.render_prometheus_exposition())
        assert not errors, errors
        assert "odoo_up" in declared

    def test_pool_counters_are_typed_as_counters(self, mod, pooled_db):
        health = {
            "read_write": {
                "mode": "read/write",
                "pool": {
                    "borrows": 12,
                    "borrows_failed": 1,
                    "borrow_wait_seconds_total": 0.5,
                    "borrow_wait_seconds_max": 0.25,
                    "borrow_wait_seconds": {"le_0.001": 10, "le_+Inf": 12},
                    "budget_maxconn": 64,
                    "budget_in_use": 3,
                    "budget_exhausted": 0,
                    "pools": 2,
                },
                "per_database": {"prod": {"pool_size": 5, "requests_waiting": 0}},
            }
        }
        with patch.object(pooled_db, "get_pool_health", return_value=health):
            text = mod.render_prometheus_exposition()
        declared, errors = parse_exposition(text)
        assert not errors, errors
        pid = os.getpid()
        assert declared["odoo_pool_borrows_total"] == "counter"
        assert declared["odoo_pool_budget_maxconn"] == "gauge"
        assert (
            f'odoo_pool_borrow_wait_seconds_bucket{{pid="{pid}",pool="read_write",'
            'le="+Inf"} 12' in text
        )
        assert (
            f'odoo_db_pool_pool_size{{pid="{pid}",pool="read_write",database="prod"}} 5'
            in text
        )

    def test_database_names_are_escaped_in_labels(self, mod, pooled_db):
        health = {
            "read_write": {
                "pool": {"borrows": 1},
                "per_database": {'we"ird\\name': {"pool_size": 1}},
            }
        }
        with patch.object(pooled_db, "get_pool_health", return_value=health):
            text = mod.render_prometheus_exposition()
        _, errors = parse_exposition(text)
        assert not errors, errors
        assert r'database="we\"ird\\name"' in text

    def test_non_numeric_per_database_stats_are_dropped(self, mod, pooled_db):
        health = {
            "read_write": {
                "pool": {"borrows": 1},
                "per_database": {
                    "prod": {
                        "pool_size": 5,
                        "pool_name": "read_write_prod",
                        "pool_available": True,
                        "requests_waiting": 0,
                        "wait_ms": 1.5,
                    }
                },
            }
        }
        with patch.object(pooled_db, "get_pool_health", return_value=health):
            text = mod.render_prometheus_exposition()

        _, errors = parse_exposition(text)
        assert not errors, f"a non-numeric stat broke the exposition: {errors}"
        assert "odoo_db_pool_pool_size" in text
        assert "odoo_db_pool_wait_ms" in text
        assert "odoo_db_pool_pool_name" not in text, "a string was emitted as a value"
        assert "odoo_db_pool_pool_available" not in text, (
            "a boolean was emitted as a value; bool is an int subclass and needs "
            "its own exclusion"
        )

    def test_replica_routers_render_one_family_per_database(self, mod, pooled_db):
        health = {
            "prod": {
                "lag": {
                    "enabled": True,
                    "max_lag_seconds": 1.0,
                    "last_lag_seconds": float("inf"),
                    "lagging": True,
                },
                "breaker": {
                    "closed": False,
                    "failures": 2,
                    "trips": 1,
                    "failure_threshold": 1,
                    "failure_window_seconds": None,
                    "cooldown_seconds": 30.0,
                    "cooldown_remaining_seconds": 12.5,
                },
                "write_pins": 3,
            }
        }
        with patch.object(pooled_db, "get_replica_health", return_value=health):
            text = mod.render_prometheus_exposition()
        declared, errors = parse_exposition(text)
        assert not errors, errors
        pid = os.getpid()
        label = f'{{pid="{pid}",database="prod"}}'
        assert f"odoo_replica_breaker_closed{label} 0" in text
        assert f"odoo_replica_breaker_cooldown_remaining_seconds{label} 12.5" in text
        assert f"odoo_replica_lag_seconds{label} +Inf" in text
        assert f"odoo_replica_lagging{label} 1" in text
        assert f"odoo_replica_write_pins{label} 3" in text
        assert "odoo_replica_breaker_failure_window_seconds" not in text, (
            "None is configuration, not a sample"
        )
        assert declared["odoo_replica_breaker_trips"] == "gauge"

    def test_booleans_render_as_one_and_zero(self, mod):
        server = prefork_server(population=0)

        with patch.object(_process_state, "server", server):
            text = mod.render_prometheus_exposition()
        assert f'odoo_long_polling_alive{{pid="{os.getpid()}"}} 0' in text
        _, errors = parse_exposition(text)
        assert not errors, errors

    def test_every_series_carries_the_serving_pid(self, mod, pooled_db):
        health = {"read_write": {"pool": {"borrows": 3}, "per_database": {}}}
        with patch.object(pooled_db, "get_pool_health", return_value=health):
            text = mod.render_prometheus_exposition()
        samples = [
            line for line in text.splitlines() if line and not line.startswith("#")
        ]
        assert samples
        expected = f'pid="{os.getpid()}"'
        unlabelled = [line for line in samples if expected not in line]
        assert not unlabelled, unlabelled

    def test_render_survives_a_failing_subsystem(self, mod, pooled_db):
        with (
            patch.object(
                pooled_db, "get_pool_health", side_effect=RuntimeError("pool is gone")
            ),
            patch.object(
                mod, "get_service_metrics", side_effect=RuntimeError("no server")
            ),
        ):
            text = mod.render_prometheus_exposition()
        assert f'odoo_up{{pid="{os.getpid()}"}} 1' in text
        _, errors = parse_exposition(text)
        assert not errors, errors


class TestBorrowWaitHistogramFamily:
    HEALTH = {
        "pool": {
            "borrows": 8,
            "borrow_wait_seconds_total": 0.42,
            "borrow_wait_seconds_max": 0.19,
            "borrow_wait_seconds": {
                "le_0.001": 4,
                "le_0.01": 7,
                "le_0.1": 8,
                "le_1.0": 8,
                "le_5.0": 8,
                "le_30.0": 8,
                "le_+Inf": 8,
            },
        },
    }

    def _render(self, mod):
        exp = mod._Exposition({"pid": "1234"})
        mod._add_pool_family(exp, "read_write", self.HEALTH)
        return exp.render()

    def test_the_family_is_declared_once_as_a_histogram(self, mod):
        text = self._render(mod)
        assert "# TYPE odoo_pool_borrow_wait_seconds histogram" in text
        assert text.count("# TYPE odoo_pool_borrow_wait_seconds ") == 1
        for suffix in ("_sum", "_bucket", "_count"):
            assert f"# TYPE odoo_pool_borrow_wait_seconds{suffix} " not in text

    def test_count_is_emitted_and_equals_the_inf_bucket(self, mod):
        text = self._render(mod)
        count = [
            line
            for line in text.splitlines()
            if line.startswith("odoo_pool_borrow_wait_seconds_count")
        ]
        assert len(count) == 1
        assert count[0].endswith(" 8")
        inf = [
            line
            for line in text.splitlines()
            if 'le="+Inf"' in line and "_bucket" in line
        ]
        assert inf[0].endswith(" 8")

    def test_the_mean_wait_is_now_computable(self, mod):
        text = self._render(mod)
        values = {}
        for line in text.splitlines():
            for suffix in ("_sum", "_count"):
                head = f"odoo_pool_borrow_wait_seconds{suffix}"
                if line.startswith(head + "{"):
                    values[suffix] = float(line.rsplit(" ", 1)[1])
        assert values["_sum"] / values["_count"] == pytest.approx(0.0525)

    def test_max_stays_its_own_gauge_declared_before_the_histogram(self, mod):
        text = self._render(mod)
        assert "# TYPE odoo_pool_borrow_wait_seconds_max gauge" in text
        assert text.index(
            "# TYPE odoo_pool_borrow_wait_seconds_max gauge"
        ) < text.index("# TYPE odoo_pool_borrow_wait_seconds histogram")

    def test_the_whole_scrape_still_parses(self, mod):
        _, errors = parse_exposition(self._render(mod))
        assert not errors, errors

    def test_an_empty_bucket_map_still_emits_a_declared_family(self, mod):
        exp = mod._Exposition({"pid": "1234"})
        mod._add_pool_family(exp, "read_write", {"pool": {}})
        text = exp.render()
        assert "# TYPE odoo_pool_borrow_wait_seconds histogram" in text
        assert (
            'odoo_pool_borrow_wait_seconds_count{pid="1234",pool="read_write"} 0'
            in text
        )
        _, errors = parse_exposition(text)
        assert not errors, errors


class TestReportingAndRecyclingAreDifferentQuestions:
    """A websocket thread must be counted and must never be time-limited.

    The two used to share one tuple, which made the exemption `check_limits`
    needs also blind `get_metrics()`: in --workers 0 the long-lived threads were
    the only ones an operator could not see.
    """

    def test_websocket_threads_are_counted(self, mod):
        import threading

        server = threaded_server()
        server.httpd = None
        server.limits_reached_threads = set()
        server._overrun_start_times = {}

        stop = threading.Event()
        ws = threading.Thread(target=stop.wait, args=(10,), daemon=True)
        ws.type = "websocket"
        ws.start()
        try:
            assert server.get_metrics()["threads"]["websocket"] >= 1
        finally:
            stop.set()
            ws.join()

    def test_the_evented_port_counts_its_threads_too(self, mod):
        import threading

        server = websocket_server(httpd=MagicMock(max_http_threads=7))
        stop = threading.Event()
        ws = threading.Thread(target=stop.wait, args=(10,), daemon=True)
        ws.type = "websocket"
        ws.start()
        try:
            out = server.get_metrics()
        finally:
            stop.set()
            ws.join()
        assert out["threads"]["websocket"] >= 1
        assert out["http_threads_max"] == 7
        assert "limits_reached_threads" not in out

    def test_websocket_threads_are_never_time_limited(self):
        from odoo.service import _threaded

        assert "websocket" in _threaded._REPORTED_THREAD_TYPES
        assert "websocket" not in _threaded._TIME_LIMITED_THREAD_TYPES, (
            "a websocket over limit_time_real would reload the server under "
            "every connected client"
        )
