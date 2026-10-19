# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

import odoo
from odoo.addons.bus.models.bus import json_dump
from odoo.addons.mail.tests.common_controllers import MailControllerAttachmentCommon
from odoo.tools.misc import file_open


@odoo.tests.tagged("mail_controller")
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
        channel = self.env["discuss.channel"].create(
            {"group_public_id": None, "name": "public channel"}
        )
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

    def test_attachment_edit_and_delete_from_other_tab(self):
        """Test the author of a message receives the ownership token of its attachments on their
        own bus channel, so that they can edit the message and delete the attachments from their
        other tabs, while the other members of the channel do not receive the tokens."""

        def get_attachments(bus_record):
            bus_channel = json_dump((self.cr.dbname, bus_record._name, bus_record.id))
            for notif in self._new_bus_notifs.filtered(lambda n: n.channel == bus_channel):
                payload = json.loads(notif.message)["payload"]
                yield from payload.get("store_data", payload).get("ir.attachment", [])

        def get_tokens(bus_record):
            return {
                attachment["id"]: attachment["ownership_token"]
                for attachment in get_attachments(bus_record)
                if "ownership_token" in attachment
            }

        channel = self.env["discuss.channel"].create({"name": "Group", "channel_type": "group"})
        channel._add_members(guests=self.guest, users=self.user_portal)
        for pseudo_user in (self.guest, self.user_portal):
            user, guest = self._authenticate_pseudo_user(pseudo_user)
            persona = guest or user
            IrAttachment = self.env["ir.attachment"].with_user(user).sudo()
            posted, added = IrAttachment.create(
                [
                    {"name": "Posted", "res_id": 0, "res_model": "mail.compose.message"},
                    {"name": "Added", "res_id": 0, "res_model": "mail.compose.message"},
                ],
            )
            with self.subTest(author=persona.name), self.mock_bus():
                message_id = self.make_jsonrpc_request(
                    "/mail/message/post",
                    {
                        "post_data": {
                            "attachment_ids": posted.ids,
                            "attachment_tokens": [posted._get_ownership_token()],
                            "body": "Posted",
                            "message_type": "comment",
                        },
                        "thread_id": channel.id,
                        "thread_model": "discuss.channel",
                    },
                )["message_id"]
                tokens = get_tokens(persona)
                self.assertEqual(set(tokens), {posted.id})
                self.assertEqual(
                    {attachment["id"] for attachment in get_attachments(channel)},
                    {posted.id},
                )
                self.make_jsonrpc_request(
                    "/mail/message/update_content",
                    {
                        "message_id": message_id,
                        "update_data": {
                            "attachment_ids": (posted + added).ids,
                            "attachment_tokens": [tokens[posted.id], added._get_ownership_token()],
                            "body": "Edited",
                        },
                    },
                )
                tokens = get_tokens(persona)
                self.assertEqual(set(tokens), {posted.id, added.id})
                self.assertEqual(
                    {attachment["id"] for attachment in get_attachments(channel)},
                    {posted.id, added.id},
                )
                self.assertFalse(get_tokens(channel))
                for attachment in posted + added:
                    self.make_jsonrpc_request(
                        "/mail/attachment/delete",
                        {"access_token": tokens[attachment.id], "attachment_id": attachment.id},
                    )
                self.assertFalse((posted + added).exists())

    def test_attachment_ownership_sent_to_author(self):
        """Test the ownership token of an attachment is sent to the author of the message, and not
        to the user who posts it on their behalf, nor to an author without user."""

        def get_bus_messages(bus_record):
            bus_channel = json_dump((self.cr.dbname, bus_record._name, bus_record.id))
            notifs = self._new_bus_notifs.filtered(lambda n: n.channel == bus_channel)
            return "".join(notifs.mapped("message"))

        channel = self.env["discuss.channel"].create({"name": "Group", "channel_type": "group"})
        channel._add_members(users=self.user_portal)
        IrAttachment = self.env["ir.attachment"].with_user(self.user_admin)
        attachment = IrAttachment.create(
            {"name": "Posted", "res_id": 0, "res_model": "mail.compose.message"},
        )
        with self.mock_bus():
            channel.with_user(self.user_admin).message_post(
                attachment_ids=attachment.ids,
                author_id=self.user_portal.partner_id.id,
                body="Posted",
                message_type="comment",
            )
        self.assertIn("ownership_token", get_bus_messages(self.user_portal))
        self.assertNotIn("ownership_token", get_bus_messages(self.user_admin))
        partner = self.env["res.partner"].create({"name": "No user"})
        attachment = IrAttachment.create(
            {"name": "Posted", "res_id": 0, "res_model": "mail.compose.message"},
        )
        with self.mock_bus():
            channel.with_user(self.user_admin).message_post(
                attachment_ids=attachment.ids,
                author_id=partner.id,
                body="Posted",
                message_type="comment",
            )
        self.assertEqual(channel.message_ids[0].attachment_ids, attachment)
        self.assertFalse(self._new_bus_notifs.filtered(lambda n: "ownership_token" in n.message))

    def test_attachment_ownership_not_sent_for_public_user(self):
        """Test the ownership token of an attachment posted by the public user is not sent on the
        bus, as all the visitors share the public user."""
        channel = self.env["discuss.channel"].create({"group_public_id": None, "name": "Public"})
        self._authenticate_pseudo_user(self.user_public)
        IrAttachment = self.env["ir.attachment"].with_user(self.user_public).sudo()
        attachment = IrAttachment.create(
            {"name": "Posted", "res_id": 0, "res_model": "mail.compose.message"},
        )
        with self.mock_bus():
            self.make_jsonrpc_request(
                "/mail/message/post",
                {
                    "post_data": {
                        "attachment_ids": attachment.ids,
                        "attachment_tokens": [attachment._get_ownership_token()],
                        "body": "Posted",
                        "message_type": "comment",
                    },
                    "thread_id": channel.id,
                    "thread_model": "discuss.channel",
                },
            )
            self.assertEqual(channel.message_ids.author_id, self.user_public.partner_id)
            self.assertEqual(channel.message_ids.attachment_ids, attachment)
            self.assertNotIn("ownership_token", "".join(self._new_bus_notifs.mapped("message")))

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
