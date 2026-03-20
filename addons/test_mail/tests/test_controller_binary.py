from odoo.addons.mail.tests.common_controllers import MailControllerBinaryCommon
from odoo.tests import tagged


@tagged("-at_install", "post_install", "mail_controller")
class TestPublicBinaryController(MailControllerBinaryCommon):

    def test_avatar_no_public(self):
        """Test access to open a guest / partner avatar who hasn't sent a message on a
        public record."""
        for source in (self.guest_2, self.user_employee_nopartner.partner_id):
            self._execute_subtests(
                source, (
                    (self.user_public, False),
                    (self.guest, False),
                    (self.user_portal, False),
                    (self.user_employee, True),
                )
            )

    def test_avatar_private(self):
        """Test access to open a partner avatar who has sent a message on a private record."""
        document = self.env["mail.test.simple.unfollow"].create({"name": "Test"})
        self._post_message(document, self.user_employee_nopartner)
        self._execute_subtests(
            self.user_employee_nopartner.partner_id, (
                (self.user_public, False),
                (self.guest, False),
                (self.user_portal, False),
                (self.user_employee, True),
            )
        )

    def test_avatar_public(self):
        """Test access to open a guest avatar who has sent a message on a public record."""
        document = self.env["mail.test.access.public"].create({"name": "Test"})
        for author, source in ((self.guest_2, self.guest_2), (self.user_employee_nopartner, self.user_employee_nopartner.partner_id)):
            self._post_message(document, author)
            self._execute_subtests(
                source,
                (
                    (self.user_public, False),
                    (self.guest, False),
                    (self.user_portal, False),
                    (self.user_employee, True),
                ),
            )
