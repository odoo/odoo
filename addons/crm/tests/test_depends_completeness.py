"""`team.team`'s computed fields must declare what they read.

`dashboard_button_name` reads `use_opportunities` from an override that carried
no `@api.depends` at all, and `lead_assignment_max` sums an active-filtered o2m whose
membership changes when a team is archived.
"""

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCrmTeamDependsCompleteness(TransactionCase):
    def test_team_computes_declare_what_they_read(self):
        team = self.env["team.team"].create({"use_sale": True, "name": "Depends probe"})
        self.env["team.member"].create(
            {
                "team_id": team.id,
                "user_id": self.env.ref("base.user_admin").id,
                "lead_assignment_max": 30,
            }
        )
        self.assertDependsComplete(
            team,
            computed_fields=["dashboard_button_name", "lead_assignment_max"],
            probe_fields=["use_opportunities", "active", "name"],
        )
