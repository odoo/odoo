from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class UniversityClassroom(models.Model):
    _name = "university.classroom"
    _description = "University Classroom"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "building asc, name asc"

    name = fields.Char(string="Room Name / Number", required=True, tracking=True)
    building = fields.Char(string="Building", default="A", tracking=True)
    floor = fields.Char(string="Floor", default="1st Floor", tracking=True)
    capacity = fields.Integer(string="Capacity", default=40, tracking=True)
    image_1920 = fields.Image(string="Room Photo", max_width=1024, max_height=1024)
    image_128 = fields.Image(
        string="Room Thumbnail",
        related="image_1920",
        max_width=128,
        max_height=128,
        store=True,
    )
    room_type = fields.Selection(
        [
            ("lecture_hall", "Lecture Hall"),
            ("classroom", "Standard Classroom"),
            ("lab", "Laboratory"),
            ("auditorium", "Auditorium"),
        ],
        string="Room Type",
        default="classroom",
        tracking=True,
    )
    status = fields.Selection(
        [
            ("available", "Available"),
            ("maintenance", "Maintenance"),
            ("occupied", "Occupied"),
            ("inactive", "Inactive"),
        ],
        string="Status",
        default="available",
        required=True,
        tracking=True,
    )
    active = fields.Boolean(string="Active", default=True, tracking=True)
    color = fields.Integer(
        string="Room Color",
        default=0,
        help="Classroom accent color for timetable and kanban cards",
    )

    # Equipment and Amenities Checklist
    has_projector = fields.Boolean(string="Projector / Display", default=True, tracking=True)
    has_air_conditioning = fields.Boolean(string="Air Conditioning", default=True, tracking=True)
    has_wifi = fields.Boolean(string="Wi-Fi Coverage", default=True, tracking=True)
    has_sound_system = fields.Boolean(string="Audio / Mic System", default=False, tracking=True)
    has_computers = fields.Boolean(string="Computer Workstations", default=False, tracking=True)
    has_whiteboard = fields.Boolean(string="Whiteboard / Smartboard", default=True, tracking=True)
    has_video_conference = fields.Boolean(string="Video Conferencing", default=False, tracking=True)

    facilities = fields.Text(
        string="Facilities & Equipment",
        default="Projector, Whiteboard, Wi-Fi",
        help="List available equipment such as Projector, Sound System, Computers, Smart Board.",
        tracking=True,
    )
    notes = fields.Html(string="Internal Notes")

    slot_ids = fields.One2many(
        "university.timetable.slot",
        "classroom_id",
        string="Scheduled Sessions",
    )
    slot_count = fields.Integer(
        string="Session Count",
        compute="_compute_slot_count",
    )
    today_slot_count = fields.Integer(
        string="Today's Sessions",
        compute="_compute_slot_count",
    )

    @api.depends("name", "building")
    def _compute_display_name(self):
        for room in self:
            if room.building:
                room.display_name = f"[{room.building}] {room.name}"
            else:
                room.display_name = room.name

    def _compute_slot_count(self):
        today = fields.Date.context_today(self)
        Slot = self.env["university.timetable.slot"].sudo()
        slot_data = dict(
            Slot._read_group(
                [("classroom_id", "in", self.ids), ("state", "!=", "cancelled")],
                groupby=["classroom_id"],
                aggregates=["__count"],
            )
        )
        today_data = dict(
            Slot._read_group(
                [
                    ("classroom_id", "in", self.ids),
                    ("date", "=", today),
                    ("state", "!=", "cancelled"),
                ],
                groupby=["classroom_id"],
                aggregates=["__count"],
            )
        )
        for room in self:
            room.slot_count = slot_data.get(room, 0)
            room.today_slot_count = today_data.get(room, 0)

    def _check_status_rights(self):
        if not (self.env.user.has_group("school_management.group_school_admin") or self.env.is_superuser()):
            raise AccessError(_("Only University Administrators can change the room status."))

    def action_set_available(self):
        self._check_status_rights()
        self.write({"status": "available"})

    def action_set_maintenance(self):
        self._check_status_rights()
        self.write({"status": "maintenance"})

    def action_set_occupied(self):
        self._check_status_rights()
        self.write({"status": "occupied"})

    def action_set_inactive(self):
        self._check_status_rights()
        self.write({"status": "inactive"})

    def action_view_sessions(self):
        self.ensure_one()
        return {
            "name": _("Room Sessions: %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "university.timetable.slot",
            "view_mode": "calendar,kanban,list,form",
            "domain": [("classroom_id", "=", self.id)],
            "context": {
                "default_classroom_id": self.id,
                "search_default_group_by_status": 1,
            },
        }

    def action_view_today_sessions(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        return {
            "name": _("Today's Sessions: %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "university.timetable.slot",
            "view_mode": "calendar,kanban,list,form",
            "domain": [("classroom_id", "=", self.id), ("date", "=", today)],
            "context": {
                "default_classroom_id": self.id,
                "default_date": today,
            },
        }

    @api.constrains("capacity")
    def _check_capacity(self):
        for room in self:
            if room.capacity < 0:
                raise ValidationError(_("Classroom capacity cannot be negative."))
