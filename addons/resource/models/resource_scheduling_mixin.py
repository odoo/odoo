from datetime import timedelta

from pytz import utc

from odoo import api, fields, models
from odoo.tools import SQL
from odoo.tools.date_utils import localized, sum_intervals


class ResourceSchedulingMixin(models.AbstractModel):
    """Mixin providing standardized scheduling fields and calendar-aware methods.

    Consolidates duplicated scheduling logic from planning, project_enterprise,
    and mrp into a single canonical interface. Provides:

    - Date/time range (date_start, date_end)
    - Resource & calendar assignment with automatic calendar resolution
    - Work-hour computation respecting calendars, leaves, and flexible resources
    - Overlap/conflict detection via SQL
    - Utility methods usable even without adopting the standardized field names
    """

    _name = "resource.scheduling.mixin"
    _description = "Resource Scheduling Mixin"

    # ---- Scheduling date fields ----
    date_start = fields.Datetime(
        "Scheduled Start",
        index=True,
    )
    date_end = fields.Datetime(
        "Scheduled End",
        index=True,
    )

    # ---- Resource & calendar ----
    resource_id = fields.Many2one(
        "resource.resource",
        "Resource",
        index=True,
        help="The resource (person, equipment) assigned to this schedule.",
    )
    resource_calendar_id = fields.Many2one(
        "resource.calendar",
        "Working Calendar",
        compute="_compute_resource_calendar_id",
        store=True,
        readonly=False,
    )

    # ---- Allocation ----
    allocated_hours = fields.Float(
        "Allocated Hours",
        compute="_compute_allocated_hours",
        store=True,
        readonly=False,
        help="Working hours between start and end, respecting the resource calendar.",
    )
    allocated_percentage = fields.Float(
        "Allocation %",
        default=100.0,
        help="Percentage of the resource's work capacity allocated to this schedule.",
    )

    # ---- Conflict detection ----
    schedule_overlap_count = fields.Integer(
        "Scheduling Conflicts",
        compute="_compute_schedule_overlap_count",
    )

    # ---- Index for overlap query performance ----
    _resource_schedule_idx = models.Index("(resource_id, date_start, date_end)")

    # ------------------------------------------------------------------
    # Compute methods (wired to fields)
    # ------------------------------------------------------------------

    @api.depends("resource_id", "resource_id.calendar_id")
    def _compute_resource_calendar_id(self):
        """Use the resource's calendar, falling back to the company calendar."""
        has_company = "company_id" in self._fields
        for record in self:
            if record.resource_id and record.resource_id.calendar_id:
                record.resource_calendar_id = record.resource_id.calendar_id
            elif has_company and record.company_id:
                record.resource_calendar_id = record.company_id.resource_calendar_id
            else:
                record.resource_calendar_id = record.env.company.resource_calendar_id

    @api.depends(
        "date_start",
        "date_end",
        "resource_id",
        "resource_calendar_id",
        "allocated_percentage",
    )
    def _compute_allocated_hours(self):
        """Compute working hours between date_start and date_end.

        Respects the resource calendar (including flexible resources) and
        applies ``allocated_percentage`` to scale the result.
        """
        for record in self:
            if not record.date_start or not record.date_end:
                record.allocated_hours = 0.0
                continue
            work_hours = record._scheduling_get_work_hours(
                record.date_start,
                record.date_end,
                resource=record.resource_id,
                calendar=record.resource_calendar_id,
            )
            pct = record.allocated_percentage or 100.0
            record.allocated_hours = round(work_hours * pct / 100.0, 2)

    @api.depends("date_start", "date_end", "resource_id", "allocated_percentage")
    def _compute_schedule_overlap_count(self):
        """SQL-based overlap detection for same-resource schedule conflicts.

        Two records overlap when their datetime ranges intersect AND they
        share the same resource AND their combined allocation exceeds 100%.
        Records without an id (unsaved) or without a resource are skipped.
        """
        stored = self.filtered(
            lambda r: r.id
            and isinstance(r.id, int)
            and r.resource_id
            and r.date_start
            and r.date_end
        )
        (self - stored).schedule_overlap_count = 0
        if not stored:
            return

        stored.flush_recordset(
            ["date_start", "date_end", "resource_id", "allocated_percentage"]
        )
        table = SQL.identifier(self._table)
        query = SQL(
            """
            SELECT s1.id, COUNT(s2.id)
              FROM %s s1
              JOIN %s s2
                ON s1.resource_id = s2.resource_id
               AND s1.id != s2.id
               AND s1.date_start < s2.date_end
               AND s1.date_end > s2.date_start
               AND COALESCE(s1.allocated_percentage, 100)
                 + COALESCE(s2.allocated_percentage, 100) > 100
             WHERE s1.id = ANY(%s)
             GROUP BY s1.id
            """,
            table,
            table,
            list(stored.ids),
        )
        self.env.cr.execute(query)
        counts = dict(self.env.cr.fetchall())
        for record in stored:
            record.schedule_overlap_count = counts.get(record.id, 0)

    # ------------------------------------------------------------------
    # Utility methods (usable by modules with custom field names)
    # ------------------------------------------------------------------

    def _scheduling_get_work_hours(
        self, date_start, date_end, resource=None, calendar=None
    ):
        """Compute working hours between two datetimes using the resource calendar.

        Consolidated logic handling:
        - Timezone conversion (naive → UTC)
        - Flexible resources (use ``_get_flexible_resource_valid_work_intervals``)
        - Regular resources (calendar work intervals via ``_get_valid_work_intervals``)
        - No-resource fallback (raw timedelta)

        :param date_start: datetime (naive = UTC assumed, or timezone-aware)
        :param date_end: datetime
        :param resource: optional ``resource.resource`` singleton
        :param calendar: optional ``resource.calendar`` (overrides resource's)
        :return: float (hours)
        """
        self.ensure_one()
        if not date_start or not date_end or date_end <= date_start:
            return 0.0

        # Ensure timezone-aware datetimes (naive → UTC)
        start_utc = localized(date_start)
        end_utc = localized(date_end)

        if not resource:
            # No resource — use calendar if available, else raw timedelta
            cal = calendar or self._scheduling_resolve_calendar()
            if cal:
                return cal.get_work_hours_count(
                    start_utc, end_utc, compute_leaves=True
                )
            return (end_utc - start_utc).total_seconds() / 3600.0

        # Resource assigned — delegate to resource's interval methods
        if resource._is_flexible():
            work_intervals, hours_per_day, hours_per_week = (
                resource._get_flexible_resource_valid_work_intervals(
                    start_utc, end_utc
                )
            )
            return resource._get_flexible_resource_work_hours(
                work_intervals[resource.id],
                hours_per_day[resource.id],
                hours_per_week[resource.id],
            )

        # Regular (fixed-schedule) resource
        work_intervals, _calendar_intervals = resource._get_valid_work_intervals(
            start_utc,
            end_utc,
            calendars=(calendar,) if calendar else None,
        )
        return sum_intervals(work_intervals[resource.id])

    def _scheduling_snap_to_calendar(self, date_start, date_end, calendar=None):
        """Snap start/end to the nearest work interval boundaries.

        Useful for Gantt drag-and-drop: midnight → 9:00 AM,
        Sunday → Monday 9:00 AM.  Uses ``_work_intervals_batch`` to find
        first/last work intervals in the range.

        :param date_start: datetime
        :param date_end: datetime
        :param calendar: optional ``resource.calendar`` override
        :return: tuple ``(snapped_start, snapped_end)`` as naive UTC datetimes,
                 or the original pair if no work intervals are found.
        """
        self.ensure_one()
        cal = calendar or self._scheduling_resolve_calendar()
        if not cal or not date_start or not date_end:
            return date_start, date_end

        start_utc = localized(date_start)
        end_utc = localized(date_end)

        # [False] = calendar-only intervals (no specific resource)
        intervals = cal._work_intervals_batch(start_utc, end_utc)[False]
        if not intervals:
            return date_start, date_end

        items = list(intervals)
        snapped_start = items[0][0].astimezone(utc).replace(tzinfo=None)
        snapped_end = items[-1][1].astimezone(utc).replace(tzinfo=None)
        return snapped_start, snapped_end

    def _scheduling_plan_hours(
        self, hours, date_start, resource=None, calendar=None
    ):
        """Compute end datetime by planning forward N working hours from start.

        Inverse of ``_scheduling_get_work_hours``.  Uses the calendar's
        ``plan_hours()`` with proper timezone and leave handling.

        :param hours: float — working hours to plan
        :param date_start: datetime — start point
        :param resource: optional ``resource.resource`` singleton
        :param calendar: optional ``resource.calendar`` override
        :return: datetime (end, naive UTC) or ``False`` if hours can't be planned
        """
        self.ensure_one()
        if not hours or not date_start:
            return False

        cal = calendar or self._scheduling_resolve_calendar(resource=resource)
        if not cal:
            return date_start + timedelta(hours=hours)

        start_utc = localized(date_start)
        result = cal.plan_hours(
            hours,
            start_utc,
            compute_leaves=True,
            resource=resource,
        )
        if result:
            return result.astimezone(utc).replace(tzinfo=None)
        return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _scheduling_resolve_calendar(self, resource=None):
        """Resolve the best calendar for this record.

        Resolution order:
        1. resource's calendar (if resource provided)
        2. record's resource_calendar_id field
        3. record's company_id calendar (if company_id field exists)
        4. current company's calendar
        """
        self.ensure_one()
        if resource and resource.calendar_id:
            return resource.calendar_id
        if self.resource_calendar_id:
            return self.resource_calendar_id
        if "company_id" in self._fields and self.company_id:
            return self.company_id.resource_calendar_id
        return self.env.company.resource_calendar_id
