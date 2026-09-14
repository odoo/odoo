import re
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .common import ApprovalCommon, isolate_group_approval_manager, record_approval


@tagged("post_install", "-at_install")
class TestCancelFlow(ApprovalCommon):
    def _category(self, **vals):
        return self._make_category(
            name=f"Cancel Cat {self.id()}",
            approvers=[self.approver_1, self.approver_2],
            **vals,
        )

    def test_owner_cancels_pending_request(self):
        category = self._category()
        request = self._prepare_request(category)
        self.assertEqual(request.state, "pending")

        request.with_user(self.owner_user).action_cancel()

        self.assertEqual(request.state, "cancelled")
        self.assertTrue(request.date_cancelled)
        self.assertFalse(request.date_refused)
        self.assertFalse(request.refusal_reason_id)
        self.assertTrue(
            all(a.state == "cancelled" for a in request.approver_ids),
        )
        activity_type = self.env.ref("approval.mail_activity_data_approval")
        self.assertFalse(
            request.activity_ids.filtered(
                lambda a: a.activity_type_id == activity_type,
            ),
        )

    def test_cancel_preserves_approved_rows(self):
        category = self._category(approval_minimum=2)
        request = self._prepare_request(category)
        request.with_user(self.approver_1).action_approve()
        self.assertEqual(request.state, "pending")

        request.with_user(self.owner_user).action_cancel()

        states = {a.user_id.id: a.state for a in request.approver_ids}
        self.assertEqual(states[self.approver_1.id], "approved")
        self.assertEqual(states[self.approver_2.id], "cancelled")
        self.assertEqual(request.state, "cancelled")

    def test_cancel_guards(self):
        category = self._category()
        draft = self._prepare_request(category, confirm=False)
        with self.assertRaises(UserError):
            draft.with_user(self.owner_user).action_cancel()

        request = self._prepare_request(category)
        with self.assertRaises(AccessError):
            request.with_user(self.approver_1).action_cancel()
        request.with_user(self.manager_user).action_cancel()
        self.assertEqual(request.state, "cancelled")
        with self.assertRaises(UserError):
            request.with_user(self.owner_user).action_cancel()

    def test_cancel_clears_pending_change(self):
        category = self._category()
        request = self._prepare_request(category)
        approver_row = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_1,
        )
        request.with_user(self.approver_1).with_context(
            skip_wizard=True,
            requested_change_field="reason",
        ).action_request_change(approver=approver_row)
        self.assertEqual(request.pending_change_field, "reason")

        request.with_user(self.owner_user).action_cancel()
        self.assertFalse(request.pending_change_field)
        self.assertEqual(request.state, "cancelled")


@tagged("post_install", "-at_install")
class TestResetToDraft(ApprovalCommon):
    def _refused_request(self):
        category = self._make_category(
            name=f"Reset Cat {self.id()}",
            approvers=[self.approver_1],
        )
        request = self._prepare_request(category)
        request.with_user(self.approver_1).with_context(
            skip_wizard=True,
        ).action_refuse()
        self.assertEqual(request.state, "refused")
        return category, request

    def test_reset_reopens_and_renumbers_nothing(self):
        _category, request = self._refused_request()
        number = request.name
        self.assertTrue(number)

        request.with_user(self.owner_user).action_reset_to_draft()

        self.assertEqual(request.state, "new")
        self.assertEqual(request.name, number)
        self.assertFalse(request.date_confirmed)
        self.assertFalse(request.date_refused)
        self.assertFalse(request.refusal_reason_id)
        self.assertTrue(all(a.state == "new" for a in request.approver_ids))

        request.action_confirm()
        self.assertEqual(request.state, "pending")
        self.assertEqual(request.name, number)
        self.assertTrue(request.date_confirmed)

    def test_reset_resyncs_current_category_config(self):
        category, request = self._refused_request()
        category._add_approver(self.approver_2, sequence=20)

        request.with_user(self.manager_user).action_reset_to_draft()

        self.assertIn(self.approver_2, request.approver_ids.user_id)

    def test_reset_guards(self):
        category = self._make_category(
            name=f"Reset Guard Cat {self.id()}",
            approvers=[self.approver_1],
        )
        pending = self._prepare_request(category)
        with self.assertRaises(UserError):
            pending.with_user(self.owner_user).action_reset_to_draft()

        pending.with_user(self.owner_user).action_cancel()
        with self.assertRaises(AccessError):
            pending.with_user(self.approver_1).action_reset_to_draft()
        pending.with_user(self.owner_user).action_reset_to_draft()
        self.assertEqual(pending.state, "new")


