# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from freezegun import freeze_time
from unittest.mock import patch

from odoo import Command
from odoo import fields
from odoo.addons.im_livechat.tests.common import TestImLivechatCommon
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests.common import new_test_user

REPORTING_FIELDS = [
    "duration",
    "livechat_call_duration_hour",
    "livechat_call_count",
    "livechat_call_percentage",
    "livechat_chatbot_answers_path",
    "livechat_chatbot_answers_path_str",
    "livechat_chatbot_script_id",
    "livechat_handled_by_agent",
    "livechat_handled_by_bot",
    "livechat_handler_partner_id",
    "livechat_has_call",
    "livechat_message_count",
    "livechat_rating_percentage",
    "livechat_response_time_hour",
    "livechat_start_date_minutes",
    "livechat_start_hour",
    "livechat_visitor_partner_id",
    "livechat_week_day",
]


class TestImLivechatReport(TestImLivechatCommon):
    def setUp(self):
        super().setUp()
        self.env['discuss.channel'].search([('livechat_channel_id', '!=', False)]).unlink()

        def _compute_available_operator_ids(channel_self):
            for record in channel_self:
                record.available_operator_ids = self.operators
        with (
            patch.object(
                self.registry["im_livechat.channel"],
                "_compute_available_operator_ids",
                _compute_available_operator_ids,
            ),
            freeze_time("2023-03-17 06:05:54"),
        ):
            channel_id = self.make_jsonrpc_request(
                "/im_livechat/get_session",
                {"channel_id": self.livechat_channel.id},
            )["channel_id"]

        self.channel = self.env['discuss.channel'].browse(channel_id)
        self.operator = self.env["im_livechat.channel.member.history"].search([
            ("channel_id", "=", self.channel.id),
            ("livechat_member_type", "=", "agent"),
        ]).partner_id

        self._create_message(self.channel, self.visitor_user.partner_id, '2023-03-17 06:06:59')
        self._create_message(self.channel, self.operator, '2023-03-17 08:15:54')
        self._create_message(self.channel, self.operator, '2023-03-17 08:45:54')

        # message with the same record id, but with a different model
        # should not be taken into account for statistics
        partner_message = self._create_message(self.channel, self.operator, '2023-03-17 05:05:54')
        partner_message |= self._create_message(self.channel, self.operator, '2023-03-17 09:15:54')
        partner_message.model = 'res.partner'

        with freeze_time("2023-03-17 09:20:54"):
            self.make_jsonrpc_request(
                "/im_livechat/visitor_leave_session",
                {"channel_id": channel_id}
            )
        self.env['mail.message'].flush_model()

    def test_livechat_session_measures(self):
        sessions = self.env["discuss.channel"].search(
            [("livechat_channel_id", "=", self.livechat_channel.id)],
        )
        self.assertEqual(len(sessions), 1, "Should have one session for this live chat channel")
        # We have those messages, ordered by creation;
        # 05:05:54: wrong model
        # 06:05:54: session create
        # 06:06:59: visitor message
        # 08:15:54: operator first answer
        # 08:45:54: operator second answer
        # 09:15:54: wrong model
        # So the duration of the session is: (09:20:54 - 06:05:54) = 3h15
        # The response time of this session is: (08:15:54 - 06:05:54) = 2h10 = 7800 seconds
        self.assertEqual(sessions.livechat_response_time_hour, 7800 / 3600)
        self.assertEqual(sessions.duration, 11700 / 3600)

    def test_livechat_session_aggregates(self):
        result = self.env["discuss.channel"].formatted_read_group(
            [("channel_type", "=", "livechat")],
            aggregates=["livechat_response_time_hour:avg", "duration:avg"],
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["livechat_response_time_hour:avg"], 7800 / 3600)
        self.assertEqual(result[0]["duration:avg"], 11700 / 3600)
        rated_channel_id = self.make_jsonrpc_request(
            "/im_livechat/get_session", {"channel_id": self.livechat_channel.id}
        )["channel_id"]
        self.make_jsonrpc_request(
            "/im_livechat/feedback", {"channel_id": rated_channel_id, "rate": 5},
        )
        self._create_message(
            self.env["discuss.channel"].browse(rated_channel_id),
            self.operator,
            "2023-03-18 11:00:00",
        )
        result = self.env["discuss.channel"].formatted_read_group(
            [("channel_type", "=", "livechat")], aggregates=["livechat_rating_percentage:avg"]
        )
        self.assertEqual(
            result[0]["livechat_rating_percentage:avg"],
            100.0,
            "Rating percentage should be 100%, excluding unrated sessions",
        )

    def test_reporting_fields_read_matches_read_group(self):
        self.env["discuss.call.history"].create({
            "channel_id": self.channel.id,
            "start_dt": datetime(2023, 3, 17, 7, 0, 0),
            "end_dt": datetime(2023, 3, 17, 7, 30, 0),
        })
        self.env.flush_all()
        self.env.invalidate_all()
        for field_name in REPORTING_FIELDS:
            [(group_value,)] = self.env["discuss.channel"]._read_group(
                [("id", "=", self.channel.id)], [field_name]
            )
            record_value = self.channel[field_name]
            if isinstance(record_value, float):
                self.assertAlmostEqual(record_value, group_value, msg=field_name)
            else:
                self.assertEqual(record_value, group_value, field_name)

    @classmethod
    def _create_message(cls, channel, author, date):
        with cls.mock_datetime_and_now(date):
            date = fields.Datetime.now()
            return channel.message_post(author_id=author.id, body=f'Message {date}')

    def test_redirect_to_form_from_pivot(self):
        operator_1 = new_test_user(self.env, login="operator_1", groups="im_livechat.im_livechat_group_manager")
        operator_2 = new_test_user(self.env, login="operator_2")
        livechat_channel = self.env["im_livechat.channel"].create(
            {"name": "Support", "user_ids": [operator_1.id, operator_2.id]}
        )
        [partner_1, partner_2] = self.env["res.partner"].create([{"name": "test 1"}, {"name": "test 2"}])
        [channel_1, channel_2, channel_3] = self.env["discuss.channel"].create(
            [
                {
                    "name": "test 1",
                    "channel_type": "livechat",
                    "livechat_channel_id": livechat_channel.id,
                    "channel_member_ids": [
                        Command.create({"partner_id": operator_1.partner_id.id}),
                        Command.create({"partner_id": partner_1.id}),
                    ],
                },
                {
                    "name": "test 2",
                    "channel_type": "livechat",
                    "livechat_channel_id": livechat_channel.id,
                    "channel_member_ids": [
                        Command.create({"partner_id": operator_2.partner_id.id}),
                        Command.create({"partner_id": partner_2.id}),
                    ],
                },
                {
                    "name": "test 3",
                    "channel_type": "livechat",
                    "livechat_channel_id": livechat_channel.id,
                    "channel_member_ids": [
                        Command.create({"partner_id": operator_2.partner_id.id}),
                        Command.create({"partner_id": partner_2.id}),
                    ],
                },
            ]
        )
        self._create_message(channel_1, operator_1.partner_id, "2025-06-26 10:05:00")
        self._create_message(channel_2, operator_2.partner_id, "2025-06-26 10:15:00")
        self._create_message(channel_3, operator_2.partner_id, "2025-06-26 10:25:00")
        agent_report_action = self.env.ref("im_livechat.im_livechat_agent_history_action")
        session_report_action = self.env.ref("im_livechat.im_livechat_report_channel_action")
        self.start_tour(
            f"/odoo/action-{agent_report_action.id}?view_type=pivot",
            "im_livechat_agents_report_pivot_redirect_tour",
            login="operator_1",
        )
        self.start_tour(
            f"/odoo/action-{session_report_action.id}?view_type=pivot",
            "im_livechat_sessions_report_pivot_redirect_tour",
            login="operator_1",
        )

    def test_response_time_does_not_count_messages_after_close(self):
        with freeze_time("2025-05-20 06:00:00") as frozen_time:
            data = self.make_jsonrpc_request(
                    "/im_livechat/get_session",
                    {"channel_id": self.livechat_channel.id},
                )
            chat = self.env["discuss.channel"].browse(data["channel_id"])
            frozen_time.tick(delta=timedelta(minutes=1))
            chat.message_post(body="Question", message_type="comment")
            self._create_message(chat, self.env.user.partner_id, datetime.now())
            frozen_time.tick(delta=timedelta(minutes=5))
            self.make_jsonrpc_request("/im_livechat/visitor_leave_session", {"channel_id": chat.id})
            frozen_time.tick(delta=timedelta(minutes=5))
            agent = chat.channel_member_ids.filtered(
                lambda m: m.livechat_member_type == "agent"
            ).partner_id
            self._create_message(chat, agent, datetime.now())
            chat.invalidate_recordset()
            self.assertEqual(chat.livechat_response_time_hour, 0.0)

    def test_day_of_week_ordered_by_lang_week_start(self):
        agent = new_test_user(self.env, login="test_agent", groups="im_livechat.im_livechat_group_manager")
        livechat_channel = self.env["im_livechat.channel"].create(
            {"name": "Test Support", "user_ids": [agent.id]}
        )
        today_dt = datetime.now()
        for i in range(1, 8):
            date = today_dt + timedelta(days=i)
            with freeze_time(date):
                channel_id = self.make_jsonrpc_request(
                    "/im_livechat/get_session",
                    {"anonymous_name": f"Visitor_{i}", "channel_id": livechat_channel.id},
                )["channel_id"]
                channel = self.env["discuss.channel"].browse(channel_id)
                channel_agent = channel.channel_member_ids.filtered(
                    lambda m: m.livechat_member_type == "agent"
                ).partner_id
                self._create_message(channel, channel_agent, date)
        en_lang = self.env["res.lang"]._activate_lang("en_US")
        channel_model = self.env["discuss.channel"].with_user(agent)
        domain = [("livechat_channel_id", "=", livechat_channel.id)]
        result = channel_model.formatted_read_group(domain, groupby=["livechat_week_day"])
        self.assertEqual(
            [group["livechat_week_day"] for group in result],
            ["6", "0", "1", "2", "3", "4", "5"],
            "Days should be ordered starting from Sunday",
        )
        en_lang.week_start = "6"
        result = channel_model.formatted_read_group(domain, groupby=["livechat_week_day"])
        self.assertEqual(
            [group["livechat_week_day"] for group in result],
            ["5", "6", "0", "1", "2", "3", "4"],
            "Days should be ordered starting from Saturday",
        )

    def test_hour_and_day_of_week_in_user_timezone(self):
        alice_user = mail_new_test_user(
            self.env,
            login="alice",
            groups="im_livechat.im_livechat_group_manager",
            tz="Europe/Brussels",
        )
        livechat_channel = self.env["im_livechat.channel"].create(
            {"name": "Test Support", "user_ids": [alice_user.id]},
        )
        # Simulate Friday 23:30 UTC: Saturday 00:30 (winter) and 01:30 (summer) in Brussels.
        for date in ("2023-03-17 23:30:00", "2023-06-16 23:30:00"):
            with freeze_time(date):
                self.make_jsonrpc_request(
                    "/im_livechat/get_session",
                    {"channel_id": livechat_channel.id},
                )
        channel_model = self.env["discuss.channel"].with_user(alice_user)
        domain = [("livechat_channel_id", "=", livechat_channel.id)]
        channels = channel_model.search(domain)
        self.assertEqual(sorted(channels.mapped("livechat_start_hour")), [0.0, 1.0])
        self.assertEqual(set(channels.mapped("livechat_week_day")), {"5"})
        result = channel_model.formatted_read_group(domain, groupby=["livechat_start_hour"])
        self.assertEqual([group["livechat_start_hour"] for group in result], [0.0, 1.0])
        result = channel_model.formatted_read_group(domain, groupby=["livechat_week_day"])
        self.assertEqual([group["livechat_week_day"] for group in result], ["5"])
        self.assertEqual(channel_model.search_count(domain + [("livechat_start_hour", ">", 0)]), 1)
        history_model = self.env["im_livechat.channel.member.history"].with_user(alice_user)
        domain = [("session_livechat_channel_id", "=", livechat_channel.id)]
        histories = history_model.search(domain)
        self.assertEqual(sorted(histories.mapped("session_start_hour")), [0.0, 0.0, 1.0, 1.0])
        self.assertEqual(set(histories.mapped("session_week_day")), {"5"})
        result = history_model.formatted_read_group(domain, groupby=["session_start_hour"])
        self.assertEqual([group["session_start_hour"] for group in result], [0.0, 1.0])
        for group in result:
            self.assertEqual(history_model.search_count(domain + group["__extra_domain"]), 2)
        result = history_model.formatted_read_group(domain, groupby=["session_week_day"])
        self.assertEqual([group["session_week_day"] for group in result], ["5"])
        self.assertEqual(history_model.search_count(domain + result[0]["__extra_domain"]), 4)
        self.assertEqual(history_model.search_count(domain + [("session_start_hour", ">", 0)]), 2)
        self.assertEqual(
            history_model.search_count(domain + [("session_week_day", "!=", False)]), 4,
        )
