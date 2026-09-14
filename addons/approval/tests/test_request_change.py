from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import common, tagged

from .common import ApprovalCommon, add_category_approver, add_rule_step


@tagged("post_install", "-at_install")
class TestRequestChange(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_user = cls.env.ref("base.user_admin")
        cls.approver_user = cls.env["res.users"].create(
            {
                "name": "RC Approver",
                "login": "rc_approver",
                "email": "rc_approver@test.com",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.other_user = cls.env["res.users"].create(
            {
                "name": "RC Other",
                "login": "rc_other",
                "email": "rc_other@test.com",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.category = cls.env["approval.category"].create(
            {
                "sequence_code": "SC0051",
                "name": "Test Request Change Category",
                "approval_minimum": 1,
            }
        )
        add_category_approver(cls.category, cls.approver_user, required=True)

    def _pending_request(self):
        request = self.env["approval.request"].create(
            {
                "name": "RC Test Request",
                "request_owner_id": self.admin_user.id,
                "category_id": self.category.id,
                "reason": "<p>Initial description.</p>",
                "date": fields.Datetime.now(),
            }
        )
        request.action_confirm()
        return request

    def test_action_request_change_opens_wizard(self):
        request = self._pending_request()
        action = request.with_user(self.approver_user).action_request_change()
        self.assertIsInstance(action, dict)
        self.assertEqual(action["res_model"], "approval.decision.wizard")
        self.assertEqual(action["context"]["default_decision_type"], "change")
        self.assertIn("default_approver_id", action["context"])
        self.assertFalse(request.pending_change_field)

    def test_action_request_change_inline_sets_flag(self):
        request = self._pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )
        request.with_context(
            skip_wizard=True, requested_change_field="date"
        ).action_request_change(approver=approver)
        self.assertEqual(request.pending_change_field, "date")
        self.assertEqual(request.state, "pending")

    def test_action_request_change_requires_pending_state(self):
        request = self.env["approval.request"].create(
            {
                "name": "RC New Request",
                "request_owner_id": self.admin_user.id,
                "category_id": self.category.id,
            }
        )
        with self.assertRaises(UserError):
            request.with_user(self.approver_user).action_request_change()

    def test_action_request_change_blocked_when_already_pending(self):
        request = self._pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )
        request.with_context(
            skip_wizard=True, requested_change_field="date"
        ).action_request_change(approver=approver)
        with self.assertRaises(UserError):
            request.with_user(self.approver_user).action_request_change()

    def test_approve_blocked_while_pending_change(self):
        request = self._pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )
        request.with_context(
            skip_wizard=True, requested_change_field="reason"
        ).action_request_change(approver=approver)
        with self.assertRaises(UserError):
            request.with_user(self.approver_user).action_approve(approver)

    def test_refuse_blocked_while_pending_change(self):
        request = self._pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )
        request.with_context(
            skip_wizard=True, requested_change_field="reason"
        ).action_request_change(approver=approver)
        with self.assertRaises(UserError):
            request.with_user(self.approver_user).with_context(
                skip_wizard=True
            ).action_refuse(approver)

    def test_resubmit_clears_pending_change_field(self):
        request = self._pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )
        request.with_context(
            skip_wizard=True, requested_change_field="date"
        ).action_request_change(approver=approver)
        request.with_user(self.admin_user).action_resubmit()
        self.assertFalse(request.pending_change_field)
        request.with_user(self.approver_user).with_context(
            skip_wizard=True
        ).action_approve(approver)
        self.assertEqual(request.state, "approved")

    def test_resubmit_blocked_for_non_owner_non_manager(self):
        request = self._pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )
        request.with_context(
            skip_wizard=True, requested_change_field="date"
        ).action_request_change(approver=approver)
        with self.assertRaises(UserError):
            request.with_user(self.other_user).action_resubmit()

    def test_resubmit_requires_pending_change(self):
        request = self._pending_request()
        with self.assertRaises(UserError):
            request.with_user(self.admin_user).action_resubmit()

    def test_resubmit_posts_chatter_notification(self):
        request = self._pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )
        request.with_context(
            skip_wizard=True, requested_change_field="reason"
        ).action_request_change(approver=approver)
        msg_count_before = len(request.message_ids)
        request.with_user(self.admin_user).action_resubmit()
        new_messages = request.message_ids[
            : len(request.message_ids) - msg_count_before
        ]
        bodies = " ".join(m.body or "" for m in new_messages)
        self.assertIn("reason", bodies.lower())

    def test_wizard_requires_change_field(self):
        request = self._pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )
        wizard = (
            self.env["approval.decision.wizard"]
            .with_user(self.approver_user)
            .create(
                {
                    "approver_id": approver.id,
                    "decision_type": "change",
                    "note": "Please fix it",
                }
            )
        )
        with self.assertRaises(UserError):
            wizard.action_confirm_change()

    def test_wizard_requires_change_note(self):
        request = self._pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )
        wizard = (
            self.env["approval.decision.wizard"]
            .with_user(self.approver_user)
            .create(
                {
                    "approver_id": approver.id,
                    "decision_type": "change",
                    "change_field": "date",
                }
            )
        )
        with self.assertRaises(UserError):
            wizard.action_confirm_change()

    def test_wizard_confirm_sets_flag_and_schedules_activity(self):
        request = self._pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )
        wizard = (
            self.env["approval.decision.wizard"]
            .with_user(self.approver_user)
            .create(
                {
                    "approver_id": approver.id,
                    "decision_type": "change",
                    "change_field": "date",
                    "note": "Move the date to next Monday.",
                }
            )
        )
        wizard.action_confirm_change()
        self.assertEqual(request.pending_change_field, "date")
        change_type = self.env.ref("approval.mail_activity_data_change_request")
        activities = request.activity_ids.filtered(
            lambda a: a.activity_type_id == change_type
        )
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities.user_id, self.admin_user)
        self.assertIn("Date", activities.summary)
        self.assertIn("Move the date to next Monday.", activities.note)

    def test_resubmit_marks_change_activity_done(self):
        request = self._pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )
        wizard = (
            self.env["approval.decision.wizard"]
            .with_user(self.approver_user)
            .create(
                {
                    "approver_id": approver.id,
                    "decision_type": "change",
                    "change_field": "reason",
                    "note": "Clarify the description.",
                }
            )
        )
        wizard.action_confirm_change()
        change_type = self.env.ref("approval.mail_activity_data_change_request")
        self.assertTrue(
            request.activity_ids.filtered(lambda a: a.activity_type_id == change_type)
        )
        request.with_user(self.admin_user).action_resubmit()
        self.assertFalse(
            request.activity_ids.filtered(lambda a: a.activity_type_id == change_type)
        )


