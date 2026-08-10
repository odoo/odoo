# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import SQL


class HrLeaveEmployeeReport(models.Model):
    _name = 'hr.leave.employee.report'
    _description = 'Time Off Per Employee Summary / Report'
    _auto = False
    _order = False

    employee_id = fields.Many2one('hr.employee', string="Employee", readonly=True)
    leave_id = fields.Many2one('hr.leave', string="Time Off Request", readonly=True)
    working_schedule_aligned_date_from = fields.Datetime('Date From', readonly=True, store=True)
    number_of_days = fields.Float(readonly=True, store=True)
    number_of_hours = fields.Float(readonly=True, store=True)
    description = fields.Char()
    work_entry_type_id = fields.Many2one("hr.work.entry.type", string="Time Type")
    state = fields.Selection([
        ('confirm', 'To Approve'),
        ('refuse', 'Refused'),
        ('validate1', 'Second Approval'),
        ('validate', 'Approved'),
        ('cancel', 'Cancelled'),
    ])
    color = fields.Integer(string="Color", related='work_entry_type_id.color')

    @property
    def _table_query(self):
        return SQL(
            """
            -- Step 1: Gather validated leave facts, calendar metadata and leave type options.
            WITH leave_base AS (
                SELECT
                    hl.id AS leave_id,
                    hl.employee_id,
                    hl.date_from,
                    hl.date_to,
                    hl.number_of_days,
                    hl.number_of_hours,
                    hl.work_entry_type_id,
                    hl.state,
                    hl.private_name AS description,
                    hl.resource_calendar_id,
                    hl.employee_company_id,
                    COALESCE(v.tz, 'UTC') AS tz,
                    COALESCE(rc.two_weeks_calendar, FALSE) AS two_weeks_calendar,
                    wet.include_public_holidays_in_duration
                FROM hr_leave AS hl
                JOIN hr_work_entry_type AS wet
                  ON wet.id = hl.work_entry_type_id
                LEFT JOIN resource_calendar AS rc
                  ON rc.id = hl.resource_calendar_id
                LEFT JOIN LATERAL (
                        SELECT hv.tz
                        FROM hr_version AS hv
                        WHERE hv.employee_id = hl.employee_id
                            AND hv.date_version <= hl.date_from::DATE
                            AND hv.contract_date_start <= hl.date_from::DATE
                            AND (hv.contract_date_end IS NULL OR hv.contract_date_end >= hl.date_from::DATE)
                        ORDER BY hv.date_version DESC
                        LIMIT 1
                ) AS v ON TRUE
                WHERE hl.employee_company_id IN %(company_ids)s
                  AND hl.employee_id IS NOT NULL
                  AND hl.date_from IS NOT NULL
                  AND hl.date_to IS NOT NULL

            -- Step 2: Pre-aggregate planned working hours per calendar/day/week bucket.
            ), cal_day_hours AS (
                SELECT
                    rca.calendar_id,
                    rca.dayofweek::INTEGER AS dayofweek,
                    rca.week_type,
                    SUM(rca.hour_to - rca.hour_from) AS day_work_hours
                FROM resource_calendar_attendance AS rca
                WHERE rca.day_period != 'lunch'
                GROUP BY rca.calendar_id, rca.dayofweek, rca.week_type

            -- Step 3: Expand each leave into local days, keep only working days, and optionally exclude public holidays.
            ), leave_days AS (
                SELECT
                    lb.leave_id,
                    lb.employee_id,
                    lb.date_from,
                    lb.date_to,
                    lb.number_of_days,
                    lb.number_of_hours,
                    lb.work_entry_type_id,
                    lb.state,
                    lb.description,
                    day_hours.day_work_hours,
                    ((gs.day::TIMESTAMP AT TIME ZONE lb.tz) AT TIME ZONE 'UTC') AS day_start_utc
                FROM leave_base AS lb
                CROSS JOIN LATERAL GENERATE_SERIES(
                    (lb.date_from AT TIME ZONE 'UTC' AT TIME ZONE lb.tz)::DATE,
                    (lb.date_to AT TIME ZONE 'UTC' AT TIME ZONE lb.tz)::DATE,
                    INTERVAL '1 day'
                ) AS gs(day)
                JOIN cal_day_hours AS day_hours
                  ON day_hours.calendar_id = lb.resource_calendar_id
                 AND day_hours.dayofweek = EXTRACT(ISODOW FROM gs.day)::INTEGER - 1
                 AND (
                     (NOT lb.two_weeks_calendar AND day_hours.week_type IS NULL)
                     OR (lb.two_weeks_calendar AND day_hours.week_type = ((((gs.day::DATE - DATE '0001-01-01')::INTEGER / 7) %% 2))::TEXT)
                 )
                 AND day_hours.day_work_hours > 0
                LEFT JOIN LATERAL (
                    SELECT 1
                    FROM resource_calendar_leaves AS rcl
                    WHERE rcl.resource_id IS NULL
                      AND rcl.company_id = lb.employee_company_id
                      AND (rcl.calendar_id = lb.resource_calendar_id OR rcl.calendar_id IS NULL)
                      AND gs.day::DATE BETWEEN
                          (rcl.date_from AT TIME ZONE 'UTC' AT TIME ZONE lb.tz)::DATE
                          AND
                          (rcl.date_to AT TIME ZONE 'UTC' AT TIME ZONE lb.tz)::DATE
                    LIMIT 1
                ) AS public_holiday ON TRUE
                WHERE lb.include_public_holidays_in_duration OR public_holiday IS NULL

            -- Step 4: Compute per-leave denominators for day split and hour weighting.
            ), leave_days_numbered AS (
                SELECT
                    ld.*,
                    COUNT(*) OVER (PARTITION BY ld.leave_id) AS workday_count,
                    SUM(ld.day_work_hours) OVER (PARTITION BY ld.leave_id) AS leave_work_hours_total
                FROM leave_days AS ld
            )

            -- Step 5: At the end we want 1 row per day containing hours and days.
            SELECT
                ROW_NUMBER() OVER(ORDER BY leave_id, day_start_utc) AS id,
                leave_id,
                employee_id,
                GREATEST(date_from, day_start_utc) AS working_schedule_aligned_date_from,
                number_of_days / workday_count::FLOAT AS number_of_days,
                number_of_hours * day_work_hours / leave_work_hours_total AS number_of_hours,
                description,
                work_entry_type_id,
                state
            FROM leave_days_numbered
            WHERE workday_count > 0
            """,
            company_ids=tuple(self.env.companies.ids),
        )
