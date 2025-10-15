# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.addons.mail.tests.common_controllers import MailControllerAttachmentCommon
from odoo.tools.misc import file_open


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

    def test_attachment_delete_linked_to_public_channel(self):
        """Test access to delete an attachment associated with a public channel
        whether or not limited `ownership_token` is sent"""
        channel = self.env["discuss.channel"].create({"name": "public channel"})
        self._execute_subtests_delete(self.all_users, token=True, allowed=True, thread=channel)
        self._execute_subtests_delete(
            (self.user_admin, self.user_employee),
            token=False,
            allowed=True,
            thread=channel,
        )
        self._execute_subtests_delete(
            (self.guest, self.user_portal, self.user_public),
            token=False,
            allowed=False,
            thread=channel,
        )

    def test_attachment_delete_linked_to_private_channel(self):
        """Test access to delete an attachment associated with a private channel
        whether or not limited `ownership_token` is sent"""
        channel = self.env["discuss.channel"].create(
            {"name": "Private Channel", "channel_type": "group"}
        )
        self._execute_subtests_delete(self.all_users, token=True, allowed=True, thread=channel)
        self._execute_subtests_delete(self.user_admin, token=False, allowed=True, thread=channel)
        self._execute_subtests_delete(
            (self.guest, self.user_employee, self.user_portal, self.user_public),
            token=False,
            allowed=False,
            thread=channel,
        )

    def test_first_page_access_of_mail_attachment_pdf(self):
        """Test accessing the first page of a PDF that is encrypted(test_AES.pdf) or has invalid encoding(test_unicode.pdf)."""
        attachments = []
        for pdf in (
            'mail/tests/discuss/files/test_AES.pdf',
            'mail/tests/discuss/files/test_unicode.pdf',
        ):
            with file_open(pdf, "rb") as file:
                attachments.append({
                    'name': pdf,
                    'raw': file.read(),
                    'mimetype': 'application/pdf',
                })
        attachments = self.env['ir.attachment'].create(attachments)

        self.authenticate("admin", "admin")

        for attachment in attachments:
            ownership_token = attachment._get_ownership_token()
            url = f'/mail/attachment/pdf_first_page/{attachment.id}?access_token={ownership_token}'
            response = self.url_open(url)
            # Depending on the environment, the response status_code may vary:
            # - 200 if PyPDF2 and PyCryptodome are installed (PDF successfully parsed)
            # - 415 if those libs are missing (PDF cannot be processed)
            self.assertIn(response.status_code, [415, 200])
