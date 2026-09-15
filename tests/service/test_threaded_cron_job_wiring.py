from unittest.mock import MagicMock, patch

import pytest

from odoo.service import _threaded
from odoo.service import settings as server_settings
from odoo.service._cron import CRON_TRIGGER_CHANNEL, JOB_QUEUE_CHANNEL

from .conftest import threaded_server


@pytest.fixture
def server():
    obj = threaded_server()
    obj.logger = MagicMock()
    return obj


class TestEachListenerIsWiredToItsOwnQueue:
    """Cron and job are the same loop given different arguments.

    Every mix-up here is a one-token edit and none of them raises. Wire the job
    listener to the cron channel and the job queue still drains -- on the
    60-second periodic sweep instead of on NOTIFY -- so it presents as "jobs are
    slow", not as "jobs are broken". Wire it to the cron processor and the queue
    never drains at all.
    """

    def _call(self, server, method):
        with patch.object(server, "_run_listener_thread") as listen:
            getattr(server, method)(3)
        assert listen.call_count == 1
        return listen.call_args

    def test_the_cron_listener_takes_the_cron_channel_and_processor(self, server):
        args, kwargs = self._call(server, "run_cron_thread")
        from odoo.addons.base.models.ir_cron import IrCron

        assert args == (3,)
        assert kwargs["channel"] == CRON_TRIGGER_CHANNEL
        assert kwargs["process_jobs"] == IrCron._process_jobs
        assert kwargs["label"] == "cron"

    def test_the_job_listener_takes_the_job_channel_and_processor(self, server):
        args, kwargs = self._call(server, "run_job_thread")
        from odoo.addons.base.models.ir_job import IrJob

        assert args == (3,)
        assert kwargs["channel"] == JOB_QUEUE_CHANNEL
        assert kwargs["process_jobs"] == IrJob._process_jobs
        assert kwargs["label"] == "job"

    def test_the_two_listeners_agree_on_nothing_that_distinguishes_them(self, server):
        """Guards the case where both constants or both processors collapse.

        Asserting each side separately still passes if `JOB_QUEUE_CHANNEL` is
        ever redefined to equal `CRON_TRIGGER_CHANNEL`; this is what notices.
        """
        _, cron = self._call(server, "run_cron_thread")
        _, job = self._call(server, "run_job_thread")

        assert cron["channel"] != job["channel"]
        assert cron["process_jobs"] != job["process_jobs"]
        assert cron["label"] != job["label"]

    def test_each_spawner_hands_over_its_own_recycle_age(self, server):
        """The recycle age is an argument, so the label is cosmetic.

        A cron thread recycles on `limit_time_worker_cron`; a job thread on
        `job_max_age`, which inherits the cron value only while its own is
        unset.
        """
        with server_settings.override(
            limit_time_worker_cron=300, limit_time_worker_job=45
        ):
            _, cron = self._call(server, "run_cron_thread")
            _, job = self._call(server, "run_job_thread")
        assert cron["max_age"] == 300
        assert job["max_age"] == 45

        with server_settings.override(
            limit_time_worker_cron=300,
            limit_time_worker_job=server_settings.INHERIT_FROM_CRON,
        ):
            _, job = self._call(server, "run_job_thread")
        assert job["max_age"] == 300


class TestSpawnersTypeTheirThreadsForTheRightTimeBudget:
    """`check_limits` reads `thread.type` to choose the real-time budget.

    A thread typed "cron" is measured against `settings.cron_real_time_budget`, "job"
    against `settings.job_real_time_budget`, anything else against `limit_time_real`.
    Mistype a thread and it is recycled on the wrong deadline -- and the deadline
    is the thing that restarts the whole server.
    """

    def _spawn(self, server, method, cfg):
        made = []

        def fake_thread(**kwargs):
            t = MagicMock(**{k: v for k, v in kwargs.items() if k != "target"})
            t.target = kwargs["target"]
            t.name = kwargs["name"]
            made.append(t)
            return t

        with (
            server_settings.override(**cfg),
            patch.object(_threaded.threading, "Thread", side_effect=fake_thread),
            patch.object(_threaded, "as_worker_thread", side_effect=lambda t: t),
        ):
            getattr(server, method)()
        return made

    def test_cron_threads_are_counted_by_max_cron_threads_and_typed_cron(self, server):
        made = self._spawn(
            server, "spawn_cron_threads", {"max_cron_threads": 2, "job_workers": 7}
        )

        assert len(made) == 2, "spawn_cron_threads must count from max_cron_threads"
        assert [t.type for t in made] == ["cron", "cron"]
        assert [t.name for t in made] == [
            "odoo.service.cron.cron0",
            "odoo.service.cron.cron1",
        ]
        assert all(t.target == server.run_cron_thread for t in made)
        assert all(t.start.called for t in made)

    def test_job_threads_are_counted_by_job_workers_and_typed_job(self, server):
        made = self._spawn(
            server, "spawn_job_threads", {"max_cron_threads": 7, "job_workers": 2}
        )

        assert len(made) == 2, "spawn_job_threads must count from job_workers"
        assert [t.type for t in made] == ["job", "job"]
        assert [t.name for t in made] == [
            "odoo.service.job.job0",
            "odoo.service.job.job1",
        ]
        assert all(t.target == server.run_job_thread for t in made)

    def test_both_spawn_nothing_when_their_own_knob_is_zero(self, server):
        cfg = {"max_cron_threads": 0, "job_workers": 0}
        assert self._spawn(server, "spawn_cron_threads", cfg) == []
        assert self._spawn(server, "spawn_job_threads", cfg) == []

    def test_the_types_are_the_ones_the_settings_budget_answers_for(self):
        """A typo in either string is silent: the thread falls to the default.

        `check_limits` matches these against `_TIME_LIMITED_THREAD_TYPES` and
        asks `ServerSettings.get_real_time_budget` for the budget; an
        unrecognised type is simply measured against `limit_time_real`.
        """
        assert set(_threaded._TIME_LIMITED_THREAD_TYPES) >= {"cron", "job"}
        settings = server_settings.ServerSettings(
            limit_time_real=120, limit_time_real_cron=300, limit_time_real_job=45
        )
        assert settings.get_real_time_budget("http") == 120
        assert settings.get_real_time_budget("cron") == 300
        assert settings.get_real_time_budget("job") == 45
        assert settings.get_real_time_budget("websocket") == 120
        assert (
            server_settings.ServerSettings(limit_time_real=-1).get_real_time_budget(
                "http"
            )
            == 0
        )
