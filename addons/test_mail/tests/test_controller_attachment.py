# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.addons.mail.tests.common_controllers import MailControllerAttachmentCommon


@odoo.tests.tagged("-at_install", "post_install", "mail_controller")
class TestAttachmentController(MailControllerAttachmentCommon):
    def test_independent_attachment_delete(self):
        """Test access to delete an attachment whether or not limited `ownership_token` is sent"""
        self._execute_subtests_delete(self.all_users, token=True, allowed=True)
        self._execute_subtests_delete(self.user_admin, token=False, allowed=True)
        self._execute_subtests_delete(
            (self.guest, self.user_employee, self.user_portal, self.user_public),
            token=False,
            allowed=False,
        )

    def test_attachment_delete_linked_to_thread(self):
        """Test access to delete an attachment associated with a thread
        whether or not limited `ownership_token` is sent"""
        thread = self.env["mail.test.simple"].create({"name": "Test"})
        self._execute_subtests_delete(self.all_users, token=True, allowed=True, thread=thread)
        self._execute_subtests_delete(
            (self.user_admin, self.user_employee),
            token=False,
            allowed=True,
            thread=thread,
        )
        self._execute_subtests_delete(
            (self.guest, self.user_portal, self.user_public),
            token=False,
            allowed=False,
            thread=thread,
        )
