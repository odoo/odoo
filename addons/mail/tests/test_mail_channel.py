# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tests.common import MailCommon
from odoo.exceptions import AccessError, ValidationError, UserError
from odoo.tests import tagged, Form
from odoo.tests.common import users
from odoo.tools import mute_logger, formataddr


@tagged('mail_channel')
class TestChannelAccessRights(MailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestChannelAccessRights, cls).setUpClass()
        Channel = cls.env['mail.channel'].with_context(cls._test_context)

        cls.user_public = mail_new_test_user(cls.env, login='user_public', groups='base.group_public', name='Bert Tartignole')
        cls.user_portal = mail_new_test_user(cls.env, login='user_portal', groups='base.group_portal', name='Chell Gladys')

        # Pigs: base group for tests
        cls.group_groups = Channel.create({
            'name': 'Pigs',
            'public': 'groups',
            'group_public_id': cls.env.ref('base.group_user').id})
        # Jobs: public group
        cls.group_public = Channel.create({
            'name': 'Jobs',
            'description': 'NotFalse',
            'public': 'public'})
        # Private: private group
        cls.group_private = Channel.create({
            'name': 'Private',
            'public': 'private'})

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.addons.base.models.ir_model', 'odoo.models')
    @users('user_public')
    def test_access_public(self):
        # Read public group -> ok
        self.env['mail.channel'].browse(self.group_public.id).read()

        # Read groups -> ko, restricted to employees
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.group_groups.id).read()
        # Read private -> ko, restricted to members
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.group_private.id).read()

        # Read a private group when being a member: ok
        self.group_private.write({'channel_partner_ids': [(4, self.user_public.partner_id.id)]})
        self.env['mail.channel'].browse(self.group_private.id).read()

        # Create group: ko, no access rights
        with self.assertRaises(AccessError):
            self.env['mail.channel'].create({'name': 'Test'})

        # Update group: ko, no access rights
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.group_public.id).write({'name': 'Broutouschnouk'})

        # Unlink group: ko, no access rights
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.group_public.id).unlink()

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.models', 'odoo.models.unlink')
    @users('employee')
    def test_access_employee(self):
        # Employee read employee-based group: ok
        group_groups = self.env['mail.channel'].browse(self.group_groups.id)
        group_groups.read()

        # Employee can create a group
        new_channel = self.env['mail.channel'].create({'name': 'Test'})
        self.assertIn(new_channel.channel_partner_ids, self.partner_employee)

        # Employee update employee-based group: ok
        group_groups.write({'name': 'modified'})

        # Employee unlink employee-based group: ok
        group_groups.unlink()

        # Employee cannot read a private group
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.group_private.id).read()

        # Employee cannot write on private
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.group_private.id).write({'name': 're-modified'})

        # Employee cannot unlink private
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.group_private.id).unlink()

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.models')
    @users('user_portal')
    def test_access_portal(self):
        with self.assertRaises(AccessError):
            self.env['mail.channel'].browse(self.group_private.id).name

        self.group_private.write({'channel_partner_ids': [(4, self.user_portal.partner_id.id)]})
        group_private_portal = self.env['mail.channel'].browse(self.group_private.id)
        group_private_portal.read(['name'])
        for message in group_private_portal.message_ids:
            message.read(['subject'])

        # no access to followers (employee only)
        with self.assertRaises(AccessError):
            group_private_portal.message_partner_ids

        for partner in self.group_private.message_partner_ids:
            if partner.id == self.user_portal.partner_id.id:
                # Chell can read her own partner record
                continue
            with self.assertRaises(AccessError):
                trigger_read = partner.with_user(self.user_portal).name

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.addons.base.models.ir_model', 'odoo.models')
    @users('user_portal')
    def test_members(self):
        group_public = self.env['mail.channel'].browse(self.group_public.id)
        group_public.read(['name'])
        self.assertFalse(group_public.is_member)

        with self.assertRaises(AccessError):
            group_public.write({'name': 'Better Name'})

        with self.assertRaises(AccessError):
            group_public.action_follow()

        group_private = self.env['mail.channel'].browse(self.group_private.id)
        with self.assertRaises(AccessError):
            group_private.read(['name'])

        with self.assertRaises(AccessError):
            self.env['mail.channel.partner'].create({
                'partner_id': self.env.user.partner_id.id,
                'channel_id': group_private.id,
            })


