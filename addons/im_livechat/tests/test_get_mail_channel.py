# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestGetMailChannel(TransactionCase):
    def setUp(self):
        super(TestGetMailChannel, self).setUp()
        self.operators = self.env['res.users'].create([{
            'name': 'Michel',
            'login': 'michel'
        }, {
            'name': 'Paul',
            'login': 'paul'
        }, {
            'name': 'Pierre',
            'login': 'pierre'
        }, {
            'name': 'Jean',
            'login': 'jean'
        }, {
            'name': 'Georges',
            'login': 'georges'
        }])

        self.visitor_user = self.env['res.users'].create({
            'name': 'Rajesh',
            'login': 'rajesh',
            'country_id': self.ref('base.in'),
        })

        self.livechat_channel = self.env['im_livechat.channel'].create({
            'name': 'The channel',
            'user_ids': [(6, 0, self.operators.ids)]
        })

        operators = self.operators
        def get_available_users(self):
            return operators

        self.patch(type(self.env['im_livechat.channel']), '_get_available_users', get_available_users)

    def test_get_mail_channel(self):
        """For a livechat with 5 available operators, we open 5 channels 5 times (25 channels total).
        For every 5 channels opening, we check that all operators were assigned.
        """

        for i in range(5):
            mail_channels = self._open_livechat_mail_channel()
            channel_operators = [channel_info['operator_pid'] for channel_info in mail_channels]
            channel_operator_ids = [channel_operator[0] for channel_operator in channel_operators]
            self.assertTrue(all(partner_id in channel_operator_ids for partner_id in self.operators.mapped('partner_id').ids))

        visitor_user_channel = self.livechat_channel._open_livechat_mail_channel('Visitor', user_id=self.visitor_user.id)
        chat_title = '%s (%s)' % (self.visitor_user.display_name, self.visitor_user.country_id.name)
        self.assertEqual(visitor_user_channel['correspondent_name'], chat_title, "Chat title should be correct and should contain visitor's country name")

    def _open_livechat_mail_channel(self):
        mail_channels = []

        for i in range(5):
            mail_channel = self.livechat_channel._open_livechat_mail_channel('Anonymous')
            mail_channels.append(mail_channel)
            # send a message to mark this channel as 'active'
            self.env['mail.channel'].browse(mail_channel['id']).write({
                'channel_message_ids': [(0, 0, {'body': 'cc'})]
            })

        return mail_channels