@tagged("post_install", "-at_install")
class TestAutoTerminalPaths(ApprovalCommon):
    def test_auto_expire_cancels_and_preserves_decisions(self):
        category = self._make_category(
            name=f"Expire Cat {self.id()}",
            approvers=[self.approver_1, self.approver_2],
            approval_minimum=2,
            auto_expire_hours=48,
        )
        request = self._prepare_request(category)
        request.with_user(self.approver_1).action_approve()
        request.date_confirmed = fields.Datetime.now() - timedelta(hours=72)

        self.env["approval.request"].cron_auto_expire()

        self.assertEqual(request.state, "cancelled")
        states = {a.user_id.id: a.state for a in request.approver_ids}
        self.assertEqual(states[self.approver_1.id], "approved")
        self.assertEqual(states[self.approver_2.id], "cancelled")

    def test_auto_refuse_rule_records_reason(self):
        category = self._make_category(
            name=f"Rule Cat {self.id()}",
            approvers=[self.approver_1],
        )
        self.env["approval.rule"].create(
            {
                "name": "Refuse big amounts",
                "category_id": category.id,
                "condition_field": "amount",
                "operator": "gt",
                "threshold": 1000,
                "action_type": "auto_refuse",
            },
        )
        request = self._prepare_request(category, amount=5000)

        self.assertEqual(request.state, "refused")
        self.assertEqual(
            request.refusal_reason_id,
            self.env.ref("approval.refusal_reason_auto_rule"),
        )


@tagged("post_install", "-at_install")
class TestPendingIntegrity(ApprovalCommon):
    def test_locked_fields_are_server_side(self):
        category = self._make_category(
            name=f"Lock Cat {self.id()}",
            approvers=[self.approver_1],
        )
        request = self._prepare_request(category, amount=100)
        with self.assertRaises(ValidationError):
            request.write({"amount": 1_000_000})
        with self.assertRaises(ValidationError):
            request.sudo().write({"amount": 1_000_000})
        self.assertEqual(request.amount, 100)

    def test_pending_change_reopens_only_flagged_field(self):
        category = self._make_category(
            name=f"Change Cat {self.id()}",
            approvers=[self.approver_1],
        )
        request = self._prepare_request(
            category, amount=100, date=fields.Datetime.now()
        )
        approver_row = request.approver_ids
        request.with_user(self.approver_1).with_context(
            skip_wizard=True,
            requested_change_field="date",
        ).action_request_change(approver=approver_row)

        request.write({"date": fields.Datetime.now()})
        with self.assertRaises(ValidationError):
            request.write({"amount": 500})

    def test_consent_cron_respects_pending_change(self):
        category = self._make_category(
            name=f"Consent Cat {self.id()}",
            approvers=[self.approver_1],
            consent_approval_hours=4,
        )
        request = self._prepare_request(category)
        approver_row = request.approver_ids
        request.with_user(self.approver_1).with_context(
            skip_wizard=True,
            requested_change_field="reason",
        ).action_request_change(approver=approver_row)
        request.date_confirmed = fields.Datetime.now() - timedelta(hours=10)

        self.env["approval.request"].cron_consent_approval()

        self.assertEqual(request.state, "pending")

        request.with_user(self.owner_user).action_resubmit()
        self.env["approval.request"].cron_consent_approval()
        self.assertEqual(request.state, "approved")

    def test_sync_is_draft_only(self):
        category = self._make_category(
            name=f"Sync Cat {self.id()}",
            approvers=[self.approver_1],
        )
        request = self._prepare_request(category)
        self.assertEqual(request.state, "pending")

        category._add_approver(self.approver_2, sequence=20)
        request._sync_approvers()

        self.assertEqual(request.state, "pending")
        self.assertEqual(request.approver_ids.user_id, self.approver_1)

        request.with_user(self.approver_1).with_context(
            skip_wizard=True,
        ).action_refuse()
        request.with_user(self.owner_user).action_reset_to_draft()
        self.assertIn(self.approver_2, request.approver_ids.user_id)


