# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import SQL

python_to_sql_types = {
    'int': 'INTEGER',
    'float': 'REAL',
    'string': 'TEXT',
    'datetime': 'TIMESTAMP',
}


class HrLeaveEmployeeReport(models.Model):
    _name = 'hr.leave.employee.report'
    _description = 'Time Off Per Employee Summary / Report'
    _auto = False
    _order = False

    employee_id = fields.Many2one('hr.employee', string="Employee", readonly=True)
    leave_id = fields.Many2one('hr.leave', string="Time Off Request", readonly=True)
    working_schedule_aligned_date_from = fields.Datetime('Date From', readonly=True, store=True)
    number_of_days = fields.Float(compute='_compute_leave_duration', readonly=True, store=True)
    number_of_hours = fields.Float(compute='_compute_leave_duration', readonly=True, store=True)
    description = fields.Char()
    holiday_status_id = fields.Many2one("hr.leave.type", string="Time Off Type")
    state = fields.Selection([
        ('confirm', 'To Approve'),
        ('refuse', 'Refused'),
        ('validate1', 'Second Approval'),
        ('validate', 'Approved'),
        ('cancel', 'Cancelled'),
    ])
    color = fields.Integer(string="Color", related='holiday_status_id.color')

    @property
    def _table_query(self):
        fetched_leave_field_names, leave_records = self._fetch_leave_data()
        report_records = self._create_report_records_from_leave_records(leave_records, fetched_leave_field_names)
        self._compute_leave_duration(report_records)
        return self._generate_report_query(report_records)

    def _fetch_leave_data(self):
        self.env.cr.execute(SQL(
            """
            WITH leave_data AS (
                SELECT
                    ROW_NUMBER() OVER(ORDER BY employee_id, days_included_in_request) AS id,
                    id AS leave_id, employee_id, date_from, date_to,
                    holiday_status_id, state, private_name AS description,
                    DATE_TRUNC('day', days_included_in_request) AS day_start
                FROM hr_leave hl
                CROSS JOIN LATERAL GENERATE_SERIES(
                    DATE_TRUNC('day', date_from),
                    DATE_TRUNC('day', date_to),
                    INTERVAL '1 day'
                ) AS days_included_in_request
                WHERE hl.employee_company_id IN %(company_ids)s
            )
            SELECT
                id, leave_id, employee_id,
                holiday_status_id, state, description,
                GREATEST(date_from, day_start) AS working_schedule_aligned_date_from,
                LEAST(date_to, (day_start + INTERVAL '1 day' - INTERVAL '1 second')) AS day_aligned_date_to
            FROM leave_data;
            """,
            company_ids=tuple(self.env.companies.ids),
        ))
        fetched_leave_field_names = [desc[0] for desc in self.env.cr.description]
        leave_records = self.env.cr.fetchall()
        return fetched_leave_field_names, leave_records

    def _create_report_records_from_leave_records(self, leave_records, leave_field_names):
        report_records = []
        for leave_record in leave_records:
            report_records.append({field_name: leave_record[index] for index, field_name in enumerate(leave_field_names)})
        return report_records

    def _compute_leave_duration(self, report_records):
        if not report_records:
            return
        leave_ids = [report_record['leave_id'] for report_record in report_records]
        leaves = self.env['hr.leave'].browse(leave_ids)
        holiday_status_id_by_leave_id = {leave.id: leave.holiday_status_id.id for leave in leaves}
        virtual_leaves_data = [{
            'date_from': report_record['working_schedule_aligned_date_from'],
            'date_to': report_record.pop('day_aligned_date_to'),
            'employee_id': report_record['employee_id'],
            'holiday_status_id': holiday_status_id_by_leave_id[report_record['leave_id']],
        } for report_record in report_records]
        virtual_leaves = self.env['hr.leave']
        for virtual_leave_data in virtual_leaves_data:
            virtual_leaves |= self.env['hr.leave'].new(virtual_leave_data)
        leaves_durations = virtual_leaves._get_durations(additional_domain=[('holiday_id', 'not in', leave_ids)])
        for report_record, virtual_leave in zip(report_records, virtual_leaves):
            duration = leaves_durations.get(virtual_leave.id, (0, 0))
            report_record['number_of_days'] = duration[0]
            report_record['number_of_hours'] = duration[1]

    def _generate_report_query(self, report_records):
        report_records = [report_record for report_record in report_records if report_record.get('number_of_days', 0) > 0]
        if not report_records:
            return ""

        column_names = list(report_records[0].keys())
        report_records_tuples = []
        for report_record in report_records:
            report_records_tuples.append(tuple(report_record[column_name] for column_name in column_names))

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
