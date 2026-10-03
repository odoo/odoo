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
                    wet.include_public_holidays_in_duration,
                    wet.request_unit,
                    hl.request_date_from_period,
                    hl.request_date_to_period
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
                    SUM(rca.duration_hours) AS day_work_hours
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
                    ((gs.day::TIMESTAMP AT TIME ZONE lb.tz) AT TIME ZONE 'UTC') AS day_start_utc,
                    ROW_NUMBER() OVER (PARTITION BY lb.leave_id ORDER BY gs.day) AS day_rank,
                    COUNT(*)    OVER (PARTITION BY lb.leave_id)                  AS workday_count
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
                -- carry the local calendar day and its dayofweek/week_type bucket
                -- forward so Step 4 can re-join the individual attendance
                -- intervals (not just their SUM) for that exact day.

            -- Step 4: For each leave/day, sum the actual worked hours by
            -- clipping every attendance interval of that day to the leave's
            -- real [date_from, date_to] instants. This replaces the old
            -- "divide the leave total evenly" logic, which ignored that
            -- date_from/date_to can start/end mid-day (e.g. a half-day).
            ), leave_day_hours AS (
                SELECT
                    ld.leave_id,
                    ld.employee_id,
                    ld.date_from,
                    ld.date_to,
                    ld.work_entry_type_id,
                    ld.state,
                    ld.description,
                    ld.day_work_hours,
                    ld.day_start_utc,
                    SUM(
                        -- duration-based calendars: no hour window to clip against; scale by 0.5 on half-day boundaries.
                        CASE
                            WHEN rca.hour_from = rca.hour_to
                                THEN rca.duration_hours * CASE
                                    WHEN ld.day_rank = 1              AND lb.request_unit = 'half_day' AND lb.request_date_from_period = 'pm' THEN 0.5
                                    WHEN ld.day_rank = ld.workday_count AND lb.request_unit = 'half_day' AND lb.request_date_to_period   = 'am' THEN 0.5
                                    ELSE 1.0
                                END
                            ELSE GREATEST(0, EXTRACT(EPOCH FROM (
                                LEAST(ld.date_to, ((gs.day::TIMESTAMP + rca.hour_to * INTERVAL '1 hour') AT TIME ZONE lb.tz) AT TIME ZONE 'UTC')
                                -
                                GREATEST(ld.date_from, ((gs.day::TIMESTAMP + rca.hour_from * INTERVAL '1 hour') AT TIME ZONE lb.tz) AT TIME ZONE 'UTC')
                            )) / 3600.0)
                        END
                    ) AS worked_hours
                FROM leave_days AS ld
                JOIN leave_base AS lb ON lb.leave_id = ld.leave_id
                CROSS JOIN LATERAL (SELECT (ld.day_start_utc AT TIME ZONE 'UTC' AT TIME ZONE lb.tz)::DATE AS day) AS gs
                JOIN resource_calendar_attendance AS rca
                  ON rca.calendar_id = lb.resource_calendar_id
                 AND rca.day_period != 'lunch'
                 AND rca.dayofweek::INTEGER = EXTRACT(ISODOW FROM gs.day)::INTEGER - 1
                 AND (
                     (NOT lb.two_weeks_calendar AND rca.week_type IS NULL)
                     OR (lb.two_weeks_calendar AND rca.week_type = ((((gs.day - DATE '0001-01-01')::INTEGER / 7) %% 2))::TEXT)
                 )
                GROUP BY ld.leave_id, ld.employee_id, ld.date_from, ld.date_to,
                         ld.work_entry_type_id, ld.state, ld.description,
                         ld.day_work_hours, ld.day_start_utc,
                         ld.day_rank, ld.workday_count
             )

            -- Step 5: At the end we want 1 row per day containing hours and days.
            SELECT
                ROW_NUMBER() OVER(ORDER BY leave_id, day_start_utc) AS id,
                leave_id,
                employee_id,
                GREATEST(date_from, day_start_utc) AS working_schedule_aligned_date_from,
                worked_hours / NULLIF(day_work_hours, 0) AS number_of_days,
                worked_hours AS number_of_hours,
                description,
                work_entry_type_id,
                state
            FROM leave_day_hours
            WHERE worked_hours > 0
            """,
            company_ids=tuple(self.env.companies.ids),
        )
