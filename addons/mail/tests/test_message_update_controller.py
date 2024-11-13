from odoo.tests import tagged
from odoo.addons.mail.tests.common_controllers import MailControllerUpdateCommon


@tagged("-at_install", "post_install", "mail_controller")
class TestMessageUpdateController(MailControllerUpdateCommon):

    def test_message_update_partner_as_owner(self):
        """Test only admin user and message author can update the message content."""
        message = self.user_demo.partner_id.message_post(
            body=self.message_body,
            author_id=self.user_demo.partner_id.id,
            message_type="comment",
        )
        self._execute_subtests(
            message,
            (
                (self.guest, False),
                (self.user_admin, True),
                (self.user_demo, True),
                (self.user_employee, False),
                (self.user_portal, False),
                (self.user_public, False),
            ),
        )

    def test_message_update_non_owner_partner(self):
        """Test only admin user can update the message content if the user is not the author."""
        message = self.user_demo.partner_id.message_post(
            body=self.message_body,
            author_id=self.user_admin.partner_id.id,
            message_type="comment",
        )
        self._execute_subtests(
            message,
            (
                (self.guest, False),
                (self.user_admin, True),
                (self.user_demo, False),
                (self.user_employee, False),
                (self.user_portal, False),
                (self.user_public, False),
            ),
        )

    def test_message_update_fake_message(self):
        """Test update a non-existing message."""
        self._execute_subtests(
            self.fake_message,
            (
                (self.guest, False),
                (self.user_admin, False),
                (self.user_demo, False),
                (self.user_employee, False),
                (self.user_portal, False),
                (self.user_public, False),
            ),
        )
