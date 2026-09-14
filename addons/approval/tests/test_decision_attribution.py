from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import ApprovalCommon, add_rule_step, isolate_group_approval_manager


@tagged("post_install", "-at_install")
class TestDecisionFunnelScoping(ApprovalCommon):
    def test_explicit_approver_from_another_request_is_rejected(self):
        category = self._make_category(
            "Funnel Scoping",
            approvers=[(self.approver_1, True, 10)],
        )
        request_a = self._prepare_request(category)
        request_b = self._prepare_request(category)
        self.assertEqual(request_a.state, "pending")
        self.assertEqual(request_b.state, "pending")

        foreign_row = request_b.approver_ids[0]
        with self.assertRaises(UserError):
            request_a.with_user(self.approver_1).action_approve(
                foreign_row.with_user(self.approver_1),
            )

        self.assertEqual(
            request_b.state,
            "pending",
            "a decision aimed at request A must never move request B",
        )
        self.assertEqual(request_a.state, "pending")

    def test_own_approver_row_still_decides_normally(self):
        category = self._make_category(
            "Funnel Scoping OK",
            approvers=[(self.approver_1, True, 10)],
        )
        request = self._prepare_request(category)
        row = request.approver_ids[0]
        request.with_user(self.approver_1).action_approve(
            row.with_user(self.approver_1),
        )
        self.assertEqual(request.state, "approved")


@tagged("post_install", "-at_install")
class TestDecisionAttribution(ApprovalCommon):
    def test_decided_by_records_the_delegate_not_the_principal(self):
        category = self._make_category(
            "Attribution",
            approvers=[(self.approver_1, True, 10)],
        )
        request = self._prepare_request(category)
        row = request.approver_ids[0]
        self._delegate_row(row, self.approver_2)
        self.assertEqual(row._get_effective_approver(), self.approver_2)

        request.with_user(self.approver_2).action_approve()

        self.assertEqual(row.state, "approved")
        self.assertEqual(
            row.user_id,
            self.approver_1,
            "user_id keeps recording WHOSE slot it is",
        )
        self.assertEqual(
            row.decided_by_user_id,
            self.approver_2,
            "decided_by_user_id records WHO exercised it",
        )

    def test_undelegated_decision_records_the_approver_themselves(self):
        category = self._make_category(
            "Attribution Plain",
            approvers=[(self.approver_1, True, 10)],
        )
        request = self._prepare_request(category)
        request.with_user(self.approver_1).action_approve()
        row = request.approver_ids[0]
        self.assertEqual(row.decided_by_user_id, self.approver_1)

    def test_withdraw_clears_the_attribution(self):
        category = self._make_category(
            "Attribution Withdraw",
            approvers=[(self.approver_1, True, 10)],
        )
        request = self._prepare_request(category)
        request.with_user(self.approver_1).action_approve()
        row = request.approver_ids[0]
        self.assertEqual(row.decided_by_user_id, self.approver_1)

        request.with_user(self.approver_1).action_withdraw()
        self.assertFalse(
            row.decided_by_user_id,
            "a withdrawal un-makes the decision, so its attribution goes too",
        )
        self.assertFalse(row.decision_date)

    def test_reset_to_draft_clears_the_attribution(self):
        category = self._make_category(
            "Attribution Reset",
            approvers=[(self.approver_1, True, 10)],
        )
        request = self._prepare_request(category)
        request.with_user(self.approver_1).action_approve()
        request.with_user(self.manager_user).action_reset_to_draft()
        self.assertFalse(request.approver_ids.mapped("decided_by_user_id"))


