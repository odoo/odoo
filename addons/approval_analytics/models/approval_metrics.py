from odoo import fields, models

from odoo.addons.approval.models import approval_trace as trace


class ApprovalMetrics(models.Model):
    _name = "approval.metrics"
    _inherit = "mixin.sql.report"
    _description = "Approval Metrics"
    _auto = False
    _order = "category_id, avg_approval_hours"

    category_id = fields.Many2one(
        comodel_name="approval.category",
        string="Approval Category",
        readonly=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        readonly=True,
    )
    total_requests = fields.Integer(
        readonly=True,
        help="Total number of approval requests submitted",
    )
    approved_count = fields.Integer(
        string="Approved",
        readonly=True,
    )
    rejected_count = fields.Integer(
        string="Rejected",
        readonly=True,
    )
    pending_count = fields.Integer(
        string="Pending",
        readonly=True,
    )
    cancelled_count = fields.Integer(
        string="Cancelled",
        readonly=True,
        help="Number of cancelled requests (owner retraction / auto-expiration)",
    )
    approval_rate = fields.Float(
        string="Approval Rate %",
        readonly=True,
        help="Percentage of DECIDED requests that were approved. The "
        "denominator counts approvals and refusals only — a cancelled "
        "request was retracted or expired, so nobody decided it, and "
        "counting it would drag the rate down without any approver "
        "having said no.",
    )
    avg_approval_hours = fields.Float(
        string="Avg Approval Time (hours)",
        readonly=True,
        help="Average time from submission to approval",
    )
    median_approval_hours = fields.Float(
        string="Median Approval Time (hours)",
        readonly=True,
        help="Median time from submission to approval (50th percentile)",
    )
    sla_target_hours = fields.Float(
        string="SLA Target (hours)",
        readonly=True,
        help="Approval deadline configured on the category",
    )
    sla_compliant_count = fields.Integer(
        string="SLA Compliant",
        readonly=True,
        help="Number of approved requests resolved within the SLA target",
    )
    sla_compliance_rate = fields.Float(
        string="SLA Compliance %",
        readonly=True,
        help="Percentage of approved requests that met the SLA deadline",
    )

    _SLA_ELIGIBLE = (
        "ar.state = 'approved' AND ac.sla_target_hours > 0 "
        "AND ar.date_confirmed IS NOT NULL "
        "AND ar.date_approval_granted IS NOT NULL"
    )
    _APPROVAL_HOURS = (
        "EXTRACT(EPOCH FROM (ar.date_approval_granted - ar.date_confirmed))/3600"
    )

    def _get_fields_select(self) -> dict:
        sla_eligible = self._SLA_ELIGIBLE
        approval_hours = self._APPROVAL_HOURS
        decision_states = self.env["approval.request"]._decision_states_sql()
        columns = {
            "id": "MIN(ar.id)",
            "category_id": "ar.category_id",
            "company_id": "ar.company_id",
            "total_requests": "COUNT(*)",
            "approved_count": "SUM(CASE WHEN ar.state = 'approved' THEN 1 ELSE 0 END)",
            "rejected_count": "SUM(CASE WHEN ar.state = 'refused' THEN 1 ELSE 0 END)",
            "pending_count": "SUM(CASE WHEN ar.state = 'pending' THEN 1 ELSE 0 END)",
            "cancelled_count": "SUM(CASE WHEN ar.state = 'cancelled' THEN 1 ELSE 0 END)",
            "approval_rate": f"""ROUND(
                    ((SUM(CASE WHEN ar.state = 'approved' THEN 1 ELSE 0 END)::float /
                     NULLIF(
                        SUM(CASE WHEN ar.state IN {decision_states}
                            THEN 1 ELSE 0 END),
                        0
                     )) * 100)::numeric,
                    2
                )""",
            "avg_approval_hours": f"""ROUND(
                    AVG(
                        CASE
                            WHEN ar.state = 'approved' AND ar.date_confirmed IS NOT NULL
                                AND ar.date_approval_granted IS NOT NULL
                            THEN {approval_hours}
                            ELSE NULL
                        END
                    )::numeric,
                    2
                )""",
            "median_approval_hours": f"""ROUND(
                    PERCENTILE_CONT(0.5) WITHIN GROUP (
                        ORDER BY
                            CASE
                                WHEN ar.state = 'approved' AND ar.date_confirmed IS NOT NULL
                                    AND ar.date_approval_granted IS NOT NULL
                                THEN {approval_hours}
                                ELSE NULL
                            END
                    )::numeric,
                    2
                )""",
            "sla_target_hours": "COALESCE(ac.sla_target_hours, 0)",
            "sla_compliant_count": f"""SUM(CASE
                    WHEN {sla_eligible} AND {approval_hours} <= ac.sla_target_hours
                    THEN 1 ELSE 0
                END)""",
            "sla_compliance_rate": f"""ROUND(
                    (SUM(CASE
                        WHEN {sla_eligible} AND {approval_hours} <= ac.sla_target_hours
                        THEN 1 ELSE 0
                    END)::float /
                    NULLIF(SUM(CASE WHEN {sla_eligible} THEN 1 ELSE 0 END), 0) * 100)::numeric,
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
            ("approval_request", "ar", None, None),
            ("approval_category", "ac", "JOIN", "ac.id = ar.category_id"),
        ]

    def _get_where_conditions(self) -> list:
        return ["ar.state != 'new'"]

    def _get_fields_group_by(self) -> list:
        return ["ar.category_id", "ar.company_id", "ac.sla_target_hours"]
