# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time
from unittest.mock import patch

from odoo import Command
from odoo.addons.im_livechat.tests.common import TestImLivechatCommon
from odoo.tests.common import new_test_user, tagged


@tagged("post_install", "-at_install")
class TestImLivechatReport(TestImLivechatCommon):
    def setUp(self):
        super().setUp()
        self.env['discuss.channel'].search([('livechat_channel_id', '!=', False)]).unlink()

        def _compute_available_operator_ids(channel_self):
            for record in channel_self:
                record.available_operator_ids = self.operators
        with (
            patch.object(
                type(self.env["im_livechat.channel"]),
                "_compute_available_operator_ids",
                _compute_available_operator_ids,
            ),
            freeze_time("2023-03-17 06:05:54"),
        ):
            channel_id = self.make_jsonrpc_request(
                "/im_livechat/get_session",
                {"channel_id": self.livechat_channel.id},
            )["channel_id"]

        channel = self.env['discuss.channel'].browse(channel_id)
        self.operator = channel.livechat_operator_id

        self._create_message(channel, self.visitor_user.partner_id, '2023-03-17 06:06:59')
        self._create_message(channel, self.operator, '2023-03-17 08:15:54')
        self._create_message(channel, self.operator, '2023-03-17 08:45:54')

        # message with the same record id, but with a different model
        # should not be taken into account for statistics
        partner_message = self._create_message(channel, self.operator, '2023-03-17 05:05:54')
        partner_message |= self._create_message(channel, self.operator, '2023-03-17 09:15:54')
        partner_message.model = 'res.partner'

        with freeze_time("2023-03-17 09:20:54"):
            self.make_jsonrpc_request(
                "/im_livechat/visitor_leave_session",
                {"channel_id": channel_id}
            )
        self.env['mail.message'].flush_model()

    def test_im_livechat_report_channel(self):
        report = self.env['im_livechat.report.channel'].search([('livechat_channel_id', '=', self.livechat_channel.id)])
        self.assertEqual(len(report), 1, 'Should have one channel report for this live channel')
        # We have those messages, ordered by creation;
        # 05:05:54: wrong model
        # 06:05:54: session create
        # 06:06:59: visitor message
        # 08:15:54: operator first answer
        # 08:45:54: operator second answer
        # 09:15:54: wrong model
        # So the duration of the session is: (09:20:54 - 06:05:54) = 3h15 = 195 minutes
        # The time to answer of this session is: (08:15:54 - 06:05:54) = 2h10 = 7800 seconds
        self.assertEqual(report.time_to_answer, 7800 / 3600)
        self.assertEqual(int(report.duration), 195)

    def test_im_livechat_report_operator(self):
        result = self.env["im_livechat.report.channel"].formatted_read_group([], aggregates=["time_to_answer:avg", "duration:avg"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["time_to_answer:avg"], 7800 / 3600)
        self.assertEqual(int(result[0]['duration:avg']), 195)
        channel = self.env["discuss.channel"].search([("livechat_channel_id", "=", self.livechat_channel.id)])
        rated_channel = channel.copy({"rating_last_value": 5})
        self._create_message(rated_channel, self.operator, "2023-03-18 11:00:00")
        result = self.env["im_livechat.report.channel"].formatted_read_group([], aggregates=["rating:avg"])
        self.assertEqual(result[0]["rating:avg"], 5, "Rating average should be 5, excluding unrated sessions")

    @classmethod
    def _create_message(cls, channel, author, date):
        with patch.object(cls.env.cr, 'now', lambda: date):
            return channel.message_post(author_id=author.id, body=f'Message {date}')

    def test_redirect_to_form_from_pivot(self):
        operator_1 = new_test_user(self.env, login="operator_1", groups="im_livechat.im_livechat_group_manager")
        operator_2 = new_test_user(self.env, login="operator_2")
        livechat_channel = self.env["im_livechat.channel"].create(
            {"name": "Support", "user_ids": [operator_1.id, operator_2.id]}
        )
        [partner_1, partner_2] = self.env["res.partner"].create([{"name": "test 1"}, {"name": "test 2"}])
        [channel_1, channel_2, channel_3] = self.env["discuss.channel"].create(
            [{
                "name": "test 1",
                "channel_type": "livechat",
                "livechat_channel_id": livechat_channel.id,
                "livechat_operator_id": operator_1.partner_id.id,
                "channel_member_ids": [Command.create({"partner_id": partner_1.id})],
            },
            {
                "name": "test 2",
                "channel_type": "livechat",
                "livechat_channel_id": livechat_channel.id,
                "livechat_operator_id": operator_2.partner_id.id,
                "channel_member_ids": [Command.create({"partner_id": partner_2.id})],
            },
            {
                "name": "test 3",
                "channel_type": "livechat",
                "livechat_channel_id": livechat_channel.id,
                "livechat_operator_id": operator_2.partner_id.id,
                "channel_member_ids": [Command.create({"partner_id": partner_2.id})],
            }]
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
