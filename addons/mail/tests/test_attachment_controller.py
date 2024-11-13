from odoo.tests import tagged
from odoo.addons.mail.tests.common_controllers import MailControllerAttachmentCommon


@tagged("-at_install", "post_install", "mail_controller")
class TestAttachmentController(MailControllerAttachmentCommon):

    def test_attachment_partner(self):
        """Test access to upload an attachment on a non channel thread"""
        record = self.user_demo.partner_id
        self._execute_subtests(
            record,
            (
                (self.guest, False),
                (self.user_admin, True),
                (self.user_demo, True),
                (self.user_employee, False),
                (self.user_portal, False),
                (self.user_public, False),
            ),
        )
