# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tests
from odoo.tests import HttpCase
from odoo.tests.common import users
from odoo.addons.sales_team.tests.common import SalesTeamCommon


@tests.tagged('post_install', '-at_install')
class TestUi(HttpCase, SalesTeamCommon):

    @users('salesmanager')
    def test_crm_team_members_mono_company(self):
        """ Make sure you can create crm.team records with members in a mono-company scenario """
        self.sale_manager.sudo().group_ids -= self.env.ref("base.group_multi_company")
        self.env['ir.config_parameter'].sudo().set_param('sales_team.membership_multi', True)

        self.start_tour("/", "create_crm_team_tour", login="salesmanager")

        created_team = self.env["crm.team"].search([("name", "=", "My CRM Team")])
        self.assertTrue(bool(created_team))
        self.assertEqual(
            created_team.member_ids,
            self.sale_user | self.sale_manager
        )
