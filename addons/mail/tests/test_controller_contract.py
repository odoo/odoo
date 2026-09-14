from unittest.mock import patch

from markupsafe import Markup

from odoo.http import Request, SessionExpiredException
from odoo.libs.guarded_http import GuardedSession
from odoo.tests import JsonRpcException, tagged

from odoo.addons.mail.controllers.webclient import WebclientController
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tests.common_controllers import (
    MailControllerAttachmentCommon,
    MailControllerCommon,
)


@tagged("-at_install", "post_install", "mail_controller")
class TestMailControllerContract(MailControllerCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.contract_user = mail_new_test_user(
            cls.env,
            login="contract_user",
            groups="base.group_user",
            name="Contract User",
        )
        cls.record = cls.env["res.partner"].create({"name": "Contract Target"})
        cls.channel = cls.env["discuss.channel"]._create_channel(
            "Contract Channel", cls.env.ref("base.group_user").id
        )

    def assertRejected(self, route, params, msg):
        self.authenticate("contract_user", "contract_user")
        with self.assertRaises(JsonRpcException, msg=msg) as capture:
            self.call_jsonrpc(route, params)
        self.assertEqual(
            capture.exception.code,
            404,
            f"{msg}: expected a 404, got {capture.exception.args[0]!r}. A non-404 here "
            f"means the route let an exception escape instead of rejecting the input.",
        )

    def test_update_content_on_message_without_a_thread(self):
        self.authenticate("contract_user", "contract_user")
        message = self.env["mail.message"].create(
            {
                "author_id": self.contract_user.partner_id.id,
                "body": "<p>no thread</p>",
                "message_type": "comment",
            }
        )
        self.assertFalse(message.model, "the fixture must have no thread model")
        self.assertRejected(
            "/mail/message/update_content",
            {"message_id": message.id, "update_data": {"body": "<p>edited</p>"}},
            "editing a message with no thread model",
        )

    def test_recipient_routes_on_an_unreachable_thread(self):
        for route in (
            "/mail/thread/recipients",
            "/mail/thread/recipients/get_suggested_recipients",
        ):
            with self.subTest(route=route):
                self.assertRejected(
                    route,
                    {"thread_model": "res.partner", "thread_id": 0x7FFFFFF},
                    f"{route} on a nonexistent thread",
                )

    def test_read_subscription_data_on_a_stale_follower(self):
        self.assertRejected(
            "/mail/read_subscription_data",
            {"follower_id": 0x7FFFFFF},
            "reading subscription data for a follower that is gone",
        )

    def test_thread_messages_on_an_unreachable_thread(self):
        self.assertRejected(
            "/mail/thread/messages",
            {"thread_model": "res.partner", "thread_id": 0x7FFFFFF},
            "fetching the messages of a thread that resolves empty",
        )

    def test_thread_messages_still_answers_for_a_reachable_thread(self):
        self.authenticate("contract_user", "contract_user")
        message = self.record.message_post(
            body=Markup("<p>on the record</p>"),
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        result = self.call_jsonrpc(
            "/mail/thread/messages",
            {"thread_model": "res.partner", "thread_id": self.record.id},
        )
        self.assertIn(
            message.id, result["messages"], "a reachable thread must still answer"
        )
        answered = self.env["mail.message"].browse(result["messages"])
        self.assertEqual(
            {(msg.model, msg.res_id) for msg in answered},
            {("res.partner", self.record.id)},
            "and must answer with its own messages, and only those",
        )

    def test_follower_routes_on_a_stale_record(self):
        for route in ("/mail/thread/subscribe", "/mail/thread/unsubscribe"):
            with self.subTest(route=route):
                self.assertRejected(
                    route,
                    {
                        "res_model": "res.partner",
                        "res_id": 0x7FFFFFF,
                        "partner_ids": [self.contract_user.partner_id.id],
                    },
                    f"{route} on a record that no longer exists",
                )

    def test_recipients_reject_a_message_from_another_thread(self):
        other = self.env["res.partner"].create({"name": "Another Thread"})
        foreign = other.message_post(
            body=Markup("<p>elsewhere</p>"),
            message_type="email",
            subtype_xmlid="mail.mt_comment",
        )
        foreign.sudo().write({"email_from": '"Outsider" <outsider@example.com>'})
        self.assertRejected(
            "/mail/thread/recipients",
            {
                "thread_model": "res.partner",
                "thread_id": self.record.id,
                "message_id": foreign.id,
            },
            "answering one thread's recipients from another thread's message",
        )

    def test_recipients_accept_a_message_of_the_thread(self):
        self.authenticate("contract_user", "contract_user")
        message = self.record.message_post(
            body=Markup("<p>from a customer</p>"),
            message_type="email",
            subtype_xmlid="mail.mt_comment",
        )
        message.sudo().write({"email_from": '"Known" <known@example.com>'})
        result = self.call_jsonrpc(
            "/mail/thread/recipients",
            {
                "thread_model": "res.partner",
                "thread_id": self.record.id,
                "message_id": message.id,
            },
        )
        self.assertIsInstance(
            result, list, "a message of this thread must still be answered"
        )

    def test_a_client_context_key_does_not_reach_the_orm(self):
        self.authenticate("admin", "admin")
        bystander = self.env["res.partner"].create({"name": "Bystander"})
        self.call_jsonrpc(
            "/mail/message/post",
            {
                "thread_model": "res.partner",
                "thread_id": self.record.id,
                "post_data": {
                    "body": "<p>hello</p>",
                    "message_type": "comment",
                    "subtype_xmlid": "mail.mt_comment",
                    "partner_ids": [bystander.id],
                },
                "context": {"mail_post_autofollow": True},
            },
        )
        self.assertNotIn(
            bystander,
            self.record.message_follower_ids.partner_id,
            "a context key the client invented changed what the post did",
        )

    def test_the_context_a_client_does_send_still_works(self):
        self.authenticate("admin", "admin")
        result = self.call_jsonrpc(
            "/mail/message/post",
            {
                "thread_model": "res.partner",
                "thread_id": self.record.id,
                "post_data": {
                    "body": "<p>with a context</p>",
                    "message_type": "comment",
                    "subtype_xmlid": "mail.mt_comment",
                },
                "context": {
                    "allowed_company_ids": self.env.company.ids,
                    "lang": "en_US",
                    "temporary_id": 0.01,
                    "tz": "Europe/Brussels",
                    "uid": self.env.ref("base.user_admin").id,
                },
            },
        )
        self.assertTrue(result["message_id"], "the post must still go through")
        self.call_jsonrpc(
            "/mail/data",
            {"fetch_params": ["init_messaging"], "context": {"active_test": False}},
        )

    def test_a_context_that_is_not_a_mapping_is_rejected(self):
        self.assertRejected(
            "/mail/data",
            {"fetch_params": ["init_messaging"], "context": ["not", "a", "dict"]},
            "fetching with a list where the context belongs",
        )

    def test_mute_rejects_unusable_durations(self):
        for minutes, label in (
            ("abc", "a non-numeric duration"),
            (10**12, "a duration that overflows datetime"),
            (-5, "a negative duration that is not the -1 sentinel"),
        ):
            with self.subTest(minutes=minutes):
                self.assertRejected(
                    "/discuss/settings/mute",
                    {"minutes": minutes, "channel_id": self.channel.id},
                    f"muting for {label}",
                )

    def test_mute_still_accepts_its_sentinels(self):
        self.authenticate("contract_user", "contract_user")
        self.call_jsonrpc(
            "/discuss/settings/mute", {"minutes": -1, "channel_id": self.channel.id}
        )
        member = self.channel.with_user(self.contract_user).self_member_id
        self.assertTrue(member.mute_until_dt, "-1 means muted forever")
        self.call_jsonrpc(
            "/discuss/settings/mute", {"minutes": 0, "channel_id": self.channel.id}
        )
        self.assertFalse(member.mute_until_dt, "0 means unmuted")

    def test_record_ids_are_not_truncated_or_coerced(self):
        for value, label in (
            (float(self.channel.id) + 0.9, "a fractional id"),
            (True, "a boolean id"),
            ("not-an-id", "a non-numeric id"),
            (None, "a null id"),
        ):
            with self.subTest(channel_id=value):
                self.assertRejected(
                    "/discuss/channel/messages",
                    {"channel_id": value},
                    f"fetching messages for {label}",
                )

    def test_a_thread_model_that_is_not_a_string_is_rejected(self):
        for value, label in (
            (["mail.test.ticket"], "a list"),
            ({"model": "mail.test.ticket"}, "a dict"),
            (42, "a number"),
            (True, "a boolean"),
        ):
            with self.subTest(thread_model=value):
                self.assertRejected(
                    "/mail/message/post",
                    {
                        "thread_model": value,
                        "thread_id": self.record.id,
                        "post_data": {"body": "hello"},
                    },
                    f"posting to {label} where the model name belongs",
                )

    def test_fetch_params_that_is_not_a_mapping_means_no_params(self):
        self.authenticate("contract_user", "contract_user")
        baseline = self.call_jsonrpc(
            "/discuss/channel/messages", {"channel_id": self.channel.id}
        )
        for value in (["search_term"], "search_term", 1.5, 7, True):
            with self.subTest(fetch_params=value):
                result = self.call_jsonrpc(
                    "/discuss/channel/messages",
                    {"channel_id": self.channel.id, "fetch_params": value},
                )
                self.assertEqual(
                    sorted(result),
                    sorted(baseline),
                    "unusable fetch_params must read as absent, not as a search",
                )
                self.assertNotIn(
                    "count",
                    result,
                    "no search was asked for, so no count is paid for",
                )

    def test_id_lists_are_rejected_whole_rather_than_narrowed(self):
        self.assertRejected(
            "/mail/thread/unsubscribe",
            {
                "res_model": "res.partner",
                "res_id": self.record.id,
                "partner_ids": [self.contract_user.partner_id.id, "junk"],
            },
            "unsubscribing with one unparseable id among valid ones",
        )

    def test_partner_from_email_rejects_a_bare_string(self):
        self.assertRejected(
            "/mail/partner/from_email",
            {
                "thread_model": "res.partner",
                "thread_id": self.record.id,
                "emails": "someone@example.com",
            },
            "resolving addresses from a string instead of a list",
        )

    def test_partner_from_email_caps_the_address_list(self):
        self.assertRejected(
            "/mail/partner/from_email",
            {
                "thread_model": "res.partner",
                "thread_id": self.record.id,
                "emails": [f"user{i}@example.com" for i in range(500)],
            },
            "resolving more addresses than the cap allows",
        )

    def test_partner_from_email_requires_access_to_the_thread_it_names(self):
        self.assertRejected(
            "/mail/partner/from_email",
            {
                "thread_model": "res.partner",
                "thread_id": 0x7FFFFFF,
                "emails": ["someone@example.com"],
            },
            "resolving addresses against a thread the caller cannot read",
        )

    def test_message_body_must_be_text(self):
        self.assertRejected(
            "/mail/message/post",
            {
                "thread_model": "res.partner",
                "thread_id": self.record.id,
                "post_data": {"body": {"not": "a string"}},
            },
            "posting a message whose body is not text",
        )

    def test_fetch_params_must_be_a_list(self):
        self.assertRejected(
            "/mail/data",
            {"fetch_params": "init_messaging"},
            "fetching with a bare string instead of a list of params",
        )

    def test_gif_favorite_routes_agree_on_what_an_id_is(self):
        for route in ("/discuss/gif/add_favorite", "/discuss/gif/remove_favorite"):
            for value, label in (({"a": 1}, "an object"), ([1], "a list")):
                with self.subTest(route=route, tenor_gif_id=value):
                    self.assertRejected(
                        route,
                        {"tenor_gif_id": value},
                        f"favouriting with {label} as the provider id",
                    )

    def test_gif_favorite_routes_still_accept_a_numeric_id(self):
        self.authenticate("contract_user", "contract_user")
        self.call_jsonrpc("/discuss/gif/add_favorite", {"tenor_gif_id": 12345})
        favorite = self.env["discuss.gif.favorite"].search(
            [("create_uid", "=", self.contract_user.id)]
        )
        self.assertEqual(favorite.tenor_gif_id, "12345", "stored as the char it is")
        self.call_jsonrpc("/discuss/gif/remove_favorite", {"tenor_gif_id": 12345})
        self.assertFalse(favorite.exists(), "and removable by the same id")

    def test_zip_route_caps_its_id_list(self):
        self.authenticate("contract_user", "contract_user")
        response = self.url_open(
            "/mail/attachment/zip",
            data={
                "file_ids": ",".join(str(i) for i in range(10_000)),
                "zip_name": "everything.zip",
                "csrf_token": Request.csrf_token(self),
            },
        )
        self.assertEqual(
            response.status_code,
            404,
            "an id list past the cap must be refused, not assembled",
        )

    def test_malformed_fetch_params_are_discarded_at_info_not_error(self):
        self.authenticate("contract_user", "contract_user")
        with self.assertNoLogs("odoo.addons.mail.controllers.webclient", level="ERROR"):
            result = self.call_jsonrpc(
                "/mail/data",
                {
                    "fetch_params": [
                        "init_messaging",
                        ["mixin.mail.thread", {"thread_model": "res.partner"}],
                        ["mixin.mail.thread", "not a mapping"],
                        [
                            "mixin.mail.thread",
                            {
                                "thread_model": ["res.partner"],
                                "thread_id": self.record.id,
                                "request_list": [],
                            },
                        ],
                        ["avatar_card", 5],
                        [42, {}],
                        [["nested"]],
                        [],
                        ["mail.canned.response", None, None, "one too many"],
                    ]
                },
            )
        self.assertIsInstance(result, dict)
        self.assertTrue(result, "the well-formed params around them are answered")

    def test_gif_search_sends_no_absent_parameter(self):
        self.env["credential.credential"]._set_system_secret(
            "discuss.klipy_api_key", "test-key"
        )
        self.authenticate("contract_user", "contract_user")
        urls = []

        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"results": []}

        def fake_request(session, method, url, **kwargs):
            urls.append(url)
            return FakeResponse()

        with patch.object(GuardedSession, "request", fake_request):
            self.call_jsonrpc("/discuss/gif/search", {"search_term": "cat"})
            self.call_jsonrpc(
                "/discuss/gif/search", {"search_term": "cat", "position": "abc"}
            )
            self.call_jsonrpc("/discuss/gif/categories", {})

        self.assertEqual(len(urls), 3)
        self.assertNotIn("pos=", urls[0], "an absent cursor must not be sent")
        self.assertNotIn("None", urls[0])
        self.assertIn("pos=abc", urls[1])
        self.assertNotIn("None", urls[2])


@tagged("-at_install", "post_install", "mail_controller")
class TestMailDataBatching(MailControllerCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.batch_user = mail_new_test_user(
            cls.env, login="batch_user", groups="base.group_user", name="Batch User"
        )

    def test_a_failing_param_does_not_take_the_batch_down(self):
        self.authenticate("batch_user", "batch_user")
        result = self.call_jsonrpc(
            "/mail/data",
            {
                "fetch_params": [
                    "init_messaging",
                    ["not_a_real_fetch_param", {}],
                    "mail.canned.response",
                ]
            },
        )
        self.assertIsInstance(result, dict, "the batch must still answer")

    def test_a_param_naming_an_unusable_model_does_not_take_the_batch_down(self):
        self.authenticate("batch_user", "batch_user")
        for thread_model, label in (
            ("no.such.model", "a model that is not in the registry"),
            ("res.currency", "a model that carries no chatter"),
        ):
            with self.subTest(thread_model=thread_model):
                result = self.call_jsonrpc(
                    "/mail/data",
                    {
                        "fetch_params": [
                            "init_messaging",
                            [
                                "mixin.mail.thread",
                                {
                                    "thread_model": thread_model,
                                    "thread_id": 1,
                                    "request_list": [],
                                },
                            ],
                        ]
                    },
                )
                self.assertIsInstance(
                    result, dict, f"a param naming {label} must not fail the batch"
                )
                self.assertTrue(result, "the params around it must still be answered")

    def test_an_expired_session_is_not_absorbed_by_the_batch(self):
        def expire(cls, store, name, params):
            raise SessionExpiredException

        self.authenticate("batch_user", "batch_user")
        with (
            patch.object(
                WebclientController, "_process_request_for_all", classmethod(expire)
            ),
            self.assertRaises(
                JsonRpcException, msg="an expired session must not be swallowed"
            ),
        ):
            self.call_jsonrpc("/mail/data", {"fetch_params": ["init_messaging"]})

    def test_the_batch_answers_the_same_data_as_isolated_params(self):
        self.authenticate("batch_user", "batch_user")
        params = ["init_messaging", "mail.canned.response"]
        batched = self.call_jsonrpc("/mail/data", {"fetch_params": params})
        isolated = self.call_jsonrpc("/mail/action", {"fetch_params": params})
        self.assertEqual(
            set(batched),
            set(isolated),
            "readonly batching must not change which models come back",
        )


@tagged("-at_install", "post_install", "mail_controller")
class TestMailControllerSecurity(MailControllerAttachmentCommon):
    def test_mail_view_does_not_reveal_a_forbidden_message_record(self):
        channel = self.env["discuss.channel"]._create_group(
            self.user_admin.partner_id.ids, name="Secret Group"
        )
        message = channel.message_post(body="secret", message_type="comment")
        self.authenticate(None, None)
        res = self.url_open(
            f"/mail/view?message_id={message.id}", allow_redirects=False
        )
        location = res.headers.get("Location", "")
        self.assertNotIn(
            f"/discuss/channel/{channel.id}",
            location,
            "anonymous /mail/view must not resolve a private message to its channel",
        )
        self.assertNotIn(f"res_id={channel.id}", location)

    def test_upload_ignores_a_forged_company_cookie(self):
        other_company = self.env["res.company"].create({"name": "Forged Co"})
        self.assertNotIn(other_company.id, self.user_employee.company_ids.ids)
        thread = self.env["res.partner"].create(
            {"name": "Company-less", "company_id": False}
        )
        self.assertFalse(
            thread._mail_get_companies()[thread.id],
            "the fixture thread must have no company so the cids branch is reached",
        )
        self.authenticate(self.user_employee.login, self.user_employee.login)
        self.opener.cookies["cids"] = str(other_company.id)
        attachment = (
            self.env["ir.attachment"].sudo().browse(self._upload_attachment(thread, {}))
        )
        self.assertNotEqual(
            attachment.company_id.id,
            other_company.id,
            "a company the user does not belong to must not be stamped from the cookie",
        )

    def test_public_user_cannot_create_a_channel_through_mail_data(self):
        self.authenticate(None, None)
        before = self.env["discuss.channel"].sudo().search_count([])
        self.call_jsonrpc(
            "/mail/data",
            {
                "fetch_params": [
                    ["/discuss/create_channel", {"name": "Sneaky", "group_id": None}]
                ]
            },
        )
        self.assertEqual(
            self.env["discuss.channel"].sudo().search_count([]),
            before,
            "a public user must not create a channel through /mail/data",
        )
