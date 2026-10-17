# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.addons.mail.tests.common_tracking import MailTrackingDurationMixinCase
from odoo.tests import Form, tagged


@tagged('is_query_count')
class TestProjectTaskMailTrackingDuration(MailTrackingDurationMixinCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass('project.task', {'project_id': 'create'})

    def test_project_task_mail_tracking_duration(self):
        self._test_record_duration_tracking()

    def test_project_task_mail_tracking_duration_batch(self):
        self._test_record_duration_tracking_batch()

    def test_project_task_queries_batch_mail_tracking_duration(self):
        self._test_queries_batch_duration_tracking()

    def test_task_mail_tracking_duration_during_onchange_stage(self):
        """
        Checks that the status bar duration is correctly set during an onchange of its stage_id.
        """
        task = self.rec_1
        task.stage_id = self.stage_1
        initial_tracking = task.duration_tracking
        with Form(task) as task_form:
            task_form.stage_id = self.stage_2
        final_tracking = task.duration_tracking
        self.assertEqual(initial_tracking[str(self.stage_1.id)], final_tracking[str(self.stage_1.id)])
        self.assertEqual(final_tracking[str(self.stage_2.id)], 0)

    def test_task_rotting_during_onchange_stage(self):
        (self.stage_1 | self.stage_2).rotting_threshold_days = 2
        task = self.rec_1
        task.stage_id = self.stage_1
        task.date_last_stage_update = fields.Datetime.subtract(fields.Datetime.now(), days=10)
        self.assertTrue(task.is_rotting)
        with Form(task) as task_form:
            task_form.stage_id = self.stage_2
            self.assertFalse(task_form.is_rotting, "Moving a task to another stage should stop it from rotting")
