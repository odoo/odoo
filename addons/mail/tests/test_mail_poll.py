# Part of Odoo. See LICENSE file for full copyright and licensing details.

from pprint import pformat

from odoo.tests.common import HttpCase, JsonRpcException, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestMailPoll(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.internal = new_test_user(cls.env, "internal", groups="base.group_user")

    def test_only_one_option_allowed_on_single_option_polls(self):
        self.authenticate(self.internal.login, self.internal.login)
        channel = self.env["discuss.channel"].create({"name": "General"})
        poll_id = self.make_jsonrpc_request(
            "/mail/poll/create",
            {
                "duration": 1,
                "option_labels": ["Burger", "Pizza", "Tacos"],
                "question": "What is your favorite food?",
                "thread_id": channel.id,
                "thread_model": "discuss.channel",
            },
        )
        poll = self.env["mail.poll"].search([("id", "=", poll_id)])
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

    def test_multiple_options_allowed_on_multi_option_polls(self):
        self.authenticate(self.internal.login, self.internal.login)
        channel = self.env["discuss.channel"].create({"name": "General"})
        poll_id = self.make_jsonrpc_request(
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
        poll = self.env["mail.poll"].search([("id", "=", poll_id)])
        self.make_jsonrpc_request(
            "/mail/poll/vote", {"poll_id": poll.id, "option_ids": poll.option_ids.ids}
        )
        self.assertIn(self.internal, poll.option_ids[0].vote_ids.user_id)
        self.assertIn(self.internal, poll.option_ids[1].vote_ids.user_id)
        self.assertIn(self.internal, poll.option_ids[2].vote_ids.user_id)

    def test_vote_percentage_computation(self):
        self.authenticate(self.internal.login, self.internal.login)
        channel = self.env["discuss.channel"].create({"name": "General"})
        poll_id = self.make_jsonrpc_request(
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
        poll = self.env["mail.poll"].search([("id", "=", poll_id)])
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

    def test_poll_ui(self):
        channel = self.env["discuss.channel"].create({"name": "General"})
        self.start_tour(
            f"/odoo/discuss?active_id={channel.id}",
            "mail_poll_tour.js",
            login=self.internal.login,
        )
