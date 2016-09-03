# -*- coding: utf-8 -*-

from email.utils import formataddr

from .common import TestMail
from odoo import api
from odoo.exceptions import AccessError, except_orm
from odoo.tools import mute_logger


class TestMailGroup(TestMail):

    @classmethod
    def setUpClass(cls):
        super(TestMailGroup, cls).setUpClass()
        # for specific tests of mail channel, get back to its expected behavior
        cls.registry('mail.channel')._revert_method('message_get_recipient_values')

        # Private: private group
        cls.group_private = cls.env['mail.channel'].with_context({
            'mail_create_nolog': True,
            'mail_create_nosubscribe': True
        }).create({
            'name': 'Private',
            'public': 'private'}
        ).with_context({'mail_create_nosubscribe': False})

    @classmethod
    def tearDownClass(cls):
        # set master class behavior back
        @api.multi
        def mail_group_message_get_recipient_values(self, notif_message=None, recipient_ids=None):
            return self.env['mail.thread'].message_get_recipient_values(notif_message=notif_message, recipient_ids=recipient_ids)
        cls.env['mail.channel']._patch_method('message_get_recipient_values', mail_group_message_get_recipient_values)
        super(TestMail, cls).tearDownClass()

    @mute_logger('odoo.addons.base.ir.ir_model', 'odoo.models')
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

    @mute_logger('odoo.addons.base.ir.ir_model', 'odoo.models')
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

    def test_mail_group_notification_recipients_grouped(self):
        # Data: set alias_domain to see emails with alias
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', 'schlouby.fr')
        self.group_private.write({'alias_name': 'Test'})
        self.group_private.message_subscribe_users([self.user_employee.id, self.user_portal.id])

        self.group_private.message_post(body="Test", message_type='comment', subtype='mt_comment')
        sent_emails = self._mails
        self.assertEqual(len(sent_emails), 1)
        for email in sent_emails:
            self.assertEqual(
                set(email['email_to']),
                set([formataddr((self.user_employee.name, self.user_employee.email)), formataddr((self.user_portal.name, self.user_portal.email))]))

    def test_mail_group_notification_recipients_separated(self):
        # Remove alias, should trigger classic behavior of mail group
        self.group_private.write({'alias_name': False})
        self.group_private.message_subscribe_users([self.user_employee.id, self.user_portal.id])

        self.group_private.message_post(body="Test", message_type='comment', subtype='mt_comment')
        sent_emails = self._mails
        self.assertEqual(len(sent_emails), 2)
        for email in sent_emails:
            self.assertIn(
                email['email_to'][0],
                [formataddr((self.user_employee.name, self.user_employee.email)), formataddr((self.user_portal.name, self.user_portal.email))])
