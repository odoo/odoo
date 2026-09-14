import logging
from urllib.parse import parse_qs, urlsplit

from odoo import Command
from odoo.tests import HttpCase, common, tagged
from odoo.tools import format_datetime, mute_logger

from odoo.addons.mail.tests.common import mail_new_test_user

_logger = logging.getLogger(__name__)


@tagged("mail_message")
class TestMessageFormatPortal(common.TransactionCase):
    def test_derived_properties_do_not_require_requesting_source_fields(self):
        message = self.env["mail.message"].create(
            {
                "body": "Derived properties",
                "date": "2026-09-13 12:30:00",
                "subtype_id": self.env.ref("mail.mt_note").id,
            }
        )
        result = message._portal_message_format(
            {"is_message_subtype_note", "published_date_str"}
        )[0]
        _logger.debug("Requested derived message properties: %s", result)
        self.assertTrue(result["is_message_subtype_note"])
        self.assertEqual(
            result["published_date_str"], format_datetime(self.env, message.date)
        )
        self.assertNotIn("date", result)
        self.assertNotIn("subtype_id", result)

    def test_avatar_credentials_are_encoded_as_query_values(self):
        message = self.env["mail.message"].create({"body": "Avatar query test"})
        cases = [
            ({"token": "a+b&c?# value"}, {"access_token": ["a+b&c?# value"]}),
            (
                {"hash": "a+b&c?# value", "pid": 123},
                {"_hash": ["a+b&c?# value"], "pid": ["123"]},
            ),
        ]
        for options, expected in cases:
            with self.subTest(keys=sorted(options)):
                url = urlsplit(message._portal_format_avatar_url(message, options))
                _logger.debug(
                    "Avatar credential keys=%s fragment=%r",
                    sorted(options),
                    url.fragment,
                )
                self.assertEqual(url.fragment, "")
                self.assertEqual(parse_qs(url.query), expected)
        self.assertEqual(
            message._portal_format_avatar_url(message, {}),
            f"/web/image/mail.message/{message.id}/author_avatar/50x50",
        )

    def test_distinct_attachments_do_not_add_queries_per_message(self):
        attachments = self.env["ir.attachment"].create(
            [
                {"name": f"file-{index}.txt", "raw": b"Attachment scaling"}
                for index in range(30)
            ]
        )
        messages = self.env["mail.message"].create(
            [
                {
                    "model": "res.partner",
                    "res_id": self.env.user.partner_id.id,
                    "author_id": self.env.user.partner_id.id,
                    "attachment_ids": [Command.link(attachment.id)],
                }
                for attachment in attachments
            ]
        )

        # Warm registry/ACL metadata once, then measure cold record caches in both arms.
        messages.portal_message_format()
        costs = []
        for batch in (messages[:3], messages):
            self.env.flush_all()
            self.env.invalidate_all()
            before = self.env.cr.sql_statement_count
            formatted = batch.portal_message_format()
            costs.append(self.env.cr.sql_statement_count - before)
            returned = [message["attachment_ids"][0] for message in formatted]
            self.assertEqual(
                {attachment["id"] for attachment in returned},
                set(batch.attachment_ids.ids),
            )
            for attachment in returned:
                self.assertTrue(attachment["raw_access_token"])
                self.assertTrue(attachment["ownership_token"])
        _logger.debug(
            "Formatting 3 versus 30 distinct attachments used queries=%s", costs
        )
        self.assertLessEqual(costs[1], costs[0] + 5)

    @mute_logger("odoo.models.unlink")
    def test_portal_message_format(self):

        partner = self.env["res.partner"].create({"name": "Partner"})
        message_no_subtype = self.env["mail.message"].create(
            [
                {
                    "model": "res.partner",
                    "res_id": partner.id,
                }
            ]
        )
        formatted_result = message_no_subtype.portal_message_format()
        self.assertFalse(formatted_result[0].get("is_message_subtype_note"))

        message_comment = self.env["mail.message"].create(
            [
                {
                    "model": "res.partner",
                    "res_id": partner.id,
                    "subtype_id": self.env["ir.model.data"]._xmlid_to_res_id(
                        "mail.mt_comment"
                    ),
                }
            ]
        )
        formatted_result = message_comment.portal_message_format()
        self.assertFalse(formatted_result[0].get("is_message_subtype_note"))

        message_note = self.env["mail.message"].create(
            [
                {
                    "model": "res.partner",
                    "res_id": partner.id,
                    "subtype_id": self.env["ir.model.data"]._xmlid_to_res_id(
                        "mail.mt_note"
                    ),
                }
            ]
        )
        formatted_result = message_note.portal_message_format()
        self.assertTrue(formatted_result[0].get("is_message_subtype_note"))

    def test_portal_message_format_without_author(self):
        message = self.env["mail.message"].create(
            {
                "model": "res.partner",
                "res_id": self.env.user.partner_id.id,
                "author_id": False,
                "body": "Hello",
            }
        )
        result = message.portal_message_format()
        self.assertEqual(result[0]["author_id"], False)

    def test_shared_attachment_ownership_is_per_message(self):
        other_author = self.env["res.partner"].create({"name": "Other author"})
        attachment = self.env["ir.attachment"].create(
            {"name": "shared.txt", "raw": b"Shared attachment"}
        )
        own_message, other_message = self.env["mail.message"].create(
            [
                {
                    "model": "res.partner",
                    "res_id": self.env.user.partner_id.id,
                    "author_id": author.id,
                    "attachment_ids": [Command.link(attachment.id)],
                }
                for author in (self.env.user.partner_id, other_author)
            ]
        )

        for messages in (own_message | other_message, other_message | own_message):
            with self.subTest(order=messages.ids):
                formatted = {
                    values["id"]: values["attachment_ids"][0]
                    for values in messages.portal_message_format()
                }
                _logger.debug(
                    "Attachment ownership flags by message: %s",
                    {
                        key: "ownership_token" in value
                        for key, value in formatted.items()
                    },
                )
                self.assertIn("ownership_token", formatted[own_message.id])
                self.assertNotIn("ownership_token", formatted[other_message.id])
                self.assertIsNot(formatted[own_message.id], formatted[other_message.id])


