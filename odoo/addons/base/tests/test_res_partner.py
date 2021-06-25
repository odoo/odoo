# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestPartner(TransactionCase):

    def test_name_search(self):
        """ Check name_search on partner, especially with domain based on auto_join
        user_ids field. Check specific SQL of name_search correctly handle joined tables. """
        test_partner = self.env['res.partner'].create({'name': 'Vlad the Impaler'})
        test_user = self.env['res.users'].create({'name': 'Vlad the Impaler', 'login': 'vlad', 'email': 'vlad.the.impaler@example.com'})

        ns_res = self.env['res.partner'].name_search('Vlad', operator='ilike')
        self.assertEqual(set(i[0] for i in ns_res), set((test_partner | test_user.partner_id).ids))

        ns_res = self.env['res.partner'].name_search('Vlad', args=[('user_ids.email', 'ilike', 'vlad')])
        self.assertEqual(set(i[0] for i in ns_res), set(test_user.partner_id.ids))

    def test_company_change_propagation(self):
        """ Check propagation of company_id across children """
        User = self.env['res.users']
        Partner = self.env['res.partner']
        Company = self.env['res.company']

        company_1 = Company.create({'name': 'company_1'})
        company_2 = Company.create({'name': 'company_2'})

        test_partner_company = Partner.create({'name': 'This company'})
        test_user = User.create({'name': 'This user', 'login': 'thisu', 'email': 'this.user@example.com', 'company_id': company_1.id, 'company_ids': [company_1.id]})
        test_user.partner_id.write({'parent_id': test_partner_company.id})

        test_partner_company.write({'company_id': company_1.id})
        self.assertEqual(test_user.partner_id.company_id.id, company_1.id, "The new company_id of the partner company should be propagated to its children")

        test_partner_company.write({'company_id': False})
        self.assertFalse(test_user.partner_id.company_id.id, "If the company_id is deleted from the partner company, it should be propagated to its children")

        with self.assertRaises(UserError, msg="You should not be able to update the company_id of the partner company if the linked user of a child partner is not an allowed to be assigned to that company"), self.cr.savepoint():
            test_partner_company.write({'company_id': company_2.id})

    def test_partner_merge_wizard_dst_partner_id(self):
        """ Check that dst_partner_id in merge wizard displays id along with partner name """
        test_partner = self.env['res.partner'].create({'name': 'Radu the Handsome'})
        expected_partner_name = '%s (%s)' % (test_partner.name, test_partner.id)

        partner_merge_wizard = self.env['base.partner.merge.automatic.wizard'].with_context(
            {'partner_show_db_id': True, 'default_dst_partner_id': test_partner}).new()
        self.assertEqual(partner_merge_wizard.dst_partner_id.display_name, expected_partner_name, "'Destination Contact' name should contain db ID in brackets")

    def test_public_customer_status(self):
        """ Test customer / share / public computation on partner, depending
        on its users and including active flag test. """
        partner = self.env['res.partner'].create({
            'name': 'Brigitte Boitaclous',
            'email': '"Brigitte, Boitaclous" <brigitte@boitaclous.example.com>',
        })
        self.assertTrue(partner.partner_share, "Partner wo user is considered as share")
        self.assertFalse(partner.partner_public, "Partner has no public user linked")

        user_portal = self.env['res.users'].create({
            'partner_id': partner.id,
            'groups_id': [(4, self.env.ref('base.group_portal').id)],
            'active': True,
            'login': 'test.portal',
        })
        self.assertTrue(user_portal.share, "Portal users are considered as share")
        self.assertTrue(partner.partner_share, "Partner with portal user is considered as share")
        self.assertFalse(partner.partner_public, "Partner has other users than public users")

        user_public = self.env['res.users'].create({
            'partner_id': partner.id,
            'groups_id': [(4, self.env.ref('base.group_public').id)],
            'active': True,
            'login': 'test.public',
        })
        self.assertTrue(user_public.share, "Public users are considered as share")
        self.assertEqual(partner.user_ids, user_portal | user_public)
        self.assertTrue(partner.partner_share, "Partner with portal and public users is considered as share")
        self.assertFalse(partner.partner_public, "Partner has other users than public users")

        user_portal.toggle_active()
        self.assertEqual(partner.user_ids, user_public)
        self.assertEqual(partner.with_context(active_test=False).user_ids, user_portal | user_public)
        self.assertTrue(partner.partner_share, "Partner with portal (even archived) and public users is considered as share")
        self.assertFalse(partner.partner_public, "Partner has other users (even archived) than public users")

        user_public.toggle_active()
        self.assertFalse(partner.user_ids)
        self.assertEqual(partner.with_context(active_test=False).user_ids, user_portal | user_public)
        self.assertTrue(partner.partner_share, "Partner with portal and public users (even archived) is considered as share")
        self.assertFalse(partner.partner_public, "Partner has other users (even archived) than public users")

        user_portal.unlink()
        self.assertFalse(partner.user_ids)
        self.assertEqual(partner.with_context(active_test=False).user_ids, user_public)
        self.assertTrue(partner.partner_share, "Partner public user (even archived) is considered as share")
        self.assertTrue(partner.partner_public, "Partner has only (archived) public users")

        user_public.toggle_active()
        self.assertEqual(partner.user_ids, user_public)
        self.assertTrue(partner.partner_share, "Partner with portal (even archived) and public users (even archived) is considered as share")
        self.assertTrue(partner.partner_public, "Partner has only public users")

        user_public2 = self.env['res.users'].create({
            'partner_id': partner.id,
            'groups_id': [(4, self.env.ref('base.group_public').id)],
            'active': True,
            'login': 'test.public.2',
        })
        self.assertEqual(partner.user_ids, user_public | user_public2)
        self.assertTrue(partner.partner_share, "Partner with several share users is considered as share")
        self.assertTrue(partner.partner_public, "Partner has only public users")

        user_internal = self.env['res.users'].create({
            'partner_id': partner.id,
            'groups_id': [(4, self.env.ref('base.group_user').id)],
            'active': True,
            'login': 'test.internal',
        })
        self.assertEqual(partner.user_ids, user_public | user_public2 | user_internal)
        self.assertFalse(partner.partner_share, "Partner has internal users")
        self.assertFalse(partner.partner_public, "Partner has internal users")

        # check famous example: public partner
        self.assertTrue(self.env.ref('base.public_partner').partner_public)
