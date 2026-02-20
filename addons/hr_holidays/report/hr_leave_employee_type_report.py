# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import SQL


class HrLeaveEmployeeTypeReport(models.Model):
    _name = 'hr.leave.employee.type.report'
    _description = 'Time Off Summary / Report'
    _auto = False
    _order = "employee_id"

    employee_id = fields.Many2one('hr.employee', string="Employee", readonly=True)
    active_employee = fields.Boolean(readonly=True)
    number_of_days = fields.Float('Number of Days', readonly=True, aggregator="sum")
    number_of_hours = fields.Float('Number of Hours', readonly=True, aggregator="sum")
    department_id = fields.Many2one('hr.department', string='Department', readonly=True)
    manager_id = fields.Many2one(related="employee_id.parent_id", string="Manager", readonly=True)
    job_id = fields.Many2one(related="employee_id.current_version_id.job_id", string="Job Position", readonly=True)
    working_schedule = fields.Many2one(
        related="employee_id.current_version_id.resource_calendar_id",
        string="Working Schedule", readonly=True)
    work_entry_type_id = fields.Many2one("hr.work.entry.type", string="Time Off Type", readonly=True)
    holiday_status = fields.Selection([
        ('allocated', 'Allocated'),
        ('left', 'Left'),
    ])
    company_id = fields.Many2one('res.company', string="Company", readonly=True)

    @property
    def _table_query(self):
        return self._generate_balance_query()

    def _generate_balance_query(self):
        today = fields.Date.today()
        if self.env.context.get('active_ids'):
            employees = self.env['hr.employee'].search([
                ('id', 'in', self.env.context['active_ids']),
                ('company_id', 'in', self.env.companies.ids),
            ])
        else:
            employees = self.env['hr.employee'].search([
                ('company_id', 'in', self.env.companies.ids),
            ])

        if not employees:
            return self._empty_query()

        # Fetch all valid allocations
        allocations = self.env['hr.leave.allocation'].search([
            ('employee_id', 'in', employees.ids),
            ('state', '=', 'validate'),
            ('date_from', '<=', today),
            '|',
            ('date_to', '=', False),
            ('date_to', '>=', today),
        ])
        if not allocations:
            return self._empty_query()

        work_entry_types = allocations.work_entry_type_id
        leaves_taken = employees._get_consumed_leaves(work_entry_types)[0]

        records = []
        row_id = 1
        for employee in employees:
            for work_entry_type in leaves_taken[employee]:
                if not work_entry_type.requires_allocation or work_entry_type.hide_on_dashboard or not work_entry_type.active:
                    continue
                allocated_days = 0
                allocated_hours = 0
                remaining_days = 0
                remaining_hours = 0
                for allocation in leaves_taken[employee][work_entry_type]:
                    if not allocation:
                        continue
                    # Only count allocations valid as of today (same as dashboard)
                    if allocation.date_from <= today and (not allocation.date_to or allocation.date_to >= today):
                        allocation_data = leaves_taken[employee][work_entry_type][allocation]
                        allocated_days += allocation.number_of_days
                        allocated_hours += allocation.number_of_hours_display
                        hours_per_day = employee.resource_calendar_id.hours_per_day or 8.0
                        if work_entry_type.unit_of_measure == 'hour':
                            remaining_hours += allocation_data['virtual_remaining_leaves']
                            remaining_days += allocation_data['virtual_remaining_leaves'] / hours_per_day
                        else:
                            remaining_days += allocation_data['virtual_remaining_leaves']
                            remaining_hours += allocation_data['virtual_remaining_leaves'] * hours_per_day

                if allocated_days == 0 and allocated_hours == 0:
                    continue
                department_id = employee.department_id.id or False
                company_id = employee.company_id.id
                # ALLOCATED row — total valid allocated days for this leave type
                records.append((
                    row_id,
                    employee.id,
                    employee.active,
                    allocated_days,
                    allocated_hours,
                    department_id,
                    work_entry_type.id,
                    'allocated',
                    company_id,
                ))
                row_id += 1
                # LEFT row — remaining balance (capped at 0, matching dashboard behavior)
                records.append((
                    row_id,
                    employee.id,
                    employee.active,
                    max(0.0, remaining_days),
                    max(0.0, remaining_hours),
                    department_id,
                    work_entry_type.id,
                    'left',
                    company_id,
                ))
                row_id += 1
        if not records:
            return self._empty_query()

        return SQL(
            """
            WITH report_records (
                id, employee_id, active_employee,
                number_of_days, number_of_hours,
                department_id, work_entry_type_id,
                holiday_status, company_id
            ) AS (
                VALUES %(values)s
            )
            SELECT * FROM report_records
            """,
            values=SQL(', ').join(records),
        )

    def _empty_query(self):
        return SQL("""
            SELECT
                NULL::INTEGER AS id,
                NULL::INTEGER AS employee_id,
                NULL::BOOLEAN AS active_employee,
                NULL::REAL AS number_of_days,
                NULL::REAL AS number_of_hours,
                NULL::INTEGER AS department_id,
                NULL::INTEGER AS work_entry_type_id,
                NULL::VARCHAR AS holiday_status,
                NULL::INTEGER AS company_id
            WHERE FALSE
        """)

    @api.model
    def action_time_off_analysis(self):
        domain = [('company_id', 'in', self.env.companies.ids)]
        if self.env.context.get('active_ids'):
            domain = [('employee_id', 'in', self.env.context.get('active_ids', []))]

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
                'search_default_left_balance': True,
                'search_default_company': True,
                'search_default_employee': True,
                'group_expand': True,
            },
        }
