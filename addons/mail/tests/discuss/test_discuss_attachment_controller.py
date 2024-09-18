# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.addons.mail.tests.test_attachment_controller import TestAttachmentControllerCommon


@odoo.tests.tagged("-at_install", "post_install")
class TestDiscussAttachmentController(TestAttachmentControllerCommon):
    def test_attachment_not_allowed_upload_public_channel(self):
        """Test access to upload an attachment on a not allowed upload public channel"""
        channel = self.env["discuss.channel"].create(
            {"group_public_id": None, "name": "public channel"}
        )
        channel.add_members(guest_ids=[self.guest.id])
        channel.env.context = {**channel.env.context, "guest": self.guest}
        self._execute_subtests(
            channel,
            (
                (self.guest, False),
                (self.user_admin, True),
                (self.user_demo, True),
                (self.user_employee, True),
                (self.user_portal, False),
                (self.user_public, False),
            ),
        )

    def test_attachment_allowed_upload_public_channel(self):
        """Test access to upload an attachment on an allowed upload public channel"""
        channel = self.env["discuss.channel"].create(
            {"group_public_id": None, "name": "public channel"}
        )
        channel.write({"allow_public_upload": True})
        channel.add_members(guest_ids=[self.guest.id])
        channel.env.context = {**channel.env.context, "guest": self.guest}
        self._execute_subtests(
            channel,
            (
                (self.guest, True),
                (self.user_admin, True),
                (self.user_demo, True),
                (self.user_employee, True),
                (self.user_portal, True),
                (self.user_public, True),
            ),
        )
