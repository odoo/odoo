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

    # ------------------------------------------------------------------
    # SQL view
    #
    # The view is built as a set of CTEs so every heavy table is scanned
    # exactly once and every join happens on plain equality keys (which the
    # planner can turn into hash joins).
    # ------------------------------------------------------------------

    def _cte_cal_workday(self):
        """ One row per (calendar, weekday) on which the calendar has working
            time.  ``dayofweek`` follows Odoo's numbering (Monday = 0 ...
            Sunday = 6), which is exactly ``EXTRACT(ISODOW) - 1``.
        """
        return SQL("""
            SELECT DISTINCT
                   calendar_id,
                   dayofweek::integer AS dayofweek
              FROM resource_calendar_attendance
        """)

    def _cte_holiday(self):
        """ Calendar-level closures (public holidays) expanded to one concrete
            row per covered day, so the exclusion can run as an equi-join on
            (company_id, calendar_id, day).  Global closures
            (``calendar_id IS NULL``) are expanded against every calendar,
            each in its own timezone.
        """
        return SQL("""
            SELECT DISTINCT
                   rcl.company_id,
                   rc.id AS calendar_id,
                   gs.day::date AS day
              FROM resource_calendar_leaves AS rcl
              JOIN resource_calendar AS rc
                ON rcl.calendar_id = rc.id OR rcl.calendar_id IS NULL
        CROSS JOIN LATERAL generate_series(
                       (rcl.date_from AT TIME ZONE 'UTC' AT TIME ZONE COALESCE(rc.tz, 'UTC'))::date,
                       (rcl.date_to   AT TIME ZONE 'UTC' AT TIME ZONE COALESCE(rc.tz, 'UTC'))::date,
                       INTERVAL '1 day'
                    ) AS gs(day)
             WHERE rcl.resource_id IS NULL
        """)

    def _cte_emp_day(self):
        """ The report grid: one row per (employee, day) over the last ~13
            months, carrying the working schedule that applied to the employee
            on that day (the most recent effective contract version).

            ``hr_version`` is scanned once and every version is expanded over
            the day span on which it is a candidate -- from
            ``GREATEST(contract_date_start, date_version)`` to
            ``contract_date_end`` -- clamped to the report window.  When several
            versions overlap a day, ``DISTINCT ON`` keeps the one with the most
            recent ``date_version``.
        """
        return SQL("""
            SELECT DISTINCT ON (v.employee_id, gs.day)
                   v.employee_id,
                   emp.company_id,
                   gs.day::date AS day,
                   v.resource_calendar_id
              FROM hr_version AS v
              JOIN hr_employee AS emp
                ON emp.id = v.employee_id
        CROSS JOIN LATERAL generate_series(
                       GREATEST(v.contract_date_start,
                                v.date_version,
                                (date_trunc('month', CURRENT_DATE) - INTERVAL '1 year')::date),
                       LEAST(v.contract_date_end, (CURRENT_DATE - 1)::date),
                       INTERVAL '1 day'
                    ) AS gs(day)
             WHERE v.contract_date_start IS NOT NULL
          ORDER BY v.employee_id, gs.day, v.date_version DESC
        """)

    def _cte_emp_cal(self):
        """ Distinct (employee, calendar) pairs actually used in the grid, with
            the calendar timezone -- i.e. the calendars a leave may have to be
            pro-rated against.
        """
        return SQL("""
            SELECT DISTINCT
                   ed.employee_id,
                   ed.company_id,
                   rc.id AS calendar_id,
                   rc.tz
              FROM emp_day AS ed
              JOIN resource_calendar AS rc
                ON rc.id = ed.resource_calendar_id
        """)

    def _cte_attendance(self):
        """ Hours worked per (employee, day), aggregated from raw attendances
            within the report window.
        """
        return SQL("""
            SELECT employee_id,
                   (check_in AT TIME ZONE 'UTC')::date AS check_date,
                   SUM(worked_hours) AS worked_hours
              FROM hr_attendance
             WHERE check_in >= (date_trunc('month', CURRENT_DATE) - INTERVAL '1 year' - INTERVAL '1 day')
               AND check_in <  (CURRENT_DATE + INTERVAL '1 day')
          GROUP BY employee_id, check_date
        """)

    def _cte_leave(self):
        """ Validated time off overlapping the report window, with the
            leave-type flag deciding whether public holidays count towards the
            leave duration.
        """
        return SQL("""
            SELECT lv.id AS leave_id,
                   lv.employee_id,
                   lv.number_of_hours,
                   lv.date_from,
                   lv.date_to,
                   lvt.include_public_holidays_in_duration
              FROM hr_leave AS lv
              JOIN hr_leave_type AS lvt
                ON lvt.id = lv.holiday_status_id
             WHERE lv.state = 'validate'
               AND lv.date_from <  (CURRENT_DATE + INTERVAL '1 day')
               AND lv.date_to   >= (date_trunc('month', CURRENT_DATE) - INTERVAL '1 year' - INTERVAL '1 day')
        """)

    def _cte_leave_day(self):
        """ Pro-rate every validated time off across the working days it covers.

            A leave stores its total ``number_of_hours`` for the whole span, so
            the per-day amount is ``number_of_hours / <working days in span>``.
            The denominator depends on the working schedule (and, unless the
            leave type includes public holidays, on closures), so the expansion
            is done once per (leave, calendar) pair.  The result is one row
            per (employee, calendar, day), ready to be joined on the grid.
        """
        return SQL("""
            SELECT charge.employee_id,
                   charge.calendar_id,
                   charge.day,
                   SUM(charge.leave_hours) AS leave_hours
              FROM (
                    SELECT ec.employee_id,
                           ec.calendar_id,
                           d.day::date AS day,
                           lv.number_of_hours
                               / COUNT(*) OVER (PARTITION BY lv.leave_id, ec.calendar_id)
                               AS leave_hours
                      FROM leave AS lv
                      JOIN emp_cal AS ec
                        ON ec.employee_id = lv.employee_id
                CROSS JOIN LATERAL generate_series(
                               (lv.date_from AT TIME ZONE 'UTC' AT TIME ZONE COALESCE(ec.tz, 'UTC'))::date,
                               (lv.date_to   AT TIME ZONE 'UTC' AT TIME ZONE COALESCE(ec.tz, 'UTC'))::date,
                               INTERVAL '1 day'
                            ) AS d(day)
                      JOIN cal_workday AS cw
                        ON cw.calendar_id = ec.calendar_id
                       AND cw.dayofweek = EXTRACT(ISODOW FROM d.day)::integer - 1
                 -- Drop public holidays from the working-day count, unless the
                 -- leave type counts them as part of the duration.  The
                 -- leave-type flag is in the ON clause so the exclusion is a
                 -- hash anti-join.
                 LEFT JOIN holiday AS h
                        ON NOT lv.include_public_holidays_in_duration
                       AND h.company_id  = ec.company_id
                       AND h.calendar_id = ec.calendar_id
                       AND h.day         = d.day::date
                     WHERE h.day IS NULL
                   ) AS charge
          GROUP BY charge.employee_id, charge.calendar_id, charge.day
        """)

    def _select(self):
        return SQL("""
            SELECT row_number() OVER (ORDER BY ed.day DESC, ed.employee_id) AS id,
                   ed.day AS date,
                   ed.employee_id AS employee_id,
                   rc.id AS schedule_id,
                   ROUND(COALESCE(att.worked_hours, 0.0)::numeric, 2) AS worked_hours,
                   ROUND(COALESCE(rc.hours_per_day, 0.0)::numeric, 2) AS expected_hours,
                   ROUND(COALESCE(ld.leave_hours, 0.0)::numeric, 2) AS leave_hours,
                   (
                       ROUND(COALESCE(att.worked_hours, 0.0)::numeric, 2)
                       - ROUND(COALESCE(rc.hours_per_day, 0.0)::numeric, 2)
                       + ROUND(COALESCE(ld.leave_hours, 0.0)::numeric, 2)
                   ) AS difference_hours
        """)

    def _from(self):
        return SQL("""
              FROM emp_day AS ed
              JOIN resource_calendar AS rc
                ON rc.id = ed.resource_calendar_id
              JOIN cal_workday AS cw
                ON cw.calendar_id = rc.id
               AND cw.dayofweek = EXTRACT(ISODOW FROM ed.day)::integer - 1
         LEFT JOIN att
                ON att.employee_id = ed.employee_id
               AND att.check_date = ed.day
         LEFT JOIN leave_day AS ld
                ON ld.employee_id = ed.employee_id
               AND ld.calendar_id = rc.id
               AND ld.day = ed.day
        """)

    def _where(self):
        return SQL("""
             WHERE NOT EXISTS (
                       SELECT 1
                         FROM holiday AS h
                        WHERE h.company_id = ed.company_id
                          AND h.calendar_id = rc.id
                          AND h.day = ed.day
                   )
        """)

    def init(self):
        drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(SQL(
            """
            CREATE OR REPLACE VIEW %s AS (
                WITH cal_workday AS MATERIALIZED (%s),
                     holiday     AS MATERIALIZED (%s),
                     emp_day     AS MATERIALIZED (%s),
                     emp_cal     AS (%s),
                     att         AS MATERIALIZED (%s),
                     leave       AS MATERIALIZED (%s),
                     leave_day   AS (%s)
                %s -- select
                %s -- from
                %s -- where
            )""",
            SQL.identifier(self._table),
            self._cte_cal_workday(),
            self._cte_holiday(),
            self._cte_emp_day(),
            self._cte_emp_cal(),
            self._cte_attendance(),
            self._cte_leave(),
            self._cte_leave_day(),
            self._select(),
            self._from(),
            self._where(),
        ))
