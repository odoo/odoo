import ast

from lxml import etree

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tests import tagged

from .common import ApprovalCommon


@tagged("post_install", "-at_install")
class TestCategorySteps(ApprovalCommon):
    """A category that declares steps: each a pool with its own quorum.

    The flat model -- one approver list and one request-wide minimum -- cannot
    tell two steps that each need one of two people from one step that needs two.
    These pin what steps add, and that a category without steps is untouched.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        approver_group = cls.env.ref("approval.group_approval_approver")
        cls.approver_3, cls.approver_4 = (
            cls.env["res.users"].create(
                {
                    "name": name,
                    "login": login,
                    "email": f"{login}@test.com",
                    "group_ids": [(4, approver_group.id)],
                },
            )
            for name, login in (("Step Three", "step_u3"), ("Step Four", "step_u4"))
        )
        cls.step_group = cls.env["res.groups"].create({"name": "Step Test Group"})

    def test_every_domain_editor_reads_its_model_from_a_model_name(self):
        """The domain widget takes a model name; a many2one hands it a record value."""
        for model_name in ("approval.category.step", "approval.rule"):
            Model = self.env[model_name]
            arch = etree.fromstring(Model.get_view(view_type="form")["arch"])
            editors = [
                node for node in arch.iter("field") if node.get("widget") == "domain"
            ]
            self.assertTrue(editors, model_name)
            for node in editors:
                source = ast.literal_eval(node.get("options") or "{}").get("model")
                self.assertEqual(
                    Model._fields[source].type,
                    "char",
                    f"{model_name}.{node.get('name')} reads its model from {source}",
                )

    def _category(self, **vals):
        return self._make_category(name=f"Steps {self.id()}", **vals)

    def _step(self, category, name, users=(), sequence=10, **vals):
        return self.env["approval.category.step"].create(
            {
                "category_id": category.id,
                "name": name,
                "sequence": sequence,
                "member_ids": [Command.create({"user_id": user.id}) for user in users],
                **vals,
            },
        )

    def _approval_activity_users(self, request):
        activity_type = self.env.ref("approval.mail_activity_data_approval")
        return request.activity_ids.filtered(
            lambda activity: activity.activity_type_id == activity_type
        ).user_id

    # -- the defect steps exist for ----------------------------------------

    def test_two_one_of_two_steps_need_one_approval_from_each(self):
        category = self._category()
        self._step(category, "First", (self.approver_1, self.approver_2), 10)
        self._step(category, "Second", (self.approver_3, self.approver_4), 20)
        request = self._prepare_request(category)
        request.with_user(self.approver_1).action_approve()
        request.with_user(self.approver_2).action_approve()
        self.assertEqual(
            request.state,
            "pending",
            "two approvals from the first step must not stand in for the second",
        )
        request.with_user(self.approver_3).action_approve()
        self.assertEqual(request.state, "approved")

    def test_a_step_quorum_of_two(self):
        category = self._category()
        self._step(
            category,
            "Board",
            (self.approver_1, self.approver_2, self.approver_3),
            minimum=2,
        )
        request = self._prepare_request(category)
        request.with_user(self.approver_1).action_approve()
        self.assertEqual(request.state, "pending")
        request.with_user(self.approver_2).action_approve()
        self.assertEqual(request.state, "approved")

    # -- one row per user, and what exclusivity does with it ---------------

    def test_a_user_in_two_steps_counts_for_both_when_neither_is_exclusive(self):
        category = self._category()
        first = self._step(category, "First", (self.approver_1, self.approver_2), 10)
        second = self._step(category, "Second", (self.approver_1, self.approver_3), 20)
        request = self._prepare_request(category)
        row = request.approver_ids.filtered(lambda a: a.user_id == self.approver_1)
        self.assertEqual(len(row), 1, "one row per user per request")
        self.assertEqual(row.step_ids, first | second)
        request.with_user(self.approver_1).action_approve()
        self.assertEqual(request.state, "approved")

    def test_an_exclusive_step_takes_the_approval_for_itself(self):
        category = self._category()
        self._step(
            category, "First", (self.approver_1, self.approver_2), 10, exclusive=True
        )
        self._step(category, "Second", (self.approver_1, self.approver_3), 20)
        request = self._prepare_request(category)
        request.with_user(self.approver_1).action_approve()
        self.assertEqual(
            request.state,
            "pending",
            "an approval on an exclusive step may not also complete another step",
        )
        request.with_user(self.approver_3).action_approve()
        self.assertEqual(request.state, "approved")

    def test_exclusivity_holds_in_the_other_direction(self):
        category = self._category()
        self._step(category, "First", (self.approver_1, self.approver_3), 10)
        self._step(
            category, "Second", (self.approver_1, self.approver_2), 20, exclusive=True
        )
        request = self._prepare_request(category)
        request.with_user(self.approver_1).action_approve()
        self.assertEqual(request.state, "pending")
        request.with_user(self.approver_2).action_approve()
        self.assertEqual(request.state, "approved")

    # -- who is in the pool ----------------------------------------------

    def test_group_members_join_the_step_pool(self):
        self.step_group.user_ids = self.approver_4
        category = self._category()
        self._step(category, "Group step", group_id=self.step_group.id)
        request = self._prepare_request(category)
        self.assertIn(self.approver_4, request.approver_ids.user_id)
        request.with_user(self.approver_4).action_approve()
        self.assertEqual(request.state, "approved")

    def test_an_expired_member_is_not_asked(self):
        category = self._category()
        step = self._step(category, "Delegated", (self.approver_2,))
        self.env["approval.category.step.member"].create(
            {
                "step_id": step.id,
                "user_id": self.approver_1.id,
                "date_end": fields.Date.subtract(fields.Date.today(), days=1),
                "delegated_by_id": self.approver_2.id,
            },
        )
        request = self._prepare_request(category)
        self.assertNotIn(self.approver_1, request.approver_ids.user_id)
        self.assertIn(self.approver_2, request.approver_ids.user_id)

    def test_a_step_whose_condition_does_not_match_is_not_required(self):
        person = self.env["res.partner"].create({"name": "A person"})
        category = self._category()
        self._step(category, "Always", (self.approver_1,), 10)
        self._step(
            category,
            "Companies only",
            (self.approver_2,),
            20,
            subject_model_id=self.env["ir.model"]._get("res.partner").id,
            subject_domain="[('is_company', '=', True)]",
        )
        request = self._prepare_request(
            category, res_model="res.partner", res_id=person.id
        )
        self.assertNotIn(self.approver_2, request.approver_ids.user_id)
        request.with_user(self.approver_1).action_approve()
        self.assertEqual(request.state, "approved")

    # -- decisions --------------------------------------------------------

    def test_a_refusal_in_any_step_refuses_the_request(self):
        category = self._category()
        self._step(category, "First", (self.approver_1,), 10)
        self._step(category, "Second", (self.approver_2,), 20)
        request = self._prepare_request(category)
        request.with_user(self.approver_1).action_approve()
        request.with_user(self.approver_2).with_context(
            skip_wizard=True
        ).action_refuse()
        self.assertEqual(request.state, "refused")

    def test_steps_requested_in_order_only_ask_the_open_step(self):
        category = self._category(notify_sequentially=True)
        self._step(category, "First", (self.approver_1,), 10)
        self._step(category, "Second", (self.approver_2,), 20)
        self._step(category, "Third", (self.approver_3,), 30)
        request = self._prepare_request(category)
        self.assertEqual(self._approval_activity_users(request), self.approver_1)
        request.with_user(self.approver_1).action_approve()
        self.assertIn(self.approver_2, self._approval_activity_users(request))
        self.assertNotIn(self.approver_3, self._approval_activity_users(request))

    def test_a_later_step_may_decide_before_it_is_asked(self):
        """Studio orders the asking, not the deciding."""
        category = self._category(notify_sequentially=True)
        self._step(category, "First", (self.approver_1,), 10)
        self._step(category, "Second", (self.approver_2,), 20)
        request = self._prepare_request(category)
        request.with_user(self.approver_2).action_approve()
        self.assertEqual(request.state, "pending")
        request.with_user(self.approver_1).action_approve()
        self.assertEqual(request.state, "approved")

    def test_the_step_notify_list_is_told_of_a_decision(self):
        category = self._category()
        self._step(
            category,
            "Watched",
            (self.approver_1,),
            notify_user_ids=[Command.set(self.manager_user.ids)],
        )
        request = self._prepare_request(category)
        request.with_user(self.approver_1).action_approve()
        notes = request.message_ids.filtered(
            lambda message: (
                self.manager_user.partner_id in message.partner_ids
                and message.subtype_id == self.env.ref("mail.mt_note")
            )
        )
        self.assertTrue(notes, "the step's notify list got no note")

    # -- configuration that could never work ------------------------------

    def test_confirm_refuses_a_step_that_can_never_meet_its_quorum(self):
        category = self._category()
        self._step(category, "Short", (self.approver_1,), minimum=2)
        with self.assertRaises(UserError):
            self._prepare_request(category)

    def test_a_step_needs_members_or_a_group(self):
        category = self._category()
        with self.assertRaises(ValidationError):
            self._step(category, "Empty")

    def test_the_snapshot_records_the_steps(self):
        category = self._category()
        self._step(category, "First", (self.approver_1,), 10)
        self._step(category, "Second", (self.approver_2,), 20)
        request = self._prepare_request(category)
        self.assertEqual(
            [step["name"] for step in request.category_snapshot["steps"]],
            ["First", "Second"],
        )

    def test_a_pool_step_keeps_its_minimum(self):
        category = self._category(
            approvers=[(self.approver_1, False, 10), (self.approver_2, False, 20)],
            approval_minimum=2,
        )
        request = self._prepare_request(category)
        request.with_user(self.approver_1).action_approve()
        self.assertEqual(request.state, "pending")
        request.with_user(self.approver_2).action_approve()
        self.assertEqual(request.state, "approved")


@tagged("post_install", "-at_install")
class TestStepReadingTheRequest(ApprovalCommon):
    """A step whose source model is approval.request reads the request itself, so a
    request raised with no document can still have its approvers named for it."""

    def _category_with_request_step(self, **step_vals):
        category = self._make_category("Request subject")
        self.env["approval.category.step"].create(
            {
                "category_id": category.id,
                "name": "From the request",
                "minimum": 1,
                "subject_model_id": self.env["ir.model"]._get("approval.request").id,
                "subject_user_path": "partner_id.user_ids",
                **step_vals,
            }
        )
        return category

    def test_the_approver_path_reads_the_request(self):
        self.partner.user_ids = self.approver_1
        request = self._prepare_request(
            self._category_with_request_step(), partner_id=self.partner.id
        )
        self.assertEqual(request.approver_ids.user_id, self.approver_1)
        request.with_user(self.approver_1).action_approve()
        self.assertEqual(request.state, "approved")

    def test_the_condition_reads_the_request(self):
        self.partner.user_ids = self.approver_1
        category = self._category_with_request_step(
            subject_domain=f"[('partner_id', '=', {self.partner.id})]"
        )
        matching = self._prepare_request(category, partner_id=self.partner.id)
        self.assertEqual(matching._get_applicable_steps(), category.step_ids)
        other = self.env["res.partner"].create({"name": "Other partner"})
        request = self.env["approval.request"].create(
            {
                "category_id": category.id,
                "request_owner_id": self.owner_user.id,
                "partner_id": other.id,
            }
        )
        self.assertFalse(request._get_applicable_steps())
