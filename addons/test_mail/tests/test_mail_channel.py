# -*- coding: utf-8 -*-

from email.utils import formataddr

from odoo.addons.test_mail.tests import common
from odoo.exceptions import AccessError, except_orm
from odoo.tools import mute_logger


class TestChannelAccessRights(common.BaseFunctionalTest, common.MockEmails):

    @classmethod
    def setUpClass(cls):
        super(TestChannelAccessRights, cls).setUpClass()
        Channel = cls.env['mail.channel'].with_context(cls._quick_create_ctx)

        Users = cls.env['res.users'].with_context(cls._quick_create_user_ctx)
        cls.user_public = Users.create({
            'name': 'Bert Tartignole',
            'login': 'bert',
            'email': 'b.t@example.com',
            'groups_id': [(6, 0, [cls.env.ref('base.group_public').id])]})
        cls.user_portal = Users.create({
            'name': 'Chell Gladys',
            'login': 'chell',
            'email': 'chell@gladys.portal',
            'groups_id': [(6, 0, [cls.env.ref('base.group_portal').id])]})

        # Pigs: base group for tests
        cls.group_pigs = Channel.create({
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

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_access_rights_public(self):
        # Read public group -> ok
        self.group_public.sudo(self.user_public).read()

        # Read Pigs -> ko, restricted to employees
        # TODO: Change the except_orm to Warning ( Because here it's call check_access_rule
        # which still generate exception in except_orm.So we need to change all
        # except_orm to warning in mail module.)
        with self.assertRaises(except_orm):
            self.group_pigs.sudo(self.user_public).read()

        # Read a private group when being a member: ok
        self.group_private.write({'channel_partner_ids': [(4, self.user_public.partner_id.id)]})
        self.group_private.sudo(self.user_public).read()

        # Create group: ko, no access rights
        with self.assertRaises(AccessError):
            self.env['mail.channel'].sudo(self.user_public).create({'name': 'Test'})

        # Update group: ko, no access rights
        with self.assertRaises(AccessError):
            self.group_public.sudo(self.user_public).write({'name': 'Broutouschnouk'})

        # Unlink group: ko, no access rights
        with self.assertRaises(AccessError):
            self.group_public.sudo(self.user_public).unlink()

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models', 'odoo.models.unlink')
    def test_access_rights_groups(self):
        # Employee read employee-based group: ok
        # TODO Change the except_orm to Warning
        self.group_pigs.sudo(self.user_employee).read()

        # Employee can create a group
        self.env['mail.channel'].sudo(self.user_employee).create({'name': 'Test'})

        # Employee update employee-based group: ok
        self.group_pigs.sudo(self.user_employee).write({'name': 'modified'})

        # Employee unlink employee-based group: ok
        self.group_pigs.sudo(self.user_employee).unlink()

        # Employee cannot read a private group
        with self.assertRaises(except_orm):
            self.group_private.sudo(self.user_employee).read()

        # Employee cannot write on private
        with self.assertRaises(AccessError):
            self.group_private.sudo(self.user_employee).write({'name': 're-modified'})

    @mute_logger('odoo.addons.base.ir.ir_model', 'odoo.models')
    def test_access_rights_followers_ko(self):
        with self.assertRaises(AccessError):
            self.group_private.sudo(self.user_portal).name

    def test_access_rights_followers_portal(self):
        # Do: Chell is added into Pigs members and browse it -> ok for messages, ko for partners (no read permission)
        self.group_private.write({'channel_partner_ids': [(4, self.user_portal.partner_id.id)]})
        chell_pigs = self.group_private.sudo(self.user_portal)
        trigger_read = chell_pigs.name
        for message in chell_pigs.message_ids:
            trigger_read = message.subject
        for partner in chell_pigs.message_partner_ids:
            if partner.id == self.user_portal.partner_id.id:
                # Chell can read her own partner record
                continue
            # TODO Change the except_orm to Warning
            with self.assertRaises(except_orm):
                trigger_read = partner.name


class TestChannelFeatures(common.BaseFunctionalTest, common.MockEmails):

    @classmethod
    def setUpClass(cls):
        super(TestChannelFeatures, cls).setUpClass()
        cls.test_channel = cls.env['mail.channel'].with_context(cls._quick_create_ctx).create({
            'name': 'Test',
            'description': 'Description',
            'alias_name': 'test',
            'public': 'public',
        })
        cls.test_partner = cls.env['res.partner'].with_context(cls._quick_create_ctx).create({
            'name': 'Test Partner',
            'email': 'test@example.com',
        })

    def _join_channel(self, channel, partners):
        for partner in partners:
            channel.write({'channel_last_seen_partner_ids': [(0, 0, {'partner_id': partner.id})]})
        channel.invalidate_cache()

    def _leave_channel(self, channel, partners):
        for partner in partners:
            channel._action_unfollow(partner)

    def test_channel_listeners(self):
        self.assertEqual(self.test_channel.message_channel_ids, self.test_channel)
        self.assertEqual(self.test_channel.message_partner_ids, self.env['res.partner'])
        self.assertEqual(self.test_channel.channel_partner_ids, self.env['res.partner'])

        self._join_channel(self.test_channel, self.test_partner)
        self.assertEqual(self.test_channel.message_channel_ids, self.test_channel)
        self.assertEqual(self.test_channel.message_partner_ids, self.env['res.partner'])
        self.assertEqual(self.test_channel.channel_partner_ids, self.test_partner)

        self._leave_channel(self.test_channel, self.test_partner)
        self.assertEqual(self.test_channel.message_channel_ids, self.test_channel)
        self.assertEqual(self.test_channel.message_partner_ids, self.env['res.partner'])
        self.assertEqual(self.test_channel.channel_partner_ids, self.env['res.partner'])

    def test_channel_post_nofollow(self):
        self.test_channel.message_post(body='Test', message_type='comment', subtype='mt_comment')
        self.assertEqual(self.test_channel.message_channel_ids, self.test_channel)
        self.assertEqual(self.test_channel.message_partner_ids, self.env['res.partner'])

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_channel_mailing_list_recipients(self):
        """ Posting a message on a mailing list should send one email to all recipients """
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', 'schlouby.fr')
        self.test_channel.write({'email_send': True})
        self._join_channel(self.test_channel, self.user_employee.partner_id | self.test_partner)
        self.test_channel.message_post(body="Test", message_type='comment', subtype='mt_comment')

        self.assertEqual(len(self._mails), 1)
        for email in self._mails:
            self.assertEqual(
                set(email['email_to']),
                set([formataddr((self.user_employee.name, self.user_employee.email)), formataddr((self.test_partner.name, self.test_partner.email))]))

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_channel_chat_recipients(self):
        """ Posting a message on a chat should not send emails """
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', 'schlouby.fr')
        self.test_channel.write({'email_send': False})
        self._join_channel(self.test_channel, self.user_employee.partner_id | self.test_partner)
        self.test_channel.message_post(body="Test", message_type='comment', subtype='mt_comment')

        self.assertEqual(len(self._mails), 0)

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_channel_classic_recipients(self):
        """ Posting a message on a classic channel should work like classic post """
        self.test_channel.write({'alias_name': False})
        self.test_channel.message_subscribe([self.user_employee.partner_id.id, self.test_partner.id])
        self.test_channel.message_post(body="Test", message_type='comment', subtype='mt_comment')

        sent_emails = self._mails
        self.assertEqual(len(sent_emails), 2)
        for email in sent_emails:
            self.assertIn(
                email['email_to'][0],
                [formataddr((self.user_employee.name, self.user_employee.email)), formataddr((self.test_partner.name, self.test_partner.email))])
