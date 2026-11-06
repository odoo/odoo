from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class UniversityClassScheduleLine(models.Model):
    _name = "university.class.schedule.line"
    _description = "Weekly Schedule Line"
    _order = "weekday, id"

    _unique_class_weekday_timeslot = models.Constraint(
        "UNIQUE (class_id, weekday, timeslot_id)",
        "A schedule line for this class section, weekday, and timeslot already exists.",
    )

    class_id = fields.Many2one(
        "university.class.section",
        string="Class Section",
        required=True,
        ondelete="cascade",
        index=True,
    )
    academic_year_id = fields.Many2one(
        "university.academic.year",
        string="Academic Year",
        related="class_id.academic_year_id",
        store=True,
        readonly=True,
        index=True,
    )
    semester_id = fields.Many2one(
        "university.semester",
        string="Semester",
        related="class_id.semester_id",
        store=True,
        readonly=True,
        index=True,
    )
    subject_id = fields.Many2one(
        "university.subject",
        string="Subject",
        related="class_id.subject_id",
        store=True,
        readonly=True,
    )
    weekday = fields.Selection(
        [
            ("0", "Monday"),
            ("1", "Tuesday"),
            ("2", "Wednesday"),
            ("3", "Thursday"),
            ("4", "Friday"),
            ("5", "Saturday"),
            ("6", "Sunday"),
        ],
        string="Weekday",
        required=True,
        default="0",
    )
    timeslot_id = fields.Many2one(
        "university.timeslot",
        string="Timeslot",
        required=True,
        domain="[('active', '=', True)]",
    )
    room_id = fields.Many2one(
        "university.classroom",
        string="Room",
        domain="[('active', '=', True), ('status', '!=', 'maintenance')]",
    )
    teacher_id = fields.Many2one(
        "university.teacher",
        string="Teacher",
        domain="[('active', '=', True)]",
    )
    active = fields.Boolean(string="Active", default=True)

    @api.onchange("class_id")
    def _onchange_class_id(self):
        if self.class_id:
            if not self.room_id and self.class_id.classroom_id:
                self.room_id = self.class_id.classroom_id
            if not self.teacher_id and self.class_id.teacher_id:
                self.teacher_id = self.class_id.teacher_id

    @api.onchange("timeslot_id")
    def _onchange_timeslot_id(self):
        if self.timeslot_id and self.timeslot_id.day_of_week:
            self.weekday = self.timeslot_id.day_of_week

    @api.onchange("room_id")
    def _onchange_room_id(self):
        if self.room_id and self.class_id and self.class_id.capacity:
            if self.room_id.capacity and self.room_id.capacity < self.class_id.capacity:
                return {
                    "warning": {
                        "title": _("Room Capacity Warning"),
                        "message": _(
                            "Warning: Room '%(room)s' capacity (%(rcap)d) is smaller than class capacity (%(ccap)d)."
                        )
                        % {
                            "room": self.room_id.name,
                            "rcap": self.room_id.capacity,
                            "ccap": self.class_id.capacity,
                        },
                    }
                }

    @api.constrains("timeslot_id")
    def _check_timeslot_hours(self):
        for line in self:
            if line.timeslot_id and line.timeslot_id.start_hour >= line.timeslot_id.end_hour:
                raise ValidationError(_("Timeslot start hour must be strictly before end hour."))
