import odoo
from odoo.addons.mail.tests.common_controllers import MailControllerAttachmentCommon


@odoo.tests.tagged("-at_install", "post_install", "mail_controller")
class TestAttachmentController(MailControllerAttachmentCommon):
    def test_independent_attachment_delete(self):
        """Test access to delete an attachment whether or not
        limited `as_author_access_token` is sent"""
        # Subtest format: (user, token, result)
        self._execute_subtests_delete(
            (
                (self.guest, True, True),
                (self.guest, False, False),
                (self.user_admin, True, True),
                (self.user_admin, False, True),
                (self.user_employee, True, True),
                (self.user_employee, False, False),
                (self.user_portal, True, True),
                (self.user_portal, False, False),
                (self.user_public, True, True),
                (self.user_public, False, False),
            ),
        )

    def test_attachment_delete_linked_to_thread(self):
        """Test access to delete an attachment associated with a thread
        whether or not limited `as_author_access_token` is sent"""
        thread = self.env["mail.test.simple"].create({"name": "Test"})
        # Subtest format: (user, token, result)
        self._execute_subtests_delete(
            (
                (self.guest, True, True),
                (self.guest, False, False),
                (self.user_admin, True, True),
                (self.user_admin, False, True),
                (self.user_employee, True, True),
                (self.user_employee, False, True),
                (self.user_portal, True, True),
                (self.user_portal, False, False),
                (self.user_public, True, True),
                (self.user_public, False, False),
            ),
            thread=thread,
        )

    def test_attachment_delete_linked_to_message(self):
        """Test access to delete an attachment associated with a message
        whether or not limited `as_author_access_token` is sent"""
        message = self.env["mail.message"].create({"body": "Test"})
        # Subtest format: (user, token, result)
        self._execute_subtests_delete(
            (
                (self.guest, True, True),
                (self.guest, False, False),
                (self.user_admin, True, True),
                (self.user_admin, False, True),
                (self.user_employee, True, True),
                (self.user_employee, False, False),
                (self.user_portal, True, True),
                (self.user_portal, False, False),
                (self.user_public, True, True),
                (self.user_public, False, False),
            ),
            message=message,
        )
