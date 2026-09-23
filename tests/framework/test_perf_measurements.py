import threading
from types import SimpleNamespace

import pytest

from tests.perf import _bench, conftest


def test_residual_wall_and_cpu_are_separate_measurements(monkeypatch):
    wall = iter((10.0, 10.1))
    cpu = iter((3.0, 3.001))
    monkeypatch.setattr(
        _bench,
        "time",
        SimpleNamespace(
            perf_counter=lambda: next(wall),
            thread_time=lambda: next(cpu),
        ),
    )
    counter = _bench.StatementCounter()

    def operation():
        threading.current_thread().query_time += 0.02
        counter._record(None, None, None, 0, 0.02)

    with counter.on():
        readings = _bench.measure(operation, counter, repeat=1, rounds=1)
    assert readings == {
        "wall_ms": 100,
        "cpu_ms": 1,
        "sql_ms": 20,
        "non_sql_ms": 80,
        "non_sql_ms_median": 80,
        "statements": 1,
        "statements_min": 1,
        "statements_max": 1,
    }


def test_an_intermittent_extra_statement_cannot_hide_behind_the_median(monkeypatch):
    monkeypatch.setattr(conftest, "load_floors", lambda: {"probe": {"statements": 1}})
    with pytest.raises(AssertionError, match="counts varied"):
        conftest._check(
            "probe",
            {
                "statements": 1,
                "statements_min": 1,
                "statements_max": 2,
            },
            counts_only=True,
        )


def test_counts_only_keeps_statement_checks_and_omits_host_time_limits(monkeypatch):
    monkeypatch.setattr(
        conftest,
        "load_floors",
        lambda: {
            "probe": {"statements": 1, "non_sql_ms": 1},
        },
    )
    readings = {
        "statements": 1,
        "statements_min": 1,
        "statements_max": 1,
        "non_sql_ms": 100,
    }
    conftest._check("probe", readings, counts_only=True)
    with pytest.raises(AssertionError, match="non_sql_ms"):
        conftest._check("probe", readings, counts_only=False)
    with pytest.raises(AssertionError, match="was not measured"):
        conftest._check("probe", {}, counts_only=True)


@pytest.mark.parametrize(("repeat", "rounds"), [(0, 1), (1, 0), (-1, 1)])
def test_a_benchmark_cannot_measure_nothing(repeat, rounds):
    with pytest.raises(ValueError, match="positive"):
        _bench.measure(
            lambda: None, _bench.StatementCounter(), repeat=repeat, rounds=rounds
        )
