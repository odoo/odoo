import logging
from unittest.mock import MagicMock, patch

import pytest

from odoo.service import settings as server_settings
from odoo.service._cron import ReconnectBackoff
from odoo.service._limits import BACKOFF_BASE_S, BACKOFF_CEILING_S

from .conftest import build_worker

CURVES = {
    60: [2, 4, 8, 16, 32, 60, 60, 60, 60, 60, 60, 60],
    30: [2, 4, 8, 16, 30, 30, 30, 30, 30, 30, 30, 30],
    10: [2, 4, 8, 10, 10, 10, 10, 10, 10, 10, 10, 10],
    2: [2] * 12,
}


def _schedule(ceiling, attempts=12):
    """The waits `ReconnectBackoff` actually sleeps for, in order."""
    slept = []
    backoff = ReconnectBackoff(MagicMock(spec=logging.Logger), ceiling=ceiling)
    for _ in range(attempts):
        backoff.wait_after_failure("probe", RuntimeError("down"), sleep=slept.append)
    return slept


@pytest.mark.parametrize("ceiling", sorted(CURVES))
def test_the_reconnect_curve_doubles_then_clamps(ceiling):
    assert _schedule(ceiling) == CURVES[ceiling]


def test_the_default_ceiling_and_base_are_the_reconnect_curve():
    assert BACKOFF_CEILING_S == 60
    assert BACKOFF_BASE_S == 2
    assert _schedule(BACKOFF_CEILING_S) == CURVES[60]


def test_a_runaway_attempt_count_stays_clamped_and_cheap():
    backoff = ReconnectBackoff(MagicMock(spec=logging.Logger))
    backoff.attempts = 10_000
    slept = []
    backoff.wait_after_failure("probe", RuntimeError("down"), sleep=slept.append)
    assert slept == [BACKOFF_CEILING_S], (
        "a database down for 10,000 reconnects must clamp to the ceiling, not "
        "raise OverflowError out of the retry path that exists to survive it"
    )


def test_a_ceiling_under_the_base_is_rejected_at_construction():
    with pytest.raises(ValueError, match="flattens the reconnect curve"):
        ReconnectBackoff(MagicMock(spec=logging.Logger), ceiling=1)


def test_reset_returns_the_schedule_to_the_base():
    backoff = ReconnectBackoff(MagicMock(spec=logging.Logger))
    slept = []
    for _ in range(4):
        backoff.wait_after_failure("probe", RuntimeError("down"), sleep=slept.append)
    backoff.reset()
    backoff.wait_after_failure("probe", RuntimeError("down"), sleep=slept.append)
    assert slept == [2, 4, 8, 16, 2]


class TestJobLimitsAreSeparableFromCron:
    CRON = {"limit_time_worker_cron": 300, "limit_time_real_cron": 120}

    def _with(self, **overrides):
        from odoo.tools import config

        return patch.dict(config.options, {**self.CRON, **overrides})

    def test_the_default_follows_cron(self):
        from odoo.service._limits import get_job_real_time_budget
        from odoo.service.settings import current

        with self._with(limit_time_worker_job=-1, limit_time_real_job=-1):
            assert current().job_max_age == 300
            assert get_job_real_time_budget() == 120

    def test_an_explicit_job_limit_wins(self):
        from odoo.service._limits import get_job_real_time_budget
        from odoo.service.settings import current

        with self._with(limit_time_worker_job=900, limit_time_real_job=3600):
            assert current().job_max_age == 900
            assert get_job_real_time_budget() == 3600

    def test_zero_disables_for_jobs_without_disabling_cron(self):
        from odoo.service._limits import get_job_real_time_budget
        from odoo.service.settings import current

        with self._with(limit_time_worker_job=0, limit_time_real_job=0):
            assert current().job_max_age == 0
            assert get_job_real_time_budget() == 0
        from odoo.tools import config

        with self._with(limit_time_worker_job=0, limit_time_real_job=0):
            assert config["limit_time_worker_cron"] == 300

    def test_both_options_are_registered(self):
        from odoo.tools import config

        assert "limit_time_worker_job" in config.options
        assert "limit_time_real_job" in config.options

    def test_worker_job_overrides_the_cron_max_age(self, worker_multi):
        from odoo.service._worker import WorkerCron, WorkerJob

        assert WorkerJob.get_max_age is not WorkerCron.get_max_age
        worker = build_worker(WorkerJob, worker_multi)
        with self._with(limit_time_worker_job=900):
            assert worker.get_max_age() == 900
        with self._with(limit_time_worker_job=-1):
            assert worker.get_max_age() == 300

    def test_worker_job_arms_its_watchdog_from_the_job_timeout(self, worker_multi):
        from odoo.service._worker import WorkerCron, WorkerJob

        worker_multi.cron_timeout, worker_multi.job_timeout = 300, 45
        assert build_worker(WorkerCron, worker_multi).watchdog_timeout == 300
        assert build_worker(WorkerJob, worker_multi).watchdog_timeout == 45


CRON_BUDGET_CASES = [
    (120, -1, 120),
    (120, -5, 120),
    (120, 0, 0),
    (120, 30, 30),
    (0, -5, 0),
    (0, 0, 0),
]


@pytest.mark.parametrize(("real", "cron", "expected"), CRON_BUDGET_CASES)
def test_the_cron_budget_resolves_the_whole_sentinel_chain(real, cron, expected):
    from odoo.service._limits import get_cron_real_time_budget
    from odoo.tools import config

    with patch.dict(
        config.options, {"limit_time_real": real, "limit_time_real_cron": cron}
    ):
        assert get_cron_real_time_budget() == expected


