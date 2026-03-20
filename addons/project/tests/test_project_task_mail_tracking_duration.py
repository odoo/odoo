# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common_tracking import MailTrackingDurationMixinCase
from odoo.tests import Form, tagged


@tagged('is_query_count')
@tagged('at_install', '-post_install')  # LEGACY at_install
class TestProjectTaskMailTrackingDuration(MailTrackingDurationMixinCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass('project.task')

    @classmethod
    def _prepare_duration_setup(cls, test_model_name):
        if test_model_name == 'project.task':
            cls.test_project = cls.env['project.project'].create({'name': 'Test Project'})
        return super()._prepare_duration_setup

    @classmethod
    def _create_records(cls, test_model_name, count=5, record_vals=None):
        if test_model_name == 'project.task':
            record_vals = record_vals or {}
            record_vals['project_id'] = cls.test_project.id
        return super()._create_records(test_model_name, count=count, record_vals=record_vals)

    def test_project_task_mail_tracking_duration(self):
        self._test_record_duration_tracking()

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
