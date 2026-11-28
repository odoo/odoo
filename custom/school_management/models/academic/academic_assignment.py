from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import format_date


class UniversityAcademicAssignment(models.Model):
    _name = "university.academic.assignment"
    _description = "Academic Role Assignment"
    _order = "start_date desc, id desc"

    name = fields.Char(
        string="Reference",
        compute="_compute_name",
        store=True,
    )
    staff_id = fields.Many2one(
        "university.teacher",
        string="Academic Staff",
        required=True,
        ondelete="cascade",
    )
    staff_image = fields.Binary(related="staff_id.image_1920", string="Staff Photo")
    staff_avatar = fields.Binary(related="staff_id.avatar_128", string="Staff Avatar")
    staff_email = fields.Char(related="staff_id.email", string="Staff Email")
    staff_phone = fields.Char(related="staff_id.phone", string="Staff Phone")
    staff_code = fields.Char(related="staff_id.teacher_id", string="Staff ID")

    role = fields.Selection(
        [
            ("dean", "Head of Faculty"),
            ("vice_dean", "Vice Head of Faculty"),
            ("department_head", "Head of Department"),
        ],
        string="Role",
        required=True,
    )
    faculty_id = fields.Many2one(
        "university.faculty",
        string="Faculty",
        domain="[('active', '=', True)]",
    )
    department_id = fields.Many2one(
        "university.department",
        string="Department",
        domain="[('active', '=', True)]",
    )
    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date")
    active = fields.Boolean(string="Active", default=True)
    notes = fields.Text(string="Notes")

    @api.depends("staff_id", "role", "faculty_id", "department_id")
    def _compute_name(self):
        for rec in self:
            who = rec.staff_id.name or "Staff"
            role_label = dict(self._fields["role"].selection).get(rec.role, rec.role)
            scope = " / ".join(
                p for p in (rec.faculty_id.name, rec.department_id.name) if p
            )
            rec.name = f"{who} - {role_label}" + (f" ({scope})" if scope else "")

    @api.constrains("staff_id", "role", "faculty_id", "department_id", "start_date", "end_date")
    def _check_org_consistency(self):
        role_labels = dict(self._fields["role"].selection)
        for rec in self:
            label = role_labels.get(rec.role, rec.role)

            if rec.role in ("dean", "vice_dean") and not rec.faculty_id:
                raise ValidationError("A Head of Faculty / Vice Head must be assigned to a Faculty.")
            if rec.role == "department_head" and not rec.department_id:
                raise ValidationError("A Head of Department must be assigned to a Department.")

            staff = rec.staff_id
            if not staff.active:
                raise ValidationError(
                    f"{staff.name} is inactive and cannot hold the '{label}' role."
                )

            if rec.role in ("dean", "vice_dean") and rec.faculty_id:
                if staff.faculty_id != rec.faculty_id:
                    raise ValidationError(
                        f"{staff.name} is not a member of {rec.faculty_id.name} and cannot be assigned as its {label}."
                    )

            if rec.role == "department_head" and rec.department_id:
                if staff.department_id != rec.department_id:
                    raise ValidationError(
                        f"{staff.name} is not a member of {rec.department_id.name} and cannot be assigned as its Head."
                    )

            if rec.start_date and rec.end_date and rec.end_date <= rec.start_date:
                raise ValidationError(
                    "The End Date must be strictly after the Start Date."
                )

    @api.constrains("role", "faculty_id", "department_id", "start_date", "end_date", "active")
    def _check_no_overlapping_assignments(self):
        role_labels = dict(self._fields["role"].selection)
        for rec in self.filtered(lambda assignment: assignment.active and assignment.start_date):
            domain = [
                ("id", "!=", rec.id),
                ("active", "=", True),
                ("role", "=", rec.role),
                ("start_date", "<=", rec.end_date) if rec.end_date else ("id", "!=", 0),
                "|",
                ("end_date", "=", False),
                ("end_date", ">=", rec.start_date),
            ]
            if rec.role == "department_head":
                domain.append(("department_id", "=", rec.department_id.id))
            else:
                domain.append(("faculty_id", "=", rec.faculty_id.id))

            conflict = self.search(domain, limit=1)
            if conflict:
                role_label = role_labels.get(rec.role, rec.role)
                conflict_end = format_date(self.env, conflict.end_date) if conflict.end_date else _("ongoing")
                raise ValidationError(
                    _("%(staff)s is already %(role)s for %(scope)s from %(start)s to %(end)s - assignments cannot overlap.")
                    % {
                        "staff": conflict.staff_id.name,
                        "role": role_label,
                        "scope": rec.department_id.name or rec.faculty_id.name,
                        "start": format_date(self.env, conflict.start_date),
                        "end": conflict_end,
                    }
                )

    @api.constrains("role", "faculty_id", "department_id", "end_date", "active")
    def _check_one_active_head_per_scope(self):
        today = fields.Date.context_today(self)
        head_roles = {"dean", "department_head"}
        role_labels = dict(self._fields["role"].selection)
        for rec in self.filtered(lambda assignment: assignment.active and assignment.role in head_roles):
            domain = [
                ("id", "!=", rec.id),
                ("active", "=", True),
                ("role", "=", rec.role),
                "|",
                ("end_date", "=", False),
                ("end_date", ">=", today),
            ]
            if rec.role == "department_head":
                domain.append(("department_id", "=", rec.department_id.id))
                scope = rec.department_id.name
            else:
                domain.append(("faculty_id", "=", rec.faculty_id.id))
                scope = rec.faculty_id.name

            conflict = self.search(domain, limit=1)
            if conflict:
                raise ValidationError(
                    _("%(staff)s already holds %(role)s for %(scope)s with an active appointment; only one active Head may hold this scope at a time.")
                    % {
                        "staff": conflict.staff_id.name,
                        "role": role_labels.get(rec.role, rec.role),
                        "scope": scope,
                    }
                )

    @api.onchange("role")
    def _onchange_role(self):
        if self.role == "department_head":
            self.faculty_id = False
        elif self.role in ("dean", "vice_dean"):
            self.department_id = False

    @api.onchange("department_id")
    def _onchange_department_id(self):
        if self.department_id and self.role != "department_head":
            self.faculty_id = self.department_id.faculty_id

    @api.onchange("role", "faculty_id", "department_id")
    def _onchange_staff_scope(self):
        domain = [("active", "=", True)]
        if self.role == "department_head" and self.department_id:
            domain.append(("department_id", "=", self.department_id.id))
        elif self.role in ("dean", "vice_dean") and self.faculty_id:
            domain.append(("faculty_id", "=", self.faculty_id.id))
        return {"domain": {"staff_id": domain}}
