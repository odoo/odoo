from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError
from odoo.fields import Domain

class ResUsers(models.Model):
    """Extend the user to link them to an academic staff record, enabling
    organizational record rules (a teacher sees their own data, a HOD their
    department, a Dean their faculty)."""
    _inherit = "res.users"
    teacher_id = fields.Many2one(
        "university.teacher",
        string="Academic Staff",
        ondelete="set null",
        help="The academic staff record this user belongs to.",
    )

    _unique_teacher_id = models.UniqueIndex(
        "(teacher_id) WHERE teacher_id IS NOT NULL",
        "An academic staff record can only be linked to one user.",
    )

    @api.model
    def _get_login_domain(self, login):
        normalized_login = (login or "").strip()
        if "@" in normalized_login:
            return Domain("login", "=ilike", tools.escape_psql(normalized_login))
        return super()._get_login_domain(login)

    def _get_signup_student(self, email):
        normalized_email = (email or "").strip()
        if not normalized_email:
            raise UserError(_("A student email is required to create an account."))

        students = self.env["university.student"].sudo().search(
            [("email", "=ilike", normalized_email)],
            limit=2,
        )
        if not students:
            raise UserError(
                _("No student record was found for this email address. Please contact the administrator.")
            )
        if len(students) > 1:
            raise UserError(
                _("More than one student uses this email address. Please contact the administrator.")
            )

        student = students[0]
        if student.user_id:
            raise UserError(_("This student record is already linked to another login."))
        return student

    @api.model
    def _signup_create_user(self, values):
        if "partner_id" in values:
            return super()._signup_create_user(values)

        email = values.get("email") or values.get("login")
        student = self._get_signup_student(email)
        student_group = self.env.ref("school_management.group_school_student")
        internal_group = self.env.ref("base.group_user")

        signup_values = dict(values)
        # Default student sign-up creates an internal school user with the
        # regular student role.
        signup_values["group_ids"] = [(6, 0, [internal_group.id, student_group.id])]
        signup_values["share"] = False

        user = super()._signup_create_user(signup_values)
        student.write({"user_id": user.id})
        return user

    @api.model
    def _fix_demo_attendance_links(self):
        """Align the demo logins with the role assignments used by the
        attendance record rules (HOD -> department head, Dean -> faculty head)
        and give the HOD login the teacher capabilities expected by the
        attendance UI. Runs on every upgrade through a <function> record;
        fully idempotent and a no-op when the demo records are absent."""
        self._fix_demo_staff_links()

        teacher_model = self.env["university.teacher"].sudo()
        users = {
            login: user.sudo()
            for login in ("hod", "dean", "teacher")
            for user in self.search([("login", "=", login)], limit=1)
        }

        teacher_group = self.env.ref("school_management.group_school_teacher")
        hod_user = users.get("hod")
        if hod_user and teacher_group not in hod_user.group_ids:
            hod_user.write({"group_ids": [(4, teacher_group.id)]})

        jenkins = teacher_model.search([("name", "=", "Dr. Sarah Jenkins")], limit=1)
        xavier = teacher_model.search([("name", "=", "Prof. Charles Xavier")], limit=1)

        Assignment = self.env["university.academic.assignment"].sudo()
        today = fields.Date.context_today(self)

        if jenkins and jenkins.department_id and not Assignment.search([
            ("role", "=", "department_head"),
            ("department_id", "=", jenkins.department_id.id),
            ("active", "=", True),
        ], limit=1):
            Assignment.create({
                "staff_id": jenkins.id,
                "role": "department_head",
                "department_id": jenkins.department_id.id,
                "start_date": today,
            })

        if xavier and xavier.faculty_id and not Assignment.search([
            ("role", "=", "dean"),
            ("faculty_id", "=", xavier.faculty_id.id),
            ("active", "=", True),
        ], limit=1):
            Assignment.create({
                "staff_id": xavier.id,
                "role": "dean",
                "faculty_id": xavier.faculty_id.id,
                "start_date": today,
            })

        # B202 is the teacher-facing demo section; make sure the demo teacher
        # (Dr. Gregory Hous, linked to the "teacher" login) owns it instead of
        # an orphan staff record that has no portal user.
        homes = teacher_model.search([("name", "=", "Dr. Gregory Hous")], limit=1)
        section = self.env["university.class.section"].sudo().search(
            [("name", "=", "B202")], limit=1
        )
        if homes and section and \
                (not section.teacher_id or not section.teacher_id.user_id):
            if section.subject_id and homes not in section.subject_id.teacher_ids:
                section.subject_id.write({"teacher_ids": [(4, homes.id)]})
            section.write({"teacher_id": homes.id})
        return True

    @api.model
    def _fix_demo_staff_links(self):
        """One-time data migration: make res.users.teacher_id and
        university.teacher.user_id reciprocal for the seeded demo logins,
        pointing each login at the teacher record that actually holds the
        matching active role assignment. Idempotent; no-op when the demo
        records are absent."""
        mapping = [
            ("hod", "Dr. Sarah Jenkins"),
            ("dean", "Prof. Charles Xavier"),
            ("teacher", "Dr. Gregory Hous"),
        ]
        teacher_model = self.env["university.teacher"].sudo()
        users = {
            login: user.sudo()
            for login, _ in mapping
            for user in self.search([("login", "=", login)], limit=1)
        }

        teachers_to_clear = teacher_model.search(
            [("user_id", "in", [u.id for u in users.values() if u])]
        )
        if teachers_to_clear:
            teachers_to_clear.write({"user_id": False})
            teacher_model.flush_model(["user_id"])

        users_to_clear = self.sudo().search([
            "|",
            ("id", "in", [u.id for u in users.values() if u]),
            ("teacher_id", "!=", False),
        ])
        target_teachers = teacher_model.search([("name", "in", [t[1] for t in mapping])])
        if target_teachers:
            users_with_target = self.sudo().search([("teacher_id", "in", target_teachers.ids)])
            if users_with_target:
                users_with_target.write({"teacher_id": False})
                self.flush_model(["teacher_id"])

        for login, teacher_name in mapping:
            user = users.get(login)
            teacher = teacher_model.search(
                [("name", "=", teacher_name)], limit=1
            )
            if not user or not teacher:
                continue
            teacher.write({"user_id": user.id})
            user.write({"teacher_id": teacher.id})
