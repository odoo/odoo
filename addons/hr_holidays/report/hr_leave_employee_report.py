# Part of Odoo. See LICENSE file for full copyright and licensing details.

from pytz import utc

from odoo import api, fields, models
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
    description = fields.Char()
    holiday_status_id = fields.Many2one("hr.leave.type", string="Time Off Type")
    state = fields.Selection([
        ('confirm', 'To Approve'),
        ('refuse', 'Refused'),
        ('validate1', 'Second Approval'),
        ('validate', 'Approved'),
        ('cancel', 'Cancelled'),
    ])
    is_hatched = fields.Boolean('Hatched', compute='_compute_is_hatched', store=True)
    is_striked = fields.Boolean('Striked', compute='_compute_is_hatched', store=True)
    color = fields.Integer(string="Color", related='holiday_status_id.color')

    @property
    def _table_query(self):
        fetched_leave_field_names, leave_records = self._fetch_leave_data()
        report_records = self._create_report_records_from_leave_records(leave_records, fetched_leave_field_names)
        self._compute_working_schedule_aligned_dates(report_records)
        self._compute_leave_duration(report_records)
        self._compute_is_hatched(report_records)
        return self._generate_report_query(report_records)

    def _fetch_leave_data(self):
        self._cr.execute(SQL(
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
                GREATEST(date_from, day_start) AS day_aligned_date_from,
                LEAST(date_to, (day_start + INTERVAL '1 day' - INTERVAL '1 second')) AS day_aligned_date_to
            FROM leave_data;
            """,
            company_ids=tuple(self.env.companies.ids),
        ))
        fetched_leave_field_names = [desc[0] for desc in self._cr.description]
        leave_records = self._cr.fetchall()
        return fetched_leave_field_names, leave_records

    def _compute_is_hatched(self, report_records):
        for report_record in report_records:
            report_record['is_striked'] = report_record['state'] == 'refuse'
            report_record['is_hatched'] = report_record['state'] not in ['refuse', 'validate']

    def _create_report_records_from_leave_records(self, leave_records, leave_field_names):
        report_records = [
            {field_name: leave_record[index] for index, field_name in enumerate(leave_field_names)}
            for leave_record in leave_records
        ]
        return report_records

    def _compute_working_schedule_aligned_dates(self, report_records):
        for report_record in report_records:
            start_date = report_record['day_aligned_date_from'].replace(tzinfo=utc)
            end_date = report_record['day_aligned_date_to'].replace(tzinfo=utc)
            work_intervals = self.env['hr.leave'].browse(report_record['leave_id'])\
                .resource_calendar_id._work_intervals_batch(start_date, end_date, compute_leaves=False)[False]\
                .items()
            if work_intervals:
                report_record['working_schedule_aligned_date_from'] = work_intervals[0][0].astimezone(utc).replace(tzinfo=None)
                report_record['working_schedule_aligned_date_to'] = work_intervals[-1][1].astimezone(utc).replace(tzinfo=None)
            else:
                # Fallback if no work intervals found
                report_record['working_schedule_aligned_date_from'] = start_date.replace(tzinfo=None)
                report_record['working_schedule_aligned_date_to'] = end_date.replace(tzinfo=None)

    def _compute_leave_duration(self, report_records):
        for report_record in report_records:
            # Remove the day_aligned_date_from/to as they are intermediate values for computing other values
            virtual_leave = self.env['hr.leave'].new({
                'date_from': report_record.pop('day_aligned_date_from'),
                'date_to': report_record.pop('day_aligned_date_to'),
                'employee_id': report_record['employee_id'],
                'holiday_status_id': self.env['hr.leave'].browse(report_record['leave_id']).holiday_status_id.id,
            })
            leave_duration = virtual_leave._get_durations(additional_domain=[('holiday_id', '!=', report_record['leave_id'])])[virtual_leave.id]
            report_record['number_of_days'] = leave_duration[0]
            report_record['number_of_hours'] = leave_duration[1]

    def _generate_report_query(self, report_records):
        report_records = [report_record for report_record in report_records if report_record.get('number_of_days', 0) > 0]
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
            'res_model': 'hr.leave',
        }

    @api.model
    def get_unusual_days(self, working_schedule_aligned_date_from, working_schedule_aligned_date_to=None):
        return self.env.user.employee_id._get_unusual_days(working_schedule_aligned_date_from, working_schedule_aligned_date_to)
