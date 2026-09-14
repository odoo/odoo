from ast import literal_eval
from datetime import datetime, timedelta

from freezegun import freeze_time
from lxml import etree

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.approval.tests.common import ApprovalCommon, pool_step


@tagged("post_install", "-at_install")
class TestApprovalDashboard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.ApprovalRequest = cls.env["approval.request"]
        cls.ApprovalCategory = cls.env["approval.category"]
        cls.ApprovalDashboard = cls.env["approval.dashboard"]
        cls.ResUsers = cls.env["res.users"]

        cls.approver1 = cls.ResUsers.create(
            {
                "name": "Approver 1",
                "login": "dashboard_approver_1",
                "email": "approver1@test.com",
            }
        )
        cls.approver2 = cls.ResUsers.create(
            {
                "name": "Approver 2",
                "login": "dashboard_approver_2",
                "email": "approver2@test.com",
            }
        )

        cls.category = cls.ApprovalCategory.create(
            {
                "sequence_code": "SCDASH1",
                "name": "Test Category",
                "approval_minimum": 1,
                "step_ids": pool_step([(cls.approver1.id, True, 1)], minimum=1),
            }
        )

    def test_dashboard_is_a_transient_view(self):
        dashboard = self.ApprovalDashboard.get_dashboard()
        self.assertTrue(dashboard.exists(), "Dashboard should be created")
        self.assertTrue(
            self.ApprovalDashboard._transient,
            "The dashboard holds computed figures only; it is a transient "
            "record, not a table with history.",
        )

    def test_today_stats_empty(self):
        dashboard = self.ApprovalDashboard.get_dashboard()

        self.assertGreaterEqual(dashboard.submitted_today, 0)
        self.assertGreaterEqual(dashboard.approved_today, 0)
        self.assertGreaterEqual(dashboard.refused_today, 0)
        self.assertGreaterEqual(dashboard.pending_today, 0)
        self.assertGreaterEqual(dashboard.avg_response_time_hours, 0.0)

    def test_today_stats_with_requests(self):
        dashboard = self.ApprovalDashboard.get_dashboard()
        baseline_submitted = dashboard.submitted_today
        baseline_approved = dashboard.approved_today
        baseline_pending = dashboard.pending_today

        request1 = self.ApprovalRequest.create(
            {
                "name": "Test Request 1",
                "category_id": self.category.id,
                "request_owner_id": self.env.user.id,
            }
        )
        request1.action_confirm()
        self.assertTrue(request1.approver_ids)

        dashboard.invalidate_recordset()
        self.assertEqual(dashboard.submitted_today, baseline_submitted + 1)
        self.assertEqual(dashboard.pending_today, baseline_pending + 1)

        today_start = fields.Datetime.to_datetime(fields.Date.context_today(self))
        request1.sudo().write({"date_confirmed": today_start})

        approver = request1.approver_ids[0]
        approver.with_user(self.approver1).with_context(
            skip_wizard=True
        ).action_approve()

        request1.invalidate_recordset()
        self.env.flush_all()
        dashboard.invalidate_recordset()

        self.assertEqual(dashboard.approved_today, baseline_approved + 1)

    def test_trend_analysis_no_data(self):
        dashboard = self.ApprovalDashboard.get_dashboard()

        self.assertIsInstance(dashboard.trend_7days, float)
        self.assertIsInstance(dashboard.trend_30days, float)

    def test_trend_analysis_increasing(self):
        dashboard = self.ApprovalDashboard.get_dashboard()
        baseline_trend = dashboard.trend_7days

        last_week_date = fields.Datetime.now() - timedelta(days=10)
        for i in range(2):
            request = self.ApprovalRequest.create(
                {
                    "name": f"Last Week Request {i}",
                    "category_id": self.category.id,
                    "request_owner_id": self.env.user.id,
                }
            )
            request.sudo().write({"date_confirmed": last_week_date})

        this_week_date = fields.Datetime.now() - timedelta(days=3)
        for i in range(4):
            request = self.ApprovalRequest.create(
                {
                    "name": f"This Week Request {i}",
                    "category_id": self.category.id,
                    "request_owner_id": self.env.user.id,
                }
            )
            request.sudo().write({"date_confirmed": this_week_date})

        dashboard.invalidate_recordset()

        self.assertGreaterEqual(
            dashboard.trend_7days,
            baseline_trend,
            "Trend should increase when this-week volume exceeds last-week",
        )

    def test_bottleneck_detection_slowest_category(self):
        category2 = self.ApprovalCategory.create(
            {
                "sequence_code": "SCDASH2",
                "name": "Fast Category",
                "approval_minimum": 1,
                "step_ids": pool_step([(self.approver2.id, True, 1)], minimum=1),
            }
        )

        request1 = self.ApprovalRequest.create(
            {
                "name": "Slow Request",
                "category_id": self.category.id,
                "request_owner_id": self.env.user.id,
            }
        )
        request1.action_confirm()
        self.assertTrue(request1.approver_ids, "Should have approvers")

        five_hours_ago = fields.Datetime.now() - timedelta(hours=5)
        request1.sudo().write({"date_confirmed": five_hours_ago})
        request1.approver_ids[0].with_user(self.approver1).with_context(
            skip_wizard=True
        ).action_approve()

        request2 = self.ApprovalRequest.create(
            {
                "name": "Fast Request",
                "category_id": category2.id,
                "request_owner_id": self.env.user.id,
            }
        )
        request2.action_confirm()
        self.assertTrue(request2.approver_ids, "Should have approvers")

        one_hour_ago = fields.Datetime.now() - timedelta(hours=1)
        request2.sudo().write({"date_confirmed": one_hour_ago})
        request2.approver_ids[0].with_user(self.approver2).with_context(
            skip_wizard=True
        ).action_approve()

        self.env.flush_all()
        self.env.invalidate_all()

        dashboard = self.ApprovalDashboard.get_dashboard()
        dashboard.invalidate_recordset()

        self.assertGreater(
            dashboard.slowest_category_hours,
            0,
            "Slowest category time should be > 0",
        )

    def test_bottleneck_detection_overloaded_approver(self):
        for i in range(5):
            request = self.ApprovalRequest.create(
                {
                    "name": f"Pending Request {i}",
                    "category_id": self.category.id,
                    "request_owner_id": self.env.user.id,
                }
            )
            request.action_confirm()

        self.env.flush_all()
        self.env.invalidate_all()

        dashboard = self.ApprovalDashboard.get_dashboard()
        dashboard.invalidate_recordset()

        self.assertGreaterEqual(
            dashboard.most_pending_count,
            5,
            "Most overloaded approver should have at least 5 pending",
        )

    def test_all_time_stats(self):
        for i in range(10):
            request = self.ApprovalRequest.create(
                {
                    "name": f"Request {i}",
                    "category_id": self.category.id,
                    "request_owner_id": self.env.user.id,
                }
            )
            request.action_confirm()

            hours_ago = fields.Datetime.now() - timedelta(hours=i + 1)
            request.sudo().write({"date_confirmed": hours_ago})

            if i < 7:
                request.approver_ids[0].with_user(self.approver1).with_context(
                    skip_wizard=True
                ).action_approve()
            else:
                request.approver_ids[0].with_user(self.approver1).with_context(
                    skip_wizard=True
                ).action_refuse()

        self.env.flush_all()

        dashboard = self.ApprovalDashboard.get_dashboard()
        dashboard.invalidate_recordset()

        self.assertGreaterEqual(
            dashboard.total_requests_all_time,
            10,
            "Total requests should include at least the 10 we just created",
        )
        self.assertGreater(
            dashboard.overall_approval_rate,
            0,
            "Approval rate should be > 0 with approved requests",
        )
        self.assertGreater(
            dashboard.avg_approval_time_all_time,
            0,
            "Average approval time should be > 0",
        )

    def test_dashboard_actions(self):
        request = self.ApprovalRequest.create(
            {
                "name": "Test Request",
                "category_id": self.category.id,
                "request_owner_id": self.env.user.id,
            }
        )
        request.action_confirm()
        self.assertTrue(request.approver_ids, "Should have approvers")

        two_hours_ago = fields.Datetime.now() - timedelta(hours=2)
        request.sudo().write({"date_confirmed": two_hours_ago})
        request.approver_ids.sudo().write({"pending_since": two_hours_ago})

        request.approver_ids[0].with_user(self.approver1).with_context(
            skip_wizard=True
        ).action_approve()

        self.env.flush_all()
        self.env.invalidate_all()

        dashboard = self.ApprovalDashboard.get_dashboard()
        dashboard.invalidate_recordset()

        action = dashboard.action_view_slowest_category()
        self.assertEqual(
            action["res_model"],
            "approval.request",
            "Should open approval.request",
        )

        action = dashboard.action_view_slowest_approver()
        self.assertEqual(
            action["res_model"],
            "approval.approver",
            "Should open approval.approver",
        )

        action = dashboard.action_refresh()
        self.assertEqual(
            action["type"],
            "ir.actions.client",
            "Should trigger client reload",
        )

    def test_dashboard_refresh(self):
        dashboard = self.ApprovalDashboard.get_dashboard()
        initial_refresh = dashboard.last_refresh

        dashboard.invalidate_recordset()
        dashboard._compute_last_refresh()

        self.assertGreaterEqual(
            dashboard.last_refresh,
            initial_refresh,
            "Last refresh should update",
        )

    def test_trend_display_formatting(self):
        fmt = self.ApprovalDashboard._format_trend_display

        self.assertEqual(fmt(50.0, 50.0), "↑ 50.0%")
        self.assertEqual(fmt(-30.0, 30.0), "↓ 30.0%")
        self.assertEqual(fmt(0.0, "0.0"), "→ 0.0")
        self.assertEqual(fmt(100.0, "NEW"), "↑ NEW")


