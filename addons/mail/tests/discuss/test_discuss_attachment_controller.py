# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

import odoo
from odoo.addons.bus.tests.common import BusResult
from odoo.addons.mail.tests.common_controllers import MailControllerAttachmentCommon
from odoo.addons.mail.tools.discuss import Store
from odoo.tools.misc import file_open


@odoo.tests.tagged("mail_controller")
class TestDiscussAttachmentController(MailControllerAttachmentCommon):
    def _new_message_payload(self, channel, message, attachments):
        store_data = (
            Store(bus_channel=channel)
            .add(message, "_store_message_fields")
            .add(message, {"attachment_ids": attachments.ids})
            ._build_result()
        )
        self.assertFalse(
            [vals for vals in store_data["ir.attachment"] if "ownership_token" in vals],
        )
        return {"id": channel.id, "store_data": store_data}

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
                (self.user_public, False),
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
        channel = self.env["discuss.channel"].create({"name": "Group", "channel_type": "group"})
        channel._add_members(guests=self.guest, users=self.user_portal)
        for pseudo_user, now in (
            (self.guest, "2026-01-01 10:00:00"),
            (self.user_portal, "2026-01-01 11:00:00"),
        ):
            user, guest = self._authenticate_pseudo_user(pseudo_user)
            persona = guest or user
            IrAttachment = self.env["ir.attachment"].with_user(user).sudo()
            posted, added = IrAttachment.create(
                [
                    {"name": "Posted", "res_id": 0, "res_model": "mail.compose.message"},
                    {"name": "Added", "res_id": 0, "res_model": "mail.compose.message"},
                ],
            )
            with self.subTest(author=persona.name), freeze_time(now):

                def post_notifications():
                    message = self.env["mail.message"].browse(message_id)
                    member = channel.channel_member_ids.filtered(
                        lambda m: (m.guest_id or m.partner_id) == (guest or user.partner_id),
                    )
                    return [
                        BusResult(
                            channel,
                            "mail.record/insert",
                            Store().add(channel, ["last_interest_dt"]),
                        ),
                        BusResult(
                            persona,
                            "mail.record/insert",
                            Store().add(
                                member,
                                lambda res: (
                                    res.from_method("_store_identifying_fields"),
                                    res.extend(["message_unread_counter", "new_message_separator"]),
                                    res.attr("message_unread_counter_bus_id", 0),
                                ),
                            ),
                        ),
                        BusResult(
                            channel,
                            "discuss.channel/new_message",
                            self._new_message_payload(channel, message, posted),
                        ),
                        BusResult(
                            persona,
                            "mail.record/insert",
                            Store().add(posted, "_store_ownership_fields"),
                        ),
                    ]

                with self.assertBus(post_notifications):
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
                message = self.env["mail.message"].browse(message_id)
                with self.assertBus(
                    lambda: [
                        BusResult(
                            channel,
                            "mail.record/insert",
                            Store(bus_channel=channel)
                            .add(posted + added, "_store_attachment_fields")
                            .add(
                                message,
                                [
                                    "body",
                                    "parent_id",
                                    "partner_ids",
                                    "pinned_at",
                                    "subject",
                                    "write_date",
                                ],
                            )
                            .add(
                                message,
                                {"attachment_ids": (posted + added).ids, "translationValue": False},
                            )
                            ._build_result(),
                        ),
                        BusResult(
                            persona,
                            "mail.record/insert",
                            Store().add(posted + added, "_store_ownership_fields"),
                        ),
                    ],
                ):
                    self.make_jsonrpc_request(
                        "/mail/message/update_content",
                        {
                            "message_id": message_id,
                            "update_data": {
                                "attachment_ids": (posted + added).ids,
                                "attachment_tokens": [
                                    posted._get_ownership_token(),
                                    added._get_ownership_token(),
                                ],
                                "body": "Edited",
                            },
                        },
                    )
                self.make_jsonrpc_request(
                    "/mail/attachment/delete",
                    {
                        "access_token_by_attachment_id": {
                            posted.id: posted._get_ownership_token(),
                            added.id: added._get_ownership_token(),
                        },
                    },
                )
                self.assertFalse((posted + added).exists())

    @freeze_time("2026-01-01 10:00:00")
    def test_attachment_ownership_sent_to_author(self):
        """Test the ownership token of an attachment is sent to the author of the message, and not
        to the user who posts it on their behalf, nor to an author without user."""
        channel = self.env["discuss.channel"].create({"name": "Group", "channel_type": "group"})
        channel._add_members(users=self.user_portal)
        IrAttachment = self.env["ir.attachment"].with_user(self.user_admin)
        attachment = IrAttachment.create(
            {"name": "Posted", "res_id": 0, "res_model": "mail.compose.message"},
        )

        def new_message(attachment):
            message = channel.message_ids[0]
            return BusResult(
                channel,
                "discuss.channel/new_message",
                self._new_message_payload(channel, message, attachment),
            )

        with self.assertBus(
            lambda: [
                BusResult(
                    channel,
                    "mail.record/insert",
                    Store().add(channel, ["last_interest_dt"]),
                ),
                new_message(attachment),
                BusResult(
                    self.user_portal,
                    "mail.record/insert",
                    Store().add(attachment, "_store_ownership_fields"),
                ),
            ],
        ):
            channel.with_user(self.user_admin).message_post(
                attachment_ids=attachment.ids,
                author_id=self.user_portal.partner_id.id,
                body="Posted",
                message_type="comment",
            )
        partner = self.env["res.partner"].create({"name": "No user"})
        attachment = IrAttachment.create(
            {"name": "Posted", "res_id": 0, "res_model": "mail.compose.message"},
        )
        with self.assertBus(lambda: [new_message(attachment)]):
            channel.with_user(self.user_admin).message_post(
                attachment_ids=attachment.ids,
                author_id=partner.id,
                body="Posted",
                message_type="comment",
            )
        self.assertEqual(channel.message_ids[0].attachment_ids, attachment)

    def test_attachment_ownership_not_sent_for_public_user(self):
        """Test the ownership token of an attachment posted by the public user is not sent on the
        bus, as all the visitors share the public user."""
        channel = self.env["discuss.channel"].create({"group_public_id": None, "name": "Public"})
        IrAttachment = self.env["ir.attachment"].with_user(self.user_public).sudo()
        attachment = IrAttachment.create(
            {"name": "Posted", "res_id": 0, "res_model": "mail.compose.message"},
        )

        def notifications():
            message = channel.with_user(self.user_public).sudo().message_ids
            return [
                BusResult(
                    channel,
                    "mail.record/insert",
                    Store().add(channel, ["last_interest_dt"]),
                ),
                BusResult(
                    channel,
                    "discuss.channel/new_message",
                    self._new_message_payload(channel, message, attachment),
                ),
            ]

        with self.assertBus(notifications):
            channel.with_user(self.user_public).sudo().message_post(
                attachment_ids=attachment.ids,
                body="Posted",
                message_type="comment",
            )
        self.assertEqual(channel.message_ids.author_id, self.user_public.partner_id)
        self.assertEqual(channel.message_ids.attachment_ids, attachment)

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
