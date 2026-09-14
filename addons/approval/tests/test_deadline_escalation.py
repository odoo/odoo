from datetime import datetime, timedelta
from unittest.mock import patch

from freezegun import freeze_time

from odoo import fields
from odoo.tests import common, tagged

from .common import (
    ApprovalCommon,
    add_category_approver,
    isolate_group_approval_manager,
    record_approval,
)
from .common import isolate_group_approval_manager as _isolate_group_approval_manager
from odoo.addons.approval.models import approval_request_escalation


@tagged("post_install", "-at_install")
class TestDeadlineEscalation(common.TransactionCase):
    def setUp(self):
        super().setUp()

        self.admin_user = self.env.ref("base.user_admin")
        self.approver_user = self.env["res.users"].create(
            {
                "name": "Test Approver",
                "login": "test_approver",
                "email": "approver@test.com",
            }
        )
        self.escalation_user = self.env["res.users"].create(
            {
                "name": "Escalation Manager",
                "login": "escalation_mgr",
                "email": "escalation@test.com",
            }
        )

        self.category_with_deadline = self.env["approval.category"].create(
            {
                "sequence_code": "SC0036",
                "name": "Test Category with Deadline",
                "approval_minimum": 1,
                "approval_deadline_hours": 48,
                "escalate_overdue": True,
                "escalation_user_id": self.escalation_user.id,
            }
        )

        self.category_no_deadline = self.env["approval.category"].create(
            {
                "sequence_code": "SC0037",
                "name": "Test Category without Deadline",
                "approval_minimum": 1,
                "approval_deadline_hours": 0,
                "escalate_overdue": False,
            }
        )

        add_category_approver(
            self.category_with_deadline, self.approver_user, required=True
        )
        add_category_approver(
            self.category_no_deadline, self.approver_user, required=True
        )

    def test_approval_deadline_calculation(self):
        request = self.env["approval.request"].create(
            {
                "name": "Test Request with Deadline",
                "request_owner_id": self.admin_user.id,
                "category_id": self.category_with_deadline.id,
            }
        )

        self.assertFalse(
            request.approval_deadline,
            "Deadline should be False before confirmation",
        )

        with freeze_time("2025-10-16 10:00:00"):
            request.action_confirm()

            expected_deadline = fields.Datetime.to_datetime(
                "2025-10-16 10:00:00"
            ) + timedelta(hours=48)
            self.assertEqual(
                request.approval_deadline,
                expected_deadline,
                "Deadline should be date_confirmed + 48 hours",
            )

    def test_approval_deadline_no_hours_set(self):
        request = self.env["approval.request"].create(
            {
                "name": "Test Request without Deadline",
                "request_owner_id": self.admin_user.id,
                "category_id": self.category_no_deadline.id,
            }
        )

        request.action_confirm()

        self.assertFalse(
            request.approval_deadline,
            "Deadline should be False when category has 0 deadline hours",
        )

    def test_overdue_detection_not_overdue(self):
        request = self.env["approval.request"].create(
            {
                "name": "Test Request Not Overdue",
                "request_owner_id": self.admin_user.id,
                "category_id": self.category_with_deadline.id,
            }
        )

        with freeze_time("2025-10-16 10:00:00"):
            request.action_confirm()

            with freeze_time("2025-10-16 11:00:00"):
                request.invalidate_recordset(["is_overdue"])
                self.assertFalse(
                    request.is_overdue,
                    "Request should not be overdue within deadline period",
                )

    def test_overdue_detection_is_overdue(self):
        request = self.env["approval.request"].create(
            {
                "name": "Test Request Overdue",
                "request_owner_id": self.admin_user.id,
                "category_id": self.category_with_deadline.id,
            }
        )

        with freeze_time("2025-10-16 10:00:00"):
            request.action_confirm()

            with freeze_time("2025-10-19 11:00:00"):
                request.invalidate_recordset(["is_overdue"])
                self.assertTrue(
                    request.is_overdue,
                    "Request should be overdue when past deadline and state=pending",
                )

    def test_overdue_not_set_when_approved(self):
        request = self.env["approval.request"].create(
            {
                "name": "Test Request Approved",
                "request_owner_id": self.admin_user.id,
                "category_id": self.category_with_deadline.id,
            }
        )

        with freeze_time("2025-10-16 10:00:00"):
            request.action_confirm()

            approver = request.approver_ids.filtered(
                lambda a: a.user_id == self.approver_user
            )
            record_approval(approver)

            with freeze_time("2025-10-19 11:00:00"):
                request.invalidate_recordset(["is_overdue", "state"])
                self.assertEqual(
                    request.state, "approved", "Request should be approved"
                )
                self.assertFalse(
                    request.is_overdue,
                    "Approved request should not be overdue even if past deadline",
                )

    def test_search_is_overdue_true(self):
        request = self.env["approval.request"].create(
            {
                "name": "Overdue Request",
                "request_owner_id": self.admin_user.id,
                "category_id": self.category_with_deadline.id,
            }
        )

        with freeze_time("2025-10-16 10:00:00"):
            request.action_confirm()
            self.env.flush_all()

        request.invalidate_recordset()
        self.assertEqual(
            request.state, "pending", "State should be pending after confirm"
        )
        self.assertTrue(
            request.approval_deadline, "Deadline should be set after confirm"
        )

        past_deadline = datetime(2020, 1, 1, 10, 0, 0)
        self.env.cr.execute(
            "UPDATE approval_request SET approval_deadline = %s WHERE id = %s",
            [past_deadline, request.id],
        )
        request.invalidate_recordset()

        self.assertEqual(
            request.approval_deadline.replace(microsecond=0),
            past_deadline,
            "Deadline should be updated via SQL",
        )

        now = fields.Datetime.now()
        overdue_domain = [
            ("id", "=", request.id),
            ("approval_deadline", "!=", False),
            ("approval_deadline", "<", now),
            ("state", "=", "pending"),
        ]
        overdue_requests = self.env["approval.request"].search(overdue_domain)
        self.assertIn(
            request,
            overdue_requests,
            "Request should be found with explicit overdue domain",
        )

        future_deadline = datetime(2099, 12, 31, 23, 59, 59)
        self.env.cr.execute(
            "UPDATE approval_request SET approval_deadline = %s WHERE id = %s",
            [future_deadline, request.id],
        )
        request.invalidate_recordset()

        not_overdue_domain = [
            ("id", "=", request.id),
            ("approval_deadline", "!=", False),
            ("approval_deadline", "<", now),
            ("state", "=", "pending"),
        ]
        not_overdue_requests = self.env["approval.request"].search(not_overdue_domain)
        self.assertNotIn(
            request,
            not_overdue_requests,
            "Request should not be found when deadline is in future",
        )

    def test_escalation_cron_sends_notifications(self):
        request = self.env["approval.request"].create(
            {
                "name": "Test Escalation",
                "request_owner_id": self.admin_user.id,
                "category_id": self.category_with_deadline.id,
            }
        )

        with freeze_time("2025-10-16 10:00:00"):
            request.action_confirm()
            self.env.flush_all()

        request.invalidate_recordset()
        self.assertEqual(
            request.state, "pending", "State should be pending after confirm"
        )

        past_deadline = datetime(2020, 1, 1, 10, 0, 0)
        self.env.cr.execute(
            "UPDATE approval_request SET approval_deadline = %s WHERE id = %s",
            [past_deadline, request.id],
        )
        request.invalidate_recordset()

        message_count_before = len(request.message_ids)

        pending_approvers = request.approver_ids.filtered(
            lambda a: a.state == "pending"
        )
        escalation_user = self.escalation_user

        body = self.env._(
            "⚠ OVERDUE APPROVAL REQUEST\n\n"
            "Request: %(name)s\n"
            "Submitted: %(date)s\n"
            "Deadline: %(deadline)s\n"
            "Pending Approvers: %(approvers)s\n\n"
            "Please review this request urgently.",
            name=request.name,
            date=request.date_confirmed,
            deadline=request.approval_deadline,
            approvers=", ".join(pending_approvers.mapped("user_id.name")),
        )

        request.message_post(
            body=body,
            subject=self.env._("⚠ Overdue Approval: %s", request.name),
            partner_ids=(
                escalation_user.partner_id.ids
                + pending_approvers.mapped("user_id.partner_id").ids
            ),
            message_type="notification",
            subtype_id=self.env.ref("mail.mt_note").id,
        )

        request.invalidate_recordset(["message_ids"])
        message_count_after = len(request.message_ids)
        self.assertGreater(
            message_count_after,
            message_count_before,
            "Escalation should post a message",
        )

        latest_message = request.message_ids[0]
        self.assertIn(
            "OVERDUE",
            latest_message.body,
            "Escalation message should contain OVERDUE text",
        )

    def test_escalation_notifies_pending_approvers(self):
        request = self.env["approval.request"].create(
            {
                "name": "Test Approver Notification",
                "request_owner_id": self.admin_user.id,
                "category_id": self.category_with_deadline.id,
            }
        )

        with freeze_time("2025-10-16 10:00:00"):
            request.action_confirm()
            self.env.flush_all()

        request.invalidate_recordset()
        self.assertEqual(
            request.state, "pending", "State should be pending after confirm"
        )

        pending_approvers = request.approver_ids.filtered(
            lambda a: a.state == "pending"
        )
        self.assertTrue(pending_approvers, "Should have pending approvers")

        body = self.env._(
            "⚠ OVERDUE APPROVAL REQUEST\n\nRequest: %(name)s\nPending Approvers: %(approvers)s\n",
            name=request.name,
            approvers=", ".join(pending_approvers.mapped("user_id.name")),
        )

        request.message_post(
            body=body,
            subject=self.env._("⚠ Overdue Approval: %s", request.name),
            partner_ids=(
                self.escalation_user.partner_id.ids
                + pending_approvers.mapped("user_id.partner_id").ids
            ),
            message_type="notification",
            subtype_id=self.env.ref("mail.mt_note").id,
        )

        request.invalidate_recordset(["message_ids"])
        latest_message = request.message_ids[0]

        self.assertIn(
            self.approver_user.name,
            latest_message.body,
            "Escalation message should mention pending approver name",
        )

        notified_partners = latest_message.partner_ids
        self.assertIn(
            self.escalation_user.partner_id,
            notified_partners,
            "Escalation user should be in notified partners",
        )
        self.assertIn(
            self.approver_user.partner_id,
            notified_partners,
            "Pending approver should be in notified partners",
        )

    def _make_urgent_pending_request(self, confirmed_at):
        request = self.env["approval.request"].create(
            {
                "name": "Urgent Escalation Test",
                "request_owner_id": self.admin_user.id,
                "category_id": self.category_with_deadline.id,
                "priority": "3",
            }
        )
        with freeze_time(confirmed_at):
            request.action_confirm()
        self.env.flush_all()
        return request

    def test_cron_smart_escalation_sends_first_reminder(self):
        confirmed_at = "2026-01-05 08:00:00"
        request = self._make_urgent_pending_request(confirmed_at)
        self.assertEqual(request.reminder_count, 0)
        self.assertFalse(request.last_reminder_date)

        five_hours_later = "2026-01-05 13:00:00"
        with freeze_time(five_hours_later):
            sent = self.env["approval.request"].cron_smart_escalation()
            self.env.flush_all()

        request.invalidate_recordset()
        self.assertGreaterEqual(sent, 1)
        self.assertEqual(
            request.reminder_count,
            1,
            "First reminder should increment reminder_count from 0 to 1",
        )
        self.assertEqual(
            request.last_reminder_date,
            fields.Datetime.to_datetime(five_hours_later),
        )
        self.assertFalse(
            request.escalated_to_manager,
            "4h reminder is below the 8h escalation threshold",
        )

        activity = request.activity_ids.filtered(
            lambda a: (
                a.activity_type_id
                == self.env.ref("approval.mail_activity_data_approval")
            ),
        )
        self.assertIn(
            "Reminder",
            activity.summary or "",
            "The pending approver's activity should be updated with a reminder summary",
        )

    def test_cron_smart_escalation_before_threshold_is_a_noop(self):
        confirmed_at = "2026-01-05 08:00:00"
        request = self._make_urgent_pending_request(confirmed_at)

        one_hour_later = "2026-01-05 09:00:00"
        with freeze_time(one_hour_later):
            self.env["approval.request"].cron_smart_escalation()
            self.env.flush_all()

        request.invalidate_recordset()
        self.assertEqual(request.reminder_count, 0)
        self.assertFalse(request.last_reminder_date)

    def test_cron_smart_escalation_uses_category_escalation_contact(self):
        confirmed_at = "2026-01-05 08:00:00"
        request = self._make_urgent_pending_request(confirmed_at)

        nine_hours_later = "2026-01-05 17:00:00"
        with freeze_time(nine_hours_later):
            sent = self.env["approval.request"].cron_smart_escalation()
            self.env.flush_all()

        request.invalidate_recordset()
        self.assertGreaterEqual(sent, 1)
        self.assertEqual(request.reminder_count, 1)
        self.assertTrue(
            request.escalated_to_manager,
            "The category escalation contact must receive the escalation",
        )
        escalation_messages = request.message_ids.filtered(
            lambda m: self.escalation_user.partner_id in m.partner_ids,
        )
        self.assertTrue(
            escalation_messages,
            "The escalation notice must be addressed to the category's "
            "escalation contact",
        )

    def _escalation_notices(self, request):
        request.invalidate_recordset()
        return request.message_ids.filtered(
            lambda m: "Escalation Notice" in (m.body or ""),
        )

    def test_escalation_notice_body_is_markup(self):
        confirmed_at = "2026-01-05 08:00:00"
        request = self._make_urgent_pending_request(confirmed_at)

        with freeze_time("2026-01-05 17:00:00"):
            self.env["approval.request"].cron_smart_escalation()
            self.env.flush_all()

        notices = self._escalation_notices(request)
        self.assertEqual(len(notices), 1)
        self.assertIn(
            "<strong>Escalation Notice</strong>",
            notices.body,
            "the notice must reach the reader as markup",
        )
        self.assertNotIn(
            "&lt;",
            notices.body,
            "a translated str carrying tags is escaped by message_post and "
            "shows the reader its own source",
        )

    def test_a_stalled_approver_escalates_once_not_every_run(self):
        # A second approver is what keeps the archive handover from
        # reassigning the first one: the successor it would pick is already an
        # approver, so the archived one stays pending. That is the shape a
        # stalled approver actually has in production.
        add_category_approver(
            self.category_with_deadline, self.escalation_user, required=False
        )
        confirmed_at = "2026-01-05 08:00:00"
        request = self._make_urgent_pending_request(confirmed_at)
        self.assertEqual(
            len(request.approver_ids),
            2,
            "the scenario needs a second approver to block the handover",
        )

        with freeze_time("2026-01-05 17:00:00"):
            self.env["approval.request"].cron_smart_escalation()
            self.env.flush_all()
        request.invalidate_recordset()
        self.assertTrue(request.escalated_to_manager)
        self.assertEqual(len(self._escalation_notices(request)), 1)

        self.approver_user.write({"active": False})
        self.env.flush_all()
        self.assertTrue(
            any(
                not a._get_effective_approver().active
                for a in request.approver_ids
                if a.state == "pending"
            ),
            "the archived approver must stay pending for this scenario",
        )

        # An approver who left the company is a reason to escalate ahead of
        # the age threshold, not a reason to escalate again on every run:
        # nothing clears the condition, so this re-sent the same notice daily
        # for the rest of the request's life.
        for day in ("2026-01-06 17:00:00", "2026-01-07 17:00:00"):
            with freeze_time(day):
                self.env["approval.request"].cron_smart_escalation()
                self.env.flush_all()

        self.assertEqual(
            len(self._escalation_notices(request)),
            1,
            "an already-escalated request must not re-escalate while a "
            "pending approver stays archived",
        )

    def test_cron_smart_escalation_escalates_falls_back_without_manager_hook(
        self,
    ):
        _isolate_group_approval_manager(self.env, self.env["res.users"])
        self.category_with_deadline.write(
            {"escalate_overdue": False, "escalation_user_id": False},
        )
        confirmed_at = "2026-01-05 08:00:00"
        request = self._make_urgent_pending_request(confirmed_at)

        nine_hours_later = "2026-01-05 17:00:00"
        with freeze_time(nine_hours_later):
            sent = self.env["approval.request"].cron_smart_escalation()
            self.env.flush_all()

        request.invalidate_recordset()
        self.assertGreaterEqual(
            sent,
            1,
            "The fallback reminder must still count as work done",
        )
        self.assertEqual(request.reminder_count, 1)
        self.assertFalse(
            request.escalated_to_manager,
            "Must stay False: _get_escalation_manager() found no manager "
            "and no category escalation contact, so nothing was escalated",
        )
        activity_type = self.env.ref("approval.mail_activity_data_approval")
        activities = request.activity_ids.filtered(
            lambda a: (
                a.activity_type_id == activity_type and a.user_id == self.approver_user
            ),
        )
        self.assertTrue(
            activities,
            "Pending approver should have an approval activity after "
            "the reminder fallback runs.",
        )

    def test_cron_smart_escalation_does_not_resend_before_next_threshold(self):
        confirmed_at = "2026-01-05 08:00:00"
        request = self._make_urgent_pending_request(confirmed_at)

        with freeze_time("2026-01-05 13:00:00"):
            self.env["approval.request"].cron_smart_escalation()
            self.env.flush_all()
        request.invalidate_recordset()
        self.assertEqual(request.reminder_count, 1)

        with freeze_time("2026-01-05 14:00:00"):
            sent = self.env["approval.request"].cron_smart_escalation()
            self.env.flush_all()
        request.invalidate_recordset()
        self.assertEqual(
            sent,
            0,
            "Only 1h since the last reminder — well under the 4h "
            "interval, must not resend",
        )
        self.assertEqual(request.reminder_count, 1)

    def test_cron_smart_escalation_batch_limit_defers_the_rest(self):
        confirmed_at = "2026-01-05 08:00:00"
        requests = self.env["approval.request"]
        for _ in range(3):
            requests |= self._make_urgent_pending_request(confirmed_at)

        five_hours_later = "2026-01-05 13:00:00"
        with (
            patch.object(approval_request_escalation, "CRON_BATCH_LIMIT", 2),
            freeze_time(five_hours_later),
        ):
            sent = self.env["approval.request"].cron_smart_escalation()
            self.env.flush_all()

        requests.invalidate_recordset()
        self.assertEqual(
            sent,
            2,
            "Exactly CRON_BATCH_LIMIT requests should be processed this tick",
        )
        self.assertEqual(
            sum(requests.mapped("reminder_count")),
            2,
            "The request(s) beyond the batch limit are deferred to the "
            "next tick, not dropped",
        )


