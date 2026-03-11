# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools.sql import SQL, drop_view_if_exists


class HrLeaveAttendanceReport(models.Model):
    _name = "hr.leave.attendance.report"
    _description = "Attendance and Leave Analysis Report"
    _auto = False

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.employee_id.display_name}, {rec.date}"

    date = fields.Date("Date")
    employee_id = fields.Many2one("hr.employee", string="Employee")
    active = fields.Boolean(related="employee_id.active")
    department_id = fields.Many2one(related="employee_id.department_id", string="Department")
    job_id = fields.Many2one(related="employee_id.job_id", string="Job Position")
    schedule_id = fields.Many2one("resource.calendar", string="Working Schedule")
    expected_hours = fields.Float("Expected Hours")
    worked_hours = fields.Float("Worked Hours")
    leave_hours = fields.Float("Approved Time Off")
    difference_hours = fields.Float("Difference", help="Worked Hours - Expected Hours + Approved Time Off")

    leave_type_names = fields.Char("Time Off Types", compute="_compute_leave_attendance_fields")
    leave_ids = fields.Many2many("hr.leave", string="Time Offs", compute="_compute_leave_attendance_fields")
    attendance_ids = fields.Many2many("hr.attendance", string="Attendances", compute="_compute_leave_attendance_fields")

    @api.depends('employee_id', 'date')
    def _compute_leave_attendance_fields(self):
        today = fields.Date.today()
        min_date = today - relativedelta(years=1)
        max_date = today - relativedelta(days=1)

        leaves_by_employees = dict(self.env['hr.leave']._read_group(
            domain=[
                ('employee_id', 'in', self.employee_id.ids),
                ('state', '=', 'validate'),
                ('date_from', '<=', max_date),
                ('date_to', '>=', min_date),
            ],
            groupby=['employee_id'],
            aggregates=['id:recordset'],
        ))
        attendances_by_employees = dict(self.env['hr.attendance']._read_group(
            domain=[
                ('employee_id', 'in', self.employee_id.ids),
                ('check_in', '>=', min_date),
                ('check_in', '<=', max_date),
            ],
            groupby=['employee_id'],
            aggregates=['id:recordset'],
        ))

        for rec in self:
            leaves = leaves_by_employees.get(rec.employee_id, self.env['hr.leave'])
            rec_date_leaves = leaves.filtered(
                lambda lv: self._timestamped(lv.date_from) <= rec.date <= self._timestamped(lv.date_to),
            )
            rec.leave_ids = rec_date_leaves.ids
            leave_type_ids = rec_date_leaves.mapped('holiday_status_id')
            rec.leave_type_names = ', '.join(leave_type_ids.mapped('name'))

            attendances = attendances_by_employees.get(rec.employee_id, self.env['hr.attendance'])
            rec.attendance_ids = attendances.filtered(
                lambda att: self._timestamped(att.check_in) == rec.date,
            ).ids

    def _timestamped(self, date):
        return fields.Datetime.context_timestamp(self, date).date()

    def _with(self):
        return SQL("""
            WITH rca AS (
                     SELECT DISTINCT ON (calendar_id, dayofweek) *
                       FROM resource_calendar_attendance
                      ORDER BY calendar_id, dayofweek
                 ),
                 blocked_days AS (
                     SELECT rcl.company_id,
                            rcl.calendar_id,
                            d.day
                       FROM resource_calendar_leaves rcl
                 CROSS JOIN LATERAL generate_series(
                                        (rcl.date_from AT TIME ZONE 'UTC')::date,
                                        (rcl.date_to   AT TIME ZONE 'UTC')::date,
                                        INTERVAL '1 day'
                                    ) AS d(day)
                      WHERE rcl.resource_id IS NULL
                        AND (rcl.date_to   AT TIME ZONE 'UTC')::date >= (date_trunc('month', CURRENT_DATE) - INTERVAL '1 year')::date
                        AND (rcl.date_from AT TIME ZONE 'UTC')::date <= (CURRENT_DATE - 1)
                 ),
                 blocked_days_cal AS (
                     SELECT company_id, calendar_id, day
                       FROM blocked_days
                      WHERE calendar_id IS NOT NULL
                 ),
                 blocked_days_global AS (
                     SELECT company_id, day
                       FROM blocked_days
                      WHERE calendar_id IS NULL
                 ),
                 leave_working_days AS (
                     SELECT lv.id                    AS leave_id,
                            v.resource_calendar_id   AS calendar_id,
                            e.company_id,
                            COUNT(*)                 AS working_days
                       FROM hr_leave lv
                       JOIN hr_employee e ON e.id = lv.employee_id
                       JOIN hr_leave_type lvt ON lvt.id = lv.holiday_status_id
                       JOIN hr_version v
                         ON v.employee_id = lv.employee_id
                        AND v.contract_date_start IS NOT NULL
                        AND v.contract_date_start <= (lv.date_to   AT TIME ZONE 'UTC')::date
                        AND (v.contract_date_end IS NULL
                             OR v.contract_date_end >= (lv.date_from AT TIME ZONE 'UTC')::date)
                 CROSS JOIN LATERAL generate_series(
                                        (lv.date_from AT TIME ZONE 'UTC')::date,
                                        (lv.date_to   AT TIME ZONE 'UTC')::date,
                                        INTERVAL '1 day'
                                    ) AS d(day)
                       JOIN rca rca2
                         ON rca2.calendar_id = v.resource_calendar_id
                        AND CAST(rca2.dayofweek AS INTEGER) = (
                                CASE WHEN EXTRACT(DOW FROM d.day) = 0 THEN 6
                                     ELSE EXTRACT(DOW FROM d.day) - 1
                                END
                            )
                  LEFT JOIN blocked_days_cal bd_c
                         ON bd_c.company_id = e.company_id
                        AND bd_c.calendar_id = v.resource_calendar_id
                        AND bd_c.day = d.day
                        AND NOT lvt.include_public_holidays_in_duration
                  LEFT JOIN blocked_days_global bd_g
                         ON bd_g.company_id = e.company_id
                        AND bd_g.day = d.day
                        AND NOT lvt.include_public_holidays_in_duration
                      WHERE lv.state = 'validate'
                        AND (lv.date_to   AT TIME ZONE 'UTC')::date >= (date_trunc('month', CURRENT_DATE) - INTERVAL '1 year')::date
                        AND (lv.date_from AT TIME ZONE 'UTC')::date <= (CURRENT_DATE - 1)
                        AND bd_c.day IS NULL
                        AND bd_g.day IS NULL
                      GROUP BY lv.id, v.resource_calendar_id, e.company_id
                 ),
                 daily_leave_hours AS (
                     SELECT lv.employee_id,
                            d.day::date        AS day,
                            lwd.calendar_id,
                            lwd.company_id,
                            SUM(lv.number_of_hours / NULLIF(lwd.working_days, 0)) AS leave_hours
                       FROM hr_leave lv
                       JOIN leave_working_days lwd ON lwd.leave_id = lv.id
                 CROSS JOIN LATERAL generate_series(
                                        (lv.date_from AT TIME ZONE 'UTC')::date,
                                        (lv.date_to   AT TIME ZONE 'UTC')::date,
                                        INTERVAL '1 day'
                                    ) AS d(day)
                      WHERE lv.state = 'validate'
                        AND (lv.date_to   AT TIME ZONE 'UTC')::date >= (date_trunc('month', CURRENT_DATE) - INTERVAL '1 year')::date
                        AND (lv.date_from AT TIME ZONE 'UTC')::date <= (CURRENT_DATE - 1)
                      GROUP BY lv.employee_id, d.day::date, lwd.calendar_id, lwd.company_id
                 )
        """)

    def _select(self):
        return SQL("""
         SELECT row_number() OVER (ORDER BY gs.day DESC, emp.id) AS id,
                gs.day::date AS date,
                emp.id AS employee_id,
                rc.id AS schedule_id,
                ROUND(COALESCE(att.worked_hours, 0.0)::numeric, 2) AS worked_hours,
                ROUND(COALESCE(rc.hours_per_day, 0.0)::numeric, 2) AS expected_hours,
                ROUND(COALESCE(dlh.leave_hours, 0.0)::numeric, 2) AS leave_hours,
                (
                    ROUND(COALESCE(att.worked_hours, 0.0)::numeric, 2)
                    - ROUND(COALESCE(rc.hours_per_day, 0.0)::numeric, 2)
                    + ROUND(COALESCE(dlh.leave_hours, 0.0)::numeric, 2)
                ) AS difference_hours
        """)

    def _from(self):
        return SQL("""
                FROM hr_employee AS emp
          CROSS JOIN LATERAL generate_series(
                        (date_trunc('month', CURRENT_DATE) - INTERVAL '1 year')::date,
                        (CURRENT_DATE - 1)::date,
                        INTERVAL '1 day'
                     ) AS gs(day)
           LEFT JOIN LATERAL (
                        SELECT resource_calendar_id
                          FROM hr_version AS v
                         WHERE v.employee_id = emp.id
                           AND v.contract_date_start IS NOT NULL
                           AND v.contract_date_start <= gs.day
                           AND (v.contract_date_end >= gs.day OR v.contract_date_end IS NULL)
                           AND v.date_version <= gs.day
                         ORDER BY v.date_version DESC
                         LIMIT 1
                     ) AS ver
                  ON TRUE
        """)

    def _join_attendance(self):
        return SQL("""
            LEFT JOIN (
                       SELECT employee_id,
                              (check_in AT TIME ZONE 'UTC')::date AS check_date,
                              SUM(worked_hours) AS worked_hours
                         FROM hr_attendance
                        WHERE check_in >= date_trunc('month', CURRENT_DATE) - INTERVAL '1 year'
                          AND check_in <  CURRENT_DATE
                        GROUP BY employee_id, check_date
                      ) AS att
                   ON att.employee_id = emp.id
                  AND att.check_date = gs.day
        """)

    def _join_calendar(self):
        return SQL("""
            JOIN resource_calendar AS rc
              ON ver.resource_calendar_id = rc.id
        """)

    def _join_calendar_leaves(self):
        return SQL("""
            LEFT JOIN blocked_days_cal AS rcl_c
                   ON rcl_c.company_id = emp.company_id
                  AND rcl_c.calendar_id = rc.id
                  AND rcl_c.day = gs.day
            LEFT JOIN blocked_days_global AS rcl_g
                   ON rcl_g.company_id = emp.company_id
                  AND rcl_g.day = gs.day
        """)

    def _join_resource_calendar_attendance(self):
        return SQL("""
            JOIN rca AS rca3
              ON rc.id = rca3.calendar_id
             AND CAST(rca3.dayofweek AS INTEGER) = (
                   CASE
                        WHEN EXTRACT(DOW FROM gs.day) = 0 THEN 6
                        ELSE EXTRACT(DOW FROM gs.day) - 1
                   END
                 )  -- to map days between Odoo (Monday = 0, Tuesday = 1, ...) and Postgres (Sunday = 0, Monday = 1, ...)
        """)

    def _join_daily_leave_hours(self):
        return SQL("""
            LEFT JOIN daily_leave_hours AS dlh
                   ON dlh.employee_id = emp.id
                  AND dlh.day = gs.day
                  AND dlh.calendar_id = rc.id
                  AND dlh.company_id = emp.company_id
        """)

    def _where(self):
        return SQL("""
            WHERE rcl_c.day IS NULL
              AND rcl_g.day IS NULL
        """)

    def init(self):
        drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(SQL("""
            CREATE OR REPLACE VIEW %s AS (
                %s -- with
                %s -- select
                %s -- from
                %s -- join_attendance
                %s -- join_calendar
                %s -- join_calendar_leaves
                %s -- join_resource_calendar_attendance
                %s -- join_daily_leave_hours
                %s -- where
            )""",
                SQL.identifier(self._table),
                self._with(),
                self._select(),
                self._from(),
                self._join_attendance(),
                self._join_calendar(),
                self._join_calendar_leaves(),
                self._join_resource_calendar_attendance(),
                self._join_daily_leave_hours(),
                self._where(),
            ))
