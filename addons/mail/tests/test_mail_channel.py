# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tests.common import MailCommon
from odoo.exceptions import AccessError, ValidationError, UserError
from odoo.tests import tagged, Form
from odoo.tests.common import users
from odoo.tools import mute_logger, formataddr


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


class TestChannelInternals(MailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestChannelInternals, cls).setUpClass()
        cls.test_channel = cls.env['mail.channel'].with_context(cls._test_context).create({
            'name': 'Test',
            'channel_type': 'channel',
            'email_send': False,
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

    def test_channel_members(self):
        self.assertEqual(self.test_channel.message_channel_ids, self.test_channel)
        self.assertEqual(self.test_channel.message_partner_ids, self.env['res.partner'])
        self.assertEqual(self.test_channel.channel_partner_ids, self.env['res.partner'])

        self.test_channel._action_add_members(self.test_partner)
        self.assertEqual(self.test_channel.message_channel_ids, self.test_channel)
        self.assertEqual(self.test_channel.message_partner_ids, self.env['res.partner'])
        self.assertEqual(self.test_channel.channel_partner_ids, self.test_partner)

        self.test_channel._action_remove_members(self.test_partner)
        self.assertEqual(self.test_channel.message_channel_ids, self.test_channel)
        self.assertEqual(self.test_channel.message_partner_ids, self.env['res.partner'])
        self.assertEqual(self.test_channel.channel_partner_ids, self.env['res.partner'])

        self.test_channel.message_post(body='Test', message_type='comment', subtype_xmlid='mail.mt_comment')
        self.assertEqual(self.test_channel.message_channel_ids, self.test_channel)
        self.assertEqual(self.test_channel.message_partner_ids, self.env['res.partner'])
        self.assertEqual(self.test_channel.channel_partner_ids, self.env['res.partner'])

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_channel_recipients_chat(self):
        """ Posting a message on a chat should not send emails """
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', 'schlouby.fr')
        self.test_channel.write({'email_send': False})
        self.test_channel._action_add_members(self.user_employee.partner_id | self.test_partner)
        with self.mock_mail_gateway():
            self.test_channel.message_post(body="Test", message_type='comment', subtype_xmlid='mail.mt_comment')
        self.assertNotSentEmail()
        self.assertEqual(len(self._mails), 0)

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_channel_recipients_mailing_list(self):
        """ Posting a message on a mailing list should send one email to all recipients """
        self.test_channel.write({'email_send': True})
        self.user_employee.write({'notification_type': 'email'})

        # Subscribe an user without email. We shouldn't try to send email to them.
        self.test_channel._action_add_members(self.user_employee.partner_id | self.test_partner | self.partner_employee_nomail)
        with self.mock_mail_gateway():
            self.test_channel.message_post(body="Test", message_type='comment', subtype_xmlid='mail.mt_comment')
        self.assertSentEmail(self.test_channel.env.user.partner_id, [self.partner_employee, self.test_partner])

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_channel_recipient_noalias(self):
        """ Posting a message on a classic channel should work like classic post """
        self.test_channel.write({'alias_name': False})
        self.test_channel.message_subscribe([self.user_employee.partner_id.id, self.test_partner.id, self.partner_employee_nomail.id])
        with self.mock_mail_gateway():
            self.test_channel.message_post(body="Test", message_type='comment', subtype_xmlid='mail.mt_comment')
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

        msg_1 = self._add_messages(
            self.test_channel, 'Body1', author=self.user_employee.partner_id,
            channel_ids=[self.test_channel.id])
        msg_2 = self._add_messages(
            self.test_channel, 'Body2', author=self.user_employee.partner_id,
            channel_ids=[self.test_channel.id])

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

    def test_multi_company_chat(self):
        self._activate_multi_company()
        self.assertEqual(self.env.user.company_id, self.company_admin)

        with self.with_user('employee'):
            initial_channel_info = self.env['mail.channel'].with_context(
                allowed_company_ids=self.company_admin.ids
            ).channel_get(self.partner_employee_c2.ids)
            self.assertTrue(initial_channel_info, 'should be able to chat with multi company user')


@tagged('moderation')
class TestChannelModeration(MailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestChannelModeration, cls).setUpClass()

        cls.channel_1 = cls.env['mail.channel'].create({
            'name': 'Moderation_1',
            'email_send': True,
            'moderation': True,
            'channel_partner_ids': [(4, cls.partner_employee.id)],
            'moderator_ids': [(4, cls.user_employee.id)],
        })

        # ensure initial data
        cls.user_employee_2 = mail_new_test_user(
            cls.env, login='employee2', groups='base.group_user', company_id=cls.company_admin.id,
            name='Enguerrand Employee2', notification_type='inbox', signature='--\nEnguerrand'
        )
        cls.partner_employee_2 = cls.user_employee_2.partner_id

        cls.user_portal = cls._create_portal_user()

    def test_moderator_consistency(self):
        # moderators should be channel members
        with self.assertRaises(ValidationError):
            self.channel_1.write({'moderator_ids': [(4, self.user_admin.id)]})

        # member -> moderator or
        self.channel_1.write({'channel_partner_ids': [(4, self.partner_admin.id)]})
        self.channel_1.write({'moderator_ids': [(4, self.user_admin.id)]})

        # member -> moderator ko if no email
        self.channel_1.write({'moderator_ids': [(3, self.partner_admin.id)]})
        self.user_admin.write({'email': False})
        with self.assertRaises(ValidationError):
            self.channel_1.write({'moderator_ids': [(4, self.user_admin.id)]})

    def test_moderation_consistency(self):
        # moderation enabled channels are restricted to mailing lists
        with self.assertRaises(ValidationError):
            self.channel_1.write({'email_send': False})

        # moderation enabled channels should always have moderators
        with self.assertRaises(ValidationError):
            self.channel_1.write({'moderator_ids': [(5, 0)]})

    def test_moderation_count(self):
        self.assertEqual(self.channel_1.moderation_count, 0)
        self.channel_1.write({'moderation_ids': [
            (0, 0, {'email': 'test0@example.com', 'status': 'allow'}),
            (0, 0, {'email': 'test1@example.com', 'status': 'ban'})
        ]})
        self.assertEqual(self.channel_1.moderation_count, 2)

    @mute_logger('odoo.addons.mail.models.mail_channel', 'odoo.models.unlink')
    def test_send_guidelines(self):
        self.channel_1.write({'channel_partner_ids': [(4, self.partner_portal.id), (4, self.partner_admin.id)]})
        self.channel_1._update_moderation_email([self.partner_admin.email], 'ban')
        with self.mock_mail_gateway():
            self.channel_1.with_user(self.user_employee).send_guidelines()
        for mail in self._new_mails:
            self.assertEqual(mail.author_id, self.partner_employee)
            self.assertEqual(mail.subject, 'Guidelines of channel %s' % self.channel_1.name)
            self.assertEqual(mail.state, 'outgoing')
            self.assertEqual(mail.email_from, self.user_employee.company_id.catchall_formatted)
        self.assertEqual(self._new_mails.mapped('recipient_ids'), self.partner_employee | self.partner_portal)

    def test_send_guidelines_crash(self):
        self.channel_1.write({
            'channel_partner_ids': [(4, self.partner_admin.id)],
            'moderator_ids': [(4, self.user_admin.id), (3, self.user_employee.id)]
        })
        with self.assertRaises(UserError):
            self.channel_1.with_user(self.user_employee).send_guidelines()

    def test_update_moderation_email(self):
        self.channel_1.write({'moderation_ids': [
            (0, 0, {'email': 'test0@example.com', 'status': 'allow'}),
            (0, 0, {'email': 'test1@example.com', 'status': 'ban'})
        ]})
        self.channel_1._update_moderation_email(['test0@example.com', 'test3@example.com'], 'ban')
        self.assertEqual(len(self.channel_1.moderation_ids), 3)
        self.assertTrue(all(status == 'ban' for status in self.channel_1.moderation_ids.mapped('status')))

    def test_moderation_reset(self):
        self.channel_2 = self.env['mail.channel'].create({
            'name': 'Moderation_1',
            'email_send': True,
            'moderation': True,
            'channel_partner_ids': [(4, self.partner_employee.id)],
            'moderator_ids': [(4, self.user_employee.id)],
        })

        self.msg_c1_1 = self._add_messages(self.channel_1, 'Body11', author=self.partner_admin, moderation_status='accepted')
        self.msg_c1_2 = self._add_messages(self.channel_1, 'Body12', author=self.partner_admin, moderation_status='pending_moderation')
        self.msg_c2_1 = self._add_messages(self.channel_2, 'Body21', author=self.partner_admin, moderation_status='pending_moderation')

        self.assertEqual(self.env['mail.message'].search_count([
            ('moderation_status', '=', 'pending_moderation'),
            ('model', '=', 'mail.channel'), ('res_id', '=', self.channel_1.id)
        ]), 1)
        self.channel_1.write({'moderation': False})
        self.assertEqual(self.env['mail.message'].search_count([
            ('moderation_status', '=', 'pending_moderation'),
            ('model', '=', 'mail.channel'), ('res_id', '=', self.channel_1.id)
        ]), 0)
        self.assertEqual(self.env['mail.message'].search_count([
            ('moderation_status', '=', 'pending_moderation'),
            ('model', '=', 'mail.channel'), ('res_id', '=', self.channel_2.id)
        ]), 1)
        self.channel_2.write({'moderation': False})
        self.assertEqual(self.env['mail.message'].search_count([
            ('moderation_status', '=', 'pending_moderation'),
            ('model', '=', 'mail.channel'), ('res_id', '=', self.channel_2.id)
        ]), 0)

    @mute_logger('odoo.models.unlink')
    def test_message_post(self):
        email1 = 'test0@example.com'
        email2 = 'test1@example.com'

        self.channel_1._update_moderation_email([email1], 'ban')
        self.channel_1._update_moderation_email([email2], 'allow')

        msg_admin = self.channel_1.message_post(message_type='email', subtype_xmlid='mail.mt_comment', author_id=self.partner_admin.id)
        msg_moderator = self.channel_1.message_post(message_type='comment', subtype_xmlid='mail.mt_comment', author_id=self.partner_employee.id)
        msg_email1 = self.channel_1.message_post(message_type='comment', subtype_xmlid='mail.mt_comment', email_from=formataddr(("MyName", email1)))
        msg_email2 = self.channel_1.message_post(message_type='email', subtype_xmlid='mail.mt_comment', email_from=email2)
        msg_notif = self.channel_1.message_post()

        messages = self.env['mail.message'].search([('model', '=', 'mail.channel'), ('res_id', '=', self.channel_1.id)])
        pending_messages = messages.filtered(lambda m: m.moderation_status == 'pending_moderation')
        accepted_messages = messages.filtered(lambda m: m.moderation_status == 'accepted')

        self.assertFalse(msg_email1)
        self.assertEqual(msg_admin, pending_messages)
        self.assertEqual(accepted_messages, msg_moderator | msg_email2 | msg_notif)
        self.assertFalse(msg_admin.channel_ids)
        self.assertEqual(msg_email2.channel_ids, self.channel_1)

    def test_user_is_moderator(self):
        self.assertTrue(self.user_employee.is_moderator)
        self.assertFalse(self.user_employee_2.is_moderator)
        self.channel_1.write({
            'channel_partner_ids': [(4, self.partner_employee_2.id)],
            'moderator_ids': [(4, self.user_employee_2.id)],
        })
        self.assertTrue(self.user_employee_2.is_moderator)

    def test_user_moderation_counter(self):
        self._add_messages(self.channel_1, 'B', moderation_status='pending_moderation', author=self.partner_employee_2)
        self._add_messages(self.channel_1, 'B', moderation_status='accepted', author=self.partner_employee_2)
        self._add_messages(self.channel_1, 'B', moderation_status='accepted', author=self.partner_employee)
        self._add_messages(self.channel_1, 'B', moderation_status='pending_moderation', author=self.partner_employee)
        self._add_messages(self.channel_1, 'B', moderation_status='accepted', author=self.partner_employee)

        self.assertEqual(self.user_employee.moderation_counter, 2)
        self.assertEqual(self.user_employee_2.moderation_counter, 0)

        self.channel_1.write({
            'channel_partner_ids': [(4, self.partner_employee_2.id)],
            'moderator_ids': [(4, self.user_employee_2.id)]
        })
        self.assertEqual(self.user_employee.moderation_counter, 2)
        self.assertEqual(self.user_employee_2.moderation_counter, 0)
