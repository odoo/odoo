# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    timesheet_show_rates = fields.Boolean(export_string_translation=False)
    timesheet_show_leaderboard = fields.Boolean(export_string_translation=False)

    def _get_leaderboard_query(self):
        return """
            WITH A AS (
                   SELECT aal.employee_id AS id,
                          he.name, he.billable_time_target,
                          SUM(
                            CASE
                                WHEN aal.timesheet_invoice_type != 'non_billable'
                                THEN aal.unit_amount
                                ELSE 0
                            END
                          ) AS billable_time,
                          SUM(aal.unit_amount) AS total_time,
                          SUM(CASE WHEN aal.date < %s THEN aal.unit_amount ELSE 0 END) AS total_valid_time
                     FROM account_analytic_line AS aal
                LEFT JOIN hr_employee AS he
                       ON aal.employee_id = he.id
                    WHERE aal.project_id IS NOT NULL
                      AND date BETWEEN %s AND %s
                      AND he.company_id = %s
                      AND billable_time_target > 0
                 GROUP BY aal.employee_id,
                          he.name,
                          he.billable_time_target
            )
            SELECT *,
                   A.billable_time / A.billable_time_target * 100 AS billing_rate
              FROM A
        """

    def _get_leaderboard_data(self, period_start, period_end, today):
        self.ensure_one()
        self.env.cr.execute(self._get_leaderboard_query(), [today, period_start, period_end, self.id])
        return self.env.cr.dictfetchall()

    @api.model
    def get_timesheet_ranking_data(self, period_start, period_end, today, fetch_tip=False):
        if not (
            self.env.company.timesheet_show_rates
            and self.env.user.has_group("hr_timesheet.group_hr_timesheet_user")
        ):
            return {
                "leaderboard": [],
                "employee_id": False,
                "billing_rate_target": 0,
                "total_time_target": 0,
            }
        period_start, period_end, today = (fields.Date.from_string(d) for d in [period_start, period_end, today])

        employee = self.env.user.employee_id
        data = {
            "leaderboard": self.env.company._get_leaderboard_data(period_start, period_end, today),
            "employee_id": employee.id,
            "total_time_target": sum(self.env.user.employee_id.get_daily_working_hours(period_start, period_end)[self.env.user.employee_id.id].values()),
        }
        if not self.env.company.timesheet_show_leaderboard:
            data['leaderboard'] = [employee_data for employee_data in data['leaderboard'] if employee_data['id'] == employee.id]

        if fetch_tip:
            data["tip"] = self.env["hr.timesheet.tip"]._get_random_tip() or _("Make it a habit to record timesheets every day.")

        return data
