import json

from requests.exceptions import HTTPError

from odoo import http
from odoo.addons.mail.tests.common_controllers import MailControllerThreadCommon
from odoo.tests import JsonRpcException, tagged
from odoo.tools import mute_logger


@tagged("-at_install", "post_install", "mail_controller")
class TestMessageController(MailControllerThreadCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_public_record = cls.env["mail.test.access.public"].create({"name": "Public Channel", "email": "john@test.be", "mobile": "+32455001122"})
        admin_records = cls.env["mail.test.access"].create(
            [
                {"access": "admin", "name": "Admin Record"},
                {"access": "admin", "name": "Other Admin Record"},
                {"access": "admin", "name": "Followed Admin Record"},
            ],
        )
        cls.test_admin_record, test_admin_record_other, cls.test_followed_record = admin_records
        cls.test_followed_record.message_subscribe(cls.user_employee.partner_id.ids)
        cls.message_followed = cls.test_followed_record.message_post(
            body="Hello",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        cls.message_notified = cls.test_admin_record.message_post(
            body="Hello",
            message_type="comment",
            partner_ids=cls.user_employee.partner_id.ids,
            subtype_xmlid="mail.mt_comment",
        )
        cls.message_not_notified = cls.test_admin_record.message_post(
            body="Hello",
            message_type="comment",
        )
        cls.message_note = cls.test_admin_record.message_post(
            body="Hello",
            message_type="comment",
            partner_ids=cls.user_employee.partner_id.ids,
            subtype_xmlid="mail.mt_note",
        )
        cls.message_other_record = test_admin_record_other.message_post(
            body="Hello",
            message_type="comment",
            partner_ids=cls.user_employee.partner_id.ids,
        )
        cls.test_group = cls.env["discuss.channel"]._create_group(cls.user_employee.partner_id.ids)
        cls.message_left_group = cls.test_group.message_post(
            body="Hello",
            message_type="comment",
            partner_ids=cls.user_employee.partner_id.ids,
        )
        cls.test_group._action_unfollow(partner=cls.user_employee.partner_id)

    @mute_logger("odoo.http")
    def test_thread_attachment_hijack(self):
        att = self.env["ir.attachment"].create({
            "name": "arguments_for_firing_marc_demo",
            "res_id": 0,
            "res_model": "mail.compose.message",
        })
        self.authenticate(self.user_employee.login, self.user_employee.login)
        record = self.env["mail.test.access.public"].create({"name": "Public Channel"})
        record.with_user(self.user_employee).write({'name': 'updated'})  # can access, update, ...
        # if this test breaks, it might be due to a change in /web/content, or the default rules for accessing an attachment. This is not an issue but it makes this test irrelevant.
        self.assertFalse(self.url_open(f"/web/content/{att.id}").ok)
        response = self.url_open(
            url="/mail/message/post",
            headers={"Content-Type": "application/json"},  # route called as demo
            data=json.dumps(
                {
                    "params": {
                        "post_data": {
                            "attachment_ids": [att.id],  # demo does not have access to this attachment id
                            "body": "",
                            "message_type": "comment",
                            "partner_ids": [],
                            "subtype_xmlid": "mail.mt_comment",
                        },
                        "thread_id": record.id,
                        "thread_model": record._name,
                    }
                },
            ),
        )
        self.assertNotIn(
            "arguments_for_firing_marc_demo", response.text
        )  # demo should not be able to see the name of the document

    def test_thread_partner_from_email_authenticated(self):
        self.authenticate(self.user_employee.login, self.user_employee.login)
        res3 = self.url_open(
            url="/mail/partner/from_email",
            data=json.dumps(
                {
                    "params": {
                        "thread_model": self.test_public_record._name,
                        "thread_id": self.test_public_record.id,
                        "emails": ["john@test.be"],
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res3.status_code, 200)
        self.assertEqual(
            1,
            self.env["res.partner"].search_count([('email', '=', "john@test.be"), ('phone', '=', "+32455001122")]),
            "authenticated users can create a partner from an email",
        )
        # should not create another partner with same email
        res4 = self.url_open(
            url="/mail/partner/from_email",
            data=json.dumps(
                {
                    "params": {
                        "thread_model": self.test_public_record._name,
                        "thread_id": self.test_public_record.id,
                        "emails": ["john@test.be"],
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res4.status_code, 200)
        self.assertEqual(
            1,
            self.env["res.partner"].search_count([('email', '=', "john@test.be")]),
            "'mail/partner/from_email' does not create another user if there's already a user with matching email",
        )

        self.test_public_record.write({'email': 'john2@test.be'})
        res5 = self.url_open(
            url="/mail/message/post",
            data=json.dumps(
                {
                    "params": {
                        "thread_model": self.test_public_record._name,
                        "thread_id": self.test_public_record.id,
                        "post_data": {
                            "body": "test",
                            "partner_emails": ["john2@test.be"],
                        },
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res5.status_code, 200)
        self.assertEqual(
            1,
            self.env["res.partner"].search_count([('email', '=', "john2@test.be"), ('phone', '=', "+32455001122")]),
            "authenticated users can create a partner from an email from message_post",
        )
        # should not create another partner with same email
        res6 = self.url_open(
            url="/mail/message/post",
            data=json.dumps(
                {
                    "params": {
                        "thread_model": self.test_public_record._name,
                        "thread_id": self.test_public_record.id,
                        "post_data": {
                            "body": "test",
                            "partner_emails": ["john2@test.be"],
                        },
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res6.status_code, 200)
        self.assertEqual(
            1,
            self.env["res.partner"].search_count([('email', '=', "john2@test.be")]),
            "'mail/message/post' does not create another user if there's already a user with matching email",
        )

    def test_thread_post_archived_record(self):
        self.authenticate(self.user_employee.login, self.user_employee.login)
        archived_partner = self.env["res.partner"].create({"name": "partner", "active": False})

        # 1. posting a message
        data = self.make_jsonrpc_request("/mail/message/post", {
            "thread_model": "res.partner",
            "thread_id": archived_partner.id,
            "post_data": {
                "body": "A great message",
            }
        })
        message = next(filter(lambda m: m["id"] == data["message_id"], data["store_data"]["mail.message"]))
        self.assertEqual(["markup", "<p>A great message</p>"], message["body"])

        # 2. attach a file
        response = self.url_open(
            "/mail/attachment/upload",
            {
                "csrf_token": http.Request.csrf_token(self),
                "thread_id": archived_partner.id,
                "thread_model": "res.partner",
            },
            files={"ufile": b""},
        )
        self.assertEqual(response.status_code, 200)

    @mute_logger("odoo.http")
    def test_thread_post_reply_to_notified_message(self):
        self.assertFalse(self.test_admin_record.with_user(self.user_employee).has_access("read"))
        for message in (self.message_followed, self.message_left_group):
            self.assertIn(self.user_employee.partner_id, message.notification_ids.res_partner_id)
        self.authenticate(self.user_employee.login, self.user_employee.login)
        post_data = {"body": "Reply", "message_type": "comment"}
        for thread, parent, subtype_xmlid in (
            (self.test_admin_record, self.message_notified, "mail.mt_comment"),
            (self.test_admin_record, self.message_note, "mail.mt_note"),
            (self.test_followed_record, self.message_followed, "mail.mt_comment"),
        ):
            with self.subTest(thread=thread, parent=parent):
                attachment = self._upload_reply_attachment(thread, parent)
                message = self._message_post(
                    thread,
                    {
                        **post_data,
                        "attachment_ids": attachment.ids,
                        "attachment_tokens": [attachment._get_ownership_token()],
                        "parent_id": parent.id,
                        "subtype_xmlid": subtype_xmlid,
                    },
                    {},
                )
                self.assertEqual(message.attachment_ids, attachment)
                self.assertEqual(message.author_id, self.user_employee.partner_id)
                self.assertEqual(message.body, "<p>Reply</p>")
                self.assertEqual(message.subtype_id, self.env.ref(subtype_xmlid))
        with self.assertRaisesRegex(HTTPError, "404"):
            self._upload_reply_attachment(self.test_admin_record, self.message_notified, "false")
        self.assertNotIn(self.user_employee.partner_id, self.test_admin_record.message_partner_ids)
        for thread, parent in (
            (self.test_admin_record, self.message_not_notified),
            (self.test_admin_record, self.message_other_record),
            (self.test_group, self.message_left_group),
        ):
            with self.subTest(thread=thread, parent=parent):
                with self.assertRaisesRegex(JsonRpcException, "werkzeug.exceptions.NotFound"):
                    self._message_post(thread, {**post_data, "parent_id": parent.id}, {})
                with self.assertRaisesRegex(HTTPError, "404"):
                    self._upload_reply_attachment(thread, parent)

    def _upload_reply_attachment(self, thread, parent, is_pending="true"):
        response = self.url_open(
            "/mail/attachment/upload",
            {
                "csrf_token": http.Request.csrf_token(self),
                "is_pending": is_pending,
                "parent_id": parent.id,
                "thread_id": thread.id,
                "thread_model": thread._name,
            },
            files={"ufile": b"Reply"},
        )
        response.raise_for_status()
        return self.env["ir.attachment"].browse(response.json()["data"]["attachment_id"])
