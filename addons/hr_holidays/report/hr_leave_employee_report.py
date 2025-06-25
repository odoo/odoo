# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta

from pytz import utc

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
        self._compute_working_schedule_aligned_dates(report_records)
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
                GREATEST(date_from, day_start) AS day_aligned_date_from,
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

    def _compute_working_schedule_aligned_dates(self, report_records):
        calendars = self.env['resource.calendar']
        dates_to_check_by_calendar = {}

        for rec in report_records:
            leave = self.env['hr.leave'].browse(rec['leave_id'])
            calendar = leave.resource_calendar_id
            if calendar:
                calendars |= calendar
                # Since start and end dates are the same, we only need one
                target_date = rec['day_aligned_date_from'].date()

                if calendar not in dates_to_check_by_calendar:
                    dates_to_check_by_calendar[calendar] = set()
                dates_to_check_by_calendar[calendar].add(target_date)

        work_intervals_by_calendar_by_date = {}
        for calendar in calendars:
            work_intervals_by_calendar_by_date[calendar] = {}
            dates = list(dates_to_check_by_calendar.get(calendar, set()))
            if not dates:
                continue

            start_dt = fields.Datetime.to_datetime(min(dates)).replace(tzinfo=utc)
            end_dt = fields.Datetime.to_datetime(max(dates) + timedelta(days=1, seconds=-1)).replace(tzinfo=utc)
            all_intervals_data = calendar._work_intervals_batch(start_dt, end_dt, compute_leaves=False)[False]

            for start_utc, stop_utc, _ in all_intervals_data:
                day = start_utc.astimezone(utc).date()
                if day not in work_intervals_by_calendar_by_date[calendar]:
                    work_intervals_by_calendar_by_date[calendar][day] = []
                work_intervals_by_calendar_by_date[calendar][day].append((start_utc, stop_utc))

        for report_record in report_records:
            calendar = self.env['hr.leave'].browse(report_record['leave_id']).resource_calendar_id
            target_date = report_record['day_aligned_date_from'].date()
            day_intervals = work_intervals_by_calendar_by_date.get(calendar, {}).get(target_date)

            if day_intervals:
                report_record['working_schedule_aligned_date_from'] = day_intervals[0][0].astimezone(utc).replace(tzinfo=None)
                report_record['working_schedule_aligned_date_to'] = day_intervals[-1][1].astimezone(utc).replace(tzinfo=None)
            else:
                # Fallback if no work intervals found
                report_record['working_schedule_aligned_date_from'] = report_record['day_aligned_date_from']
                report_record['working_schedule_aligned_date_to'] = report_record['day_aligned_date_to']

    def _compute_leave_duration(self, report_records):
        leave_ids = [report_record['leave_id'] for report_record in report_records]
        leaves = self.env['hr.leave'].browse(leave_ids)
        holiday_status_id_by_leave_id = {leave.id: leave.holiday_status_id.id for leave in leaves}
        for report_record in report_records:
            # Remove the day_aligned_date_from/to as they are intermediate values for computing other values
            virtual_leave = self.env['hr.leave'].new({
                'date_from': report_record.pop('day_aligned_date_from'),
                'date_to': report_record.pop('day_aligned_date_to'),
                'employee_id': report_record['employee_id'],
                'holiday_status_id': holiday_status_id_by_leave_id[report_record['leave_id']],
            })
            leave_duration = virtual_leave._get_durations(additional_domain=[('holiday_id', '!=', report_record['leave_id'])])[virtual_leave.id]
            report_record['number_of_days'] = leave_duration[0]
            report_record['number_of_hours'] = leave_duration[1]

    def _generate_report_query(self, report_records):
        report_records = [report_record for report_record in report_records if report_record.get('number_of_days', 0) > 0]
        if not report_records:
            return ""

        column_names = list(report_records[0].keys())
        report_records_tuples = []
        for report_record in report_records:
            report_records_tuples.append(tuple(report_record[column_name] for column_name in column_names))

        query = SQL(
            """
                WITH report_records (%(columns)s) AS (
                    VALUES %(values)s
                )
                SELECT * FROM report_records
            """,
            columns=SQL(', ').join(map(SQL.identifier, column_names)),
            values=SQL(', ').join(report_records_tuples),
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
