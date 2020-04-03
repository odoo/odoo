# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sales_team.tests.common import TestSalesCommon
from odoo.tests.common import users


class TestMembership(TestSalesCommon):
    """Tests to ensure membership behavior """

    @classmethod
    def setUpClass(cls):
        super(TestMembership, cls).setUpClass()
        cls.new_team = cls.env['crm.team'].create({
            'name': 'Test Specific',
            'sequence': 10,
        })

    @users('user_sales_manager')
    def test_membership_sync(self):
        self.assertEqual(self.new_team.crm_team_member_ids, self.env['crm.team.member'])
        self.assertEqual(self.new_team.crm_team_member_all_ids, self.env['crm.team.member'])
        self.assertEqual(self.new_team.member_ids, self.env['res.users'])

        # creating memberships correctly updates m2m without any refresh
        new_member = self.env['crm.team.member'].create({
            'user_id': self.env.user.id,
            'crm_team_id': self.new_team.id,
        })
        self.assertEqual(self.new_team.crm_team_member_ids, new_member)
        self.assertEqual(self.new_team.crm_team_member_all_ids, new_member)
        self.assertEqual(self.new_team.member_ids, self.env.user)

        # adding members correctly update o2m with right values
        self.new_team.write({
            'member_ids': [(4, self.user_sales_leads.id)]
        })
        added = self.env['crm.team.member'].search([('crm_team_id', '=', self.new_team.id), ('user_id', '=', self.user_sales_leads.id)])
        self.assertEqual(self.new_team.crm_team_member_ids, new_member + added)
        self.assertEqual(self.new_team.crm_team_member_all_ids, new_member + added)
        self.assertEqual(self.new_team.member_ids, self.env.user | self.user_sales_leads)

        # archiving membership correctly updates m2m and o2m
        added.write({'active': False})
        self.assertEqual(self.new_team.crm_team_member_ids, new_member)
        self.assertEqual(self.new_team.crm_team_member_all_ids, new_member + added)
        self.assertEqual(self.new_team.member_ids, self.env.user)

        # reactivating correctly updates m2m and o2m
        added.write({'active': True})
        self.assertEqual(self.new_team.crm_team_member_ids, new_member + added)
        self.assertEqual(self.new_team.crm_team_member_all_ids, new_member + added)
        self.assertEqual(self.new_team.member_ids, self.env.user | self.user_sales_leads)

        # send to db as errors may pop at that step (like trying to set NULL on a m2o inverse of o2m)
        self.new_team.flush()

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
