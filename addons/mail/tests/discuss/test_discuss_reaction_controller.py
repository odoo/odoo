from odoo.addons.mail.tests.common_controllers import MailControllerReactionCommon
from odoo.tests import tagged


@tagged("-at_install", "post_install", "mail_controller")
class TestMessageReactionController(MailControllerReactionCommon):

    def test_message_reaction_public_channel(self):
        """Test access of message reaction for a public channel."""
        channel = self.env["discuss.channel"].create(
            {"group_public_id": None, "name": "public channel"}
        )
        message = channel.message_post(body="public message")
        self._execute_subtests(
            message,
            (
                (self.user_public, False),
                (self.guest, True),
                (self.user_portal, True),
                (self.user_employee, True),
                (self.user_admin, True),
            ),
        )

    def test_message_reaction_channel_as_member(self):
        """Test access of message reaction for a channel as member."""
        channel = self.env["discuss.channel"]._create_group(
            partners_to=(self.user_portal + self.user_employee).partner_id.ids
        )
        channel._add_members(guests=self.guest)
        message = channel.message_post(body="invite message")
        self._execute_subtests(
            message,
            (
                (self.user_public, False),
                (self.guest, True),
                (self.user_portal, True),
                (self.user_employee, True),
                (self.user_admin, True),
            ),
        )

    def test_message_reaction_channel_as_non_member(self):
        """Test access of message reaction for a channel as non-member."""
        channel = self.env["discuss.channel"]._create_group(partners_to=[])
        message = channel.message_post(body="private message")
        self._execute_subtests(
            message,
            (
                (self.user_public, False),
                (self.guest, False),
                (self.user_portal, False),
                (self.user_employee, False),
                (self.user_admin, True),
            ),
        )