@tagged("post_install", "-at_install")
class TestPortalAttachmentOwnershipHttp(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.owner = mail_new_test_user(
            cls.env, "portal_attachment_owner", groups="base.group_portal"
        )
        cls.other = mail_new_test_user(
            cls.env, "portal_attachment_other", groups="base.group_portal"
        )
        cls.attachment = cls.env["ir.attachment"].create(
            {
                "name": "shared.txt",
                "raw": b"Shared file",
                "res_model": "res.partner",
                "res_id": cls.owner.partner_id.id,
            }
        )
        cls.own_message, cls.other_message = cls.env["mail.message"].create(
            [
                {
                    "model": "res.partner",
                    "res_id": cls.owner.partner_id.id,
                    "message_type": "comment",
                    "subtype_id": cls.env.ref("mail.mt_comment").id,
                    "body": "Shared attachment test",
                    "author_id": author.id,
                    "attachment_ids": [Command.link(cls.attachment.id)],
                }
                for author in (cls.owner.partner_id, cls.env.user.partner_id)
            ]
        )

    def _fetch_messages(self):
        return self.call_jsonrpc(
            "/mail/chatter_fetch",
            {"thread_model": "res.partner", "thread_id": self.owner.partner_id.id},
        )

    def test_portal_response_owns_only_the_authored_message(self):
        self.authenticate(self.owner.login, self.owner.login)
        result = self._fetch_messages()
        attachments = {
            message["id"]: message["attachment_ids"][0]
            for message in result["data"]["mail.message"]
            if message["id"] in (self.own_message | self.other_message).ids
        }
        _logger.debug(
            "HTTP ownership flags: %s",
            {key: "ownership_token" in value for key, value in attachments.items()},
        )
        own_token = attachments[self.own_message.id]["ownership_token"]
        self.assertNotIn("ownership_token", attachments[self.other_message.id])
        # The capability is attachment-wide, not scoped to a message. The old
        # duplicate did not grant this reader a token absent from the response.
        self.assertEqual(own_token, self.attachment._get_ownership_token())
        self.assertTrue(
            self.attachment.with_user(self.owner)._has_attachments_ownership(
                [own_token]
            )
        )

    def test_unrelated_portal_user_cannot_fetch_messages_or_delete_file(self):
        self.authenticate(self.other.login, self.other.login)
        result = self._fetch_messages()
        self.assertFalse(
            set(result["messages"]) & set((self.own_message | self.other_message).ids)
        )
        response = self.url_open(
            "/mail/attachment/delete",
            json={"params": {"attachment_id": self.attachment.id}},
        ).json()
        _logger.debug(
            "Unrelated reader received messages=%s deletion_error=%s",
            result["messages"],
            response.get("error", {}).get("code"),
        )
        self.assertEqual(response["error"]["code"], 404)
        self.assertTrue(self.attachment.exists())
