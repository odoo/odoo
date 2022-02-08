# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2 import IntegrityError

from odoo import Command, tools
from odoo.addons.mail_group.tests.data import GROUP_TEMPLATE
from odoo.addons.mail_group.tests.common import TestMailListCommon
from odoo.exceptions import AccessError
from odoo.tests.common import tagged, users
from odoo.tools import mute_logger


@tagged('mail_group_moderation')
class TestMailGroupModeration(TestMailListCommon):
    @classmethod
    def setUpClass(cls):
        super(TestMailGroupModeration, cls).setUpClass()

        cls.test_group_2 = cls.env['mail.group'].create({
            'access_mode': 'members',
            'alias_name': 'test.mail.group.2',
            'moderation': True,
            'moderator_ids': [Command.link(cls.user_employee.id)],
            'name': 'Test group 2',
        })

    @mute_logger('odoo.sql_db')
    @users('employee')
    def test_constraints(self):
        mail_group = self.env['mail.group'].browse(self.test_group.ids)
        with self.assertRaises(IntegrityError):
            moderation = self.env['mail.group.moderation'].create({
                'mail_group_id': mail_group.id,
                'email': 'banned_member@test.com',
                'status': 'ban',
            })
            moderation.flush()

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail_group.models.mail_group_message')
    @users('employee')
    def test_moderation_rule_api(self):
        """ Test moderation rule creation / update through API """
        mail_group = self.env['mail.group'].browse(self.test_group.ids)
        mail_group_2 = self.env['mail.group'].browse(self.test_group_2.ids)
        self.assertEqual(
            set(mail_group.moderation_rule_ids.mapped('email')),
            set(['banned_member@test.com'])
        )

        moderation_1, moderation_2, moderation_3 = self.env['mail.group.moderation'].create([{
            'email': 'std@test.com',
            'status': 'allow',
            'mail_group_id': mail_group.id,
        }, {
            'email': 'xss@test.com',
            'status': 'ban',
            'mail_group_id': mail_group.id,
        }, {
            'email': 'xss@test.com',
            'status': 'ban',
            'mail_group_id': mail_group_2.id,
        }])

        self.assertEqual(
            set(mail_group.moderation_rule_ids.mapped('email')),
            set(['banned_member@test.com', 'std@test.com', 'xss@test.com'])
        )

        message_1, message_2, message_3 = self.env['mail.group.message'].create([{
            'email_from': '"Boum" <sTd@teST.com>',
            'mail_group_id': mail_group.id,
        }, {
            'email_from': '"xSs" <xss@teST.com>',
            'mail_group_id': mail_group.id,
        }, {
            'email_from': '"Bob" <bob@teST.com>',
            'mail_group_id': mail_group.id,
        }])

        # status 'bouh' does not exist
        with self.assertRaises(ValueError):
            (message_1 | message_2 | message_3)._create_moderation_rule('bouh')

        (message_1 | message_2 | message_3)._create_moderation_rule('allow')

        self.assertEqual(len(mail_group.moderation_rule_ids), 4, "Should have created only one moderation rule")
        self.assertEqual(
            set(mail_group.moderation_rule_ids.mapped('email')),
            set(['banned_member@test.com', 'std@test.com', 'xss@test.com', 'bob@test.com'])
        )
        self.assertEqual(moderation_1.status, 'allow')
        self.assertEqual(moderation_2.status, 'allow', 'Should have write on the existing moderation rule')
        self.assertEqual(moderation_3.status, 'ban', 'Should not have changed moderation of the other group')
        new_moderation = mail_group.moderation_rule_ids.filtered(lambda rule: rule.email == 'bob@test.com')
        self.assertEqual(new_moderation.status, 'allow', 'Should have created the moderation with the right status')

    @users('employee')
    def test_moderation_rule_email_normalize(self):
        """ Test emails are automatically normalized """
        rule = self.env['mail.group.moderation'].create({
            'mail_group_id': self.test_group.id,
            'email': '"Bob" <bob@test.com>',
            'status': 'ban',
        })
        self.assertEqual(rule.email, 'bob@test.com')

        rule.email = '"Alice" <alice@test.com>'
        self.assertEqual(rule.email, 'alice@test.com')

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.addons.base.models.ir_model')
    def test_moderation_rule_security(self):
        with self.assertRaises(AccessError, msg='Portal should not have access to moderation rules'):
            self.env['mail.group.moderation'].with_user(self.user_portal).browse(self.moderation.ids).email

        self.test_group.write({
            'moderator_ids': [(4, self.user_admin.id), (3, self.user_employee.id)]
            })
        with self.assertRaises(AccessError, msg='Non moderators should not have access to moderation rules'):
            self.env['mail.group.moderation'].with_user(self.user_employee).browse(self.moderation.ids).email

        self.assertEqual(
            self.env['mail.group.moderation'].with_user(self.user_admin).browse(self.moderation.ids).email,
            'banned_member@test.com',
            msg='Moderators should have access to moderation rules')


