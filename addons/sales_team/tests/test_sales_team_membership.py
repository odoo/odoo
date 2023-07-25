# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import exceptions
from odoo.addons.sales_team.tests.common import TestSalesCommon
from odoo.tests.common import users
from odoo.tools import mute_logger


class TestMembership(TestSalesCommon):
    """Tests to ensure membership behavior """

    @classmethod
    def setUpClass(cls):
        super(TestMembership, cls).setUpClass()
        cls.new_team = cls.env['crm.team'].create({
            'name': 'Test Specific',
            'sequence': 10,
        })
        cls.env['ir.config_parameter'].set_param('sales_team.membership_multi', True)

    @users('user_sales_manager')
    def test_fields(self):
        self.assertTrue(self.sales_team_1.with_user(self.env.user).is_membership_multi)
        self.assertTrue(self.new_team.with_user(self.env.user).is_membership_multi)

        self.env['ir.config_parameter'].sudo().set_param('sales_team.membership_multi', False)
        self.assertFalse(self.sales_team_1.with_user(self.env.user).is_membership_multi)
        self.assertFalse(self.new_team.with_user(self.env.user).is_membership_multi)

    @users('user_sales_manager')
    def test_members_mono(self):
        """ Test mono mode using the user m2m relationship """
        self.env['ir.config_parameter'].sudo().set_param('sales_team.membership_multi', False)
        # ensure initial data
        sales_team_1 = self.sales_team_1.with_user(self.env.user)
        new_team = self.new_team.with_user(self.env.user)
        self.assertEqual(sales_team_1.member_ids, self.user_sales_leads | self.user_admin)

        # test various add / remove on computed m2m
        self.assertEqual(new_team.member_ids, self.env['res.users'])
        new_team.write({'member_ids': [(4, self.env.uid)]})
        self.assertEqual(new_team.member_ids, self.env.user)
        new_team.write({'member_ids': [(4, self.user_sales_leads.id)]})
        self.assertEqual(new_team.member_ids, self.env.user | self.user_sales_leads)
        new_team.write({'member_ids': [(3, self.user_sales_leads.id)]})
        self.assertEqual(new_team.member_ids, self.env.user)
        new_team.write({'member_ids': [(6, 0, (self.user_sales_leads | self.env.user).ids)]})
        self.assertEqual(new_team.member_ids, self.env.user | self.user_sales_leads)

        # archived memberships on sales_team_1 for user_sales_leads
        self.assertEqual(sales_team_1.member_ids, self.user_admin)

        # create a new user on the fly, just for testing
        self.user_sales_manager.write({'groups_id': [(4, self.env.ref('base.group_system').id)]})
        new_team.write({'member_ids': [(0, 0, {
            'name': 'Marty OnTheMCFly',
            'login': 'mcfly@test.example.com',
        })]})
        new_user = self.env['res.users'].search([('login', '=', 'mcfly@test.example.com')])
        self.assertTrue(len(new_user))
        self.assertEqual(new_team.member_ids, self.env.user | self.user_sales_leads | new_user)
        self.user_sales_manager.write({'groups_id': [(3, self.env.ref('base.group_system').id)]})

        new_team.flush()
        memberships = self.env['crm.team.member'].with_context(active_test=False).search([('user_id', '=', self.user_sales_leads.id)])
        self.assertEqual(len(memberships), 3)  # subscribed twice to new_team + subscribed to sales_team_1
        self.assertEqual(memberships.crm_team_id, sales_team_1 | new_team)
        self.assertFalse(memberships.filtered(lambda m: m.crm_team_id == sales_team_1).active)
        new_team_memberships = memberships.filtered(lambda m: m.crm_team_id == new_team)
        self.assertEqual(len(new_team_memberships), 2)  # subscribed, removed, then subscribed again
        self.assertTrue(set(new_team_memberships.mapped('active')), set([False, True]))

        # still avoid duplicated team / user entries
        with self.assertRaises(exceptions.UserError):
            self.env['crm.team.member'].create({'crm_team_id': new_team.id, 'user_id': new_user.id})

    @users('user_sales_manager')
    def test_members_multi(self):
        # ensure initial data
        sales_team_1 = self.sales_team_1.with_user(self.env.user)
        new_team = self.new_team.with_user(self.env.user)
        self.assertEqual(sales_team_1.member_ids, self.user_sales_leads | self.user_admin)

        # test various add / remove on computed m2m
        self.assertEqual(new_team.member_ids, self.env['res.users'])
        new_team.write({'member_ids': [(4, self.env.uid), (4, self.user_sales_leads.id)]})
        self.assertEqual(new_team.member_ids, self.env.user | self.user_sales_leads)
        new_team.write({'member_ids': [(3, self.user_sales_leads.id)]})
        self.assertEqual(new_team.member_ids, self.env.user)
        new_team.write({'member_ids': [(6, 0, (self.user_sales_leads | self.env.user).ids)]})
        self.assertEqual(new_team.member_ids, self.env.user | self.user_sales_leads)

        # nothing changed on sales_team_1
        self.assertEqual(sales_team_1.member_ids, self.user_sales_leads | self.user_admin)

        # create a new user on the fly, just for testing
        self.user_sales_manager.write({'groups_id': [(4, self.env.ref('base.group_system').id)]})
        new_team.write({'member_ids': [(0, 0, {
            'name': 'Marty OnTheMCFly',
            'login': 'mcfly@test.example.com',
        })]})
        new_user = self.env['res.users'].search([('login', '=', 'mcfly@test.example.com')])
        self.assertTrue(len(new_user))
        self.assertEqual(new_team.member_ids, self.env.user | self.user_sales_leads | new_user)
        self.user_sales_manager.write({'groups_id': [(3, self.env.ref('base.group_system').id)]})
        new_team.flush()

        # still avoid duplicated team / user entries
        with self.assertRaises(exceptions.UserError):
            self.env['crm.team.member'].create({'crm_team_id': new_team.id, 'user_id': new_user.id})

    @users('user_sales_manager')
    def test_memberships_mono(self):
        """ Test mono mode: updating crm_team_member_ids field """
        self.env['ir.config_parameter'].sudo().set_param('sales_team.membership_multi', False)
        # ensure initial data
        sales_team_1 = self.env['crm.team'].browse(self.sales_team_1.ids)
        new_team = self.env['crm.team'].browse(self.new_team.ids)
        self.assertEqual(sales_team_1.member_ids, self.user_sales_leads | self.user_admin)

        # subscribe on new team (user_sales_leads will have two memberships -> old one deactivated)
        self.assertEqual(new_team.member_ids, self.env['res.users'])
        new_team.write({'crm_team_member_ids': [
            (0, 0, {'user_id': self.user_sales_leads.id}),
            (0, 0, {'user_id': self.uid}),
        ]})
        self.assertEqual(new_team.member_ids, self.env.user | self.user_sales_leads)
        self.assertEqual(sales_team_1.member_ids, self.user_admin)
        new_team.flush()

        memberships = self.env['crm.team.member'].with_context(active_test=False).search([('user_id', '=', self.user_sales_leads.id)])
        self.assertEqual(memberships.crm_team_id, sales_team_1 | new_team)
        self.assertFalse(memberships.filtered(lambda m: m.crm_team_id == sales_team_1).active)
        self.assertTrue(memberships.filtered(lambda m: m.crm_team_id == new_team).active)

        # subscribe user_sales_leads on old team -> old membership still archived and kept
        sales_team_1.write({'crm_team_member_ids': [(0, 0, {'user_id': self.user_sales_leads.id})]})
        memberships_new = self.env['crm.team.member'].with_context(active_test=False).search([('user_id', '=', self.user_sales_leads.id)])
        self.assertTrue(memberships < memberships_new)
        self.assertEqual(memberships.crm_team_id, sales_team_1 | new_team)

        # old membership is still inactive, new membership is active
        old_st_1 = memberships_new.filtered(lambda m: m.crm_team_id == sales_team_1 and m in memberships)
        new_st_1 = memberships_new.filtered(lambda m: m.crm_team_id == sales_team_1 and m not in memberships)
        new_nt = memberships_new.filtered(lambda m: m.crm_team_id == new_team)
        self.assertFalse(old_st_1.active)
        self.assertTrue(new_st_1.active)
        self.assertFalse(new_nt.active)

        # check members fields
        self.assertEqual(new_team.member_ids, self.env.user)
        self.assertEqual(sales_team_1.member_ids, self.user_admin | self.user_sales_leads)

        # activate another team membership: previous team membership should be de activated
        new_nt.toggle_active()
        self.assertTrue(new_nt.active)
        self.assertFalse(old_st_1.active)
        self.assertFalse(new_st_1.active)
        # activate another team membership: previous team membership should be de activated
        old_st_1.toggle_active()
        self.assertFalse(new_nt.active)
        self.assertTrue(old_st_1.active)
        self.assertFalse(new_st_1.active)

        # try to activate duplicate memberships again, which should trigger issues
        with self.assertRaises(exceptions.UserError):
            new_st_1.toggle_active()

    @users('user_sales_manager')
    def test_memberships_multi(self):
        # ensure initial data
        sales_team_1 = self.env['crm.team'].browse(self.sales_team_1.ids)
        new_team = self.env['crm.team'].browse(self.new_team.ids)
        self.assertEqual(sales_team_1.member_ids, self.user_sales_leads | self.user_admin)

        # subscribe on new team (user_sales_leads will have two memberships -> old one deactivated)
        self.assertEqual(new_team.member_ids, self.env['res.users'])
        new_team.write({'crm_team_member_ids': [
            (0, 0, {'user_id': self.user_sales_leads.id}),
            (0, 0, {'user_id': self.uid}),
        ]})
        self.assertEqual(new_team.member_ids, self.env.user | self.user_sales_leads)
        self.assertEqual(sales_team_1.member_ids, self.user_sales_leads | self.user_admin)
        new_team.flush()

        memberships = self.env['crm.team.member'].with_context(active_test=False).search([('user_id', '=', self.user_sales_leads.id)])
        self.assertEqual(memberships.crm_team_id, sales_team_1 | new_team)
        self.assertTrue(memberships.filtered(lambda m: m.crm_team_id == sales_team_1).active)
        self.assertTrue(memberships.filtered(lambda m: m.crm_team_id == new_team).active)

        # archive membership on sales_team_1 and try creating a new one
        memberships.filtered(lambda m: m.crm_team_id == sales_team_1).write({'active': False})
        # subscribe user_sales_leads on old team -> old membership still archived and kept
        sales_team_1.write({'crm_team_member_ids': [(0, 0, {'user_id': self.user_sales_leads.id})]})
        memberships_new = self.env['crm.team.member'].with_context(active_test=False).search([('user_id', '=', self.user_sales_leads.id)])
        self.assertTrue(memberships < memberships_new)
        self.assertEqual(memberships.crm_team_id, sales_team_1 | new_team)

        # old membership is still inactive, new membership is active
        old_st_1 = memberships_new.filtered(lambda m: m.crm_team_id == sales_team_1 and m in memberships)
        new_st_1 = memberships_new.filtered(lambda m: m.crm_team_id == sales_team_1 and m not in memberships)
        new_nt = memberships_new.filtered(lambda m: m.crm_team_id == new_team)
        self.assertFalse(old_st_1.active)
        self.assertTrue(new_st_1.active)
        self.assertTrue(new_nt.active)

        # check members fields
        self.assertEqual(new_team.member_ids, self.env.user | self.user_sales_leads)
        self.assertEqual(sales_team_1.member_ids, self.user_admin | self.user_sales_leads)

        # try to activate duplicate memberships again, which should trigger issues
        with self.assertRaises(exceptions.UserError):
            old_st_1.toggle_active()

    @users('user_sales_manager')
    def test_memberships_sync(self):
        sales_team_1 = self.env['crm.team'].browse(self.sales_team_1.ids)
        new_team = self.env['crm.team'].browse(self.new_team.ids)
        self.assertEqual(sales_team_1.member_ids, self.user_sales_leads | self.user_admin)
        self.assertEqual(new_team.crm_team_member_ids, self.env['crm.team.member'])
        self.assertEqual(new_team.crm_team_member_all_ids, self.env['crm.team.member'])
        self.assertEqual(new_team.member_ids, self.env['res.users'])

        # creating memberships correctly updates m2m without any refresh
        new_member = self.env['crm.team.member'].create({
            'user_id': self.env.user.id,
            'crm_team_id': self.new_team.id,
        })
        self.assertEqual(new_team.crm_team_member_ids, new_member)
        self.assertEqual(new_team.crm_team_member_all_ids, new_member)
        self.assertEqual(new_team.member_ids, self.env.user)

        # adding members correctly update o2m with right values
        new_team.write({
            'member_ids': [(4, self.user_sales_leads.id)]
        })
        added = self.env['crm.team.member'].search([('crm_team_id', '=', new_team.id), ('user_id', '=', self.user_sales_leads.id)])
        self.assertEqual(new_team.crm_team_member_ids, new_member + added)
        self.assertEqual(new_team.crm_team_member_all_ids, new_member + added)
        self.assertEqual(new_team.member_ids, self.env.user | self.user_sales_leads)

        # archiving membership correctly updates m2m and o2m
        added.write({'active': False})
        self.assertEqual(new_team.crm_team_member_ids, new_member)
        self.assertEqual(new_team.crm_team_member_all_ids, new_member + added)
        self.assertEqual(new_team.member_ids, self.env.user)

        # reactivating correctly updates m2m and o2m
        added.write({'active': True})
        self.assertEqual(new_team.crm_team_member_ids, new_member + added)
        self.assertEqual(new_team.crm_team_member_all_ids, new_member + added)
        self.assertEqual(new_team.member_ids, self.env.user | self.user_sales_leads)

        # archived are kept if duplicated on write
        admin_original = self.env['crm.team.member'].search([
            ('crm_team_id', '=', sales_team_1.id),
            ('user_id', '=', self.user_admin.id)
        ])
        self.assertTrue(bool(admin_original))
        admin_archived = self.env['crm.team.member'].create({
            'crm_team_id': new_team.id,
            'user_id': self.user_admin.id,
            'active': False,
        })
        admin_original.write({'crm_team_id': new_team.id})
        # send to db as errors may pop at that step (like trying to set NULL on a m2o inverse of o2m)
        self.new_team.flush()
        self.assertTrue(self.user_admin in new_team.member_ids)
        self.assertTrue(admin_original.active)
        self.assertTrue(admin_archived.exists())
        self.assertFalse(admin_archived.active)

        # change team of membership should raise unicity constraint
        with self.assertRaises(exceptions.UserError), mute_logger('odoo.sql_db'):
            added.write({'crm_team_id': sales_team_1.id})
            self.new_team.flush()

    def test_sales_team_member_search(self):
        """ when a search is triggered on the member_ids field in crm.team
        it is currently returning the archived records also. this test will
        ensure that the search wont return archived record.

        this is to fix unwanted ORM behavior
        """
        self.env['res.partner'].create({'name': 'Test Partner', 'team_id': self.new_team.id})
        self.env['crm.team.member'].create({
            'user_id': self.env.uid,
            'crm_team_id': self.new_team.id,
            'active': False,
        })
        partner_exists = self.env['res.partner'].search([
            ('team_id.member_ids', 'in', [self.env.uid])
        ])
        self.assertFalse(partner_exists, msg="Partner should return empty as current user is removed from team")

    def test_users_sale_team_id(self):
        self.assertTrue(self.sales_team_1.sequence < self.new_team.sequence)

        self.assertEqual(self.user_sales_leads.crm_team_ids, self.sales_team_1)
        self.assertEqual(self.user_sales_leads.sale_team_id, self.sales_team_1)

        # subscribe to new team -> default team is still the old one
        self.new_team.write({
            'member_ids': [(4, self.user_sales_leads.id)]
        })
        self.assertEqual(self.user_sales_leads.crm_team_ids, self.sales_team_1 | self.new_team)
        self.assertEqual(self.user_sales_leads.sale_team_id, self.sales_team_1)

        # archive membership to first team -> second one becomes default
        self.sales_team_1_m1.write({'active': False})
        self.assertEqual(self.user_sales_leads.crm_team_ids, self.new_team)
        self.assertEqual(self.user_sales_leads.sale_team_id, self.new_team)

        # activate membership to first team -> first one becomes default again
        self.sales_team_1_m1.write({'active': True})
        self.assertEqual(self.user_sales_leads.crm_team_ids, self.sales_team_1 | self.new_team)
        self.assertEqual(self.user_sales_leads.sale_team_id, self.sales_team_1)

        # keep only one membership -> default team
        self.sales_team_1_m1.unlink()
        self.assertEqual(self.user_sales_leads.crm_team_ids, self.new_team)
        self.assertEqual(self.user_sales_leads.sale_team_id, self.new_team)