@tagged("post_install", "-at_install")
class TestEscalationHookDefaults(common.TransactionCase):
    def setUp(self):
        super().setUp()
        _isolate_group_approval_manager(self.env, self.env["res.users"])
        self.admin_user = self.env.ref("base.user_admin")
        self.approver_user = self.env["res.users"].create(
            {
                "name": "Escalation Hook Approver",
                "login": "escalation_hook_approver",
                "email": "escalation_hook_approver@test.com",
            }
        )
        self.category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0055",
                "name": "Escalation Hook Category",
                "approval_minimum": 1,
                "approval_deadline_hours": 24,
            }
        )
        add_category_approver(self.category, self.approver_user, required=True)

    def _make_pending_request(self, confirmed_at="2025-10-16 10:00:00", priority="1"):
        request = self.env["approval.request"].create(
            {
                "name": "Escalation Hook Request",
                "request_owner_id": self.admin_user.id,
                "category_id": self.category.id,
                "priority": priority,
            }
        )
        with freeze_time(confirmed_at):
            request.action_confirm()
            self.env.flush_all()
        request.invalidate_recordset()
        self.assertEqual(request.state, "pending")
        return request

    def test_get_escalation_manager_default_is_empty(self):
        request = self._make_pending_request()
        approver = request.approver_ids[:1]

        manager = request._get_escalation_manager(approver)

        self.assertEqual(
            manager,
            self.env["res.users"],
            "Should return empty when no category contact AND no "
            "group_approval_manager member exist for this company.",
        )

    def test_escalate_to_manager_returns_zero_when_no_hook(self):
        request = self._make_pending_request()

        count = request._escalate_to_manager()

        self.assertEqual(
            count,
            0,
            "Without a manager hook, escalation should report 0 managers notified.",
        )
        self.assertFalse(
            request.escalated_to_manager,
            "escalated_to_manager must stay False when nothing was "
            "actually escalated — otherwise the smart cron would loop "
            "forever without ever sending a real reminder.",
        )

    def test_smart_escalation_no_counter_bump_when_nothing_happens(self):
        request = self._make_pending_request(
            confirmed_at="2025-10-16 00:00:00", priority="3"
        )

        request.approver_ids.sudo()._record_decision("refused")
        self.env.cr.execute(
            "UPDATE approval_request SET state = 'pending' WHERE id = %s",
            [request.id],
        )
        request.invalidate_recordset()

        with freeze_time("2025-10-16 10:00:00"):
            self.env["approval.request"].cron_smart_escalation()

        request.invalidate_recordset()
        self.assertEqual(
            request.reminder_count,
            0,
            "Counter must NOT bump when nothing was actually sent.",
        )


