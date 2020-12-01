# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user
from odoo.exceptions import UserError, AccessError
from odoo.tests.common import users


class TestPortalWizard(MailCommon):
    def setUp(self):
        super(TestPortalWizard, self).setUp()

        self.partner = self.env['res.partner'].create({
            'name': 'Testing Partner',
            'email': 'testing_partner@example.com',
        })

        self.public_user = mail_new_test_user(
            self.env,
            name='Public user',
            login='public_user',
            email='public_user@example.com',
            groups='base.group_public',
        )

        self.portal_user = mail_new_test_user(
            self.env,
            name='Portal user',
            login='portal_user',
            email='portal_user@example.com',
            groups='base.group_portal',
        )

        self.internal_user = mail_new_test_user(
            self.env,
            name='Internal user',
            login='internal_user',
            email='internal_user@example.com',
            groups='base.group_user',
        )

    def test_portal_wizard_acl(self):
        portal_wizard = self.env['portal.wizard'].with_context(active_ids=[self.partner.id]).create({})

        with self.assertRaises(AccessError, msg='Standard users should not be able to open the portal wizard'):
            self.env['portal.wizard'].with_context(active_ids=[self.partner.id]).with_user(self.user_employee).create({})

        portal_wizard.invalidate_cache()

        with self.assertRaises(AccessError, msg='Standard users should not be able to open the portal wizard'):
            portal_wizard.with_user(self.user_employee).welcome_message

        portal_wizard.user_ids.invalidate_cache()

        with self.assertRaises(AccessError, msg='Standard users should not be able to open the portal wizard'):
            portal_wizard.user_ids.with_user(self.user_employee).email

    @users('admin')
    def test_portal_wizard_partner(self):
        portal_wizard = self.env['portal.wizard'].with_context(active_ids=[self.partner.id]).create({})

        self.assertEqual(len(portal_wizard.user_ids), 1)

        portal_user = portal_wizard.user_ids

        self.assertFalse(portal_user.user_id.id)
        self.assertFalse(portal_user.is_portal)
        self.assertFalse(portal_user.is_internal)

        portal_user.email = 'first_email@example.com'
        with self.mock_mail_gateway():
            portal_user.action_grant_access()
        new_user = portal_user.user_id

        self.assertTrue(new_user.id, 'Must create a new user')
        self.assertTrue(new_user.has_group('base.group_portal'), 'Must add the group to the user')
        self.assertEqual(self.partner.email, 'first_email@example.com', 'Must write on the email of the partner')
        self.assertEqual(new_user.email, 'first_email@example.com', 'Must create the user with the right email')
        self.assertSentEmail(self.env.user.partner_id, [self.partner])

    @users('admin')
    def test_portal_wizard_public_user(self):
        """Test to grant the access to a public user.

        Should remove the group "base.group_public" and add the group "base.group_portal"
        """
        group_public = self.env.ref('base.group_public')
        public_partner = self.public_user.partner_id
        portal_wizard = self.env['portal.wizard'].with_context(active_ids=[public_partner.id]).create({})

        self.assertEqual(len(portal_wizard.user_ids), 1)
        portal_user = portal_wizard.user_ids

        self.assertEqual(portal_user.user_id, self.public_user)
        self.assertFalse(portal_user.is_portal)
        self.assertFalse(portal_user.is_internal)

        portal_user.email = 'new_email@example.com'
        with self.mock_mail_gateway():
            portal_user.action_grant_access()

        self.assertTrue(portal_user.is_portal)
        self.assertFalse(portal_user.is_internal)

        self.assertTrue(self.public_user.has_group('base.group_portal'), 'Must add the group portal')
        self.assertFalse(self.public_user.has_group('base.group_public'), 'Must remove the group public')
        self.assertEqual(public_partner.email, 'new_email@example.com', 'Must change the email of the partner')
        self.assertEqual(self.public_user.email, 'new_email@example.com', 'Must change the email of the user')
        self.assertSentEmail(self.env.user.partner_id, [public_partner])

        with self.mock_mail_gateway():
            portal_user.action_revoke_access()

        self.assertEqual(portal_user.user_id, self.public_user, 'Must keep the user even if it is archived')
        self.assertEqual(group_public, portal_user.user_id.groups_id, 'Must add the group public after removing the portal group')
        self.assertFalse(portal_user.user_id.active, 'Must have archived the user')
        self.assertFalse(portal_user.is_portal)
        self.assertFalse(portal_user.is_internal)
        self.assertNotSentEmail()

    @users('admin')
    def test_portal_wizard_internal_user(self):
        """Internal user can not be managed from this wizard."""
        internal_partner = self.internal_user.partner_id
        portal_wizard = self.env['portal.wizard'].with_context(active_ids=[internal_partner.id]).create({})

        self.assertEqual(len(portal_wizard.user_ids), 1)
        portal_user = portal_wizard.user_ids

        self.assertTrue(portal_user.is_internal)

        with self.assertRaises(UserError, msg='Should not be able to manage internal user'), self.mock_mail_gateway():
            portal_wizard.user_ids.action_grant_access()

        self.assertNotSentEmail()

        with self.assertRaises(UserError, msg='Should not be able to manage internal user'):
            portal_wizard.user_ids.action_revoke_access()

    @users('admin')
    def test_portal_wizard_error(self):
        portal_wizard = self.env['portal.wizard'].with_context(active_ids=[self.portal_user.partner_id.id]).create({})

        self.assertEqual(len(portal_wizard.user_ids), 1)
        portal_user = portal_wizard.user_ids

        self.internal_user.login = 'test_error@example.com'
        portal_user.email = 'test_error@example.com'

        with self.assertRaises(UserError, msg='Must detect the already used email.'):
            portal_user.action_revoke_access()

        portal_user.email = 'wrong email format'
        with self.assertRaises(UserError, msg='Must detect wrong email format.'):
            portal_user.action_revoke_access()

        portal_wizard = self.env['portal.wizard'].with_context(active_ids=[self.internal_user.partner_id.id]).create({})
        with self.assertRaises(UserError, msg='Must not be able to change internal user group.'):
            portal_user.action_revoke_access()

    def test_portal_wizard_multi_company(self):
        company_1 = self.env['res.company'].search([], limit=1)
        company_2 = self.env['res.company'].create({'name': 'Company 2'})

        partner_company_2 = self.env['res.partner'].with_company(company_2).create({
            'name': 'Testing Partner',
            'email': 'testing_partner@example.com',
            'company_id': company_2.id,
        })

        portal_wizard = self.env['portal.wizard'].with_context(active_ids=[partner_company_2.id]).create({})
        portal_user = portal_wizard.user_ids

        portal_user.with_company(company_1).action_grant_access()

        self.assertEqual(portal_user.user_id.company_id, company_2, 'Must create the user in the same company as the partner.')
