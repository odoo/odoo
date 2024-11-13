from odoo.tests import tagged
from odoo.addons.mail.tests.common_controllers import MailControllerBinaryCommon


@tagged("-at_install", "post_install", "mail_controller")
class TestBinaryController(MailControllerBinaryCommon):

    def test_open_partner_avatar(self):
        """Test access to open the partner avatar."""
        self._execute_subtests(
            self.user_test,
            (
                (self.user_public, False),
                (self.guest, False),
                (self.user_portal, False),
                (self.user_employee, True),
                (self.user_demo, True),
                (self.user_admin, True),
            ),
        )

    def test_open_partner_avatar_has_message(self):
        """Test access to open a partner avatar who has sent a message on a private record."""
        self._send_message(self.user_test, "res.partner", self.user_test.partner_id.id)
        self._execute_subtests(
            self.user_test,
            (
                (self.user_public, False),
                (self.guest, False),
                (self.user_portal, False),
                (self.user_employee, True),
                (self.user_demo, True),
                (self.user_admin, True),
            ),
        )
