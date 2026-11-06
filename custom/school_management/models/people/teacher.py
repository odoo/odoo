import re

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


TITLES_MAP = {
    "dr.": "dr",
    "dr": "dr",
    "prof.": "prof",
    "prof": "prof",
    "mr.": "mr",
    "mr": "mr",
    "ms.": "ms",
    "ms": "ms",
    "mrs.": "mrs",
    "mrs": "mrs",
}


def _normalize_name_and_extract_title(raw_name, explicit_title=None):
    if not raw_name or not isinstance(raw_name, str):
        return explicit_title, raw_name
    parts = raw_name.strip().split()
    if not parts:
        return explicit_title, ""
    first_lower = parts[0].lower()
    title = explicit_title
    if first_lower in TITLES_MAP:
        if not title:
            title = TITLES_MAP[first_lower]
        parts = parts[1:]
    normalized_name = " ".join(part.capitalize() for part in parts)
    return title, normalized_name


def _hod_assignment(teacher):
    return teacher.assignment_ids.filtered(
        lambda a: a.active and a.role == "department_head"
    )[:1]


def _dean_assignment(teacher):
    return teacher.assignment_ids.filtered(
        lambda a: a.active and a.role == "dean"
    )[:1]


def _is_positive_boolean_search(operator, value):
    if operator in ("=", "=="):
        return bool(value)
    if operator in ("!=", "<>"):
        return not bool(value)
    if operator == "in":
        vals = set(value) if hasattr(value, "__iter__") else {value}
        if True in vals and False not in vals:
            return True
        if False in vals and True not in vals:
            return False
    if operator == "not in":
        vals = set(value) if hasattr(value, "__iter__") else {value}
        if True in vals and False not in vals:
            return False
        if False in vals and True not in vals:
            return True
    return bool(value)


