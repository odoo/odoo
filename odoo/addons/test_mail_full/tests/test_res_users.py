# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.test_mail_full.tests.common import TestMailFullCommon


class TestResUsers(TestMailFullCommon):

    @classmethod
    def setUpClass(cls):
        super(TestResUsers, cls).setUpClass()
        cls.portal_user = mail_new_test_user(
            cls.env,
            login='portal_user',
            mobile='+32 494 12 34 56',
            phone='+32 494 12 34 89',
            password='password',
            name='Portal User',
            email='portal@test.example.com',
            groups='base.group_portal',
        )

        cls.portal_user_2 = mail_new_test_user(
            cls.env,
            login='portal_user_2',
            mobile='+32 494 12 34 22',
            phone='invalid phone',
            password='password',
            name='Portal User 2',
            email='portal_2@test.example.com',
            groups='base.group_portal',
        )

        # Remove existing blacklisted email / phone (they will be sanitized, so we avoid to sanitize them here)
        cls.env['mail.blacklist'].search([]).unlink()
        cls.env['phone.blacklist'].search([]).unlink()

    def test_deactivate_portal_users_blacklist(self):
        """Test that the email and the phone are blacklisted
        when a portal user deactivate his own account.
        """
        (self.portal_user | self.portal_user_2)._deactivate_portal_user(request_blacklist=True)

        self.assertFalse(self.portal_user.active, 'Should have archived the user')
        self.assertFalse(self.portal_user.partner_id.active, 'Should have archived the partner')
        self.assertFalse(self.portal_user_2.active, 'Should have archived the user')
        self.assertFalse(self.portal_user_2.partner_id.active, 'Should have archived the partner')

        blacklist = self.env['mail.blacklist'].search([
            ('email', 'in', ('portal@test.example.com', 'portal_2@test.example.com')),
        ])
        self.assertEqual(len(blacklist), 2, 'Should have blacklisted the users email')

        blacklists = self.env['phone.blacklist'].search([
            ('number', 'in', ('+32494123489', '+32494123456', '+32494123422')),
        ])
        self.assertEqual(len(blacklists), 3, 'Should have blacklisted the user phone and mobile')

        blacklist = self.env['phone.blacklist'].search([('number', '=', 'invalid phone')])
        self.assertFalse(blacklist, 'Should have skipped invalid phone')

    def test_deactivate_portal_users_no_blacklist(self):
        """Test the case when the user do not want to blacklist his email / phone."""
        (self.portal_user | self.portal_user_2)._deactivate_portal_user(request_blacklist=False)

        self.assertFalse(self.portal_user.active, 'Should have archived the user')
        self.assertFalse(self.portal_user.partner_id.active, 'Should have archived the partner')
        self.assertFalse(self.portal_user_2.active, 'Should have archived the user')
        self.assertFalse(self.portal_user_2.partner_id.active, 'Should have archived the partner')

        blacklists = self.env['mail.blacklist'].search([])
        self.assertFalse(blacklists, 'Should not have blacklisted the users email')

        blacklists = self.env['phone.blacklist'].search([])
        self.assertFalse(blacklists, 'Should not have blacklisted the user phone and mobile')
