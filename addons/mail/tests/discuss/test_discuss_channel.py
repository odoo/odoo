# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from datetime import datetime
from unittest.mock import patch

from odoo import Command, fields
from odoo.addons.mail.models.discuss.discuss_channel import channel_avatar, group_avatar
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tests.common import MailCommon
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged, users
from odoo.tools import html_escape, mute_logger
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT


@tagged("post_install", "-at_install")
class TestChannelInternals(MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_channel = cls.env['discuss.channel'].with_context(cls._test_context).channel_create(name='Channel', group_id=None)
        cls.test_partner = cls.env['res.partner'].with_context(cls._test_context).create({
            'name': 'Test Partner',
            'email': 'test_customer@example.com',
        })
        cls.user_employee_nomail = mail_new_test_user(
            cls.env, login='employee_nomail',
            email=False,
            groups='base.group_user',
            company_id=cls.company_admin.id,
            name='Evita Employee NoEmail',
            notification_type='email',
            signature='--\nEvite'
        )
        cls.partner_employee_nomail = cls.user_employee_nomail.partner_id

    def test_channel_member_cannot_be_public_user(self):
        """Public users can only join channels as guest."""
        user_public = mail_new_test_user(self.env, login='user_public', groups='base.group_public', name='Bert Tartignole')
        public_channel = self.env['discuss.channel'].channel_create(name='Public Channel', group_id=None)
        with self.assertRaises(ValidationError):
            public_channel.add_members(user_public.partner_id.id)

    @users('employee')
    def test_channel_members(self):
        channel = self.env['discuss.channel'].browse(self.test_channel.ids)
        self.assertEqual(channel.message_partner_ids, self.env['res.partner'])
        self.assertEqual(channel.channel_partner_ids, self.env['res.partner'])

        channel.add_members(self.test_partner.ids)
        self.assertEqual(channel.message_partner_ids, self.env['res.partner'])
        self.assertEqual(channel.channel_partner_ids, self.test_partner)

        self.env['discuss.channel.member'].sudo().search([
            ('partner_id', 'in', self.test_partner.ids),
            ('channel_id', 'in', channel.ids)
        ]).unlink()
        self.assertEqual(channel.message_partner_ids, self.env['res.partner'])
        self.assertEqual(channel.channel_partner_ids, self.env['res.partner'])

        channel.message_post(body='Test', message_type='comment', subtype_xmlid='mail.mt_comment')
        self.assertEqual(channel.message_partner_ids, self.env['res.partner'])
        self.assertEqual(channel.channel_partner_ids, self.env['res.partner'])

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_channel_chat_message_post_should_update_last_interest_dt(self):
        chat = self.env['discuss.channel'].with_user(self.user_admin).channel_get((self.partner_employee | self.user_admin.partner_id).ids)
        post_time = fields.Datetime.now()
        # Mocks the return value of field.Datetime.now(),
        # so we can see if the `last_interest_dt` is updated correctly
        with patch.object(fields.Datetime, 'now', lambda: post_time):
            chat.message_post(body="Test", message_type='comment', subtype_xmlid='mail.mt_comment')
        channel_member_employee = self.env['discuss.channel.member'].search([
            ('partner_id', '=', self.partner_employee.id),
            ('channel_id', '=', chat.id),
        ])
        channel_member_admin = self.env['discuss.channel.member'].search([
            ('partner_id', '=', self.partner_admin.id),
            ('channel_id', '=', chat.id),
        ])
        self.assertEqual(channel_member_employee.last_interest_dt, post_time)
        self.assertEqual(channel_member_admin.last_interest_dt, post_time)

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_channel_recipients_channel(self):
        """ Posting a message on a channel should not send emails """
        channel = self.env['discuss.channel'].browse(self.test_channel.ids)
        # sudo: discuss.channel.member - adding members in non-accessible channel in a test file
        channel.sudo().add_members((self.partner_employee | self.partner_admin | self.test_partner).ids)
        with self.mock_mail_gateway():
            new_msg = channel.message_post(body="Test", message_type='comment', subtype_xmlid='mail.mt_comment')
        self.assertNotSentEmail()
        self.assertEqual(new_msg.model, self.test_channel._name)
        self.assertEqual(new_msg.res_id, self.test_channel.id)
        self.assertEqual(new_msg.partner_ids, self.env['res.partner'])
        self.assertEqual(new_msg.notified_partner_ids, self.env['res.partner'])

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_channel_recipients_chat(self):
        """ Posting a message on a chat should not send emails """
        chat = self.env['discuss.channel'].with_user(self.user_admin).channel_get((self.partner_employee | self.user_admin.partner_id).ids)
        with self.mock_mail_gateway():
            with self.with_user('employee'):
                new_msg = chat.message_post(body="Test", message_type='comment', subtype_xmlid='mail.mt_comment')
        self.assertNotSentEmail()
        self.assertEqual(new_msg.model, chat._name)
        self.assertEqual(new_msg.res_id, chat.id)
        self.assertEqual(new_msg.partner_ids, self.env['res.partner'])
        self.assertEqual(new_msg.notified_partner_ids, self.env['res.partner'])

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_channel_recipients_mention(self):
        """ Posting a message on a classic channel should support mentioning somebody """
        with self.mock_mail_gateway():
            self.test_channel.message_post(
                body="Test", partner_ids=self.test_partner.ids,
                message_type='comment', subtype_xmlid='mail.mt_comment')
        self.assertSentEmail(self.test_channel.env.user.partner_id, [self.test_partner])

    @mute_logger('odoo.models.unlink')
    def test_channel_user_synchronize(self):
        """Archiving / deleting a user should automatically unsubscribe related partner from group restricted channels"""
        group_restricted_channel = self.env['discuss.channel'].channel_create(name='Sic Mundus', group_id=self.env.ref('base.group_user').id)

        self.test_channel.add_members((self.partner_employee | self.partner_employee_nomail).ids)
        group_restricted_channel.add_members((self.partner_employee | self.partner_employee_nomail).ids)

        # Unsubscribe archived user from the private channels, but not from public channels
        self.user_employee.active = False
        self.assertEqual(group_restricted_channel.channel_partner_ids, self.partner_employee_nomail)
        self.assertEqual(self.test_channel.channel_partner_ids, self.user_employee.partner_id | self.partner_employee_nomail)

        # Unsubscribe deleted user from the private channels, but not from public channels
        self.user_employee_nomail.unlink()
        self.assertEqual(group_restricted_channel.channel_partner_ids, self.env['res.partner'])
        self.assertEqual(self.test_channel.channel_partner_ids, self.user_employee.partner_id | self.partner_employee_nomail)

    @users('employee_nomail')
    def test_channel_info_get(self):
        # `channel_get` should return a new channel the first time a partner is given
        initial_channel_info = self.env['discuss.channel'].channel_get(partners_to=self.test_partner.ids)._channel_info()[0]
        # shape of channelMembers is [('ADD', data...)], [0][1] accesses the data
        self.assertEqual({m['persona']['id'] for m in initial_channel_info['channelMembers'][0][1]}, {self.partner_employee_nomail.id, self.test_partner.id})

        # `channel_get` should return the existing channel every time the same partner is given
        same_channel_info = self.env['discuss.channel'].channel_get(partners_to=self.test_partner.ids)._channel_info()[0]
        self.assertEqual(same_channel_info['id'], initial_channel_info['id'])

        # `channel_get` should return the existing channel when the current partner is given together with the other partner
        together_channel_info = self.env['discuss.channel'].channel_get(partners_to=(self.partner_employee_nomail + self.test_partner).ids)._channel_info()[0]
        self.assertEqual(together_channel_info['id'], initial_channel_info['id'])

        # `channel_get` should return a new channel the first time just the current partner is given,
        # even if a channel containing the current partner together with other partners already exists
        solo_channel_info = self.env['discuss.channel'].channel_get(partners_to=self.partner_employee_nomail.ids)._channel_info()[0]
        self.assertNotEqual(solo_channel_info['id'], initial_channel_info['id'])
        # shape of channelMembers is [('ADD', data...)], [0][1] accesses the data
        self.assertEqual({m['persona']['id'] for m in solo_channel_info['channelMembers'][0][1]}, {self.partner_employee_nomail.id})

        # `channel_get` should return the existing channel every time the current partner is given
        same_solo_channel_info = self.env['discuss.channel'].channel_get(partners_to=self.partner_employee_nomail.ids)._channel_info()[0]
        self.assertEqual(same_solo_channel_info['id'], solo_channel_info['id'])

    # `channel_get` will pin the channel by default and thus last interest will be updated.
    @users('employee')
    def test_channel_info_get_should_update_last_interest_dt(self):
        self.env['discuss.channel'].channel_get(partners_to=self.partner_admin.ids)

        retrieve_time = datetime(2021, 1, 1, 0, 0)
        with patch.object(fields.Datetime, 'now', lambda: retrieve_time):
            # `last_interest_dt` should be updated again when `channel_get` is called
            # because `channel_pin` is called.
            channel_info = self.env['discuss.channel'].channel_get(partners_to=self.partner_admin.ids)._channel_info()[0]
        self.assertEqual(channel_info['last_interest_dt'], retrieve_time.strftime(DEFAULT_SERVER_DATETIME_FORMAT))

    @users('employee')
    def test_channel_info_seen(self):
        """ In case of concurrent channel_seen RPC, ensure the oldest call has no effect. """
        chat = self.env['discuss.channel'].with_user(self.user_admin).channel_get((self.partner_employee | self.user_admin.partner_id).ids)
        msg_1 = self._add_messages(chat, 'Body1', author=self.user_employee.partner_id)
        msg_2 = self._add_messages(chat, 'Body2', author=self.user_employee.partner_id)

        chat._channel_seen(msg_2.id)
        self.assertEqual(
            chat._channel_info()[0]['seen_partners_info'][0]['seen_message_id'],
            msg_2.id,
            "Last message id should have been updated"
        )

        chat._channel_seen(msg_1.id)
        self.assertEqual(
            chat._channel_info()[0]['seen_partners_info'][0]['seen_message_id'],
            msg_2.id,
            "Last message id should stay the same after mark channel as seen with an older message"
        )

    @users('employee')
    def test_set_last_seen_message_should_send_notification_only_once(self):
        chat = self.env['discuss.channel'].with_user(self.user_admin).channel_get((self.partner_employee | self.user_admin.partner_id).ids)
        msg_1 = self._add_messages(chat, 'Body1', author=self.user_employee.partner_id)
        member = chat.channel_member_ids.filtered(lambda m: m.partner_id == self.user_admin.partner_id)
        self._reset_bus()
        with self.assertBus(
            [
                (self.env.cr.dbname, "discuss.channel", chat.id),
                (self.env.cr.dbname, "res.partner", self.user_admin.partner_id.id)
            ],
            [
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "ChannelMember": {
                            "id": member.id,
                            "persona": {
                                "id": self.user_admin.partner_id.id,
                                "type": "partner",
                            },
                            "lastSeenMessage": {"id": msg_1.id},
                        },
                    },
                },
                   {
                    "type": "mail.record/insert",
                    "payload": {
                        "ChannelMember": {
                            "id": member.id,
                            "persona": {
                                "id": self.user_admin.partner_id.id,
                                "type": "partner",
                            },
                            "lastSeenMessage": {"id": msg_1.id},
                            "thread": {
                                "id": chat.id,
                                "message_unread_counter": 0,
                                "message_unread_counter_bus_id": self.env['bus.bus'].sudo()._bus_last_id(),
                                "model": "discuss.channel",
                                "seen_message_id": msg_1.id
                            }
                        },
                    },
                },
            ],
        ):
            chat._channel_seen(msg_1.id)
        # There should be no channel member to be set as seen in the second time
        # So no notification should be sent
        self._reset_bus()
        with self.assertBus([], []):
            chat._channel_seen(msg_1.id)

    def test_channel_message_post_should_not_allow_adding_wrong_parent(self):
        channels = self.env['discuss.channel'].create([{'name': '1'}, {'name': '2'}])
        message = self._add_messages(channels[0], 'Body1')
        message_format2 = channels[1].message_post(body='Body2', parent_id=message.id)
        self.assertFalse(message_format2['parent_id'], "should not allow parent from wrong thread")
        message_format3 = channels[1].message_post(body='Body3', parent_id=message.id + 100)
        self.assertFalse(message_format3['parent_id'], "should not allow non-existing parent")

    def test_channel_message_post_with_voice_attachment(self):
        """ Test 'voice' info being supported to create voice metadata. """
        channel = self.env['discuss.channel'].create({'name': 'channel_1'})
        channel.message_post(attachments=[('audio', b'OggS\x00\x02', {'voice': True})])
        self.assertTrue(channel.message_ids.attachment_ids.voice_ids, "message's attachment should have voice metadata")

    @mute_logger('odoo.models.unlink')
    def test_channel_unsubscribe_auto(self):
        """ Archiving / deleting a user should automatically unsubscribe related
        partner from private channels """
        test_user = self.env['res.users'].create({
            "login": "adam",
            "name": "Jonas",
        })
        test_partner = test_user.partner_id
        group_restricted_channel = self.env['discuss.channel'].with_context(self._test_context).create({
            'name': 'Sic Mundus',
            'group_public_id': self.env.ref('base.group_user').id,
            'channel_partner_ids': [Command.link(self.user_employee.partner_id.id), Command.link(test_partner.id)],
        })
        self.test_channel.with_context(self._test_context).write({
            'channel_partner_ids': [Command.link(self.user_employee.partner_id.id), Command.link(test_partner.id)],
        })
        private_group = self.env['discuss.channel'].with_user(self.user_employee).with_context(self._test_context).create({
            'name': 'test',
            'channel_type': 'group',
            'channel_partner_ids': [Command.link(self.user_employee.partner_id.id), Command.link(test_partner.id)],
        })

        # Unsubscribe archived user from the private channels, but not from public channels and not from group
        self.user_employee.active = False
        (private_group | self.test_channel).invalidate_recordset(['channel_partner_ids'])
        self.assertEqual(group_restricted_channel.channel_partner_ids, test_partner)
        self.assertEqual(self.test_channel.channel_partner_ids, self.user_employee.partner_id | test_partner)
        self.assertEqual(private_group.channel_partner_ids, self.user_employee.partner_id | test_partner)

        # Unsubscribe deleted user from the private channels, but not from public channels and not from group
        test_user.unlink()
        self.assertEqual(group_restricted_channel.channel_partner_ids, self.env['res.partner'])
        self.assertEqual(self.test_channel.channel_partner_ids, self.user_employee.partner_id | test_partner)
        self.assertEqual(private_group.channel_partner_ids, self.user_employee.partner_id | test_partner)

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_channel_private_unfollow(self):
        """ Test that a partner can leave (unfollow) a channel/group/chat. """
        group_restricted_channel = self.env['discuss.channel'].channel_create(name='Channel for Groups', group_id=self.env.ref('base.group_user').id)
        public_channel = self.env['discuss.channel'].channel_create(name='Channel for Everyone', group_id=None)
        private_group = self.env['discuss.channel'].create_group(partners_to=self.user_employee.partner_id.ids, name="Group")
        chat_user_current = self.env['discuss.channel'].channel_get(self.env.user.partner_id.ids)
        self.assertEqual(len(group_restricted_channel.channel_member_ids), 1)
        self.assertEqual(len(public_channel.channel_member_ids), 1)
        self.assertEqual(len(private_group.sudo().channel_member_ids), 1)
        self.assertEqual(len(chat_user_current.sudo().channel_member_ids), 1)
        group_restricted_channel.action_unfollow()
        public_channel.action_unfollow()
        private_group.action_unfollow()
        chat_user_current.action_unfollow()
        self.assertEqual(len(group_restricted_channel.channel_member_ids), 0)
        self.assertEqual(len(public_channel.channel_member_ids), 0)
        # sudo: mail.channel - reading members of non-accessible channel for testing purposes
        self.assertEqual(len(private_group.sudo().channel_member_ids), 0)
        # sudo: mail.channel - reading members of non-accessible channel for testing purposes
        self.assertEqual(len(chat_user_current.sudo().channel_member_ids), 0)

    def test_channel_unfollow_should_not_post_message_if_the_partner_has_been_removed(self):
        '''
        When a partner leaves a channel, the system will help post a message under
        that partner's name in the channel to notify others if `email_sent` is set `False`.
        The message should only be posted when the partner is still a member of the channel
        before method `_action_unfollow()` is called.
        If the partner has been removed earlier, no more messages will be posted
        even if `_action_unfollow()` is called again.
        '''
        channel = self.env['discuss.channel'].browse(self.test_channel.id)
        channel.add_members(self.test_partner.ids)

        # no message should be posted under test_partner's name
        messages_0 = self.env['mail.message'].search([
            ('model', '=', 'discuss.channel'),
            ('res_id', '=', channel.id),
            ('author_id', '=', self.test_partner.id)
        ])
        self.assertEqual(len(messages_0), 0)

        # a message should be posted to notify others when a partner is about to leave
        channel._action_unfollow(self.test_partner)
        messages_1 = self.env['mail.message'].search([
            ('model', '=', 'discuss.channel'),
            ('res_id', '=', channel.id),
            ('author_id', '=', self.test_partner.id)
        ])
        self.assertEqual(len(messages_1), 1)

        # no more messages should be posted if the partner has been removed before.
        channel._action_unfollow(self.test_partner)
        messages_2 = self.env['mail.message'].search([
            ('model', '=', 'discuss.channel'),
            ('res_id', '=', channel.id),
            ('author_id', '=', self.test_partner.id)
        ])
        self.assertEqual(len(messages_2), 1)
        self.assertEqual(messages_1, messages_2)

    def test_channel_should_generate_correct_default_avatar(self):
        test_channel = self.env['discuss.channel'].channel_create(name='Channel', group_id=self.env.ref('base.group_user').id)
        test_channel.uuid = 'channel-uuid'
        private_group = self.env['discuss.channel'].create_group(partners_to=self.user_employee.partner_id.ids)
        private_group.uuid = 'group-uuid'
        bgcolor_channel = html_escape('hsl(316, 61%, 45%)')  # depends on uuid
        bgcolor_group = html_escape('hsl(17, 60%, 45%)')  # depends on uuid
        expceted_avatar_channel = (channel_avatar.replace('fill="#875a7b"', f'fill="{bgcolor_channel}"')).encode()
        expected_avatar_group = (group_avatar.replace('fill="#875a7b"', f'fill="{bgcolor_group}"')).encode()

        self.assertEqual(base64.b64decode(test_channel.avatar_128), expceted_avatar_channel)
        self.assertEqual(base64.b64decode(private_group.avatar_128), expected_avatar_group)

        test_channel.image_128 = base64.b64encode(("<svg/>").encode())
        self.assertEqual(test_channel.avatar_128, test_channel.image_128)

    def test_channel_write_should_send_notification(self):
        channel = self.env['discuss.channel'].create({"name": "test", "description": "test"})
        self._reset_bus()
        with self.assertBus(
            [(self.cr.dbname, 'discuss.channel', channel.id)],
            [{
                "type": "mail.record/insert",
                "payload": {
                    'Thread': {
                        "id": channel.id,
                        "model": "discuss.channel",
                        "name": "test test",
                    }
                },
            }]
        ):
            channel.name = "test test"

    def test_channel_write_should_send_notification_if_image_128_changed(self):
        channel = self.env['discuss.channel'].create({'name': '', 'uuid': 'test-uuid'})
        # do the operation once before the assert to grab the value to expect
        channel.image_128 = base64.b64encode(("<svg/>").encode())
        avatar_cache_key = channel._get_avatar_cache_key()
        channel.image_128 = False
        self._reset_bus()
        with self.assertBus(
            [(self.cr.dbname, 'discuss.channel', channel.id)],
            [{
                "type": "mail.record/insert",
                "payload": {
                    'Thread': {
                        "id": channel.id,
                        'model': "discuss.channel",
                        "avatarCacheKey": avatar_cache_key,
                    }
                },
            }]
        ):
            channel.image_128 = base64.b64encode(("<svg/>").encode())

    def test_mail_message_starred_group(self):
        """ Test starred message computation for a group. A starred
        message in a group should be considered only if:
            - It's our message
            - OR we have access to the channel
        """
        self.assertEqual(self.user_employee._init_messaging()['starred_counter'], 0)
        test_group = self.env['discuss.channel'].create({
            'name': 'Private Channel',
            'channel_type': 'group',
            'channel_partner_ids': [(6, 0, self.partner_employee.id)]
        })

        test_group_own_message = test_group.with_user(self.user_employee.id).message_post(body='TestingMessage')
        test_group_own_message.write({'starred_partner_ids': [(6, 0, self.partner_employee.ids)]})
        self.assertEqual(self.user_employee.with_user(self.user_employee)._init_messaging()['starred_counter'], 1)

        test_group_message = test_group.message_post(body='TestingMessage')
        test_group_message.write({'starred_partner_ids': [(6, 0, self.partner_employee.ids)]})
        self.assertEqual(self.user_employee.with_user(self.user_employee)._init_messaging()['starred_counter'], 2)

        test_group.write({'channel_partner_ids': False})
        self.assertEqual(self.user_employee.with_user(self.user_employee)._init_messaging()['starred_counter'], 1)

    def test_multi_company_chat(self):
        self.assertEqual(self.env.user.company_id, self.company_admin)

        with self.with_user('employee'):
            chat = self.env['discuss.channel'].with_context(
                allowed_company_ids=self.company_admin.ids
            ).channel_get(self.partner_employee_c2.ids)
            self.assertTrue(chat, 'should be able to chat with multi company user')

    @users('employee')
    def test_create_chat_channel_should_only_pin_the_channel_for_the_current_user(self):
        chat = self.env['discuss.channel'].channel_get(partners_to=self.test_partner.ids)
        member_of_current_user = self.env['discuss.channel.member'].search([('channel_id', '=', chat.id), ('partner_id', '=', self.env.user.partner_id.id)])
        member_of_correspondent = self.env['discuss.channel.member'].search([('channel_id', '=', chat.id), ('partner_id', '=', self.test_partner.id)])
        self.assertTrue(member_of_current_user.is_pinned)
        self.assertFalse(member_of_correspondent.is_pinned)

    @users("employee")
    def test_channel_command_help_in_channel(self):
        """Ensures the command '/help' works in a channel"""
        channel = self.env["discuss.channel"].browse(self.test_channel.ids)
        channel.name = "<strong>R&D</strong>"
        self._reset_bus()
        with self.assertBus(
            [(self.env.cr.dbname, "res.partner", self.env.user.partner_id.id)],
            [
                {
                    "type": "discuss.channel/transient_message",
                    "payload": {
                        "body":
                            "<span class='o_mail_notification'>"
                            "You are in channel <b>#&lt;strong&gt;R&amp;D&lt;/strong&gt;</b>."
                            "<br><br>Type <b>@username</b> to mention someone, and grab their attention."
                            "<br>Type <b>#channel</b> to mention a channel."
                            "<br>Type <b>/command</b> to execute a command."
                            "</span>",
                        "model": "discuss.channel",
                        "res_id": channel.id,
                    },
                },
            ],
        ):
            channel.execute_command_help()

    def test_channel_command_help_in_group(self):
        """Ensures the command '/help' works in a group"""
        test_user = self.env['res.users'].create({
            "login": "mario",
            "name": "Mario",
        })
        self.partner_employee_nomail.name = f"<strong>{self.partner_employee_nomail.name}</strong>"
        # Guarantee that the channel member ids in the group are in order.
        test_group = self.env['discuss.channel'].create({
            'name': 'Private Channel',
            'channel_type': 'group',
            'channel_partner_ids': [(6, 0, test_user.partner_id.id)]
        })
        test_group.add_members(self.partner_employee_nomail.ids)
        self._reset_bus()
        with self.assertBus(
            [(self.env.cr.dbname, "res.partner", self.env.user.partner_id.id)],
            [
                {
                    "type": "discuss.channel/transient_message",
                    "payload": {
                        "body":
                            "<span class='o_mail_notification'>"
                            "You are in a private conversation with <b>@Mario</b> and <b>@&lt;strong&gt;Evita Employee NoEmail&lt;/strong&gt;</b>."
                            "<br><br>Type <b>@username</b> to mention someone, and grab their attention."
                            "<br>Type <b>#channel</b> to mention a channel."
                            "<br>Type <b>/command</b> to execute a command."
                            "</span>",
                        "model": "discuss.channel",
                        "res_id": test_group.id,
                    },
                },
            ],
        ):
            test_group.execute_command_help()

    def test_create_channel_with_partners_and_guests(self):
        channel = self.env['discuss.channel'].create({
            'name': 'test channel',
            'channel_member_ids': [
                (0, 0, {'guest_id': self.guest.id}),
                (0, 0, {'partner_id': self.partner_employee.id})
            ]
        })
        actual_member_ids = [m.partner_id.id if m.partner_id else m.guest_id.id for m in channel.channel_member_ids]
        expected_member_ids = [self.partner_employee.id, self.guest.id, self.env.user.partner_id.id]
        self.assertCountEqual(actual_member_ids, expected_member_ids)
