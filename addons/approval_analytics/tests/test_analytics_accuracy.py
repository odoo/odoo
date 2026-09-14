from datetime import timedelta

from freezegun import freeze_time

from odoo import fields
from odoo.tests import common, tagged

from odoo.addons.approval.tests.common import ApprovalCommon, add_category_approver


@tagged("post_install", "-at_install")
class TestAnalyticsAccuracy(common.TransactionCase):
    def setUp(self):
        super().setUp()

        self.admin_user = self.env.ref("base.user_admin")
        self.approver1 = self.env["res.users"].create(
            {
                "name": "Approver 1",
                "login": "approver1_analytics",
                "email": "approver1_analytics@test.com",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        self.approver2 = self.env["res.users"].create(
            {
                "name": "Approver 2",
                "login": "approver2_analytics",
                "email": "approver2_analytics@test.com",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )

        self.category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0001",
                "name": "Test Analytics Category",
                "approval_minimum": 1,
            }
        )

        add_category_approver(self.category, self.approver1, required=True)

    def _create_and_process_request(self, state, confirmed_date, decision_date=None):
        request = self.env["approval.request"].create(
            {
                "name": f"Test Request {state}",
                "request_owner_id": self.admin_user.id,
                "category_id": self.category.id,
            }
        )

        with freeze_time(confirmed_date):
            request.action_confirm()

        if state in ("approved", "refused"):
            approver = request.approver_ids.filtered(
                lambda a: a.user_id == self.approver1
            )
            if state == "approved":
                approver.with_user(self.approver1).with_context(
                    skip_wizard=True
                ).action_approve()
            else:
                approver.with_user(self.approver1).with_context(
                    skip_wizard=True
                ).action_refuse()

        elif state == "cascade_refused":
            request._refuse_cascade()

        self.env.flush_all()

        if state in ("approved", "refused"):
            decision_dt = decision_date or confirmed_date
            self.env.cr.execute(
                """
                UPDATE approval_request
                SET date_approval_granted = %s, write_date = %s
                WHERE id = %s AND state = 'approved'
                """,
                [decision_dt, decision_dt, request.id],
            )
            self.env.cr.execute(
                """
                UPDATE approval_request
                SET date_refused = %s, write_date = %s
                WHERE id = %s AND state = 'refused'
                """,
                [decision_dt, decision_dt, request.id],
            )
            self.env.cr.execute(
                "UPDATE approval_approver "
                "SET write_date = %s, decision_date = %s WHERE id = %s",
                [decision_dt, decision_dt, approver.id],
            )
            request.invalidate_recordset()
            approver.invalidate_recordset()
        elif state == "cascade_refused":
            decision_dt = decision_date or confirmed_date
            self.env.cr.execute(
                """
                UPDATE approval_request
                SET date_refused = %s, write_date = %s
                WHERE id = %s AND state = 'refused'
                """,
                [decision_dt, decision_dt, request.id],
            )
            request.invalidate_recordset()

        return request

    def test_approval_metrics_approval_rate_calculation(self):
        with freeze_time("2025-10-01 10:00:00"):
            confirmed = fields.Datetime.now()

        self._create_and_process_request("approved", confirmed)
        self._create_and_process_request("approved", confirmed)
        self._create_and_process_request("approved", confirmed)
        self._create_and_process_request("refused", confirmed)
        self._create_and_process_request("pending", confirmed)

        metrics = self.env["approval.metrics"].search(
            [("category_id", "=", self.category.id)]
        )

        self.assertEqual(metrics.total_requests, 5, "Should count all requests")
        self.assertEqual(metrics.approved_count, 3, "Should count 3 approved")
        self.assertEqual(metrics.rejected_count, 1, "Should count 1 refused")
        self.assertEqual(metrics.pending_count, 1, "Should count 1 pending")

        self.assertAlmostEqual(
            metrics.approval_rate,
            75.0,
            places=1,
            msg="Approval rate should be 75% (3 approved / 4 decided, "
            "excluding the still-pending request)",
        )

    def test_approval_metrics_average_time_calculation(self):
        with freeze_time("2025-10-01 10:00:00"):
            confirmed = fields.Datetime.now()

        decision1 = confirmed + timedelta(hours=2)
        self._create_and_process_request("approved", confirmed, decision1)

        decision2 = confirmed + timedelta(hours=4)
        self._create_and_process_request("approved", confirmed, decision2)

        decision3 = confirmed + timedelta(hours=6)
        self._create_and_process_request("approved", confirmed, decision3)

        metrics = self.env["approval.metrics"].search(
            [("category_id", "=", self.category.id)]
        )

        self.assertAlmostEqual(
            metrics.avg_approval_hours,
            4.0,
            places=1,
            msg="Average approval time should be 4 hours",
        )

    def test_approval_metrics_median_time_calculation(self):
        with freeze_time("2025-10-01 10:00:00"):
            confirmed = fields.Datetime.now()

        for hours in [1, 3, 5, 7, 9]:
            decision = confirmed + timedelta(hours=hours)
            self._create_and_process_request("approved", confirmed, decision)

        metrics = self.env["approval.metrics"].search(
            [("category_id", "=", self.category.id)]
        )

        self.assertAlmostEqual(
            metrics.median_approval_hours,
            5.0,
            places=1,
            msg="Median approval time should be 5 hours",
        )

    def test_approval_metrics_excludes_new_state_requests(self):
        with freeze_time("2025-10-01 10:00:00"):
            confirmed = fields.Datetime.now()

        self._create_and_process_request("approved", confirmed)

        self.env["approval.request"].create(
            {
                "name": "New Request",
                "request_owner_id": self.admin_user.id,
                "category_id": self.category.id,
            }
        )

        metrics = self.env["approval.metrics"].search(
            [("category_id", "=", self.category.id)]
        )

        self.assertEqual(
            metrics.total_requests,
            1,
            "Should exclude 'new' state requests from metrics",
        )

    def test_metrics_counts_cascade_refused_but_performance_excludes_it(self):
        with freeze_time("2025-10-01 10:00:00"):
            confirmed = fields.Datetime.now()

        request = self._create_and_process_request("cascade_refused", confirmed)
        self.assertEqual(request.state, "refused")
        approver = request.approver_ids.filtered(lambda a: a.user_id == self.approver1)
        self.assertFalse(
            approver.decision_date,
            "A cascade refusal must not stamp decision_date — no "
            "approver personally decided.",
        )

        metrics = self.env["approval.metrics"].search(
            [("category_id", "=", self.category.id)]
        )
        self.assertEqual(
            metrics.rejected_count,
            1,
            "A cascade-refused request is still a real refusal and "
            "must count in approval.metrics.",
        )

        performance = self.env["approver.performance"].search(
            [("user_id", "=", self.approver1.id)]
        )
        total_approvals = performance.total_approvals if performance else 0
        refused_count = performance.refused_count if performance else 0
        self.assertEqual(
            total_approvals,
            0,
            "approver.performance must not count a decision the "
            "approver never personally made.",
        )
        self.assertEqual(refused_count, 0)

    def test_approver_performance_response_time_calculation(self):
        with freeze_time("2025-10-01 10:00:00"):
            confirmed = fields.Datetime.now()

        decision1 = confirmed + timedelta(hours=2)
        self._create_and_process_request("approved", confirmed, decision1)

        decision2 = confirmed + timedelta(hours=4)
        self._create_and_process_request("approved", confirmed, decision2)

        decision3 = confirmed + timedelta(hours=6)
        self._create_and_process_request("approved", confirmed, decision3)

        performance = self.env["approver.performance"].search(
            [("user_id", "=", self.approver1.id)]
        )

        self.assertAlmostEqual(
            performance.avg_response_hours,
            4.0,
            places=1,
            msg="Average response time should be 4 hours",
        )

    def test_approver_performance_approval_rate(self):
        with freeze_time("2025-10-01 10:00:00"):
            confirmed = fields.Datetime.now()

        for _ in range(7):
            self._create_and_process_request("approved", confirmed)

        for _ in range(3):
            self._create_and_process_request("refused", confirmed)

        performance = self.env["approver.performance"].search(
            [("user_id", "=", self.approver1.id)]
        )

        self.assertAlmostEqual(
            performance.approval_rate,
            70.0,
            places=1,
            msg="Approver approval rate should be 70%",
        )

    def test_approver_performance_counts_decisions_not_total_requests(self):
        with freeze_time("2025-10-01 10:00:00"):
            confirmed = fields.Datetime.now()

        self._create_and_process_request("approved", confirmed)
        self._create_and_process_request("approved", confirmed)
        self._create_and_process_request("refused", confirmed)
        self._create_and_process_request("pending", confirmed)
        self._create_and_process_request("pending", confirmed)

        performance = self.env["approver.performance"].search(
            [("user_id", "=", self.approver1.id)]
        )

        self.assertEqual(
            performance.total_approvals,
            3,
            "Should count only decisions (approved + refused), not pending",
        )
        self.assertEqual(performance.approved_count, 2)
        self.assertEqual(performance.refused_count, 1)

        self.assertEqual(
            performance.pending_count,
            2,
            "Should track current pending workload",
        )

    def test_approver_performance_excludes_new_state(self):
        with freeze_time("2025-10-01 10:00:00"):
            confirmed = fields.Datetime.now()

        self._create_and_process_request("approved", confirmed)

        self.env["approval.request"].create(
            {
                "name": "Unconfirmed Request",
                "request_owner_id": self.admin_user.id,
                "category_id": self.category.id,
            }
        )

        performance = self.env["approver.performance"].search(
            [("user_id", "=", self.approver1.id)]
        )

        self.assertEqual(
            performance.total_approvals,
            1,
            "Should exclude 'new' state approvers from performance",
        )

    def test_approval_metrics_with_multiple_categories(self):
        category2 = self.env["approval.category"].create(
            {
                "sequence_code": "SC0002",
                "name": "Second Category",
                "approval_minimum": 1,
            }
        )
        add_category_approver(category2, self.approver1, required=True)

        with freeze_time("2025-10-01 10:00:00"):
            confirmed = fields.Datetime.now()

        self._create_and_process_request("approved", confirmed)
        self._create_and_process_request("approved", confirmed)

        for i in range(3):
            req = self.env["approval.request"].create(
                {
                    "name": f"Category 2 Request {i}",
                    "request_owner_id": self.admin_user.id,
                    "category_id": category2.id,
                }
            )
            with freeze_time(confirmed):
                req.action_confirm()
            approver = req.approver_ids.filtered(lambda a: a.user_id == self.approver1)
            approver.with_user(self.approver1).with_context(
                skip_wizard=True
            ).action_approve()

        self.env.flush_all()

        metrics1 = self.env["approval.metrics"].search(
            [("category_id", "=", self.category.id)]
        )
        metrics2 = self.env["approval.metrics"].search(
            [("category_id", "=", category2.id)]
        )

        self.assertEqual(
            metrics1.total_requests,
            2,
            "Category 1 should have 2 requests",
        )
        self.assertEqual(
            metrics2.total_requests,
            3,
            "Category 2 should have 3 requests",
        )

    def test_a_slower_category_ranks_above_a_faster_one(self):
        category2 = self.env["approval.category"].create(
            {
                "sequence_code": "SC0003",
                "name": "Fast Category",
                "approval_minimum": 1,
            }
        )
        add_category_approver(category2, self.approver1, required=True)

        with freeze_time("2025-10-01 10:00:00"):
            confirmed = fields.Datetime.now()

        self._create_and_process_request(
            "approved", confirmed, confirmed + timedelta(hours=5)
        )

        fast = self.env["approval.request"].create(
            {
                "name": "Fast Request",
                "request_owner_id": self.admin_user.id,
                "category_id": category2.id,
            }
        )
        with freeze_time(confirmed):
            fast.action_confirm()
        approver = fast.approver_ids.filtered(lambda a: a.user_id == self.approver1)
        approver.with_user(self.approver1).with_context(
            skip_wizard=True
        ).action_approve()
        self.env.flush_all()
        decided = confirmed + timedelta(hours=1)
        self.env.cr.execute(
            "UPDATE approval_request SET date_approval_granted = %s, write_date = %s "
            "WHERE id = %s",
            [decided, decided, fast.id],
        )
        self.env.cr.execute(
            "UPDATE approval_approver SET write_date = %s, decision_date = %s "
            "WHERE id = %s",
            [decided, decided, approver.id],
        )
        fast.invalidate_recordset()

        rows = self.env["approval.metrics"].search(
            [("category_id", "in", (self.category + category2).ids)]
        )
        hours = {row.category_id: row.avg_approval_hours for row in rows}
        self.assertGreater(
            hours.get(self.category, 0.0),
            hours.get(category2, 0.0),
            "The five-hour category must rank above the one-hour category; this "
            "cross-category ranking used to be asserted at the tail of the "
            "dashboard's slowest-category test, which no longer sees this view.",
        )

    def test_approval_metrics_handles_no_approved_requests(self):
        with freeze_time("2025-10-01 10:00:00"):
            confirmed = fields.Datetime.now()

        self._create_and_process_request("pending", confirmed)
        self._create_and_process_request("refused", confirmed)

        metrics = self.env["approval.metrics"].search(
            [("category_id", "=", self.category.id)]
        )

        self.assertAlmostEqual(
            metrics.approval_rate,
            0.0,
            places=1,
            msg="Approval rate should be 0% when no approved requests",
        )

        self.assertIsNotNone(
            metrics.avg_approval_hours,
            "Avg time should handle no approved requests",
        )

    def test_approver_performance_multiple_approvers(self):
        add_category_approver(self.category, self.approver2, required=False)
        self.category.step_ids.minimum = 2

        with freeze_time("2025-10-01 10:00:00"):
            confirmed = fields.Datetime.now()

        request1 = self.env["approval.request"].create(
            {
                "name": "Request 1",
                "request_owner_id": self.admin_user.id,
                "category_id": self.category.id,
            }
        )
        with freeze_time(confirmed):
            request1.action_confirm()

        approver1_rec = request1.approver_ids.filtered(
            lambda a: a.user_id == self.approver1
        )
        approver1_rec.with_user(self.approver1).with_context(
            skip_wizard=True
        ).action_approve()

        approver2_rec = request1.approver_ids.filtered(
            lambda a: a.user_id == self.approver2
        )
        approver2_rec.with_user(self.approver2).with_context(
            skip_wizard=True
        ).action_refuse()

        self.env.flush_all()

        perf1 = self.env["approver.performance"].search(
            [("user_id", "=", self.approver1.id)]
        )
        perf2 = self.env["approver.performance"].search(
            [("user_id", "=", self.approver2.id)]
        )

        self.assertEqual(perf1.approved_count, 1, "Approver1 approved 1")
        self.assertEqual(perf1.refused_count, 0, "Approver1 refused 0")

        self.assertEqual(perf2.approved_count, 0, "Approver2 approved 0")
        self.assertEqual(perf2.refused_count, 1, "Approver2 refused 1")

    def test_sql_views_performance_with_large_dataset(self):
        with freeze_time("2025-10-01 10:00:00"):
            confirmed = fields.Datetime.now()

        for i in range(50):
            state = "approved" if i % 2 == 0 else "refused"
            decision = confirmed + timedelta(hours=(i % 10) + 1)
            self._create_and_process_request(state, confirmed, decision)

        metrics = self.env["approval.metrics"].search(
            [("category_id", "=", self.category.id)]
        )
        performance = self.env["approver.performance"].search(
            [("user_id", "=", self.approver1.id)]
        )

        self.assertEqual(
            metrics.total_requests,
            50,
            "Should handle 50 requests",
        )
        self.assertEqual(
            performance.total_approvals,
            50,
            "Should aggregate 50 decisions",
        )

        self.assertAlmostEqual(
            metrics.approval_rate,
            50.0,
            places=1,
            msg="Approval rate should be 50% with large dataset",
        )


@tagged("post_install", "-at_install")
class TestApproverResponseTimeBasis(ApprovalCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sequential = cls._make_category(
            name="Response Basis Seq",
            approvers=[(cls.approver_1, True, 10), (cls.approver_2, True, 20)],
            in_order=True,
            approval_minimum=2,
        )

    def _hours_by_user(self, users):
        self.env.invalidate_all()
        return {
            row["user_id"][0]: row["avg_response_hours"]
            for row in self.env["approver.performance"]
            .sudo()
            .search_read(
                [("user_id", "in", users.ids)],
                ["user_id", "avg_response_hours"],
            )
        }

    def test_pending_since_is_stamped_on_promotion(self):
        request = self._prepare_request(self.sequential)
        first = request.approver_ids.filtered(lambda a: a.user_id == self.approver_1)
        second = request.approver_ids.filtered(lambda a: a.user_id == self.approver_2)

        self.assertTrue(
            first.pending_since,
            "The first approver enters the decision window at confirmation.",
        )
        self.assertFalse(
            second.pending_since,
            "A waiting row has not reached its approver yet.",
        )

        request.with_user(self.approver_1).with_context(
            skip_wizard=True,
        ).action_approve()

        self.assertTrue(
            second.pending_since,
            "Promotion into 'pending' must stamp the row.",
        )
        self.assertGreaterEqual(second.pending_since, first.pending_since)

    def test_reset_to_draft_clears_the_stamp(self):
        request = self._prepare_request(self.sequential)
        request.with_user(self.approver_1).with_context(
            skip_wizard=True,
        ).action_refuse()

        request.with_user(self.manager_user).action_reset_to_draft()

        self.assertFalse(
            any(request.approver_ids.mapped("pending_since")),
            "A new cycle must time its own decision window.",
        )

    def test_later_approver_is_not_billed_for_the_earlier_one(self):
        request = self._prepare_request(self.sequential)
        first = request.approver_ids.filtered(lambda a: a.user_id == self.approver_1)
        second = request.approver_ids.filtered(lambda a: a.user_id == self.approver_2)

        now = fields.Datetime.now()
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE approval_request SET date_confirmed = %s WHERE id = %s",
            (now - timedelta(hours=100), request.id),
        )
        self.env.cr.execute(
            "UPDATE approval_approver SET pending_since = %s WHERE id = %s",
            (now - timedelta(hours=100), first.id),
        )
        request.invalidate_recordset(["date_confirmed"])

        request.with_user(self.approver_1).with_context(
            skip_wizard=True,
        ).action_approve()
        request.with_user(self.approver_2).with_context(
            skip_wizard=True,
        ).action_approve()

        self.env.cr.execute(
            "UPDATE approval_approver SET decision_date = %s, pending_since = %s "
            "WHERE id = %s",
            (now - timedelta(hours=1), now - timedelta(hours=100), first.id),
        )
        self.env.cr.execute(
            "UPDATE approval_approver SET decision_date = %s, pending_since = %s "
            "WHERE id = %s",
            (now, now - timedelta(hours=1), second.id),
        )

        hours = self._hours_by_user(self.approver_1 | self.approver_2)

        self.assertAlmostEqual(hours[self.approver_1.id], 99.0, places=1)
        self.assertAlmostEqual(
            hours[self.approver_2.id],
            1.0,
            places=1,
            msg="The second approver answered within an hour of being "
            "asked and must be scored on that, not on the request's age.",
        )

    def test_parallel_basis_is_unchanged(self):
        parallel = self._make_category(
            name="Response Basis Par",
            approvers=[(self.approver_1, True, 10), (self.approver_2, True, 10)],
            approval_minimum=2,
        )
        request = self._prepare_request(parallel)

        now = fields.Datetime.now()
        for user in (self.approver_1, self.approver_2):
            request.with_user(user).with_context(
                skip_wizard=True,
            ).action_approve()
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE approval_request SET date_confirmed = %s WHERE id = %s",
            (now - timedelta(hours=200), request.id),
        )
        self.env.cr.execute(
            "UPDATE approval_approver SET decision_date = %s, pending_since = %s "
            "WHERE request_id = %s",
            (now, now - timedelta(hours=200), request.id),
        )

        hours = self._hours_by_user(self.approver_1 | self.approver_2)

        for user in (self.approver_1, self.approver_2):
            self.assertAlmostEqual(hours[user.id], 200.0, places=1)

    def test_legacy_rows_without_a_stamp_still_score(self):
        request = self._prepare_request(self.sequential)
        first = request.approver_ids.filtered(lambda a: a.user_id == self.approver_1)
        request.with_user(self.approver_1).with_context(
            skip_wizard=True,
        ).action_approve()

        now = fields.Datetime.now()
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE approval_request SET date_confirmed = %s WHERE id = %s",
            (now - timedelta(hours=12), request.id),
        )
        self.env.cr.execute(
            "UPDATE approval_approver SET pending_since = NULL, decision_date = %s "
            "WHERE id = %s",
            (now, first.id),
        )

        hours = self._hours_by_user(self.approver_1)

        self.assertAlmostEqual(hours[self.approver_1.id], 12.0, places=1)


