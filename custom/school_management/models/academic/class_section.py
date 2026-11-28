import pytz
import math
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class UniversityClassSection(models.Model):
    _name = "university.class.section"
    _description = "Class Section"

    name = fields.Char(string="Section Name", required=True)
    section_type = fields.Selection(
        [
            ("cohort", "Cohort"),
            ("course", "Course"),
        ],
        string="Section Type",
        default="cohort",
        help="Cohort sections are program/year groups. Course sections are subject-based classes.",
    )
    curriculum_line_id = fields.Many2one(
        "university.curriculum.line",
        string="Curriculum Line",
        ondelete="set null",
        help="Optional: link this class section to a Curriculum Line.",
    )
    year_level = fields.Selection(
        [
            ("1", "Year 1"),
            ("2", "Year 2"),
            ("3", "Year 3"),
            ("4", "Year 4"),
        ],
        string="Year Level",
        help="Academic year level (Year 1 to Year 4).",
    )
    program_id = fields.Many2one(
        "university.program",
        string="Major / Level",
        help="Optional: link the section to a major/program (program-level "
             "cohort sections such as 'GM-Y1-A'). Preferred over Subject for "
             "the main major enrollment flow.",
    )
    subject_id = fields.Many2one(
        "university.subject",
        string="Subject",
        domain="[('program_ids', 'in', [program_id])] if program_id else []",
        help="Set for subject-based class sections.",
    )
    teacher_id = fields.Many2one(
        "university.teacher",
        string="Instructor",
        help="Instructor for this class section.",
    )
    semester_id = fields.Many2one(
        "university.semester",
        string="Semester / Term",
        required=True,
        domain="[('academic_year_id', '=?', academic_year_id), ('active', '=', True)]",
    )
    term_id = fields.Many2one(
        "university.department.term",
        string="Department Term",
        domain="[('semester_id', '=?', semester_id), ('department_id', '=?', department_id)]",
        help="Department term schedule for this class section.",
    )
    academic_year_id = fields.Many2one(
        "university.academic.year",
        string="Academic Year",
        compute="_compute_academic_year_id",
        store=True,
        readonly=False,
    )
    department_id = fields.Many2one(
        "university.department",
        string="Department",
        related="program_id.department_id",
        store=True,
        readonly=True,
    )
    classroom_id = fields.Many2one(
        "university.classroom",
        string="Classroom",
        domain="[('active', '=', True), ('status', '!=', 'maintenance')]",
    )
    capacity = fields.Integer(string="Max Capacity", default=30)
    enrollment_ids = fields.One2many(
        "university.enrollment", "section_id", string="Enrolled Students"
    )
    schedule_line_ids = fields.One2many(
        "university.class.schedule.line",
        "class_id",
        string="Weekly Schedule",
    )
    slot_ids = fields.One2many(
        "university.timetable.slot", "section_id", string="Timetable Slots"
    )
    slot_count = fields.Integer(
        string="Sessions Count",
        compute="_compute_slot_count",
    )
    active = fields.Boolean(string="Active", default=True)
    auto_quiz_per_session = fields.Boolean(
        string="Auto-Quiz per Session",
        default=False,
        help="If enabled, the system automatically creates a quiz when a timetable session starts.",
    )
    enrolled_student_count = fields.Integer(
        string="Enrolled Count",
        compute="_compute_enrolled_student_count",
        store=True,
    )
    available_seats = fields.Integer(
        string="Available Seats",
        compute="_compute_capacity_status",
        store=True,
    )
    has_available_seats = fields.Boolean(
        string="Has Available Seats",
        compute="_compute_capacity_status",
        store=True,
    )
    capacity_used_percent = fields.Integer(
        string="Capacity Used",
        compute="_compute_capacity_status",
        store=True,
    )
    is_full = fields.Boolean(
        string="Full",
        compute="_compute_capacity_status",
        store=True,
    )
    day_summary = fields.Char(
        string="Days",
        compute="_compute_schedule_summary",
        store=True,
    )
    time_summary = fields.Char(
        string="Time",
        compute="_compute_schedule_summary",
        store=True,
    )
    schedule_summary = fields.Char(
        string="Schedule Summary",
        compute="_compute_schedule_summary",
        store=True,
    )
    schedule_warning = fields.Char(
        string="Schedule Warning",
        compute="_compute_schedule_warning",
    )
    assignment_ids = fields.One2many(
        "university.assignment",
        "section_id",
        string="Assignments",
    )
    assignment_count = fields.Integer(
        string="Assignments Count",
        compute="_compute_assignment_count",
    )
    exam_ids = fields.One2many(
        "university.exam",
        "section_id",
        string="Exams & Quizzes",
    )
    exam_count = fields.Integer(
        string="Exams Count",
        compute="_compute_exam_count",
    )
    date_start = fields.Date(
        string="Start Date",
        help="Custom class start date (overrides term start date).",
    )
    date_end = fields.Date(
        string="End Date",
        help="Custom class end date (overrides term end date).",
    )
    timeline = fields.Char(
        string="Timeline",
        compute="_compute_timeline",
    )
    state = fields.Selection(
        [
            ("draft", "New"),
            ("confirmed", "Confirmed"),
        ],
        string="Status",
        default="confirmed",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if not res.get("semester_id") and res.get("subject_id") and res.get("program_id") and res.get("academic_year_id"):
            cline = self.env["university.curriculum.line"].search([
                ("program_id", "=", res["program_id"]),
                ("subject_id", "=", res["subject_id"]),
            ], limit=1)
            if cline and cline.semester_number:
                sem = self.env["university.semester"].search([
                    ("academic_year_id", "=", res["academic_year_id"]),
                    ("active", "=", True),
                    "|", ("semester_type", "=", f"semester_{cline.semester_number}"),
                    ("name", "=", f"Semester {cline.semester_number}"),
                ], limit=1)
                if sem:
                    res["semester_id"] = sem.id
        return res

    @api.depends("semester_id", "semester_id.academic_year_id")
    def _compute_academic_year_id(self):
        for rec in self:
            if rec.semester_id and rec.semester_id.academic_year_id:
                rec.academic_year_id = rec.semester_id.academic_year_id
            elif not rec.academic_year_id:
                rec.academic_year_id = False

    @api.onchange("term_id")
    def _onchange_term_id(self):
        if self.term_id:
            if self.term_id.semester_id:
                self.semester_id = self.term_id.semester_id
            if self.term_id.academic_year_id:
                self.academic_year_id = self.term_id.academic_year_id

    @api.onchange("curriculum_line_id")
    def _onchange_curriculum_line_id(self):
        if self.curriculum_line_id:
            if self.curriculum_line_id.subject_id:
                self.subject_id = self.curriculum_line_id.subject_id
            if self.curriculum_line_id.year_level:
                self.year_level = self.curriculum_line_id.year_level
            if self.curriculum_line_id.program_id and not self.program_id:
                self.program_id = self.curriculum_line_id.program_id
            elif (
                self.curriculum_line_id.curriculum_id
                and self.curriculum_line_id.curriculum_id.program_id
                and not self.program_id
            ):
                self.program_id = self.curriculum_line_id.curriculum_id.program_id
            if self.curriculum_line_id.semester_number and self.academic_year_id and not self.semester_id:
                sem_type = f"semester_{self.curriculum_line_id.semester_number}"
                sem = self.env["university.semester"].search([
                    ("academic_year_id", "=", self.academic_year_id.id),
                    ("active", "=", True),
                    "|", ("semester_type", "=", sem_type),
                    ("name", "=", f"Semester {self.curriculum_line_id.semester_number}"),
                ], limit=1)
                if sem:
                    self.semester_id = sem

    @api.onchange("subject_id", "program_id")
    def _onchange_subject_and_program_default_term(self):
        if self.subject_id and self.program_id and self.academic_year_id and not self.semester_id:
            cline = self.env["university.curriculum.line"].search([
                ("program_id", "=", self.program_id.id),
                ("subject_id", "=", self.subject_id.id),
            ], limit=1)
            if cline and cline.semester_number:
                sem_type = f"semester_{cline.semester_number}"
                sem = self.env["university.semester"].search([
                    ("academic_year_id", "=", self.academic_year_id.id),
                    ("active", "=", True),
                    "|", ("semester_type", "=", sem_type),
                    ("name", "=", f"Semester {cline.semester_number}"),
                ], limit=1)
                if sem:
                    self.semester_id = sem

    @api.depends("enrollment_ids", "enrollment_ids.status")
    def _compute_enrolled_student_count(self):
        for section in self:
            section.enrolled_student_count = len(
                section.enrollment_ids.filtered(lambda e: e.status == "enrolled")
            )

    @api.depends("capacity", "enrolled_student_count")
    def _compute_capacity_status(self):
        for section in self:
            if section.capacity:
                section.capacity_used_percent = min(
                    100,
                    round(section.enrolled_student_count * 100 / section.capacity),
                )
                section.is_full = section.enrolled_student_count >= section.capacity
                section.available_seats = max(0, section.capacity - section.enrolled_student_count)
                section.has_available_seats = section.available_seats > 0
            else:
                section.capacity_used_percent = 0
                section.is_full = False
                section.available_seats = 0
                section.has_available_seats = False

    @api.depends("assignment_ids")
    def _compute_assignment_count(self):
        for section in self:
            section.assignment_count = len(section.assignment_ids)

    @api.depends("exam_ids")
    def _compute_exam_count(self):
        for section in self:
            section.exam_count = len(section.exam_ids)

    def action_view_assignments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Assignments - %s") % self.name,
            "res_model": "university.assignment",
            "view_mode": "list,form",
            "domain": [("section_id", "=", self.id)],
            "context": {
                "default_section_id": self.id,
                "default_subject_id": self.subject_id.id if self.subject_id else False,
                "default_teacher_id": self.teacher_id.id if self.teacher_id else False,
            },
        }

    def action_download_class_marksheet(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/university/class_marksheet/{self.id}/xlsx",
            "target": "self",
        }

    def action_print_class_marksheet_pdf(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/university/class_marksheet/{self.id}/pdf",
            "target": "self",
        }

    def action_view_exams(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Exams & Quizzes - %s") % self.name,
            "res_model": "university.exam",
            "view_mode": "list,form,pivot,graph",
            "domain": [("section_id", "=", self.id)],
            "context": {
                "default_section_id": self.id,
                "default_subject_id": self.subject_id.id if self.subject_id else False,
                "default_teacher_id": self.teacher_id.id if self.teacher_id else False,
                "default_semester_id": self.semester_id.id if self.semester_id else False,
                "default_academic_year_id": self.academic_year_id.id if self.academic_year_id else False,
            },
        }

    @api.depends("slot_ids")
    def _compute_slot_count(self):
        for section in self:
            section.slot_count = len(section.slot_ids)

    @api.depends(
        "schedule_line_ids.active",
        "schedule_line_ids.weekday",
        "schedule_line_ids.timeslot_id",
        "schedule_line_ids.room_id",
        "slot_ids.start_time",
        "slot_ids.end_time",
        "slot_ids.classroom_id",
    )
    def _compute_schedule_summary(self):
        weekday_short = {
            "0": "Mon",
            "1": "Tue",
            "2": "Wed",
            "3": "Thu",
            "4": "Fri",
            "5": "Sat",
            "6": "Sun",
        }
        for section in self:
            active_lines = section.schedule_line_ids.filtered(lambda l: l.active)
            if active_lines:
                days = []
                times = []
                details = []
                sorted_lines = active_lines.sorted(
                    key=lambda l: (
                        l.weekday or "0",
                        l.timeslot_id.start_hour if l.timeslot_id else 0,
                    )
                )
                for l in sorted_lines:
                    day = weekday_short.get(l.weekday, "Day")
                    if day not in days:
                        days.append(day)
                    t_name = ""
                    if l.timeslot_id:
                        t_name = "%s-%s" % (
                            l.timeslot_id._format_hour(l.timeslot_id.start_hour),
                            l.timeslot_id._format_hour(l.timeslot_id.end_hour),
                        )
                        if t_name not in times:
                            times.append(t_name)
                    room = f" ({l.room_id.name})" if l.room_id else ""
                    desc = f"{day} {t_name}{room}".strip()
                    if desc and desc not in details:
                        details.append(desc)
                section.day_summary = ", ".join(days)
                section.time_summary = ", ".join(times[:2])
                section.schedule_summary = "; ".join(details[:3]) + (
                    "..." if len(details) > 3 else ""
                )
            elif section.slot_ids:
                days = []
                times = []
                details = []
                slots = section.slot_ids.sorted(key=lambda s: s.start_time or fields.Datetime.now())
                for s in slots:
                    if s.start_time:
                        slot_dt = fields.Datetime.context_timestamp(section, s.start_time)
                        day_name = slot_dt.strftime("%a")
                        if day_name not in days:
                            days.append(day_name)
                        time_range = slot_dt.strftime("%H:%M")
                        if s.end_time:
                            end_dt = fields.Datetime.context_timestamp(section, s.end_time)
                            time_range += f"-{end_dt.strftime('%H:%M')}"
                        if time_range not in times:
                            times.append(time_range)
                        room = f" ({s.classroom_id.name})" if s.classroom_id else ""
                        desc = f"{day_name} {time_range}{room}"
                        if desc not in details:
                            details.append(desc)
                section.day_summary = ", ".join(days)
                section.time_summary = ", ".join(times[:2])
                section.schedule_summary = "; ".join(details[:3]) + (
                    "..." if len(details) > 3 else ""
                )
            else:
                section.day_summary = ""
                section.time_summary = ""
                section.schedule_summary = ""

    @api.depends("schedule_line_ids.active", "schedule_line_ids.timeslot_id", "subject_id.credits")
    def _compute_schedule_warning(self):
        for section in self:
            if not section.subject_id or not section.subject_id.credits or not section.schedule_line_ids:
                section.schedule_warning = False
                continue
            weekly_hours = sum(
                (l.timeslot_id.end_hour - l.timeslot_id.start_hour)
                for l in section.schedule_line_ids
                if l.active and l.timeslot_id and l.timeslot_id.end_hour and l.timeslot_id.start_hour
            )
            expected_hours = section.subject_id.credits
            if weekly_hours > 0 and abs(weekly_hours - expected_hours) > 0.01:
                section.schedule_warning = (
                    f"Weekly schedule is {weekly_hours:g} hours, but subject '{section.subject_id.name}' "
                    f"requires {expected_hours} hours (1 credit = 1 weekly hour)."
                )
            else:
                section.schedule_warning = False

    @api.constrains("capacity")
    def _check_capacity_positive(self):
        for section in self:
            if section.capacity is not None and section.capacity < 1:
                raise ValidationError("The class section capacity must be at least 1.")

    @api.constrains("program_id", "subject_id")
    def _check_has_program_or_subject(self):
        for section in self:
            if not section.program_id and not section.subject_id:
                raise ValidationError(
                    "A class section must be linked to a Major/Program or a Subject."
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("program_id") and not vals.get("subject_id"):
                raise ValidationError(
                    "A class section must be linked to a Major/Program or a Subject."
                )
            if not vals.get("section_type"):
                vals["section_type"] = "course" if vals.get("subject_id") else "cohort"
        return super().create(vals_list)

    def write(self, vals):
        if "program_id" in vals or "subject_id" in vals:
            for section in self:
                program_id = vals.get("program_id", section.program_id.id)
                subject_id = vals.get("subject_id", section.subject_id.id)
                if not program_id and not subject_id:
                    raise ValidationError(
                        "A class section must be linked to a Major/Program or a Subject."
                    )
        return super().write(vals)

    @api.constrains("teacher_id", "subject_id")
    def _check_teacher_subject(self):
        for section in self:
            if not section.subject_id or not section.teacher_id:
                continue
            if (
                section.subject_id.teacher_ids
                and section.teacher_id not in section.subject_id.teacher_ids
            ):
                raise ValidationError(
                    "The selected instructor is not assigned to teach this subject."
                )

    @api.constrains("program_id", "subject_id")
    def _check_program_subject(self):
        for section in self:
            if not section.program_id or not section.subject_id:
                continue
            subject = section.subject_id
            if subject.program_ids and section.program_id not in subject.program_ids:
                raise ValidationError(
                    "The selected subject does not belong to the chosen major/program."
                )
            if not subject.program_ids and subject.department_id != section.program_id.department_id:
                raise ValidationError(
                    "The selected subject does not belong to the chosen major/program."
                )

    @api.onchange("program_id")
    def _onchange_program_id(self):
        domain = [("program_ids", "in", [self.program_id.id])] if self.program_id else []
        if self.subject_id and self.program_id not in self.subject_id.program_ids:
            self.subject_id = False
            self.teacher_id = False
        return {"domain": {"subject_id": domain}}

    def action_view_enrolled_students(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Enrolled Students - {self.name}",
            "res_model": "university.enrollment",
            "view_mode": "list,form",
            "domain": [("section_id", "=", self.id)],
            "context": {"default_section_id": self.id},
        }

    def action_view_sessions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Sessions - %s") % self.name,
            "res_model": "university.timetable.slot",
            "view_mode": "kanban,list,calendar,form",
            "domain": [("section_id", "=", self.id)],
            "context": {
                "default_section_id": self.id,
                "default_subject_id": self.subject_id.id if self.subject_id else False,
                "default_teacher_id": self.teacher_id.id if self.teacher_id else False,
                "default_classroom_id": self.classroom_id.id if self.classroom_id else False,
            },
        }

    @api.depends(
        "term_id", "term_id.date_start", "term_id.date_end",
        "semester_id", "semester_id.date_start", "semester_id.date_end",
        "date_start", "date_end"
    )
    def _compute_timeline(self):
        for section in self:
            # Term dates take precedence, fallback to semester dates
            start = section.date_start or (section.term_id.date_start if section.term_id else (section.semester_id.date_start if section.semester_id else False))
            end = section.date_end or (section.term_id.date_end if section.term_id else (section.semester_id.date_end if section.semester_id else False))
            if not (section.term_id or section.semester_id):
                section.timeline = ""
                continue
            if start and end:
                days = (end - start).days + 1
                weeks = max(0, math.ceil(days / 7.0))
                section.timeline = f"{start} -> {end} ({weeks} weeks)"
            elif start:
                section.timeline = f"{start} ->"
            else:
                section.timeline = ""

    def action_confirm(self):
        self.write({"state": "confirmed"})

    def action_set_to_draft(self):
        self.write({"state": "draft"})

    def action_view_schedule(self):
        self.ensure_one()
        default_date = False
        today = fields.Datetime.now()
        upcoming_slot = self.slot_ids.filtered(lambda s: s.start_time and s.start_time >= today).sorted("start_time")
        if upcoming_slot:
            default_date = upcoming_slot[0].start_time.strftime("%Y-%m-%d")
        elif self.slot_ids:
            latest_slot = self.slot_ids.filtered(lambda s: bool(s.start_time)).sorted("start_time", reverse=True)
            if latest_slot:
                default_date = latest_slot[0].start_time.strftime("%Y-%m-%d")

        ctx = {
            "default_section_id": self.id,
            "default_view_mode": "resource",
            "default_resource_type": "section",
            "filters": {"section_id": str(self.id)},
        }
        if default_date:
            ctx["default_date"] = default_date

        return {
            "type": "ir.actions.client",
            "tag": "university_schedule_view",
            "name": f"Weekly Schedule - {self.name}",
            "context": ctx,
        }

    def action_open_bulk_enroll_wizard(self):
        if not self.env.user.has_group("school_management.group_school_admin"):
            raise AccessError(_("Only University Administrators can enroll multiple students."))
        self.ensure_one()
        program = self.program_id
        if not program and self.subject_id.program_ids:
            program = self.subject_id.program_ids[:1]

        return {
            "type": "ir.actions.act_window",
            "name": "Enroll Multiple Students",
            "res_model": "university.bulk.enrollment.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_section_id": self.id,
                "default_program_id": program.id if program else False,
                "default_academic_year_id": self.semester_id.academic_year_id.id if self.semester_id and self.semester_id.academic_year_id else False,
                "default_semester_id": self.semester_id.id if self.semester_id else False,
            },
        }

    def action_open_populate_class_wizard(self):
        if not self.env.user.has_group("school_management.group_school_admin"):
            raise AccessError(_("Only University Administrators can populate a class."))
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Populate Class",
            "res_model": "university.populate.class.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_section_id": self.id},
        }

    def action_open_timetable_generation_wizard(self):
        if not (self.env.user.has_group("school_management.group_school_admin") or self.env.user.has_group("school_management.group_school_timetable_manager")):
            raise AccessError(_("Only University Administrators or Timetable Managers can schedule a timetable."))
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Generate Timetable",
            "res_model": "university.timetable.generation.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_academic_year_id": self.semester_id.academic_year_id.id if self.semester_id and self.semester_id.academic_year_id else False,
                "default_semester_id": self.semester_id.id if self.semester_id else False,
                "default_section_ids": [(6, 0, [self.id])],
            },
        }


    def action_sync_schedule_lines(self):
        self.ensure_one()
        user_tz = pytz.timezone(self.env.user.tz or 'Asia/Phnom_Penh')
        all_ts = self.env['university.timeslot'].search([('active', '=', True)])
        ts_map = {(str(ts.day_of_week), round(ts.start_hour, 2)): ts for ts in all_ts}

        for s in self.slot_ids:
            if not s.start_time:
                continue
            dt_local = pytz.utc.localize(s.start_time).astimezone(user_tz)
            weekday = str(dt_local.weekday())
            start_hour = round(dt_local.hour + dt_local.minute / 60.0, 2)
            ts = s.timeslot_id or ts_map.get((weekday, start_hour))
            if not ts:
                day_ts = [t for t in all_ts if str(t.day_of_week) == weekday]
                if day_ts:
                    ts = min(day_ts, key=lambda t: abs(t.start_hour - start_hour))
            room = s.classroom_id or self.classroom_id
            teacher = s.teacher_id or self.teacher_id
            if ts:
                line_day = str(ts.day_of_week) if ts.day_of_week is not False else weekday
                existing = self.env['university.class.schedule.line'].search([
                    ('class_id', '=', self.id),
                    ('weekday', '=', line_day),
                    ('timeslot_id', '=', ts.id),
                ], limit=1)
                if not existing:
                    self.env['university.class.schedule.line'].create({
                        'class_id': self.id,
                        'weekday': line_day,
                        'timeslot_id': ts.id,
                        'room_id': room.id if room else False,
                        'teacher_id': teacher.id if teacher else False,
                        'active': True,
                    })
        self._compute_schedule_summary()
        return True

    def action_enroll_self(self):
        self.ensure_one()
        student = self.env["university.student"].search([("user_id", "=", self.env.uid)], limit=1)
        if not student:
            return self.action_open_bulk_enroll_wizard()

        if self.is_full:
            raise ValidationError(_("This class section is full. No available seats."))

        existing = self.env["university.enrollment"].search([
            ("student_id", "=", student.id),
            ("section_id", "=", self.id),
            ("status", "=", "enrolled"),
        ], limit=1)
        if existing:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Already Enrolled"),
                    "message": _("You are already enrolled in %s.") % self.name,
                    "type": "info",
                    "sticky": False,
                },
            }

        program = self.program_id or (self.subject_id.program_ids[:1] if self.subject_id and self.subject_id.program_ids else student.program_id)
        self.env["university.enrollment"].create({
            "student_id": student.id,
            "section_id": self.id,
            "program_id": program.id if program else False,
            "academic_year_id": self.academic_year_id.id if self.academic_year_id else False,
            "semester_id": self.semester_id.id if self.semester_id else False,
            "enrollment_date": fields.Date.context_today(self),
            "status": "enrolled",
        })

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Enrolled Successfully"),
                "message": _("You have been successfully enrolled in %s.") % self.name,
                "type": "success",
                "sticky": False,
            },
        }
