# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class HrLeaveEmployeeTypeMonthlyReport(models.Model):
    _name = 'hr.leave.employee.type.monthly.report'
    _description = 'Time Off Summary / Monthly Report'
    _auto = False

    employee_id = fields.Many2one('hr.employee', string="Employee", readonly=True)
    balance_days = fields.Float('Balance', readonly=True)
    change_this_month = fields.Float('Change', readonly=True)
    leave_type = fields.Many2one("hr.leave.type", string="Time Off Type", readonly=True)
    month = fields.Date('Month', readonly=True)
    company_id = fields.Many2one('res.company', string="Company", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'hr_leave_employee_type_monthly_report')

        self.env.cr.execute("""
CREATE OR REPLACE VIEW hr_leave_employee_type_monthly_report AS (
WITH months AS (
    SELECT date_trunc('month', dd)::date AS month
    FROM generate_series(
        (SELECT min(date_from) FROM hr_leave_allocation),
        (SELECT max(COALESCE(date_to, CURRENT_DATE)) FROM hr_leave_allocation),
        interval '1 month'
    ) dd
),

emp_leave_types AS (
    SELECT DISTINCT employee_id,
                    holiday_status_id AS leave_type,
                    employee_company_id AS company_id
    FROM hr_leave_allocation
    WHERE state = 'validate'
),

allocations AS (
    SELECT
        a.id AS allocation_id,
        a.employee_id,
        a.holiday_status_id AS leave_type,
        a.number_of_days,
        a.date_from,
        COALESCE(a.date_to, '9999-12-31') AS date_to
    FROM hr_leave_allocation a
    WHERE a.state = 'validate'
),

leaves AS (
    SELECT
        l.employee_id,
        l.holiday_status_id AS leave_type,
        l.date_from,
        l.date_to,
        l.number_of_days
    FROM hr_leave l
    WHERE l.state IN ('validate','validate1')
),

allocation_month_balances AS (
    SELECT
        m.month,
        e.employee_id,
        e.leave_type,
        e.company_id,
        SUM(
            GREATEST(
                a.number_of_days
                - COALESCE((
                    SELECT SUM(l2.number_of_days)
                    FROM leaves l2
                    WHERE l2.employee_id = a.employee_id
                      AND l2.leave_type = a.leave_type
                      -- Only leaves that overlap this allocation period and are before end of month
                      AND l2.date_from <= m.month + interval '1 month - 1 day'
                      AND l2.date_to >= a.date_from
                ), 0),
                0
            )
        ) AS balance_days
    FROM months m
    CROSS JOIN emp_leave_types e
    LEFT JOIN allocations a
        ON a.employee_id = e.employee_id
       AND a.leave_type = e.leave_type
       AND a.date_from <= m.month + interval '1 month - 1 day'
       AND a.date_to >= m.month
    GROUP BY m.month, e.employee_id, e.leave_type, e.company_id
),

balances_with_change AS (
    SELECT
        row_number() OVER (ORDER BY employee_id, leave_type, month) AS id,
        employee_id,
        leave_type,
        month,
        balance_days,
        balance_days
          - LAG(balance_days) OVER (PARTITION BY employee_id, leave_type ORDER BY month) AS change_this_month,
        company_id
    FROM allocation_month_balances
)

SELECT *
FROM balances_with_change
ORDER BY employee_id, leave_type, month

            );
        """)

    @api.model
    def action_time_off_analysis(self):
        domain = [('company_id', 'in', self.env.companies.ids)]
        return {
            'name': self.env._('Balance'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave.employee.type.monthly.report',
            'view_mode': 'graph,pivot',
            'search_view_id': [self.env.ref('hr_holidays.view_search_hr_holidays_employee_type_monthly_report').id],
            'domain': domain,
            'context': {
                'search_default_groupby_month': True,
                'search_default_groupby_employee': True,
            },
        }
