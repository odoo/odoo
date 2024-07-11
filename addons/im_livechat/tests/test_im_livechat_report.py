# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.im_livechat.tests.common import TestImLivechatCommon
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class TestImLivechatReport(TestImLivechatCommon):
    def setUp(self):
        super().setUp()
        self.env['discuss.channel'].search([('livechat_channel_id', '!=', False)]).unlink()

        def _compute_available_operator_ids(channel_self):
            for record in channel_self:
                record.available_operator_ids = self.operators

        with patch.object(type(self.env['im_livechat.channel']), '_compute_available_operator_ids', _compute_available_operator_ids):
            channel_id = self.make_jsonrpc_request("/im_livechat/get_session", {'anonymous_name': 'Anonymous', 'channel_id': self.livechat_channel.id})['id']

        channel = self.env['discuss.channel'].browse(channel_id)
        self.operator = channel.livechat_operator_id

        self._create_message(channel, self.visitor_user.partner_id, '2023-03-17 06:05:54')
        self._create_message(channel, self.operator, '2023-03-17 08:15:54')
        self._create_message(channel, self.operator, '2023-03-17 08:45:54')

        # message with the same record id, but with a different model
        # should not be taken into account for statistics
        partner_message = self._create_message(channel, self.operator, '2023-03-17 05:05:54')
        partner_message |= self._create_message(channel, self.operator, '2023-03-17 09:15:54')
        partner_message.model = 'res.partner'
        self.env['mail.message'].flush_model()

    def test_im_livechat_report_channel(self):
        report = self.env['im_livechat.report.channel'].search([('livechat_channel_id', '=', self.livechat_channel.id)])
        self.assertEqual(len(report), 1, 'Should have one channel report for this live channel')
        # We have those messages, ordered by creation;
        # 05:05:54: wrong model
        # 06:05:54: visitor message
        # 08:15:54: operator first answer
        # 08:45:54: operator second answer
        # 09:15:54: wrong model
        # So the duration of the session is: (08:45:54 - 06:05:54) = 2h40 = 9600 seconds
        # The time to answer of this session is: (08:15:54 - 06:05:54) = 2h10 = 7800 seconds
        self.assertEqual(int(report.time_to_answer), 7800)
        self.assertEqual(int(report.duration), 9600)

    def test_im_livechat_report_operator(self):
        result = self.env['im_livechat.report.operator'].read_group([], ['time_to_answer:avg', 'duration:avg'], [])
        self.assertEqual(len(result), 1)
        self.assertEqual(int(result[0]['time_to_answer']), 7800)
        self.assertEqual(int(result[0]['duration']), 9600)

    @classmethod
    def _create_message(cls, channel, author, date):
        with patch.object(cls.env.cr, 'now', lambda: date):
            return channel.message_post(author_id=author.id, body=f'Message {date}')
