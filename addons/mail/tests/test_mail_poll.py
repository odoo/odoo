# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from pprint import pformat

from odoo import fields
from odoo.addons.mail.tests.common import freeze_all_time
from odoo.exceptions import UserError
from odoo.tests.common import HttpCase, JsonRpcException, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestMailPoll(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin = new_test_user(
            cls.env, "admin_user", groups="base.group_erp_manager,base.group_system"
        )
        cls.internal = new_test_user(cls.env, "internal", groups="base.group_user")
        cls.public = new_test_user(cls.env, "public_user", groups="base.group_public")
        cls.guest = cls.env["mail.guest"].create({"name": "Guest"})
        cls.portal = new_test_user(cls.env, "portal_user", groups="base.group_portal")

    def test_01_only_one_option_allowed_on_single_option_polls(self):
        self.authenticate(self.internal.login, self.internal.login)
        channel = self.env["discuss.channel"].create({"name": "General"})
        self.make_jsonrpc_request(
            "/mail/poll/create",
            {
                "duration": 1,
                "option_labels": ["Burger", "Pizza", "Tacos"],
                "question": "What is your favorite food?",
                "thread_id": channel.id,
                "thread_model": "discuss.channel",
            },
        )
        poll = self.env["mail.poll"].search([("start_message_id.res_id", "=", channel.id)])
        with (
            self.assertRaises(JsonRpcException) as error_catcher,
            self.assertLogs("odoo.http", level="WARNING") as log_catcher,
        ):
            self.make_jsonrpc_request(
                "/mail/poll/vote", {"poll_id": poll.id, "option_ids": poll.option_ids.ids}
            )
        self.assertEqual(error_catcher.exception.args[0], "odoo.exceptions.ValidationError")
        self.assertIn(
            'WARNING:odoo.http:Cannot vote on poll "What is your favorite food?": only one vote is allowed per user.',
            log_catcher.output,
        )
        self.make_jsonrpc_request(
            "/mail/poll/vote", {"poll_id": poll.id, "option_ids": poll.option_ids[0].ids}
        )
        self.assertIn(self.internal, poll.option_ids[0].vote_ids.user_id)

    def test_02_multiple_options_allowed_on_multi_option_polls(self):
        self.authenticate(self.internal.login, self.internal.login)
        channel = self.env["discuss.channel"].create({"name": "General"})
        self.make_jsonrpc_request(
            "/mail/poll/create",
            {
                "allow_multiple_options": True,
                "duration": 1,
                "option_labels": ["Burger", "Pizza", "Tacos"],
                "question": "What is your favorite food?",
                "thread_id": channel.id,
                "thread_model": "discuss.channel",
            },
        )
        poll = self.env["mail.poll"].search([("start_message_id.res_id", "=", channel.id)])
        self.make_jsonrpc_request(
            "/mail/poll/vote", {"poll_id": poll.id, "option_ids": poll.option_ids.ids}
        )
        self.assertIn(self.internal, poll.option_ids[0].vote_ids.user_id)
        self.assertIn(self.internal, poll.option_ids[1].vote_ids.user_id)
        self.assertIn(self.internal, poll.option_ids[2].vote_ids.user_id)

    def test_03_end_poll_after_duration(self):
        self.authenticate(self.internal.login, self.internal.login)
        channel = self.env["discuss.channel"].create({"name": "General"})
        with freeze_all_time(fields.Datetime.now() - timedelta(minutes=30)):
            self.make_jsonrpc_request(
                "/mail/poll/create",
                {
                    "duration": 60,
                    "option_labels": ["Red", "Green", "Blue"],
                    "question": "What is your favorite color?",
                    "thread_id": channel.id,
                    "thread_model": "discuss.channel",
                },
            )
            self.make_jsonrpc_request(
                "/mail/poll/create",
                {
                    "duration": 10,
                    "option_labels": ["Burger", "Pizza", "Tacos"],
                    "question": "What is your favorite food?",
                    "thread_id": channel.id,
                    "thread_model": "discuss.channel",
                },
            )
        ongoing_poll = self.env["mail.poll"].search(
            [
                ("poll_question", "=", "What is your favorite color?"),
                ("start_message_id.res_id", "=", channel.id),
            ]
        )
        expired_poll = self.env["mail.poll"].search(
            [
                ("poll_question", "=", "What is your favorite food?"),
                ("start_message_id.res_id", "=", channel.id),
            ]
        )
        self.assertFalse(ongoing_poll.end_message_id)
        self.assertFalse(expired_poll.end_message_id)
        self.env["mail.poll"]._end_expired_polls()
        self.assertFalse(ongoing_poll.end_message_id)
        self.assertTrue(expired_poll.end_message_id)

    def test_04_winning_option(self):
        self.authenticate(self.internal.login, self.internal.login)
        channel = self.env["discuss.channel"].create({"name": "General"})
        with freeze_all_time(fields.Datetime.now() - timedelta(hours=2)):
            self.make_jsonrpc_request(
                "/mail/poll/create",
                {
                    "duration": 1,
                    "option_labels": ["Burger", "Pizza", "Tacos"],
                    "question": "What is your favorite food?",
                    "thread_id": channel.id,
                    "thread_model": "discuss.channel",
                },
            )
        poll = self.env["mail.poll"].search([("start_message_id.res_id", "=", channel.id)])
        self.make_jsonrpc_request(
            "/mail/poll/vote", {"poll_id": poll.id, "option_ids": poll.option_ids[0].ids}
        )
        self.env["mail.poll"]._end_expired_polls()
        self.assertEqual(poll.winning_option_id, poll.option_ids[0])

    def test_05_no_winning_option_when_tied(self):
        self.authenticate(self.internal.login, self.internal.login)
        channel = self.env["discuss.channel"].create({"name": "General"})
        with freeze_all_time(fields.Datetime.now() - timedelta(hours=2)):
            self.make_jsonrpc_request(
                "/mail/poll/create",
                {
                    "allow_multiple_options": True,
                    "duration": 1,
                    "option_labels": ["Burger", "Pizza", "Tacos"],
                    "question": "What is your favorite food?",
                    "thread_id": channel.id,
                    "thread_model": "discuss.channel",
                },
            )
        poll = self.env["mail.poll"].search([("start_message_id.res_id", "=", channel.id)])
        self.make_jsonrpc_request(
            "/mail/poll/vote", {"poll_id": poll.id, "option_ids": poll.option_ids[:2].ids}
        )
        self.env["mail.poll"]._end_expired_polls()
        self.assertFalse(poll.winning_option_id)

    def test_06_vote_percentage_computation(self):
        self.authenticate(self.internal.login, self.internal.login)
        channel = self.env["discuss.channel"].create({"name": "General"})
        self.make_jsonrpc_request(
            "/mail/poll/create",
            {
                "allow_multiple_options": True,
                "duration": 1,
                "option_labels": ["Burger", "Pizza", "Tacos"],
                "question": "What is your favorite food?",
                "thread_id": channel.id,
                "thread_model": "discuss.channel",
            },
        )
        poll = self.env["mail.poll"].search([("start_message_id.res_id", "=", channel.id)])
        cases = [
            [{"option": poll.option_ids[0], "votes": 1, "expected_percentage": 100}],
            [
                {"option": poll.option_ids[0], "votes": 1, "expected_percentage": 50},
                {"option": poll.option_ids[1], "votes": 1, "expected_percentage": 50},
            ],
            # Remainder skipped not to skew the results.
            [
                {"option": poll.option_ids[0], "votes": 1, "expected_percentage": 33},
                {"option": poll.option_ids[1], "votes": 1, "expected_percentage": 33},
                {"option": poll.option_ids[2], "votes": 1, "expected_percentage": 33},
            ],
            [
                {"option": poll.option_ids[0], "votes": 0, "expected_percentage": 0},
                {"option": poll.option_ids[1], "votes": 0, "expected_percentage": 0},
                {"option": poll.option_ids[2], "votes": 0, "expected_percentage": 0},
            ],
            [
                {"option": poll.option_ids[0], "votes": 2, "expected_percentage": 67},
                {"option": poll.option_ids[1], "votes": 1, "expected_percentage": 33},
            ],
            [
                {"option": poll.option_ids[0], "votes": 3, "expected_percentage": 50},
                {"option": poll.option_ids[1], "votes": 2, "expected_percentage": 33},
                {"option": poll.option_ids[2], "votes": 1, "expected_percentage": 17},
            ],
        ]
        max_votes = max(sum(a["votes"] for a in case) for case in cases)
        users = self.env["res.users"].browse(
            [
                new_test_user(self.env, f"user{i}", groups="base.group_user").id
                for i in range(1, max_votes + 1)
            ]
        )
        for case in cases:
            with self.subTest(pformat(case)):
                poll.option_ids.vote_ids.unlink()
                self.env["mail.poll.vote"].create(
                    [
                        {"option_id": option_data["option"].id, "user_id": user.id}
                        for option_data in case
                        for user in users[: option_data["votes"]]
                    ]
                )
                for option_data in case:
                    self.assertEqual(
                        option_data["option"].vote_percentage, option_data["expected_percentage"]
                    )

    def test_07_cannot_vote_on_closed_polls(self):
        self.authenticate(self.internal.login, self.internal.login)
        channel = self.env["discuss.channel"].create({"name": "General"})
        with freeze_all_time(fields.Datetime.now() - timedelta(hours=2)):
            self.make_jsonrpc_request(
                "/mail/poll/create",
                {
                    "allow_multiple_options": True,
                    "duration": 1,
                    "option_labels": ["Burger", "Pizza", "Tacos"],
                    "question": "What is your favorite food?",
                    "thread_id": channel.id,
                    "thread_model": "discuss.channel",
                },
            )
        poll = self.env["mail.poll"].search([("start_message_id.res_id", "=", channel.id)])
        self.make_jsonrpc_request(
            "/mail/poll/vote", {"poll_id": poll.id, "option_ids": poll.option_ids[0].ids}
        )
        self.env["mail.poll"]._end_expired_polls()
        self.assertTrue(poll.end_message_id)
        with (
            self.assertRaises(JsonRpcException) as error_catcher,
            self.assertLogs("odoo.http", level="WARNING") as log_catcher,
        ):
            self.make_jsonrpc_request(
                "/mail/poll/vote", {"poll_id": poll.id, "option_ids": poll.option_ids[1].ids}
            )
        self.assertEqual(error_catcher.exception.args[0], "odoo.exceptions.ValidationError")
        self.assertIn(
            'WARNING:odoo.http:Cannot vote on closed poll: "What is your favorite food?"',
            log_catcher.output,
        )

    def test_08_cannot_change_option_poll(self):
        self.authenticate(self.internal.login, self.internal.login)
        general = self.env["discuss.channel"].create({"name": "General"})
        sales = self.env["discuss.channel"].create({"name": "Sales"})
        self.make_jsonrpc_request(
            "/mail/poll/create",
            {
                "duration": 1,
                "option_labels": ["Burger", "Pizza", "Tacos"],
                "question": "What is your favorite food?",
                "thread_id": general.id,
                "thread_model": "discuss.channel",
            },
        )
        self.make_jsonrpc_request(
            "/mail/poll/create",
            {
                "duration": 1,
                "option_labels": ["Red", "Green", "Blue"],
                "question": "What is your favorite color?",
                "thread_id": sales.id,
                "thread_model": "discuss.channel",
            },
        )
        general_poll = self.env["mail.poll"].search([("start_message_id.res_id", "=", general.id)])
        sales_poll = self.env["mail.poll"].search([("start_message_id.res_id", "=", sales.id)])
        with self.assertRaises(UserError) as error_catcher:
            general_poll.option_ids.poll_id = sales_poll
        self.assertEqual(
            error_catcher.exception.args[0],
            "Cannot change the poll linked to the following options: Burger, Pizza, and Tacos.",
        )

    def test_09_poll_ui(self):
        channel = self.env["discuss.channel"].create({"name": "General"})
        self.start_tour(
            f"/odoo/discuss?active_id={channel.id}",
            "mail_poll_tour.js",
            login=self.internal.login,
        )
