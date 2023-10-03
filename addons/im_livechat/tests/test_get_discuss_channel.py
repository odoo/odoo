# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta
from freezegun import freeze_time
from unittest.mock import patch, PropertyMock

from odoo import fields
from odoo.addons.im_livechat.tests.common import TestImLivechatCommon


class TestGetDiscussChannel(TestImLivechatCommon):
    def test_get_discuss_channel(self):
        """For a livechat with 5 available operators, we open 5 channels 5 times (25 channels total).
        For every 5 channels opening, we check that all operators were assigned.
        """

        for i in range(5):
            discuss_channels = self._open_livechat_discuss_channel()
            channel_operators = [channel_info['operator_pid'] for channel_info in discuss_channels]
            channel_operator_ids = [channel_operator[0] for channel_operator in channel_operators]
            self.assertTrue(all(partner_id in channel_operator_ids for partner_id in self.operators.mapped('partner_id').ids))

    def test_channel_get_livechat_visitor_info(self):
        belgium = self.env.ref('base.be')
        test_user = self.env['res.users'].create({'name': 'Roger', 'login': 'roger', 'password': self.password, 'country_id': belgium.id})

        # ensure visitor info are correct with anonymous
        operator = self.operators[0]
        with patch('odoo.http.GeoIP.country_code', new_callable=PropertyMock(return_value=belgium.code)):
            channel_info = self.make_jsonrpc_request(
                '/im_livechat/get_session',
                {
                    'anonymous_name': 'Visitor 22',
                    'previous_operator_id': operator.partner_id.id,
                    'channel_id': self.livechat_channel.id,
                    'country_id': belgium.id,
                },
            )
        self.assertEqual(channel_info['channel']['anonymous_name'], "Visitor 22")
        self.assertEqual(channel_info['channel']['anonymous_country'], {'code': 'BE', 'id': belgium.id, 'name': 'Belgium'})

        # ensure member info are hidden (in particular email and real name when livechat username is present)
        # shape of channelMembers is [('ADD', data...)], [0][1] accesses the data
        self.assertEqual(sorted((m['persona'] for m in channel_info['channel']['channelMembers'][0][1]), key=lambda m: m['id']), sorted([{
            'id': self.env['discuss.channel'].browse(channel_info['id']).channel_member_ids.filtered(lambda m: m.guest_id)[0].guest_id.id,
            'name': 'Visitor',
            'im_status': 'offline',
            'type': "guest",
        }, {
            'active': True,
            'country': False,
            'id': operator.partner_id.id,
            'is_bot': False,
            'is_public': False,
            'type': "partner",
            'user_livechat_username': 'Michel Operator',
        }], key=lambda m: m['id']))

        # ensure visitor info are correct with real user
        self.authenticate(test_user.login, self.password)
        channel_info = self.make_jsonrpc_request('/im_livechat/get_session', {
            'anonymous_name': 'whatever',
            'previous_operator_id': operator.partner_id.id,
            'user_id': test_user.id,
            'channel_id': self.livechat_channel.id,
        })
        self.assertFalse(channel_info['channel']['anonymous_name'])
        self.assertEqual(channel_info['channel']['anonymous_country'], {'code': 'BE', 'id': belgium.id, 'name': 'Belgium'})
        self.assertEqual(channel_info['channel']['channelMembers'], [['ADD', [
            {
                'channel': {'id': channel_info['id']},
                'id': self.env['discuss.channel.member'].search([('channel_id', '=', channel_info['id']), ('partner_id', '=', operator.partner_id.id)]).id,
                'persona': {
                    'active': True,
                    'country': False,
                    'id': operator.partner_id.id,
                    'is_bot': False,
                    'is_public': False,
                    'type': "partner",
                    'user_livechat_username': 'Michel Operator',
                },
            },
            {
                'channel': {'id': channel_info['id']},
                'id': self.env['discuss.channel.member'].search([('channel_id', '=', channel_info['id']), ('partner_id', '=', test_user.partner_id.id)]).id,
                'persona': {
                    'active': True,
                    'country': {
                        'code': 'BE',
                        'id': belgium.id,
                        'name': 'Belgium',
                    },
                    'id': test_user.partner_id.id,
                    'is_bot': False,
                    'is_public': False,
                    'name': 'Roger',
                    'type': "partner",
                },
            },
        ]]])

        # ensure visitor info are correct when operator is testing themselves
        operator = self.operators[0]
        self.authenticate(operator.login, self.password)
        channel_info = self.make_jsonrpc_request('/im_livechat/get_session', {
            'anonymous_name': 'whatever',
            'previous_operator_id': operator.partner_id.id,
            'user_id': operator.id,
            'channel_id': self.livechat_channel.id,
        })
        self.assertEqual(channel_info['operator_pid'], [operator.partner_id.id, "Michel Operator"])
        self.assertFalse(channel_info['channel']['anonymous_name'])
        self.assertEqual(channel_info['channel']['anonymous_country'], False)
        self.assertEqual(channel_info['channel']['channelMembers'], [['ADD', [
            {
                'channel': {'id': channel_info['id']},
                'id': self.env['discuss.channel.member'].search([('channel_id', '=', channel_info['id']), ('partner_id', '=', operator.partner_id.id)]).id,
                'persona': {
                    'active': True,
                    'country': False,
                    'id': operator.partner_id.id,
                    'is_bot': False,
                    'is_public': False,
                    'type': "partner",
                    'user_livechat_username': 'Michel Operator',
                },
            },
        ]]])

    def _open_livechat_discuss_channel(self):
        discuss_channels = []

        for i in range(5):
            discuss_channel = self.make_jsonrpc_request('/im_livechat/get_session', {'anonymous_name': 'Anonymous', 'channel_id': self.livechat_channel.id})
            discuss_channels.append(discuss_channel)
            # send a message to mark this channel as 'active'
            self.env['discuss.channel'].browse(discuss_channel['id']).message_post(body='cc')

        return discuss_channels

    def test_channel_not_pinned_for_operator_before_first_message(self):
        channel_info = self.make_jsonrpc_request('/im_livechat/get_session', {'anonymous_name': 'whatever', 'channel_id': self.livechat_channel.id})
        operator_channel_member = self.env['discuss.channel.member'].search([('channel_id', '=', channel_info['id']), ('partner_id', 'in', self.operators.partner_id.ids)])
        self.assertEqual(len(operator_channel_member), 1, "operator should be member of channel")
        self.assertFalse(operator_channel_member.is_pinned, "channel should not be pinned for operator initially")
        self.env['discuss.channel'].browse(channel_info['id']).message_post(body='cc')
        self.assertTrue(operator_channel_member.is_pinned, "channel should be pinned for operator after visitor sent a message")
        self.assertIn(channel_info['id'], operator_channel_member.partner_id._get_channels_as_member().ids, "channel should be fetched by operator on new page")

    def test_operator_livechat_username(self):
        """Ensures the operator livechat_username is returned by `_channel_fetch_message`, which is
        the method called by the public route displaying chat history."""
        operator = self.operators[0]
        operator.write({
            'email': 'michel@example.com',
            'livechat_username': 'Michel at your service',
        })
        channel_info = self.make_jsonrpc_request('/im_livechat/get_session', {'anonymous_name': 'whatever', 'channel_id': self.livechat_channel.id})
        channel = self.env['discuss.channel'].browse(channel_info['id'])
        channel.with_user(operator).message_post(body='Hello', message_type='comment', subtype_xmlid='mail.mt_comment')
        message_formats = channel.with_user(None).sudo()._channel_fetch_message()
        self.assertEqual(len(message_formats), 1)
        self.assertEqual(message_formats[0]['author']['id'], operator.partner_id.id)
        self.assertEqual(message_formats[0]['author']['user_livechat_username'], operator.livechat_username)
        self.assertFalse(message_formats[0].get('email_from'), "should not send email_from to livechat user")

    def test_read_channel_unpined_for_operator_after_one_day(self):
        channel_info = self.make_jsonrpc_request('/im_livechat/get_session', {'anonymous_name': 'visitor', 'channel_id': self.livechat_channel.id})
        member_of_operator = self.env['discuss.channel.member'].search([('channel_id', '=', channel_info['id']), ('partner_id', 'in', self.operators.partner_id.ids)])
        message = self.env['discuss.channel'].browse(channel_info['id']).message_post(body='cc')
        member_of_operator.channel_id.with_user(self.operators.filtered(
            lambda operator: operator.partner_id == member_of_operator.partner_id
        ))._channel_seen(message.id)
        with freeze_time(fields.Datetime.to_string(fields.datetime.now() + timedelta(days=1))):
            member_of_operator._gc_unpin_livechat_sessions()
        self.assertFalse(member_of_operator.is_pinned, "read channel should be unpinned after one day")

    def test_unread_channel_not_unpined_for_operator_after_autovacuum(self):
        channel_info = self.make_jsonrpc_request('/im_livechat/get_session', {'anonymous_name': 'visitor', 'channel_id': self.livechat_channel.id})
        member_of_operator = self.env['discuss.channel.member'].search([('channel_id', '=', channel_info['id']), ('partner_id', 'in', self.operators.partner_id.ids)])
        self.env['discuss.channel'].browse(channel_info['id']).message_post(body='cc')
        with freeze_time(fields.Datetime.to_string(fields.datetime.now() + timedelta(days=1))):
            member_of_operator._gc_unpin_livechat_sessions()
        self.assertTrue(member_of_operator.is_pinned, "unread channel should not be unpinned after autovacuum")
