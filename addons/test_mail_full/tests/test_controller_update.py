from odoo.addons.mail.tests.common_controllers import MailControllerUpdateCommon
from odoo.tests import tagged


@tagged("-at_install", "post_install", "mail_controller")
class TestPortalMessageUpdateController(MailControllerUpdateCommon):

    def test_message_update_no_message(self):
        """Test update a non-existing message."""
        self._execute_subtests(
            self.fake_message,
            ((user, False) for user in [self.guest, self.user_admin, self.user_employee, self.user_portal, self.user_public]),
        )

    def test_message_update_portal(self):
        """Test only admin and author can modify content of a message, works if
        author is a portal user. """
        record = self.env["mail.test.portal.no.partner"].create({"name": "Test"})
        token, bad_token, sign, bad_sign, _ = self._get_sign_token_params(record)
        message = record.message_post(
            body=self.message_body,
            author_id=self.user_portal.partner_id.id,
            message_type="comment",
        )
        self._execute_subtests(
            message,
            (
                (self.user_public, False),
                (self.user_public, False, token),
                (self.user_public, False, sign),
                (self.guest, False),
                (self.guest, False, token),
                (self.guest, False, sign),
                (self.user_portal, False),
                (self.user_portal, False, bad_token),
                (self.user_portal, False, bad_sign),
                (self.user_portal, True, token),
                (self.user_portal, True, sign),
                (self.user_employee, False),
                (self.user_employee, False, token),
                (self.user_employee, False, sign),
                (self.user_admin, True),
                (self.user_admin, True, bad_token),
                (self.user_admin, True, bad_sign),
                (self.user_admin, True, token),
                (self.user_admin, True, sign),
            ),
        )
