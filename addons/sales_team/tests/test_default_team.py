from odoo.tests import common


class TestDefaultTeam(common.SavepointCase):
    """Tests to check if correct default team is found."""

    @classmethod
    def setUpClass(cls):
        """Set up data for default team tests."""
        super(TestDefaultTeam, cls).setUpClass()
        cls.CrmTeam = cls.env['crm.team']
        ResUsers = cls.env['res.users'].with_context(
            {'no_reset_password': True})
        group_sale_manager = cls.env.ref('sales_team.group_sale_manager')
        cls.user = ResUsers.create({
            'name': 'Team User',
            'login': 'sales_team_user',
            'email': 'sales.team.user@example.com',
            'groups_id': [(6, 0, [group_sale_manager.id])]
        })
        cls.team_1 = cls.env['crm.team'].create({
            'name': 'Test Team',
            'member_ids': [(4, cls.user.id)],
            'company_id': False
        })
        # Europe Team (fall back  team)
        cls.team_2 = cls.env.ref('sales_team.team_sales_department')

    def test_01_user_team(self):
        """Get default team, when user belongs to one."""
        team = self.CrmTeam.sudo(self.user)._get_default_team_id()
        self.assertEqual(team, self.team_1)

    def test_02_fallback_team(self):
        """Get default team when user does not belong to any team.

        Case 1: fall back default team (from XML ref) is active.
        Case 2: fall back default team is not active.
        """
        # Clear users from team.
        self.team_1.member_ids = [(5,)]
        # Case 1.
        team = self.CrmTeam.sudo(self.user)._get_default_team_id()
        self.assertEqual(team, self.team_2)
        # Case 2.
        self.team_2.active = False
        team = self.CrmTeam.sudo(self.user)._get_default_team_id()
        self.assertEqual(team, self.CrmTeam)
