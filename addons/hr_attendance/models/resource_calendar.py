from odoo import api, models


class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    # Changing any of these re-prices every attendance worked against this
    # schedule. `attendance_ids` is handled by the lines themselves, below,
    # so that editing one line refreshes as much as replacing the whole set.
    _ATTENDANCE_DERIVING_FIELDS = frozenset(
        {"tz", "two_weeks_calendar", "flexible_hours"}
    )

    def write(self, vals):
        res = super().write(vals)
        if not self._ATTENDANCE_DERIVING_FIELDS.isdisjoint(vals):
            self._refresh_derived_attendance_fields()
        return res

    def _refresh_derived_attendance_fields(self):
        """Recompute the attendance fields this schedule is an input to.

        `hr.attendance.worked_hours` and `hr.attendance.date` are stored, and
        both are computed from the schedule: the first subtracts the lunch the
        calendar carries, the second localizes the check-in in the calendar's
        zone. Neither can declare that in `@api.depends`, because the schedule
        is not reached by a field path -- `_schedule_version` resolves it as a
        fixed point over the employee's versions.

        Without this hook the stored values do not follow the schedule and do
        not stay on the old one either: they keep whatever they had until some
        unrelated write to the attendance retriggers the compute, and then they
        jump. Two identical days for one employee could end up stored at eight
        and nine hours, the difference being only which of the two rows had
        been touched since.

        The set is every attendance of every employee who has ever been on this
        calendar -- versions included, because an attendance is priced by the
        version in force on the day it was worked, not by the employee's
        current one. There is no smaller correct set: an attendance priced
        against this schedule is stale whatever its date.
        """
        if not self:
            return
        attendances = (
            self.env["hr.attendance"]
            .sudo()
            .search([("employee_id.version_ids.resource_calendar_id", "in", self.ids)])
        )
        if not attendances:
            return
        for name in ("date", "worked_hours"):
            self.env.add_to_compute(attendances._fields[name], attendances)


class ResourceCalendarAttendance(models.Model):
    _inherit = "resource.calendar.attendance"

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines.calendar_id._refresh_derived_attendance_fields()
        return lines

    def write(self, vals):
        # Both sides: a line moved to another calendar changes the hours of the
        # one it left as much as the one it joins.
        calendars = self.calendar_id
        res = super().write(vals)
        (calendars | self.calendar_id)._refresh_derived_attendance_fields()
        return res

    def unlink(self):
        calendars = self.calendar_id
        res = super().unlink()
        calendars._refresh_derived_attendance_fields()
        return res