@tagged("post_install", "-at_install")
class TestEscalationFanOut(ApprovalCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.escalation_contact = cls.env["res.users"].create(
            {
                "name": "Escalation Contact",
                "login": "fanout_contact",
                "email": "fanout.contact@test.com",
            },
        )
        cls.third_approver = cls.env["res.users"].create(
            {
                "name": "Third Approver",
                "login": "fanout_third",
                "email": "fanout.third@test.com",
            },
        )
        cls.category = cls._make_category(
            name="Fan-out Cat",
            approvers=[
                (cls.approver_1, False, 10),
                (cls.approver_2, False, 10),
                (cls.third_approver, False, 10),
            ],
            approval_minimum=3,
            escalate_overdue=True,
            escalation_user_id=cls.escalation_contact.id,
        )

    def test_one_message_per_manager_not_per_approver(self):
        request = self._prepare_request(self.category)
        self.assertEqual(
            len(request.approver_ids.filtered(lambda a: a.state == "pending")),
            3,
        )
        before = len(request.message_ids)

        escalated = request._escalate_to_manager()

        self.assertEqual(
            len(request.message_ids) - before,
            1,
            "Three approvers resolving to one contact must produce one "
            "notice, not three.",
        )
        self.assertEqual(escalated, 1, "The return value counts MANAGERS.")

    def test_the_single_notice_names_every_approver(self):
        request = self._prepare_request(self.category)
        before = request.message_ids

        request._escalate_to_manager()

        body = (request.message_ids - before).body
        for user in (self.approver_1, self.approver_2, self.third_approver):
            self.assertIn(
                user.name,
                body,
                "Collapsing the notices must not lose who is being chased.",
            )

    def test_no_manager_means_no_escalation_and_no_flag(self):
        category = self._make_category(
            name="Fan-out no contact",
            approvers=[(self.approver_1, False, 10)],
        )
        isolate_group_approval_manager(self.env)
        request = self._prepare_request(category)

        self.assertEqual(request._escalate_to_manager(), 0)
        self.assertFalse(
            request.escalated_to_manager,
            "escalated_to_manager must stay False when nothing went out, "
            "or the cron will never retry.",
        )

    def test_targets_resolve_in_one_pass(self):
        request = self._prepare_request(self.category)

        by_manager, unescalated = request._resolve_escalation_targets()

        self.assertEqual(list(by_manager), [self.escalation_contact])
        self.assertEqual(len(by_manager[self.escalation_contact]), 3)
        self.assertFalse(unescalated)

    def test_default_escalation_manager_is_memoised(self):
        request = self._prepare_request(
            self._make_category(
                name="Fan-out generic",
                approvers=[(self.approver_1, False, 10)],
            ),
        )
        self.env.flush_all()
        self.env.cr.cache.pop("approval_default_escalation_manager", None)

        with patch.object(
            type(self.env["res.users"]),
            "search",
            side_effect=self.env["res.users"].search,
            autospec=False,
        ) as spy:
            for _ in range(5):
                request._get_default_escalation_manager()

        self.assertEqual(
            spy.call_count,
            1,
            "Repeated lookups within one transaction must hit the cache.",
        )


@tagged("post_install", "-at_install")
class TestEscalationManagerCacheInvalidation(ApprovalCommon):
    def setUp(self):
        super().setUp()
        isolate_group_approval_manager(self.env, keep=self.manager_user)
        self.category = self._make_category(
            name="Escalation Memo",
            approvers=[(self.approver_1, False, 10)],
        )
        self.request = self._prepare_request(self.category)

    def test_moving_the_group_between_users_is_reflected(self):
        self.assertEqual(
            self.request._get_default_escalation_manager(),
            self.manager_user,
        )

        newcomer = self.env["res.users"].create(
            {
                "name": "Newly Appointed",
                "login": "escalation_memo_newcomer",
                "email": "memo_newcomer@test.com",
            },
        )
        self.manager_user.write(
            {"group_ids": [(3, self.env.ref("approval.group_approval_manager").id)]},
        )
        newcomer.write(
            {"group_ids": [(4, self.env.ref("approval.group_approval_manager").id)]},
        )

        self.assertEqual(
            self.request._get_default_escalation_manager(),
            newcomer,
            "Revoking and granting the manager group in this transaction "
            "must be reflected in the escalation target.",
        )

    def test_archiving_the_manager_invalidates_the_memo(self):
        self.assertEqual(
            self.request._get_default_escalation_manager(),
            self.manager_user,
        )

        self.manager_user.write({"active": False})

        self.assertFalse(
            self.request._get_default_escalation_manager(),
            "An archived manager is not an escalation target, and the memo "
            "must be dropped on an 'active' write.",
        )

    def test_group_side_membership_change_invalidates_the_memo(self):
        self.assertEqual(
            self.request._get_default_escalation_manager(),
            self.manager_user,
        )

        group = self.env.ref("approval.group_approval_manager")
        group.write({"user_ids": [(3, self.manager_user.id)]})

        self.assertFalse(
            self.request._get_default_escalation_manager(),
            "Removing the only manager through the GROUP must invalidate "
            "the memo too, not just a write on res.users.",
        )
