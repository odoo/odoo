# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail_group.tests.common import TestMailListCommon
from odoo.exceptions import ValidationError, UserError, AccessError
from odoo.tests.common import users
from odoo.tools import mute_logger


class TestMailGroup(TestMailListCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailGroup, cls).setUpClass()

        cls.user_portal = cls._create_portal_user()

    def test_constraint_valid_email(self):
        mail_group = self.env['mail.group'].with_user(self.user_employee).browse(self.test_group.ids)
        user_without_email = mail_new_test_user(
            self.env, login='user_employee_nomail',
            company_id=self.company_admin.id,
            email=False,
            groups='base.group_user',
            name='User without email',
        )

        with self.assertRaises(ValidationError, msg="Moderators must have an email"):
            mail_group.moderator_ids |= user_without_email

    @users('employee')
    def test_join_group(self):
        mail_group = self.env['mail.group'].browse(self.test_group.ids)
        self.assertEqual(len(mail_group.member_ids), 4)

        mail_group._join_group('"Jack" <jack@test.com>')
        self.assertEqual(len(mail_group.member_ids), 5)

        with self.assertRaises(UserError):
            mail_group._join_group('"Jack the developer" <jack@test.com>')
        self.assertEqual(len(mail_group.member_ids), 5, 'Should not have added the duplicated email')

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.addons.base.models.ir_model')
    @users('employee')
    def test_mail_group_access_mode_groups(self):
        test_group = self.env.ref('base.group_partner_manager')
        mail_group = self.env['mail.group'].browse(self.test_group.ids)
        mail_group.write({
            'access_group_id': test_group.id,
            'access_mode': 'groups',
        })

        with self.assertRaises(AccessError):
            mail_group.with_user(self.user_portal).check_access_rule('read')

        public_user = self.env.ref('base.public_user')
        with self.assertRaises(AccessError):
            mail_group.with_user(public_user).check_access_rule('read')

        with self.assertRaises(AccessError):
            mail_group.with_user(self.user_employee_2).check_access_rule('read')

        # Add the group to the user
        self.user_employee_2.groups_id |= test_group
        mail_group.with_user(self.user_employee_2).check_access_rule('read')
        mail_group.with_user(self.user_employee_2).check_access_rule('write')

        # Remove the group of the user BUT add it in the moderators list
        self.user_employee_2.groups_id -= test_group
        mail_group.moderator_ids |= self.user_employee_2
        mail_group.with_user(self.user_employee_2).check_access_rule('read')
        mail_group.with_user(self.user_employee_2).check_access_rule('write')

        # Test with public user
        mail_group.access_group_id = self.env.ref('base.group_public')
        mail_group.with_user(public_user).check_access_rule('read')
        mail_group.with_user(public_user).check_access_rights('read')
        with self.assertRaises(AccessError):
            mail_group.with_user(public_user).check_access_rule('write')
            mail_group.with_user(public_user).check_access_rights('write')

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.addons.base.models.ir_model')
    @users('employee')
    def test_mail_group_access_mode_public(self):
        mail_group = self.env['mail.group'].browse(self.test_group.ids)
        mail_group.access_mode = 'public'

        public_user = self.env.ref('base.public_user')
        mail_group.with_user(public_user).check_access_rule('read')
        with self.assertRaises(AccessError):
            mail_group.with_user(public_user).check_access_rights('write')

        mail_group.with_user(self.user_employee_2).check_access_rule('read')
        mail_group.with_user(self.user_employee_2).check_access_rights('write')

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.addons.base.models.ir_model')
    @users('employee')
    def test_mail_group_access_mode_members(self):
        mail_group = self.env['mail.group'].browse(self.test_group.ids)
        mail_group.access_mode = 'members'
        portal_partner = self.user_portal.partner_id
        self.assertNotIn(portal_partner, mail_group.member_partner_ids)

        with self.assertRaises(AccessError, msg='Non-member should not have access to the group'):
            mail_group.with_user(self.user_portal).check_access_rule('read')

        public_user = self.env.ref('base.public_user')
        with self.assertRaises(AccessError, msg='Non-member should not have access to the group'):
            mail_group.with_user(public_user).check_access_rule('read')

        mail_group.write({'member_ids': [(0, 0, {
            'partner_id': portal_partner.id,
        })]})
        self.assertIn(portal_partner, mail_group.member_partner_ids)

        # Now that portal is in the member list he should have access
        mail_group.with_user(self.user_portal).check_access_rule('read')
        mail_group.with_user(self.user_portal).check_access_rule('write')

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.addons.base.models.ir_model')
    @users('employee')
    def test_mail_group_member_security(self):
        member = self.env['mail.group.member'].browse(self.test_group_member_1.ids)
        self.assertEqual(member.email, '"Member 1" <member_1@test.com>', msg='Moderators should have access to members')

        # with self.assertRaises(AccessError, msg='Portal should not have access to members'):
        #     self.env['mail.group.member'].with_user(self.user_portal).browse(member.ids).email

        # with self.assertRaises(AccessError, msg='Non moderators should not have access to member'):
        #     self.env['mail.group.member'].with_user(self.user_employee_2).browse(member.ids).email
