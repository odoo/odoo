from odoo.addons.mail.tests.mail_tracking_duration_testing import TestMailTrackingDurationMixin


class TestProjectTaskMailTrackingDuration(TestMailTrackingDurationMixin):

    @classmethod
    def setUpClass(cls):
        super().setUpClass('project.task', {'project_id': 'create'})

    def test_project_task_mail_tracking_duration(self):
        self._test_record_duration_tracking()

    def test_project_task_mail_tracking_duration_batch(self):
        self._test_record_duration_tracking_batch()

    def test_project_task_queries_batch_mail_tracking_duration(self):
        self._test_queries_batch_duration_tracking()
