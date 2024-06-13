# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.mail_tracking_duration_mixin_case import MailTrackingDurationMixinCase


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
