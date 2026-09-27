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
                WITH
                /* Validated leaves */
                validated_leaves as (
                    SELECT
						l.id as leave_id,
						l.employee_id as employee_id,
						l.number_of_days as number_of_days,
						l.number_of_hours as number_of_hours,
						l.holiday_status_id as leave_type,
						l.date_from as date_from,
						l.date_to as date_to
                    FROM hr_leave l
                    WHERE l.state IN ('validate', 'validate1')
                ),

                /* Base allocations with overlap group detection */
                base_allocations as (
                    SELECT
						allocation.id as allocation_id,
						allocation.employee_id as employee_id,
						employee.active as active_employee,
						allocation.number_of_days as number_of_days,
						allocation.number_of_hours_display as number_of_hours,
						employee.department_id as department_id,
						allocation.holiday_status_id as leave_type,
						allocation.state as state,
						allocation.date_from as date_from,
						allocation.date_to as date_to,
						allocation.employee_company_id as company_id,
						CASE
							WHEN allocation.date_from > MAX(COALESCE(allocation.date_to, 'infinity'::date)) OVER (
								PARTITION BY allocation.employee_id, allocation.holiday_status_id
								ORDER BY allocation.date_from, allocation.id
								ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
							)
							THEN 1
							ELSE 0
						END as is_new_group
                    FROM hr_leave_allocation allocation
                    JOIN hr_employee employee ON (allocation.employee_id = employee.id)
                    WHERE allocation.state = 'validate'
                ),

                /* Assign overlap group ids */
                grouped_allocations as (
                    SELECT
						ba.*,
						SUM(ba.is_new_group) OVER (
							PARTITION BY ba.employee_id, ba.leave_type
							ORDER BY ba.date_from, ba.allocation_id
							ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
						) as overlap_group
                    FROM base_allocations ba
                ),

                /* FIFO-ordered allocations with cumulative sums within each overlap group */
                ordered_allocations as (
                    SELECT
						ga.allocation_id as allocation_id,
						ga.employee_id as employee_id,
						ga.active_employee as active_employee,
						ga.number_of_days as number_of_days,
						ga.number_of_hours as number_of_hours,
						ga.department_id as department_id,
						ga.leave_type as leave_type,
						ga.state as state,
						ga.date_from as date_from,
						ga.date_to as date_to,
						ga.company_id as company_id,
						ga.overlap_group as overlap_group,
						ROW_NUMBER() OVER (
							PARTITION BY ga.employee_id, ga.leave_type, ga.overlap_group
							ORDER BY ga.date_from, ga.allocation_id
						) as fifo_rank,
						SUM(ga.number_of_days) OVER (
							PARTITION BY ga.employee_id, ga.leave_type, ga.overlap_group
							ORDER BY ga.date_from, ga.allocation_id
							ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
						) as cumulative_allocated_days,
						SUM(ga.number_of_hours) OVER (
							PARTITION BY ga.employee_id, ga.leave_type, ga.overlap_group
							ORDER BY ga.date_from, ga.allocation_id
							ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
						) as cumulative_allocated_hours
                    FROM grouped_allocations ga
                ),

                /* Identify the EARLIEST valid allocation for each leave */
                leave_entry_points as (
                    SELECT
                        vl.leave_id,
                        vl.number_of_days,
                        vl.number_of_hours,
                        vl.employee_id,
                        vl.leave_type,
                        oa.overlap_group,
                        MIN(oa.fifo_rank) as entry_rank
                    FROM validated_leaves vl
                    JOIN ordered_allocations oa
                        ON  vl.employee_id = oa.employee_id
                        AND vl.leave_type = oa.leave_type
                        AND vl.date_from <= COALESCE(oa.date_to, 'infinity')
                        AND (oa.date_to IS NULL OR vl.date_to >= oa.date_from)
                    GROUP BY vl.leave_id, vl.number_of_days, vl.number_of_hours,
                             vl.employee_id, vl.leave_type, oa.overlap_group
                ),

                /* Aggregate entry points by rank for cumulative summing */
                taken_by_rank as (
                    SELECT
                        employee_id,
                        leave_type,
                        overlap_group,
                        entry_rank,
                        SUM(number_of_days) as rank_days,
                        SUM(number_of_hours) as rank_hours
                    FROM leave_entry_points
                    GROUP BY employee_id, leave_type, overlap_group, entry_rank
                ),

                /* FIFO remaining balance per allocation */
                fifo_balances as (
                    SELECT
                        sub.employee_id,
                        sub.active_employee,
                        GREATEST(sub.cumul_rem_days - COALESCE(LAG(sub.cumul_rem_days) OVER w, 0), 0) as number_of_days,
                        GREATEST(sub.cumul_rem_hours - COALESCE(LAG(sub.cumul_rem_hours) OVER w, 0), 0) as number_of_hours,
                        sub.department_id,
                        sub.leave_type,
                        sub.state,
                        sub.date_from,
                        sub.date_to,
                        sub.company_id
                    FROM (
                        SELECT
                            oa.*,
                            GREATEST(oa.cumulative_allocated_days - SUM(COALESCE(tbr.rank_days, 0)) OVER w, 0) as cumul_rem_days,
                            GREATEST(oa.cumulative_allocated_hours - SUM(COALESCE(tbr.rank_hours, 0)) OVER w, 0) as cumul_rem_hours
                        FROM ordered_allocations oa
                        LEFT JOIN taken_by_rank tbr
                            ON  tbr.employee_id = oa.employee_id
                            AND tbr.leave_type = oa.leave_type
                            AND tbr.overlap_group = oa.overlap_group
                            AND tbr.entry_rank = oa.fifo_rank
                        WINDOW w AS (PARTITION BY oa.employee_id, oa.leave_type, oa.overlap_group ORDER BY oa.fifo_rank)
                    ) sub
                    WINDOW w AS (PARTITION BY sub.employee_id, sub.leave_type, sub.overlap_group ORDER BY sub.fifo_rank)
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
						fb.date_from::timestamp + interval '12 hours' as date_from,
						fb.date_to::timestamp + interval '12 hours' as date_to,
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
						employee.department_id as department_id,
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
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """
        Override read_group to fix Total calculation for balance report: Total =  Left + Taken (= Allocated), excluding Planned.
        """
        is_grouping_by_status = groupby and any('holiday_status' in str(gb) for gb in (groupby if isinstance(groupby, list) else [groupby]))

        res = super().read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

        if not is_grouping_by_status:
            for data in res:
                group_domain = list(domain) if domain else []
                if groupby:
                    for gb_field in (groupby if isinstance(groupby, list) else [groupby]):
                        field_name = gb_field.split(':')[0]
                        if field_name in data and data[field_name]:
                            field_value = data[field_name][0] if isinstance(data[field_name], tuple) else data[field_name]
                            group_domain.append((field_name, '=', field_value))

                group_domain.append(('holiday_status', 'in', ['left', 'taken']))

                allocated_records = self.search_read(group_domain, ['number_of_days', 'number_of_hours'])

                if 'number_of_days' in data:
                    data['number_of_days'] = sum(r.get('number_of_days', 0) for r in allocated_records)
                if 'number_of_hours' in data:
                    data['number_of_hours'] = sum(r.get('number_of_hours', 0) for r in allocated_records)

        return res

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
