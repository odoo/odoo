# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, time, UTC
from zoneinfo import ZoneInfo
from odoo import fields, models
from odoo.tools import SQL
from odoo.tools.date_utils import sum_intervals
from odoo.tools.intervals import Intervals


class HrAttendanceReport(models.Model):
    _name = 'hr.attendance.report'
    _description = 'Attendance Report'
    _auto = False
    _order = False

    employee_id = fields.Many2one('hr.employee', readonly=True)
    department_id = fields.Many2one('hr.department', readonly=True)
    manager_id = fields.Many2one(comodel_name='hr.employee', related="employee_id.parent_id", readonly=True, export_string_translation=False)
    check_in = fields.Datetime(readonly=True, store=True)
    check_out = fields.Datetime(readonly=True, store=True)
    worked_hours = fields.Float(readonly=True, store=True)
    expected_hours = fields.Float(readonly=True, store=True)
    overtime_hours = fields.Float(readonly=True, store=True)
    validated_overtime_hours = fields.Float(readonly=True, store=True)
    in_mode = fields.Selection(selection=[('kiosk', "Kiosk"),
                                        ('systray', "Systray"),
                                        ('manual', "Manual"),
                                        ('technical', 'Technical')],
                            readonly=True,
                            default='manual')
    out_mode = fields.Selection(selection=[('kiosk', "Kiosk"),
                                        ('systray', "Systray"),
                                        ('manual', "Manual"),
                                        ('technical', 'Technical'),
                                        ('auto_check_out', 'Automatic Check-Out')],
                            readonly=True,
                            default='manual')

    @property
    def _table_query(self):
        field_names, attendance_records = self._fetch_attendance_data()
        report_records = self._create_report_records(attendance_records, field_names)
        self._compute_attendance_metrics(report_records)
        return self._generate_report_query(report_records)

    def _fetch_attendance_data(self):
        query = """
            WITH attendance_data AS (
                SELECT
                    a.id AS attendance_id,
                    a.employee_id,
                    v.department_id,
                    a.check_in,
                    a.check_out,
                    a.in_mode,
                    a.out_mode,
                    COALESCE(v.tz, 'UTC') as employee_tz,
                    DATE_TRUNC('day', days_included_in_request AT TIME ZONE 'UTC' AT TIME ZONE COALESCE(v.tz, 'UTC')) AS day_start
                FROM hr_attendance a
                JOIN hr_employee e ON a.employee_id = e.id
                JOIN hr_version v ON e.current_version_id = v.id
                CROSS JOIN LATERAL GENERATE_SERIES(
                    DATE_TRUNC('day', a.check_in AT TIME ZONE 'UTC' AT TIME ZONE COALESCE(v.tz, 'UTC')),
                    DATE_TRUNC('day', a.check_out AT TIME ZONE 'UTC' AT TIME ZONE COALESCE(v.tz, 'UTC')),
                    INTERVAL '1 day'
                ) AS days_included_in_request
                WHERE a.check_out IS NOT NULL
                  AND e.company_id IN %(company_ids)s
            )
            SELECT
                ROW_NUMBER() OVER(ORDER BY attendance_id, check_in) AS id,
                attendance_id,
                employee_id,
                department_id,
                in_mode,
                out_mode,
                GREATEST(check_in, (day_start AT TIME ZONE employee_tz AT TIME ZONE 'UTC')) AS check_in,
                LEAST(check_out, ((day_start + INTERVAL '1 day') AT TIME ZONE employee_tz AT TIME ZONE 'UTC')) AS day_aligned_check_out
            FROM attendance_data
        """
        self.env.cr.execute(SQL(query, company_ids=tuple(self.env.companies.ids)))
        fetched_fields = [desc[0] for desc in self.env.cr.description]
        return fetched_fields, self.env.cr.fetchall()

    def _create_report_records(self, records, field_names):
        report_records = []
        for att_record in records:
            report_records.append({field_name: att_record[index] for index, field_name in enumerate(field_names)})
        return report_records

    def _compute_attendance_metrics(self, report_records):
        if not report_records:
            return
        employee_ids = [record['employee_id'] for record in report_records]
        employee_by_id = {e.id: e for e in self.env['hr.employee'].browse(employee_ids)}

        overtimes = self.env['hr.attendance.overtime.line']._read_group(
            domain=[('employee_id', 'in', employee_ids)],
            groupby=['employee_id', 'date:day'],
            aggregates=['manual_duration:sum'],
        )
        overtime_map = {(emp.id, ot_date): duration for emp, ot_date, duration in overtimes}

        approved_overtimes = self.env['hr.attendance.overtime.line']._read_group(
            domain=[('employee_id', 'in', employee_ids), ('status', '=', 'approved')],
            groupby=['employee_id', 'date:day'],
            aggregates=['manual_duration:sum'],
        )
        approved_overtime_map = {(emp.id, ot_date): duration for emp, ot_date, duration in approved_overtimes}

        for report_record in report_records:
            c_in = report_record['check_in']
            c_out = report_record.pop('day_aligned_check_out')

            emp = employee_by_id.get(report_record['employee_id'])
            employee_tz = ZoneInfo(emp._get_tz())
            local_date = c_in.astimezone(employee_tz).date()

            # 1. Worked Hours
            worked_hours = sum_intervals(Intervals([(
                (c_in).replace(tzinfo=UTC).astimezone(employee_tz),
                (c_out).replace(tzinfo=UTC).astimezone(employee_tz),
                self.env['hr.attendance']
            )]))

            # 2. Expected Hours
            resources_per_tz = {employee_tz: emp.resource_id}
            res_intervals = emp.resource_calendar_id._work_intervals_batch(
                datetime.combine(c_in.date(), time.min).replace(tzinfo=UTC),
                datetime.combine(c_in.date(), time.max).replace(tzinfo=UTC),
                resources_per_tz=resources_per_tz,
            )
            expected_hours = sum_intervals(res_intervals.get(emp.resource_id.id))

            # 3. Overtime Hours
            overtime_hours = overtime_map.get((emp.id, local_date), 0.0)
            validated_overtime_hours = approved_overtime_map.get((emp.id, local_date), 0.0)

            report_record['check_in'] = c_in
            report_record['check_out'] = c_out
            report_record['worked_hours'] = worked_hours
            report_record['expected_hours'] = expected_hours
            report_record['overtime_hours'] = overtime_hours
            report_record['validated_overtime_hours'] = validated_overtime_hours

    def _generate_report_query(self, report_records):
        if not report_records:
            return ""

        column_names = list(report_records[0].keys())
        rows = []
        for report_record in report_records:
            rows.append(tuple(report_record[column_name] for column_name in column_names))

        return SQL(
            """
            WITH report_records (%(columns)s) AS (
                VALUES %(values)s
            )
            SELECT * FROM report_records
            """,
            columns=SQL(', ').join(map(SQL.identifier, column_names)),
            values=SQL(', ').join(rows),
        )