@tagged("post_install", "-at_install")
class TestDelegationPaths(ApprovalCommon):
    def _delegate(self, approver_row, to_user):
        today = fields.Date.today()
        approver_row.with_user(approver_row.user_id).write(
            {
                "delegate_id": to_user.id,
                "delegate_start_date": today,
                "delegate_end_date": today + timedelta(days=7),
            },
        )

    def test_bulk_approve_resolves_delegation(self):
        category = self._make_category(
            name=f"Bulk Deleg Cat {self.id()}",
            approvers=[self.approver_1],
        )
        request = self._prepare_request(category)
        self._delegate(request.approver_ids, self.approver_2)

        request.with_user(self.approver_2).action_approve_bulk()
        self.assertEqual(request.state, "approved")

    def test_review_inbox_includes_delegations(self):
        category = self._make_category(
            name=f"Inbox Deleg Cat {self.id()}",
            approvers=[self.approver_1],
        )
        request = self._prepare_request(category)
        self._delegate(request.approver_ids, self.approver_2)

        action = (
            self.env["approval.request"]
            .with_user(self.approver_2)
            .action_view_to_review()
        )
        found = self.env["approval.request"].search(action["domain"])
        self.assertIn(request, found)

    def test_sequential_multi_row_anchor_no_crash(self):
        category = self._make_category(
            name=f"Anchor Cat {self.id()}",
            approvers=[
                (self.approver_1, True, 10),
                (self.approver_2, True, 20),
                (self.manager_user, False, 30),
            ],
            in_order=True,
        )
        request = self._prepare_request(category)
        rows = request.approver_ids.sorted("sequence")
        self.assertEqual(rows.mapped("state"), ["pending", "waiting", "waiting"])
        record_approval(rows[0])

        request.sudo()._refresh_turn_states()
        self.assertEqual(rows[1:].mapped("state"), ["pending", "waiting"])


@tagged("post_install", "-at_install")
class TestSlaAndConfig(ApprovalCommon):
    def test_sla_status_search_matches_compute(self):
        category = self._make_category(
            name=f"SLA Cat {self.id()}",
            approvers=[self.approver_1],
            sla_target_hours=24,
        )
        fresh = self._prepare_request(category)
        breached = self._prepare_request(category)
        breached.date_confirmed = fields.Datetime.now() - timedelta(hours=30)

        self.assertEqual(fresh.sla_status, "on_track")
        self.assertEqual(breached.sla_status, "breached")

        found = self.env["approval.request"].search(
            [("sla_status", "in", ["at_risk", "breached"])],
        )
        self.assertIn(breached, found)
        self.assertNotIn(fresh, found)

    def test_escalation_rules_config_override(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "approval.escalation.3.first_reminder",
            "1",
        )
        rules = self.env["approval.request"]._get_escalation_rules()
        self.assertEqual(rules["3"]["first_reminder"], 1)
        self.assertEqual(rules["3"]["escalation"], 8)


@tagged("post_install", "-at_install")
class TestActionLocking(ApprovalCommon):
    def _assert_locks(self, request, action_callable):
        with patch.object(
            type(request),
            "_lock_for_approval_action",
            autospec=True,
        ) as mock_lock:
            action_callable()
        self.assertTrue(
            mock_lock.called,
            f"{action_callable} must call _lock_for_approval_action() "
            "before mutating state, like _apply_decision() does.",
        )

    def test_action_confirm_locks(self):
        category = self._make_category(approvers=[self.approver_1])
        request = self._prepare_request(category, confirm=False)
        self._assert_locks(request, request.action_confirm)

    def test_action_cancel_locks(self):
        category = self._make_category(approvers=[self.approver_1])
        request = self._prepare_request(category)
        self._assert_locks(request, request.action_cancel)

    def test_action_reset_to_draft_locks(self):
        category = self._make_category(approvers=[self.approver_1])
        request = self._prepare_request(category)
        request.approver_ids[0].with_context(skip_wizard=True).action_refuse()
        self.assertEqual(request.state, "refused")
        self._assert_locks(request, request.action_reset_to_draft)

    def test_action_request_change_inline_locks(self):
        category = self._make_category(approvers=[self.approver_1])
        request = self._prepare_request(category)
        approver = request.approver_ids[0]

        def action():
            request.with_context(
                skip_wizard=True,
                requested_change_field="reason",
            ).action_request_change(approver=approver)

        self._assert_locks(request, action)

    def test_action_approve_raises_on_already_approved_passed_in(self):
        category = self._make_category(approvers=[self.approver_1])
        request = self._prepare_request(category)
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_1,
        )
        self.assertTrue(approver)

        record_approval(approver)

        with self.assertRaises(UserError):
            request.sudo().action_approve(approver)


