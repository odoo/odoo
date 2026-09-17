from datetime import date

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.models import ValuesType


class ResourceCalendarAttendance(models.Model):
    _name = "resource.calendar.attendance"
    _description = "Work Detail"
    _order = "sequence, week_type, dayofweek, hour_from"

    calendar_id = fields.Many2one(
        comodel_name="resource.calendar",
        string="Resource's Calendar",
        index=True,
        required=True,
        ondelete="cascade",
    )
    duration_based = fields.Boolean(
        related="calendar_id.duration_based",
    )
    two_weeks_calendar = fields.Boolean(
        related="calendar_id.two_weeks_calendar",
        string="Calendar in 2 weeks mode",
    )
    name = fields.Char(required=True)
    sequence = fields.Integer(
        default=10,
        help="Gives the sequence of this line when displaying the resource calendar.",
    )
    dayofweek = fields.Selection(
        selection=[
            ("0", "Monday"),
            ("1", "Tuesday"),
            ("2", "Wednesday"),
            ("3", "Thursday"),
            ("4", "Friday"),
            ("5", "Saturday"),
            ("6", "Sunday"),
        ],
        string="Day of Week",
        default="0",
        index=True,
        required=True,
    )
    hour_from = fields.Float(
        string="Work from",
        default=0,
        index=True,
        required=True,
        help="Start and End time of working.\n"
        "A specific value of 24:00 is interpreted as 23:59:59.999999.",
    )
    hour_to = fields.Float(
        string="Work to",
        default=0,
        required=True,
    )
    duration_hours = fields.Float(
        string="Duration (hours)",
        compute="_compute_duration_hours",
        inverse="_inverse_duration_hours",
        store=True,
        readonly=False,
    )
    duration_days = fields.Float(
        string="Duration (days)",
        compute="_compute_duration_days",
        store=True,
        readonly=False,
    )
    day_period = fields.Selection(
        selection=[
            ("morning", "Morning"),
            ("lunch", "Break"),
            ("afternoon", "Afternoon"),
            ("full_day", "Full Day"),
        ],
        default="morning",
        required=True,
    )
    week_type = fields.Selection(
        selection=[("1", "Second"), ("0", "First")],
        string="Week Number",
        default=False,
    )
    display_type = fields.Selection(
        selection=[("line_section", "Section")],
        default=False,
        help="Technical field for UX purpose.",
    )

    @api.constrains("day_period")
    def _check_day_period(self):
        for attendance in self:
            if attendance.day_period == "lunch" and attendance.duration_based:
                raise ValidationError(
                    self.env._(
                        "%(att)s is a break attendance, You should not have such record on duration based calendar",
                        att=attendance.name,
                    )
                )

    @api.constrains("week_type", "display_type", "calendar_id")
    def _check_week_type(self):
        for attendance in self:
            if attendance.calendar_id.two_weeks_calendar and not attendance.week_type:
                raise ValidationError(
                    self.env._(
                        "%(name)s: a line on a 2 weeks calendar must belong"
                        " to the first or the second week.",
                        name=attendance.name,
                    )
                )

    @api.constrains(
        "calendar_id", "dayofweek", "week_type", "hour_from", "hour_to", "display_type"
    )
    def _check_overlap(self):
        self.calendar_id._check_attendance_ids()

    @api.constrains("hour_from", "hour_to")
    def _check_hours(self):
        for attendance in self:
            if attendance.display_type:
                continue
            if not (0.0 <= attendance.hour_from <= 23.99):
                raise ValidationError(
                    self.env._(
                        "%(name)s: 'Work from' must be between 0:00 and 23:59.",
                        name=attendance.name,
                    )
                )
            if not (0.0 <= attendance.hour_to <= 24.0):
                raise ValidationError(
                    self.env._(
                        "%(name)s: 'Work to' must be between 0:00 and 24:00.",
                        name=attendance.name,
                    )
                )
            if attendance.hour_from > attendance.hour_to:
                raise ValidationError(
                    self.env._(
                        "%(name)s: 'Work from' (%(from_)s) must not exceed 'Work to' (%(to)s).",
                        name=attendance.name,
                        from_=attendance.hour_from,
                        to=attendance.hour_to,
                    )
                )

    @api.depends("hour_from", "hour_to", "day_period")
    def _compute_duration_hours(self):
        for attendance in self:
            attendance.duration_hours = attendance._derived_duration_hours()

    @api.depends("day_period", "duration_hours", "calendar_id.hours_per_day")
    def _compute_duration_days(self):
        for attendance in self:
            if attendance.day_period == "lunch":
                attendance.duration_days = 0
            elif attendance.day_period == "full_day":
                attendance.duration_days = 1
            else:
                attendance.duration_days = (
                    0.5
                    if attendance.duration_hours
                    <= attendance.calendar_id.hours_per_day * 3 / 4
                    else 1
                )

    @api.depends("week_type", "display_type")
    def _compute_display_name(self):
        super()._compute_display_name()
        this_week_type = str(self.get_week_type(fields.Date.context_today(self)))
        section_names = {"0": self.env._("First week"), "1": self.env._("Second week")}
        section_info = {True: self.env._("this week"), False: self.env._("other week")}
        for record in self.filtered(lambda l: l.display_type == "line_section"):
            week_name = section_names.get(record.week_type)
            if not week_name:
                record.display_name = self.env._("Unassigned week")
                continue
            record.display_name = (
                f"{week_name} ({section_info[this_week_type == record.week_type]})"
            )

    def _inverse_duration_hours(self):
        for calendar, attendances in self.grouped("calendar_id").items():
            if not calendar.duration_based:
                for attendance in attendances:
                    derived = attendance._derived_duration_hours()
                    if attendance.duration_hours != derived:
                        attendance.duration_hours = derived
                continue
            for attendance in attendances:
                duration = attendance.duration_hours
                if attendance.day_period == "full_day":
                    bounds = (12 - duration / 2, 12 + duration / 2)
                elif attendance.day_period == "morning":
                    bounds = (12 - duration, 12)
                elif attendance.day_period == "afternoon":
                    bounds = (12, 12 + duration)
                else:
                    continue
                vals = {"hour_from": bounds[0], "hour_to": bounds[1]}
                if isinstance(attendance.id, int):
                    attendance.write(vals)
                else:
                    attendance.update(vals)

    @api.onchange("hour_from", "hour_to")
    def _onchange_hours(self):
        self.hour_from = min(self.hour_from, 23.99)
        self.hour_from = max(self.hour_from, 0.0)
        self.hour_to = min(self.hour_to, 24)
        self.hour_to = max(self.hour_to, 0.0)

        self.hour_to = max(self.hour_to, self.hour_from)

    def _copy_attendance_vals(self) -> ValuesType:
        self.check_singleton()
        return {
            "name": self.name,
            "dayofweek": self.dayofweek,
            "hour_from": self.hour_from,
            "hour_to": self.hour_to,
            "day_period": self.day_period,
            "week_type": self.week_type,
            "display_type": self.display_type,
            "sequence": self.sequence,
        }

    def _derived_duration_hours(self) -> float:
        self.check_singleton()
        if self.day_period == "lunch":
            return 0.0
        return max(0.0, self.hour_to - self.hour_from)

    @api.model
    def get_week_type(self, date: date) -> int:
        return (date.toordinal() - 1) // 7 % 2