@tagged("post_install", "-at_install")
class TestDashboardAuditRegressions(ApprovalCommon):
    def test_local_day_start_utc_matches_tz_offset(self):
        dashboard = self.env["approval.dashboard"].with_context(tz="Etc/GMT+6")
        with freeze_time("2026-07-03 12:00:00"):
            local_start = dashboard._local_day_start_utc()
        self.assertEqual(
            local_start,
            datetime(2026, 7, 3, 6, 0, 0),
            "Local midnight (UTC-6) on the 3rd is 06:00 UTC on the 3rd — "
            "reinterpreting the local date as a UTC timestamp would "
            "wrongly give 00:00 UTC instead.",
        )

    def test_velocity_excludes_boundary_request_from_wrong_local_day(self):
        category = self._make_category(approvers=[self.approver_1])
        tz_env = self.env(context={**self.env.context, "tz": "Etc/GMT+6"})
        dashboard = tz_env["approval.dashboard"].get_dashboard()

        with freeze_time("2026-07-10 12:00:00"):
            dashboard.invalidate_recordset()
            baseline_7d = dashboard.requests_per_day_7d

        with freeze_time("2026-07-03 03:00:00"):
            request = self._prepare_request(category, confirm=False)
            request.action_confirm()
        self.assertEqual(request.date_confirmed, datetime(2026, 7, 3, 3, 0, 0))

        with freeze_time("2026-07-10 12:00:00"):
            dashboard.invalidate_recordset()
            after_7d = dashboard.requests_per_day_7d

        self.assertEqual(
            after_7d,
            baseline_7d,
            "A request confirmed at local July 2 (UTC-6) must not shift "
            "the 7-day window measured from local July 10 — it's 8 "
            "local days old, so the count must be unchanged.",
        )

    def test_my_pending_urgent_count_excludes_high_priority(self):
        category = self._make_category(approvers=[self.approver_1])
        self._prepare_request(category, priority="2")
        dashboard = (
            self.env["approval.dashboard"]
            .with_user(
                self.approver_1,
            )
            .sudo()
            .get_dashboard()
        )
        self.assertEqual(dashboard.my_pending_urgent_count, 0)

    def test_my_pending_urgent_count_includes_urgent_priority(self):
        category = self._make_category(approvers=[self.approver_1])
        self._prepare_request(category, priority="3")
        dashboard = (
            self.env["approval.dashboard"]
            .with_user(
                self.approver_1,
            )
            .sudo()
            .get_dashboard()
        )
        self.assertEqual(dashboard.my_pending_urgent_count, 1)


