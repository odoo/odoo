from odoo.addons.mail.tests.mail_tracking_duration_testing import TestMailTrackingDurationMixin


class TestMailTrackingDuration(TestMailTrackingDurationMixin):

    @classmethod
    def setUpClass(cls):
        super().setUpClass('mail.test.mail.tracking.duration')

    def test_mail_tracking_duration(self):
        self._test_record_duration_tracking()

    def test_mail_tracking_duration_batch(self):
        self._test_record_duration_tracking_batch()

    def test_queries_batch_mail_tracking_duration(self):
        self._test_queries_batch_duration_tracking()