@tagged("post_install", "-at_install")
class TestRequestChangeAuditRegressions(ApprovalCommon):
    def test_change_request_note_preserves_line_breaks(self):
        category = self._make_category(approvers=[self.approver_1])
        request = self._prepare_request(category, date=fields.Datetime.now())
        approver = request.approver_ids

        wizard = (
            self.env["approval.decision.wizard"]
            .with_user(
                self.approver_1,
            )
            .create(
                {
                    "approver_id": approver.id,
                    "decision_type": "change",
                    "change_field": "date",
                    "note": "Line one.\nLine two <script>alert(1)</script>.",
                },
            )
        )
        wizard.action_confirm_change()

        change_type = self.env.ref("approval.mail_activity_data_change_request")
        activity = request.activity_ids.filtered(
            lambda a: a.activity_type_id == change_type,
        )
        self.assertIn("<br", activity.note)
        self.assertNotIn("<script>", activity.note)
        self.assertIn("&lt;script&gt;", activity.note)


@tagged("post_install", "-at_install")
class TestRequestChangeInvalidatesApprovals(ApprovalCommon):
    def _request_change(self, request, user, field="date"):
        approver = request.approver_ids.filtered(
            lambda a, u=user: a.user_id == u,
        )
        request.with_user(user).with_context(
            skip_wizard=True,
            requested_change_field=field,
        ).action_request_change(approver=approver)

    def _parallel_request(self):
        category = self._make_category(
            name=f"Change Cat {self.id()}",
            approval_minimum=2,
            approvers=[(self.approver_1, True, 10), (self.approver_2, True, 20)],
        )
        return self._prepare_request(category, date=fields.Datetime.now())

    def test_resubmit_resets_approvals_given_before_the_change(self):
        request = self._parallel_request()
        request.with_user(self.approver_1).action_approve()
        self._request_change(request, self.approver_2)

        request.with_user(self.owner_user).write(
            {"date": fields.Datetime.now() + timedelta(days=90)},
        )
        request.with_user(self.owner_user).action_resubmit()

        rows = {a.user_id: a for a in request.approver_ids}
        self.assertEqual(
            rows[self.approver_1].state,
            "pending",
            "The first approver signed off on the previous date; the "
            "re-submission must ask them again.",
        )
        self.assertFalse(rows[self.approver_1].decision_date)
        activity_type = self.env.ref("approval.mail_activity_data_approval")
        self.assertTrue(
            request.activity_ids.filtered(
                lambda a: (
                    a.activity_type_id == activity_type and a.user_id == self.approver_1
                ),
            ),
            "Re-opening a row must come with the To-Do that makes it visible.",
        )

        request.with_user(self.approver_2).action_approve()
        self.assertEqual(request.state, "pending")
        request.with_user(self.approver_1).action_approve()
        self.assertEqual(request.state, "approved")

    def test_resubmit_without_prior_approvals_touches_nothing(self):
        request = self._parallel_request()
        self._request_change(request, self.approver_2)
        pending_since = {a.id: a.pending_since for a in request.approver_ids}

        request.with_user(self.owner_user).action_resubmit()

        self.assertEqual(
            {a.id: a.pending_since for a in request.approver_ids},
            pending_since,
            "A re-submission that invalidates nothing must not restart "
            "anybody's measured response time.",
        )
        self.assertTrue(
            all(a.state == "pending" for a in request.approver_ids),
        )

    def test_resubmit_restarts_a_sequential_chain(self):
        category = self._make_category(
            name=f"Change Seq Cat {self.id()}",
            approval_minimum=2,
            in_order=True,
            approvers=[(self.approver_1, True, 10), (self.approver_2, True, 20)],
        )
        request = self._prepare_request(category, date=fields.Datetime.now())
        request.with_user(self.approver_1).action_approve()
        self._request_change(request, self.approver_2)

        request.with_user(self.owner_user).action_resubmit()

        rows = {a.user_id: a for a in request.approver_ids}
        self.assertEqual(
            rows[self.approver_1].state,
            "pending",
            "The chain restarts from its first approver.",
        )
        self.assertEqual(
            rows[self.approver_2].state,
            "waiting",
            "The approver who asked for the change waits their turn "
            "again — approving out of order is exactly what "
            "approve_sequentially forbids.",
        )

    def test_an_approver_cannot_apply_the_requested_change_themselves(self):
        request = self._parallel_request()
        self._request_change(request, self.approver_2)

        with self.assertRaises(ValidationError):
            request.with_user(self.approver_1).write(
                {"date": fields.Datetime.now() + timedelta(days=90)},
            )
        with self.assertRaises(ValidationError):
            request.with_user(self.approver_2).write(
                {"date": fields.Datetime.now() + timedelta(days=90)},
            )

    def test_the_owner_and_a_manager_may_apply_the_requested_change(self):
        request = self._parallel_request()
        self._request_change(request, self.approver_2)

        new_date = fields.Datetime.now() + timedelta(days=90)
        request.with_user(self.owner_user).write({"date": new_date})
        self.assertEqual(request.date, new_date)

        manager_date = fields.Datetime.now() + timedelta(days=120)
        request.with_user(self.manager_user).write({"date": manager_date})
        self.assertEqual(request.date, manager_date)

    def test_the_owner_may_only_touch_the_flagged_field(self):
        request = self._parallel_request()
        self._request_change(request, self.approver_2, field="reason")

        with self.assertRaises(ValidationError):
            request.with_user(self.owner_user).write(
                {"date": fields.Datetime.now() + timedelta(days=90)},
            )
        request.with_user(self.owner_user).write({"reason": "<p>Reworded.</p>"})


