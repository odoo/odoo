# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.im_livechat.tests.common import TestImLivechatCommon


class TestImLivechatReport(TestImLivechatCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['mail.channel'].search([('livechat_channel_id', '!=', False)]).unlink()

        with patch.object(type(cls.env['im_livechat.channel']), '_get_available_users', lambda _: cls.operators):
            channel_id = cls.livechat_channel._open_livechat_mail_channel('Anonymous')['id']

        channel = cls.env['mail.channel'].browse(channel_id)
        cls.operator = channel.livechat_operator_id

        cls._create_message(channel, cls.visitor_user.partner_id, '2023-03-17 06:05:54')
        cls._create_message(channel, cls.operator, '2023-03-17 08:15:54')
        cls._create_message(channel, cls.operator, '2023-03-17 08:45:54')

        # message with the same record id, but with a different model
        # should not be taken into account for statistics
        partner_message = cls._create_message(channel, cls.operator, '2023-03-17 05:05:54')
        partner_message |= cls._create_message(channel, cls.operator, '2023-03-17 09:15:54')
        partner_message.model = 'res.partner'
        cls.env['mail.message'].flush()

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
