# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from odoo.tools import SQL


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
    work_entry_type_id = fields.Many2one("hr.work.entry.type", string="Time Type", readonly=True)
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

        self.env.cr.execute(SQL("""
            CREATE OR REPLACE VIEW hr_leave_employee_type_report AS (%(query)s)""", query=self._query()))

    def _query(self):
        select_columns = SQL(",\n").join(map(SQL, self._select()))
        return SQL("""
            WITH
                %(ctes)s
            SELECT
                %(columns)s
            FROM (
                %(union_queries)s
            ) leaves
        """, ctes=self._get_ctes(), columns=select_columns, union_queries=self._get_union_queries())

    def _get_ctes(self):
        return SQL("""
            /* Validated leaves */
            validated_leaves as (
                SELECT
                    l.id as leave_id,
                    l.employee_id as employee_id,
                    l.number_of_days as number_of_days,
                    l.number_of_hours as number_of_hours,
                    l.work_entry_type_id as work_entry_type_id,
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
                    v.department_id as department_id,
                    allocation.work_entry_type_id as work_entry_type_id,
                    allocation.state as state,
                    allocation.date_from as date_from,
                    allocation.date_to as date_to,
                    allocation.employee_company_id as company_id,
                    CASE
                        WHEN allocation.date_from > MAX(COALESCE(allocation.date_to, 'infinity'::date)) OVER (
                            PARTITION BY allocation.employee_id, allocation.work_entry_type_id
                            ORDER BY allocation.date_from, allocation.id
                            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                        )
                        THEN 1
                        ELSE 0
                    END as is_new_group
                FROM hr_leave_allocation allocation
                JOIN hr_employee employee ON (allocation.employee_id = employee.id)
                LEFT JOIN hr_version v ON v.id = employee.current_version_id
                WHERE allocation.state = 'validate'
            ),

            /* Assign overlap group ids */
            grouped_allocations as (
                SELECT
                    ba.*,
                    SUM(ba.is_new_group) OVER (
                        PARTITION BY ba.employee_id, ba.work_entry_type_id
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
                    ga.work_entry_type_id as work_entry_type_id,
                    ga.state as state,
                    ga.date_from as date_from,
                    ga.date_to as date_to,
                    ga.company_id as company_id,
                    ga.overlap_group as overlap_group,
                    ROW_NUMBER() OVER (
                        PARTITION BY ga.employee_id, ga.work_entry_type_id, ga.overlap_group
                        ORDER BY ga.date_from, ga.allocation_id
                    ) as fifo_rank,
                    SUM(ga.number_of_days) OVER (
                        PARTITION BY ga.employee_id, ga.work_entry_type_id, ga.overlap_group
                        ORDER BY ga.date_from, ga.allocation_id
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ) as cumulative_allocated_days,
                    SUM(ga.number_of_hours) OVER (
                        PARTITION BY ga.employee_id, ga.work_entry_type_id, ga.overlap_group
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
                    vl.work_entry_type_id,
                    oa.overlap_group,
                    MIN(oa.fifo_rank) as entry_rank
                FROM validated_leaves vl
                JOIN ordered_allocations oa
                    ON  vl.employee_id = oa.employee_id
                    AND vl.work_entry_type_id = oa.work_entry_type_id
                    AND vl.date_from <= COALESCE(oa.date_to, 'infinity')
                    AND (oa.date_to IS NULL OR vl.date_to >= oa.date_from)
                GROUP BY vl.leave_id, vl.number_of_days, vl.number_of_hours,
                            vl.employee_id, vl.work_entry_type_id, oa.overlap_group
            ),

            /* Aggregate entry points by rank for cumulative summing */
            taken_by_rank as (
                SELECT
                    employee_id,
                    work_entry_type_id,
                    overlap_group,
                    entry_rank,
                    SUM(number_of_days) as rank_days,
                    SUM(number_of_hours) as rank_hours
                FROM leave_entry_points
                GROUP BY employee_id, work_entry_type_id, overlap_group, entry_rank
            ),
            %(balance_query)s
            )
        """, balance_query=self._get_balance_cte_query())

    def _select(self):
        return [
            "row_number() OVER (ORDER BY leaves.employee_id, leaves.date_from) AS id",
            "leaves.employee_id AS employee_id",
            "leaves.active_employee AS active_employee",
            "leaves.number_of_days AS number_of_days",
            "leaves.number_of_hours AS number_of_hours",
            "leaves.department_id AS department_id",
            "leaves.work_entry_type_id AS work_entry_type_id",
            "leaves.state AS state",
            "leaves.date_from AS date_from",
            "leaves.date_to AS date_to",
            "leaves.holiday_status AS holiday_status",
            "leaves.company_id AS company_id",
        ]

    def _get_balance_cte_query(self):
        return SQL("""
            /* FIFO remaining balance per allocation */
            fifo_balances as (
                SELECT
                    sub.employee_id,
                    sub.active_employee,
                    GREATEST(sub.cumul_rem_days - COALESCE(LAG(sub.cumul_rem_days) OVER w, 0), 0) as number_of_days,
                    GREATEST(sub.cumul_rem_hours - COALESCE(LAG(sub.cumul_rem_hours) OVER w, 0), 0) as number_of_hours,
                    sub.department_id,
                    sub.work_entry_type_id,
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
                        AND tbr.work_entry_type_id = oa.work_entry_type_id
                        AND tbr.overlap_group = oa.overlap_group
                        AND tbr.entry_rank = oa.fifo_rank
                    WINDOW w AS (PARTITION BY oa.employee_id, oa.work_entry_type_id, oa.overlap_group ORDER BY oa.fifo_rank)
                ) sub
                WINDOW w AS (PARTITION BY sub.employee_id, sub.work_entry_type_id, sub.overlap_group ORDER BY sub.fifo_rank)
        """)

    def _get_union_queries(self):
        remaining_balance_columns = SQL(",\n").join(map(SQL, self._remaining_balance_select_query()))
        leave_request_columns = SQL(",\n").join(map(SQL, self._leave_request_select_query()))

        return SQL("""
            /* Remaining leave balances */
            SELECT
                %(balance_columns)s
            FROM fifo_balances fb
            WHERE fb.number_of_days >= 0

            /* Planned and taken leave requests */
            UNION ALL SELECT
                %(request_columns)s
            FROM hr_leave as request
            JOIN hr_employee as employee ON (request.employee_id = employee.id)
            LEFT JOIN hr_version v ON v.id = employee.current_version_id
            WHERE request.state IN ('confirm', 'validate', 'validate1')
        """, balance_columns=remaining_balance_columns, request_columns=leave_request_columns)

    def _remaining_balance_select_query(self):
        return [
            "fb.employee_id AS employee_id",
            "fb.active_employee AS active_employee",
            "fb.number_of_days AS number_of_days",
            "fb.number_of_hours AS number_of_hours",
            "fb.department_id AS department_id",
            "fb.work_entry_type_id AS work_entry_type_id",
            "fb.state AS state",
            "fb.date_from::timestamp + interval '12 hours' AS date_from",
            "fb.date_to::timestamp + interval '12 hours' AS date_to",
            "'left' AS holiday_status",
            "fb.company_id AS company_id",
        ]

    def _leave_request_select_query(self):
        return [
            "request.employee_id AS employee_id",
            "employee.active AS active_employee",
            "request.number_of_days AS number_of_days",
            "request.number_of_hours AS number_of_hours",
            "v.department_id AS department_id",
            "request.work_entry_type_id AS work_entry_type_id",
            "request.state AS state",
            "request.date_from AS date_from",
            "request.date_to AS date_to",
            """
            CASE
                WHEN request.state IN ('validate', 'validate1') THEN 'taken'
                WHEN request.state = 'confirm' THEN 'planned'
            END AS holiday_status
            """,
            "request.employee_company_id AS company_id",
        ]

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
