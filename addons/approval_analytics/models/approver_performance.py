from odoo import fields, models

from odoo.addons.approval.models import approval_trace as trace


class ApproverPerformance(models.Model):
    _name = "approver.performance"
    _inherit = "mixin.sql.report"
    _description = "Approver Performance Metrics"
    _auto = False
    _order = "avg_response_hours"

    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Approver",
        readonly=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        readonly=True,
    )
    total_approvals = fields.Integer(
        readonly=True,
        help="Total number of approval decisions made",
    )
    approved_count = fields.Integer(
        string="Approved",
        readonly=True,
        help="Number of requests approved by this user",
    )
    refused_count = fields.Integer(
        string="Refused",
        readonly=True,
        help="Number of requests this user moved to the terminal refused state.",
    )
    pending_count = fields.Integer(
        string="Pending Now",
        readonly=True,
        help="Number of requests currently awaiting this user's approval",
    )
    avg_response_hours = fields.Float(
        string="Avg Response Time (hours)",
        readonly=True,
        help="Average time from request submission to approval/refusal",
    )
    approval_rate = fields.Float(
        string="Approval Rate %",
        readonly=True,
        help="Percentage of decisions that were approvals (vs refusals)",
    )

    def _get_fields_select(self) -> dict:
        columns = {
            "id": "MIN(a.id)",
            "user_id": "COALESCE(a.decided_by_user_id, a.user_id)",
            "company_id": "ar.company_id",
            "total_approvals": "SUM(CASE WHEN a.decision_date IS NOT NULL THEN 1 ELSE 0 END)",
            "approved_count": (
                "SUM(CASE WHEN a.state = 'approved' AND a.decision_date IS NOT NULL "
                "THEN 1 ELSE 0 END)"
            ),
            "refused_count": (
                "SUM(CASE WHEN a.state = 'refused' AND a.decision_date IS NOT NULL "
                "THEN 1 ELSE 0 END)"
            ),
            "pending_count": "SUM(CASE WHEN a.state = 'pending' THEN 1 ELSE 0 END)",
            "avg_response_hours": """ROUND(
                    AVG(
                        CASE
                            WHEN a.decision_date IS NOT NULL
                                AND COALESCE(a.pending_since, ar.date_confirmed)
                                    IS NOT NULL
                            THEN EXTRACT(EPOCH FROM (
                                a.decision_date
                                - COALESCE(a.pending_since, ar.date_confirmed)
                            )) / 3600
                            ELSE NULL
                        END
                    )::numeric,
                    2
                )""",
            "approval_rate": """ROUND(
                    (
                        (
                            SUM(
                                CASE WHEN a.state = 'approved' AND a.decision_date IS NOT NULL
                                    THEN 1
                                    ELSE 0
                                END
                            )::float
                            / NULLIF(
                                SUM(
                                    CASE WHEN a.decision_date IS NOT NULL
                                        THEN 1
                                        ELSE 0
                                    END
                                ),
                                0
                            )
                        ) * 100
                    )::numeric,
                    2
                )""",
        }
        trace.REPORT.event(
            "view_shape",
            report=self,
            columns=len(columns),
            tables=len(self._get_from_tables()),
            group_by=len(self._get_fields_group_by()),
            where=len(self._get_where_conditions()),
        )
        return columns

    def _get_from_tables(self) -> list:
        return [
            ("approval_approver", "a", None, None),
            ("approval_request", "ar", "JOIN", "ar.id = a.request_id"),
        ]

    def _get_where_conditions(self) -> list:
        return ["a.state != 'new'"]

    def _get_fields_group_by(self) -> list:
        return ["COALESCE(a.decided_by_user_id, a.user_id)", "ar.company_id"]
