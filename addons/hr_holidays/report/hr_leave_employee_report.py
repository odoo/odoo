# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools import SQL


class HrLeaveEmployeeReport(models.Model):
    _name = 'hr.leave.employee.report'
    _description = 'Time Off Per Employee Summary / Report'
    _auto = False
    _order = False

    employee_id = fields.Many2one('hr.employee', string="Employee", readonly=True)
    leave_id = fields.Many2one('hr.leave', string="Time Off Request", readonly=True)
    working_schedule_aligned_date_from = fields.Datetime('Date From', readonly=True)
    number_of_days = fields.Float(readonly=True)
    number_of_hours = fields.Float(readonly=True)
    description = fields.Char()
    work_entry_type_id = fields.Many2one("hr.work.entry.type", string="Time Off Type")
    state = fields.Selection([
        ('confirm', 'To Approve'),
        ('refuse', 'Refused'),
        ('validate1', 'Second Approval'),
        ('validate', 'Approved'),
        ('cancel', 'Cancelled'),
    ])
    color = fields.Integer(string="Color", related='work_entry_type_id.color')

    @api.model
    def _search(self, domain, *args, **kwargs):
        query = super()._search(domain, *args, **kwargs)
        # an array rather than a subquery, for Postgres to filter hr_leave before the split
        domain = list(Domain(domain))
        if '|' in domain or '!' in domain:
            return query
        leave_domain = Domain.AND(
            Domain('date_to' if operator in ('>', '>=') else 'date_from', operator, value)
            for field_expr, operator, value in (item for item in domain if isinstance(item, tuple))
            if field_expr == 'working_schedule_aligned_date_from' and operator in ('>', '>=', '<', '<=')
        )
        if not query.is_empty() and not leave_domain.is_true():
            leaves = self.env['hr.leave'].sudo()._search(leave_domain)
            query.add_where(SQL("%s = ANY(ARRAY%s)", query.table.leave_id, leaves.subselect()))
        return query

    @property
    def _table_query(self):
        # no window or aggregate at this level, for the domain to be applied to hr_leave
        return SQL(
            """
            -- sorted, for the holidays of a leave to be found by binary search (WIDTH_BUCKET)
            WITH public_holiday AS MATERIALIZED (
                SELECT
                    company_id,
                    calendar_id,
                    ARRAY_AGG(date_from ORDER BY date_from) AS starts,
                    ARRAY_AGG(TSRANGE(date_from, date_to) ORDER BY date_from) AS periods,
                    MAX(date_to - date_from) AS max_duration
                  FROM resource_calendar_leaves
                 WHERE resource_id IS NULL
                   AND count_as = 'absence'
                   AND company_id IN %(company_ids)s
                   AND date_to > date_from
              GROUP BY company_id, calendar_id
            )
            SELECT
                hl.id::BIGINT * 100000 + leave_day.day_index AS id,
                hl.id AS leave_id,
                hl.employee_id,
                GREATEST(hl.date_from, leave_day.day_start) AS working_schedule_aligned_date_from,
                hl.number_of_days * leave_day.day_share AS number_of_days,
                hl.number_of_hours * leave_day.hour_share AS number_of_hours,
                hl.private_name AS description,
                hl.work_entry_type_id,
                hl.state
            FROM hr_leave hl
            -- LIMIT: as a join, the laterals below would be evaluated for every (leave, resource)
            CROSS JOIN LATERAL (
                SELECT resource.tz
                  FROM hr_employee employee
                  JOIN resource_resource resource ON resource.id = employee.resource_id
                 WHERE employee.id = hl.employee_id
                 LIMIT 1
            ) resource
            -- version at the start of the leave, as hr.employee._get_version
            LEFT JOIN LATERAL (
                SELECT version.resource_calendar_id IS NULL AS is_flexible
                  FROM hr_version version
                 WHERE version.employee_id = hl.employee_id
              ORDER BY version.active DESC,
                       version.date_version <= hl.request_date_from DESC,
                       CASE WHEN version.date_version <= hl.request_date_from THEN version.date_version END DESC,
                       version.date_version
                 LIMIT 1
            ) version ON TRUE
            JOIN hr_work_entry_type work_entry_type ON work_entry_type.id = hl.work_entry_type_id
            CROSS JOIN LATERAL (
                SELECT version.is_flexible IS TRUE
                    OR (work_entry_type.count_as != 'absence' AND work_entry_type.request_unit = 'hour') AS calendar_time
            ) spread
            LEFT JOIN resource_calendar calendar ON calendar.id = hl.resource_calendar_id
            -- an aggregate, not to be inlined in every expression using it
            CROSS JOIN LATERAL (
                SELECT COALESCE(ARRAY_AGG(period), '{}') AS periods
                  FROM public_holiday
                 CROSS JOIN LATERAL UNNEST(public_holiday.periods[
                     WIDTH_BUCKET(hl.date_from - public_holiday.max_duration, public_holiday.starts) + 1
                     :WIDTH_BUCKET(hl.date_to, public_holiday.starts)
                 ]) AS period
                 WHERE public_holiday.company_id = hl.employee_company_id
                   AND (public_holiday.calendar_id IS NULL OR public_holiday.calendar_id = hl.resource_calendar_id)
                   AND period && TSRANGE(hl.date_from, hl.date_to)
                   AND work_entry_type.include_public_holidays_in_duration IS NOT TRUE
            ) leave_public_holiday
            CROSS JOIN LATERAL (
                SELECT
                    day.day_index,
                    day.day_start,
                    CASE WHEN SUM(day.work_days) OVER () > 0
                        THEN day.work_days / SUM(day.work_days) OVER ()
                        ELSE day.calendar_hours / NULLIF(SUM(day.calendar_hours) OVER (), 0)
                    END AS day_share,
                    CASE WHEN SUM(day.work_hours) OVER () > 0
                        THEN day.work_hours / SUM(day.work_hours) OVER ()
                        ELSE day.calendar_hours / NULLIF(SUM(day.calendar_hours) OVER (), 0)
                    END AS hour_share
                FROM (
                    SELECT
                        local_day.day - local_bounds.first_day AS day_index,
                        day_bounds.day_start,
                        COALESCE(attendance.work_hours, 0) AS work_hours,
                        -- days counted as in hr.leave._get_durations
                        CASE
                            WHEN COALESCE(attendance.work_hours, 0) <= 0 THEN 0
                            WHEN work_entry_type.request_unit = 'day' THEN 1
                            WHEN attendance.duration_based THEN attendance.work_hours / NULLIF(attendance.day_hours, 0)
                            WHEN attendance.work_hours <= calendar.hours_per_day * 3 / 4 THEN 0.5
                            ELSE 1
                        END AS work_days,
                        EXTRACT(EPOCH FROM
                            LEAST(hl.date_to, day_bounds.day_stop) - GREATEST(hl.date_from, day_bounds.day_start)
                        ) / 3600 AS calendar_hours
                    FROM (
                        SELECT
                            ((hl.date_from AT TIME ZONE 'UTC') AT TIME ZONE resource.tz)::DATE AS first_day,
                            ((hl.date_to AT TIME ZONE 'UTC') AT TIME ZONE resource.tz)::DATE AS last_day
                    ) local_bounds
                    -- not a bare GENERATE_SERIES, estimated at 1000 rows per leave, which triggers JIT
                    CROSS JOIN LATERAL UNNEST(ARRAY(
                        SELECT GENERATE_SERIES(local_bounds.first_day, local_bounds.last_day, INTERVAL '1 day')
                    )) AS local_day_ts
                    CROSS JOIN LATERAL (SELECT local_day_ts::DATE AS day) local_day
                    CROSS JOIN LATERAL (
                        SELECT
                            (local_day.day::TIMESTAMP AT TIME ZONE resource.tz) AT TIME ZONE 'UTC' AS day_start,
                            ((local_day.day + 1)::TIMESTAMP AT TIME ZONE resource.tz) AT TIME ZONE 'UTC' AS day_stop
                    ) day_bounds
                    -- duration-based attendances are centered around noon
                    LEFT JOIN LATERAL (
                        SELECT
                            BOOL_AND(rca.duration_based) AS duration_based,
                            SUM(EXTRACT(EPOCH FROM slot.stop - slot.start)) / 3600 AS day_hours,
                            SUM(GREATEST(0, EXTRACT(EPOCH FROM
                                LEAST(hl.date_to, slot.stop) - GREATEST(hl.date_from, slot.start)
                            ))) / 3600 AS work_hours
                        FROM resource_calendar_attendance rca
                        CROSS JOIN LATERAL (
                            SELECT
                                CASE WHEN rca.duration_based THEN 12 - rca.duration_hours / 2 ELSE rca.hour_from END AS hour_from,
                                CASE WHEN rca.duration_based THEN 12 + rca.duration_hours / 2 ELSE rca.hour_to END AS hour_to
                        ) hours
                        CROSS JOIN LATERAL (
                            SELECT
                                ((local_day.day + hours.hour_from * INTERVAL '1 hour') AT TIME ZONE resource.tz) AT TIME ZONE 'UTC' AS start,
                                ((local_day.day + hours.hour_to * INTERVAL '1 hour') AT TIME ZONE resource.tz) AT TIME ZONE 'UTC' AS stop
                        ) slot
                        WHERE NOT spread.calendar_time
                          AND rca.calendar_id = hl.resource_calendar_id
                          AND rca.dayofweek = (EXTRACT(ISODOW FROM local_day.day)::INTEGER - 1)::VARCHAR
                          AND (
                              calendar.two_weeks_calendar IS NOT TRUE
                              OR rca.week_type = (((local_day.day - DATE '0001-01-01') / 7) %% 2)::VARCHAR
                          )
                          AND NOT TSRANGE(slot.start, slot.stop) && ANY(leave_public_holiday.periods)
                    ) attendance ON TRUE
                ) day
            ) leave_day
            WHERE hl.employee_company_id IN %(company_ids)s
              AND (hl.number_of_days > 0 OR hl.number_of_hours > 0)
              AND leave_day.day_share > 0
            """,
            company_ids=tuple(self.env.companies.ids),
        )