@tagged("post_install", "-at_install")
class TestActionWithdrawMultiRecord(ApprovalCommon):
    def test_c5_action_withdraw_multi_record_no_closure_leak(self):
        category = self._make_category(approvers=[self.approver_1])
        req1 = self._prepare_request(category)
        req2 = self._prepare_request(category)

        ap1 = req1.approver_ids.filtered(lambda a: a.user_id == self.approver_1)
        ap2 = req2.approver_ids.filtered(lambda a: a.user_id == self.approver_1)

        record_approval(ap1)
        record_approval(ap2)

        combined = req1 + req2
        combined.with_user(self.approver_1).action_withdraw()

        self.assertEqual(
            ap1.state,
            "pending",
            "req1's approver_1 was not rolled back to pending after withdraw.",
        )
        self.assertEqual(
            ap2.state,
            "pending",
            "req2's approver_1 was not rolled back to pending — the "
            "closure-default leak applied req1's approver state to "
            "req2.",
        )


@tagged("post_install", "-at_install")
class TestApproverRowIntegrity(ApprovalCommon):
    def _refused_two_approver_request(self):
        category = self._make_category(
            name=f"Row Integrity Cat {self.id()}",
            approvers=[(self.approver_1, False, 10), (self.approver_2, False, 20)],
            approval_minimum=2,
        )
        request = self._prepare_request(category)
        request.with_user(self.approver_1).action_approve()
        request.with_user(self.approver_2).with_context(
            skip_wizard=True,
        ).action_refuse()
        self.assertEqual(request.state, "refused")
        return request

    def test_delete_refusing_row_blocked(self):
        request = self._refused_two_approver_request()
        refusing_row = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_2,
        )
        with self.assertRaises(ValidationError):
            refusing_row.with_user(self.manager_user).unlink()
        self.assertEqual(request.state, "refused")

    def test_delete_all_rows_blocked(self):
        request = self._refused_two_approver_request()
        with self.assertRaises(ValidationError):
            request.approver_ids.with_user(self.manager_user).unlink()
        self.assertEqual(request.state, "refused")
        request.with_user(self.manager_user).action_reset_to_draft()
        self.assertEqual(request.state, "new")
        self.assertFalse(request.date_confirmed)
        self.assertFalse(request.category_snapshot)

    def test_add_row_outside_draft_blocked(self):
        request = self._refused_two_approver_request()
        for state_setup in ("refused", "pending"):
            if state_setup == "pending":
                request.with_user(self.manager_user).action_reset_to_draft()
                request.action_confirm()
            with self.assertRaises(ValidationError):
                self.env["approval.approver"].with_user(self.manager_user).create(
                    {
                        "request_id": request.id,
                        "user_id": self.manager_user.id,
                    },
                )

    def test_sync_still_reconciles_after_reset(self):
        request = self._refused_two_approver_request()
        category = request.category_id
        category.step_ids.member_ids.filtered(
            lambda member: member.user_id == self.approver_2,
        ).unlink()
        category.step_ids.minimum = 1
        request.with_user(self.manager_user).action_reset_to_draft()
        self.assertEqual(request.approver_ids.user_id, self.approver_1)


