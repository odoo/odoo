# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import exceptions
from odoo.tests import tagged, users
from odoo.addons.mail.tests.common import mail_new_test_user

from odoo.addons.sales_team.tests.common import SalesTeamCommon, TestSalesCommon, TestSalesMC


class TestDefaultTeam(TestSalesCommon):
    """Tests to check if correct default team is found."""

    @classmethod
    def setUpClass(cls):
        """Set up data for default team tests."""
        super(TestDefaultTeam, cls).setUpClass()
        cls.env['ir.config_parameter'].set_param('sales_team.membership_multi', True)

        # Salesmen organization
        # ------------------------------------------------------------
        # Role: M (team member) R (team manager)
        # SALESMAN---------------sales_team_1---C2Team1---LowSequ---Team3
        # admin------------------M-------------- --------- ---------
        # user_sales_manager-----R-------------- --------- ---------R
        # user_sales_leads-------M-------------- ---------M---------
        # user_sales_salesman----/-------------- --------- ---------

        # Sales teams organization
        # ------------------------------------------------------------
        # SALESTEAM-----------SEQU-----COMPANY
        # LowSequence---------0--------False
        # C2Team1-------------1--------C2
        # Team3---------------3--------Main
        # sales_team_1--------5--------False
        # data----------------9999-----??

        cls.company_2 = cls.env['res.company'].create({
            'name': 'New Test Company',
            'email': 'company.2@test.example.com',
            'country_id': cls.env.ref('base.fr').id,
        })
        cls.team_c2 = cls.env['crm.team'].create({
            'name': 'C2 Team1',
            'sequence': 1,
            'company_id': cls.company_2.id,
            'user_id': False,
        })
        cls.team_sequence = cls.env['crm.team'].create({
            'company_id': False,
            'name': 'Team LowSequence',
            'member_ids': [(4, cls.user_sales_leads.id)],
            'sequence': 0,
            'user_id': False,
        })
        cls.team_responsible = cls.env['crm.team'].create({
            'company_id': cls.company_main.id,
            'name': 'Team 3',
            'user_id': cls.user_sales_manager.id,
            'sequence': 3,
        })

    def test_default_team_fallback(self):
        """ Test fallbacks when computing default team without any memberships:
        domain, order """
        self.sales_team_1.member_ids = [(5,)]
        self.team_sequence.member_ids = [(5,)]
        (self.sales_team_1 + self.team_sequence).flush_model()
        self.assertFalse(self.env['crm.team.member'].search([('user_id', '=', self.user_sales_leads.id)]))

        # default is better sequence matching company criterion
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
        self.user_sales_leads.write({
            'company_id': self.company_2.id,
            'company_ids': [(4, self.company_2.id)],
        })
        with self.with_user('user_sales_leads'):
            team = self.env['crm.team']._get_default_team_id()
            self.assertEqual(team, self.team_c2)

    def test_default_team_member(self):
        """ Test default team choice based on sequence, when having several
        possible choices due to membership """
        with self.with_user('user_sales_leads'):
            team = self.env['crm.team']._get_default_team_id()
            self.assertEqual(team, self.team_sequence)

        self.team_sequence.member_ids = [(5,)]
        self.team_sequence.flush_model()
        with self.with_user('user_sales_leads'):
            team = self.env['crm.team']._get_default_team_id()
            self.assertEqual(team, self.sales_team_1)

        # responsible with lower sequence better than member with higher sequence
        self.team_responsible.user_id = self.user_sales_leads.id
        with self.with_user('user_sales_leads'):
            team = self.env['crm.team']._get_default_team_id()
            self.assertEqual(team, self.team_responsible)

        # in case of same sequence: take latest team
        self.team_responsible.sequence = self.sales_team_1.sequence
        with self.with_user('user_sales_leads'):
            team = self.env['crm.team']._get_default_team_id()
            self.assertEqual(team, self.team_responsible)

    def test_default_team_wcontext(self):
        """ Test default team choice when having a value in context """
        with self.with_user('user_sales_leads'):
            team = self.env['crm.team']._get_default_team_id()
            self.assertEqual(team, self.team_sequence)

            team = self.env['crm.team'].with_context(
                default_team_id=self.sales_team_1.id
            )._get_default_team_id()
            self.assertEqual(
                team, self.sales_team_1,
                'SalesTeam: default takes over ordering when member / responsible'
            )

        # remove all memberships
        self.sales_team_1.member_ids = [(5,)]
        self.team_sequence.member_ids = [(5,)]
        (self.sales_team_1 + self.team_sequence).flush_model()
        self.assertFalse(self.env['crm.team.member'].search([('user_id', '=', self.user_sales_leads.id)]))

        with self.with_user('user_sales_leads'):
            team = self.env['crm.team']._get_default_team_id()
            self.assertEqual(team, self.team_sequence)

            team = self.env['crm.team'].with_context(
                default_team_id=self.sales_team_1.id
            )._get_default_team_id()
            self.assertEqual(
                team, self.sales_team_1,
                'SalesTeam: default taken into account when no member / responsible'
            )

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

        # cannot add someone from another company (when user allowed only in c1 and team is in c2)
        with self.assertRaises(exceptions.UserError):
            team_c2.write({'member_ids': [(4, self.user_sales_salesman.id)]})

        # reset members, change company
        team_c2.write({'member_ids': [(5, 0)], 'company_id': self.company_main.id})
        self.assertEqual(team_c2.member_ids, self.env['res.users'])
        team_c2.write({'member_ids': [(4, self.user_sales_salesman.id)]})
        self.assertEqual(team_c2.member_ids, self.user_sales_salesman)

        # cannot change team company if its users aren't allowed in the new company
        with self.assertRaises(exceptions.UserError):
            team_c2.write({'company_id': self.company_2.id})

        # a user allowed in multiple companies can be added to a team of any of these companies
        team_c2.write({'member_ids': [(5, 0)]})
        team_c2.write({'company_id': self.company_2.id})
        c1, c2 = self.company_main, self.company_2
        with self.with_user('admin'):  # user_sales_manager can't create user
            user_c1_c2 = mail_new_test_user(
                self.env,
                login=f"Test_user_default_to_c{c1.id}_allowed_c{'c'.join(map(str, [c1.id, c2.id]))}",
                company_id=c1.id,
                company_ids=[(4, company.id) for company in c1 + c2]
            )
        user_c1_c2 = user_c1_c2.with_env(self.env)
        team_c2.write({'member_ids': [(4, user_c1_c2.id)]})
        self.assertIn(user_c1_c2, team_c2.member_ids)

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


@tagged('post_install', '-at_install')
class TestAccessRights(SalesTeamCommon):

    @users('salesmanager')
    def test_access_sales_manager(self):
        """ Test sales manager's access rights """
        # Manager can create a Sales Team
        india_channel = self.env['crm.team'].with_context(tracking_disable=True).create({
            'name': 'India',
        })
        self.assertIn(
            india_channel.id, self.env['crm.team'].search([]).ids,
            'Sales manager should be able to create a Sales Team')

        # Manager can edit a Sales Team
        india_channel.write({'name': 'new_india'})
        self.assertEqual(
            india_channel.name, 'new_india',
            'Sales manager should be able to edit a Sales Team')

        # Manager can delete a Sales Team
        india_channel.unlink()
        self.assertNotIn(
            india_channel.id, self.env['crm.team'].search([]).ids,
            'Sales manager should be able to delete a Sales Team')
