# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from unittest.mock import patch

from odoo import fields, tools
from odoo.addons.mail.tests.common import MailCommon


class TestChannelLastInterestDt(MailCommon):
    """Cover the asynchronous ``last_interest_dt`` machinery (durable queue append, post-commit
    sync and cron drain).

    ``_update_last_interest_dt`` writes synchronously under ``test_enable``, so business-code tests
    bypass this path entirely; these tests exercise it by calling the sync/cron helpers directly and
    by forcing the async branch.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.LastInterestUpdate = cls.env["discuss.channel.last.interest.update"]
        cls.sync_cron = cls.env.ref("mail.ir_cron_discuss_channel_sync_last_interest_dt")
        now = fields.Datetime.now()
        cls.dt_early = now + timedelta(minutes=10)
        cls.dt_mid = now + timedelta(minutes=20)
        cls.dt_late = now + timedelta(minutes=30)

    def _make_channel(self, name):
        return self.env["discuss.channel"]._create_channel(name=name, group_id=None)

    def _queue(self, channel, date):
        return self.LastInterestUpdate.create({"channel_id": channel.id, "last_interest_dt": date})

    def _pending(self, channels):
        return self.LastInterestUpdate.search([("channel_id", "in", channels.ids)])

    def _triggers(self):
        return self.env["ir.cron.trigger"].search([("cron_id", "=", self.sync_cron.id)])

    def _trigger_count(self):
        return self.env["ir.cron.trigger"].search_count([("cron_id", "=", self.sync_cron.id)])

    def test_sync_applies_max_and_clears_queue(self):
        channel = self._make_channel("sync-max")
        self._queue(channel, self.dt_early)
        self._queue(channel, self.dt_late)
        self._queue(channel, self.dt_mid)
        channel._sync_last_interest_dt(channel.ids)
        self.assertEqual(channel.last_interest_dt, self.dt_late, "the newest queued value wins")
        self.assertFalse(self._pending(channel), "the queue is drained after syncing")

    def test_sync_does_not_downgrade_existing_value(self):
        channel = self._make_channel("sync-nodowngrade")
        channel.last_interest_dt = self.dt_late
        self._queue(channel, self.dt_early)
        channel._sync_last_interest_dt(channel.ids)
        self.assertEqual(channel.last_interest_dt, self.dt_late, "an older queued value must not overwrite a newer one")
        self.assertFalse(self._pending(channel), "pending rows are drained even when no update is applied")

    def test_sync_batches_multiple_channels(self):
        channel_a = self._make_channel("sync-a")
        channel_b = self._make_channel("sync-b")
        self._queue(channel_a, self.dt_early)
        self._queue(channel_b, self.dt_late)
        channels = channel_a | channel_b
        channels._sync_last_interest_dt(channels.ids)
        self.assertEqual(channel_a.last_interest_dt, self.dt_early)
        self.assertEqual(channel_b.last_interest_dt, self.dt_late)
        self.assertFalse(self._pending(channels))

    def test_sync_skips_locked_channel_without_triggering(self):
        channel = self._make_channel("sync-locked")
        before = channel.last_interest_dt
        self._queue(channel, self.dt_late)
        trigger_count = self._trigger_count()
        # simulate the row being held by a concurrent transaction: SKIP LOCKED yields nothing
        with patch.object(self.registry["discuss.channel"], "try_lock_for_update", lambda self, **kw: self.browse()):
            synced = channel._sync_last_interest_dt(channel.ids)
        self.assertFalse(synced, "a channel that could not be locked is not in the synced set")
        self.assertEqual(channel.last_interest_dt, before, "a channel that could not be locked is not synced")
        self.assertTrue(self._pending(channel), "its pending rows stay queued")
        self.assertEqual(self._trigger_count(), trigger_count,
            "the sync does not manage triggers itself; retriggering is the caller's responsibility")

    def test_cron_drains_and_retriggers_immediately_on_backlog(self):
        channel_a = self._make_channel("cron-a")
        channel_b = self._make_channel("cron-b")
        self._queue(channel_a, self.dt_late)
        self._queue(channel_b, self.dt_late)
        channels = channel_a | channel_b
        # batch_size=1 → a single pending row is drained, the backlog must retrigger the cron immediately
        self.env["discuss.channel"]._cron_sync_last_interest_dt(batch_size=1)
        self.assertEqual(self.LastInterestUpdate.search_count([("channel_id", "in", channels.ids)]), 1,
            "only one batch is drained per cron run")
        triggers = self._triggers()
        self.assertEqual(len(triggers), 1, "leftover drainable backlog retriggers the cron exactly once")
        self.assertLessEqual(triggers.call_at, fields.Datetime.now(),
            "progress plus a drainable row retriggers immediately")
        # a second run clears the rest and does not retrigger again
        self.env["discuss.channel"]._cron_sync_last_interest_dt(batch_size=1)
        self.assertFalse(self.LastInterestUpdate.search_count([("channel_id", "in", channels.ids)]))
        self.assertFalse(self._triggers(), "an emptied queue leaves no trigger behind")

    def test_cron_collapses_accumulated_triggers(self):
        # earlier retries and parallel posters pile up triggers, but the queue is already empty
        self.sync_cron._trigger()
        self.sync_cron._trigger(at=self.dt_late)
        self.assertEqual(self._trigger_count(), 2)
        self.env["discuss.channel"]._cron_sync_last_interest_dt()
        self.assertFalse(self._triggers(), "an empty queue collapses all accumulated triggers and adds none")

    def test_cron_collapses_triggers_into_single_retrigger(self):
        channel_a = self._make_channel("cron-a")
        channel_b = self._make_channel("cron-b")
        self._queue(channel_a, self.dt_late)
        self._queue(channel_b, self.dt_late)
        # earlier retries and parallel posters already piled up several triggers
        self.sync_cron._trigger()
        self.sync_cron._trigger(at=self.dt_late)
        self.sync_cron._trigger(at=self.dt_late)
        self.assertEqual(self._trigger_count(), 3)
        # a run that leaves a drainable backlog collapses them all and recreates exactly one
        self.env["discuss.channel"]._cron_sync_last_interest_dt(batch_size=1)
        self.assertEqual(self._trigger_count(), 1, "piled-up triggers collapse into the single recreated one")

    def test_cron_backs_off_when_batch_fully_locked(self):
        channel = self._make_channel("cron-locked")
        self._queue(channel, self.dt_late)
        with patch.object(self.registry["discuss.channel"], "try_lock_for_update", lambda self, **kw: self.browse()):
            self.env["discuss.channel"]._cron_sync_last_interest_dt()
        self.assertTrue(self._pending(channel), "a fully locked batch drains nothing")
        triggers = self._triggers()
        self.assertEqual(len(triggers), 1, "it retriggers to retry the locked rows later")
        self.assertGreater(triggers.call_at, fields.Datetime.now(),
            "a batch with no progress backs off instead of hot-looping")

    def test_cron_backs_off_when_only_locked_rows_remain(self):
        channel_a = self._make_channel("cron-drained")
        channel_b = self._make_channel("cron-held")
        self._queue(channel_a, self.dt_late)
        self._queue(channel_b, self.dt_late)
        # channel_a can be locked and drained, channel_b is held by a concurrent transaction
        with patch.object(self.registry["discuss.channel"], "try_lock_for_update",
                          lambda records, **kw: records & channel_a):
            self.env["discuss.channel"]._cron_sync_last_interest_dt()
        self.assertFalse(self._pending(channel_a), "the lockable channel is drained")
        self.assertTrue(self._pending(channel_b), "the held channel stays queued")
        triggers = self._triggers()
        self.assertEqual(len(triggers), 1, "it retriggers to retry the held channel")
        self.assertGreater(triggers.call_at, fields.Datetime.now(),
            "progress was made but only locked rows remain, so it backs off instead of looping")

    def test_cron_no_immediate_retrigger_when_whole_batch_locked_despite_backlog(self):
        channel_a = self._make_channel("cron-held")
        channel_b = self._make_channel("cron-waiting")
        self._queue(channel_a, self.dt_late)
        self._queue(channel_b, self.dt_late)
        # batch_size=1 picks up only one row and it is held → no progress this run; channel_b's row is
        # unlocked but sits beyond the batch, so it must not cause an immediate rerun (would hot-loop)
        with patch.object(self.registry["discuss.channel"], "try_lock_for_update", lambda self, **kw: self.browse()):
            self.env["discuss.channel"]._cron_sync_last_interest_dt(batch_size=1)
        triggers = self._triggers()
        self.assertEqual(len(triggers), 1, "it retriggers to retry later")
        self.assertGreater(triggers.call_at, fields.Datetime.now(),
            "a batch with no progress backs off even when unlocked rows sit beyond it")

    def test_update_enqueues_and_schedules_postcommit(self):
        channel = self._make_channel("async-enqueue")
        with patch.dict(tools.config._runtime_options, {"test_enable": False}):
            self.assertTrue(self.env.registry.ready, "the async branch requires a ready registry")
            channel._update_last_interest_dt(date=self.dt_late)
        self.assertEqual(self._pending(channel).mapped("last_interest_dt"), [self.dt_late],
            "the async path appends a durable queue row instead of writing the channel")
        self.assertIn(channel.id, self.env.cr.postcommit.data.get("mail.sync_last_interest_dt", ()),
            "a post-commit sync is scheduled for the channel")
        self.assertEqual(self._trigger_count(), 1, "a durable safety-net trigger is created up front")
        self.assertNotEqual(channel.last_interest_dt, self.dt_late, "the channel row stays untouched until the sync runs")

    def test_postcommit_sync_applies_queued_value(self):
        channel = self._make_channel("async-e2e")
        with patch.dict(tools.config._runtime_options, {"test_enable": False}):
            channel._update_last_interest_dt(date=self.dt_late)
        # the scheduled hook opens its own cursor: run it in registry test mode so that cursor
        # shares the test transaction (and thus sees the queued row)
        with self.registry_test_mode():
            self.env.cr.postcommit.run()
        self.assertEqual(channel.last_interest_dt, self.dt_late, "the post-commit hook syncs the queued value onto the channel")
        self.assertFalse(self._pending(channel), "the queue is drained by the post-commit sync")
        self.assertFalse(self._triggers(), "the safety-net trigger is cancelled once every channel is drained")

    def test_postcommit_keeps_trigger_when_channel_locked(self):
        channel = self._make_channel("async-locked")
        with patch.dict(tools.config._runtime_options, {"test_enable": False}):
            channel._update_last_interest_dt(date=self.dt_late)
        self.assertEqual(self._trigger_count(), 1, "a durable safety-net trigger is created up front")
        # the channel is held when the post-commit sync runs, so it cannot be drained
        with self.registry_test_mode(), patch.object(
            self.registry["discuss.channel"], "try_lock_for_update", lambda self, **kw: self.browse()
        ):
            self.env.cr.postcommit.run()
        self.assertTrue(self._pending(channel), "a locked channel is not drained by the post-commit sync")
        self.assertEqual(self._trigger_count(), 1,
            "the safety-net trigger is kept so the cron drains the leftover rows later")
