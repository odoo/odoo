import time

import pytest

from ._bench import ServerClock, calibration_ms
from .conftest import CALIBRATION_KEY, _check

FLOORS = {
    CALIBRATION_KEY: 20.0,
    "scenario": {"statements": 4, "non_sql_ms": 10.0},
}
READINGS = {
    "statements": 4,
    "statements_min": 4,
    "statements_max": 4,
    "non_sql_ms": 30.0,
}


def test_a_slow_reading_on_a_machine_at_floor_speed_is_red():
    with pytest.raises(AssertionError, match=r"non_sql_ms reads 30\.0"):
        _check(
            "scenario",
            READINGS,
            counts_only=False,
            calibration=20.0,
            floors_data=FLOORS,
        )


def test_a_slowed_machine_leaves_time_unjudged_and_counts_exact():
    assert not _check(
        "scenario",
        READINGS,
        counts_only=False,
        calibration=40.0,
        floors_data=FLOORS,
    )
    with pytest.raises(AssertionError, match="an exact ratchet"):
        _check(
            "scenario",
            {**READINGS, "statements": 5, "statements_max": 5},
            counts_only=False,
            calibration=40.0,
            floors_data=FLOORS,
        )


def test_a_reading_within_tolerance_is_judged_and_green():
    assert _check(
        "scenario",
        {**READINGS, "non_sql_ms": 12.0},
        counts_only=False,
        calibration=24.0,
        floors_data=FLOORS,
    )


def test_the_calibration_is_a_positive_duration():
    assert calibration_ms(runs=2) > 0


class _Server:
    def outer(self):
        time.sleep(0.02)
        return self.inner()

    def inner(self):
        time.sleep(0.02)
        return "answer"


def test_the_server_clock_counts_only_the_outermost_call_and_unwraps():
    clock = ServerClock()
    original_outer = _Server.__dict__["outer"]
    original_inner = _Server.__dict__["inner"]
    clock.wrap(_Server, "outer", "inner")
    try:
        assert _Server().outer() == "answer"
    finally:
        clock.unwrap()
    assert 0.035 <= clock() < 0.08
    assert _Server.__dict__["outer"] is original_outer
    assert _Server.__dict__["inner"] is original_inner