@tagged("post_install", "-at_install")
class TestRequestChangeReachability(ApprovalCommon):
    def _pending(self, **request_vals):
        category = self._make_category(
            name=f"Reach Cat {self.id()}",
            approval_minimum=1,
            approvers=[(self.approver_1, True, 10)],
        )
        return self._prepare_request(category, **request_vals)

    def _request_change(self, request, field):
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_1,
        )
        request.with_user(self.approver_1).with_context(
            skip_wizard=True,
            requested_change_field=field,
        ).action_request_change(approver=approver)

    def test_date_change_refused_when_the_request_carries_no_date(self):
        request = self._pending()

        with self.assertRaises(UserError):
            self._request_change(request, "date")

        self.assertFalse(
            request.pending_change_field,
            "A request must not be frozen on a field nobody can edit.",
        )
        self.assertEqual(request.state, "pending")
        self._request_change(request, "reason")
        self.assertEqual(request.pending_change_field, "reason")

    def test_date_change_allowed_when_only_the_period_is_set(self):
        request = self._pending(
            date_start=fields.Datetime.now(),
            date_end=fields.Datetime.now() + timedelta(days=1),
        )

        self._request_change(request, "date")

        self.assertEqual(request.pending_change_field, "date")
        request.with_user(self.owner_user).write(
            {"date_end": fields.Datetime.now() + timedelta(days=2)},
        )
        request.with_user(self.owner_user).action_resubmit()
        self.assertFalse(request.pending_change_field)

    def test_reason_is_always_reachable(self):
        request = self._pending()
        self.assertEqual(
            request._get_pending_change_candidates(),
            frozenset({"reason"}),
        )

    def test_the_wizard_surfaces_the_same_refusal(self):
        request = self._pending()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_1,
        )
        wizard = (
            self.env["approval.decision.wizard"]
            .with_user(self.approver_1)
            .create(
                {
                    "approver_id": approver.id,
                    "decision_type": "change",
                    "change_field": "date",
                    "note": "Please move it.",
                },
            )
        )

        with self.assertRaises(UserError):
            wizard.action_confirm_change()

        self.assertFalse(request.pending_change_field)


