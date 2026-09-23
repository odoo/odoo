from odoo.tests import TransactionCase, tagged

from odoo.addons.team.hooks import SALES_TEAM_RULES, _remove_sales_team_rules


@tagged("post_install", "-at_install")
class TestSalesTeamRulesRemoved(TransactionCase):
    def test_every_row_base_converted_from_a_sales_team_rule_goes(self):
        # what base 1.97 left of a sales_team rule with two groups: the rule's
        # own row and one `<rule>_<group>` row for the second group
        model_id = self.env["ir.model"]._get_id("res.partner")
        rows = self.env["ir.access"]
        for name in ("crm_team_member_rule_all", "crm_team_member_rule_all_group_x"):
            row = self.env["ir.access"].create(
                {
                    "name": name,
                    "model_id": model_id,
                    "group_id": self.env.ref("base.group_user").id,
                    "kind": "permission",
                    "operation": "r",
                }
            )
            self.env["ir.model.data"].create(
                {
                    "module": "sale_team",
                    "name": name,
                    "model": "ir.access",
                    "res_id": row.id,
                    "noupdate": True,
                }
            )
            rows |= row
        kept = self.env["ir.access"].create(
            {
                "name": "kept",
                "model_id": model_id,
                "group_id": self.env.ref("base.group_user").id,
                "kind": "permission",
                "operation": "r",
            }
        )
        self.env.flush_all()
        self.assertIn("crm_team_member_rule_all", SALES_TEAM_RULES)

        _remove_sales_team_rules(self.env.cr)

        self.env.invalidate_all()
        self.assertFalse(rows.exists())
        self.assertTrue(kept.exists())
