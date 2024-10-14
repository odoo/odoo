from odoo.addons.mail.tests.common_controllers import MailControllerUpdateCommon
from odoo.tests import tagged


@tagged("-at_install", "post_install", "mail_controller")
class TestDiscussMessageUpdateController(MailControllerUpdateCommon):

    def test_message_update_guest_as_owner(self):
        """Test only admin user and message author can update the message content in a channel."""
        channel = self.env["discuss.channel"].create(
            {"group_public_id": None, "name": "public channel"}
        )
        channel.add_members(guest_ids=[self.guest.id])
        channel = channel.with_context(guest=self.guest)
        message = channel.with_user(self.user_public).message_post(
            body=self.message_body,
            message_type="comment",
        )
        self._execute_subtests(
            message,
            (
                (self.guest, True),
                (self.user_admin, True),
                (self.user_employee, False),
                (self.user_portal, False),
                (self.user_public, False),
            ),
        )

    def test_message_update_public_channel(self):
        """Test only admin user can update the message content of other authors in a channel."""
        channel = self.env["discuss.channel"].create(
            {"group_public_id": None, "name": "public channel"}
        )
        message = channel.message_post(
            body=self.message_body,
            message_type="comment",
        )
        self._execute_subtests(
            message,
            (
                (self.guest, False),
                (self.user_admin, True),
                (self.user_employee, False),
                (self.user_portal, False),
                (self.user_public, False),
            ),
        )
