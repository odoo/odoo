from ast import literal_eval
import base64
import json

from odoo.addons.mail.tests.common_controllers import MailControllerThreadCommon
from odoo.tests import JsonRpcException, tagged
from odoo.tools import mute_logger


@tagged("-at_install", "post_install", "mail_controller")
class TestMessageController(MailControllerThreadCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_public_record = cls.env["mail.test.access.public"].create({"name": "Public Channel", "email": "john@test.be", "mobile": "+32455001122"})

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
                "csrf_token": self.csrf_token(),
                "thread_id": archived_partner.id,
                "thread_model": "res.partner",
            },
            files={"ufile": b""},
        )
        self.assertEqual(response.status_code, 200)

    def test_thread_post_no_access(self):
        """Test the case where the user tries to upload on a record he can't access."""
        self.authenticate(self.user_admin.login, self.user_admin.login)
        partner = self.env["res.partner"].create({"name": "partner"})

        self.env['ir.access'].create({
            'name': 'Access Partner',
            'model_id': self.env.ref('base.model_res_partner').id,
            'operation': 'crud',
            'domain': f"[('id', '!=', {partner.id})]",
        })
        self.authenticate(self.user_employee.login, self.user_employee.login)

        response = self.url_open(
            "/mail/attachment/upload",
            {
                "csrf_token": self.csrf_token(),
                "thread_id": partner.id,
                "thread_model": "res.partner",
            },
            files={"ufile": base64.b64decode(b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")},
        )
        self.assertEqual(response.status_code, 404)

    def test_mail_message_post(self):
        """Test sending a mail with the controller using "Cc"."""
        self.authenticate(self.user_employee.login, self.user_employee.login)
        test_record = self.env["res.partner"].create({"name": "partner"})
        partner_to1, partner_cc1, partner_to2, partner_cc2 = self.env['res.partner'].create([
            {'name': f'partner{name}', 'email': f'test_mail_message_post_{name}@ex.com'}
            for name in ('to1', 'cc1', 'to2', 'cc2')])
        partner_to = partner_to1 | partner_to2
        partner_cc = partner_cc1 | partner_cc2

        data = self.make_jsonrpc_request("/mail/message/post", {
            "thread_model": "res.partner",
            "thread_id": test_record.id,
            "post_data": {
                "body": "Test message",
                "partner_ids": partner_to.ids,
                "partner_cc_ids": partner_cc.ids,
            }
        })
        message = next(filter(lambda m: m["id"] == data["message_id"], data["store_data"]["mail.message"]))
        self.assertEqual(message['partner_ids'], partner_to.ids)
        self.assertEqual(message['partner_cc_ids'], partner_cc.ids)
        mail = self.env['mail.mail'].search([('mail_message_id', '=', message['id'])], limit=1)
        self.assertEqual(len(mail), 1)
        header = literal_eval(mail.headers)
        self.assertEqual(header.get('X-Msg-Cc-Add'), ','.join(partner_cc.mapped('email_formatted')))


@tagged("mail_controller")
class TestFollowersController(MailControllerThreadCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_public_record = (
            cls.env["mail.test.access.public"]
            .with_context(
                mail_create_nosubscribe=True,
            )
            .create({"name": "Test Followers"})
        )
        cls.partners = cls.env["res.partner"].create(
            [
                {"name": "Zebra", "email": "zebra@example.com"},
                {"name": "Alpha", "email": "first@example.com"},
                {"name": "Alpha", "email": "second@example.com"},
                {"name": "Bravo", "email": "unique@example.com"},
            ],
        )
        # Reverse the Alpha partners so the tie-break must use follower IDs.
        cls.followers = cls.env["mail.followers"].create(
            [
                {
                    "res_model": cls.test_public_record._name,
                    "res_id": cls.test_public_record.id,
                    "partner_id": partner.id,
                }
                for partner in (
                    cls.partners[0],
                    cls.partners[2],
                    cls.partners[1],
                    cls.partners[3],
                )
            ],
        )
        cls.self_follower = cls.env["mail.followers"].create(
            {
                "res_model": cls.test_public_record._name,
                "res_id": cls.test_public_record.id,
                "partner_id": cls.user_employee.partner_id.id,
            },
        )
        cls.expected_follower_ids = [
            cls.followers[1].id,
            cls.followers[2].id,
            cls.followers[3].id,
            cls.followers[0].id,
        ]

    def _fetch_followers(self, thread=None, **kwargs):
        thread = self.test_public_record if thread is None else thread
        return self.make_jsonrpc_request(
            "/mail/thread/followers",
            {
                "thread_model": thread._name,
                "thread_id": thread.id,
                **kwargs,
            },
        )

    @mute_logger("odoo.http")
    def test_thread_followers_access(self):
        restricted = self.env["mail.test.access"].create(
            {"name": "Restricted", "access": "admin"},
        )
        self.authenticate(self.user_employee.login, self.user_employee.login)
        self.assertTrue(self._fetch_followers()["follower_ids"])
        with self.assertRaises(JsonRpcException, msg="werkzeug.exceptions.NotFound"):
            self._fetch_followers(restricted)
        missing_thread = self.test_public_record.browse(self.test_public_record.id)
        missing_thread.unlink()
        with self.assertRaises(JsonRpcException, msg="werkzeug.exceptions.NotFound"):
            self._fetch_followers(missing_thread)

    def test_thread_followers_name_id_order(self):
        self.authenticate(self.user_employee.login, self.user_employee.login)
        self.assertEqual(
            self._fetch_followers()["follower_ids"], self.expected_follower_ids,
        )

    def test_thread_followers_offset(self):
        self.authenticate(self.user_employee.login, self.user_employee.login)
        for offset, expected_ids, has_count in (
            (0, self.expected_follower_ids[:2], True),
            (2, self.expected_follower_ids[2:], False),
            (3, self.expected_follower_ids[3:], True),
            (4, [], True),
        ):
            with self.subTest(offset=offset):
                result = self._fetch_followers(offset=offset, limit=2)
                self.assertEqual(result["follower_ids"], expected_ids)
                thread_data = result["store_data"].get("mail.thread", [{}])[0]
                if has_count:
                    self.assertEqual(thread_data["followersCount"], 5)
                else:
                    self.assertNotIn("followersCount", thread_data)

    def test_thread_followers_excludes_current_user(self):
        self.authenticate(self.user_employee.login, self.user_employee.login)
        result = self._fetch_followers()
        self.assertNotIn(self.self_follower.id, result["follower_ids"])
        result = self._fetch_followers(search_term=self.user_employee.email)
        self.assertEqual(result["follower_ids"], [])

    def test_thread_followers_search_name_email(self):
        self.authenticate(self.user_employee.login, self.user_employee.login)
        for term, expected_ids in (
            ("aLP", self.expected_follower_ids[:2]),
            ("UNIQUE@", [self.followers[3].id]),
            ("no-match", []),
            ("", self.expected_follower_ids),
        ):
            with self.subTest(search_term=term):
                result = self._fetch_followers(search_term=term)
                self.assertEqual(result["follower_ids"], expected_ids)
                if term in ("aLP", "no-match"):
                    self.assertEqual(
                        result["store_data"]["mail.thread"][0]["followersCount"], 5,
                    )
        result = self._fetch_followers(search_term="Alpha", offset=1, limit=1)
        self.assertEqual(result["follower_ids"], [self.followers[2].id])
