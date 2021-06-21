# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import exceptions
from odoo.addons.sales_team.tests.common import TestSalesCommon, TestSalesMC
from odoo.tests.common import users


class TestDefaultTeam(TestSalesCommon):
    """Tests to check if correct default team is found."""

    @classmethod
    def setUpClass(cls):
        """Set up data for default team tests."""
        super(TestDefaultTeam, cls).setUpClass()
        cls.company_2 = cls.env['res.company'].create({
            'name': 'New Test Company',
            'email': 'company.2@test.example.com',
            'country_id': cls.env.ref('base.fr').id,
        })
        cls.team_c2 = cls.env['crm.team'].create({
            'name': 'C2 Team1',
            'sequence': 1,
            'company_id': cls.company_2.id,
        })
        cls.team_sequence = cls.env['crm.team'].create({
            'name': 'Team LowSequence',
            'sequence': 0,
            'company_id': False,
        })
        cls.team_responsible = cls.env['crm.team'].create({
            'name': 'Team 3',
            'user_id': cls.user_sales_manager.id,
            'sequence': 3,
            'company_id': cls.company_main.id
        })

    def test_default_team_member(self):
        with self.with_user('user_sales_leads'):
            team = self.env['crm.team']._get_default_team_id()
            self.assertEqual(team, self.sales_team_1)

        # responsible with lower sequence better than member with higher sequence
        self.team_responsible.user_id = self.user_sales_leads.id
        with self.with_user('user_sales_leads'):
            team = self.env['crm.team']._get_default_team_id()
            self.assertEqual(team, self.team_responsible)

    def test_default_team_fallback(self):
        """ Test fallback: domain, order """
        self.sales_team_1.member_ids = [(5,)]
        self.sales_team_1.flush()

        with self.with_user('user_sales_leads'):
            team = self.env['crm.team']._get_default_team_id()
            self.assertEqual(team, self.team_sequence)

        # next one is team_responsible with sequence = 3 (team_c2 is in another company)
        self.team_sequence.active = False
        with self.with_user('user_sales_leads'):
            team = self.env['crm.team']._get_default_team_id()
            self.assertEqual(team, self.team_responsible)

        self.user_sales_leads.write({
            'company_ids': [(4, self.company_2.id)],
            'company_id': self.company_2.id,
        })
        # multi company: switch company
        self.user_sales_leads.write({'company_id': self.company_2.id})
        with self.with_user('user_sales_leads'):
            team = self.env['crm.team']._get_default_team_id()
            self.assertEqual(team, self.team_c2)


class TestMultiCompany(TestSalesMC):
    """Tests to check multi company management with sales team and their
    members. """

    @users('user_sales_manager')
    def test_team_members(self):
        """ Test update of team users involving company check """
        team_c2 = self.env['crm.team'].browse(self.team_c2.id)
        team_c2.write({'name': 'Manager Update'})
        self.assertEqual(team_c2.member_ids, self.env['res.users'])

        # can add someone from same company
        self.env.user.write({'company_id': self.company_2.id})
        team_c2.write({'member_ids': [(4, self.env.user.id)]})
        self.assertEqual(team_c2.member_ids, self.env.user)

        # cannot add someone from another company
        with self.assertRaises(exceptions.UserError):
            team_c2.write({'member_ids': [(4, self.user_sales_salesman.id)]})

        # reset members, change company
        team_c2.write({'member_ids': [(5, 0)], 'company_id': self.company_main.id})
        self.assertEqual(team_c2.member_ids, self.env['res.users'])
        team_c2.write({'member_ids': [(4, self.user_sales_salesman.id)]})
        self.assertEqual(team_c2.member_ids, self.user_sales_salesman)

        # cannot change company as it breaks memberships mc check
        with self.assertRaises(exceptions.UserError):
            team_c2.write({'company_id': self.company_2.id})

    @users('user_sales_manager')
    def test_team_memberships(self):
        """ Test update of team member involving company check """
        team_c2 = self.env['crm.team'].browse(self.team_c2.id)
        team_c2.write({'name': 'Manager Update'})
        self.assertEqual(team_c2.member_ids, self.env['res.users'])

        # can add someone from same company
        self.env.user.write({'company_id': self.company_2.id})
        team_c2.write({'crm_team_member_ids': [(0, 0, {'user_id': self.env.user.id})]})
        self.assertEqual(team_c2.member_ids, self.env.user)

        # cannot add someone from another company
        with self.assertRaises(exceptions.UserError):
            team_c2.write({'crm_team_member_ids': [(0, 0, {'user_id': self.user_sales_salesman.id})]})

        # reset members, change company
        team_c2.write({'member_ids': [(5, 0)], 'company_id': self.company_main.id})
        self.assertEqual(team_c2.member_ids, self.env['res.users'])
        team_c2.write({'crm_team_member_ids': [(0, 0, {'user_id': self.user_sales_salesman.id})]})
        self.assertEqual(team_c2.member_ids, self.user_sales_salesman)

        # cannot change company as it breaks memberships mc check
        with self.assertRaises(exceptions.UserError):
            team_c2.write({'company_id': self.company_2.id})
