from odoo.tests import TransactionCase, new_test_user, tagged

from odoo.addons.base.tests.common import converted_reach


@tagged("post_install", "-at_install")
class TestEventLeadRuleCompanyGuard(TransactionCase):
    def test_a_rule_of_another_company_is_out_of_reach(self):
        other_company = self.env["res.company"].create({"name": "Lead Rule Elsewhere"})
        manager = new_test_user(
            self.env, login="lead_rule_manager", groups="event.group_event_manager"
        )
        Rule = self.env["event.lead.rule"]
        values = {
            "lead_creation_basis": "attendee",
            "lead_creation_trigger": "create",
            "lead_type": "lead",
        }
        here = Rule.create(
            {**values, "name": "Here", "company_id": self.env.company.id}
        )
        there = Rule.create({**values, "name": "There", "company_id": other_company.id})
        shared = Rule.create({**values, "name": "Shared", "company_id": False})
        rules = here | there | shared

        self.assertEqual(
            rules.with_user(manager).search([("id", "in", rules.ids)]), here | shared
        )
        self.assertEqual(
            converted_reach(self.env, "event.lead.rule", manager) & rules,
            here | shared,
        )
