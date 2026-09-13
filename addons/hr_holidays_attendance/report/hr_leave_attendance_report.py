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

    def _cte_bounds(self):
        return SQL("""
            SELECT (date_trunc('month', (now())::date) - INTERVAL '1 year')::date AS date_from,
                   ((now())::date - 1)::date AS date_to
        """)

    def _cte_cal_workday(self):
        """Aggregate scheduled hours per calendar/weekday, summing split shifts on the same day.
        Two-weeks calendars keep both weeks apart (`week_type`) so the join in `_from`/
        `_cte_leave_day` can pick the one that actually applies to a given real date,
        instead of blending both weeks together.
        """
        return SQL("""
            SELECT calendar_id,
                   dayofweek::integer AS dayofweek,
                   week_type,
                   SUM(duration_hours) AS hours_per_day
              FROM resource_calendar_attendance
          GROUP BY calendar_id, dayofweek, week_type
        """)

    def _sql_week_type(self, day_column):
        """Global week parity of `day_column` (an SQL expression for a date/timestamp
        column), mirroring resource.calendar.attendance.get_week_type(): the parity of
        the number of weeks since 0001-01-01 -- the same for every two-weeks calendar,
        with no per-calendar reference date needed.
        """
        return SQL("MOD((%s::date - DATE '0001-01-01') / 7, 2)", day_column)

    def _cte_emp_day(self):
        """Resolve the effective version once for every employee/day."""
        return SQL("""
            SELECT DISTINCT ON (v.employee_id, gs.day)
                   v.employee_id,
                   emp.company_id,
                   gs.day::date AS day,
                   v.resource_calendar_id,
                   COALESCE(rc.tz, 'UTC') AS tz
              FROM hr_version AS v
              JOIN hr_employee AS emp
                ON emp.id = v.employee_id
              JOIN resource_calendar AS rc
                ON rc.id = v.resource_calendar_id
        CROSS JOIN bounds AS b
        CROSS JOIN LATERAL generate_series(
                       GREATEST(v.contract_date_start, v.date_version, b.date_from),
                       LEAST(COALESCE(v.contract_date_end, b.date_to), b.date_to),
                       INTERVAL '1 day'
                   ) AS gs(day)
             WHERE v.contract_date_start IS NOT NULL
               AND v.date_version <= b.date_to
          ORDER BY v.employee_id, gs.day, v.date_version DESC
        """)

    def _cte_emp_cal(self):
        """Calendar/timezone combinations that can affect each employee in the report."""
        return SQL("""
            SELECT DISTINCT
                   employee_id,
                   company_id,
                   resource_calendar_id AS calendar_id,
                   tz
              FROM emp_day
        """)

    def _cte_holiday(self):
        return SQL("""
            SELECT DISTINCT
                   closure.company_id,
                   closure.calendar_id,
                   closure.tz,
                   closure.day
              FROM (
                    SELECT ct.company_id,
                           ct.calendar_id,
                           ct.tz,
                           gs.day::date AS day
                      FROM resource_calendar_leaves AS rcl
                      JOIN (
                            SELECT DISTINCT company_id, calendar_id, tz
                              FROM emp_cal
                           ) AS ct
                        ON ct.company_id = rcl.company_id
                       AND ct.calendar_id = rcl.calendar_id
                CROSS JOIN LATERAL generate_series(
                               (rcl.date_from AT TIME ZONE 'UTC' AT TIME ZONE ct.tz)::date,
                               (rcl.date_to AT TIME ZONE 'UTC' AT TIME ZONE ct.tz)::date,
                               INTERVAL '1 day'
                           ) AS gs(day)
                     WHERE rcl.resource_id IS NULL
                       AND rcl.calendar_id IS NOT NULL

                    UNION ALL

                    SELECT ct.company_id,
                           ct.calendar_id,
                           ct.tz,
                           gs.day::date AS day
                      FROM resource_calendar_leaves AS rcl
                      JOIN (
                            SELECT DISTINCT company_id, calendar_id, tz
                              FROM emp_cal
                           ) AS ct
                        ON ct.company_id = rcl.company_id
                CROSS JOIN LATERAL generate_series(
                               (rcl.date_from AT TIME ZONE 'UTC' AT TIME ZONE ct.tz)::date,
                               (rcl.date_to AT TIME ZONE 'UTC' AT TIME ZONE ct.tz)::date,
                               INTERVAL '1 day'
                           ) AS gs(day)
                     WHERE rcl.resource_id IS NULL
                       AND rcl.calendar_id IS NULL
                   ) AS closure
        """)

    def _cte_attendance(self):
        """Aggregate only rows that can map to a day in the report window."""
        return SQL("""
            SELECT employee_id,
                   (check_in AT TIME ZONE 'UTC')::date AS check_date,
                   SUM(worked_hours) AS worked_hours
              FROM hr_attendance
        CROSS JOIN bounds AS b
             WHERE check_in >= b.date_from - INTERVAL '1 day'
               AND check_in < b.date_to + INTERVAL '2 days'
          GROUP BY employee_id, check_date
        """)

    def _cte_leave(self):
        return SQL("""
            SELECT lv.id,
                   lv.employee_id,
                   lv.number_of_hours,
                   lv.date_from,
                   lv.date_to,
                   lvt.include_public_holidays_in_duration
              FROM hr_leave AS lv
              JOIN hr_leave_type AS lvt
                ON lvt.id = lv.holiday_status_id
        CROSS JOIN bounds AS b
             WHERE lv.state = 'validate'
               AND lv.date_from < b.date_to + INTERVAL '2 days'
               AND lv.date_to >= b.date_from - INTERVAL '1 day'
        """)

    def _cte_leave_day(self):
        """Compute leave pro-ration once per leave/calendar/timezone."""
        return SQL("""
            SELECT charge.employee_id,
                   charge.calendar_id,
                   charge.tz,
                   charge.day,
                   SUM(charge.leave_hours) AS leave_hours
              FROM (
                    SELECT ec.employee_id,
                           ec.calendar_id,
                           ec.tz,
                           d.day::date AS day,
                           lv.number_of_hours
                               / COUNT(*) OVER (
                                     PARTITION BY lv.id, ec.calendar_id, ec.tz
                                 ) AS leave_hours
                      FROM leave AS lv
                      JOIN emp_cal AS ec
                        ON ec.employee_id = lv.employee_id
                CROSS JOIN LATERAL generate_series(
                               (lv.date_from AT TIME ZONE 'UTC' AT TIME ZONE ec.tz)::date,
                               (lv.date_to AT TIME ZONE 'UTC' AT TIME ZONE ec.tz)::date,
                               INTERVAL '1 day'
                           ) AS d(day)
                      JOIN cal_workday AS cw
                        ON cw.calendar_id = ec.calendar_id
                       AND cw.dayofweek = EXTRACT(ISODOW FROM d.day)::integer - 1
                       AND (cw.week_type IS NULL OR cw.week_type::integer = %s)
                 LEFT JOIN holiday AS h
                        ON NOT lv.include_public_holidays_in_duration
                       AND h.company_id = ec.company_id
                       AND h.calendar_id = ec.calendar_id
                       AND h.tz = ec.tz
                       AND h.day = d.day::date
                     WHERE h.day IS NULL
                   ) AS charge
          GROUP BY charge.employee_id, charge.calendar_id, charge.tz, charge.day
        """, self._sql_week_type(SQL("d.day")))

    def _select(self):
        return SQL("""
            SELECT row_number() OVER (ORDER BY ed.day DESC, ed.employee_id) AS id,
                   ed.day AS date,
                   ed.employee_id,
                   rc.id AS schedule_id,
                   ROUND(COALESCE(att.worked_hours, 0.0)::numeric, 2) AS worked_hours,
                   ROUND(COALESCE(cw.hours_per_day, 0.0)::numeric, 2) AS expected_hours,
                   ROUND(COALESCE(ld.leave_hours, 0.0)::numeric, 2) AS leave_hours,
                   (
                       ROUND(COALESCE(att.worked_hours, 0.0)::numeric, 2)
                       - ROUND(COALESCE(cw.hours_per_day, 0.0)::numeric, 2)
                       + ROUND(COALESCE(ld.leave_hours, 0.0)::numeric, 2)
                   ) AS difference_hours
        """)

    def _from(self):
        return SQL("""
              FROM emp_day AS ed
              JOIN resource_calendar AS rc
                ON rc.id = ed.resource_calendar_id
              JOIN cal_workday AS cw
                ON cw.calendar_id = ed.resource_calendar_id
               AND cw.dayofweek = EXTRACT(ISODOW FROM ed.day)::integer - 1
               AND (cw.week_type IS NULL OR cw.week_type::integer = %s)
         LEFT JOIN attendance AS att
                ON att.employee_id = ed.employee_id
               AND att.check_date = ed.day
         LEFT JOIN leave_day AS ld
                ON ld.employee_id = ed.employee_id
               AND ld.calendar_id = ed.resource_calendar_id
               AND ld.tz = ed.tz
               AND ld.day = ed.day
        """, self._sql_week_type(SQL("ed.day")))

    def _where(self):
        return SQL("""
             WHERE NOT EXISTS (
                       SELECT 1
                         FROM holiday AS h
                        WHERE h.company_id = ed.company_id
                          AND h.calendar_id = ed.resource_calendar_id
                          AND h.tz = ed.tz
                          AND h.day = ed.day
                   )
        """)

    def init(self):
        drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(SQL(
            """
            CREATE OR REPLACE VIEW %s AS (
                WITH bounds       AS (%s),
                     cal_workday  AS (%s),
                     emp_day      AS (%s),
                     emp_cal      AS (%s),
                     holiday      AS (%s),
                     attendance   AS (%s),
                     leave        AS (%s),
                     leave_day    AS (%s)
                %s -- select
                %s -- from
                %s -- where
            )""",
            SQL.identifier(self._table),
            self._cte_bounds(),
            self._cte_cal_workday(),
            self._cte_emp_day(),
            self._cte_emp_cal(),
            self._cte_holiday(),
            self._cte_attendance(),
            self._cte_leave(),
            self._cte_leave_day(),
            self._select(),
            self._from(),
            self._where(),
        ))
