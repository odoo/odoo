# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from datetime import datetime
from unittest.mock import patch

from odoo import Command, fields
from odoo.addons.mail.models.mail_channel import channel_avatar, group_avatar
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tests.common import MailCommon
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged, Form
from odoo.tests.common import users
from odoo.tools import html_escape, mute_logger
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT


@tagged('mail_channel')
class TestChannelAccessRights(MailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestChannelAccessRights, cls).setUpClass()

        cls.user_employee_1 = mail_new_test_user(cls.env, login='user_employee_1', groups='base.group_user', name='Tao Lee')
        cls.user_public = mail_new_test_user(cls.env, login='user_public', groups='base.group_public', name='Bert Tartignole')
        cls.user_portal = mail_new_test_user(cls.env, login='user_portal', groups='base.group_portal', name='Chell Gladys')

        # Channel for certain group
        cls.group_restricted_channel = cls.env['mail.channel'].browse(cls.env['mail.channel'].channel_create(name='Channel for Groups', group_id=cls.env.ref('base.group_user').id)['id'])
        # Public Channel
        cls.public_channel = cls.env['mail.channel'].browse(cls.env['mail.channel'].channel_create(name='Public Channel', group_id=None)['id'])
        # Group
        cls.private_group = cls.env['mail.channel'].browse(cls.env['mail.channel'].create_group(partners_to=cls.user_employee.partner_id.ids, name="Group")['id'])
        # Chat
        cls.chat_user_employee = cls.env['mail.channel'].browse(cls.env['mail.channel'].channel_get(cls.user_employee.partner_id.ids)['id'])
        cls.chat_user_employee_1 = cls.env['mail.channel'].browse(cls.env['mail.channel'].channel_get(cls.user_employee_1.partner_id.ids)['id'])
        cls.chat_user_portal = cls.env['mail.channel'].browse(cls.env['mail.channel'].channel_get(cls.user_portal.partner_id.ids)['id'])
        cls.chat_user_public = cls.env['mail.channel'].browse(cls.env['mail.channel'].channel_get(cls.user_public.partner_id.ids)['id'])

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.addons.base.models.ir_model', 'odoo.models')
    @users('user_public')
    def test_access_public(self):
        # Read public channel -> ok
        self.env['mail.channel'].browse(self.public_channel.id).read()

        # Read group restricted channel -> ko, no access rights
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.group_restricted_channel.id).read()
        # Read group -> ko, no access rights
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.private_group.id).read()

        # Being a member of public channel: -> ok
        self.public_channel.add_members(self.user_public.partner_id.id)
        # Being a member of group restricted channel: -> ko, no access rights
        with self.assertRaises(UserError):
            self.group_restricted_channel.add_members(self.user_public.partner_id.id)
        # Being a group member: -> ok
        self.private_group.add_members(self.user_public.partner_id.id)

        # Read a group when being a member: -> ko, no access rights
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.private_group.id).read()
        # Read a chat when being a member: -> ko, no access rights
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.chat_user_public.id).read()

        # Create channel/group/chat: ko, no access rights
        with self.assertRaises(AccessError):
            self.env['mail.channel'].create({'name': 'Test', 'channel_type': 'channel'})
        with self.assertRaises(AccessError):
            self.env['mail.channel'].create({'name': 'Test', 'channel_type': 'group'})
        with self.assertRaises(AccessError):
            self.env['mail.channel'].create({'name': 'Test', 'channel_type': 'chat'})

        # Update channel/group/chat: ko, no access rights
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.public_channel.id).write({'name': 'modified'})
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.group_restricted_channel.id).write({'name': 'modified'})
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.private_group.id).write({'name': 'modified'})
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.chat_user_public.id).write({'name': 'modified'})

        # Unlink channel/group/chat: ko, no access rights
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.public_channel.id).unlink()
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.group_restricted_channel.id).unlink()
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.private_group.id).unlink()
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.chat_user_public.id).unlink()

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.addons.base.models.ir_model', 'odoo.models')
    @users('employee')
    def test_access_employee(self):
        # Read public channel -> ok
        self.env['mail.channel'].browse(self.public_channel.id).read()
        # Read group restricted channel -> ok
        self.env['mail.channel'].browse(self.group_restricted_channel.id).read()
        # Read chat when not being a member: ko, no access rights
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.chat_user_employee_1.id).read()

        # Update chat when not being a member: ko, no access rights
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.chat_user_employee_1.id).write({'name': 'modified'})

        # Being a channel/group member: -> ok
        self.public_channel.add_members(self.user_public.partner_id.id)
        self.group_restricted_channel.add_members(self.env.user.partner_id.id)
        self.private_group.add_members(self.env.user.partner_id.id)

        # Read a group when being a member: ok
        self.env['mail.channel'].browse(self.private_group.id).read()
        # Read a chat when being a member: ok
        self.env['mail.channel'].browse(self.chat_user_employee.id).read()

        # Update channel/group/chat when being a member: ok
        self.env['mail.channel'].browse(self.public_channel.id).write({'name': 'modified again'})
        self.env['mail.channel'].browse(self.group_restricted_channel.id).write({'name': 'modified again'})
        self.env['mail.channel'].browse(self.private_group.id).write({'name': 'modified again'})
        self.env['mail.channel'].browse(self.chat_user_employee.id).write({'name': 'modified again'})

        # Create channel/group/chat: ok
        new_channel = self.env['mail.channel'].create(
            {'name': 'Test', 'channel_type': 'channel'})
        new_group = self.env['mail.channel'].create(
            {'name': 'Test', 'channel_type': 'group'})
        new_chat = self.env['mail.channel'].create(
            {'name': 'Test', 'channel_type': 'chat'})

        # Employee should be inside the created chat/group/chat
        self.assertIn(new_channel.channel_partner_ids, self.partner_employee)
        self.assertIn(new_group.channel_partner_ids, self.partner_employee)
        self.assertIn(new_chat.channel_partner_ids, self.partner_employee)

        # Unlink channel/group/chat: ko, no access rights
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.public_channel.id).unlink()
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.group_restricted_channel.id).unlink()
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.private_group.id).unlink()
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.chat_user_employee.id).unlink()

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.addons.base.models.ir_model', 'odoo.models')
    @users('user_portal')
    def test_access_portal(self):
        # Read public channel -> ok
        self.env['mail.channel'].browse(self.public_channel.id).read()
        # Read group restricted channel/group -> ko, no access rights
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.group_restricted_channel.id).read()
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.private_group.id).read()

        # Being a group member: -> ok
        self.private_group.add_members(self.user_portal.partner_id.id)

        # Read a group/chat when being a member: ok
        self.env['mail.channel'].browse(self.private_group.id).read()
        self.env['mail.channel'].browse(self.chat_user_portal.id).read()

        # Update group/chat when being a member: ko, no access rights
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.private_group.id).write({'name': 'modified'})
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.chat_user_portal.id).write({'name': 'modified'})

        # Create group/chat: ko, no access rights
        with self.assertRaises(AccessError):
            self.env['mail.channel'].create({'name': 'Test', 'channel_type': 'group'})
        with self.assertRaises(AccessError):
            self.env['mail.channel'].create({'name': 'Test', 'channel_type': 'chat'})

        # Unlink group/chat: ko, no access rights
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.private_group.id).unlink()
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.chat_user_portal.id).unlink()

        # Read message from group/chat: ok
        group_portal = self.env['mail.channel'].browse(self.private_group.id)
        for message in group_portal.message_ids:
            message.read(['subject'])
        chat_portal = self.env['mail.channel'].browse(self.chat_user_portal.id)
        for message in chat_portal.message_ids:
            message.read(['subject'])

        # Read partner list from group: ko, no access rights
        with self.assertRaises(AccessError):
            group_portal.message_partner_ids
        for partner in self.private_group.message_partner_ids:
            if partner.id == self.user_portal.partner_id.id:
                # Portal user can read their own partner record
                continue
            with self.assertRaises(AccessError):
                partner.with_user(self.user_portal).name

        # Read partner list from chat: ko, no access rights
        with self.assertRaises(AccessError):
            chat_portal.message_partner_ids
        for partner in self.chat_user_portal.message_partner_ids:
            if partner.id == self.user_portal.partner_id.id:
                # Portal user can read their own partner record
                continue
            with self.assertRaises(AccessError):
                partner.with_user(self.user_portal).name