@tagged("post_install", "-at_install")
class TestRequestChangeReroutes(ApprovalCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.long_trip_approver = cls.env["res.users"].create(
            {
                "name": "Long Trip Approver",
                "login": "rc_long_trip",
                "email": "longtrip@rc.test",
            },
        )

    def _category_with_range_rule(self):
        category = self._make_category(
            "RC Reroute",
            approvers=[self.approver_1],
        )
        add_rule_step(
            category,
            self.long_trip_approver,
            required=False,
            sequence=20,
            name="Long trips need a second signature",
            condition_field="date_range_days",
            operator="gt",
            threshold=14,
        )
        return category

    def _short_trip(self, category):
        start = fields.Datetime.now()
        return self._prepare_request(
            category,
            date_start=start,
            date_end=start + timedelta(days=5),
        )

    def _ask_for_a_date_change(self, request, user=None):
        user = user or self.approver_1
        approver = request.approver_ids.filtered(lambda a, u=user: a.user_id == u)
        request.with_user(user).with_context(
            skip_wizard=True,
            requested_change_field="date",
        ).action_request_change(approver=approver)

    def test_editing_the_dates_mid_change_does_not_reroute_yet(self):
        category = self._category_with_range_rule()
        request = self._short_trip(category)
        self._ask_for_a_date_change(request)

        request.with_user(self.owner_user).write(
            {"date_end": request.date_start + timedelta(days=30)},
        )

        self.assertEqual(request.pending_change_field, "date")
        self.assertNotIn(self.long_trip_approver, request.approver_ids.user_id)

    def test_resubmit_reroutes_on_the_new_dates(self):
        category = self._category_with_range_rule()
        request = self._short_trip(category)
        self._ask_for_a_date_change(request)
        request.with_user(self.owner_user).write(
            {"date_end": request.date_start + timedelta(days=30)},
        )

        request.with_user(self.owner_user).action_resubmit()

        self.assertFalse(request.pending_change_field)
        self.assertEqual(request.state, "pending")
        self.assertIn(self.long_trip_approver, request.approver_ids.user_id)

    def test_resubmit_resets_approvals_and_reroutes_in_one_round(self):
        category = self._make_category(
            "RC Reroute Reset",
            approvers=[(self.approver_1, False, 10), (self.approver_2, False, 20)],
            approval_minimum=2,
        )
        add_rule_step(
            category,
            self.long_trip_approver,
            required=False,
            sequence=20,
            name="Long trips need a second signature",
            condition_field="date_range_days",
            operator="gt",
            threshold=14,
        )
        request = self._short_trip(category)
        request.with_user(self.approver_1).action_approve()
        self._ask_for_a_date_change(request, user=self.approver_2)
        request.with_user(self.owner_user).write(
            {"date_end": request.date_start + timedelta(days=30)},
        )

        request.with_user(self.owner_user).action_resubmit()

        self.assertNotEqual(
            request.approver_ids.filtered(
                lambda a: a.user_id == self.approver_1,
            ).state,
            "approved",
        )
        self.assertIn(self.long_trip_approver, request.approver_ids.user_id)
        self.assertEqual(request.state, "pending")

    def test_resubmit_without_a_routing_change_adds_nobody(self):
        category = self._category_with_range_rule()
        request = self._short_trip(category)
        before = request.approver_ids.user_id
        self._ask_for_a_date_change(request)

        request.with_user(self.owner_user).action_resubmit()

        self.assertEqual(request.approver_ids.user_id, before)
        self.assertEqual(request.state, "pending")


class TestChangeRequestActivityBelongsToTheAction(ApprovalCommon):
    def test_inline_request_change_schedules_the_owner_activity(self):
        category = self._make_category(
            name="Inline Change", approvers=[self.approver_1]
        )
        request = self._prepare_request(category)
        change_type = self.env.ref("approval.mail_activity_data_change_request")

        request.with_user(self.approver_1).with_context(
            skip_wizard=True,
            requested_change_field="reason",
            requested_change_note="Say why.",
        ).action_request_change()

        activities = request.activity_ids.filtered(
            lambda a: a.activity_type_id == change_type
        )
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities.user_id, self.owner_user)
        self.assertIn("Say why.", activities.note)

        request.with_user(self.owner_user).action_resubmit()
        self.assertFalse(
            request.activity_ids.filtered(lambda a: a.activity_type_id == change_type)
        )