@pytest.mark.parametrize(("real", "cron", "expected"), CRON_BUDGET_CASES)
def test_the_prefork_watchdog_agrees_with_the_resolver(real, cron, expected):
    from unittest.mock import MagicMock

    from odoo.service import server
    from odoo.service._limits import get_cron_real_time_budget

    cfg = {
        "http_interface": "",
        "http_port": 8069,
        "workers": 2,
        "limit_request": 100,
        "limit_time_real": real,
        "limit_time_real_cron": cron,
        "limit_time_real_job": -1,
    }
    with (
        server_settings.override(**cfg),
    ):
        prefork = server.PreforkServer(MagicMock())
        assert prefork.cron_timeout == (get_cron_real_time_budget() or None)
        assert prefork.cron_timeout == (expected or None)


def test_nothing_outside_the_resolver_reads_the_raw_cron_knob():
    import pathlib

    import odoo

    root = pathlib.Path(odoo.__file__).resolve().parent
    scanned = [
        *sorted((root / "service").glob("*.py")),
        root / "addons" / "base" / "models" / "ir_cron.py",
        root / "addons" / "base" / "models" / "ir_job.py",
    ]
    offenders = sorted(
        path.name
        for path in scanned
        if path.exists()
        and "limit_time_real_cron" in path.read_text()
        and path.name not in {"_limits.py", "settings.py"}
    )
    assert offenders == [], (
        "ServerSettings.cron_real_time_budget, behind get_cron_real_time_budget(), "
        f"is the one answer to how long cron work may run; {offenders} resolve "
        "the knob themselves"
    )


SENTINELS = [-5, -1, 0, 30, 300]


def _legacy_inherits(limit):
    """The pre-`_get_inherited_budget` predicate, spelled out as it was."""
    return limit == -1 or limit < -1


@pytest.mark.parametrize("worker_job", SENTINELS)
@pytest.mark.parametrize("worker_cron", SENTINELS)
def test_job_max_age_still_walks_the_two_level_chain(worker_job, worker_cron):
    """`_get_inherited_budget` must be a rewrite, not a behaviour change."""
    from odoo.service.settings import current
    from odoo.tools import config

    expected = worker_cron if _legacy_inherits(worker_job) else worker_job
    with patch.dict(
        config.options,
        {
            "limit_time_worker_job": worker_job,
            "limit_time_worker_cron": worker_cron,
        },
    ):
        assert current().job_max_age == expected


@pytest.mark.parametrize("real_job", SENTINELS)
@pytest.mark.parametrize("real_cron", SENTINELS)
@pytest.mark.parametrize("real", [-1, 0, 120])
def test_the_job_budget_still_walks_the_three_level_chain(real_job, real_cron, real):
    """The one chain with three links, and the only one that re-tests a result.

    The old code reached `limit_time_real` by asking `_is_inherited_from_cron`
    about the *return value* of a two-level helper, which is a chain hidden in
    the call graph rather than stated.  That helper was deleted on 2026-08-30
    once nothing called it; this pins that the flattened version resolves every
    one of the 75 sentinel combinations identically to the nested one.
    """
    from odoo.service._limits import get_job_real_time_budget
    from odoo.tools import config

    legacy = real_cron if _legacy_inherits(real_job) else real_job
    if _legacy_inherits(legacy):
        legacy = real
    expected = max(legacy, 0)

    with patch.dict(
        config.options,
        {
            "limit_time_real_job": real_job,
            "limit_time_real_cron": real_cron,
            "limit_time_real": real,
        },
    ):
        assert get_job_real_time_budget() == expected


def test_a_chain_whose_last_link_also_inherits_returns_the_sentinel():
    """Documented edge: the caller's clamp, not the resolver, absorbs it."""
    from odoo.service._limits import get_cron_real_time_budget
    from odoo.service.settings import _get_first_owned_limit
    from odoo.tools import config

    with patch.dict(
        config.options, {"limit_time_real_cron": -1, "limit_time_real": -1}
    ):
        assert _get_first_owned_limit(-1, -1) == -1
        assert get_cron_real_time_budget() == 0


class TestBothCronLoopsReleaseADatabaseTheSameWay:
    """One behaviour, one primitive.

    The threaded loop drained and the prefork worker closed, with the same
    guard and the same intent on both sides.  `close_database` pops the pool
    AND discards `_reachable_keys`, so `_get_or_create_pool` then pays a fresh
    connectability probe plus a pool construction for that database on every
    sweep; `drain_database` keeps both.
    """

    def test_it_drains_rather_than_closes(self):
        from odoo.service import _cron

        with (
            patch.object(_cron.db, "drain_db") as drain,
            patch.object(_cron.db, "close_db") as close,
        ):
            _cron.drain_swept_database("somedb")

        drain.assert_called_once_with("somedb")
        assert not close.called, (
            "closing discards the pool and its proven-reachable record, so the "
            "next sweep re-probes and rebuilds the pool for this database"
        )

    def test_neither_loop_reaches_past_the_helper(self):
        import pathlib

        import odoo

        service = pathlib.Path(odoo.__file__).resolve().parent / "service"
        offenders = sorted(
            path.name
            for path in (service / "_threaded.py", service / "_worker.py")
            if "close_db(" in path.read_text() or "drain_db(" in path.read_text()
        )
        assert offenders == [], (
            "drain_swept_database() is the one answer to how a sweep lets go "
            f"of a database; {offenders} call the pool primitives directly and "
            "can drift apart again"
        )
