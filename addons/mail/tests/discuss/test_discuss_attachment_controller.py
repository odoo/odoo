# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.addons.mail.tests.common_controllers import MailControllerAttachmentCommon


@odoo.tests.tagged("-at_install", "post_install", "mail_controller")
class TestDiscussAttachmentController(MailControllerAttachmentCommon):
    def test_attachment_allowed_upload_public_channel(self):
        """Test access to upload an attachment on an allowed upload public channel"""
        channel = self.env["discuss.channel"].create(
            {"group_public_id": None, "name": "public channel"}
        )
        channel._add_members(guests=self.guest)
        channel = channel.with_context(guest=self.guest)
        self._execute_subtests_upload(
            channel,
            (
                (self.guest, True),
                (self.user_admin, True),
                (self.user_employee, True),
                (self.user_portal, True),
                (self.user_public, True),
            ),
        )

    def test_attachment_delete_linked_to_channel(self):
        """Test access to delete an attachment associated with a channel
        whether or not limited `as_author_access_token` is sent"""
        channel = self.env["discuss.channel"].create({"name": "public channel"})
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
            thread=channel,
        )