@tagged('mail_channel')
class TestChannelInternals(MailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestChannelInternals, cls).setUpClass()
        cls.test_channel = cls.env['mail.channel'].browse(cls.env['mail.channel'].with_context(cls._test_context).channel_create(name='Channel', group_id=None)['id'])
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

    @users('employee')
    def test_channel_members(self):
        channel = self.env['mail.channel'].browse(self.test_channel.ids)
        self.assertEqual(channel.message_partner_ids, self.env['res.partner'])
        self.assertEqual(channel.channel_partner_ids, self.env['res.partner'])

        channel.add_members(self.test_partner.ids)
        self.assertEqual(channel.message_partner_ids, self.env['res.partner'])
        self.assertEqual(channel.channel_partner_ids, self.test_partner)

        self.env['mail.channel.member'].sudo().search([
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
        channel_info = self.env['mail.channel'].with_user(self.user_admin).channel_get((self.partner_employee | self.user_admin.partner_id).ids)
        chat = self.env['mail.channel'].with_user(self.user_admin).browse(channel_info['id'])
        post_time = fields.Datetime.now()
        # Mocks the return value of field.Datetime.now(),
        # so we can see if the `last_interest_dt` is updated correctly
        with patch.object(fields.Datetime, 'now', lambda: post_time):
            chat.message_post(body="Test", message_type='comment', subtype_xmlid='mail.mt_comment')
        channel_member_employee = self.env['mail.channel.member'].search([
            ('partner_id', '=', self.partner_employee.id),
            ('channel_id', '=', chat.id),
        ])
        channel_member_admin = self.env['mail.channel.member'].search([
            ('partner_id', '=', self.partner_admin.id),
            ('channel_id', '=', chat.id),
        ])
        self.assertEqual(channel_member_employee.last_interest_dt, post_time)
        self.assertEqual(channel_member_admin.last_interest_dt, post_time)

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_channel_recipients_channel(self):
        """ Posting a message on a channel should not send emails """
        channel = self.env['mail.channel'].browse(self.test_channel.ids)
        channel.add_members((self.partner_employee | self.partner_admin | self.test_partner).ids)
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
        channel_info = self.env['mail.channel'].with_user(self.user_admin).channel_get((self.partner_employee | self.user_admin.partner_id).ids)
        chat = self.env['mail.channel'].with_user(self.user_admin).browse(channel_info['id'])
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
        group_restricted_channel = self.env['mail.channel'].browse(self.env['mail.channel'].channel_create(name='Sic Mundus', group_id=self.env.ref('base.group_user').id)['id'])

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
        initial_channel_info = self.env['mail.channel'].channel_get(partners_to=self.test_partner.ids)
        # shape of channelMembers is [('insert', data...)], [0][1] accesses the data
        self.assertEqual(set(m['persona']['partner']['id'] for m in initial_channel_info['channel']['channelMembers'][0][1]), {self.partner_employee_nomail.id, self.test_partner.id})

        # `channel_get` should return the existing channel every time the same partner is given
        same_channel_info = self.env['mail.channel'].channel_get(partners_to=self.test_partner.ids)
        self.assertEqual(same_channel_info['id'], initial_channel_info['id'])

        # `channel_get` should return the existing channel when the current partner is given together with the other partner
        together_channel_info = self.env['mail.channel'].channel_get(partners_to=(self.partner_employee_nomail + self.test_partner).ids)
        self.assertEqual(together_channel_info['id'], initial_channel_info['id'])

        # `channel_get` should return a new channel the first time just the current partner is given,
        # even if a channel containing the current partner together with other partners already exists
        solo_channel_info = self.env['mail.channel'].channel_get(partners_to=self.partner_employee_nomail.ids)
        self.assertNotEqual(solo_channel_info['id'], initial_channel_info['id'])
        # shape of channelMembers is [('insert', data...)], [0][1] accesses the data
        self.assertEqual(set(m['persona']['partner']['id'] for m in solo_channel_info['channel']['channelMembers'][0][1]), {self.partner_employee_nomail.id})

        # `channel_get` should return the existing channel every time the current partner is given
        same_solo_channel_info = self.env['mail.channel'].channel_get(partners_to=self.partner_employee_nomail.ids)
        self.assertEqual(same_solo_channel_info['id'], solo_channel_info['id'])

    # `channel_get` will pin the channel by default and thus last interest will be updated.
    @users('employee')
    def test_channel_info_get_should_update_last_interest_dt(self):
        # create the channel via `channel_get`
        self.env['mail.channel'].channel_get(partners_to=self.partner_admin.ids)

        retrieve_time = datetime(2021, 1, 1, 0, 0)
        with patch.object(fields.Datetime, 'now', lambda: retrieve_time):
            # `last_interest_dt` should be updated again when `channel_get` is called
            # because `channel_pin` is called.
            channel_info = self.env['mail.channel'].channel_get(partners_to=self.partner_admin.ids)
        self.assertEqual(channel_info['last_interest_dt'], retrieve_time.strftime(DEFAULT_SERVER_DATETIME_FORMAT))

    @users('employee')
    def test_channel_info_seen(self):
        """ In case of concurrent channel_seen RPC, ensure the oldest call has no effect. """
        channel_info = self.env['mail.channel'].with_user(self.user_admin).channel_get((self.partner_employee | self.user_admin.partner_id).ids)
        chat = self.env['mail.channel'].with_user(self.user_admin).browse(channel_info['id'])
        msg_1 = self._add_messages(chat, 'Body1', author=self.user_employee.partner_id)
        msg_2 = self._add_messages(chat, 'Body2', author=self.user_employee.partner_id)

        chat._channel_seen(msg_2.id)
        self.assertEqual(
            chat.channel_info()[0]['seen_partners_info'][0]['seen_message_id'],
            msg_2.id,
            "Last message id should have been updated"
        )

        chat._channel_seen(msg_1.id)
        self.assertEqual(
            chat.channel_info()[0]['seen_partners_info'][0]['seen_message_id'],
            msg_2.id,
            "Last message id should stay the same after mark channel as seen with an older message"
        )

    def test_channel_message_post_should_not_allow_adding_wrong_parent(self):
        channels = self.env['mail.channel'].create([{'name': '1'}, {'name': '2'}])
        message = self._add_messages(channels[0], 'Body1')
        message_format2 = channels[1].message_post(body='Body2', parent_id=message.id)
        self.assertFalse(message_format2['parent_id'], "should not allow parent from wrong thread")
        message_format3 = channels[1].message_post(body='Body3', parent_id=message.id + 100)
        self.assertFalse(message_format3['parent_id'], "should not allow non-existing parent")

    @mute_logger('odoo.models.unlink')
    def test_channel_unsubscribe_auto(self):
        """ Archiving / deleting a user should automatically unsubscribe related
        partner from private channels """
        test_user = self.env['res.users'].create({
            "login": "adam",
            "name": "Jonas",
        })
        test_partner = test_user.partner_id
        group_restricted_channel = self.env['mail.channel'].with_context(self._test_context).create({
            'name': 'Sic Mundus',
            'group_public_id': self.env.ref('base.group_user').id,
            'channel_partner_ids': [Command.link(self.user_employee.partner_id.id), Command.link(test_partner.id)],
        })
        self.test_channel.with_context(self._test_context).write({
            'channel_partner_ids': [Command.link(self.user_employee.partner_id.id), Command.link(test_partner.id)],
        })
        private_group = self.env['mail.channel'].with_user(self.user_employee).with_context(self._test_context).create({
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
        group_restricted_channel = self.env['mail.channel'].browse(self.env['mail.channel'].channel_create(name='Channel for Groups', group_id=self.env.ref('base.group_user').id)['id'])
        public_channel = self.env['mail.channel'].browse(self.env['mail.channel'].channel_create(name='Channel for Everyone', group_id=None)['id'])
        private_group = self.env['mail.channel'].browse(self.env['mail.channel'].create_group(partners_to=self.user_employee.partner_id.ids, name="Group")['id'])
        chat_user_current = self.env['mail.channel'].browse(self.env['mail.channel'].channel_get(self.env.user.partner_id.ids)['id'])

        group_restricted_channel.add_members(self.env.user.partner_id.id)
        public_channel.add_members(self.env.user.partner_id.id)

        group_restricted_channel.action_unfollow()
        public_channel.action_unfollow()
        private_group.action_unfollow()
        chat_user_current.action_unfollow()

        self.assertEqual(group_restricted_channel.channel_partner_ids, self.env['res.partner'])
        self.assertEqual(public_channel.channel_partner_ids, self.env['res.partner'])
        self.assertEqual(private_group.channel_partner_ids, self.env['res.partner'])
        self.assertEqual(chat_user_current.channel_partner_ids, self.env['res.partner'])

    def test_channel_unfollow_should_not_post_message_if_the_partner_has_been_removed(self):
        '''
        When a partner leaves a channel, the system will help post a message under
        that partner's name in the channel to notify others if `email_sent` is set `False`.
        The message should only be posted when the partner is still a member of the channel
        before method `_action_unfollow()` is called.
        If the partner has been removed earlier, no more messages will be posted
        even if `_action_unfollow()` is called again.
        '''
        channel = self.env['mail.channel'].browse(self.test_channel.id)
        channel.add_members(self.test_partner.ids)

        # no message should be posted under test_partner's name
        messages_0 = self.env['mail.message'].search([
            ('model', '=', 'mail.channel'),
            ('res_id', '=', channel.id),
            ('author_id', '=', self.test_partner.id)
        ])
        self.assertEqual(len(messages_0), 0)

        # a message should be posted to notify others when a partner is about to leave
        channel._action_unfollow(self.test_partner)
        messages_1 = self.env['mail.message'].search([
            ('model', '=', 'mail.channel'),
            ('res_id', '=', channel.id),
            ('author_id', '=', self.test_partner.id)
        ])
        self.assertEqual(len(messages_1), 1)

        # no more messages should be posted if the partner has been removed before.
        channel._action_unfollow(self.test_partner)
        messages_2 = self.env['mail.message'].search([
            ('model', '=', 'mail.channel'),
            ('res_id', '=', channel.id),
            ('author_id', '=', self.test_partner.id)
        ])
        self.assertEqual(len(messages_2), 1)
        self.assertEqual(messages_1, messages_2)

    def test_channel_should_generate_correct_default_avatar(self):
        test_channel = self.env['mail.channel'].browse(self.env['mail.channel'].channel_create(name='Channel', group_id=self.env.ref('base.group_user').id)['id'])
        test_channel.uuid = 'channel-uuid'
        private_group = self.env['mail.channel'].browse(self.env['mail.channel'].create_group(partners_to=self.user_employee.partner_id.ids)['id'])
        private_group.uuid = 'group-uuid'
        bgcolor_channel = html_escape('hsl(316, 61%, 45%)')  # depends on uuid
        bgcolor_group = html_escape('hsl(17, 60%, 45%)')  # depends on uuid
        expceted_avatar_channel = (channel_avatar.replace('fill="#875a7b"', f'fill="{bgcolor_channel}"')).encode()
        expected_avatar_group = (group_avatar.replace('fill="#875a7b"', f'fill="{bgcolor_group}"')).encode()

        self.assertEqual(base64.b64decode(test_channel.avatar_128), expceted_avatar_channel)
        self.assertEqual(base64.b64decode(private_group.avatar_128), expected_avatar_group)

        test_channel.image_128 = base64.b64encode(("<svg/>").encode())
        self.assertEqual(test_channel.avatar_128, test_channel.image_128)

    def test_channel_write_should_send_notification_if_image_128_changed(self):
        channel = self.env['mail.channel'].create({'name': '', 'uuid': 'test-uuid'})
        # do the operation once before the assert to grab the value to expect
        channel.image_128 = base64.b64encode(("<svg/>").encode())
        avatar_cache_key = channel._get_avatar_cache_key()
        channel.image_128 = False
        self.env['bus.bus'].search([]).unlink()
        with self.assertBus(
            [(self.cr.dbname, 'mail.channel', channel.id)],
            [{
                "type": "mail.channel/insert",
                "payload": {
                    "avatarCacheKey": avatar_cache_key,
                    "id": channel.id,
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
        test_group = self.env['mail.channel'].create({
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
        self._activate_multi_company()
        self.assertEqual(self.env.user.company_id, self.company_admin)

        with self.with_user('employee'):
            initial_channel_info = self.env['mail.channel'].with_context(
                allowed_company_ids=self.company_admin.ids
            ).channel_get(self.partner_employee_c2.ids)
            self.assertTrue(initial_channel_info, 'should be able to chat with multi company user')
