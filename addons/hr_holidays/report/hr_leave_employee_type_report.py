# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models
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
    work_entry_type_id = fields.Many2one("hr.work.entry.type", string="Time Type", readonly=True)
    holiday_status = fields.Selection([
        ('allocated', 'Allocated'),
        ('left', 'Left'),
    ])
    company_id = fields.Many2one('res.company', string="Company", readonly=True)

    @property
    def _table_query(self):
        report_records = self._get_report_records()
        return self._generate_report_query(report_records)

    def _get_report_records(self):
        target_date = fields.Date.today()
        employees_by_work_entry_type = self._get_report_scope(target_date)
        if not employees_by_work_entry_type:
            return []

        relevant_types_by_employee = defaultdict(set)
        all_employee_ids = set()
        for work_entry_type_id, employee_ids in employees_by_work_entry_type.items():
            for employee_id in employee_ids:
                relevant_types_by_employee[employee_id].add(work_entry_type_id)
                all_employee_ids.add(employee_id)

        work_entry_types = self.env['hr.work.entry.type'].browse(employees_by_work_entry_type.keys())
        employees = self.env['hr.employee'].browse(all_employee_ids)

        allocation_data = work_entry_types.get_allocation_data(employees, target_date=target_date)

        report_records = []
        row_id = 1
        for employee, employee_allocation_data in allocation_data.items():
            scoped_type_ids = relevant_types_by_employee.get(employee.id, set())
            for data, allocation_work_entry_type_id in employee_allocation_data:
                if allocation_work_entry_type_id not in scoped_type_ids or not data['max_leaves']:
                    continue
                allocated_days, allocated_hours = self._get_report_duration(employee, data, 'max_leaves')
                left_days, left_hours = self._get_report_duration(employee, data, 'virtual_remaining_leaves')
                common_values = {
                    'employee_id': employee.id,
                    'active_employee': employee.active,
                    'department_id': employee.department_id.id or None,
                    'work_entry_type_id': allocation_work_entry_type_id,
                    'company_id': employee.company_id.id or None,
                }
                report_records.append({
                    'id': row_id, **common_values,
                    'number_of_days': allocated_days, 'number_of_hours': allocated_hours,
                    'holiday_status': 'allocated',
                })
                row_id += 1
                report_records.append({
                    'id': row_id, **common_values,
                    'number_of_days': left_days, 'number_of_hours': left_hours,
                    'holiday_status': 'left',
                })
                row_id += 1
        return report_records

    def _get_report_scope(self, target_date):
        self.env.flush_all()
        query = """
            SELECT DISTINCT allocation.work_entry_type_id, allocation.employee_id
              FROM hr_leave_allocation allocation
             WHERE allocation.state = 'validate'
               AND allocation.employee_company_id IN %s
               AND allocation.date_from <= %s
               AND (allocation.date_to IS NULL OR allocation.date_to >= %s)
        """
        params = [tuple(self.env.companies.ids), target_date, target_date]
        if self.env.context.get('active_ids'):
            query += " AND allocation.employee_id IN %s"
            params.append(tuple(self.env.context['active_ids']))
        self.env.cr.execute(query, params)
        employees_by_work_entry_type = defaultdict(list)
        for work_entry_type_id, employee_id in self.env.cr.fetchall():
            employees_by_work_entry_type[work_entry_type_id].append(employee_id)
        return employees_by_work_entry_type

    def _get_report_duration(self, employee, data, field_name):
        value = data[field_name]
        hours_per_day = employee.resource_calendar_id.hours_per_day or 8.0

        if data['unit_of_measure'] == 'hour':
            return value / hours_per_day, value
        return value, value * hours_per_day

    def _generate_report_query(self, report_records):
        if not report_records:
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
        column_names = list(report_records[0].keys())
        report_records_tuples = [
            tuple(report_record[column_name] for column_name in column_names)
            for report_record in report_records
        ]
        return SQL(
            """
                WITH report_records (%(columns)s) AS (
                    VALUES %(values)s
                )
                SELECT * FROM report_records
            """,
            columns=SQL(', ').join(map(SQL.identifier, column_names)),
            values=SQL(', ').join(report_records_tuples),
        )

    @api.model
    def action_time_off_analysis(self):
        domain = [('company_id', 'in', self.env.companies.ids)]
        if self.env.context.get('active_ids'):
            domain = [('employee_id', 'in', self.env.context.get('active_ids', []))]

        return {
            'name': self.env._('Balance'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave.employee.type.report',
            'view_mode': 'pivot',
            'search_view_id': [self.env.ref('hr_holidays.view_search_hr_holidays_employee_type_report').id],
            'domain': domain,
            'help': self.env._("""
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