@tagged("post_install", "-at_install")
class TestSyncProvenance(ApprovalCommon):
    def test_removed_category_approver_leaves_drafts(self):
        category = self._make_category(
            name=f"Provenance Cat {self.id()}",
            approvers=[(self.approver_1, True, 10), (self.approver_2, False, 20)],
        )
        request = self._prepare_request(category, confirm=False, amount=100)
        self.assertEqual(
            request.approver_ids.user_id,
            self.approver_1 | self.approver_2,
        )
        self.assertTrue(all(request.approver_ids.mapped("source_synced")))

        category.step_ids.member_ids.filtered(
            lambda member: member.user_id == self.approver_1,
        ).unlink()
        request.write({"amount": 200})

        self.assertEqual(
            request.approver_ids.user_id,
            self.approver_2,
            "A category approver removed from the category must be "
            "removed from open drafts, not preserved as a phantom "
            "optional approver.",
        )


@tagged("post_install", "-at_install")
class TestDepartureHandover(ApprovalCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.successor = cls.env["res.users"].create(
            {
                "name": "Escalation Successor",
                "login": "departure_successor",
                "email": "successor.departure@test.com",
                "group_ids": [
                    (4, cls.env.ref("approval.group_approval_approver").id),
                ],
            },
        )

    def _pending_request(self, with_contact=True, extra_approver=None):
        approvers = [(self.approver_1, False, 10)]
        if extra_approver is not None:
            approvers.append((extra_approver, False, 20))
        vals = {"approval_minimum": len(approvers)}
        if with_contact:
            vals.update(
                {
                    "escalate_overdue": True,
                    "escalation_user_id": self.successor.id,
                },
            )
        category = self._make_category(
            name=f"Departure Cat {self.id()}",
            approvers=approvers,
            **vals,
        )
        request = self._prepare_request(category)
        self.assertEqual(request.state, "pending")
        return request

    def test_archive_reassigns_row_to_successor(self):
        request = self._pending_request()
        self.approver_1.action_archive()

        row = request.approver_ids
        self.assertEqual(row.user_id, self.successor)
        self.assertEqual(row.state, "pending")
        self.assertEqual(request.state, "pending")
        activity_type = self.env.ref("approval.mail_activity_data_approval")
        todo_users = request.activity_ids.filtered(
            lambda a: a.activity_type_id == activity_type,
        ).user_id
        self.assertIn(self.successor, todo_users)
        self.assertNotIn(self.approver_1, todo_users)

    def test_archive_without_contact_reassigns_to_generic_manager(self):
        isolate_group_approval_manager(self.env, self.manager_user)
        request = self._pending_request(with_contact=False)
        self.approver_1.action_archive()

        row = request.approver_ids
        self.assertEqual(row.user_id, self.manager_user)
        self.assertEqual(row.state, "pending")

    def test_archive_without_successor_creates_admin_todo(self):
        isolate_group_approval_manager(self.env, self.env["res.users"])
        request = self._pending_request(with_contact=False)
        self.approver_1.action_archive()

        row = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_1,
        )
        self.assertTrue(row, "row must not be reassigned — no successor exists")
        todos = request.activity_ids.filtered(
            lambda a: (
                a.activity_type_id == self.env.ref("mail.mail_activity_data_todo")
            ),
        )
        self.assertTrue(todos, "the archiving admin must get a To-Do")
        self.assertEqual(todos.user_id, self.env.user)

    def test_archive_successor_already_coapprover_falls_back(self):
        request = self._pending_request(extra_approver=self.successor)
        self.approver_1.action_archive()

        row = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_1,
        )
        self.assertTrue(row, "row not reassigned onto a co-approver")
        todos = request.activity_ids.filtered(
            lambda a: (
                a.activity_type_id == self.env.ref("mail.mail_activity_data_todo")
            ),
        )
        self.assertTrue(todos)

    def test_archive_skips_actively_delegated_rows(self):
        request = self._pending_request()
        row = request.approver_ids
        today = fields.Date.today()
        row.with_user(self.approver_1).write(
            {
                "delegate_id": self.approver_2.id,
                "delegate_start_date": today - timedelta(days=1),
                "delegate_end_date": today + timedelta(days=1),
            },
        )
        self.approver_1.action_archive()

        self.assertEqual(
            row.user_id,
            self.approver_1,
            "an actively delegated row is already covered — left alone",
        )

    def test_cron_escalates_stalled_approver_immediately(self):
        request = self._pending_request(with_contact=True)
        request.priority = "3"
        request.sudo().date_confirmed = fields.Datetime.now() - timedelta(
            hours=5,
        )
        self.env.cr.execute(
            "UPDATE res_users SET active = FALSE WHERE id = %s",
            [self.approver_1.id],
        )
        self.approver_1.invalidate_recordset(["active"])

        self.env["approval.request"].cron_smart_escalation()

        request.invalidate_recordset()
        self.assertTrue(
            request.escalated_to_manager,
            "a stalled request must escalate at reminder time, not wait "
            "for the escalation threshold",
        )
        escalations = request.message_ids.filtered(
            lambda m: self.successor.partner_id in m.partner_ids,
        )
        self.assertTrue(
            escalations,
            "the escalation notice must reach the category contact",
        )