@tagged('mail_channel')
class TestChannelInternals(MailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestChannelInternals, cls).setUpClass()
        cls.test_channel = cls.env['mail.channel'].with_context(cls._test_context).create({
            'name': 'Test',
            'channel_type': 'channel',
            'description': 'Description',
            'alias_name': 'test',
            'public': 'public',
        })
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
    def test_channel_form(self):
        """A user that create a private channel should be able to read it."""
        channel_form = Form(self.env['mail.channel'].with_user(self.user_employee))
        channel_form.name = 'Test private channel'
        channel_form.public = 'private'
        channel = channel_form.save()
        self.assertEqual(channel.name, 'Test private channel', 'Must be able to read the created channel')

    @users('employee')
    def test_channel_members(self):
        channel = self.env['mail.channel'].browse(self.test_channel.ids)
        self.assertEqual(channel.message_partner_ids, self.env['res.partner'])
        self.assertEqual(channel.channel_partner_ids, self.env['res.partner'])

        channel._action_add_members(self.test_partner)
        self.assertEqual(channel.message_partner_ids, self.env['res.partner'])
        self.assertEqual(channel.channel_partner_ids, self.test_partner)

        channel._action_remove_members(self.test_partner)
        self.assertEqual(channel.message_partner_ids, self.env['res.partner'])
        self.assertEqual(channel.channel_partner_ids, self.env['res.partner'])

        channel.message_post(body='Test', message_type='comment', subtype_xmlid='mail.mt_comment')
        self.assertEqual(channel.message_partner_ids, self.env['res.partner'])
        self.assertEqual(channel.channel_partner_ids, self.env['res.partner'])

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_channel_recipients_channel(self):
        """ Posting a message on a channel should not send emails """
        channel = self.env['mail.channel'].browse(self.test_channel.ids)
        channel._action_add_members(self.partner_employee | self.partner_admin | self.test_partner)
        with self.mock_mail_gateway():
            new_msg = channel.message_post(body="Test", message_type='comment', subtype_xmlid='mail.mt_comment')
        self.assertNotSentEmail()
        self.assertEqual(new_msg.model, self.test_channel._name)
        self.assertEqual(new_msg.res_id, self.test_channel.id)
        self.assertEqual(new_msg.partner_ids, self.env['res.partner'])
        self.assertEqual(new_msg.notified_partner_ids, self.env['res.partner'])

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_channel_recipients_chat(self):
        """ Posting a message on a chat should not send emails """
        self.test_channel.write({
            'channel_type': 'chat',
        })
        self.test_channel._action_add_members(self.partner_employee | self.partner_admin | self.test_partner)
        with self.mock_mail_gateway():
            with self.with_user('employee'):
                channel = self.env['mail.channel'].browse(self.test_channel.ids)
                new_msg = channel.message_post(body="Test", message_type='comment', subtype_xmlid='mail.mt_comment')
        self.assertNotSentEmail()
        self.assertEqual(new_msg.model, self.test_channel._name)
        self.assertEqual(new_msg.res_id, self.test_channel.id)
        self.assertEqual(new_msg.partner_ids, self.env['res.partner'])
        self.assertEqual(new_msg.notified_partner_ids, self.env['res.partner'])

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_channel_recipients_mention(self):
        """ Posting a message on a classic channel should support mentioning somebody """
        self.test_channel.write({'alias_name': False})
        with self.mock_mail_gateway():
            self.test_channel.message_post(
                body="Test", partner_ids=self.test_partner.ids,
                message_type='comment', subtype_xmlid='mail.mt_comment')
        self.assertSentEmail(self.test_channel.env.user.partner_id, [self.test_partner])

    @mute_logger('odoo.models.unlink')
    def test_channel_user_synchronize(self):
        """Archiving / deleting a user should automatically unsubscribe related partner from private channels"""
        test_channel_private = self.env['mail.channel'].with_context(self._test_context).create({
            'name': 'Winden caves',
            'description': 'Channel to travel through time',
            'public': 'private',
        })
        test_channel_group = self.env['mail.channel'].with_context(self._test_context).create({
            'name': 'Sic Mundus',
            'public': 'groups',
            'group_public_id': self.env.ref('base.group_user').id})

        self.test_channel._action_add_members(self.partner_employee | self.partner_employee_nomail)
        test_channel_private._action_add_members(self.partner_employee | self.partner_employee_nomail)
        test_channel_group._action_add_members(self.partner_employee | self.partner_employee_nomail)

        # Unsubscribe archived user from the private channels, but not from public channels
        self.user_employee.active = False
        self.assertEqual(test_channel_private.channel_partner_ids, self.partner_employee_nomail)
        self.assertEqual(test_channel_group.channel_partner_ids, self.partner_employee_nomail)
        self.assertEqual(self.test_channel.channel_partner_ids, self.user_employee.partner_id | self.partner_employee_nomail)

        # Unsubscribe deleted user from the private channels, but not from public channels
        self.user_employee_nomail.unlink()
        self.assertEqual(test_channel_private.channel_partner_ids, self.env['res.partner'])
        self.assertEqual(test_channel_group.channel_partner_ids, self.env['res.partner'])
        self.assertEqual(self.test_channel.channel_partner_ids, self.user_employee.partner_id | self.partner_employee_nomail)

    @users('employee_nomail')
    def test_channel_info_get(self):
        # `channel_get` should return a new channel the first time a partner is given
        initial_channel_info = self.env['mail.channel'].channel_get(partners_to=self.test_partner.ids)
        self.assertEqual(set(p['id'] for p in initial_channel_info['members']), {self.partner_employee_nomail.id, self.test_partner.id})

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
        self.assertEqual(set(p['id'] for p in solo_channel_info['members']), {self.partner_employee_nomail.id})

        # `channel_get` should return the existing channel every time the current partner is given
        same_solo_channel_info = self.env['mail.channel'].channel_get(partners_to=self.partner_employee_nomail.ids)
        self.assertEqual(same_solo_channel_info['id'], solo_channel_info['id'])

    @users('employee')
    def test_channel_info_seen(self):
        """ In case of concurrent channel_seen RPC, ensure the oldest call has no effect. """
        channel = self.env['mail.channel'].browse(self.test_channel.id)
        channel.write({'channel_type': 'chat'})
        channel.action_follow()

        msg_1 = self._add_messages(self.test_channel, 'Body1', author=self.user_employee.partner_id)
        msg_2 = self._add_messages(self.test_channel, 'Body2', author=self.user_employee.partner_id)

        self.test_channel.channel_seen(msg_2.id)
        self.assertEqual(
            channel.channel_info()[0]['seen_partners_info'][0]['seen_message_id'],
            msg_2.id,
            "Last message id should have been updated"
        )

        self.test_channel.channel_seen(msg_1.id)
        self.assertEqual(
            channel.channel_info()[0]['seen_partners_info'][0]['seen_message_id'],
            msg_2.id,
            "Last message id should stay the same after mark channel as seen with an older message"
        )

    @mute_logger('odoo.models.unlink')
    def test_channel_unsubscribe_auto(self):
        """ Archiving / deleting a user should automatically unsubscribe related
        partner from private channels """
        test_user = self.env['res.users'].create({
            "login": "adam",
            "name": "Jonas",
        })
        test_partner = test_user.partner_id
        test_channel_private = self.env['mail.channel'].with_context(self._test_context).create({
            'name': 'Winden caves',
            'description': 'Channel to travel through time',
            'public': 'private',
            'channel_partner_ids': [Command.link(self.user_employee.partner_id.id), Command.link(test_partner.id)],
        })
        test_channel_group = self.env['mail.channel'].with_context(self._test_context).create({
            'name': 'Sic Mundus',
            'public': 'groups',
            'group_public_id': self.env.ref('base.group_user').id,
            'channel_partner_ids': [Command.link(self.user_employee.partner_id.id), Command.link(test_partner.id)],
        })
        self.test_channel.with_context(self._test_context).write({
            'channel_partner_ids': [Command.link(self.user_employee.partner_id.id), Command.link(test_partner.id)],
        })
        test_chat = self.env['mail.channel'].with_context(self._test_context).create({
            'name': 'test',
            'channel_type': 'chat',
            'public': 'private',
            'channel_partner_ids': [Command.link(self.user_employee.partner_id.id), Command.link(test_partner.id)],
        })

        # Unsubscribe archived user from the private channels, but not from public channels and not from chat
        self.user_employee.active = False
        (test_chat | self.test_channel).invalidate_cache(fnames=['channel_partner_ids'])
        self.assertEqual(test_channel_private.channel_partner_ids, test_partner)
        self.assertEqual(test_channel_group.channel_partner_ids, test_partner)
        self.assertEqual(self.test_channel.channel_partner_ids, self.user_employee.partner_id | test_partner)
        self.assertEqual(test_chat.channel_partner_ids, self.user_employee.partner_id | test_partner)

        # Unsubscribe deleted user from the private channels, but not from public channels and not from chat
        test_user.unlink()
        self.assertEqual(test_channel_private.channel_partner_ids, self.env['res.partner'])
        self.assertEqual(test_channel_group.channel_partner_ids, self.env['res.partner'])
        self.assertEqual(self.test_channel.channel_partner_ids, self.user_employee.partner_id | test_partner)
        self.assertEqual(test_chat.channel_partner_ids, self.user_employee.partner_id | test_partner)

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
        channel._action_add_members(self.test_partner)

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

    def test_multi_company_chat(self):
        self._activate_multi_company()
        self.assertEqual(self.env.user.company_id, self.company_admin)

        with self.with_user('employee'):
            initial_channel_info = self.env['mail.channel'].with_context(
                allowed_company_ids=self.company_admin.ids
            ).channel_get(self.partner_employee_c2.ids)
            self.assertTrue(initial_channel_info, 'should be able to chat with multi company user')
