from odoo.addons.mail.tests.common_tracking import MailTrackingDurationMixinCase
from odoo.tests import tagged


@tagged('is_query_count', 'mail_track')
class TestCrmLeadMailTrackingDuration(MailTrackingDurationMixinCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass('crm.lead')

    def test_crm_lead_mail_tracking_duration(self):
        self._test_record_duration_tracking()

    def test_crm_lead_queries_batch_mail_tracking_duration(self):
        self._test_queries_batch_duration_tracking()
