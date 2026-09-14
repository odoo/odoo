from odoo.exceptions import UserError, ValidationError
from odoo.tests import common, tagged

from odoo.addons.approval.tests.common import add_category_approver, pool_step


@tagged("post_install", "-at_install")
class TestSequentialApproval(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.approver_1 = cls.env["res.users"].create(
            {
                "name": "First Approver",
                "login": "seq_approver_1",
                "email": "approver1@test.com",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.approver_2 = cls.env["res.users"].create(
            {
                "name": "Second Approver",
                "login": "seq_approver_2",
                "email": "approver2@test.com",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.approver_3 = cls.env["res.users"].create(
            {
                "name": "Third Approver",
                "login": "seq_approver_3",
                "email": "approver3@test.com",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.request_owner = cls.env["res.users"].create(
            {
                "name": "Request Owner",
                "login": "seq_owner",
                "email": "owner@test.com",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )

        cls.sequential_category = cls.env["approval.category"].create(
            {
                "sequence_code": "SC0057",
                "name": "Sequential Test Category",
                "approval_minimum": 2,
                "step_ids": pool_step([], minimum=2, in_order=True),
            }
        )

        add_category_approver(
            cls.sequential_category, cls.approver_1, required=True, sequence=10
        )
        add_category_approver(
            cls.sequential_category, cls.approver_2, required=True, sequence=20
        )
        add_category_approver(
            cls.sequential_category, cls.approver_3, required=False, sequence=30
        )

        cls.parallel_category = cls.env["approval.category"].create(
            {
                "sequence_code": "SC0058",
                "name": "Parallel Test Category",
                "approval_minimum": 2,
                "step_ids": pool_step([], minimum=2, in_order=False),
            }
        )
        add_category_approver(
            cls.parallel_category, cls.approver_1, required=True, sequence=10
        )
        add_category_approver(
            cls.parallel_category, cls.approver_2, required=True, sequence=20
        )

    def _create_sequential_request(self):
        return self.env["approval.request"].create(
            {
                "name": "Sequential Test Request",
                "request_owner_id": self.request_owner.id,
                "category_id": self.sequential_category.id,
            }
        )

    def _create_parallel_request(self):
        return self.env["approval.request"].create(
            {
                "name": "Parallel Test Request",
                "request_owner_id": self.request_owner.id,
                "category_id": self.parallel_category.id,
            }
        )

    def test_sequential_confirm_sets_first_approver_pending(self):
        request = self._create_sequential_request()
        self.assertEqual(request.state, "new")

        for approver in request.approver_ids:
            self.assertEqual(
                approver.state,
                "new",
                f"Approver {approver.user_id.name} should be new before confirm",
            )

        request.action_confirm()

        first_approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_1
        )
        self.assertEqual(
            first_approver.state,
            "pending",
            "First approver should be pending after confirm",
        )

    def test_sequential_confirm_sets_subsequent_approvers_waiting(self):
        request = self._create_sequential_request()
        request.action_confirm()

        second_approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_2
        )
        third_approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_3
        )

        self.assertEqual(
            second_approver.state,
            "waiting",
            "Second approver should be waiting after confirm",
        )
        self.assertEqual(
            third_approver.state,
            "waiting",
            "Third approver should be waiting after confirm",
        )

    def test_parallel_confirm_sets_all_approvers_pending(self):
        request = self._create_parallel_request()
        request.action_confirm()

        for approver in request.approver_ids:
            self.assertEqual(
                approver.state,
                "pending",
                f"Approver {approver.user_id.name} should be pending in parallel mode",
            )

    def test_sequential_approval_moves_next_to_pending(self):
        request = self._create_sequential_request()
        request.action_confirm()

        first = request.approver_ids.filtered(lambda a: a.user_id == self.approver_1)
        second = request.approver_ids.filtered(lambda a: a.user_id == self.approver_2)
        self.assertEqual(first.state, "pending")
        self.assertEqual(second.state, "waiting")

        request.with_user(self.approver_1).action_approve()

        second = request.approver_ids.filtered(lambda a: a.user_id == self.approver_2)
        self.assertEqual(
            second.state,
            "pending",
            "Second approver should be pending after first approves",
        )

    def test_sequential_approval_keeps_remaining_waiting(self):
        request = self._create_sequential_request()
        request.action_confirm()

        request.with_user(self.approver_1).action_approve()

        third = request.approver_ids.filtered(lambda a: a.user_id == self.approver_3)
        self.assertEqual(
            third.state,
            "waiting",
            "Third approver should remain waiting after first approves",
        )

    def test_sequential_full_approval_chain(self):
        request = self._create_sequential_request()
        request.action_confirm()

        self.assertEqual(request.state, "pending")

        request.with_user(self.approver_1).action_approve()
        self.assertEqual(request.state, "pending")

        first = request.approver_ids.filtered(lambda a: a.user_id == self.approver_1)
        second = request.approver_ids.filtered(lambda a: a.user_id == self.approver_2)
        third = request.approver_ids.filtered(lambda a: a.user_id == self.approver_3)
        self.assertEqual(first.state, "approved")
        self.assertEqual(second.state, "pending")
        self.assertEqual(third.state, "waiting")

        request.with_user(self.approver_2).action_approve()
        self.assertEqual(
            request.state,
            "approved",
            "Request should be approved after minimum approvals",
        )

    def test_sequential_blocks_second_approving_before_first(self):
        request = self._create_sequential_request()
        request.action_confirm()

        with self.assertRaises(UserError) as cm:
            request.with_user(self.approver_2).action_approve()

        self.assertIn(
            "decide in order",
            str(cm.exception).lower(),
            "Error should say the members decide in order",
        )

    def test_sequential_blocks_third_approving_when_waiting(self):
        request = self._create_sequential_request()
        request.action_confirm()

        request.with_user(self.approver_1).action_approve()

        with self.assertRaises(UserError) as cm:
            request.with_user(self.approver_3).action_approve()

        self.assertIn("decide in order", str(cm.exception).lower())

    def test_parallel_allows_any_order(self):
        request = self._create_parallel_request()
        request.action_confirm()

        request.with_user(self.approver_2).action_approve()
        second = request.approver_ids.filtered(lambda a: a.user_id == self.approver_2)
        self.assertEqual(
            second.state,
            "approved",
            "Second approver can approve first in parallel mode",
        )

    def test_sequential_respects_sequence_numbers(self):
        request = self._create_sequential_request()
        request.action_confirm()

        sorted_approvers = request.approver_ids.sorted("sequence")

        self.assertEqual(sorted_approvers[0].user_id, self.approver_1)
        self.assertEqual(sorted_approvers[1].user_id, self.approver_2)
        self.assertEqual(sorted_approvers[2].user_id, self.approver_3)

        self.assertEqual(sorted_approvers[0].state, "pending")
        self.assertEqual(sorted_approvers[1].state, "waiting")
        self.assertEqual(sorted_approvers[2].state, "waiting")

    def test_sequential_same_sequence_uses_id_as_tiebreaker(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0059",
                "name": "Same Sequence Category",
                "approval_minimum": 1,
                "step_ids": pool_step([], minimum=1, in_order=True),
            }
        )
        add_category_approver(category, self.approver_1, sequence=10)
        add_category_approver(category, self.approver_2, sequence=10)

        request = self.env["approval.request"].create(
            {
                "name": "Same Sequence Request",
                "request_owner_id": self.request_owner.id,
                "category_id": category.id,
            }
        )
        request.action_confirm()

        pending_count = len(
            request.approver_ids.filtered(lambda a: a.state == "pending")
        )
        waiting_count = len(
            request.approver_ids.filtered(lambda a: a.state == "waiting")
        )

        self.assertEqual(pending_count, 1, "Exactly one approver should be pending")
        self.assertEqual(waiting_count, 1, "Exactly one approver should be waiting")

    def test_sequential_refusal_sets_remaining_to_refused(self):
        request = self._create_sequential_request()
        request.action_confirm()

        request.with_user(self.approver_1).with_context(
            skip_wizard=True
        ).action_refuse()

        self.assertEqual(request.state, "refused")

        first = request.approver_ids.filtered(lambda a: a.user_id == self.approver_1)
        self.assertEqual(first.state, "refused")

    def test_sequential_refusal_mid_chain(self):
        request = self._create_sequential_request()
        request.action_confirm()

        request.with_user(self.approver_1).action_approve()

        request.with_user(self.approver_2).with_context(
            skip_wizard=True
        ).action_refuse()

        self.assertEqual(
            request.state,
            "refused",
            "Request should be refused after second refuses",
        )

    def test_sequential_withdrawal_resets_next_to_waiting(self):
        request = self._create_sequential_request()
        request.action_confirm()

        request.with_user(self.approver_1).action_approve()

        second = request.approver_ids.filtered(lambda a: a.user_id == self.approver_2)
        self.assertEqual(second.state, "pending")

        request.with_user(self.approver_1).action_withdraw()

        second = request.approver_ids.filtered(lambda a: a.user_id == self.approver_2)
        self.assertEqual(
            second.state,
            "waiting",
            "Second approver should be waiting after first withdraws",
        )

        first = request.approver_ids.filtered(lambda a: a.user_id == self.approver_1)
        self.assertEqual(first.state, "pending")

    def test_sequential_withdrawal_of_a_surplus_approval_parks_the_row(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0059",
                "name": "Sequential Surplus Category",
                "approval_minimum": 1,
                "step_ids": pool_step([], minimum=1, in_order=True),
            }
        )
        add_category_approver(category, self.approver_1, required=False, sequence=10)
        add_category_approver(category, self.approver_2, required=True, sequence=20)
        request = self.env["approval.request"].create(
            {
                "name": "Sequential Surplus Request",
                "request_owner_id": self.request_owner.id,
                "category_id": category.id,
            }
        )
        request.action_confirm()

        request.with_user(self.approver_1).action_approve()
        self.assertEqual(
            request.state,
            "pending",
            "The minimum is met but the required approver is only now "
            "reaching the front of the chain.",
        )
        request.with_user(self.approver_2).action_approve()
        self.assertEqual(request.state, "approved")

        request.with_user(self.approver_1).action_withdraw()

        first = request.approver_ids.filtered(lambda a: a.user_id == self.approver_1)
        second = request.approver_ids.filtered(lambda a: a.user_id == self.approver_2)
        self.assertEqual(
            request.state,
            "approved",
            "The required approval alone still satisfies the request.",
        )
        self.assertEqual(
            first.state,
            "waiting",
            "A 'pending' row on an approved request is a To-Do that "
            "raises when clicked.",
        )
        self.assertEqual(
            second.state,
            "approved",
            "A withdrawal upstream must not disturb a decision already "
            "taken downstream.",
        )
        activity_type = self.env.ref("approval.mail_activity_data_approval")
        self.assertFalse(
            request.activity_ids.filtered(
                lambda a: (
                    a.activity_type_id == activity_type and a.user_id == self.approver_1
                ),
            ),
        )

    def test_sequential_user_state_waiting(self):
        request = self._create_sequential_request()
        request.action_confirm()

        request_as_second = request.with_user(self.approver_2)
        self.assertEqual(
            request_as_second.user_approver_state,
            "waiting",
            "Second approver's user_approver_state should be 'waiting'",
        )

    def test_sequential_user_state_pending_when_active(self):
        request = self._create_sequential_request()
        request.action_confirm()

        request_as_first = request.with_user(self.approver_1)
        self.assertEqual(
            request_as_first.user_approver_state,
            "pending",
            "First approver's user_approver_state should be 'pending'",
        )

    def test_sequential_single_approver(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0060",
                "name": "Single Approver Sequential",
                "approval_minimum": 1,
                "step_ids": pool_step([], minimum=1, in_order=True),
            }
        )
        add_category_approver(category, self.approver_1, required=True)

        request = self.env["approval.request"].create(
            {
                "name": "Single Approver Request",
                "request_owner_id": self.request_owner.id,
                "category_id": category.id,
            }
        )
        request.action_confirm()

        approver = request.approver_ids[0]
        self.assertEqual(approver.state, "pending")

        request.with_user(self.approver_1).action_approve()
        self.assertEqual(request.state, "approved")

    def test_sequential_constraint_minimum_without_sequence(self):
        with self.assertRaises(ValidationError) as cm:
            self.env["approval.category"].create(
                {
                    "sequence_code": "SC0061",
                    "name": "Invalid Sequential",
                    "approval_minimum": 0,
                    "step_ids": pool_step([], minimum=0, in_order=True),
                }
            )

        self.assertIn(
            "at least one",
            str(cm.exception).lower(),
        )