@tagged("post_install", "-at_install")
class TestApprovalRateCountsDecisionsOnly(ApprovalCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = cls._make_category(
            name="Rate Category",
            approvers=[(cls.approver_1, False, 10)],
        )

    def _decided(self, outcome):
        request = self._prepare_request(self.category)
        if outcome == "approved":
            request.with_user(self.approver_1).with_context(
                skip_wizard=True,
            ).action_approve()
        elif outcome == "refused":
            request.with_user(self.approver_1).with_context(
                skip_wizard=True,
            ).action_refuse()
        else:
            request.with_user(self.owner_user).action_cancel()
        return request

    def _metrics_row(self):
        self.env.flush_all()
        return self.env["approval.metrics"].search(
            [("category_id", "=", self.category.id)],
        )

    def test_cancellations_are_not_counted_against_the_rate(self):
        for _ in range(4):
            self._decided("approved")
        for _ in range(4):
            self._decided("cancelled")

        row = self._metrics_row()

        self.assertEqual(row.approved_count, 4)
        self.assertEqual(row.cancelled_count, 4)
        self.assertEqual(row.rejected_count, 0)
        self.assertEqual(
            row.approval_rate,
            100.0,
            "Four approvals and no refusal is a 100% approval rate; the "
            "four retractions are not decisions.",
        )

    def test_refusals_are_counted_against_the_rate(self):
        for _ in range(3):
            self._decided("approved")
        self._decided("refused")

        self.assertEqual(self._metrics_row().approval_rate, 75.0)

    def test_only_cancellations_leaves_the_rate_undefined(self):
        for _ in range(3):
            self._decided("cancelled")

        self.assertEqual(
            self._metrics_row().approval_rate,
            0.0,
            "With no decision at all the rate has no denominator; NULLIF "
            "yields 0 rather than dividing by the cancellations.",
        )

    def test_dashboard_rate_agrees_with_the_metrics_view(self):
        for _ in range(4):
            self._decided("approved")
        for _ in range(4):
            self._decided("cancelled")
        self._decided("refused")

        dashboard = self.env["approval.dashboard"].get_dashboard()
        dashboard.invalidate_recordset()
        row = self._metrics_row()
        self.assertEqual(row.approval_rate, 80.0)
        self.assertGreater(
            dashboard.overall_approval_rate,
            0.0,
            "The dashboard rate must be computed, not left at zero.",
        )
