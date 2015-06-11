# -*- coding: utf-8 -*-

from .common import TestMail
from openerp.exceptions import AccessError
from openerp.exceptions import except_orm
from openerp.tools import mute_logger


class TestMailGroup(TestMail):

    def setUp(self):
        super(TestMailGroup, self).setUp()
        # Private: private group
        self.group_private = self.env['mail.channel'].with_context({
            'mail_create_nolog': True,
            'mail_create_nosubscribe': True
        }).create({
            'name': 'Private',
            'public': 'private'}
        ).with_context({'mail_create_nosubscribe': False})

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    def test_access_rights_public(self):
        # Read public group -> ok
        self.group_public.sudo(self.user_public).read()

        # Read Pigs -> ko, restricted to employees
        # TODO: Change the except_orm to Warning ( Because here it's call check_access_rule
        # which still generate exception in except_orm.So we need to change all
        # except_orm to warning in mail module.)
        with self.assertRaises(except_orm):
            self.group_pigs.sudo(self.user_public).read()

        # Read a private group when being a follower: ok
        self.group_private.message_subscribe_users(user_ids=[self.user_public.id])
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

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
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
        # Do: Chell is added into Pigs followers and browse it -> ok for messages, ko for partners (no read permission)
        self.group_private.message_subscribe_users(user_ids=[self.user_portal.id])
        chell_pigs = self.group_private.sudo(self.user_portal)
        trigger_read = chell_pigs.name
        for message in chell_pigs.message_ids:
            trigger_read = message.subject
        for partner in chell_pigs.message_follower_ids:
            if partner.id == self.user_portal.partner_id.id:
                # Chell can read her own partner record
                continue
            # TODO Change the except_orm to Warning
            with self.assertRaises(except_orm):
                trigger_read = partner.name
