import pytest

from ._bench import calibration_ms
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
