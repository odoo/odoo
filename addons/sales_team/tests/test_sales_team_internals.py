# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import exceptions
from odoo.addons.sales_team.tests.common import TestSalesMC
from odoo.tests.common import users


class TestSecurity(TestSalesMC):

    @users('user_sales_leads')
    def test_team_access(self):
        sales_team = self.sales_team_1.with_user(self.env.user)

        sales_team.read(['name'])
        for member in sales_team.member_ids:
            member.read(['name'])

        with self.assertRaises(exceptions.AccessError):
            sales_team.write({'name': 'Trolling'})

        for membership in sales_team.crm_team_member_ids:
            membership.read(['name'])
            with self.assertRaises(exceptions.AccessError):
                membership.write({'active': False})

        with self.assertRaises(exceptions.AccessError):
            sales_team.write({'member_ids': [(5, 0)]})

    @users('user_sales_leads')
    def test_team_multi_company(self):
        self.sales_team_1.with_user(self.env.user).read(['name'])
        with self.assertRaises(exceptions.AccessError):
            self.team_c2.with_user(self.env.user).read(['name'])
