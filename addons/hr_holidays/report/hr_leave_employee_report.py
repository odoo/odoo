# Part of Odoo. See LICENSE file for full copyright and licensing details.

from pytz import utc
from psycopg2 import sql

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
    working_schedule_aligned_date_from = fields.Datetime('Date From', compute='_compute_working_schedule_aligned_dates', readonly=True, store=True)
    working_schedule_aligned_date_to = fields.Datetime('Date To', compute='_compute_working_schedule_aligned_dates', readonly=True, store=True)
    number_of_days = fields.Float(compute='_compute_leave_duration', readonly=True, store=True)
    number_of_hours = fields.Float(compute='_compute_leave_duration', readonly=True, store=True)

    @property
    def _table_query(self):
        fetched_leave_field_names, leave_records = self._fetch_leave_data()
        report_records = self._create_report_records_from_leave_records(leave_records, fetched_leave_field_names)
        self._compute_working_schedule_aligned_dates(report_records)
        self._compute_leave_duration(report_records)
        return self._generate_report_query(report_records)

    def _fetch_leave_data(self):
        self._cr.execute(f"""
                WITH leave_data AS (
                    SELECT
                        ROW_NUMBER() OVER(ORDER BY employee_id) AS id,
                        id AS leave_id, employee_id, date_from, date_to,
                        DATE_TRUNC('month', months_included_in_request) AS month
                    FROM hr_leave hl 
                    CROSS JOIN LATERAL GENERATE_SERIES(
                        date_from, 
                        DATE_TRUNC('month', date_to) + INTERVAL '1 month' - INTERVAL '1 second',
                        INTERVAL '1 month'
                    ) AS months_included_in_request
                    WHERE hl.employee_company_id {f"IN {tuple(self.env.companies.ids)}" if len(self.env.companies.ids) > 1 else f"= {self.env.companies.id}"}
                )
                SELECT
                    id, leave_id, employee_id,
                    GREATEST(date_from, month) AS month_aligned_date_from,
                    LEAST(date_to, (month + INTERVAL '1 month' - INTERVAL '1 second')) AS month_aligned_date_to
                FROM leave_data;
        """)
        fetched_leave_field_names = [desc[0] for desc in self._cr.description]
        leave_records = self._cr.fetchall()
        return fetched_leave_field_names, leave_records

    def _create_report_records_from_leave_records(self, leave_records, leave_field_names):
        report_records = [
            { field_name: leave_record[index] for index, field_name in enumerate(leave_field_names) }
            for leave_record in leave_records
        ]
        return report_records

    def _compute_working_schedule_aligned_dates(self, report_records):
        for report_record in report_records:
            start_date = report_record['month_aligned_date_from'].replace(tzinfo=utc)
            end_date = report_record['month_aligned_date_to'].replace(tzinfo=utc)
            work_intervals = self.env['hr.leave'].browse(report_record['leave_id'])\
                .resource_calendar_id._work_intervals_batch(start_date, end_date, compute_leaves=False)[False]\
                .items()
            report_record['working_schedule_aligned_date_from'] = work_intervals[0][0].astimezone(utc).replace(tzinfo=None)
            report_record['working_schedule_aligned_date_to'] = work_intervals[-1][1].astimezone(utc).replace(tzinfo=None)

    def _compute_leave_duration(self, report_records):
        for report_record in report_records:
            # Remove the month_aligned_date_from/to as they are intermediate values for computing other values
            virtual_leave = self.env['hr.leave'].new({
                'date_from': report_record.pop('month_aligned_date_from'),
                'date_to': report_record.pop('month_aligned_date_to'),
                'employee_id': report_record['employee_id'],
                'holiday_status_id': self.env['hr.leave'].browse(report_record['leave_id']).holiday_status_id.id
            })
            leave_duration = virtual_leave._get_durations(additional_domain = [('holiday_id', '!=', report_record['leave_id'])])[virtual_leave.id]
            report_record['number_of_days'] = leave_duration[0]
            report_record['number_of_hours'] = leave_duration[1]

    def _generate_report_query(self, report_records):
        if not report_records:
            return ""

        column_names = list(report_records[0].keys())
        report_records_tuples = [tuple(report_record[column_name] for column_name in column_names) for report_record in report_records]

        query = SQL(
            """
                WITH report_records (%(columns)s) AS (
                    VALUES %(values)s
                )
                SELECT * FROM report_records
            """,
            columns=SQL(', ').join(map(SQL.identifier, column_names)),
            values=SQL(', ').join(report_records_tuples)
        )
        return query

    def action_open_record(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': self.leave_id.id,
            'res_model': 'hr.leave'
        }
