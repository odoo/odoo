import logging
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from .academic_lock import can_maintain_closed_year_records

_logger = logging.getLogger(__name__)


def _is_academic_manager(env):
    return (
        env.user.has_group("school_management.group_academic_year_manager")
        or env.user.has_group("school_management.group_school_admin")
        or env.is_superuser()
    )


class UniversityAcademicYear(models.Model):
    _name = "university.academic.year"
    _description = "Academic Year"
    _order = "date_start desc, name desc, id desc"

    name = fields.Char(string="Academic Year", required=True)
    image_1920 = fields.Image(string="Year Badge / Photo", max_width=1024, max_height=1024)
    date_start = fields.Date(string="Start Date", required=True)
    date_end = fields.Date(string="End Date", required=True)
    semester_ids = fields.One2many(
        "university.semester", "academic_year_id", string="Semesters"
    )
    holiday_ids = fields.One2many(
        "university.holiday", "academic_year_id", string="Holidays"
    )
    curriculum_ids = fields.One2many(
        "university.curriculum", "session_id", string="Curriculums"
    )
    curriculum_count = fields.Integer(
        string="Curriculum Count", compute="_compute_curriculum_count"
    )
    semester_count = fields.Integer(
        string="Semester Count", compute="_compute_semester_count"
    )
    timetable_slot_count = fields.Integer(
        string="Scheduled Sessions", compute="_compute_timetable_metrics"
    )
    conflict_count = fields.Integer(
        string="Schedule Conflicts", compute="_compute_timetable_metrics"
    )
    classroom_count = fields.Integer(
        string="Occupied Rooms", compute="_compute_timetable_metrics"
    )
    enrollment_count = fields.Integer(
        string="Enrolled Students", compute="_compute_timetable_metrics"
    )
    timeslot_count = fields.Integer(
        string="Timeslots", compute="_compute_timeslot_count"
    )
    current = fields.Boolean(string="Current Academic Year", default=False)
    active = fields.Boolean(string="Active", default=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("open", "Registration Open"),
            ("running", "Running"),
            ("closed", "Closed"),
            ("archived", "Archived"),
        ],
        string="State",
        default="draft",
        required=True,
    )
    semester_status = fields.Selection(
        [
            ("configured", "With Semesters"),
            ("empty", "No Semesters"),
        ],
        string="Semester Status",
        compute="_compute_semester_status",
        store=True,
    )

    _unique_name = models.Constraint(
        "UNIQUE (name)", "The academic year name must be unique."
    )
    _valid_date_range = models.Constraint(
        "CHECK (date_end >= date_start)",
        "The academic year end date must be on or after the start date.",
    )
    _one_current_year = models.UniqueIndex(
        "(current) WHERE current",
        "Only one academic year can be marked as current.",
    )

    @api.depends("curriculum_ids")
    def _compute_curriculum_count(self):
        for year in self:
            year.curriculum_count = len(year.curriculum_ids)

    @api.depends("semester_ids", "semester_ids.active")
    def _compute_semester_count(self):
        for year in self:
            year.semester_count = len(
                year.with_context(active_test=False).semester_ids.filtered(lambda s: s.active)
            )

    @api.depends("semester_ids", "semester_ids.active")
    def _compute_semester_status(self):
        for year in self:
            count = len(year.with_context(active_test=False).semester_ids.filtered(lambda s: s.active))
            year.semester_status = "configured" if count > 0 else "empty"

    def _compute_timeslot_count(self):
        count = self.env["university.timeslot"].search_count([("active", "=", True)])
        for year in self:
            year.timeslot_count = count

    def _compute_timetable_metrics(self):
        Slot = self.env["university.timetable.slot"]
        Conflict = self.env["university.timetable.conflict"]

        slot_data = dict(
            Slot._read_group(
                [("academic_year_id", "in", self.ids), ("state", "!=", "cancelled")],
                groupby=["academic_year_id"],
                aggregates=["__count"],
            )
        )
        conflict_data = dict(
            Conflict._read_group(
                [("academic_year_id", "in", self.ids), ("status", "=", "unresolved")],
                groupby=["academic_year_id"],
                aggregates=["__count"],
            )
        )
        room_data = dict(
            Slot._read_group(
                [("academic_year_id", "in", self.ids), ("classroom_id", "!=", False), ("state", "!=", "cancelled")],
                groupby=["academic_year_id"],
                aggregates=["classroom_id:count_distinct"],
            )
        )
        enrollment_data = dict(
            self.env["university.enrollment"]._read_group(
                [("academic_year_id", "in", self.ids), ("status", "=", "enrolled")],
                groupby=["academic_year_id"],
                aggregates=["__count"],
            )
        )
        for year in self:
            year.timetable_slot_count = slot_data.get(year, 0)
            year.conflict_count = conflict_data.get(year, 0)
            year.classroom_count = room_data.get(year, 0)
            year.enrollment_count = enrollment_data.get(year, 0)

    def init(self):
        super().init()
        self.env.cr.execute("""
            UPDATE university_academic_year
            SET state = CASE
                WHEN current = TRUE AND state IN ('draft', NULL) THEN 'running'
                ELSE COALESCE(state, 'draft')
            END
            WHERE state IS NULL
        """)

    @api.constrains("date_start", "date_end")
    def _check_date_range(self):
        for year in self:
            if not year.date_start or not year.date_end:
                continue

            # Overlapping active academic years check
            if year.active:
                overlapping = self.search([
                    ("id", "!=", year.id),
                    ("active", "=", True),
                    ("date_start", "<=", year.date_end),
                    ("date_end", ">=", year.date_start),
                ], limit=1)
                if overlapping:
                    raise ValidationError(
                        f"Academic year '{year.name}' overlaps with existing academic year '{overlapping.name}' "
                        f"({overlapping.date_start} to {overlapping.date_end})."
                    )

            semesters = year.with_context(active_test=False).semester_ids.filtered(lambda s: s.active)
            invalid_semester = semesters.filtered(
                lambda semester: (
                    semester.date_start
                    and semester.date_end
                    and (
                        semester.date_start < year.date_start
                        or semester.date_end > year.date_end
                    )
                )
            )[:1]
            if invalid_semester:
                raise ValidationError(
                    "Academic year dates must include all of its semester dates."
                )

    def write(self, vals):
        if not can_maintain_closed_year_records(self.env):
            closed_years = self.filtered(lambda y: y.state in ("closed", "archived"))
            if closed_years:
                is_reopening = set(vals.keys()) <= {"state"} and vals.get("state") in ("draft", "open", "running")
                if is_reopening:
                    if not _is_academic_manager(self.env):
                        raise UserError("Only an academic manager can reopen a closed or archived academic year.")
                else:
                    raise UserError("Closed and archived academic years are read-only and cannot be modified.")

        if vals.get("current"):
            other_current = self.with_context(active_test=False).search([
                ("id", "not in", self.ids),
                ("current", "=", True),
            ])
            if other_current:
                other_current.write({"current": False})
                self.env.flush_all()
            if "state" not in vals:
                for year in self:
                    if year.state == "draft":
                        vals["state"] = "running"
                        break

        return super().write(vals)

    def unlink(self):
        if not can_maintain_closed_year_records(self.env):
            if any(year.state in ("closed", "archived") for year in self):
                raise UserError("Closed and archived academic years cannot be deleted.")
        return super().unlink()

    def action_open_registration(self):
        self.ensure_one()
        return self.write({"state": "open"})

    def action_start_year(self):
        self.ensure_one()
        return self.write({"state": "running"})

    def action_close_year(self):
        self.ensure_one()
        return self.write({"state": "closed"})

    def action_archive_year(self):
        self.ensure_one()
        return self.write({"state": "archived"})

    def action_reset_draft(self):
        self.ensure_one()
        if not _is_academic_manager(self.env):
            raise UserError("Only an academic manager can reset an academic year to draft.")
        return self.with_context(allow_closed_year_write=True).write({"state": "draft"})

    def action_open_rollover(self):
        self.ensure_one()
        if self.state not in ("running", "closed"):
            raise ValidationError(
                "Rollover is available only for running or closed academic years."
            )
        return {
            "type": "ir.actions.act_window",
            "res_model": "university.year.rollover.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_source_year_id": self.id},
        }

    def action_create_semesters(self):
        self.ensure_one()
        active_semesters = self.semester_ids.filtered(lambda s: s.active)
        if active_semesters:
            raise UserError("This academic session already has semesters configured.")
        if not self.date_start or not self.date_end:
            raise UserError("Please set the academic session start and end dates first.")

        sem1_start = self.date_start
        sem1_end = sem1_start + timedelta(weeks=16) - timedelta(days=1)
        sem2_start = sem1_end + timedelta(days=1) + timedelta(weeks=5)
        sem2_end = sem2_start + timedelta(weeks=16) - timedelta(days=1)

        if self.date_end and sem2_end > self.date_end:
            sem2_end = self.date_end

        self.env["university.semester"].create([
            {
                "semester_type": "semester_1",
                "academic_year_id": self.id,
                "session_id": self.id,
                "date_start": sem1_start,
                "date_end": sem1_end,
            },
            {
                "semester_type": "semester_2",
                "academic_year_id": self.id,
                "session_id": self.id,
                "date_start": sem2_start,
                "date_end": sem2_end,
            },
        ])
        return True

    def action_view_timetable_slots(self):
        self.ensure_one()
        return {
            "name": _("Scheduled Sessions - %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "university.timetable.slot",
            "view_mode": "kanban,calendar,list,form",
            "domain": [("academic_year_id", "=", self.id)],
            "context": {
                "default_academic_year_id": self.id,
                "search_default_group_by_status": 1,
            },
        }

    def action_view_schedule(self):
        self.ensure_one()
        return {
            "name": _("Interactive Timetable - %s") % self.name,
            "type": "ir.actions.client",
            "tag": "university_schedule_view",
            "context": {
                "default_academic_year_id": self.id,
                "filters": {"academic_year_id": str(self.id)},
            },
        }

    def action_view_conflicts(self):
        self.ensure_one()
        self.env["university.timetable.conflict"]._detect_all_conflicts(academic_year_id=self.id)
        return {
            "name": _("Schedule Conflicts - %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "university.timetable.conflict",
            "view_mode": "kanban,list,form",
            "domain": [("academic_year_id", "=", self.id)],
            "context": {
                "default_academic_year_id": self.id,
                "search_default_filter_unresolved": 1,
                "search_default_group_by_type": 1,
            },
        }

    def action_view_room_occupancy(self):
        self.ensure_one()
        return {
            "name": _("Room Occupancy - %s") % self.name,
            "type": "ir.actions.act_window",
            "view_mode": "kanban,calendar,list,form",
            "res_model": "university.timetable.slot",
            "limit": 10,
            "domain": [("academic_year_id", "=", self.id), ("classroom_id", "!=", False)],
            "context": {
                "default_academic_year_id": self.id,
                "search_default_group_by_room": 1,
                "default_mode": "week",
            },
        }

    def action_view_enrollments(self):
        self.ensure_one()
        return {
            "name": _("Enrolled Students - %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "university.enrollment",
            "view_mode": "list,kanban,form",
            "domain": [("academic_year_id", "=", self.id)],
            "context": {
                "default_academic_year_id": self.id,
                "search_default_filter_enrolled": 1,
            },
        }

    def action_view_semesters(self):
        self.ensure_one()
        return {
            "name": _("Semesters - %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "university.semester",
            "view_mode": "kanban,list,form",
            "domain": [("academic_year_id", "=", self.id)],
            "context": {
                "default_academic_year_id": self.id,
            },
        }

    def action_view_curriculums(self):
        self.ensure_one()
        return {
            "name": _("Curriculums - %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "university.curriculum",
            "view_mode": "list,form",
            "domain": [("session_id", "=", self.id)],
            "context": {
                "default_session_id": self.id,
            },
        }

    def action_view_timeslots(self):
        return {
            "name": _("Teaching Timeslots"),
            "type": "ir.actions.act_window",
            "res_model": "university.timeslot",
            "view_mode": "kanban,list,form",
            "context": {
                "search_default_group_by_day": 1,
            },
        }