class Teacher(models.Model):
    _name = "university.teacher"
    _inherit = ["mail.thread", "mail.activity.mixin", "avatar.mixin"]
    _description = "University Teacher"
    _order = "name, id"

    # Personal Information
    name = fields.Char(string="Teacher Name", required=True)
    title = fields.Selection(
        [
            ("dr", "Dr."),
            ("prof", "Prof."),
            ("mr", "Mr."),
            ("ms", "Ms."),
            ("mrs", "Mrs."),
        ],
        string="Title",
    )
    teacher_id = fields.Char(string="Staff ID", copy=False, index=True)
    image_1920 = fields.Image(string="Photo", max_width=1920, max_height=1920)
    user_id = fields.Many2one(
        "res.users",
        string="Related User",
        ondelete="set null",
        help="Optionally link this academic staff member to their Odoo login for role-based access.",
    )
    gender = fields.Selection(
        [
            ("male", "Male"),
            ("female", "Female"),
            ("other", "Other"),
        ],
        string="Gender",
    )
    date_of_birth = fields.Date(string="Date of Birth")

    # Contact Information
    phone = fields.Char(string="Phone")
    email = fields.Char(string="Email")
    address = fields.Text(string="Address")

    # Academic Information
    faculty_id = fields.Many2one(
        "university.faculty",
        string="Faculty",
        related="department_id.faculty_id",
        store=True,
        readonly=True,
        help="Faculty is derived from the teacher's department.",
    )
    department_id = fields.Many2one(
        "university.department",
        string="Department",
    )
    position = fields.Selection(
        [
            ("professor", "Professor"),
            ("associate_professor", "Associate Professor"),
            ("assistant_professor", "Assistant Professor"),
            ("lecturer", "Lecturer"),
            ("instructor", "Instructor"),
        ],
        string="Position",
        help="Academic position. Administrative roles (Dean / HOD) are separate appointments.",
    )
    specialization = fields.Char(string="Specialization")
    qualification = fields.Char(string="Qualification")
    hire_date = fields.Date(string="Hire Date")

    # Status
    active = fields.Boolean(string="Active", default=True)

    # Color for Kanban left stripe
    color = fields.Integer(
        string="Color",
        related="faculty_id.color",
        store=True,
        readonly=True,
    )

    # Teaching
    subject_ids = fields.Many2many(
        "university.subject",
        "university_teacher_subject_rel",
        "teacher_id",
        "subject_id",
        string="Subjects",
    )
    section_ids = fields.One2many(
        "university.class.section",
        "teacher_id",
        string="Class Sections",
    )
    timetable_slot_ids = fields.One2many(
        "university.timetable.slot",
        "teacher_id",
        string="Timetable Sessions",
    )
    class_count = fields.Integer(
        string="Class Count",
        compute="_compute_teaching_stats",
        store=True,
    )
    weekly_hours = fields.Float(
        string="Weekly Hours",
        compute="_compute_teaching_stats",
        store=True,
    )

    # Attendance & Presence
    attendance_ids = fields.One2many(
        "university.staff.attendance",
        "staff_id",
        string="Attendance Records",
    )
    is_present = fields.Boolean(
        string="Present Today",
        compute="_compute_presence",
        search="_search_is_present",
    )
    on_leave = fields.Boolean(
        string="On Leave",
        compute="_compute_presence",
        search="_search_on_leave",
    )
    notes = fields.Text(string="Notes")

    # Administrative responsibilities (derived from role assignments)
    assignment_ids = fields.One2many(
        "university.academic.assignment",
        "staff_id",
        string="Role Assignments",
    )
    is_head = fields.Boolean(
        string="Is Head",
        compute="_compute_is_head",
        store=True,
        help="True if the staff member currently holds an active Dean, Vice Dean, or HOD appointment.",
    )
    is_dean = fields.Boolean(
        string="Is Dean",
        compute="_compute_admin_roles",
        store=True,
        help="Whether this staff member currently holds an active Dean appointment.",
    )
    is_hod = fields.Boolean(
        string="Is Head of Department",
        compute="_compute_admin_roles",
        store=True,
        help="Whether this staff member currently holds an active HOD appointment.",
    )
    dean_appointment_start = fields.Date(
        string="Dean Appointment Start",
        compute="_compute_admin_appointments",
    )
    dean_appointment_end = fields.Date(
        string="Dean Appointment End",
        compute="_compute_admin_appointments",
    )
    hod_appointment_start = fields.Date(
        string="HOD Appointment Start",
        compute="_compute_admin_appointments",
    )
    hod_appointment_end = fields.Date(
        string="HOD Appointment End",
        compute="_compute_admin_appointments",
    )
    managed_faculty_id = fields.Many2one(
        "university.faculty",
        string="Managed Faculty",
        compute="_compute_managed_scopes",
        store=True,
        index=True,
    )
    managed_department_id = fields.Many2one(
        "university.department",
        string="Managed Department",
        compute="_compute_managed_scopes",
        store=True,
        index=True,
    )
    advisee_ids = fields.One2many(
        "university.student",
        "advisor_id",
        string="Advisees",
    )
    advisee_count = fields.Integer(
        string="Advisee Count",
        compute="_compute_advisee_count",
    )

    # Academic Credentials & Employment Documentation
    resume_file = fields.Binary(string="Curriculum Vitae (CV)", attachment=True)
    resume_filename = fields.Char(string="CV Filename")
    degree_file = fields.Binary(string="Highest Degree & Transcripts", attachment=True)
    degree_filename = fields.Char(string="Degree Filename")
    contract_file = fields.Binary(string="Employment Contract", attachment=True)
    contract_filename = fields.Char(string="Contract Filename")
    id_card_file = fields.Binary(string="National ID / Passport", attachment=True)
    id_card_filename = fields.Char(string="ID Document Filename")
    doc_verification_status = fields.Selection(
        [
            ("verified", "Verified & Authenticated"),
            ("pending", "Pending Verification"),
            ("requires_update", "Requires Update"),
        ],
        string="Credentials Status",
        default="verified",
        tracking=True,
    )
    verification_date = fields.Date(string="Verified On")
    verified_by = fields.Many2one("res.users", string="Verified By")
    research_interests = fields.Text(string="Research Interests & Expertise")
    publications_summary = fields.Text(string="Key Publications & Research Projects")
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "university_teacher_attachment_rel",
        "teacher_id",
        "attachment_id",
        string="Additional Documents & Certifications",
    )

    # Odoo 19 Constraints / Indexes
    _unique_user_id = models.UniqueIndex(
        "(user_id) WHERE user_id IS NOT NULL",
        "A staff login can only be linked to one academic staff record.",
    )
    _unique_teacher_id = models.UniqueIndex(
        "(lower(teacher_id)) WHERE teacher_id IS NOT NULL",
        "The Staff ID must be unique.",
    )
    _unique_email = models.UniqueIndex(
        "(lower(email)) WHERE email IS NOT NULL",
        "The email address must be unique.",
    )

    @api.depends("name", "title")
    def _compute_display_name(self):
        title_labels = dict(self._fields["title"].selection)
        for teacher in self:
            name = teacher.name or ""
            if teacher.title:
                t_label = title_labels.get(teacher.title, teacher.title)
                teacher.display_name = f"{t_label} {name}".strip()
            else:
                teacher.display_name = name

    @api.constrains("email")
    def _check_email_format(self):
        email_regex = re.compile(r"^[\w\.\+\-]+@[a-zA-Z0-9\-]+(\.[a-zA-Z0-9\-]+)+$")
        for rec in self:
            if rec.email:
                clean = rec.email.strip()
                if not email_regex.match(clean):
                    raise ValidationError(_("Invalid email address: '%(email)s'.") % {"email": rec.email})

    @api.depends("assignment_ids.active", "assignment_ids.role", "assignment_ids.staff_id")
    def _compute_is_head(self):
        head_records = self.env["university.academic.assignment"]._read_group(
            [
                ("staff_id", "in", self.ids),
                ("active", "=", True),
                ("role", "in", ("dean", "vice_dean", "department_head")),
            ],
            groupby=["staff_id"],
            aggregates=["__count"],
        )
        head_staff_ids = {staff.id for staff, count in head_records}
        for teacher in self:
            teacher.is_head = teacher.id in head_staff_ids

    def _compute_presence(self):
        today = fields.Date.context_today(self)
        attendance_records = self.env["university.staff.attendance"]._read_group(
            [
                ("staff_id", "in", self.ids),
                ("date", "=", today),
            ],
            groupby=["staff_id", "status"],
            aggregates=["__count"],
        )
        present_ids = set()
        leave_ids = set()
        for staff, status, count in attendance_records:
            if status in ("present", "late", "official_duty", "half_day"):
                present_ids.add(staff.id)
            elif status == "leave":
                leave_ids.add(staff.id)

        for teacher in self:
            teacher.is_present = teacher.id in present_ids
            teacher.on_leave = teacher.id in leave_ids

    def _search_is_present(self, operator, value):
        today = fields.Date.context_today(self)
        attendances = self.env["university.staff.attendance"].search([
            ("date", "=", today),
            ("status", "in", ("present", "late", "official_duty", "half_day")),
        ])
        staff_ids = attendances.mapped("staff_id").ids
        if _is_positive_boolean_search(operator, value):
            return [("id", "in", staff_ids or [0])]
        return [("id", "not in", staff_ids or [0])]

    def _search_on_leave(self, operator, value):
        today = fields.Date.context_today(self)
        attendances = self.env["university.staff.attendance"].search([
            ("date", "=", today),
            ("status", "=", "leave"),
        ])
        staff_ids = attendances.mapped("staff_id").ids
        if _is_positive_boolean_search(operator, value):
            return [("id", "in", staff_ids or [0])]
        return [("id", "not in", staff_ids or [0])]

    @api.depends(
        "section_ids.active",
        "section_ids.teacher_id",
        "timetable_slot_ids.start_time",
        "timetable_slot_ids.end_time",
    )
    def _compute_teaching_stats(self):
        sec_records = self.env["university.class.section"]._read_group(
            [("teacher_id", "in", self.ids), ("active", "=", True)],
            groupby=["teacher_id"],
            aggregates=["__count"],
        )
        sec_map = {teacher.id: count for teacher, count in sec_records}

        slots = self.env["university.timetable.slot"].search([
            ("teacher_id", "in", self.ids),
        ])
        hours_map = {teacher_id: 0.0 for teacher_id in self.ids}
        for slot in slots:
            if slot.start_time and slot.end_time:
                duration = (slot.end_time - slot.start_time).total_seconds() / 3600.0
                hours_map[slot.teacher_id.id] = hours_map.get(slot.teacher_id.id, 0.0) + duration

        for teacher in self:
            teacher.class_count = sec_map.get(teacher.id, 0)
            teacher.weekly_hours = round(hours_map.get(teacher.id, 0.0), 1)

    @api.depends(
        "assignment_ids.role",
        "assignment_ids.active",
        "assignment_ids.faculty_id",
        "assignment_ids.department_id",
        "assignment_ids.start_date",
        "assignment_ids.end_date",
    )
    def _compute_admin_roles(self):
        for teacher in self:
            teacher.is_dean = bool(_dean_assignment(teacher))
            teacher.is_hod = bool(_hod_assignment(teacher))

    @api.depends(
        "assignment_ids",
        "assignment_ids.staff_id",
        "assignment_ids.role",
        "assignment_ids.active",
        "assignment_ids.faculty_id",
        "assignment_ids.department_id",
        "assignment_ids.start_date",
    )
    def _compute_managed_scopes(self):
        for teacher in self:
            # Match the assignment model's ordering independently of cached relation order.
            assignments = teacher.with_context(active_test=False).assignment_ids.sorted(
                key=lambda assignment: (
                    assignment.start_date or fields.Date.to_date("0001-01-01"),
                    assignment.id or 0,
                ),
                reverse=True,
            )
            dean = assignments.filtered(lambda assignment: assignment.active and assignment.role == "dean")[:1]
            head = assignments.filtered(lambda assignment: assignment.active and assignment.role == "department_head")[:1]
            teacher.managed_faculty_id = dean.faculty_id
            teacher.managed_department_id = head.department_id

    @api.depends(
        "assignment_ids.role",
        "assignment_ids.active",
        "assignment_ids.faculty_id",
        "assignment_ids.department_id",
        "assignment_ids.start_date",
        "assignment_ids.end_date",
    )
    def _compute_admin_appointments(self):
        for teacher in self:
            dean_asg = _dean_assignment(teacher)
            head_asg = _hod_assignment(teacher)

            teacher.dean_appointment_start = dean_asg.start_date
            teacher.dean_appointment_end = dean_asg.end_date

            teacher.hod_appointment_start = head_asg.start_date
            teacher.hod_appointment_end = head_asg.end_date

    @api.onchange("department_id")
    def _onchange_department_id(self):
        if self.department_id and self.subject_ids:
            self.subject_ids = self.subject_ids.filtered(
                lambda s: s.department_id == self.department_id
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "name" in vals:
                title, norm_name = _normalize_name_and_extract_title(vals.get("name"), vals.get("title"))
                vals["name"] = norm_name
                if title and not vals.get("title"):
                    vals["title"] = title

            raw_id = vals.get("teacher_id")
            if not raw_id or not str(raw_id).strip():
                vals["teacher_id"] = (
                    self.env["ir.sequence"].next_by_code("university.teacher")
                    or _("New")
                )
            elif isinstance(raw_id, str):
                vals["teacher_id"] = raw_id.strip()

            if "email" in vals and isinstance(vals["email"], str):
                vals["email"] = vals["email"].strip()

        records = super().create(vals_list)
        for rec in records:
            if rec.user_id and rec.user_id.teacher_id != rec:
                rec.user_id.sudo().write({"teacher_id": rec.id})
        return records

    def write(self, vals):
        clean_vals = dict(vals)
        if "name" in clean_vals:
            title, norm_name = _normalize_name_and_extract_title(clean_vals.get("name"), clean_vals.get("title"))
            clean_vals["name"] = norm_name
            if title and not clean_vals.get("title"):
                clean_vals["title"] = title

        if "teacher_id" in clean_vals and isinstance(clean_vals["teacher_id"], str):
            clean_vals["teacher_id"] = clean_vals["teacher_id"].strip()

        if "email" in clean_vals and isinstance(clean_vals["email"], str):
            clean_vals["email"] = clean_vals["email"].strip()

        res = super().write(clean_vals)
        if "user_id" in clean_vals:
            for rec in self:
                if rec.user_id and rec.user_id.teacher_id != rec:
                    rec.user_id.sudo().write({"teacher_id": rec.id})
        return res

    def unlink(self):
        for rec in self:
            blocking = []
            if rec.section_ids:
                blocking.append(_("%(count)d class section(s)", count=len(rec.section_ids)))
            if rec.timetable_slot_ids:
                blocking.append(_("%(count)d timetable session(s)", count=len(rec.timetable_slot_ids)))
            att_count = self.env["university.staff.attendance"].search_count([("staff_id", "=", rec.id)])
            if att_count:
                blocking.append(_("%(count)d attendance record(s)", count=att_count))
            if rec.assignment_ids:
                blocking.append(_("%(count)d role assignment(s)", count=len(rec.assignment_ids)))
            if blocking:
                raise UserError(
                    _("Cannot delete staff member '%(staff)s' because they have linked records: %(details)s. Archive the staff member instead.")
                    % {
                        "staff": rec.display_name or rec.name,
                        "details": ", ".join(blocking),
                    }
                )
        return super().unlink()

    def action_view_sections(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("school_management.action_university_class_section")
        action["domain"] = [("teacher_id", "=", self.id)]
        action["context"] = {"default_teacher_id": self.id}
        return action

    def action_view_attendance(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("school_management.action_university_staff_attendance")
        action["domain"] = [("staff_id", "=", self.id)]
        action["context"] = {"default_staff_id": self.id}
        return action

    def _compute_advisee_count(self):
        for teacher in self:
            teacher.advisee_count = len(teacher.advisee_ids)

    def action_view_advisees(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Assigned Advisees - %s", self.display_name),
            "res_model": "university.student",
            "view_mode": "list,kanban,form",
            "domain": [("advisor_id", "=", self.id)],
            "context": {"default_advisor_id": self.id},
        }

    def action_create_user(self):
        self.ensure_one()
        if not self.env.su and not self.env.user.has_group("school_management.group_school_admin"):
            raise AccessError(_("Only University Administrators can create teacher login accounts."))

        email = (self.email or "").strip()
        if not email:
            raise UserError(_("Cannot create user: teacher %s has no email address.") % self.display_name)

        if self.user_id:
            raise UserError(_("Teacher %s is already linked to user account %s.") % (self.display_name, self.user_id.login))

        Users = self.env["res.users"].sudo()
        teacher_group = self.env.ref("school_management.group_school_teacher")
        dashboard_group = self.env.ref("school_management.group_teacher_dashboard")
        internal_group = self.env.ref("base.group_user")

        existing_user = Users.search([("login", "=ilike", email)], limit=1)
        if existing_user:
            if existing_user.teacher_id and existing_user.teacher_id != self:
                raise UserError(
                    _("Email %(email)s is already linked to another teacher: %(teacher)s.")
                    % {"email": email, "teacher": existing_user.teacher_id.name}
                )
            existing_user.write({
                "teacher_id": self.id,
                "group_ids": [
                    (4, internal_group.id),
                    (4, teacher_group.id),
                    (4, dashboard_group.id),
                ],
            })
            self.sudo().write({"user_id": existing_user.id})
            existing_user.action_reset_password()
        else:
            user = Users.create({
                "name": self.name,
                "login": email,
                "email": email,
                "teacher_id": self.id,
                "group_ids": [(6, 0, [internal_group.id, teacher_group.id, dashboard_group.id])],
            })
            self.sudo().write({"user_id": user.id})
            user.with_context(create_user=1).action_reset_password()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("User Created"),
                "message": _("Login account created for %s with email '%s'. A password setup email was sent.")
                % (self.display_name, email),
                "type": "success",
                "sticky": False,
            },
        }

    def action_reset_password(self):
        self.ensure_one()
        if not self.env.su and not self.env.user.has_group("school_management.group_school_admin"):
            raise AccessError(_("Only University Administrators can reset teacher passwords."))

        if not self.user_id:
            raise UserError(_("Teacher %s does not have a linked login account.") % self.display_name)

        self.user_id.sudo().action_reset_password()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Password Reset"),
                "message": _("A password reset email was sent to %s.") % self.user_id.login,
                "type": "success",
                "sticky": False,
            },
        }

    @api.model
    def action_open_own_profile(self):
        """Open the existing staff profile linked to the current login.

        A teacher must never need create access on ``university.teacher`` just
        to open their profile.  Administrators without a linked staff record
        are sent to the normal staff list instead.
        """
        teacher = self.search([("user_id", "=", self.env.user.id)], limit=1)
        if not teacher:
            if self.env.user.has_group("school_management.group_school_admin") or self.env.user.has_group("base.group_system"):
                return self.env["ir.actions.act_window"]._for_xml_id(
                    "school_management.action_university_teacher"
                )
            raise UserError(
                _("No teacher profile is linked to your login. Please contact an administrator.")
            )

        return {
            "type": "ir.actions.act_window",
            "name": _("My Profile"),
            "res_model": "university.teacher",
            "res_id": teacher.id,
            "views": [
                (self.env.ref("school_management.view_university_teacher_profile_form").id, "form")
            ],
            "view_mode": "form",
            "target": "current",
            "context": {
                "create": False,
                "edit": True,
                "delete": False,
            },
        }

    def action_normalize_titles_and_names(self):
        records = self if self else self.search([])
        updated = 0
        for t in records:
            raw_name = t.name or ""
            parts = raw_name.strip().split()
            if not parts:
                continue
            first_lower = parts[0].lower()
            detected_title = TITLES_MAP.get(first_lower)
            has_embedded_title = detected_title is not None
            cleaned_parts = parts[1:] if has_embedded_title else parts
            normalized_name = " ".join(p.capitalize() for p in cleaned_parts)
            target_title = detected_title or t.title
            if t.name != normalized_name or t.title != target_title:
                vals = {"name": normalized_name}
                if target_title:
                    vals["title"] = target_title
                t.write(vals)
                t._compute_display_name()
                updated += 1
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Staff Name & Title Normalization"),
                "message": _("%(count)d staff record(s) normalized.", count=updated),
                "type": "success",
                "sticky": False,
            },
        }