@tagged("post_install", "-at_install")
class TestPendingChangeCloseOut(ApprovalCommon):
    def _open_change_request(self, request, approver_user):
        self.env["approval.decision.wizard"].with_user(approver_user).create(
            {
                "approver_id": request.approver_ids[0].id,
                "decision_type": "change",
                "change_field": "reason",
                "note": "please clarify",
            },
        ).action_confirm_change()
        request.invalidate_recordset()
        self.assertEqual(request.pending_change_field, "reason")
        self.assertEqual(len(request._get_change_request_activities()), 1)

    def test_auto_expire_closes_the_change_request(self):
        category = self._make_category(
            "Expire Close-out",
            approvers=[(self.approver_1, True, 10)],
            auto_expire_hours=1,
        )
        request = self._prepare_request(category)
        self._open_change_request(request, self.approver_1)

        self.env.cr.execute(
            "UPDATE approval_request SET date_confirmed = now() - interval "
            "'5 hours' WHERE id = %s",
            [request.id],
        )
        request.invalidate_recordset(["date_confirmed"])
        self.env["approval.request"].cron_auto_expire()
        request.invalidate_recordset()

        self.assertEqual(request.state, "cancelled")
        self.assertFalse(request.pending_change_field)
        self.assertFalse(
            request._get_change_request_activities(),
            "the change-request To-Do must not outlive the request",
        )

    def test_parent_cascade_closes_the_change_request(self):
        category = self._make_category(
            "Cascade Close-out",
            approvers=[(self.approver_1, True, 10)],
        )
        request = self._prepare_request(category)
        self._open_change_request(request, self.approver_1)

        request._refuse_cascade()
        request.invalidate_recordset()

        self.assertEqual(request.state, "refused")
        self.assertFalse(request.pending_change_field)
        self.assertFalse(request._get_change_request_activities())

    def test_reset_to_draft_closes_the_change_request(self):
        category = self._make_category(
            "Reset Close-out",
            approvers=[(self.approver_1, True, 10)],
        )
        request = self._prepare_request(category)
        self._open_change_request(request, self.approver_1)
        request.with_user(self.owner_user).action_cancel()
        request.with_user(self.manager_user).action_reset_to_draft()
        request.invalidate_recordset()

        self.assertEqual(request.state, "new")
        self.assertFalse(request.pending_change_field)
        self.assertFalse(request._get_change_request_activities())

    def test_owner_cancel_still_closes_the_change_request(self):
        category = self._make_category(
            "Cancel Close-out",
            approvers=[(self.approver_1, True, 10)],
        )
        request = self._prepare_request(category)
        self._open_change_request(request, self.approver_1)
        request.with_user(self.owner_user).action_cancel()
        request.invalidate_recordset()

        self.assertEqual(request.state, "cancelled")
        self.assertFalse(request.pending_change_field)
        self.assertFalse(request._get_change_request_activities())


@tagged("post_install", "-at_install")
class TestEscalationManagerLookup(ApprovalCommon):
    def test_implied_group_membership_is_found(self):
        manager_group = self.env.ref("approval.group_approval_manager")
        super_group = self.env["res.groups"].create(
            {
                "name": "Audit3 Super Role",
                "implied_ids": [(4, manager_group.id)],
            },
        )
        implied_manager = self.env["res.users"].create(
            {
                "name": "Audit3 Implied Manager",
                "login": "audit3_implied_manager",
                "group_ids": [(4, super_group.id)],
            },
        )
        self.assertTrue(
            implied_manager.has_group("approval.group_approval_manager"),
            "precondition: the privilege check sees the implied grant",
        )
        self.assertNotIn(
            manager_group,
            implied_manager.group_ids,
            "precondition: the grant is NOT direct",
        )

        isolate_group_approval_manager(self.env)
        self.assertFalse(
            self.env["res.users"].search(
                [
                    ("group_ids", "in", manager_group.id),
                    ("company_ids", "in", self.env.company.id),
                    ("active", "=", True),
                ],
            ),
            "precondition: nobody holds the group DIRECTLY any more",
        )

        category = self._make_category(
            "Escalation Lookup",
            approvers=[(self.approver_1, True, 10)],
        )
        request = self._prepare_request(category)
        self.env["approval.request"]._invalidate_escalation_manager_cache()

        self.assertEqual(
            request._get_default_escalation_manager(),
            implied_manager,
            "the fallback must find a manager granted the group by implication",
        )


@tagged("post_install", "-at_install")
class TestManualApproverPreservation(ApprovalCommon):
    def test_manual_approver_in_a_step_that_does_not_apply_survives(self):
        category = self._make_category(
            "Manual Preservation",
            approvers=[(self.approver_1, True, 10)],
        )
        add_rule_step(
            category,
            self.approver_2,
            name="Audit3 High Tier",
            condition_field="amount",
            operator="between",
            threshold=100000,
            threshold_max=0,
        )
        request = self._prepare_request(category, confirm=False, amount=10)
        self.env["approval.approver"].create(
            {
                "request_id": request.id,
                "user_id": self.approver_2.id,
                "sequence": 1000,
                "required": False,
            },
        )
        request.invalidate_recordset(["approver_ids"])
        self.assertIn(self.approver_2, request.approver_ids.user_id)

        request.write({"amount": 20})
        request.invalidate_recordset(["approver_ids"])

        self.assertIn(
            self.approver_2,
            request.approver_ids.user_id,
            "a manual approver must not be deleted because some "
            "non-matching tier happens to list them",
        )

    def test_a_row_whose_step_stopped_applying_is_removed(self):
        category = self._make_category(
            "Orphan Removal",
            approvers=[(self.approver_1, True, 10)],
        )
        add_rule_step(
            category,
            self.approver_2,
            name="Audit3 Matching Tier",
            condition_field="amount",
            operator="between",
            threshold=0,
            threshold_max=1000,
        )
        request = self._prepare_request(category, confirm=False, amount=100)
        request.invalidate_recordset(["approver_ids"])
        self.assertIn(
            self.approver_2,
            request.approver_ids.user_id,
            "precondition: the tier matched and injected its approver",
        )

        request.write({"amount": 5000})
        request.invalidate_recordset(["approver_ids"])
        self.assertNotIn(
            self.approver_2,
            request.approver_ids.user_id,
            "the injection's source stopped producing it — it must be removed",
        )


