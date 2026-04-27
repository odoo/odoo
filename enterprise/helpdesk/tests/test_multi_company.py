# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError, UserError
from odoo.tests import new_test_user

from .common import HelpdeskCommon


class TestHelpdeskMultyCompany(HelpdeskCommon):

    def test_team_per_company(self):
        companies = self.env['res.company'].with_context(tracking_disable=True).create([
            {'name': 'new_company1'},
            {'name': 'new_company2'},
            {'name': 'new_company3'},
        ])
        helpdek_teams = self.env['helpdesk.team'].search([('company_id', 'in', companies.ids)])
        self.assertEqual(len(helpdek_teams), len(companies), "The team should be created for each company.")
        self.assertEqual(helpdek_teams.company_id, companies, "Each helpdesk team should be set to a company.")

    def test_create_utf8_companies(self):
        """ At the moment of creating this test, mail.alias was restricted to ascii characters.
        Creating new company with helpdesk installed attempts to create a mail.alias with the company name.
        Doing it once will convert all non ASCII characters to question marks. (Ex. "好色" -> "??")
        However, doing it again for a company name with same number of characters will violate the unique constraint.

        This test checks that we have a fallback for this behavior.
        """
        companies = self.env['res.company'].with_context(tracking_disable=True).create([
            {'name': '好色'},
            {'name': '色好'},
        ])
        helpdek_teams = self.env['helpdesk.team'].search([('company_id', 'in', companies.ids)])
        self.assertEqual(len(helpdek_teams), len(companies), "The team should be created for each company.")
        self.assertEqual(helpdek_teams.company_id, companies, "Each helpdesk team should be set to a company.")

    def test_multi_company(self):
        Team = self.env['helpdesk.team'].with_context(tracking_disable=True)
        Ticket = self.env['helpdesk.ticket'].with_context(tracking_disable=True)

        # Main company
        ticket_main = Ticket.with_user(self.helpdesk_user).create({
            'name': 'Partner Ticket 1',
            'team_id': self.test_team.id,
            'partner_id': self.partner.id,
            'company_id': self.main_company_id
        })

        # company B
        company_b = self.env['res.company'].with_context(tracking_disable=True).create({
            "name": "Test Company B",
        })
        user_b = new_test_user(
            self.env,
            login='user company b',
            groups='base.group_user,helpdesk.group_helpdesk_user',
            company_id=company_b.id,
        )
        manager_b = new_test_user(
            self.env,
            login='manager company b',
            groups='base.group_user, helpdesk.group_helpdesk_manager',
            company_id=company_b.id,
        )
        team_b = Team.with_user(manager_b).create({'name': 'Team B'})
        ticket_b = Ticket.with_company(company_b).create({
            'name': 'Partner Ticket 2',
            'team_id': team_b.id,
            'partner_id': self.partner.id,
        })

        # Check access for ticket and team on main company
        self.assertEqual(ticket_main.company_id, self.helpdesk_user.company_id, "Ticket's company and helpdesk user's company should be same.")
        tickets_main = Ticket.with_user(self.helpdesk_user).search([
            ('team_id', '=', ticket_main.team_id.id),
        ])
        self.assertTrue(tickets_main.name, "Helpdesk user can read ticket of main company.")
        team_main = Team.with_user(self.helpdesk_user).search([('company_id', '=', self.main_company_id)], limit=1)
        self.assertTrue(team_main, "Helpdesk user can read team of main company.")
        # try to access the main team with company B
        with self.assertRaises(AccessError):
            self.test_team.with_user(manager_b).write({'company_id': company_b})
        with self.assertRaises(AccessError):
            self.test_team.with_user(user_b).read()
        with self.assertRaises(AccessError):
            ticket_main.with_user(user_b).read()

        # Check access for ticket and team on company B
        self.assertEqual(ticket_b.company_id, team_b.company_id, "Ticket's company and team's company should be same.")
        tickets_b = Ticket.with_user(user_b).search([
            ('team_id', '=', ticket_b.team_id.id),
        ])
        self.assertTrue(tickets_b.name, "Helpdesk user can read ticket of company B.")
        teams_b = Team.with_user(user_b).search([('company_id', '=', company_b.id)], limit=1)
        self.assertTrue(teams_b, "Helpdesk user can read team of company B.")
        # try to access the team of company B with main company
        with self.assertRaises(AccessError):
            team_b.with_user(self.helpdesk_user).read()
        with self.assertRaises(AccessError):
            ticket_b.with_user(self.helpdesk_user).read()

    def test_partner_id_company_is_different_ticket_company(self):
        '''
            Create a ticket with an associated partner with a different company than the one of the
            ticket
        '''
        Ticket = self.env['helpdesk.ticket'].with_context(tracking_disable=True)
        ticket_main = Ticket.with_user(self.helpdesk_user).create({
            'name': 'Partner Ticket 1',
            'team_id': self.test_team.id,
            'partner_id': self.partner.id,
            'company_id': self.main_company_id
        })

        company_b = self.env['res.company'].with_context(tracking_disable=True).create({
            "name": "Test Company B",
        })

        partner_b = self.env['res.partner'].create({
            'name': 'Customer B',
            'company_id': company_b.id,
        })

        # Try to change the partner of the ticket main to the partner of the company B
        with self.assertRaises(UserError):
            ticket_main.write({'partner_id': partner_b.id})

        # Try to change the company of the main partner
        with self.assertRaises(UserError):
            self.partner.write({'company_id': company_b.id})

        self.partner.write({'company_id': False})

    def test_team_assignement_resource_multicompany(self):
        '''
            Test that the team computes assignement considering only resources of the team company.

            Test Case:
            ==========
            - have a user with 1 resource in different company than the one set on the helpdesk team
            - add the user as member of a helpdesk team of company A
            - check that only the resources of company A are considered to compute working intervals
        '''
        Team = self.env['helpdesk.team'].with_context(tracking_disable=True)
        company = self.env['res.company'].with_context(tracking_disable=True).create({
            "name": "Test Company",
        })
        user_multi = new_test_user(
            self.env,
            'umc',
            'helpdesk.group_helpdesk_user',
            name='User Multi Company',
            email='a@b.c',
            context={'tracking_disable': True},
        )
        helpdesk_user = new_test_user(
            self.env,
            'helpdesk_user',
            'helpdesk.group_helpdesk_user',
            company_id=company.id,
            name='Helpdesk User',
            email='helpdesk_user@test.com',
            context={'tracking_disable': True},
        )
        self.env['resource.resource'].create({
            'name': 'Resource A',
            'user_id': user_multi.id,
        })
        team_a = Team.create({
            'name': 'Team A',
            'company_id': company.id,
            'auto_assignment': True,
            'assign_method': 'randomly',
            'member_ids': user_multi.ids,
        })
        ticket = self.env['helpdesk.ticket'].with_company(company).with_user(helpdesk_user).create({
            'name': 'test ticket',
            'team_id': team_a.id,
        })
        self.assertEqual(ticket.user_id, user_multi)
        self.assertEqual(ticket.company_id, company)
