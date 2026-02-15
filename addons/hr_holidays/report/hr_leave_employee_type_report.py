# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _


class LeaveReport(models.Model):
    _name = "hr.leave.employee.type.report"
    _description = 'Time Off Summary / Report'
    _auto = False
    _order = "date_from DESC, employee_id"

    employee_id = fields.Many2one('hr.employee', string="Employee", readonly=True)
    active_employee = fields.Boolean(readonly=True)
    number_of_days = fields.Float('Number of Days', readonly=True, aggregator="sum")
    number_of_hours = fields.Float('Number of Hours', readonly=True, aggregator="sum")
    department_id = fields.Many2one('hr.department', string='Department', readonly=True)
    leave_type = fields.Many2one("hr.leave.type", string="Time Off Type", readonly=True)
    holiday_status = fields.Selection([
        ('taken', 'Taken'), #taken = validated
        ('left', 'Left'),
        ('planned', 'Planned')
    ])
    state = fields.Selection([
        ('cancel', 'Cancelled'),
        ('confirm', 'To Approve'),
        ('refuse', 'Refused'),
        ('validate1', 'Second Approval'),
        ('validate', 'Approved')
        ], string='Status', readonly=True)
    date_from = fields.Datetime('Start Date', readonly=True)
    date_to = fields.Datetime('End Date', readonly=True)
    company_id = fields.Many2one('res.company', string="Company", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'hr_leave_employee_type_report')

        self._cr.execute("""
            CREATE or REPLACE view hr_leave_employee_type_report as (
                SELECT row_number() over(ORDER BY leaves.employee_id) as id,
                leaves.employee_id as employee_id,
                leaves.active_employee as active_employee,
                leaves.number_of_days as number_of_days,
                leaves.number_of_hours as number_of_hours,
                leaves.department_id as department_id,
                leaves.leave_type as leave_type,
                leaves.holiday_status as holiday_status,
                leaves.state as state,
                leaves.date_from as date_from,
                leaves.date_to as date_to,
                leaves.company_id as company_id
                FROM (SELECT
                    allocation.employee_id as employee_id,
                    employee.active as active_employee,
                    CASE
                        WHEN allocation.id = max_allocation_id.max_id
                            THEN aggregate_allocation_non_expired.number_of_days
                                - COALESCE(aggregate_leave_non_expired.number_of_days, 0)
                            ELSE 0
                    END as number_of_days,
                    CASE
                        WHEN allocation.id = max_allocation_id.max_id
                            THEN aggregate_allocation_non_expired.number_of_hours
                                - COALESCE(aggregate_leave_non_expired.number_of_hours, 0)
                            ELSE 0
                    END as number_of_hours,
                    allocation.department_id as department_id,
                    allocation.holiday_status_id as leave_type,
                    allocation.state as state,
                    allocation.date_from as date_from,
                    allocation.date_to as date_to,
                    'left' as holiday_status,
                    allocation.employee_company_id as company_id
                FROM hr_leave_allocation as allocation
                INNER JOIN hr_employee as employee ON (allocation.employee_id = employee.id)

                /* Maximum id for non-expired allocations only */
                LEFT JOIN
                    (SELECT employee_id, holiday_status_id, max(id) as max_id
                    FROM hr_leave_allocation
                    WHERE (date_to IS NULL OR date_to >= CURRENT_DATE)
                    GROUP BY employee_id, holiday_status_id) max_allocation_id
                ON (allocation.employee_id = max_allocation_id.employee_id AND allocation.holiday_status_id = max_allocation_id.holiday_status_id)

                /* Sum of NON-EXPIRED allocations only */
                LEFT JOIN
                    (SELECT employee_id, holiday_status_id,
                        sum(CASE WHEN state = 'validate' THEN number_of_days ELSE 0 END) as number_of_days,
                        sum(CASE WHEN state = 'validate' THEN number_of_hours_display ELSE 0 END) as number_of_hours
                    FROM hr_leave_allocation
                    WHERE (date_to IS NULL OR date_to >= CURRENT_DATE)
                    GROUP BY employee_id, holiday_status_id) aggregate_allocation_non_expired
                ON (allocation.employee_id = aggregate_allocation_non_expired.employee_id AND allocation.holiday_status_id = aggregate_allocation_non_expired.holiday_status_id)

                /* Sum of leaves - only count days AFTER the latest expired allocation, excluding weekends & public holidays */
                LEFT JOIN
                    (SELECT
                        l.employee_id,
                        l.holiday_status_id,
                        SUM(
                            CASE
                                WHEN l.state IN ('validate', 'validate1') THEN
                                    CASE
                                        WHEN l.date_from > latest_expired_allocation.max_expired_date
                                        THEN l.number_of_days

                                        WHEN l.date_to > latest_expired_allocation.max_expired_date
                                            AND l.date_from <= latest_expired_allocation.max_expired_date
                                        THEN
                                            (SELECT COUNT(DISTINCT cd.day)
                                                FROM generate_series(
                                                    (latest_expired_allocation.max_expired_date + INTERVAL '1 day')::date,
                                                    l.date_to::date,
                                                    interval '1 day'
                                                ) AS cd(day)
                                                WHERE EXISTS (
                                                    SELECT 1
                                                    FROM resource_calendar_attendance rca
                                                    WHERE rca.calendar_id = e.resource_calendar_id
                                                    AND rca.dayofweek::int = ((EXTRACT(ISODOW FROM cd.day)::int + 6) % 7)
                                                )
                                                AND NOT EXISTS (
                                                    SELECT 1
                                                    FROM resource_calendar_leaves rcl
                                                    WHERE rcl.date_from::date <= cd.day
                                                    AND rcl.date_to::date >= cd.day
                                                    AND rcl.resource_id IS NULL
                                                    AND (rcl.calendar_id IS NULL OR rcl.calendar_id = e.resource_calendar_id)
                                                )
                                            )
                                        ELSE 0
                                    END
                                ELSE 0
                            END
                        ) as number_of_days,
                        SUM(
                            CASE
                                WHEN l.state IN ('validate', 'validate1') THEN
                                    CASE
                                        WHEN l.date_from > latest_expired_allocation.max_expired_date
                                        THEN l.number_of_hours

                                        WHEN l.date_to > latest_expired_allocation.max_expired_date
                                            AND l.date_from <= latest_expired_allocation.max_expired_date
                                        THEN
                                            (l.number_of_hours *
                                                (SELECT COUNT(DISTINCT cd.day)::float
                                                    FROM generate_series(
                                                        (latest_expired_allocation.max_expired_date + INTERVAL '1 day')::date,
                                                        l.date_to::date,
                                                        interval '1 day'
                                                    ) AS cd(day)
                                                    WHERE EXISTS (
                                                        SELECT 1
                                                        FROM resource_calendar_attendance rca
                                                        WHERE rca.calendar_id = e.resource_calendar_id
                                                        AND rca.dayofweek::int = ((EXTRACT(ISODOW FROM cd.day)::int + 6) % 7)
                                                    )
                                                    AND NOT EXISTS (
                                                        SELECT 1
                                                        FROM resource_calendar_leaves rcl
                                                        WHERE rcl.date_from::date <= cd.day
                                                        AND rcl.date_to::date >= cd.day
                                                        AND rcl.resource_id IS NULL
                                                        AND (rcl.calendar_id IS NULL OR rcl.calendar_id = e.resource_calendar_id)
                                                    )
                                                ) / NULLIF(l.number_of_days, 0)
                                            )
                                        ELSE 0
                                    END
                                ELSE 0
                            END
                        ) as number_of_hours
                    FROM hr_leave l
                    INNER JOIN hr_employee e ON e.id = l.employee_id

                    /* Find the LATEST expiry date per employee/leave type */
                    LEFT JOIN
                        (SELECT employee_id, holiday_status_id, max(date_to) as max_expired_date
                        FROM hr_leave_allocation
                        WHERE date_to IS NOT NULL AND date_to < CURRENT_DATE
                        GROUP BY employee_id, holiday_status_id) latest_expired_allocation
                    ON (l.employee_id = latest_expired_allocation.employee_id AND l.holiday_status_id = latest_expired_allocation.holiday_status_id)
                    GROUP BY l.employee_id, l.holiday_status_id) aggregate_leave_non_expired
                ON (allocation.employee_id = aggregate_leave_non_expired.employee_id AND allocation.holiday_status_id = aggregate_leave_non_expired.holiday_status_id)

                WHERE (allocation.date_to IS NULL OR allocation.date_to >= CURRENT_DATE)

                UNION ALL SELECT
                    request.employee_id as employee_id,
                    employee.active as active_employee,
                    request.number_of_days as number_of_days,
                    request.number_of_hours as number_of_hours,
                    request.department_id as department_id,
                    request.holiday_status_id as leave_type,
                    request.state as state,
                    request.date_from as date_from,
                    request.date_to as date_to,
                    CASE
                        WHEN request.state IN ('validate1', 'validate') THEN 'taken'
                        WHEN request.state = 'confirm' THEN 'planned'
                    END as holiday_status,
                    request.employee_company_id as company_id
                FROM hr_leave as request
                INNER JOIN hr_employee as employee ON (request.employee_id = employee.id)
                WHERE request.state IN ('confirm', 'validate', 'validate1')) leaves
            );
        """)

    @api.model
    def action_time_off_analysis(self):
        domain = [('company_id', 'in', self.env.companies.ids)]
        if self.env.context.get('active_ids'):
            domain = [('employee_id', 'in', self.env.context.get('active_ids', [])),
                      ('state', '!=', 'cancel')]

        return {
            'name': _('Time Off Analysis'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave.employee.type.report',
            'view_mode': 'pivot',
            'search_view_id': [self.env.ref('hr_holidays.view_search_hr_holidays_employee_type_report').id],
            'domain': domain,
            'context': {
                'search_default_year': True,
                'search_default_company': True,
                'search_default_employee': True,
                'group_expand': True,
            }
        }