@tagged("post_install", "-at_install")
class TestConfirmActivityBatching(ApprovalCommon):
    def test_batch_confirm_creates_one_activity_per_approver(self):
        category = self._make_category(
            "Batch Confirm",
            approvers=[
                (self.approver_1, False, 10),
                (self.approver_2, False, 20),
            ],
            approval_minimum=1,
        )
        requests = self.env["approval.request"].create(
            [
                {
                    "category_id": category.id,
                    "request_owner_id": self.owner_user.id,
                }
                for _ in range(5)
            ],
        )
        requests.action_confirm()
        self.env.flush_all()

        activities = self.env["mail.activity"].search(
            [
                ("res_model", "=", "approval.request"),
                ("res_id", "in", requests.ids),
                (
                    "activity_type_id",
                    "=",
                    self.env.ref("approval.mail_activity_data_approval").id,
                ),
            ],
        )
        self.assertEqual(
            len(activities),
            10,
            "5 requests x 2 approvers, one To-Do each — no duplicates, none lost",
        )
        self.assertEqual(set(requests.mapped("state")), {"pending"})

    def test_batch_confirm_opens_each_sequential_round_independently(self):
        category = self._make_category(
            "Batch Sequential",
            approvers=[
                (self.approver_1, False, 10),
                (self.approver_2, False, 20),
            ],
            approval_minimum=1,
            in_order=True,
        )
        requests = self.env["approval.request"].create(
            [
                {
                    "category_id": category.id,
                    "request_owner_id": self.owner_user.id,
                }
                for _ in range(4)
            ],
        )
        requests.action_confirm()
        self.env.flush_all()

        for request in requests:
            states = [
                row.state
                for row in request.approver_ids.sorted(lambda a: (a.sequence, a.id))
            ]
            self.assertEqual(
                states,
                ["pending", "waiting"],
                "every request opens on its OWN first approver",
            )
            self.assertEqual(
                len(request.activity_ids),
                1,
                "and only the opened row gets a To-Do",
            )

    def test_batch_confirm_mixes_sequential_and_parallel_correctly(self):
        sequential = self._make_category(
            "Batch Mixed Seq",
            approvers=[
                (self.approver_1, False, 10),
                (self.approver_2, False, 20),
            ],
            approval_minimum=1,
            in_order=True,
        )
        parallel = self._make_category(
            "Batch Mixed Par",
            approvers=[
                (self.approver_1, False, 10),
                (self.approver_2, False, 20),
            ],
            approval_minimum=1,
        )
        seq_request = self._prepare_request(sequential, confirm=False)
        par_request = self._prepare_request(parallel, confirm=False)
        (seq_request | par_request).action_confirm()
        self.env.flush_all()

        self.assertEqual(
            sorted(seq_request.approver_ids.mapped("state")),
            ["pending", "waiting"],
        )
        self.assertEqual(
            sorted(par_request.approver_ids.mapped("state")),
            ["pending", "pending"],
        )

    def test_repeat_create_activity_is_idempotent(self):
        category = self._make_category(
            "Batch Idempotent",
            approvers=[(self.approver_1, True, 10)],
        )
        request = self._prepare_request(category)
        before = len(request.activity_ids)
        request.approver_ids._create_activity()
        request.invalidate_recordset()
        self.assertEqual(len(request.activity_ids), before)

    def test_fan_in_within_one_batch_creates_a_single_activity(self):
        third = self.env["res.users"].create(
            {"name": "Audit3 Third", "login": "audit3_third"},
        )
        category = self._make_category(
            "Batch Fan-in",
            approvers=[
                (self.approver_1, False, 10),
                (self.approver_2, False, 20),
            ],
            approval_minimum=1,
        )
        request = self._prepare_request(category, confirm=False)
        today = fields.Date.today()
        for row in request.approver_ids:
            row.sudo().write(
                {
                    "delegate_id": third.id,
                    "delegate_start_date": today - timedelta(days=1),
                    "delegate_end_date": today + timedelta(days=1),
                },
            )
        request.action_confirm()
        self.env.flush_all()

        third_activities = request.activity_ids.filtered(
            lambda a: (
                a.user_id == third
                and a.activity_type_id
                == self.env.ref("approval.mail_activity_data_approval")
            ),
        )
        self.assertEqual(
            len(third_activities),
            1,
            "one effective user on one request gets one To-Do",
        )
