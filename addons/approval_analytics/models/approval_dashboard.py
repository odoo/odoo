from datetime import UTC, datetime, time, timedelta
from typing import Any, Self

from odoo import api, fields, models
from odoo.libs.datetime import timezone
from odoo.tools import SQL

from odoo.addons.approval.models import approval_trace as trace


class ApprovalDashboard(models.TransientModel):
    _name = "approval.dashboard"
    _description = "Approval Dashboard"
    _rec_name = "name"

    name = fields.Char(
        string="Dashboard Name",
        default="Approval Dashboard",
        readonly=True,
    )
    last_refresh = fields.Datetime(
        string="Last Refreshed",
        compute="_compute_last_refresh",
    )

    pending_today = fields.Integer(
        compute="_compute_today_stats",
        help="Requests currently pending (submitted today)",
    )
    approved_today = fields.Integer(compute="_compute_today_stats")
    refused_today = fields.Integer(compute="_compute_today_stats")
    submitted_today = fields.Integer(compute="_compute_today_stats")
    avg_response_time_hours = fields.Float(
        string="Avg Response Time Today (hours)",
        compute="_compute_today_stats",
        help="Average time from submission to decision for requests resolved today",
    )

    trend_7days = fields.Float(
        string="7-Day Trend %",
        compute="_compute_trends",
        help="Percentage change in submission volume vs last week",
    )
    trend_15days = fields.Float(
        string="15-Day Trend %",
        compute="_compute_trends",
        help="Percentage change in submission volume vs previous 15 days",
    )
    trend_30days = fields.Float(
        string="30-Day Trend %",
        compute="_compute_trends",
        help="Percentage change in submission volume vs last month",
    )
    trend_7days_display = fields.Char(
        string="Week Trend",
        compute="_compute_trends",
        help="Human-readable 7-day trend with arrow",
    )
    trend_15days_display = fields.Char(
        string="15-Day Trend",
        compute="_compute_trends",
        help="Human-readable 15-day trend with arrow",
    )
    trend_30days_display = fields.Char(
        string="Month Trend",
        compute="_compute_trends",
        help="Human-readable 30-day trend with arrow",
    )

    slowest_category_id = fields.Many2one(
        comodel_name="approval.category",
        compute="_compute_bottlenecks",
        help="Category with longest average approval time",
    )
    slowest_category_hours = fields.Float(
        string="Slowest Category Time (hours)",
        compute="_compute_bottlenecks",
        help="Average approval time for slowest category",
    )
    slowest_approver_id = fields.Many2one(
        comodel_name="res.users",
        compute="_compute_bottlenecks",
        help="Approver with longest average response time",
    )
    slowest_approver_hours = fields.Float(
        string="Slowest Approver Time (hours)",
        compute="_compute_bottlenecks",
        help="Average response time for slowest approver",
    )
    most_pending_approver_id = fields.Many2one(
        comodel_name="res.users",
        string="Most Overloaded Approver",
        compute="_compute_bottlenecks",
        help="Approver with most pending requests",
    )
    most_pending_count = fields.Integer(
        string="Highest Pending Count",
        compute="_compute_bottlenecks",
        help="Number of pending requests for most overloaded approver",
    )

    total_requests_all_time = fields.Integer(
        string="Total Requests (All Time)",
        compute="_compute_all_time_stats",
        help="Total approval requests submitted since system deployment",
    )
    total_pending_all_time = fields.Integer(
        string="Total Pending (All Time)",
        compute="_compute_all_time_stats",
        help="Total requests currently pending approval",
    )
    overall_approval_rate = fields.Float(
        string="Overall Approval Rate %",
        compute="_compute_all_time_stats",
        help="Percentage of all requests that were approved",
    )
    avg_approval_time_all_time = fields.Float(
        string="Avg Approval Time (All Time, hours)",
        compute="_compute_all_time_stats",
        help="Average time from submission to approval across all requests",
    )

    my_pending_count = fields.Integer(
        string="My Pending Approvals",
        compute="_compute_user_metrics",
        help="Number of requests awaiting my approval",
    )
    my_pending_urgent_count = fields.Integer(
        string="My Urgent Pending",
        compute="_compute_user_metrics",
        help="Number of urgent requests awaiting my approval",
    )
    my_avg_response_hours = fields.Float(
        string="My Avg Response Time (hours)",
        compute="_compute_user_metrics",
        help="My average time to approve/refuse requests",
    )

    requests_per_day_7d = fields.Float(
        string="Requests/Day (7-day avg)",
        compute="_compute_velocity_metrics",
    )
    approvals_per_day_7d = fields.Float(
        string="Approvals/Day (7-day avg)",
        compute="_compute_velocity_metrics",
    )
    requests_per_day_15d = fields.Float(
        string="Requests/Day (15-day avg)",
        compute="_compute_velocity_metrics",
    )
    approvals_per_day_15d = fields.Float(
        string="Approvals/Day (15-day avg)",
        compute="_compute_velocity_metrics",
    )
    requests_per_day_30d = fields.Float(
        string="Requests/Day (30-day avg)",
        compute="_compute_velocity_metrics",
    )
    approvals_per_day_30d = fields.Float(
        string="Approvals/Day (30-day avg)",
        compute="_compute_velocity_metrics",
    )
    avg_response_hours_7d = fields.Float(
        string="Avg Response Time (7d, hours)",
        compute="_compute_velocity_metrics",
    )
    avg_response_hours_15d = fields.Float(
        string="Avg Response Time (15d, hours)",
        compute="_compute_velocity_metrics",
    )
    avg_response_hours_30d = fields.Float(
        string="Avg Response Time (30d, hours)",
        compute="_compute_velocity_metrics",
    )
    median_approval_hours = fields.Float(
        string="Median Approval Time (hours)",
        compute="_compute_velocity_metrics",
        help="Median time from submission to approval (50th percentile, last 90 days)",
    )

    def _compute_last_refresh(self) -> None:
        for dashboard in self:
            dashboard.last_refresh = fields.Datetime.now()

    def _local_tz_name(self) -> str:
        return self.env.context.get("tz") or self.env.user.tz or "UTC"

    def _local_day_start_utc(self) -> datetime:
        tz = timezone(self._local_tz_name())
        local_date = fields.Date.context_today(self)
        local_midnight = datetime.combine(local_date, time.min).replace(tzinfo=tz)
        return local_midnight.astimezone(UTC).replace(tzinfo=None)

    def _accessible(self, model_name: str, domain=()) -> SQL:
        with trace.REPORT.span("accessible_subselect", model=model_name):
            return self.env[model_name]._search(domain).subselect()

    @api.depends_context("uid", "allowed_company_ids", "tz")
    def _compute_today_stats(self) -> None:
        approval_request_model = self.env["approval.request"]

        today_start = self._local_day_start_utc()
        today_end = today_start + timedelta(days=1)

        submitted_by_state = dict(
            approval_request_model._read_group(
                [
                    ("date_confirmed", ">=", today_start),
                    ("date_confirmed", "<", today_end),
                ],
                ["state"],
                ["__count"],
            ),
        )
        submitted = sum(submitted_by_state.values())
        pending = submitted_by_state.get("pending", 0)

        decided_by_state = dict(
            approval_request_model._read_group(
                [
                    "|",
                    "&",
                    "&",
                    ("state", "=", "approved"),
                    ("date_approval_granted", ">=", today_start),
                    ("date_approval_granted", "<", today_end),
                    "&",
                    "&",
                    ("state", "=", "refused"),
                    ("date_refused", ">=", today_start),
                    ("date_refused", "<", today_end),
                ],
                ["state"],
                ["__count"],
            ),
        )
        approved = decided_by_state.get("approved", 0)
        refused = decided_by_state.get("refused", 0)

        avg_hours = self._get_avg_response_time_today_sql(
            today_start,
            today_end,
        )

        trace.REPORT.event(
            "today_stats",
            submitted=submitted,
            pending=pending,
            approved=approved,
            refused=refused,
            hours=avg_hours,
        )
        for dashboard in self:
            dashboard.submitted_today = submitted
            dashboard.approved_today = approved
            dashboard.refused_today = refused
            dashboard.pending_today = pending
            dashboard.avg_response_time_hours = avg_hours

    @api.depends_context("uid", "allowed_company_ids", "tz")
    def _compute_trends(self) -> None:
        approval_request_model = self.env["approval.request"]

        tz_name = self._local_tz_name()
        today = fields.Date.context_today(self)
        today_datetime = fields.Datetime.to_datetime(today)
        today_end = today_datetime + timedelta(days=1)

        today_end_utc = self._local_day_start_utc() + timedelta(days=1)

        daily_counts = approval_request_model.with_context(
            tz=tz_name,
        )._read_group(
            [
                ("date_confirmed", ">=", today_end_utc - timedelta(days=61)),
                ("date_confirmed", "<", today_end_utc),
            ],
            ["date_confirmed:day"],
            ["__count"],
        )

        trace.REPORT.event("trend_days", buckets=len(daily_counts), tz=tz_name)

        def count_window(start: datetime, end: datetime) -> int:
            return sum(count for day, count in daily_counts if start <= day < end)

        def get_trend(days: int) -> tuple[float, Any]:
            period_start = today_end - timedelta(days=days)
            prev_period_start = today_end - timedelta(days=days * 2)

            this_period_count = count_window(period_start, today_end)
            last_period_count = count_window(prev_period_start, period_start)

            if last_period_count > 0:
                trend = round(
                    ((this_period_count - last_period_count) / last_period_count) * 100,
                    1,
                )
                display_val = abs(trend)
                branch = "ratio"
            elif this_period_count > 0:
                trend = 100.0
                display_val = "NEW"
                branch = "new"
            else:
                trend = 0.0
                display_val = "0.0"
                branch = "empty"

            trace.REPORT.event(
                "trend",
                days=days,
                branch=branch,
                this_period=this_period_count,
                last_period=last_period_count,
                trend=trend,
            )
            return trend, display_val

        trend_7, trend_7_display_val = get_trend(7)
        trend_15, trend_15_display_val = get_trend(15)
        trend_30, trend_30_display_val = get_trend(30)

        trend_7_display = self._format_trend_display(trend_7, trend_7_display_val)
        trend_15_display = self._format_trend_display(trend_15, trend_15_display_val)
        trend_30_display = self._format_trend_display(trend_30, trend_30_display_val)

        for dashboard in self:
            dashboard.trend_7days = trend_7
            dashboard.trend_15days = trend_15
            dashboard.trend_30days = trend_30
            dashboard.trend_7days_display = trend_7_display
            dashboard.trend_15days_display = trend_15_display
            dashboard.trend_30days_display = trend_30_display

    @staticmethod
    def _format_trend_display(trend: float, display_val: Any) -> str:
        arrow = "↑" if trend > 0 else "↓" if trend < 0 else "→"
        if isinstance(display_val, (int, float)):
            return f"{arrow} {display_val}%"
        return f"{arrow} {display_val}"

    @api.depends_context("uid", "allowed_company_ids", "tz")
    def _compute_bottlenecks(self) -> None:
        metrics_model = self.env["approval.metrics"]
        performance_model = self.env["approver.performance"]

        slowest_category = metrics_model.search_read(
            [
                ("avg_approval_hours", ">", 0),
            ],
            ["category_id", "avg_approval_hours"],
            order="avg_approval_hours desc",
            limit=1,
        )

        slowest_approver = next(
            iter(
                performance_model.search_read(
                    [("avg_response_hours", ">", 0)],
                    ["user_id", "avg_response_hours"],
                    order="avg_response_hours desc",
                    limit=1,
                ),
            ),
            None,
        )

        most_pending = next(
            iter(
                performance_model.search_read(
                    [("pending_count", ">", 0)],
                    ["user_id", "pending_count"],
                    order="pending_count desc",
                    limit=1,
                ),
            ),
            None,
        )

        trace.REPORT.event(
            "bottlenecks",
            slowest_category=slowest_category[0]["id"] if slowest_category else None,
            slowest_approver=slowest_approver["id"] if slowest_approver else None,
            most_pending=most_pending["id"] if most_pending else None,
        )
        for dashboard in self:
            if slowest_category:
                row = slowest_category[0]
                dashboard.slowest_category_id = (
                    row["category_id"] and row["category_id"][0]
                )
                dashboard.slowest_category_hours = row["avg_approval_hours"]
            else:
                dashboard.slowest_category_id = False
                dashboard.slowest_category_hours = 0.0

            if slowest_approver:
                dashboard.slowest_approver_id = (
                    slowest_approver["user_id"] and slowest_approver["user_id"][0]
                )
                dashboard.slowest_approver_hours = slowest_approver[
                    "avg_response_hours"
                ]
            else:
                dashboard.slowest_approver_id = False
                dashboard.slowest_approver_hours = 0.0

            if most_pending:
                dashboard.most_pending_approver_id = (
                    most_pending["user_id"] and most_pending["user_id"][0]
                )
                dashboard.most_pending_count = most_pending["pending_count"]
            else:
                dashboard.most_pending_approver_id = False
                dashboard.most_pending_count = 0

    @api.depends_context("uid", "allowed_company_ids", "tz")
    def _compute_all_time_stats(self) -> None:
        approval_request_model = self.env["approval.request"]

        state_counts = dict(
            approval_request_model._read_group(
                [("state", "!=", "new")],
                ["state"],
                ["__count"],
            ),
        )

        total = sum(state_counts.values())
        pending = state_counts.get("pending", 0)
        approved = state_counts.get("approved", 0)

        total_decided = sum(
            state_counts.get(state, 0)
            for state in approval_request_model._DECISION_STATES
        )

        approval_rate = (
            round((approved / total_decided * 100), 2) if total_decided > 0 else 0.0
        )

        with trace.REPORT.span("all_time_avg_hours") as span:
            self.env.cr.execute(
                SQL(
                    """
                    SELECT AVG(EXTRACT(EPOCH FROM
                        (date_approval_granted - date_confirmed)
                    ) / 3600)
                    FROM approval_request
                    WHERE state = 'approved'
                        AND date_confirmed IS NOT NULL
                        AND date_approval_granted IS NOT NULL
                        AND id IN %s
                    """,
                    self._accessible("approval.request"),
                ),
            )
            row = self.env.cr.fetchone()
            avg_time = round(row[0], 2) if row and row[0] else 0.0
            span["hours"] = avg_time
        trace.REPORT.event(
            "all_time_stats",
            states=len(state_counts),
            total=total,
            pending=pending,
            decided=total_decided,
            rate=approval_rate,
        )

        for dashboard in self:
            dashboard.total_requests_all_time = total
            dashboard.total_pending_all_time = pending
            dashboard.overall_approval_rate = approval_rate
            dashboard.avg_approval_time_all_time = avg_time

    @api.depends_context("uid", "allowed_company_ids", "tz")
    def _compute_user_metrics(self) -> None:
        request_model = self.env["approval.request"]

        current_user = self.env.user

        pending_domain = request_model._get_domain_pending_review(current_user)
        my_pending = request_model.search_count(pending_domain)

        my_urgent = request_model.search_count(
            pending_domain + [("priority", "=", "3")],
        )

        with trace.REPORT.span("my_avg_response_hours", uid=current_user.id) as span:
            self.env.cr.execute(
                SQL(
                    """
                    SELECT AVG(
                        EXTRACT(EPOCH FROM (
                            a.decision_date
                            - COALESCE(a.pending_since, ar.date_confirmed)
                        )) / 3600
                    )
                    FROM approval_approver a
                    JOIN approval_request ar ON ar.id = a.request_id
                    WHERE COALESCE(a.decided_by_user_id, a.user_id) = %s
                        AND a.decision_date IS NOT NULL
                        AND COALESCE(a.pending_since, ar.date_confirmed) IS NOT NULL
                        AND a.id IN %s
                    """,
                    current_user.id,
                    self._accessible("approval.approver"),
                ),
            )
            row = self.env.cr.fetchone()
            avg_response = round(row[0], 2) if row and row[0] else 0.0
            span["hours"] = avg_response
        trace.REPORT.event(
            "user_metrics",
            uid=current_user.id,
            pending=my_pending,
            urgent=my_urgent,
            hours=avg_response,
        )

        for dashboard in self:
            dashboard.my_pending_count = my_pending
            dashboard.my_pending_urgent_count = my_urgent
            dashboard.my_avg_response_hours = avg_response

    @api.depends_context("uid", "allowed_company_ids", "tz")
    def _compute_velocity_metrics(self) -> None:
        approval_request_model = self.env["approval.request"]

        tz_name = self._local_tz_name()
        today_datetime = fields.Datetime.to_datetime(
            fields.Date.context_today(self),
        )
        today_utc = self._local_day_start_utc()
        today_end_utc = today_utc + timedelta(days=1)

        days_7_ago = today_datetime - timedelta(days=6)
        days_15_ago = today_datetime - timedelta(days=14)
        days_7_ago_utc = today_utc - timedelta(days=6)
        days_15_ago_utc = today_utc - timedelta(days=14)
        days_30_ago_utc = today_utc - timedelta(days=29)

        request_days = approval_request_model.with_context(
            tz=tz_name,
        )._read_group(
            [
                ("date_confirmed", ">=", days_30_ago_utc),
                ("date_confirmed", "<", today_end_utc),
            ],
            ["date_confirmed:day"],
            ["__count"],
        )

        requests_7d = sum(count for day, count in request_days if day >= days_7_ago)
        requests_per_day_7d = round(requests_7d / 7, 2)

        requests_15d = sum(count for day, count in request_days if day >= days_15_ago)
        requests_per_day_15d = round(requests_15d / 15, 2)

        requests_30d = sum(count for _day, count in request_days)
        requests_per_day_30d = round(requests_30d / 30, 2)

        approval_days = approval_request_model.with_context(
            tz=tz_name,
        )._read_group(
            [
                ("state", "=", "approved"),
                ("date_approval_granted", ">=", days_30_ago_utc),
                ("date_approval_granted", "<", today_end_utc),
            ],
            ["date_approval_granted:day"],
            ["__count"],
        )

        approvals_7d = sum(count for day, count in approval_days if day >= days_7_ago)
        approvals_per_day_7d = round(approvals_7d / 7, 2)

        approvals_15d = sum(count for day, count in approval_days if day >= days_15_ago)
        approvals_per_day_15d = round(approvals_15d / 15, 2)

        approvals_30d = sum(count for _day, count in approval_days)
        approvals_per_day_30d = round(approvals_30d / 30, 2)

        avg_7d = self._get_avg_response_time_sql(days_7_ago_utc, today_end_utc)
        avg_15d = self._get_avg_response_time_sql(days_15_ago_utc, today_end_utc)
        avg_30d = self._get_avg_response_time_sql(days_30_ago_utc, today_end_utc)

        ninety_days_ago = today_utc - timedelta(days=90)

        with trace.REPORT.span("median_approval_hours", days=90) as span:
            self.env.cr.execute(
                SQL(
                    """
                    SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY
                        EXTRACT(EPOCH FROM (date_approval_granted - date_confirmed))
                        / 3600
                    ) AS median_hours
                    FROM approval_request
                    WHERE state = 'approved'
                        AND date_confirmed IS NOT NULL
                        AND date_approval_granted IS NOT NULL
                        AND date_approval_granted >= %s
                        AND id IN %s
                    """,
                    ninety_days_ago,
                    self._accessible("approval.request"),
                ),
            )

            result = self.env.cr.fetchone()
            median_hours = round(result[0], 2) if result and result[0] else 0.0
            span["hours"] = median_hours
        trace.REPORT.event(
            "velocity_metrics",
            request_days=len(request_days),
            approval_days=len(approval_days),
            requests_30d=requests_30d,
            approvals_30d=approvals_30d,
            median=median_hours,
        )

        for dashboard in self:
            dashboard.requests_per_day_7d = requests_per_day_7d
            dashboard.approvals_per_day_7d = approvals_per_day_7d
            dashboard.requests_per_day_15d = requests_per_day_15d
            dashboard.approvals_per_day_15d = approvals_per_day_15d
            dashboard.requests_per_day_30d = requests_per_day_30d
            dashboard.approvals_per_day_30d = approvals_per_day_30d
            dashboard.avg_response_hours_7d = avg_7d
            dashboard.avg_response_hours_15d = avg_15d
            dashboard.avg_response_hours_30d = avg_30d
            dashboard.median_approval_hours = median_hours

    def _get_avg_response_time_sql(self, start_date: Any, end_date: Any) -> float:
        self.env.cr.execute(
            SQL(
                """
                SELECT AVG(EXTRACT(EPOCH FROM (
                    CASE
                        WHEN state = 'approved'
                            THEN date_approval_granted - date_confirmed
                        WHEN state = 'refused' THEN date_refused - date_confirmed
                    END
                )) / 3600) AS avg_hours
                FROM approval_request
                WHERE state IN ('approved', 'refused')
                    AND date_confirmed IS NOT NULL
                    AND id IN %s
                    AND (
                        (state = 'approved'
                         AND date_approval_granted >= %s
                         AND date_approval_granted < %s)
                        OR (state = 'refused'
                            AND date_refused >= %s
                            AND date_refused < %s)
                    )
                """,
                self._accessible("approval.request"),
                start_date,
                end_date,
                start_date,
                end_date,
            ),
        )

        result = self.env.cr.fetchone()
        hours = round(result[0], 2) if result and result[0] else 0.0
        trace.REPORT.event(
            "avg_response_window", start=start_date, end=end_date, hours=hours
        )
        return hours

    def _get_avg_response_time_today_sql(
        self,
        today_start: Any,
        today_end: Any,
    ) -> float:
        self.env.cr.execute(
            SQL(
                """
                SELECT AVG(EXTRACT(EPOCH FROM (
                    CASE
                        WHEN state = 'approved'
                            THEN date_approval_granted - date_confirmed
                        WHEN state = 'refused' THEN date_refused - date_confirmed
                    END
                )) / 3600) AS avg_hours
                FROM approval_request
                WHERE state IN ('approved', 'refused')
                    AND date_confirmed IS NOT NULL
                    AND id IN %s
                    AND date_confirmed >= %s
                    AND date_confirmed < %s
                    AND (
                        (state = 'approved'
                         AND date_approval_granted >= %s
                         AND date_approval_granted < %s)
                        OR (state = 'refused'
                            AND date_refused >= %s
                            AND date_refused < %s)
                    )
                """,
                self._accessible("approval.request"),
                today_start,
                today_end,
                today_start,
                today_end,
                today_start,
                today_end,
            ),
        )

        result = self.env.cr.fetchone()
        hours = round(result[0], 2) if result and result[0] else 0.0
        trace.REPORT.event(
            "avg_response_today", start=today_start, end=today_end, hours=hours
        )
        return hours

    def action_refresh(self) -> dict[str, Any]:
        self.invalidate_recordset()
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_view_slowest_category(self) -> dict[str, Any]:
        self.check_singleton()
        if not self.slowest_category_id:
            return {"type": "ir.actions.act_window_close"}

        return {
            "name": self.env._("Requests: %s", self.slowest_category_id.name),
            "type": "ir.actions.act_window",
            "res_model": "approval.request",
            "view_mode": "list,form",
            "domain": [("category_id", "=", self.slowest_category_id.id)],
            "context": {"create": False},
        }

    def action_view_slowest_approver(self) -> dict[str, Any]:
        self.check_singleton()
        if not self.slowest_approver_id:
            return {"type": "ir.actions.act_window_close"}

        return {
            "name": self.env._("Pending Approvals: %s", self.slowest_approver_id.name),
            "type": "ir.actions.act_window",
            "res_model": "approval.approver",
            "view_mode": "list,form",
            "domain": [
                ("user_id", "=", self.slowest_approver_id.id),
                ("state", "=", "pending"),
            ],
            "context": {"create": False},
        }

    def action_view_overloaded_approver(self) -> dict[str, Any]:
        self.check_singleton()
        if not self.most_pending_approver_id:
            return {"type": "ir.actions.act_window_close"}

        return {
            "name": self.env._(
                "Pending Approvals: %s", self.most_pending_approver_id.name
            ),
            "type": "ir.actions.act_window",
            "res_model": "approval.approver",
            "view_mode": "list,form",
            "domain": [
                ("user_id", "=", self.most_pending_approver_id.id),
                ("state", "=", "pending"),
            ],
            "context": {"create": False},
        }

    def action_view_to_review(self) -> dict[str, Any]:
        return self.env["approval.request"].action_view_to_review()

    @api.model
    def get_dashboard(self) -> Self:
        return self.create({"name": "Approval Dashboard"})
