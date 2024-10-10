# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.tests import JsonRpcException
from odoo.addons.mail.tests.test_controller_common import TestControllerCommon


class MessagePostSubTestData:
    def __init__(
        self,
        user,
        allowed,
        /,
        *,
        partners=None,
        partner_emails=None,
        route_kw=None,
        exp_author=None,
        exp_partners=None,
        exp_emails=None,
    ):
        self.user = user if user._name == "res.users" else user.env.ref("base.public_user")
        self.guest = user if user._name == "mail.guest" else user.env["mail.guest"]
        self.allowed = allowed
        self.route_kw = {
            "context": {"mail_create_nosubscribe": True, "mail_post_autofollow": False},
            **(route_kw or {}),
        }
        if partner_emails is not None:
            self.route_kw["partner_emails"] = partner_emails
        self.post_data = {
            "body": "<p>Hello</p>",
            "message_type": "comment",
            "subtype_xmlid": "mail.mt_comment",
        }
        if partners is not None:
            self.post_data["partner_ids"] = partners.ids
        self.exp_author = exp_author
        self.exp_partners = exp_partners
        self.exp_emails = exp_emails


@odoo.tests.tagged("-at_install", "post_install")
class TestThreadControllerCommon(TestControllerCommon):
    def _execute_message_post_subtests(self, record, tests: list[MessagePostSubTestData]):
        for test in tests:
            self._authenticate_user(user=test.user, guest=test.guest)
            with self.subTest(
                record=record, user=test.user.name, guest=test.guest.name, route_kw=test.route_kw
            ):
                if test.allowed:
                    self._message_post(record, test.post_data, test.route_kw)
                    message = self._find_messages(record, limit=1)
                    self.assertTrue(message)
                    if test.guest and not test.exp_author:
                        self.assertEqual(message.author_guest_id, test.guest)
                    else:
                        self.assertEqual(message.author_id, test.exp_author or test.user.partner_id)
                    if test.exp_partners is not None:
                        self.assertEqual(message.partner_ids, test.exp_partners)
                    if test.exp_emails is not None:
                        self.assertEqual(message.partner_ids.mapped("email"), test.exp_emails)
                else:
                    with self.assertRaises(JsonRpcException, msg="werkzeug.exceptions.NotFound"):
                        self._message_post(record, test.post_data, test.route_kw)

    def _message_post(self, record, post_data, route_kw):
        self.make_jsonrpc_request(
            route="/mail/message/post",
            params={
                "thread_model": record._name,
                "thread_id": record.id,
                "post_data": post_data,
                **route_kw,
            },
        )

    def _find_messages(self, record, limit=30):
        return self.env["mail.message"].search(
            [("res_id", "=", record.id), ("model", "=", record._name)], order="id desc", limit=limit
        )

    def _execute_message_fetch_subtests(self, record, subtests):
        for data_user, allowed, *args in subtests:
            route_kw = args[0] if args else {}
            user = data_user if data_user._name == "res.users" else self.user_public
            guest = data_user if data_user._name == "mail.guest" else self.env["mail.guest"]
            self._create_records(record)
            messages = self._find_messages(record)
            self._authenticate_user(user=user, guest=guest)
            with self.subTest(record=record, user=user, guest=guest, route_kw=route_kw):
                if allowed:
                    if allowed == "all":
                        self.assertEqual(
                            len(self._message_fetch(record, route_kw)["messages"]), len(messages)
                        )
                    elif allowed == "only_comments":
                        route_kw["portal"] = True
                        fetched_data = self._message_fetch(record, route_kw)
                        self.assertNotEqual(len(fetched_data["messages"]), len(messages))
                        self.assertEqual(len(fetched_data["messages"]), 1)
                        self.assertEqual(fetched_data["data"]["mail.message"][0].get("is_note"),
                                         False)

                else:
                    with self.assertRaises(
                            JsonRpcException, msg="Fetch messages should raise NotFound"
                    ):
                        self._message_fetch(record, route_kw)
            messages.unlink()

    def _message_fetch(self, record, route_kw):
        return self.make_jsonrpc_request(
            route="/mail/thread/messages",
            params={
                "thread_model": record._name,
                "thread_id": record.id,
                **route_kw,
            },
        )

    def _create_records(self, record):
        self.authenticate(self.user_admin.login, self.user_admin.login)
        self._message_post(
            record,
            {
                "body": "<p>Test comment</p>",
                "message_type": "comment",
                "subtype_xmlid": "mail.mt_comment",
            },
            {},
        )
        self._message_post(
            record,
            {
                "body": "<p>Test note</p>",
                "message_type": "comment",
                "subtype_xmlid": "mail.mt_note",
            },
            {},
        )


@odoo.tests.tagged("-at_install", "post_install")
class TestThreadController(TestThreadControllerCommon):
    def test_partner_message_post_access(self):
        """Test access of message_post on partner record."""
        record = self.env["res.partner"].create({"name": "Test Partner"})

        def test_access(user, allowed):
            return MessagePostSubTestData(user, allowed)

        self._execute_message_post_subtests(
            record,
            (
                test_access(self.user_public, False),
                test_access(self.guest, False),
                test_access(self.user_portal, False),
                # False because not base.group_partner_manager
                test_access(self.user_employee, False),
                test_access(self.user_demo, True),
                test_access(self.user_admin, True),
            ),
        )

    def test_partner_message_post_partner_ids(self):
        """Test partner_ids of message_post on partner record."""
        record = self.env["res.partner"].create({"name": "Test Partner"})
        partners = (
            self.user_portal + self.user_employee + self.user_demo + self.user_admin
        ).partner_id
        no_partner = self.env["res.partner"]

        def test_partners(user, allowed, exp_partners):
            return MessagePostSubTestData(
                user, allowed, partners=partners, exp_partners=exp_partners
            )

        self._execute_message_post_subtests(
            record,
            (
                test_partners(self.user_public, False, no_partner),
                test_partners(self.guest, False, no_partner),
                test_partners(self.user_portal, False, no_partner),
                # False because not base.group_partner_manager
                test_partners(self.user_employee, False, no_partner),
                test_partners(self.user_demo, True, partners),
                test_partners(self.user_admin, True, partners),
            ),
        )

    def test_partner_message_fetch_access(self):
        """Test access of fetching messages on a partner record."""
        record = self.env["res.partner"].create({"name": "Test Partner"})
        self._execute_message_fetch_subtests(
            record,
            (
                (self.user_public, False),
                (self.guest, False),
                (self.user_portal, False),
                (self.user_employee, "all"),
                (self.user_demo, "all"),
                (self.user_admin, "all"),

            ),
        )
