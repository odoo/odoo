# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class ResCompany(models.Model):
    _inherit = "res.company"

    def _get_leaderboard_query(self):
        return """
            WITH A AS (
               SELECT aal.employee_id AS id,
                      SUM(
                        CASE
                            WHEN aal.timesheet_invoice_type != 'non_billable'
                            THEN aal.unit_amount
                            ELSE 0
                        END
                      ) AS billable_time,
                      SUM(aal.unit_amount) AS total_time,
                      SUM(CASE WHEN aal.date <= %s THEN aal.unit_amount ELSE 0 END) AS total_valid_time
                 FROM account_analytic_line aal
            LEFT JOIN hr_leave_type hlt ON hlt.timesheet_task_id = aal.task_id
                WHERE aal.project_id IS NOT NULL
                      AND aal.date BETWEEN %s AND %s
                      AND aal.company_id = %s
                      AND hlt.timesheet_task_id IS NULL
             GROUP BY aal.employee_id
        )
        SELECT A.id,
               he.name,
               he.billable_time_target,
               billable_time,
               total_time,
               total_valid_time,
               billable_time / he.billable_time_target * 100 AS billing_rate
          FROM A
     LEFT JOIN hr_employee AS he ON A.id = he.id WHERE he.billable_time_target > 0
    """
