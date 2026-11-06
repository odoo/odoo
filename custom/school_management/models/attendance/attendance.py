import calendar
import io
from datetime import date, datetime, time, timedelta

import pytz
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.tools.misc import format_date


def _section_info(section):
    sec = section.sudo()
    return {
        "id": section.id,
        "name": section.name,
        "display_name": section.display_name,
        "subject": sec.subject_id.name or "",
        "teacher": sec.teacher_id.name or "",
        "department": sec.sudo().department_id.name or "",
        "semester": sec.semester_id.name or "",
    }


def _status_row(record):
    return record.status[:1].upper()


class UniversityAttendanceSession(models.Model):
    _name = "university.attendance.session"
    _description = "Attendance Session"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    section_id = fields.Many2one(
        "university.class.section",
        string="Class Section",
        required=True,
        ondelete="cascade",
        tracking=True,
    )
    date = fields.Date(
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    state = fields.Selection(
        [("draft", "Not recorded"), ("recorded", "Recorded")],
        default="draft",
        required=True,
        tracking=True,
    )
    notes = fields.Text(string="Session Notes", tracking=True)
    recorded_by_id = fields.Many2one("res.users", string="Last Recorded By", readonly=True)
    recorded_at = fields.Datetime(string="Last Recorded At", readonly=True)

    attendance_ids = fields.One2many(
        "university.attendance",
        "session_id",
        string="Students",
    )
    subject_id = fields.Many2one(
        related="section_id.subject_id", string="Subject", readonly=True, store=False,
    )
    teacher_id = fields.Many2one(
        related="section_id.teacher_id", string="Teacher", readonly=True, store=False,
    )
    department_id = fields.Many2one(
        related="section_id.department_id", string="Department", readonly=True, store=False,
    )
    semester_id = fields.Many2one(
        related="section_id.semester_id", string="Semester", readonly=True, store=False,
    )
    academic_year_id = fields.Many2one(
        related="section_id.semester_id.academic_year_id",
        string="Academic Year",
        readonly=True,
        store=False,
    )
    classroom_id = fields.Many2one(
        related="section_id.classroom_id", string="Classroom", readonly=True, store=False,
    )

    present_count = fields.Integer(compute="_compute_status_counts")
    late_count = fields.Integer(compute="_compute_status_counts")
    absent_count = fields.Integer(compute="_compute_status_counts")
    excused_count = fields.Integer(compute="_compute_status_counts")
    total_count = fields.Integer(compute="_compute_status_counts")
    attendance_rate = fields.Float(
        string="Attendance Rate",
        compute="_compute_status_counts",
        digits=(16, 1),
    )

    _section_date_unique = models.Constraint(
        "unique (section_id, date)",
        "An attendance session already exists for this section and date.",
    )

    @api.depends("section_id.name", "date")
    def _compute_display_name(self):
        for session in self:
            session.display_name = _("%(section)s - %(date)s") % {
                "section": session.section_id.name or _("Section"),
                "date": format_date(self.env, session.date) if session.date else _("No date"),
            }

    @api.depends("attendance_ids.status")
    def _compute_status_counts(self):
        Attendance = self.env["university.attendance"]
        for session in self:
            counts = {"present": 0, "late": 0, "absent": 0, "excused": 0}
            for line in session.attendance_ids:
                if line.status in counts:
                    counts[line.status] += 1
            session.present_count = counts["present"]
            session.late_count = counts["late"]
            session.absent_count = counts["absent"]
            session.excused_count = counts["excused"]
            session.total_count = sum(counts.values())
            session.attendance_rate = Attendance._attendance_percentage(counts)

    @api.model_create_multi
    def create(self, vals_list):
        sessions = super().create(vals_list)
        sessions._sync_attendance_lines()
        return sessions

    def write(self, vals):
        res = super().write(vals)
        if {"section_id", "date"} & set(vals):
            self._sync_attendance_lines()
        return res

    def _sync_attendance_lines(self):
        """Ensure one attendance line per enrolled student for this session."""
        Attendance = self.env["university.attendance"]
        for session in self:
            if not session.section_id or not session.date:
                continue
            # Attach orphan lines for the same section/date
            orphans = Attendance.search([
                ("section_id", "=", session.section_id.id),
                ("date", "=", session.date),
                ("session_id", "=", False),
            ])
            if orphans:
                orphans.write({"session_id": session.id})

            students = Attendance._attendance_sheet_students(session.section_id)
            existing = {
                line.student_id.id: line
                for line in session.attendance_ids
            }
            to_create = []
            for student in students:
                if student.id in existing:
                    continue
                to_create.append({
                    "session_id": session.id,
                    "student_id": student.id,
                    "section_id": session.section_id.id,
                    "date": session.date,
                    "status": "present",
                })
            if to_create:
                Attendance.create(to_create)

    def action_load_students(self):
        self.ensure_one()
        self._sync_attendance_lines()
        return True

    def action_mark_all_present(self):
        return self._mark_all("present")

    def action_mark_all_late(self):
        return self._mark_all("late")

    def action_mark_all_absent(self):
        return self._mark_all("absent")

    def action_mark_all_excused(self):
        return self._mark_all("excused")

    def _mark_all(self, status):
        self.ensure_one()
        self._sync_attendance_lines()
        self.attendance_ids.write({"status": status})
        return True

    def action_save_attendance(self):
        """Confirm the roster and post a log note on the session chatter."""
        self.ensure_one()
        Attendance = self.env["university.attendance"]
        if not Attendance._allowed_edit(self.section_id):
            raise AccessError(
                _("You are not allowed to record attendance for this class section.")
            )
        self._sync_attendance_lines()
        if not self.attendance_ids:
            raise ValidationError(_("No student attendance lines are available to save."))

        today = fields.Date.context_today(self)
        if self.date > today:
            raise ValidationError(_("Attendance cannot be recorded for a future date."))

        labels = dict(Attendance._fields["status"].selection)
        changes = [
            _("%(student)s: %(status)s") % {
                "student": line.student_id.display_name,
                "status": labels.get(line.status, line.status),
            }
            for line in self.attendance_ids
        ]
        self.write({
            "state": "recorded",
            "recorded_by_id": self.env.uid,
            "recorded_at": fields.Datetime.now(),
        })
        body = Markup("<p>%s</p>") % _("Attendance recorded")
        if changes:
            body += Markup("<ul>%s</ul>") % Markup("").join(
                Markup("<li>%s</li>") % change for change in changes[:40]
            )
            if len(changes) > 40:
                body += Markup("<p>%s</p>") % _(
                    "…and %(count)s more", count=len(changes) - 40
                )
        self.message_post(body=body, subtype_xmlid="mail.mt_note")
        return True

    def action_open_sheet(self):
        """Open this session form (native kanban / list / chatter UI)."""
        self.ensure_one()
        self.check_access("read")
        self._sync_attendance_lines()
        return {
            "type": "ir.actions.act_window",
            "name": _("Student Attendance"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
            "context": dict(self.env.context),
        }

    @api.model
    def action_open_or_create(self, section_id=None, date=None):
        """Open or create a session for section/date (used by menus and schedule)."""
        section_id = int(section_id or self.env.context.get("default_section_id") or 0)
        att_date = date or self.env.context.get("default_date") or fields.Date.context_today(self)
        if isinstance(att_date, str):
            att_date = fields.Date.to_date(att_date)
        domain = []
        if section_id:
            domain.append(("section_id", "=", section_id))
        if att_date:
            domain.append(("date", "=", att_date))
        session = self.search(domain, limit=1) if domain else self.browse()
        if not session and section_id and att_date:
            session = self.create({"section_id": section_id, "date": att_date})
        elif session:
            session._sync_attendance_lines()
        action = self.env.ref("school_management.action_university_attendance_session").read()[0]
        if session:
            action["res_id"] = session.id
            action["view_mode"] = "form"
            action["views"] = [(False, "form")]
        action["context"] = {
            **dict(self.env.context),
            "default_section_id": section_id or False,
            "default_date": fields.Date.to_string(att_date) if att_date else False,
        }
        return action


class UniversityAttendance(models.Model):
    _name = "university.attendance"
    _description = "Student Attendance"
    _order = "date desc, id desc"

    session_id = fields.Many2one(
        "university.attendance.session",
        string="Attendance Session",
        ondelete="cascade",
        index=True,
    )
    student_id = fields.Many2one("university.student", string="Student", required=True)
    section_id = fields.Many2one("university.class.section", string="Grade/Section", required=True)
    teacher_id = fields.Many2one(
        "university.teacher",
        string="Teacher",
        related="section_id.teacher_id",
        store=True,
    )
    date = fields.Date(string="Date", default=fields.Date.context_today, required=True)
    status = fields.Selection(
        [
            ("present", "Present"),
            ("absent", "Absent"),
            ("late", "Late"),
            ("excused", "Excused"),
        ],
        string="Status",
        required=True,
        default="present",
    )
    remark = fields.Char(string="Remarks")
    student_code = fields.Char(
        related="student_id.student_id", string="Student ID", readonly=True,
    )
    department_id = fields.Many2one(
        "university.department",
        string="Department",
        related="section_id.department_id",
        store=True,
        readonly=True,
        help="Department of the class section (used for HOD/dean scoping).",
    )
    faculty_id = fields.Many2one(
        "university.faculty",
        string="Faculty",
        related="department_id.faculty_id",
        store=True,
        readonly=True,
        help="Faculty of the class section (used for faculty/dean scoping).",
    )
    month = fields.Integer(
        string="Month",
        compute="_compute_month_year",
        store=True,
        help="Numeric month (1-12) of the attendance date.",
    )
    year = fields.Integer(
        string="Year",
        compute="_compute_month_year",
        store=True,
        help="Calendar year of the attendance date.",
    )

    _student_date_section_unique = models.Constraint(
        "unique (student_id, date, section_id)",
        "Attendance for this student, date, and section already exists.",
    )
    _check_date_not_future = models.Constraint(
        "check (date <= CURRENT_DATE)",
        "Attendance cannot be recorded for a future date.",
    )

    # Attendance percentage formula constant (Attendance spec, STEP 1).
    # Students are credited as "present for the day" when they are present,
    # late or excused; only unexcused absences reduce the rate.
    PRESENT_STATUSES = ("present", "late", "excused")
    STATUS_KEYS = {"present": "P", "absent": "A", "late": "L", "excused": "E"}

    @api.depends("date")
    def _compute_month_year(self):
        for record in self:
            record.month = record.date.month if record.date else 0
            record.year = record.date.year if record.date else 0

    @api.depends("student_id", "date")
    def _compute_display_name(self):
        for attendance in self:
            student_name = attendance.student_id.display_name or _("Student")
            date = fields.Date.to_string(attendance.date) if attendance.date else _("No date")
            attendance.display_name = _("%(student)s - %(date)s") % {
                "student": student_name,
                "date": date,
            }

    def action_set_present(self):
        for rec in self:
            if not self._allowed_edit(rec.section_id):
                raise AccessError(_("You are not allowed to record attendance for this class section."))
            rec.status = "present"

    def action_set_absent(self):
        for rec in self:
            if not self._allowed_edit(rec.section_id):
                raise AccessError(_("You are not allowed to record attendance for this class section."))
            rec.status = "absent"

    def action_set_late(self):
        for rec in self:
            if not self._allowed_edit(rec.section_id):
                raise AccessError(_("You are not allowed to record attendance for this class section."))
            rec.status = "late"

    def action_set_excused(self):
        for rec in self:
            if not self._allowed_edit(rec.section_id):
                raise AccessError(_("You are not allowed to record attendance for this class section."))
            rec.status = "excused"

    @api.model
    def _attendance_sheet_statuses(self):
        return {"present", "absent", "late", "excused"}

    @api.model
    def _attendance_percentage(self, status_counts):
        """Attendance % = (present + late + excused) / total recorded * 100.

        Documented percentage formula constant (STEP 1): the attendance rate
        credits present, late and excused records, and only penalises
        unexcused absences.
        """
        denominator = sum(
            status_counts.get(status, 0)
            for status in ("present", "absent", "late", "excused")
        )
        if not denominator:
            return 100.0
        numerator = sum(status_counts.get(status, 0) for status in self.PRESENT_STATUSES)
        return round(numerator * 100.0 / denominator, 1)

    @api.model
    def _attendance_threshold(self):
        return float(
            self.env["ir.config_parameter"].sudo().get_param(
                "school_management.risk_attendance_threshold", 75.0
            )
        )

    @api.model
    def _attendance_edit_window_days(self):
        return int(
            self.env["ir.config_parameter"].sudo().get_param(
                "school_management.attendance_edit_window_days", 7
            )
        )

    @api.model
    def _allowed_edit(self, section):
        """Whether the current user may record/edit attendance on a section."""
        user = self.env.user
        if self.env.is_superuser() or user.has_group("school_management.group_school_admin") \
                or user.has_group("base.group_system"):
            return True
        if not user.has_group("school_management.group_school_teacher"):
            return False
        return bool(section.teacher_id.user_id == user)

    @api.model
    def _get_role_sections(self):
        """Sections the current user is allowed to see in attendance reports,
        mirroring the HOD/dean/teacher record rules. Admin/system see all."""
        Section = self.env["university.class.section"]
        user = self.env.user
        if self.env.is_superuser() or user.has_group("school_management.group_school_admin") \
                or user.has_group("base.group_system"):
            return Section.search([])
        if user.has_group("school_management.group_school_dean"):
            return Section.search(
                ["|", "|",
                 ("department_id.faculty_id.dean_id.user_id", "=", user.id),
                 ("subject_id.department_id.faculty_id.dean_id.user_id", "=", user.id),
                 ("teacher_id.user_id", "=", user.id)]
            )
        if user.has_group("school_management.group_school_hod"):
            return Section.search(
                ["|", "|",
                 ("department_id.head_id.user_id", "=", user.id),
                 ("subject_id.department_id.head_id.user_id", "=", user.id),
                 ("teacher_id.user_id", "=", user.id)]
            )
        if user.has_group("school_management.group_school_teacher"):
            return Section.search([("teacher_id.user_id", "=", user.id)])
        return Section.browse()

    @api.model
    def _validated_month_year(self, month, year):
        try:
            month = int(month)
            year = int(year)
        except (TypeError, ValueError):
            month = fields.Date.from_string(fields.Date.context_today(self)).month
            year = fields.Date.from_string(fields.Date.context_today(self)).year
        if month < 1 or month > 12:
            month = fields.Date.from_string(fields.Date.context_today(self)).month
        if year < 2000 or year > 2100:
            year = fields.Date.from_string(fields.Date.context_today(self)).year
        return month, year

    @api.model
    def _month_calendar(self, month, year):
        """Calendar metadata for a month: weekdays, weekends and holidays."""
        first_weekday, num_days = calendar.monthrange(year, month)
        month_start = date(year, month, 1)
        month_end = date(year, month, num_days)
        holiday_days = set()
        for holiday in self.env["university.holiday"].search([]):
            if not holiday.date_start or not holiday.date_end:
                continue
            cursor = max(holiday.date_start, month_start)
            end = min(holiday.date_end, month_end)
            while cursor <= end:
                holiday_days.add(cursor)
                cursor += timedelta(days=1)
        days = []
        for day in range(1, num_days + 1):
            dow = calendar.weekday(year, month, day)
            days.append({
                "day": day,
                "dow": dow,
                "weekend": dow >= 5,
                "holiday": date(year, month, day) in holiday_days,
            })
        return {
            "month": month,
            "year": year,
            "first_weekday": first_weekday,
            "num_days": num_days,
            "days": days,
        }

    def _status_codes(self, records):
        return {
            record.date.day: self.STATUS_KEYS.get(record.status, record.status[:1].upper())
            for record in records
        }

    @api.model
    def get_attendance_options(self, role="teacher"):
        statuses = [
            {"value": value, "label": label, "key": self.STATUS_KEYS.get(value, "")}
            for value, label in self._fields["status"].selection
        ]
        return {
            "statuses": statuses,
            "presence_statuses": list(self.PRESENT_STATUSES),
            "threshold": self._attendance_threshold(),
            "edit_window_days": self._attendance_edit_window_days(),
            "can_take": role in ("teacher", "admin"),
            "can_edit": role in ("teacher", "admin"),
        }

    @api.model
    def _attendance_sheet_date(self, date):
        attendance_date = fields.Date.to_date(date)
        if not attendance_date:
            raise ValidationError(_("Please choose a valid attendance date."))
        return attendance_date

    @api.model
    def _attendance_sheet_section(self, section_id):
        try:
            section_id = int(section_id)
        except (TypeError, ValueError):
            section_id = 0
        section = self.env["university.class.section"].browse(section_id).exists()
        if not section:
            raise ValidationError(_("Please choose a valid class section."))
        section.check_access("read")
        return section

    @api.model
    def _attendance_sheet_students(self, section):
        enrollments = self.env["university.enrollment"].search([
            ("section_id", "=", section.id),
            ("status", "=", "enrolled"),
        ])
        students = enrollments.mapped("student_id").exists()
        return students.sorted(lambda student: (student.name or "").casefold())

    @api.model
    def get_sheet(self, section_id, date):
        self.check_access("read")
        Session = self.env["university.attendance.session"]
        Session.check_access("read")
        section = self._attendance_sheet_section(section_id)
        attendance_date = self._attendance_sheet_date(date)
        students = self._attendance_sheet_students(section)
        session = Session.search([
            ("section_id", "=", section.id), ("date", "=", attendance_date),
        ], limit=1)

        timezone = pytz.timezone(self.env.user.tz or "UTC")
        start = timezone.localize(datetime.combine(attendance_date, time.min)).astimezone(pytz.UTC)
        end = timezone.localize(datetime.combine(attendance_date + timedelta(days=1), time.min)).astimezone(pytz.UTC)
        slots = self.env["university.timetable.slot"].search([
            ("section_id", "=", section.id),
            ("start_time", ">=", start.replace(tzinfo=None)),
            ("start_time", "<", end.replace(tzinfo=None)),
        ])

        records = self.search([
            ("section_id", "=", section.id),
            ("date", "=", attendance_date),
            ("student_id", "in", students.ids or [0]),
        ])
        attendance_by_student = {record.student_id.id: record for record in records}

        last_write = max(
            (record.write_date for record in records if record.write_date),
            default=False,
        )

        lines = []
        for student in students:
            attendance = attendance_by_student.get(student.id)
            lines.append({
                "student_id": student.id,
                "name": student.name,
                "code": student.student_id or "",
                "section_name": section.display_name,
                "status": attendance.status if attendance else "present",
                "remark": (attendance.remark or "") if attendance else "",
                "attendance_id": attendance.id if attendance else False,
                "has_image": bool(student.image_1920),
                "student_model": "university.student",
                "image_field": "image_1920",
            })

        return {
            "taken": bool(records),
            "last_saved_at": fields.Datetime.to_string(last_write) if last_write else False,
            "section_name": section.display_name,
            "date": fields.Date.to_string(attendance_date),
            "lines": lines,
            "session_id": session.id or False,
            "notes": session.notes or "",
            "subject": section.subject_id.display_name or ", ".join(slots.mapped("subject_id.display_name")),
            "teacher": section.teacher_id.display_name or ", ".join(slots.mapped("teacher_id.display_name")),
            "semester": section.semester_id.display_name,
            "academic_year": section.semester_id.academic_year_id.display_name,
            "classroom": section.classroom_id.display_name or "",
            "recorded_by": session.recorded_by_id.display_name or "",
            "recorded_at": fields.Datetime.to_string(session.recorded_at) if session.recorded_at else False,
            "slots": [{
                "id": slot.id,
                "subject": slot.subject_id.display_name,
                "teacher": slot.teacher_id.display_name,
                "location": slot.location or slot.classroom_id.display_name or "",
                "start_time": fields.Datetime.to_string(slot.start_time),
                "end_time": fields.Datetime.to_string(slot.end_time),
            } for slot in slots],
        }

    @api.model
    def save_sheet(self, section_id, date, lines, notes=None):
        self.check_access("create")
        section = self._attendance_sheet_section(section_id)
        attendance_date = self._attendance_sheet_date(date)

        today = fields.Date.context_today(self)
        if attendance_date > today:
            raise ValidationError(_("Attendance cannot be recorded for a future date."))
        edit_window = self._attendance_edit_window_days()
        if not self._allowed_edit(section):
            raise AccessError(
                _("You are not allowed to record attendance for this class section.")
            )
        if attendance_date < today - timedelta(days=edit_window) \
                and not (self.env.is_superuser()
                         or self.env.user.has_group("school_management.group_school_admin")
                         or self.env.user.has_group("base.group_system")):
            raise ValidationError(
                _("Attendance for %s is outside the %s-day editing window.")
                % (format_date(self.env, attendance_date), edit_window)
            )

        if not isinstance(lines, list):
            raise ValidationError(_("Attendance lines must be a list."))
        if notes is not None and not isinstance(notes, str):
            raise ValidationError(_("Session notes must be text."))

        students = self._attendance_sheet_students(section)
        allowed_student_ids = set(students.ids)
        allowed_statuses = self._attendance_sheet_statuses()

        normalized_lines = {}
        for line in lines:
            if not isinstance(line, dict):
                raise ValidationError(_("Invalid attendance line."))
            try:
                student_id = int(line.get("student_id"))
            except (TypeError, ValueError):
                raise ValidationError(_("Invalid student on an attendance line."))
            if student_id not in allowed_student_ids:
                raise ValidationError(_("Student does not belong to the selected class section."))

            status = line.get("status") or "present"
            if status not in allowed_statuses:
                raise ValidationError(_("Invalid attendance status: %s") % status)

            normalized_lines[student_id] = {
                "student_id": student_id,
                "status": status,
                "remark": (line.get("remark") or "").strip(),
            }

        Session = self.env["university.attendance.session"]
        session = Session.search([
            ("section_id", "=", section.id), ("date", "=", attendance_date),
        ], limit=1)
        first_save = not session
        if not session and normalized_lines:
            # create() auto-syncs enrolled students onto attendance_ids
            session = Session.create({"section_id": section.id, "date": attendance_date})
        elif session:
            session._sync_attendance_lines()

        existing = self.search([
            ("section_id", "=", section.id),
            ("date", "=", attendance_date),
            ("student_id", "in", list(normalized_lines) or [0]),
        ])
        existing_by_student = {record.student_id.id: record for record in existing}
        changes = []
        labels = dict(self._fields["status"].selection)

        for student_id, values in normalized_lines.items():
            vals = {
                "student_id": student_id,
                "section_id": section.id,
                "date": attendance_date,
                "status": values["status"],
                "remark": values["remark"],
                "session_id": session.id if session else False,
            }
            attendance = existing_by_student.get(student_id)
            if attendance:
                if attendance.status != values["status"]:
                    changes.append(_("%(student)s: %(old)s -> %(new)s") % {
                        "student": attendance.student_id.display_name,
                        "old": labels[attendance.status], "new": labels[values["status"]],
                    })
                if (attendance.remark or "") != values["remark"]:
                    changes.append(_("%(student)s: attendance note updated") % {
                        "student": attendance.student_id.display_name,
                    })
                if (
                    attendance.status != values["status"]
                    or (attendance.remark or "") != values["remark"]
                    or attendance.session_id != session
                ):
                    attendance.write(vals)
            else:
                attendance = self.create(vals)
                changes.append(_("%(student)s: %(status)s") % {
                    "student": attendance.student_id.display_name, "status": labels[attendance.status],
                })

        if session and normalized_lines:
            session_values = {
                "state": "recorded",
                "recorded_by_id": self.env.uid,
                "recorded_at": fields.Datetime.now(),
            }
            if notes is not None:
                session_values["notes"] = notes.strip()
            session.write(session_values)
            if first_save or changes:
                body = Markup("<p>%s</p>") % (
                    _("Attendance recorded") if first_save else _("Attendance updated")
                )
                if changes:
                    body += Markup("<ul>%s</ul>") % Markup("").join(
                        Markup("<li>%s</li>") % change for change in changes
                    )
                session.message_post(body=body, subtype_xmlid="mail.mt_note")

        return self.get_sheet(section.id, fields.Date.to_string(attendance_date))

    @api.model
    def get_available_sections(self):
        """Sections available to the current user for attendance recording."""
        sections = self._get_role_sections().filtered(lambda s: s.active)
        return sections.read(["id", "name", "display_name", "department_id"])

    @api.model
    def get_section_attendance_sheet(self, section_id, date):
        """Wrapper around get_sheet matching frontend RPC expectations."""
        sheet = self.get_sheet(section_id, date)
        sheet["session"] = {
            "id": sheet.get("session_id"),
            "session_id": sheet.get("session_id"),
            "notes": sheet.get("notes") or "",
            "recorded_by": sheet.get("recorded_by") or "",
            "recorded_at": sheet.get("recorded_at") or False,
            "subject": sheet.get("subject") or "",
            "teacher": sheet.get("teacher") or "",
            "semester": sheet.get("semester") or "",
            "academic_year": sheet.get("academic_year") or "",
            "classroom": sheet.get("classroom") or "",
            "slots": sheet.get("slots") or [],
        }
        sheet["last_saved"] = sheet.get("last_saved_at")
        sheet["saved_at"] = sheet.get("last_saved_at")
        return sheet

    @api.model
    def save_section_attendance(self, section_id, date, lines, notes=None):
        """Wrapper around save_sheet matching frontend RPC expectations."""
        sheet = self.save_sheet(section_id, date, lines, notes=notes)
        sheet["session"] = {
            "id": sheet.get("session_id"),
            "session_id": sheet.get("session_id"),
            "notes": sheet.get("notes") or "",
            "recorded_by": sheet.get("recorded_by") or "",
            "recorded_at": sheet.get("recorded_at") or False,
            "subject": sheet.get("subject") or "",
            "teacher": sheet.get("teacher") or "",
            "semester": sheet.get("semester") or "",
            "academic_year": sheet.get("academic_year") or "",
            "classroom": sheet.get("classroom") or "",
            "slots": sheet.get("slots") or [],
        }
        sheet["last_saved"] = sheet.get("last_saved_at")
        sheet["saved_at"] = sheet.get("last_saved_at")
        return sheet

    # =====================================================================
    # Role-scoped helpers shared by the attendance dashboard / grid / reports
    # =====================================================================

    @api.model
    def _get_role(self):
        user = self.env.user
        if self.env.is_superuser() or user.has_group("school_management.group_school_admin") \
                or user.has_group("base.group_system"):
            return "admin"
        if user.has_group("school_management.group_school_dean"):
            return "dean"
        if user.has_group("school_management.group_school_hod"):
            return "hod"
        if user.has_group("school_management.group_school_teacher"):
            return "teacher"
        if user.has_group("school_management.group_school_student"):
            return "student"
        return "public"

    @api.model
    def _scope_attendance_domain(self, section_ids=None):
        """Attendance domain restricted to the current user's role scope."""
        allowed = self._get_role_sections()
        if section_ids:
            allowed = allowed & self.env["university.class.section"].browse(section_ids)
        if not allowed:
            return [("id", "=", False)]
        return [("section_id", "in", allowed.ids)]

    @api.model
    def _enrolled_students(self, sections):
        enrollments = self.env["university.enrollment"].search([
            ("section_id", "in", sections.ids),
            ("status", "=", "enrolled"),
        ])
        return enrollments.mapped("student_id").exists()

    # ---------------------------------------------------------------- Student
    @api.model
    def get_student_dashboard(self, month, year, section_id=False):
        month, year = self._validated_month_year(month, year)
        user = self.env.user
        student = self.env["university.student"].search(
            [("user_id", "=", user.id)], limit=1
        )
        if not student:
            return {"error": _("No student profile is linked to your account.")}

        enrollments = self.env["university.enrollment"].search(
            [("student_id", "=", student.id)]
        ).filtered(lambda e: e.section_id and e.status in ("enrolled", "completed"))
        sections = enrollments.mapped("section_id")
        if not sections:
            return {
                "error": _("You are not enrolled in any active class section yet."),
                "student": {"name": student.name},
            }

        try:
            section_id = int(section_id)
        except (TypeError, ValueError):
            section_id = 0

        if section_id:
            selected = sections.filtered(lambda s: s.id == section_id)
            if not selected:
                selected = sections[:1]
        else:
            selected = sections[:1]

        counts_domain = [
            ("student_id", "=", student.id),
            ("month", "=", month),
            ("year", "=", year),
        ]
        records = self.search(counts_domain)
        counts = {"present": 0, "absent": 0, "late": 0, "excused": 0}
        for record in records:
            counts[record.status] = counts.get(record.status, 0) + 1
        rate = self._attendance_percentage(counts)

        per_section = []
        for section in sections:
            sec_counts = {"present": 0, "absent": 0, "late": 0, "excused": 0}
            for record in records.filtered(lambda r: r.section_id == section):
                sec_counts[record.status] = sec_counts.get(record.status, 0) + 1
            per_section.append({
                **_section_info(section),
                "counts": sec_counts,
                "total": sum(sec_counts.values()),
                "rate": self._attendance_percentage(sec_counts),
            })

        selected_codes = {
            record.date.day: _status_row(record)
            for record in records if record.section_id == selected
        }
        calendar_meta = self._month_calendar(month, year)
        for day in calendar_meta["days"]:
            day["status"] = selected_codes.get(day["day"], False)

        rows = []
        for record in records.sorted(key=lambda r: r.date, reverse=True):
            rows.append({
                "id": record.id,
                "date": fields.Date.to_string(record.date),
                "status": record.status,
                "status_label": dict(self._fields["status"].selection)[record.status],
                "remark": record.remark or "",
                "section_name": record.section_id.name,
                "teacher": record.section_id.teacher_id.name or "",
            })

        threshold = self._attendance_threshold()
        return {
            "student": {
                "id": student.id,
                "name": student.name,
                "code": student.student_id or "",
                "program": student.program_id.name or "",
                "email": student.email or "",
                "phone": student.phone or "",
                "department": student.sudo().department_id.name or "",
            },
            "sections": per_section,
            "selected_section_id": selected.id or False,
            "summary": counts,
            "total": sum(counts.values()),
            "rate": rate,
            "threshold": threshold,
            "is_low": sum(counts.values()) >= 3 and rate < threshold,
            "calendar": calendar_meta,
            "records": rows,
            "edit_window_days": self._attendance_edit_window_days(),
        }

    # ------------------------------------------------------------------ Grid
    @api.model
    def get_grid_data(self, section_ids, month, year):
        month, year = self._validated_month_year(month, year)
        allowed = self._get_role_sections()
        if section_ids:
            try:
                section_ids = [int(s) for s in section_ids if int(s)]
            except (TypeError, ValueError):
                section_ids = []
            requested = self.env["university.class.section"].browse(section_ids)
            sections = requested & allowed
        else:
            sections = allowed

        if not sections:
            return {
                "role": self._get_role(),
                "calendar": self._month_calendar(month, year),
                "sections": [],
                "can_edit": False,
                "threshold": self._attendance_threshold(),
            }

        records = self.search(
            self._scope_attendance_domain(sections.ids)
            + [("month", "=", month), ("year", "=", year)]
        )
        by_section = {section.id: records.filtered(lambda r: r.section_id == section)
                      for section in sections}
        calendar_meta = self._month_calendar(month, year)
        calendar_days = calendar_meta["days"]
        num_days = calendar_meta["num_days"]

        grid_sections = []
        for section in sections:
            students = self._enrolled_students(section)
            student_records = by_section[section.id]
            grid_rows = []
            for student in students.sorted(key=lambda s: s.name or ""):
                student_rows = student_records.filtered(
                    lambda r: r.student_id == student
                )
                by_day = {r.date.day: r for r in student_rows}
                cells = []
                for day in range(1, num_days + 1):
                    record = by_day.get(day)
                    if calendar_days[day - 1]["weekend"] or calendar_days[day - 1]["holiday"]:
                        cells.append({"day": day, "code": False, "status": False,
                                      "remark": False, "attendance_id": False})
                    elif record:
                        cells.append({
                            "day": day,
                            "code": self.STATUS_KEYS.get(record.status, ""),
                            "status": record.status,
                            "remark": record.remark or "",
                            "attendance_id": record.id,
                        })
                    else:
                        cells.append({"day": day, "code": "", "status": False,
                                      "remark": False, "attendance_id": False})
                grid_rows.append({
                    "student_id": student.id,
                    "name": student.name,
                    "code": student.student_id or "",
                    "department": student.sudo().department_id.name or "",
                    "cells": cells,
                })
            grid_sections.append({
                **_section_info(section),
                "students": grid_rows,
                "can_edit": self._allowed_edit(section),
            })

        return {
            "role": self._get_role(),
            "calendar": self._month_calendar(month, year),
            "sections": grid_sections,
            "can_edit": any(s["can_edit"] for s in grid_sections),
            "threshold": self._attendance_threshold(),
            "edit_window_days": self._attendance_edit_window_days(),
            "legend": {key: label for key, label in self._fields["status"].selection},
        }

    @api.model
    def update_cell(self, section_id, student_id, date, status, remark=""):
        section = self.env["university.class.section"].browse(int(section_id)).exists()
        if not section:
            raise ValidationError(_("Please choose a valid class section."))
        if not self._allowed_edit(section):
            raise AccessError(_("You are not allowed to edit this attendance record."))

        attendance_date = self._attendance_sheet_date(date)
        today = fields.Date.context_today(self)
        if attendance_date > today:
            raise ValidationError(_("Attendance cannot be recorded for a future date."))
        edit_window = self._attendance_edit_window_days()
        if attendance_date < today - timedelta(days=edit_window):
            raise ValidationError(
                _("Attendance for %s is outside the %s-day editing window.")
                % (format_date(self.env, attendance_date), edit_window)
            )
        if status not in self._attendance_sheet_statuses():
            raise ValidationError(_("Invalid attendance status: %s") % status)
        if remark is None:
            remark = ""

        students = self._attendance_sheet_students(section)
        if int(student_id) not in students.ids:
            raise ValidationError(_("Student does not belong to the selected class section."))

        record = self.search([
            ("section_id", "=", section.id),
            ("date", "=", attendance_date),
            ("student_id", "=", int(student_id)),
        ], limit=1)
        vals = {
            "student_id": int(student_id),
            "section_id": section.id,
            "date": attendance_date,
            "status": status,
            "remark": (remark or "").strip(),
        }
        if record:
            record.write(vals)
        else:
            record = self.create(vals)

        return {
            "ok": True,
            "attendance_id": record.id,
            "date": fields.Date.to_string(attendance_date),
            "status": record.status,
            "remark": record.remark or "",
            "code": self.STATUS_KEYS.get(record.status, ""),
        }

    # --------------------------------------------------------------- At risk
    @api.model
    def get_at_risk_data(self, month=None, year=None, section_ids=None):
        sections = self._get_role_sections()
        if section_ids:
            sections = sections & self.env["university.class.section"].browse(
                [int(s) for s in section_ids if str(s).isdigit()]
            )
        month = int(month) if month and str(month).isdigit() else None
        year = int(year) if year and str(year).isdigit() else None

        students = self._enrolled_students(sections)
        threshold = self._attendance_threshold()

        domain = [("section_id", "in", sections.ids or [0])]
        if month:
            domain.append(("month", "=", month))
        if year:
            domain.append(("year", "=", year))
        all_records = self.search(domain)
        by_student = {student.id: all_records.filtered(lambda r: r.student_id == student)
                      for student in students}

        rows = []
        for student in students:
            records = by_student[student.id]
            counts = {"present": 0, "absent": 0, "late": 0, "excused": 0}
            for record in records:
                counts[record.status] = counts.get(record.status, 0) + 1
            if not records:
                continue
            rate = self._attendance_percentage(counts)
            if rate >= threshold:
                continue
            dept_name = student.sudo().department_id.name or (
                records.sudo().mapped("section_id.department_id.name") and records.sudo().mapped("section_id.department_id.name")[0]
            ) or (
                records.sudo().mapped("section_id.subject_id.department_id.name") and records.sudo().mapped("section_id.subject_id.department_id.name")[0]
            ) or ""
            prog_name = student.sudo().program_id.name or (
                records.sudo().mapped("section_id.program_id.name") and records.sudo().mapped("section_id.program_id.name")[0]
            ) or ""
            rows.append({
                "id": student.id,
                "name": student.name,
                "code": student.student_id or "",
                "department": dept_name,
                "program": prog_name,
                "email": student.email or "",
                "phone": student.phone or "",
                "sections": ", ".join(
                    records.mapped("section_id.name") and sorted(set(records.mapped("section_id.name"))) or []
                ),
                "counts": counts,
                "total": len(records),
                "rate": rate,
            })

        rows.sort(key=lambda r: (r["rate"], r["name"]))
        return {
            "threshold": threshold,
            "period": {"month": month, "year": year},
            "students": rows,
            "sections": [_section_info(s) for s in sections],
        }

    # -------------------------------------------------------------- Compare
    @api.model
    def get_comparison_data(self, year=None):
        sections = self._get_role_sections()
        year = int(year) if year and str(year).isdigit() else None

        dept_ids = set()
        faculty_ids = set()
        for sec in sections:
            dept = sec.department_id or (sec.subject_id and sec.subject_id.department_id)
            if dept:
                dept_ids.add(dept.id)
                if dept.faculty_id:
                    faculty_ids.add(dept.faculty_id.id)
        departments = self.env["university.department"].browse(list(dept_ids))
        faculties = self.env["university.faculty"].browse(list(faculty_ids))

        domain = [("section_id", "in", sections.ids or [0])]
        if year:
            domain.append(("year", "=", year))
        records = self.search(domain)

        departments_data = []
        for department in departments:
            dept_sections = sections.filtered(
                lambda s: s.department_id == department or (not s.department_id and s.subject_id and s.subject_id.department_id == department)
            )
            sections_data = []
            for section in dept_sections:
                students = self._enrolled_students(section)
                section_records = records.filtered(lambda r: r.section_id == section)
                by_student = {
                    student.id: section_records.filtered(lambda r: r.student_id == student)
                    for student in students
                }
                student_data = []
                for student in students:
                    recs = by_student.get(student.id, self.browse())
                    counts = {"present": 0, "absent": 0, "late": 0, "excused": 0}
                    for record in recs:
                        counts[record.status] = counts.get(record.status, 0) + 1
                    if recs:
                        student_data.append({
                            "id": student.id,
                            "name": student.name,
                            "code": student.student_id or "",
                            "rate": self._attendance_percentage(counts),
                            "total": len(recs),
                        })
                section_counts = {"present": 0, "absent": 0, "late": 0, "excused": 0}
                for record in section_records:
                    section_counts[record.status] = section_counts.get(record.status, 0) + 1
                sections_data.append({
                    "id": section.id,
                    "name": section.name,
                    "students": student_data,
                    "total": len(section_records),
                    "rate": self._attendance_percentage(section_counts),
                })
            dept_records = records.filtered(lambda r: r.section_id in dept_sections)
            dept_counts = {"present": 0, "absent": 0, "late": 0, "excused": 0}
            for record in dept_records:
                dept_counts[record.status] = dept_counts.get(record.status, 0) + 1
            departments_data.append({
                "id": department.id,
                "name": department.name,
                "faculty_id": department.sudo().faculty_id.id if department.sudo().faculty_id else False,
                "faculty_name": department.sudo().faculty_id.name if department.sudo().faculty_id else "",
                "faculty_code": department.sudo().faculty_id.code if department.sudo().faculty_id else "",
                "sections": sections_data,
                "total": len(dept_records),
                "rate": self._attendance_percentage(dept_counts),
            })

        departments_data.sort(key=lambda d: d["name"])

        # Also aggregate faculty-level stats
        faculties_data = []
        for faculty in faculties:
            fac_depts = [d for d in departments_data if d["faculty_id"] == faculty.id]
            fac_total_records = sum(d["total"] for d in fac_depts)
            fac_total_sections = sum(len(d["sections"]) for d in fac_depts)
            fac_dept_objs = departments.filtered(lambda d: d.sudo().faculty_id == faculty)
            fac_sections = sections.filtered(
                lambda s: s.department_id in fac_dept_objs or (s.subject_id and s.subject_id.department_id in fac_dept_objs)
            )
            fac_records = records.filtered(lambda r: r.section_id in fac_sections)
            fac_counts = {"present": 0, "absent": 0, "late": 0, "excused": 0}
            for record in fac_records:
                fac_counts[record.status] = fac_counts.get(record.status, 0) + 1
            fac_rate = self._attendance_percentage(fac_counts)
            faculties_data.append({
                "id": faculty.id,
                "name": faculty.name,
                "code": faculty.code or "",
                "dean_name": faculty.sudo().dean_id.name or "",
                "department_count": len(fac_depts),
                "section_count": fac_total_sections,
                "total": fac_total_records,
                "rate": fac_rate,
            })
        faculties_data.sort(key=lambda f: f["name"])

        return {
            "departments": departments_data,
            "faculties": faculties_data,
            "year": year,
        }

    # ----------------------------------------------------------------- Export
    def _export_grid_data(self, month, year, section_ids):
        """Rows/columns data used by the XLSX/CSV grid exports."""
        month, year = self._validated_month_year(month, year)
        grid = self.get_grid_data(section_ids, month, year)
        return month, year, grid

    @api.model
    def build_grid_xlsx(self, month, year, section_ids):
        import xlsxwriter

        month, year, grid = self._export_grid_data(month, year, section_ids)
        if not grid.get("sections"):
            raise ValidationError(_("No class sections are available for export."))
        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
        header = workbook.add_format({
            "bold": True, "bg_color": "#4B6654", "color": "white", "border": 1
        })
        cell = workbook.add_format({"border": 1, "align": "center"})
        name_cell = workbook.add_format({"border": 1})
        rate_cell = workbook.add_format({"border": 1, "align": "center", "bg_color": "#F5F9F6"})
        code_keys = {value: key for key, value in self.STATUS_KEYS.items()}
        num_days = grid["calendar"]["num_days"]

        for section in grid["sections"]:
            ws = workbook.add_worksheet(section["name"][:31] or "Attendance")
            ws.write(0, 0, "Section", header)
            ws.write(0, 1, section["display_name"], header)
            ws.write(0, 2, section.get("department") or "", header)
            ws.write(1, 1, "Student", header)
            ws.write(1, 0, "#", header)
            for day in range(1, num_days + 1):
                meta = grid["calendar"]["days"][day - 1]
                header_text = str(day)
                if meta.get("weekend"):
                    header_text = "\u2600 " + str(day)
                if meta.get("holiday"):
                    header_text = f"{day}*"
                ws.write(1, day + 1, header_text, header)
            ws.write(1, num_days + 2, "Absent", header)
            ws.write(1, num_days + 3, "Present", header)
            ws.write(1, num_days + 4, "Late", header)
            ws.write(1, num_days + 5, "Excused", header)
            ws.write(1, num_days + 6, "Rate %", header)

            for index, student in enumerate(section["students"], start=2):
                ws.write(index, 0, index - 1, name_cell)
                ws.write(index, 1, student["name"], name_cell)
                counts = {"absent": 0, "present": 0, "late": 0, "excused": 0}
                for column, cell_data in enumerate(student.get("cells") or [], start=2):
                    code = cell_data.get("code")
                    if not code:
                        continue
                    status = code_keys.get(code)
                    if status:
                        counts[status] += 1
                    ws.write(index, column, code, cell)
                rate = self._attendance_percentage(counts)
                ws.write(index, num_days + 2, counts["absent"], cell)
                ws.write(index, num_days + 3, counts["present"], cell)
                ws.write(index, num_days + 4, counts["late"], cell)
                ws.write(index, num_days + 5, counts["excused"], cell)
                ws.write(index, num_days + 6, rate, rate_cell)

            ws.set_column(0, 1, 22)
            ws.set_column(2, num_days + 2, 5)
            ws.set_header(f"&C&9Attendance Grid - {section['name']} - {month}/{year}")
            ws.set_footer("&C&P")

        workbook.close()
        return buffer.getvalue()

    @api.model
    def build_grid_csv(self, month, year, section_ids):
        import csv as csv_mod

        month, year, grid = self._export_grid_data(month, year, section_ids)
        if not grid.get("sections"):
            raise ValidationError(_("No class sections are available for export."))
        num_days = grid["calendar"]["num_days"]
        buffer = io.StringIO()
        writer = csv_mod.writer(buffer)
        writer.writerow(["Attendance Grid", f"{month}/{year}", "Generated %s" % fields.Datetime.now()])
        writer.writerow([])
        code_keys = {value: key for key, value in self.STATUS_KEYS.items()}
        for section in grid["sections"]:
            writer.writerow([section["display_name"], section["department"] or ""])
            header = ["#", "Student", "Code"]
            header += [str(day) for day in range(1, num_days + 1)]
            header += ["Absent", "Present", "Late", "Excused", "Rate %"]
            writer.writerow(header)
            for index, student in enumerate(section["students"], start=1):
                counts = {"absent": 0, "present": 0, "late": 0, "excused": 0}
                row = [index, student["name"], student["code"]]
                for column in student["cells"]:
                    code = column.get("code")
                    if code:
                        status = code_keys.get(code)
                        if status:
                            counts[status] += 1
                    row.append(code if code else "")
                rate = self._attendance_percentage(counts)
                row += [counts["absent"], counts["present"], counts["late"],
                        counts["excused"], rate]
                writer.writerow(row)
            writer.writerow([])
        return buffer.getvalue().encode("utf-8")

    @api.model
    def build_at_risk_csv(self, month, year, section_ids):
        import csv as csv_mod

        data = self.get_at_risk_data(month, year, section_ids)
        buffer = io.StringIO()
        writer = csv_mod.writer(buffer)
        writer.writerow(["At-Risk Attendance Students", f"Period: {month or 'All'}/{year or 'All'}"])
        writer.writerow(["Threshold", "%s%%" % data["threshold"]])
        writer.writerow([])
        writer.writerow(["Student", "Code", "Department", "Present", "Absent", "Late",
                         "Excused", "Total", "Rate %"])
        for student in data["students"]:
            writer.writerow([
                student["name"], student["code"], student["department"] or "",
                student["counts"]["present"], student["counts"]["absent"],
                student["counts"]["late"], student["counts"]["excused"],
                student["total"], student["rate"],
            ])
        return buffer.getvalue().encode("utf-8")

    # ------------------------------------------------------------- Demo seed
    @api.model
    def _seed_attendance_demo(self):
        """Deterministic demo attendance for every role (Attendance spec STEP 9).

        Idempotent: existing records are never overwritten, missing ones are
        created. Relies on the demo link fields being populated first
        (res.users._fix_demo_attendance_links).
        """
        Section = self.env["university.class.section"].sudo()
        sections = Section.search([("name", "in", ["DBMS-A101", "R2", "B202", "GM-Y1-A"])])
        if not sections:
            return True

        statuses = ["present", "present", "present", "late",
                    "present", "absent", "present", "excused", "present", "present"]

        def weekday_status(section_index, student_index, day):
            # Column of the generated pattern that a (student,day) maps onto.
            pick = (student_index * 3 + section_index * 2 + day) % len(statuses)
            return statuses[pick]

        created = 0
        for section_index, section in enumerate(sections):
            students = self._attendance_sheet_students(section)
            for student_index, student in enumerate(students):
                for day in range(1, 31):
                    if calendar.weekday(2026, 9, day) >= 5:
                        continue
                    att_date = date(2026, 9, day)
                    status = weekday_status(section_index, student_index, day)
                    existing = self.search([
                        ("section_id", "=", section.id),
                        ("date", "=", att_date),
                        ("student_id", "=", student.id),
                    ], limit=1)
                    if existing:
                        continue
                    self.create({
                        "student_id": student.id,
                        "section_id": section.id,
                        "date": att_date,
                        "status": status,
                    })
                    created += 1
        _logger = __import__("logging").getLogger(__name__)
        _logger.info("Attendance demo seed: created %s records", created)
        return True