@tagged("post_install", "-at_install")
class TestUrgentMeansTheSameEverywhere(ApprovalCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = cls._make_category(
            name="Priority Words",
            approvers=[(cls.approver_1, False, 10)],
        )
        for priority, count in (("3", 2), ("2", 3), ("1", 4)):
            for _ in range(count):
                cls._prepare_request(cls.category, priority=priority)

    def _filter_domain(self, filter_name):
        arch = etree.fromstring(
            self.env.ref("approval.view_approval_search_search").arch_db.encode(),
        )
        for node in arch.iter("filter"):
            if node.get("name") == filter_name:
                return literal_eval(node.get("domain")), node.get("string")
        raise AssertionError(f"filter {filter_name} not found in the search view")

    def _count(self, filter_name):
        domain, label = self._filter_domain(filter_name)
        scope = [("category_id", "=", self.category.id)]
        return self.env["approval.request"].search_count(domain + scope), label

    def test_the_strict_urgent_filter_matches_the_dashboard_kpi(self):
        count, label = self._count("filter_urgent_only")
        self.assertEqual(label, "Urgent")
        self.assertEqual(
            count,
            2,
            "The filter labelled 'Urgent' must select priority 3 only — "
            "the same rule the dashboard's urgent KPI applies.",
        )

    def test_the_broad_filter_says_that_it_is_broad(self):
        count, label = self._count("filter_urgent")
        self.assertEqual(
            label,
            "High & Urgent",
            "A filter selecting priority 2 AND 3 must not be labelled "
            "'Urgent' — that is the bug this pins.",
        )
        self.assertEqual(count, 5)

    def test_the_dashboard_kpi_counts_urgent_strictly(self):
        request = self._prepare_request(self.category, priority="3", confirm=False)
        request.action_confirm()
        strict_count, _label = self._count("filter_urgent_only")

        dashboard = self.env["approval.dashboard"].get_dashboard()
        dashboard.invalidate_recordset()
        urgent_domain, _ = self._filter_domain("filter_urgent_only")
        self.assertIn(("priority", "=", "3"), urgent_domain)
        self.assertEqual(strict_count, 3)


@tagged("post_install", "-at_install")
class TestDashboardContextDependencies(ApprovalCommon):
    def _reaches_accessible(self, dashboard, method, seen=None):
        seen = seen if seen is not None else set()
        if method in seen:
            return False
        seen.add(method)
        names = method.__code__.co_names
        if "_accessible" in names:
            return True
        return any(
            self._reaches_accessible(dashboard, called, seen)
            for called in (
                getattr(type(dashboard), name, None)
                for name in names
                if name.startswith("_")
            )
            if callable(called) and hasattr(called, "__code__")
        )

    def test_every_access_scoped_compute_declares_the_context(self):
        dashboard = self.env["approval.dashboard"]
        offenders = []
        for name, field in dashboard._fields.items():
            compute = field.compute
            if not isinstance(compute, str):
                continue
            method = getattr(type(dashboard), compute, None)
            if method is None or not self._reaches_accessible(dashboard, method):
                continue
            depends = getattr(method, "_depends_context", ())
            missing = {"uid", "allowed_company_ids"} - set(depends)
            if missing:
                offenders.append((name, compute, sorted(missing)))
        self.assertFalse(
            offenders,
            "these computes resolve access per user and company but do not "
            "declare it in depends_context: %s" % offenders,
        )