@tagged("post_install", "-at_install")
class TestCycleLogging(ApprovalCommon):
    _LOGGER = "odoo.addons.approval.models.approval_request_lifecycle"

    def _cycle_lines(self, run):
        with self.assertLogs(self._LOGGER, level="DEBUG") as captured:
            run()
            self.env.flush_all()
        return [
            line.split("approval-cycle", 1)[1].strip()
            for line in captured.output
            if "approval-cycle" in line
        ]

    def test_every_transition_leaves_one_line(self):
        category = self._make_category(
            name="Cycle Log Cat",
            approval_minimum=1,
            approvers=[(self.approver_1, True, 10)],
        )
        request = self._prepare_request(category, confirm=False)

        confirm = self._cycle_lines(request.action_confirm)
        self.assertEqual(len(confirm), 1, confirm)
        self.assertTrue(confirm[0].startswith("confirm "), confirm[0])
        self.assertIn("state=pending", confirm[0])
        self.assertIn(f"rows=[{self.approver_1.login}=pending]", confirm[0])

        decide = self._cycle_lines(
            request.with_user(self.approver_1).action_approve,
        )
        self.assertEqual(len(decide), 1, decide)
        self.assertIn("state=approved", decide[0])
        self.assertIn(f"actor={self.approver_1.login}", decide[0])

        reset = self._cycle_lines(
            request.with_user(self.manager_user).action_reset_to_draft,
        )
        self.assertEqual(len(reset), 1, reset)
        self.assertIn("was=approved", reset[0])
        self.assertIn("state=new", reset[0])

    def test_a_forced_terminal_is_traced_too(self):
        category = self._make_category(
            name="Cycle Log Cancel Cat",
            approval_minimum=1,
            approvers=[(self.approver_1, True, 10)],
        )
        request = self._prepare_request(category)

        lines = self._cycle_lines(
            request.with_user(self.owner_user).action_cancel,
        )

        self.assertEqual(len(lines), 1, lines)
        self.assertIn("terminal ", lines[0])
        self.assertIn("forced=cancelled", lines[0])
        self.assertIn("was=pending", lines[0])


@tagged("post_install", "-at_install")
class TestTerminalStateIsDefinedOnce(ApprovalCommon):
    def test_is_terminal_tracks_the_frozenset(self):
        category = self._make_category("Terminal Cat", approvers=[self.approver_1])
        request = self._prepare_request(category)
        self.assertFalse(request.is_terminal)
        request.with_user(self.approver_1).action_approve()
        self.assertEqual(request.state, "approved")
        self.assertTrue(request.is_terminal)
        self.assertEqual(
            {
                state
                for state, _label in self.env["approval.request"]
                ._fields["state"]
                .selection
                if self.env["approval.request"].new({"state": state}).is_terminal
            },
            set(self.env["approval.request"]._TERMINAL_STATES),
        )

    def test_no_view_of_this_module_re_types_the_terminal_set(self):
        views = self.env["ir.ui.view"].search(
            [("model", "in", ("approval.request", "approval.approver"))],
        )
        module_views = views.filtered(
            lambda v: (v.get_external_id().get(v.id) or "").startswith("approval."),
        )
        membership = re.compile(
            r"state\s+(?:not\s+)?in\s*[\(\[][^\)\]]*"
            r"'approved'[^\)\]]*'refused'[^\)\]]*'cancelled'",
        )
        offenders = [
            view.xml_id for view in module_views if membership.search(view.arch or "")
        ]
        self.assertFalse(
            offenders,
            "these views spell out the terminal states instead of asking "
            "is_terminal: %s" % offenders,
        )
