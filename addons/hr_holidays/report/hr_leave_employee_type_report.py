# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _


class HrLeaveEmployeeTypeReport(models.Model):
    _name = 'hr.leave.employee.type.report'
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
        tools.drop_view_if_exists(self.env.cr, 'hr_leave_employee_type_report')

        self.env.cr.execute("""
            CREATE or REPLACE view hr_leave_employee_type_report as (
                WITH
                /* Validated leaves */
                validated_leaves as (
                    SELECT
						l.employee_id as employee_id,
						l.number_of_days as number_of_days,
						l.number_of_hours as number_of_hours,
						l.holiday_status_id as leave_type,
						l.date_from as date_from,
						l.date_to as date_to
                    FROM hr_leave l
                    WHERE l.state IN ('validate', 'validate1')
                ),

                /* FIFO-ordered validated allocations */
                ordered_allocations as (
                    SELECT
						allocation.id as allocation_id,
						allocation.employee_id as employee_id,
						employee.active as active_employee,
						allocation.number_of_days as number_of_days,
						allocation.number_of_hours_display as number_of_hours,
						allocation.department_id as department_id,
						allocation.holiday_status_id as leave_type,
						allocation.state as state,
						allocation.date_from as date_from,
						allocation.date_to as date_to,
						allocation.employee_company_id as company_id,
						ROW_NUMBER() OVER (
							PARTITION BY allocation.employee_id, allocation.holiday_status_id
							ORDER BY allocation.date_from, allocation.id
						) as fifo_rank,
						SUM(allocation.number_of_days) OVER (
							PARTITION BY allocation.employee_id, allocation.holiday_status_id
							ORDER BY allocation.date_from, allocation.id
							ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
						) as cumulative_allocated_days,
						SUM(allocation.number_of_hours_display) OVER (
							PARTITION BY allocation.employee_id, allocation.holiday_status_id
							ORDER BY allocation.date_from, allocation.id
							ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
						) as cumulative_allocated_hours
                    FROM hr_leave_allocation allocation
                    JOIN hr_employee employee ON (allocation.employee_id = employee.id)
                    WHERE allocation.state = 'validate'
                ),

                /* Leaves applicable to each allocation */
                taken_per_allocation as (
                    SELECT
                        oa.allocation_id,
                        SUM(vl.number_of_days) as taken_days,
						SUM(vl.number_of_hours) as taken_hours
                    FROM ordered_allocations oa
                    LEFT JOIN validated_leaves vl
                        ON vl.employee_id = oa.employee_id
                        AND vl.leave_type = oa.leave_type
                        AND vl.date_from <= COALESCE(oa.date_to, 'infinity')
                        AND vl.date_to   >= oa.date_from
                    GROUP BY oa.allocation_id
                ),

                /* FIFO remaining balance per allocation */
                fifo_balances as (
                    SELECT
                        oa.employee_id as employee_id,
                        oa.active_employee as active_employee,
                        GREATEST(oa.number_of_days - GREATEST(
							COALESCE(tpa.taken_days, 0) - (oa.cumulative_allocated_days - oa.number_of_days), 0),
						0) as number_of_days,
						GREATEST(oa.number_of_hours - GREATEST(
							COALESCE(tpa.taken_hours, 0) - (oa.cumulative_allocated_hours - oa.number_of_hours), 0),
						0) as number_of_hours,
                        oa.department_id as department_id,
                        oa.leave_type as leave_type,
                        oa.state as state,
                        oa.date_from as date_from,
                        oa.date_to as date_to,
                        oa.company_id as company_id
                    FROM ordered_allocations oa
                    LEFT JOIN taken_per_allocation tpa
                        ON tpa.allocation_id = oa.allocation_id
                )

                /* Final unified result */
                SELECT
                    row_number() OVER (ORDER BY leaves.employee_id, leaves.date_from) as id,
					leaves.employee_id as employee_id,
					leaves.active_employee as active_employee,
					leaves.number_of_days as number_of_days,
					leaves.number_of_hours as number_of_hours,
					leaves.department_id as department_id,
					leaves.leave_type as leave_type,
					leaves.state as state,
					leaves.date_from as date_from,
					leaves.date_to as date_to,
					leaves.holiday_status as holiday_status,
					leaves.company_id as company_id
                FROM (
                    /* Remaining leave balances */
                    SELECT
						fb.employee_id as employee_id,
						fb.active_employee as active_employee,
						fb.number_of_days as number_of_days,
						fb.number_of_hours as number_of_hours,
						fb.department_id as department_id,
						fb.leave_type as leave_type,
						fb.state as state,
						fb.date_from as date_from,
						fb.date_to as date_to,
						'left' as holiday_status,
						fb.company_id as company_id
                    FROM fifo_balances fb
                    WHERE fb.number_of_days >= 0

                    /* Planned and taken leave requests */
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
							WHEN request.state IN ('validate', 'validate1') THEN 'taken'
							WHEN request.state = 'confirm' THEN 'planned'
						END as holiday_status,
						request.employee_company_id as company_id
                    FROM hr_leave as request
                    JOIN hr_employee as employee ON (request.employee_id = employee.id)
                    WHERE request.state IN ('confirm', 'validate', 'validate1')
                ) leaves
            );
        """)

    @api.model
    def action_time_off_analysis(self):
        domain = [('company_id', 'in', self.env.companies.ids)]
        if self.env.context.get('active_ids'):
            domain = [('employee_id', 'in', self.env.context.get('active_ids', [])),
                      ('state', '!=', 'cancel')]

        return {
            'name': _('Balance'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave.employee.type.report',
            'view_mode': 'pivot',
            'search_view_id': [self.env.ref('hr_holidays.view_search_hr_holidays_employee_type_report').id],
            'domain': domain,
            'help': _("""
                <p class="o_view_nocontent_empty_folder">
                    No Balance yet!
                </p>
                <p>
                    Why don't you start by <a type="action" class="text-link" name="%d">Allocating Time off</a> ?
                </p>
            """, self.env.ref("hr_holidays.hr_leave_allocation_action_form").id),
            'context': {
                'search_default_year': True,
                'search_default_company': True,
                'search_default_employee': True,
                'group_expand': True,
            }
        }
