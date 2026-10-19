from odoo.addons.mail.tests.common_tracking import MailTrackingDurationMixinCase
from odoo.tests import tagged


@tagged('mail_track', 'mail_duration_mixin')
class TestCrmLeadMailTrackingDuration(MailTrackingDurationMixinCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass('crm.lead')

    def test_crm_lead_mail_tracking_duration(self):
        self._test_record_duration_tracking()
