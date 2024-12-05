# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from datetime import datetime, timedelta
from freezegun import freeze_time
from unittest.mock import patch

from odoo import Command, fields
from odoo.addons.mail.models.discuss.discuss_channel import channel_avatar, group_avatar
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.mail.tools.discuss import Store
from odoo.exceptions import ValidationError
from odoo.tests import HttpCase, tagged, users
from odoo.tools import html_escape, mute_logger


@tagged("post_install", "-at_install")
class TestChannelInternals(MailCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.maxDiff = None
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
    @freeze_time("2020-03-22 10:42:06")
    def test_channel_members(self):
        channel = self.env['discuss.channel'].browse(self.test_channel.ids)
        self.assertEqual(channel.message_partner_ids, self.env['res.partner'])
        self.assertEqual(channel.channel_partner_ids, self.env['res.partner'])

        emp_partner_write_date = fields.Datetime.to_string(self.env.user.partner_id.write_date)
        test_partner_write_date = fields.Datetime.to_string(self.env.user.partner_id.write_date)

        def get_add_member_bus():
            message = self.env["mail.message"].search([], order="id desc", limit=1)
            member = self.env["discuss.channel.member"].search([], order="id desc", limit=1)
            return (
                [
                    (self.cr.dbname, "res.partner", self.test_partner.id),
                    (self.cr.dbname, "discuss.channel", channel.id),
                    (self.cr.dbname, "discuss.channel", channel.id, "members"),
                    (self.cr.dbname, "discuss.channel", channel.id),
                    (self.cr.dbname, "discuss.channel", channel.id),
                ],
                [
                    {
                        "type": "mail.record/insert",
                        "payload": {
                            "discuss.channel": [
                                {"id": channel.id, "last_interest_dt": "2020-03-22 10:42:06"},
                            ],
                        },
                    },
                    {
                        "type": "mail.record/insert",
                        "payload": {"discuss.channel": [{"id": channel.id, "is_pinned": True}]},
                    },
                    {
                        "type": "discuss.channel/new_message",
                        "payload": {
                            "data": {
                                "mail.message": self._filter_messages_fields(
                                    {
                                        "attachment_ids": [],
                                        "author": {
                                            "id": self.env.user.partner_id.id,
                                            "type": "partner",
                                        },
                                        "body": f'<div class="o_mail_notification">invited <a href="#" data-oe-model="res.partner" data-oe-id="{self.test_partner.id}">@Test Partner</a> to the channel</div>',
                                        "create_date": fields.Datetime.to_string(
                                            message.create_date
                                        ),
                                        "date": "2020-03-22 10:42:06",
                                        "default_subject": "Channel",
                                        "email_from": '"Ernest Employee" <e.e@example.com>',
                                        "id": message.id,
                                        "is_discussion": True,
                                        "is_note": False,
                                        "linkPreviews": [],
                                        "message_type": "notification",
                                        "model": "discuss.channel",
                                        "notifications": [],
                                        "parentMessage": False,
                                        "pinned_at": False,
                                        "rating_id": False,
                                        "reactions": [],
                                        "recipients": [],
                                        "record_name": "Channel",
                                        "res_id": channel.id,
                                        "scheduledDatetime": False,
                                        "subject": False,
                                        "subtype_description": False,
                                        "thread": {"id": channel.id, "model": "discuss.channel"},
                                        "write_date": fields.Datetime.to_string(message.write_date),
                                    },
                                ),
                                "mail.thread": self._filter_threads_fields(
                                    {
                                        "id": channel.id,
                                        "model": "discuss.channel",
                                        "module_icon": "/mail/static/description/icon.png",
                                        "rating_avg": 0.0,
                                        "rating_count": 0,
                                    },
                                ),
                                "res.partner": self._filter_partners_fields(
                                    {
                                        "id": self.env.user.partner_id.id,
                                        "isInternalUser": True,
                                        "is_company": False,
                                        "name": "Ernest Employee",
                                        "userId": self.env.user.id,
                                        "write_date": emp_partner_write_date,
                                    },
                                ),
                            },
                            "id": channel.id,
                        },
                    },
                    {
                        "type": "mail.record/insert",
                        "payload": {
                            "discuss.channel": [{"id": channel.id, "memberCount": 2}],
                            "discuss.channel.member": [
                                {
                                    "create_date": fields.Datetime.to_string(member.create_date),
                                    "fetched_message_id": False,
                                    "id": member.id,
                                    "last_seen_dt": False,
                                    "persona": {"id": self.test_partner.id, "type": "partner"},
                                    "seen_message_id": False,
                                    "thread": {"id": channel.id, "model": "discuss.channel"},
                                },
                            ],
                            "res.partner": self._filter_partners_fields(
                                {
                                    "active": True,
                                    "email": "test_customer@example.com",
                                    "id": self.test_partner.id,
                                    "im_status": "im_partner",
                                    "isInternalUser": False,
                                    "is_company": False,
                                    "name": "Test Partner",
                                    "out_of_office_date_end": False,
                                    "userId": False,
                                    "write_date": test_partner_write_date,
                                },
                            ),
                        },
                    },
                ],
            )
        self._reset_bus()
        with self.assertBus(get_params=get_add_member_bus):
            channel.add_members(self.test_partner.ids)

        def get_add_member_again_bus():
            member = self.env["discuss.channel.member"].search([], order="id desc", limit=1)
            return (
                [
                    (self.cr.dbname, "res.partner", self.env.user.partner_id.id),
                ],
                [
                    {
                        "type": "mail.record/insert",
                        "payload": {
                            "discuss.channel": [{"id": channel.id, "memberCount": 2}],
                            "discuss.channel.member": [
                                {
                                    "create_date": fields.Datetime.to_string(member.create_date),
                                    "fetched_message_id": False,
                                    "id": member.id,
                                    "last_seen_dt": False,
                                    "persona": {"id": self.test_partner.id, "type": "partner"},
                                    "seen_message_id": False,
                                    "thread": {"id": channel.id, "model": "discuss.channel"},
                                }
                            ],
                            "res.partner": self._filter_partners_fields(
                                {
                                    "active": True,
                                    "email": "test_customer@example.com",
                                    "id": self.test_partner.id,
                                    "im_status": "im_partner",
                                    "isInternalUser": False,
                                    "is_company": False,
                                    "name": "Test Partner",
                                    "out_of_office_date_end": False,
                                    "userId": False,
                                    "write_date": test_partner_write_date,
                                }
                            ),
                        },
                    },
                ],
            )
        self._reset_bus()
        with self.assertBus(get_params=get_add_member_again_bus):
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
        self.assertEqual(chat.last_interest_dt, post_time)

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
        channel = self.env["discuss.channel"].channel_get(partners_to=self.test_partner.ids)
        init_data = Store(channel).get_result()
        initial_channel_info = init_data["discuss.channel"][0]
        self.assertEqual(
            {persona["id"] for persona in init_data["res.partner"]},
            {self.partner_employee_nomail.id, self.test_partner.id}
        )

        # `channel_get` should return the existing channel every time the same partner is given
        same_channel = self.env['discuss.channel'].channel_get(partners_to=self.test_partner.ids)
        same_channel_info = Store(same_channel).get_result()["discuss.channel"][0]
        self.assertEqual(same_channel_info['id'], initial_channel_info['id'])

        # `channel_get` should return the existing channel when the current partner is given together with the other partner
        together_pids = (self.partner_employee_nomail + self.test_partner).ids
        together_channel = self.env['discuss.channel'].channel_get(partners_to=together_pids)
        together_channel_info = Store(together_channel).get_result()["discuss.channel"][0]
        self.assertEqual(together_channel_info['id'], initial_channel_info['id'])

        # `channel_get` should return a new channel the first time just the current partner is given,
        # even if a channel containing the current partner together with other partners already exists
        solo_pids = self.partner_employee_nomail.ids
        solo_channel = self.env['discuss.channel'].channel_get(partners_to=solo_pids)
        solo_channel_data = Store(solo_channel).get_result()
        solo_channel_info = solo_channel_data["discuss.channel"][0]
        self.assertNotEqual(solo_channel_info['id'], initial_channel_info['id'])
        self.assertEqual(
            {persona["id"] for persona in solo_channel_data["res.partner"]},
            {self.partner_employee_nomail.id},
        )

        # `channel_get` should return the existing channel every time the current partner is given
        same_solo_pids = self.partner_employee_nomail.ids
        same_solo_channel = self.env['discuss.channel'].channel_get(partners_to=same_solo_pids)
        same_solo_channel_info = Store(same_solo_channel).get_result()["discuss.channel"][0]
        self.assertEqual(same_solo_channel_info['id'], solo_channel_info['id'])

    # `channel_get` will pin the channel by default and thus last interest will be updated.
    @users('employee')
    def test_channel_info_get_should_update_last_interest_dt(self):
        self.env['discuss.channel'].channel_get(partners_to=self.partner_admin.ids)

        retrieve_time = datetime(2021, 1, 1, 0, 0)
        with patch.object(fields.Datetime, 'now', lambda: retrieve_time):
            # `last_interest_dt` should be updated again when `channel_get` is called
            # because `channel_pin` is called.
            channel = self.env["discuss.channel"].channel_get(
                partners_to=self.partner_admin.ids
            )
        self.assertEqual(
            fields.Datetime.to_string(
                channel.channel_member_ids.filtered(
                    lambda member: member.partner_id == self.env.user.partner_id
                ).last_interest_dt
            ),
            fields.Datetime.to_string(retrieve_time),
        )

    @users('employee')
    def test_channel_info_mark_as_read(self):
        """ In case of concurrent channel_seen RPC, ensure the oldest call has no effect. """
        pids = (self.partner_employee | self.user_admin.partner_id).ids
        chat = self.env['discuss.channel'].with_user(self.user_admin).channel_get(pids)
        msg_1 = self._add_messages(chat, 'Body1', author=self.user_employee.partner_id)
        msg_2 = self._add_messages(chat, 'Body2', author=self.user_employee.partner_id)
        self_member = chat.channel_member_ids.filtered(lambda m: m.partner_id == self.user_admin.partner_id)
        self_member._mark_as_read(msg_2.id)
        init_data = Store(chat).get_result()
        self_member_info = next(
            filter(lambda d: d["id"] == self_member.id, init_data["discuss.channel.member"])
        )
        self.assertEqual(
            self_member_info["seen_message_id"],
            msg_2.id,
            "Last message id should have been updated",
        )
        self_member._mark_as_read(msg_1.id)
        final_data = Store(chat).get_result()
        self_member_info = next(
            filter(lambda d: d["id"] == self_member.id, final_data["discuss.channel.member"])
        )
        self.assertEqual(
            self_member_info["seen_message_id"],
            msg_2.id,
            "Last message id should stay the same after mark channel as seen with an older message",
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
                (self.env.cr.dbname, "res.partner", self.user_admin.partner_id.id),
            ],
            [
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel.member": [
                            {
                                "id": member.id,
                                "message_unread_counter": 0,
                                "message_unread_counter_bus_id": 0,
                                "new_message_separator": msg_1.id + 1,
                                "persona": {"id": self.user_admin.partner_id.id, "type": "partner"},
                                "syncUnread": False,
                                "thread": {
                                    "id": chat.id,
                                    "model": "discuss.channel",
                                },
                            },
                        ],
                        "res.partner": self._filter_partners_fields(
                            {
                                "id": self.user_admin.partner_id.id,
                                "name": self.user_admin.partner_id.name,
                            },
                        ),
                    },
                },
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel.member": [
                            {
                                "id": member.id,
                                "persona": {"id": self.user_admin.partner_id.id, "type": "partner"},
                                "seen_message_id": msg_1.id,
                                "thread": {"id": chat.id, "model": "discuss.channel"},
                            },
                        ],
                        "res.partner": self._filter_partners_fields(
                            {
                                "id": self.user_admin.partner_id.id,
                                "name": self.user_admin.partner_id.name,
                            },
                        ),
                    },
                },
            ],
        ):
            member._mark_as_read(msg_1.id)
        # There should be no channel member to be set as seen in the second time
        # So no notification should be sent
        self._reset_bus()
        with self.assertBus([], []):
            member._mark_as_read(msg_1.id)

    def test_channel_message_post_should_not_allow_adding_wrong_parent(self):
        channels = self.env['discuss.channel'].create([{'name': '1'}, {'name': '2'}])
        message = self._add_messages(channels[0], 'Body1')
        message_2 = channels[1].message_post(body='Body2', parent_id=message.id)
        self.assertFalse(message_2.parent_id, "should not allow parent from wrong thread")
        message_3 = channels[1].message_post(body='Body3', parent_id=message.id + 100)
        self.assertFalse(message_3.parent_id, "should not allow non-existing parent")

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
        # sudo: discuss.channel - reading members of non-accessible channel for testing purposes
        self.assertEqual(len(private_group.sudo().channel_member_ids), 0)
        # sudo: discuss.channel - reading members of non-accessible channel for testing purposes
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
            [(self.cr.dbname, "discuss.channel", channel.id)],
            [
                {
                    "type": "mail.record/insert",
                    "payload": {"discuss.channel": [{"id": channel.id, "name": "test test"}]},
                }
            ],
        ):
            channel.name = "test test"

    def test_channel_write_should_send_notification_if_image_128_changed(self):
        channel = self.env['discuss.channel'].create({'name': '', 'uuid': 'test-uuid'})
        # do the operation once before the assert to grab the value to expect
        channel.image_128 = base64.b64encode(("<svg/>").encode())
        avatar_cache_key = channel.avatar_cache_key
        channel.image_128 = False
        self._reset_bus()
        with self.assertBus(
            [(self.cr.dbname, "discuss.channel", channel.id)],
            [
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel": [{"avatarCacheKey": avatar_cache_key, "id": channel.id}],
                    },
                }
            ],
        ):
            channel.image_128 = base64.b64encode(("<svg/>").encode())

    def test_channel_notification(self):
        all_test_user = mail_new_test_user(
            self.env,
            login="all",
            name="all",
            email="all@example.com",
            notification_type="inbox",
            groups="base.group_user",
        )
        mentions_test_user = mail_new_test_user(
            self.env,
            login="mentions",
            name="mentions",
            email="mentions@example.com",
            notification_type="inbox",
            groups="base.group_user",
        )
        nothing_test_user = mail_new_test_user(
            self.env,
            login="nothing",
            name="nothing",
            email="nothing@example.com",
            notification_type="inbox",
            groups="base.group_user",
        )
        all_test_user.res_users_settings_id.write({"channel_notifications": "all"})
        nothing_test_user.res_users_settings_id.write({"channel_notifications": "no_notif"})

        channel = self.env["discuss.channel"].channel_create(name="Channel", group_id=None)
        channel.add_members((self.partner_employee | all_test_user.partner_id | mentions_test_user.partner_id | nothing_test_user.partner_id).ids)

        # sending normal message
        with self.with_user("employee"):
            channel_msg = channel.message_post(body="Test", message_type="comment", subtype_xmlid="mail.mt_comment")
        all_notif = self.env["mail.notification"].search([
            ("mail_message_id", "=", channel_msg.id),
            ("res_partner_id", "=", all_test_user.partner_id.id)
        ])
        mentions_notif = self.env["mail.notification"].search([
            ("mail_message_id", "=", channel_msg.id),
            ("res_partner_id", "=", mentions_test_user.partner_id.id)
        ])
        nothing_notif = self.env["mail.notification"].search([
            ("mail_message_id", "=", channel_msg.id),
            ("res_partner_id", "=", nothing_test_user.partner_id.id)
        ])
        self.assertEqual(len(all_notif), 0, "all + normal message = no needaction")
        self.assertEqual(len(mentions_notif), 0, "mentions + normal message = no needaction")
        self.assertEqual(len(nothing_notif), 0, "nothing + normal message = no needaction")

        partner_ids = (
            all_test_user.partner_id + mentions_test_user.partner_id + nothing_test_user.partner_id
        ).ids
        self._reset_bus()
        with self.assertBusNotificationType(
            [
                ((self.cr.dbname, "res.partner", partner_id), "mail.message/inbox")
                for partner_id in partner_ids
            ],
        ):
            # sending mention message
            with self.with_user("employee"):
                channel_msg = channel.message_post(
                    body="Test @mentions",
                    partner_ids=partner_ids,
                    message_type="comment",
                    subtype_xmlid="mail.mt_comment",
                )
        all_notif = self.env["mail.notification"].search([
            ("mail_message_id", "=", channel_msg.id),
            ("res_partner_id", "=", all_test_user.partner_id.id)
        ])
        mentions_notif = self.env["mail.notification"].search([
            ("mail_message_id", "=", channel_msg.id),
            ("res_partner_id", "=", mentions_test_user.partner_id.id)
        ])
        nothing_notif = self.env["mail.notification"].search([
            ("mail_message_id", "=", channel_msg.id),
            ("res_partner_id", "=", nothing_test_user.partner_id.id)
        ])
        self.assertEqual(len(all_notif), 1, "all + mention message = needaction")
        self.assertEqual(len(mentions_notif), 1, "mentions + mention message = needaction")
        self.assertEqual(len(nothing_notif), 1, "nothing + mention message = no needaction")

        # mute the channel
        now = datetime.now()
        self.env["discuss.channel.member"].search([
            ("partner_id", "in", (all_test_user.partner_id + mentions_test_user.partner_id + nothing_test_user.partner_id).ids),
        ]).write({
            "mute_until_dt": now + timedelta(days=5),
        })

        # sending normal message
        with self.with_user("employee"):
            channel_msg = channel.message_post(body="Test", message_type="comment", subtype_xmlid="mail.mt_comment")
        all_notif = self.env["mail.notification"].search([
            ("mail_message_id", "=", channel_msg.id),
            ("res_partner_id", "=", all_test_user.partner_id.id)
        ])
        mentions_notif = self.env["mail.notification"].search([
            ("mail_message_id", "=", channel_msg.id),
            ("res_partner_id", "=", mentions_test_user.partner_id.id)
        ])
        nothing_notif = self.env["mail.notification"].search([
            ("mail_message_id", "=", channel_msg.id),
            ("res_partner_id", "=", nothing_test_user.partner_id.id)
        ])
        self.assertEqual(len(all_notif), 0, "mute + all + normal message = no needaction")
        self.assertEqual(len(mentions_notif), 0, "mute + mentions + normal message = no needaction")
        self.assertEqual(len(nothing_notif), 0, "mute + nothing + normal message = needaction")

        # sending mention message
        with self.with_user("employee"):
            channel_msg = channel.message_post(body="Test @mentions", partner_ids=(all_test_user.partner_id + mentions_test_user.partner_id + nothing_test_user.partner_id).ids, message_type="comment", subtype_xmlid="mail.mt_comment")
        all_notif = self.env["mail.notification"].search([
            ("mail_message_id", "=", channel_msg.id),
            ("res_partner_id", "=", all_test_user.partner_id.id)
        ])
        mentions_notif = self.env["mail.notification"].search([
            ("mail_message_id", "=", channel_msg.id),
            ("res_partner_id", "=", mentions_test_user.partner_id.id)
        ])
        nothing_notif = self.env["mail.notification"].search([
            ("mail_message_id", "=", channel_msg.id),
            ("res_partner_id", "=", nothing_test_user.partner_id.id)
        ])
        self.assertEqual(len(all_notif), 1, "mute + all + mention message = needaction")
        self.assertEqual(len(mentions_notif), 1, "mute + mentions + mention message = needaction")
        self.assertEqual(len(nothing_notif), 1, "mute + nothing + mention message = needaction")

    def test_mail_message_starred_group(self):
        """ Test starred message computation for a group. A starred
        message in a group should be considered only if:
            - It's our message
            - OR we have access to the channel
        """
        self.authenticate(self.user_employee.login, self.user_employee.login)
        self.assertEqual(self.make_jsonrpc_request("/mail/action", {"init_messaging": {}})["Store"]['starred']['counter'], 0)
        test_group = self.env['discuss.channel'].create({
            'name': 'Private Channel',
            'channel_type': 'group',
            'channel_partner_ids': [(6, 0, self.partner_employee.id)]
        })

        test_group_own_message = test_group.with_user(self.user_employee.id).message_post(body='TestingMessage')
        test_group_own_message.write({'starred_partner_ids': [(6, 0, self.partner_employee.ids)]})
        self.assertEqual(self.make_jsonrpc_request("/mail/action", {"init_messaging": {}})["Store"]['starred']['counter'], 1)

        test_group_message = test_group.message_post(body='TestingMessage')
        test_group_message.write({'starred_partner_ids': [(6, 0, self.partner_employee.ids)]})
        self.assertEqual(self.make_jsonrpc_request("/mail/action", {"init_messaging": {}})["Store"]['starred']['counter'], 2)

        test_group.write({'channel_partner_ids': False})
        self.assertEqual(self.make_jsonrpc_request("/mail/action", {"init_messaging": {}})["Store"]['starred']['counter'], 1)

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
                            "<br>Type <b>:shortcut</b> to insert a canned response in your message."
                            "</span>",
                        "thread": {
                            "id": channel.id,
                            "model": "discuss.channel",
                        },
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
                            "You are in a private conversation with "
                            f"<a href=# data-oe-model='res.partner' data-oe-id='{test_user.partner_id.id}'>@Mario</a> "
                            f"and <a href=# data-oe-model='res.partner' data-oe-id='{self.partner_employee_nomail.id}'>@&lt;strong&gt;Evita Employee NoEmail&lt;/strong&gt;</a>."
                            "<br><br>Type <b>@username</b> to mention someone, and grab their attention."
                            "<br>Type <b>#channel</b> to mention a channel."
                            "<br>Type <b>/command</b> to execute a command."
                            "<br>Type <b>:shortcut</b> to insert a canned response in your message."
                            "</span>",
                        "thread": {
                            "id": test_group.id,
                            "model": "discuss.channel",
                        },
                    },
                },
            ],
        ):
            test_group.execute_command_help()
