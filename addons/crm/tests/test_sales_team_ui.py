from odoo import tests
from odoo.tests import HttpCase
from odoo.tests.common import users

from odoo.addons.sale_team.tests.common import SalesTeamCommon


@tests.tagged("post_install", "-at_install")
class TestUi(HttpCase, SalesTeamCommon):
    @users("salesmanager")
    def test_crm_team_members_mono_company(self):
        self.sale_manager.sudo().group_ids -= self.env.ref("base.group_multi_company")
        self.env["ir.config_parameter"].sudo().set_param(
            "sale_team.membership_multi", True
        )

        self.start_tour("/", "create_crm_team_tour", login="salesmanager")

        created_team = self.env["team.team"].search([("name", "=", "My CRM Team")])
        self.assertTrue(bool(created_team))
        self.assertEqual(created_team.member_ids, self.sale_user | self.sale_manager)
