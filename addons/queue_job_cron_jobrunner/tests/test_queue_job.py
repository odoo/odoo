# Copyright 2022 Camptocamp SA (https://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@camptocamp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta

from freezegun import freeze_time

from odoo import fields
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestQueueJob(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.cron = cls.env.ref("queue_job_cron_jobrunner.queue_job_cron")
        # Cleanup triggers just in case
        cls.env["ir.cron.trigger"].search([]).unlink()

    def assertTriggerAt(self, at, message=None):
        """Ensures a cron trigger is created at the given time"""
        return self.assertTrue(
            self.env["ir.cron.trigger"].search([("call_at", "=", at)]),
            message,
        )

    @freeze_time("2022-02-22 22:22:22")
    def test_queue_job_cron_trigger(self):
        """Test that ir.cron triggers are created for every queue.job"""
        job = self.env["res.partner"].with_delay().create({"name": "test"})
        job_record = job.db_record()
        self.assertTriggerAt(fields.Datetime.now(), "Trigger should've been created")
        job_record.eta = fields.Datetime.now() + timedelta(hours=1)
        self.assertTriggerAt(job_record.eta, "A new trigger should've been created")

    @mute_logger("odoo.addons.queue_job_cron_jobrunner.models.queue_job")
    def test_queue_job_process(self):
        """Test that jobs are processed by the queue job cron"""
        # Create some jobs
        job1 = self.env["res.partner"].with_delay().create({"name": "test"})
        job1_record = job1.db_record()
        job2 = self.env["res.partner"].with_delay().create(False)
        job2_record = job2.db_record()
        job3 = self.env["res.partner"].with_delay(eta=3600).create({"name": "Test"})
        job3_record = job3.db_record()
        # Run the job processing cron
        self.env["queue.job"]._job_runner(commit=False)
        # Check that the jobs were processed
        self.assertEqual(job1_record.state, "done", "Processed OK")
        self.assertEqual(job2_record.state, "failed", "Has errors")
        self.assertEqual(job3_record.state, "pending", "Still pending, because of eta")

    @freeze_time("2022-02-22 22:22:22")
    def test_queue_job_cron_trigger_enqueue_dependencies(self):
        """Test that ir.cron execution enqueue waiting dependencies"""
        delayable = self.env["res.partner"].delayable().create({"name": "test"})
        delayable2 = self.env["res.partner"].delayable().create({"name": "test2"})
        delayable.on_done(delayable2)
        delayable.delay()
        job_record = delayable._generated_job.db_record()
        job_record_depends = delayable2._generated_job.db_record()

        self.env["queue.job"]._job_runner(commit=False)

        self.assertEqual(job_record.state, "done", "Processed OK")
        # if the state is "waiting_dependencies", it means the "enqueue_waiting()"
        # step has not been doen when the parent job has been done
        self.assertEqual(job_record_depends.state, "done", "Processed OK")
