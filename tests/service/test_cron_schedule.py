import inspect

import pytest

from odoo.service._cron import CronSchedule


class _Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.fixture
def clock():
    return _Clock()


@pytest.fixture
def catalogue():
    return {"names": ["a", "b", "c"], "calls": 0}


@pytest.fixture
def schedule(clock, catalogue):
    def _list():
        catalogue["calls"] += 1
        return list(catalogue["names"])

    return CronSchedule(_list, refresh_interval=60, clock=clock)


class TestTheSweep:
    def test_the_first_pass_lists_and_takes_everything(self, schedule, catalogue):
        assert schedule.get_due_databases([]) == ["a", "b", "c"]
        assert catalogue["calls"] == 1

    def test_notified_databases_come_first(self, schedule):
        assert schedule.get_due_databases(["c"]) == ["c", "a", "b"]

    def test_a_notify_for_an_unknown_database_is_dropped(self, schedule):
        assert schedule.get_due_databases(["nope"]) == ["a", "b", "c"]


class TestANotifyStormIsNotAScanStorm:
    """The divergence this class exists to remove."""

    def test_a_fresh_list_is_not_re_read(self, schedule, catalogue, clock):
        schedule.get_due_databases([])
        for _ in range(50):
            clock.advance(0.1)
            schedule.get_due_databases(["b"])
        assert catalogue["calls"] == 1, (
            "one pg_database scan per notify is what the prefork worker used "
            "to do while the thread scanned once a minute"
        )

    def test_between_sweeps_only_the_notified_are_due(self, schedule, clock):
        schedule.get_due_databases([])
        clock.advance(1)
        assert schedule.get_due_databases(["b"]) == ["b"]

    def test_no_notify_between_sweeps_means_nothing_to_do(self, schedule, clock):
        schedule.get_due_databases([])
        clock.advance(1)
        assert schedule.get_due_databases([]) == []

    def test_the_list_is_re_read_once_the_interval_passes(
        self, schedule, catalogue, clock
    ):
        schedule.get_due_databases([])
        clock.advance(60)
        catalogue["names"] = ["a", "d"]
        assert schedule.get_due_databases([]) == ["a", "d"]
        assert catalogue["calls"] == 2

    def test_a_database_that_disappeared_stops_being_due(
        self, schedule, catalogue, clock
    ):
        schedule.get_due_databases([])
        clock.advance(60)
        catalogue["names"] = ["a"]
        schedule.get_due_databases([])
        clock.advance(1)
        assert schedule.get_due_databases(["b"]) == []


class TestTheListIsResolvedLate:
    def test_the_callable_is_asked_each_refresh(self, clock):
        answers = [["a"], ["b"]]

        def _next():
            return answers.pop(0)

        schedule = CronSchedule(_next, refresh_interval=1, clock=clock)
        assert schedule.get_due_databases([]) == ["a"]
        clock.advance(1)
        assert schedule.get_due_databases([]) == ["b"]

    def test_known_reflects_the_last_refresh(self, schedule):
        schedule.get_due_databases([])
        assert list(schedule.known) == ["a", "b", "c"]


class TestBothLoopsUseIt:
    def test_the_threaded_loop_builds_one(self):
        from odoo.service import _threaded

        assert "CronSchedule(" in inspect.getsource(_threaded.ThreadedServer)

    def test_the_prefork_worker_builds_one(self):
        from odoo.service import _worker

        assert "CronSchedule(" in inspect.getsource(_worker.WorkerCron)

    def test_neither_still_orders_the_databases_itself(self):
        from odoo.service import _threaded, _worker

        for mod in (_threaded, _worker):
            assert "order_notified_first" not in inspect.getsource(mod), (
                f"{mod.__name__} re-implements the ordering CronSchedule owns"
            )

    def test_they_use_the_same_refresh_interval(self):
        """Both take the default, so there is nothing left to keep in step."""
        from odoo.service._cron import CRON_POLL_INTERVAL_S, CronSchedule

        assert CronSchedule()._refresh_interval == CRON_POLL_INTERVAL_S

    def test_one_seam_now_reaches_both_loops(self, monkeypatch):
        """Patching `_cron.get_cron_databases` must scope every sweep.

        It used to reach neither loop.  Each carried its own byte-identical
        `_get_databases_to_sweep` wrapper so that its *own* module attribute stayed
        the seam, which meant a test had to patch
        `odoo.service._threaded.get_cron_databases` and
        `odoo.service._worker.get_cron_databases` separately and could silence
        one while the other still swept every database on the box.
        """
        from odoo.service import _cron

        calls = []
        monkeypatch.setattr(
            _cron, "get_cron_databases", lambda: calls.append(1) or ["scoped"]
        )
        assert _cron.CronSchedule().get_due_databases([]) == ["scoped"]
        assert calls, "the schedule bound the function instead of the module"

    def test_neither_loop_carries_its_own_wrapper_any_more(self):
        from odoo.service import _threaded, _worker

        for mod in (_threaded, _worker):
            assert not hasattr(mod, "_get_databases_to_sweep"), (
                f"{mod.__name__} grew its own copy back; the seam splits again"
            )
            assert not hasattr(mod, "get_cron_databases"), (
                f"{mod.__name__} imports the lister; patch it on _cron only"
            )
