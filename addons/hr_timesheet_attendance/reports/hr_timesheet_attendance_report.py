from odoo import api, fields, models
from odoo.db.schema import drop_view_if_exists
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrTimesheetAttendanceReport(models.Model):
    _name = "hr.timesheet.attendance.report"
    _auto = False
    _description = "Timesheet Attendance Report"

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        readonly=True,
    )
    date = fields.Date(readonly=True)
    total_timesheet = fields.Float(
        string="Timesheets Time",
        readonly=True,
    )
    total_attendance = fields.Float(
        string="Attendance Time",
        readonly=True,
    )
    total_difference = fields.Float(
        string="Time Difference",
        readonly=True,
    )
    timesheets_cost = fields.Monetary(
        string="Timesheet Cost",
        readonly=True,
    )
    attendance_cost = fields.Monetary(readonly=True)
    cost_difference = fields.Monetary(readonly=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        readonly=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        readonly=True,
    )

    def init(self):
        _debug.lifecycle("attendance_report_view_rebuilt", table=self._table)
        drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """CREATE OR REPLACE VIEW %s AS (
            SELECT
                max(id) AS id,
                t.employee_id,
                t.date,
                t.company_id,
                t.currency_id,
                coalesce(sum(t.attendance), 0) AS total_attendance,
                coalesce(sum(t.timesheet), 0) AS total_timesheet,
                coalesce(sum(t.attendance), 0) - coalesce(sum(t.timesheet), 0) as total_difference,
                NULLIF(coalesce(sum(t.timesheet_cost), 0), 0) as timesheets_cost,
                NULLIF(coalesce(sum(t.attendance), 0) * t.emp_cost, 0) as attendance_cost,
                NULLIF(coalesce(sum(t.attendance), 0) * t.emp_cost
                       - coalesce(sum(t.timesheet_cost), 0), 0) as cost_difference
            FROM (
                SELECT
                    -hr_attendance.id AS id,
                    hr_employee.hourly_cost AS emp_cost,
                    hr_attendance.employee_id AS employee_id,
                    hr_attendance.worked_hours AS attendance,
                    NULL AS timesheet,
                    NULL AS timesheet_cost,
                    CAST(hr_attendance.check_in
                            at time zone 'utc'
                            at time zone
                                (SELECT resource.tz FROM resource_resource as resource
                                INNER JOIN hr_employee as employee ON employee.resource_id = resource.id
                                WHERE employee.id = hr_attendance.employee_id)
                    as DATE) as date,
                    hr_employee.company_id as company_id,
                    company.currency_id AS currency_id
                FROM hr_attendance
                LEFT JOIN hr_employee ON hr_employee.id = hr_attendance.employee_id
                LEFT JOIN res_company AS company ON company.id = hr_employee.company_id
                WHERE check_in::date <= CURRENT_DATE
            UNION ALL
                SELECT
                    ts.id AS id,
                    hr_employee.hourly_cost AS emp_cost,
                    ts.employee_id AS employee_id,
                    NULL AS attendance,
                    ts.unit_amount AS timesheet,
                    -ts.amount AS timesheet_cost,
                    ts.date AS date,
                    ts.company_id AS company_id,
                    ts_company.currency_id AS currency_id
                FROM account_analytic_line AS ts
                LEFT JOIN hr_employee ON hr_employee.id = ts.employee_id
                LEFT JOIN res_company ts_company ON ts_company.id = ts.company_id
                WHERE ts.project_id IS NOT NULL
                  AND date <= CURRENT_DATE
            ) AS t
            GROUP BY t.employee_id, t.date, t.company_id, t.currency_id, t.emp_cost
            ORDER BY t.date
        )
        """
            % self._table
        )

    @api.model
    def formatted_read_group(
        self,
        domain,
        groupby=(),
        aggregates=(),
        having=(),
        offset=0,
        limit=None,
        order=None,
    ) -> list[dict]:
        if not order and groupby:
            order = ", ".join(
                f"{spec} DESC" if spec.startswith("date:") else spec for spec in groupby
            )
            _debug.logic("report_order_defaulted", order=order)
        return super().formatted_read_group(
            domain,
            groupby,
            aggregates,
            having=having,
            offset=offset,
            limit=limit,
            order=order,
        )
