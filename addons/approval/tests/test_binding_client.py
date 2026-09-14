from odoo.exceptions import AccessError, UserError
from odoo.tests import common, tagged

from odoo.addons.approval.tests.common import add_category_approver


@tagged("post_install", "-at_install")
class TestApprovalBindingClient(common.TransactionCase):
    """What the approval button asks `approval.binding`, and what it is told."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Binding = cls.env["approval.binding"]
        cls.partner_model = cls.env["ir.model"]._get("res.partner")
        cls.approver, cls.peer, cls.later, cls.requester = (
            cls._user(login)
            for login in (
                "client_approver",
                "client_peer",
                "client_later",
                "client_req",
            )
        )
        cls.flat_category = cls.env["approval.category"].create(
            {"name": "Client Flat", "approval_minimum": 1, "allow_self_approval": True}
        )
        add_category_approver(
            cls.flat_category, cls.approver, required=True, sequence=10
        )
        cls.step_category = cls.env["approval.category"].create(
            {"name": "Client Steps", "approval_minimum": 1, "allow_self_approval": True}
        )
        for sequence, users in ((10, (cls.approver, cls.peer)), (20, (cls.later,))):
            cls.env["approval.category.step"].create(
                {
                    "category_id": cls.step_category.id,
                    "name": f"Step {sequence}",
                    "sequence": sequence,
                    "member_ids": [(0, 0, {"user_id": user.id}) for user in users],
                }
            )

    @classmethod
    def _user(cls, login):
        groups = (
            cls.env.ref("base.group_user"),
            cls.env.ref("base.group_partner_manager"),
        )
        return cls.env["res.users"].create(
            {
                "name": login,
                "login": login,
                "email": f"{login}@test.com",
                "group_ids": [(6, 0, [group.id for group in groups])],
            }
        )

    def tearDown(self):
        self.Binding._unregister_hook()
        super().tearDown()

    def _bind(self, category, **vals):
        binding = self.Binding.create(
            {
                "model_id": self.partner_model.id,
                "method": "action_archive",
                "mode": "request",
                "category_id": category.id,
                "run_on_approval": False,
                **vals,
            }
        )
        self.Binding._unregister_hook()
        self.Binding._register_hook()
        return binding

    def _partner(self, **vals):
        return self.env["res.partner"].create({"name": "Client Partner", **vals})

    def _spec(self, partner, user, method="action_archive", action_id=False):
        return self.Binding.with_user(user).get_button_approvals(
            [
                {
                    "model": "res.partner",
                    "res_id": partner.id,
                    "method": method,
                    "action_id": action_id,
                }
            ]
        )[0]

    def test_get_views_flags_a_model_gated_in_block_or_request_mode(self):
        binding = self._bind(self.flat_category, mode="advise")
        views = self.env["res.partner"].get_views([[False, "form"]])
        self.assertFalse(views["models"]["res.partner"]["has_approval_bindings"])
        binding.mode = "request"
        views = self.env["res.partner"].get_views([[False, "form"]])
        self.assertTrue(views["models"]["res.partner"]["has_approval_bindings"])

    def test_an_ungated_button_draws_nothing(self):
        result = self._spec(self._partner(), self.requester, "open_commercial_entity")
        self.assertEqual(
            result, {"gated": False, "approved": True, "request": False, "steps": []}
        )

    def test_before_any_call_the_steps_show_who_may_decide(self):
        self._bind(self.step_category)
        result = self._spec(self._partner(), self.peer)
        self.assertTrue(result["gated"])
        self.assertFalse(result["approved"])
        self.assertFalse(result["request"])
        self.assertEqual(
            [(step["name"], step["can_decide"]) for step in result["steps"]],
            [("Step 10", True), ("Step 20", False)],
        )

    def test_the_check_raises_the_request_and_runs_nothing(self):
        self._bind(self.flat_category)
        partner = self._partner()
        check = self.Binding.with_user(self.requester).check_button_approval(
            "res.partner", partner.id, "action_archive", False
        )
        self.assertFalse(check["approved"])
        request = self.env["approval.request"].browse(check["request_id"])
        self.assertEqual(request.state, "pending")
        request.with_user(self.approver).action_approve()
        check = self.Binding.with_user(self.requester).check_button_approval(
            "res.partner", partner.id, "action_archive", False
        )
        self.assertTrue(check["approved"])
        self.assertTrue(partner.active, "a check runs nothing")

    def test_a_decision_counts_toward_its_step_and_a_later_step_may_withdraw_it(self):
        self._bind(self.step_category)
        partner = self._partner()
        result = self.Binding.with_user(self.approver).action_decide_approval(
            "res.partner", partner.id, "action_archive", False, True
        )
        first = result["steps"][0]
        self.assertEqual(
            [decision["user_id"] for decision in first["decisions"]],
            [self.approver.id],
        )
        self.assertFalse(first["can_decide"], "one decision per user")
        self.assertTrue(first["decisions"][0]["can_withdraw"])
        self.assertFalse(
            self._spec(partner, self.peer)["steps"][0]["decisions"][0]["can_withdraw"]
        )
        self.assertTrue(
            self._spec(partner, self.later)["steps"][0]["decisions"][0]["can_withdraw"]
        )
        result = self.Binding.with_user(self.later).action_withdraw_decision(
            "res.partner",
            partner.id,
            "action_archive",
            False,
            first["decisions"][0]["approver_id"],
        )
        self.assertEqual(result["steps"][0]["decisions"], [])

    def test_the_button_offers_a_step_only_to_users_of_the_request_company(self):
        company_b = self.env["res.company"].create({"name": "Client Company B"})
        member_b = self._user("client_member_b")
        member_b.write({"company_ids": [(4, company_b.id)], "company_id": company_b.id})
        category = self.env["approval.category"].create(
            {
                "name": "Client Company Steps",
                "approval_minimum": 1,
                "company_id": False,
                "allow_self_approval": True,
            }
        )
        first, _later = (
            self.env["approval.category.step"].create(
                {
                    "category_id": category.id,
                    "name": name,
                    "sequence": sequence,
                    "member_ids": [(0, 0, {"user_id": user.id}) for user in users],
                }
            )
            for name, sequence, users in (
                ("First", 10, member_b),
                ("Later", 20, member_b | self.peer),
            )
        )
        self._bind(category)
        partner = self._partner()

        self.Binding.with_user(member_b).with_company(company_b).action_decide_approval(
            "res.partner", partner.id, "action_archive", False, True, first.id
        )

        request = self.env["approval.request"].search(
            [("res_model", "=", "res.partner"), ("res_id", "=", partner.id)]
        )
        self.assertEqual(request.company_id, company_b)
        self.assertNotIn(self.peer, request.approver_ids.user_id)
        steps = {step["name"]: step for step in self._spec(partner, self.peer)["steps"]}
        self.assertFalse(steps["Later"]["can_decide"])
        steps = {step["name"]: step for step in self._spec(partner, member_b)["steps"]}
        self.assertTrue(steps["Later"]["can_decide"])

    def test_the_button_decides_the_step_it_is_drawn_under(self):
        category = self.env["approval.category"].create(
            {
                "name": "Client Two Pools",
                "approval_minimum": 1,
                "allow_self_approval": True,
            }
        )
        pool_a, pool_b = (
            self.env["approval.category.step"].create(
                {
                    "category_id": category.id,
                    "name": name,
                    "sequence": sequence,
                    "member_ids": [(0, 0, {"user_id": user.id}) for user in users],
                }
            )
            for name, sequence, users in (
                ("Pool A", 10, (self.approver, self.peer)),
                ("Pool B", 20, (self.approver, self.later)),
            )
        )
        self._bind(category)
        partner = self._partner()

        def decide(step):
            return self.Binding.with_user(self.approver).action_decide_approval(
                "res.partner", partner.id, "action_archive", False, True, step.id
            )

        def steps_by_name(result):
            return {step["name"]: step for step in result["steps"]}

        result = decide(pool_b)
        steps = steps_by_name(result)
        self.assertEqual(
            [decision["user_id"] for decision in steps["Pool B"]["decisions"]],
            [self.approver.id],
        )
        self.assertEqual(
            steps["Pool A"]["decisions"], [], "approving under Pool B left Pool A open"
        )
        self.assertTrue(steps["Pool A"]["can_decide"])
        self.assertFalse(steps["Pool B"]["can_decide"])
        self.assertFalse(result["approved"])
        approver_id = steps["Pool B"]["decisions"][0]["approver_id"]

        self.assertTrue(decide(pool_a)["approved"])

        result = self.Binding.with_user(self.approver).action_withdraw_decision(
            "res.partner", partner.id, "action_archive", False, approver_id, pool_b.id
        )
        steps = steps_by_name(result)
        self.assertFalse(result["approved"])
        self.assertEqual(
            [decision["user_id"] for decision in steps["Pool A"]["decisions"]],
            [self.approver.id],
        )
        self.assertEqual(steps["Pool B"]["decisions"], [])

    def test_a_click_after_the_decided_step_is_archived_decides_the_rest(self):
        """Studio's test_08_archive."""
        category = self.env["approval.category"].create(
            {
                "name": "Client Archive",
                "approval_minimum": 1,
                "allow_self_approval": True,
            }
        )
        Step = self.env["approval.category.step"]
        exclusive = Step.create(
            {
                "category_id": category.id,
                "name": "Exclusive",
                "sequence": 10,
                "exclusive": True,
                "member_ids": [(0, 0, {"user_id": self.approver.id})],
            }
        )
        Step.create(
            {
                "category_id": category.id,
                "name": "Base",
                "sequence": 20,
                "member_ids": [
                    (0, 0, {"user_id": user.id}) for user in (self.approver, self.peer)
                ],
            }
        )
        self._bind(category, approve_on_invoke=True)
        partner = self._partner()

        def check():
            return self.Binding.with_user(self.approver).check_button_approval(
                "res.partner", partner.id, "action_archive", False
            )["approved"]

        self.assertFalse(check(), "the exclusive step takes the approval")
        exclusive.active = False
        self.assertTrue(check(), "with it archived, the next click decides the base")

    def test_a_step_of_another_button_is_not_decided(self):
        self._bind(self.flat_category)
        partner = self._partner()
        foreign = self.step_category.step_ids[:1]
        with self.assertRaises(UserError):
            self.Binding.with_user(self.approver).action_decide_approval(
                "res.partner", partner.id, "action_archive", False, True, foreign.id
            )

    def test_a_refusal_from_the_button_is_reopened_by_the_refuser_only(self):
        self._bind(self.flat_category)
        partner = self._partner()
        self.Binding.with_user(self.requester).check_button_approval(
            "res.partner", partner.id, "action_archive", False
        )
        result = self.Binding.with_user(self.approver).action_decide_approval(
            "res.partner", partner.id, "action_archive", False, False
        )
        self.assertEqual(result["request"]["state"], "refused")
        self.assertTrue(result["request"]["can_reopen"])
        step = result["steps"][0]
        self.assertEqual(
            (step["id"], step["minimum"]), (self.flat_category.step_ids.id, 1)
        )
        refusal = step["decisions"][0]
        self.assertEqual(refusal["state"], "refused")
        self.assertFalse(self._spec(partner, self.requester)["request"]["can_reopen"])
        with self.assertRaises(AccessError):
            self.Binding.with_user(self.requester).action_withdraw_decision(
                "res.partner",
                partner.id,
                "action_archive",
                False,
                refusal["approver_id"],
            )
        result = self.Binding.with_user(self.approver).action_withdraw_decision(
            "res.partner", partner.id, "action_archive", False, refusal["approver_id"]
        )
        self.assertEqual(result["request"]["state"], "new")

    def test_a_record_the_caller_cannot_read_is_refused(self):
        """Studio's test_07_forbidden_record."""
        self._bind(self.flat_category)
        elsewhere = self.env["res.company"].create({"name": "Client Elsewhere"})
        partner = self._partner(company_id=elsewhere.id)
        with self.assertRaises(AccessError):
            self._spec(partner, self.requester)

    def test_an_action_button_is_answered_by_its_action_binding(self):
        action = self.env["ir.actions.server"].create(
            {
                "name": "Client Action",
                "model_id": self.partner_model.id,
                "state": "code",
                "code": "records.write({'comment': 'ran'})",
            }
        )
        self.Binding.create(
            {
                "model_id": self.partner_model.id,
                "action_id": action.id,
                "mode": "request",
                "category_id": self.flat_category.id,
                "run_on_approval": False,
            }
        )
        partner = self._partner()
        result = self._spec(partner, self.requester, False, str(action.id))
        self.assertTrue(result["gated"])
        check = self.Binding.with_user(self.requester).check_button_approval(
            "res.partner", partner.id, False, action.id
        )
        self.assertFalse(check["approved"])
        self.assertFalse(partner.comment)
