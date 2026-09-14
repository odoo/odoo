from odoo.exceptions import UserError, ValidationError
from odoo.tests import common, tagged

from odoo.addons.approval.tests.common import add_category_approver


@tagged("post_install", "-at_install")
class TestApprovalBindingReset(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Binding = cls.env["approval.binding"]
        cls.partner_model = cls.env["ir.model"]._get("res.partner")
        groups = [
            cls.env.ref("base.group_user").id,
            cls.env.ref("base.group_partner_manager").id,
        ]
        cls.approver, cls.requester = (
            cls.env["res.users"].create(
                {
                    "name": name,
                    "login": login,
                    "email": f"{login}@test.com",
                    "group_ids": [(6, 0, groups)],
                }
            )
            for name, login in (
                ("Reset Approver", "reset_approver"),
                ("Reset Requester", "reset_requester"),
            )
        )
        cls.category = cls.env["approval.category"].create(
            {
                "name": "Reset Category",
                "approval_minimum": 1,
                "allow_self_approval": True,
            }
        )
        add_category_approver(cls.category, cls.approver, required=True, sequence=10)

    def tearDown(self):
        for wrapper, real in reversed(getattr(self, "_swapped_origins", [])):
            wrapper.approval_binding_origin = real
        self.Binding._unregister_hook()
        super().tearDown()

    def _bind(self, **vals):
        binding = self.Binding.create(
            {
                "model_id": self.partner_model.id,
                "method": "action_archive",
                "category_id": self.category.id,
                "reset_domain": "[('city', '=', 'Reset')]",
                **vals,
            }
        )
        self.Binding._unregister_hook()
        self.Binding._register_hook()
        return binding

    def _approved_request(self, partner):
        request = self.env["approval.request"].create(
            {
                "name": "Covering",
                "category_id": self.category.id,
                "request_owner_id": self.requester.id,
                "res_model": "res.partner",
                "res_id": partner.id,
            }
        )
        request.action_confirm()
        request.with_user(self.approver).action_approve()
        return request

    def _count_runs(self):
        wrapper = self.env.registry["res.partner"].action_archive
        real = wrapper.approval_binding_origin
        runs = []

        def counting(records, *args, **kwargs):
            runs.append(tuple(records.ids))
            return real(records, *args, **kwargs)

        wrapper.approval_binding_origin = counting
        self._swapped_origins = [
            *getattr(self, "_swapped_origins", []),
            (wrapper, real),
        ]
        return runs

    def test_the_managed_rule_keeps_its_transition_filter(self):
        """automation.rule clears its pre-update filter whenever `trigger` moves."""
        binding = self._bind(mode="block")
        rule = binding.reset_automation_id
        self.assertEqual(rule.trigger, "on_create_or_write")
        self.assertTrue(rule.filter_pre_domain, "the transition filter was wiped")
        binding.reset_domain = "[('city', '=', 'Again')]"
        self.assertEqual(binding.reset_automation_id, rule, "edited, not replaced")
        self.assertIn("Again", rule.filter_domain)
        self.assertTrue(rule.filter_pre_domain, "an edit wiped the transition filter")

    def test_a_record_returning_to_the_condition_needs_approval_again(self):
        self._bind(mode="block", sudo_policy="enforce")
        partner = self.env["res.partner"].create(
            {"name": "Resettable", "city": "Start"}
        )
        request = self._approved_request(partner)
        partner.city = "Reset"
        self.assertEqual(request.state, "new", "the covering approval was reset")
        with self.assertRaises(UserError):
            partner.with_user(self.requester).action_archive()
        self.assertTrue(partner.active)

    def test_an_edit_by_a_user_who_cannot_manage_approvals_still_resets(self):
        """Resetting an approved request needs a manager; the rule's action runs elevated."""
        self._bind(mode="block", sudo_policy="enforce")
        partner = self.env["res.partner"].create({"name": "Plain", "city": "Start"})
        request = self._approved_request(partner)
        partner.with_user(self.requester).city = "Reset"
        self.assertEqual(request.state, "new")

    def test_an_edit_that_keeps_the_record_in_the_condition_resets_nothing(self):
        """Approved while already matching, then a field the condition reads changes.

        The rule does not fire for a write that leaves every trigger field unchanged,
        so only a real change within the condition exercises the transition filter.
        """
        self._bind(
            mode="block",
            sudo_policy="enforce",
            reset_domain="[('city', 'ilike', 'Reset')]",
        )
        partner = self.env["res.partner"].create({"name": "Already", "city": "Reset"})
        request = self._approved_request(partner)
        partner.city = "Reset North"
        self.assertEqual(request.state, "approved")
        partner.with_user(self.requester).action_archive()
        self.assertFalse(partner.active)

    def test_leaving_and_re_entering_the_condition_is_a_transition(self):
        self._bind(mode="block", sudo_policy="enforce")
        partner = self.env["res.partner"].create(
            {"name": "Round trip", "city": "Reset"}
        )
        request = self._approved_request(partner)
        partner.city = "Elsewhere"
        self.assertEqual(request.state, "approved")
        partner.city = "Reset"
        self.assertEqual(request.state, "new")

    def test_a_second_cycle_runs_on_approval_again(self):
        """The reset clears the one-shot stamp; a reused request is confirmed again."""
        binding = self._bind(mode="request")
        runs = self._count_runs()
        partner = self.env["res.partner"].create(
            {"name": "Two cycles", "city": "Start"}
        )
        partner.with_user(self.requester).action_archive()
        request = self.env["approval.request"].search(
            [("binding_id", "=", binding.id), ("res_id", "=", partner.id)]
        )
        request.with_user(self.approver).action_approve()
        self.assertEqual(len(runs), 1)
        self.assertTrue(request.date_binding_replayed)

        partner.write({"active": True, "city": "Reset"})
        self.assertEqual(request.state, "new")
        self.assertFalse(request.date_binding_replayed, "the one-shot was not cleared")

        partner.with_user(self.requester).action_archive()
        self.assertEqual(request.state, "pending", "the reused request is asked again")
        request.with_user(self.approver).action_approve()
        self.assertEqual(
            len(runs), 2, "a second approval cycle runs the operation again"
        )

    def test_a_decision_on_a_request_still_waiting_is_reset_too(self):
        """Studio's test_create_automation: a reset clears decisions, approved or not."""
        category = self.env["approval.category"].create(
            {"name": "Reset Steps", "allow_self_approval": True}
        )
        Step = self.env["approval.category.step"]
        first, _second = (
            Step.create(
                {
                    "category_id": category.id,
                    "name": name,
                    "sequence": sequence,
                    "member_ids": [(0, 0, {"user_id": self.approver.id})],
                }
            )
            for name, sequence in (("First", 10), ("Second", 20))
        )
        self._bind(mode="request", category_id=category.id)
        partner = self.env["res.partner"].create(
            {"name": "Half decided", "city": "Start"}
        )
        self.Binding.with_user(self.approver).action_decide_approval(
            "res.partner", partner.id, "action_archive", False, True, first.id
        )
        request = self.env["approval.request"].search([("res_id", "=", partner.id)])
        self.assertEqual(request.state, "pending")
        self.assertTrue(request.approver_ids.decided_step_ids)
        partner.city = "Reset"
        self.assertEqual(request.state, "new")
        self.assertFalse(request.approver_ids.decided_step_ids)

    def test_removing_the_condition_removes_the_rule(self):
        binding = self._bind(mode="block")
        rule = binding.reset_automation_id
        binding.reset_domain = False
        self.assertFalse(binding.reset_automation_id)
        self.assertFalse(rule.exists())

    def test_deleting_the_binding_removes_the_rule(self):
        binding = self._bind(mode="block")
        rule = binding.reset_automation_id
        binding.unlink()
        self.assertFalse(rule.exists())

    def test_a_reset_condition_naming_an_unknown_field_is_refused(self):
        with self.assertRaises(ValidationError):
            self._bind(mode="block", reset_domain="[('cityy', '=', 'Reset')]")
