# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, tools
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tests.common import MailCommon


class TestMailListCommon(MailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailListCommon, cls).setUpClass()

        # Test credentials / from
        cls.email_from_unknown = tools.formataddr(("Bob Lafrite", "bob.email@test.example.com"))
        cls.user_employee_2 = mail_new_test_user(
            cls.env, login='employee_2',
            company_id=cls.company_admin.id,
            email='employee_2@test.com',
            groups='base.group_user',
            name='Albertine Another Employee',
        )

        # Test group: members, moderation
        cls.test_group = cls.env['mail.group'].create({
            'access_mode': 'public',
            'alias_name': 'test.mail.group',
            'moderation': True,
            'moderator_ids': [Command.link(cls.user_employee.id)],
            'name': 'Test group',
        })

        cls.moderation = cls.env['mail.group.moderation'].create({
            'mail_group_id': cls.test_group.id,
            'email': 'banned_member@test.com',
            'status': 'ban',
        })

        cls.test_group_member_1 = cls.env['mail.group.member'].create({
            'email': '"Member 1" <member_1@test.com>',
            'mail_group_id': cls.test_group.id,
        })
        cls.test_group_member_2 = cls.env['mail.group.member'].create({
            'email': 'member_2@test.com',
            'mail_group_id': cls.test_group.id,
        })
        cls.test_group_member_3_banned = cls.env['mail.group.member'].create({
            'email': '"Banned Member" <banned_member@test.com>',
            'mail_group_id': cls.test_group.id,
        })
        cls.test_group_member_4_emp = cls.env['mail.group.member'].create({
            'partner_id': cls.partner_employee.id,
            'mail_group_id': cls.test_group.id,
        })
        cls.test_group_valid_members = cls.test_group_member_1 + cls.test_group_member_2 + cls.test_group_member_4_emp

        # Create some messages
        cls.test_group_msg_1_pending = cls.env['mail.group.message'].create({
            'subject': 'Test message pending',
            'mail_group_id': cls.test_group.id,
            'moderation_status': 'pending_moderation',
            'email_from': '"Bob" <bob@test.com>',
        })
        cls.test_group_msg_2_accepted = cls.env['mail.group.message'].create({
            'subject': 'Test message accepted',
            'mail_group_id': cls.test_group.id,
            'moderation_status': 'accepted',
            'email_from': '"Alice" <alice@test.com>',
        })
        cls.test_group_msg_3_rejected = cls.env['mail.group.message'].create({
            'subject': 'Test message rejected',
            'mail_group_id': cls.test_group.id,
            'moderation_status': 'rejected',
            'email_from': '"Alice" <alice@test.com>',
        })

        cls.user_portal = cls._create_portal_user()