@tagged('mail_group_moderation')
class TestModeration(TestMailListCommon):

    @classmethod
    def setUpClass(cls):
        super(TestModeration, cls).setUpClass()

        # Test group: members, moderation
        cls.test_group_2 = cls.env['mail.group'].create({
            'access_mode': 'members',
            'alias_name': 'test.mail.group.2',
            'moderation': True,
            'moderator_ids': [Command.link(cls.user_employee.id)],
            'name': 'Test group 2',
        })
        cls.test_group_2_member_emp = cls.env['mail.group.member'].create({
            'partner_id': cls.user_employee_2.partner_id.id,
            'email': cls.user_employee_2.email,
            'mail_group_id': cls.test_group_2.id,
        })

        # Existing messages on group 2
        cls.test_group_2_msg_1_pending = cls.env['mail.group.message'].create({
            'email_from': cls.email_from_unknown,
            'subject': 'Group 2 Pending',
            'mail_group_id': cls.test_group_2.id,
            'moderation_status': 'pending_moderation',
        })

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.addons.mail_group.models.mail_group_message')
    @users('employee')
    def test_moderation_flow_accept(self):
        """ Unknown email sends email on moderated group, test accept """
        mail_group = self.env['mail.group'].browse(self.test_group.ids)
        self.assertEqual(len(mail_group.mail_group_message_ids), 3)

        with self.mock_mail_gateway():
            self.format_and_process(
                GROUP_TEMPLATE, self.email_from_unknown, self.test_group.alias_id.display_name,
                subject='Old email', target_model='mail.group')

            self.format_and_process(
                GROUP_TEMPLATE, self.email_from_unknown, self.test_group.alias_id.display_name,
                subject='New email', target_model='mail.group')

        # find messages
        self.assertEqual(len(mail_group.mail_group_message_ids), 5)
        old_email_message = mail_group.mail_group_message_ids[-2]
        new_email_message = mail_group.mail_group_message_ids[-1]

        # check message content
        self.assertEqual(old_email_message.moderation_status, 'pending_moderation')
        self.assertEqual(old_email_message.subject, 'Old email')
        self.assertEqual(new_email_message.moderation_status, 'pending_moderation')
        self.assertEqual(new_email_message.subject, 'New email')

        # accept email without any moderation rule
        with self.mock_mail_gateway():
            new_email_message.action_moderate_accept()

        self.assertEqual(len(self._new_mails), 4)
        for email in self.test_group_valid_members.mapped('email'):
            self.assertMailMailWEmails([email], 'outgoing',
                                       content="This should be posted on a mail.group. Or not.",
                                       fields_values={
                                        'email_from': self.email_from_unknown,
                                        'subject': 'New email',
                                       },
                                       mail_message=new_email_message.mail_message_id)

        self.assertEqual(new_email_message.moderation_status, 'accepted', 'Should have accepted the message')
        self.assertEqual(old_email_message.moderation_status, 'pending_moderation', 'Should not have touched other message of the same author')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.addons.mail_group.models.mail_group_message', 'odoo.models.unlink')
    @users('employee')
    def test_moderation_flow_allow(self):
        """ Unknown email sends email on moderated group, test allow """
        mail_group = self.test_group
        mail_group_2_as2 = self.env['mail.group'].with_user(self.user_employee_2).browse(self.test_group_2.ids)
        self.assertEqual(len(mail_group.mail_group_message_ids), 3)
        group_2_message_count = len(mail_group_2_as2.mail_group_message_ids)

        with self.mock_mail_gateway():
            self.format_and_process(
                GROUP_TEMPLATE, self.email_from_unknown, self.test_group.alias_id.display_name,
                subject='Old email', target_model='mail.group')

            self.format_and_process(
                GROUP_TEMPLATE, self.email_from_unknown, self.test_group.alias_id.display_name,
                subject='New email', target_model='mail.group')

        # find messages
        self.assertEqual(len(mail_group.mail_group_message_ids), 5)
        old_email_message = mail_group.mail_group_message_ids[-2]
        new_email_message = mail_group.mail_group_message_ids[-1]

        # check message content
        self.assertEqual(old_email_message.email_from, self.email_from_unknown)
        self.assertEqual(old_email_message.moderation_status, 'pending_moderation')
        self.assertEqual(old_email_message.subject, 'Old email')
        self.assertEqual(new_email_message.email_from, self.email_from_unknown)
        self.assertEqual(new_email_message.moderation_status, 'pending_moderation')
        self.assertEqual(new_email_message.subject, 'New email')

        # Create a moderation rule to always accept this email address
        with self.mock_mail_gateway():
            new_email_message.action_moderate_allow()

        self.assertEqual(new_email_message.moderation_status, 'accepted', 'Should have accepted the message')
        self.assertEqual(old_email_message.moderation_status, 'accepted', 'Should have accepted the old message of the same author')

        # Test that the moderation rule has been created
        new_rule = self.env['mail.group.moderation'].search([
            ('status', '=', 'allow'),
            ('email', '=', tools.email_normalize(self.email_from_unknown))
        ])
        self.assertEqual(len(new_rule), 1, 'Should have created a moderation rule')

        # Check emails have been sent
        self.assertEqual(len(self._new_mails), 8)
        for email in self.test_group_valid_members.mapped('email'):
            self.assertMailMailWEmails([email], 'outgoing',
                                       content="This should be posted on a mail.group. Or not.",
                                       fields_values={
                                        'email_from': self.email_from_unknown,
                                        'subject': 'New email',
                                       },
                                       mail_message=new_email_message.mail_message_id)
            self.assertMailMailWEmails([email], 'outgoing',
                                       content="This should be posted on a mail.group. Or not.",
                                       fields_values={
                                        'email_from': self.email_from_unknown,
                                        'subject': 'Old email',
                                       },
                                       mail_message=old_email_message.mail_message_id)

        # Send a second email with the same FROM, but with a different name
        with self.mock_mail_gateway():
            self.format_and_process(
                GROUP_TEMPLATE,
                tools.formataddr(("Another Name", "bob.email@test.example.com")),
                self.test_group.alias_id.display_name,
                subject='Another email', target_model='mail.group')

        # find messages
        self.assertEqual(len(mail_group.mail_group_message_ids), 6)
        new_email_message = mail_group.mail_group_message_ids[-1]

        self.assertEqual(new_email_message.email_from, tools.formataddr(("Another Name", "bob.email@test.example.com")))
        self.assertEqual(new_email_message.moderation_status, 'accepted', msg='Should have automatically accepted the email')
        self.assertEqual(new_email_message.subject, 'Another email')

        self.assertEqual(
            self.test_group_2_msg_1_pending.moderation_status, 'pending_moderation',
            'Should not have accepted message in the other group')
        self.assertEqual(
            len(mail_group_2_as2.mail_group_message_ids), group_2_message_count,
            'Should never have created message in the other group')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.addons.mail_group.models.mail_group_message', 'odoo.models.unlink')
    @users('employee')
    def test_moderation_flow_ban(self):
        """ Unknown email sends email on moderated group, test ban """
        mail_group = self.env['mail.group'].browse(self.test_group.ids)
        self.assertEqual(len(mail_group.mail_group_message_ids), 3)

        with self.mock_mail_gateway():
            self.format_and_process(
                GROUP_TEMPLATE, self.email_from_unknown, self.test_group.alias_id.display_name,
                subject='Old email', target_model='mail.group')

            self.format_and_process(
                GROUP_TEMPLATE, self.email_from_unknown, self.test_group.alias_id.display_name,
                subject='New email', target_model='mail.group')

        # find messages
        self.assertEqual(len(mail_group.mail_group_message_ids), 5)
        old_email_message = mail_group.mail_group_message_ids[-2]
        new_email_message = mail_group.mail_group_message_ids[-1]

        # ban and check moderation rule has been
        with self.mock_mail_gateway():
            new_email_message.action_moderate_ban()

        self.assertEqual(old_email_message.moderation_status, 'rejected')
        self.assertEqual(new_email_message.moderation_status, 'rejected')

        # Test that the moderation rule has been created
        new_rule = self.env['mail.group.moderation'].search([
            ('status', '=', 'ban'),
            ('email', '=', tools.email_normalize(self.email_from_unknown))
        ])
        self.assertEqual(len(new_rule), 1, 'Should have created a moderation rule')

        # Check no mail.mail has been sent
        self.assertEqual(len(self._new_mails), 0, 'Should not have send emails')

        # Send a second email with the same FROM, but with a different name
        with self.mock_mail_gateway():
            self.format_and_process(
                GROUP_TEMPLATE,
                tools.formataddr(("Another Name", "bob.email@test.example.com")),
                self.test_group.alias_id.display_name,
                subject='Another email', target_model='mail.group')

        # find messages
        self.assertEqual(len(mail_group.mail_group_message_ids), 6)
        new_email_message = mail_group.mail_group_message_ids[-1]
        self.assertEqual(new_email_message.moderation_status, 'rejected', 'Should have automatically rejected the email')

        # Check no mail.mail has been sent
        self.assertEqual(len(self._new_mails), 0, 'Should not have send emails')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.addons.mail_group.models.mail_group_message', 'odoo.models.unlink')
    @users('employee')
    def test_moderation_flow_reject(self):
        """ Unknown email sends email on moderated group, test reject """
        mail_group = self.env['mail.group'].browse(self.test_group.ids)
        self.assertEqual(len(mail_group.mail_group_message_ids), 3)

        with self.mock_mail_gateway():
            self.format_and_process(
                GROUP_TEMPLATE, self.email_from_unknown, self.test_group.alias_id.display_name,
                subject='Old email', target_model='mail.group')

            self.format_and_process(
                GROUP_TEMPLATE, self.email_from_unknown, self.test_group.alias_id.display_name,
                subject='New email', target_model='mail.group')

        # find messages
        self.assertEqual(len(mail_group.mail_group_message_ids), 5)
        old_email_message = mail_group.mail_group_message_ids[-2]
        new_email_message = mail_group.mail_group_message_ids[-1]

        # reject without moderation rule
        with self.mock_mail_gateway():
            new_email_message.action_moderate_reject_with_comment('Test Rejected', 'Bad email')

        self.assertEqual(new_email_message.moderation_status, 'rejected', 'Should have rejected the message')
        self.assertEqual(old_email_message.moderation_status, 'pending_moderation', 'Should not have rejected old message')

        self.assertEqual(len(self._new_mails), 1, 'Should have sent the reject email')
        self.assertMailMailWEmails([self.email_from_unknown], 'outgoing',
                                   content="This should be posted on a mail.group. Or not.",
                                   fields_values={
                                    'email_from': self.user_employee.email_formatted,
                                    'subject': 'Test Rejected',
                                   })

    @mute_logger('odoo.addons.mail_group.models.mail_group')
    @users('employee')
    def test_moderation_send_guidelines(self):
        """ Test sending guidelines """
        mail_group = self.env['mail.group'].browse(self.test_group.ids)
        mail_group.write({
            'moderation_guidelines': True,
            'moderation_guidelines_msg': 'Test guidelines group',
        })
        with self.mock_mail_gateway():
            mail_group.action_send_guidelines()

        self.assertEqual(len(self._new_mails), 3)
        for email in self.test_group_valid_members.mapped('email'):
            self.assertMailMailWEmails([email], 'outgoing',
                                       content="Test guidelines group",
                                       fields_values={
                                        'email_from': self.env.company.email_formatted,
                                        'subject': 'Guidelines of group %s' % mail_group.name,
                                       })

    @mute_logger('odoo.addons.mail_group.models.mail_group')
    @users('employee')
    def test_moderation_send_guidelines_on_new_member(self):
        """ Test sending guidelines when having a new members """
        mail_group = self.env['mail.group'].browse(self.test_group.ids)
        mail_group.write({
            'moderation_guidelines': True,
            'moderation_guidelines_msg': 'Test guidelines group',
        })
        with self.mock_mail_gateway():
            mail_group._join_group('"New Member" <new.member@test.com>')

        self.assertEqual(len(self._new_mails), 1)
        self.assertMailMailWEmails(['"New Member" <new.member@test.com>'], 'outgoing',
                                   content="Test guidelines group",
                                   fields_values={
                                    'email_from': self.env.company.email_formatted,
                                    'subject': 'Guidelines of group %s' % mail_group.name,
                                   })
