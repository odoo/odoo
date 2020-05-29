# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sales_team.tests.common import TestSalesMC


class TestDefaultTeam(TestSalesMC):
    """Tests to check if correct default team is found."""

    @classmethod
    def setUpClass(cls):
        """Set up data for default team tests."""
        super(TestDefaultTeam, cls).setUpClass()

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
