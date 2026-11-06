from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from .academic_lock import can_maintain_closed_year_records


class UniversityDepartmentTerm(models.Model):
    _name = "university.department.term"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Department Term"
    _order = "academic_year_id desc, semester_id, faculty_id, department_id"

    _semester_department_unique = models.Constraint(
        "UNIQUE (semester_id, department_id)",
        "A department can only have one term per semester.",
    )
    _date_range_constraint = models.Constraint(
        "CHECK (date_end >= date_start)",
        "The department term end date must be on or after the start date.",
    )

    semester_id = fields.Many2one(
        "university.semester",
        string="Semester",
        required=True,
        ondelete="cascade",
        index=True,
    )
    academic_year_id = fields.Many2one(
        "university.academic.year",
        string="Academic Year",
        related="semester_id.academic_year_id",
        store=True,
        readonly=True,
        index=True,
    )
    department_id = fields.Many2one(
        "university.department",
        string="Department",
        required=True,
        index=True,
    )
    faculty_id = fields.Many2one(
        "university.faculty",
        string="Faculty",
        related="department_id.faculty_id",
        store=True,
        readonly=True,
        index=True,
    )
    date_start = fields.Date(string="Start Date", required=True, tracking=True)
    date_end = fields.Date(string="End Date", required=True, tracking=True)
    registration_start = fields.Date(string="Registration Start")
    registration_end = fields.Date(string="Registration End")
    add_drop_deadline = fields.Date(string="Add/Drop Deadline")
    add_drop_start = fields.Date(string="Add/Drop Start")
    add_drop_end = fields.Date(string="Add/Drop End")
    withdraw_deadline = fields.Date(string="Withdraw Deadline")
    exam_start = fields.Date(string="Exam Start")
    exam_end = fields.Date(string="Exam End")
    grade_deadline = fields.Date(string="Grade Deadline")
    change_reason = fields.Text(string="Change Reason")

    teaching_weeks = fields.Float(
        string="Teaching Weeks", compute="_compute_teaching_weeks", store=True
    )
    min_teaching_weeks = fields.Float(
        string="Minimum Teaching Weeks",
        compute="_compute_min_teaching_weeks",
    )
    is_below_min_weeks = fields.Boolean(
        string="Below Minimum Weeks",
        compute="_compute_is_below_min_weeks",
        search="_search_is_below_min_weeks",
    )
    state = fields.Selection(
        [
            ("planned", "Planned"),
            ("running", "Running"),
            ("ended", "Ended"),
        ],
        string="State",
        compute="_compute_state",
        store=True,
        readonly=True,
        index=True,
    )
    active = fields.Boolean(string="Active", default=True)

    @api.depends("department_id", "semester_id")
    def _compute_display_name(self):
        for term in self:
            if term.department_id and term.semester_id:
                term.display_name = f"{term.department_id.name} - {term.semester_id.name}"
            elif term.department_id:
                term.display_name = term.department_id.name
            else:
                term.display_name = f"Term #{term.id}"

    @api.onchange("semester_id")
    def _onchange_semester_id(self):
        if self.semester_id:
            if not self.date_start or self.date_start != self.semester_id.date_start:
                self.date_start = self.semester_id.date_start
            if not self.date_end or self.date_end != self.semester_id.date_end:
                self.date_end = self.semester_id.date_end

    def _get_min_teaching_weeks(self):
        param = self.env["ir.config_parameter"].sudo().get_param(
            "school_management.min_teaching_weeks", "14"
        )
        try:
            return float(param)
        except (ValueError, TypeError):
            return 14.0

    def _compute_min_teaching_weeks(self):
        min_weeks = self._get_min_teaching_weeks()
        for term in self:
            term.min_teaching_weeks = min_weeks

    @api.depends("teaching_weeks")
    def _compute_is_below_min_weeks(self):
        min_weeks = self._get_min_teaching_weeks()
        for term in self:
            term.is_below_min_weeks = bool(term.teaching_weeks and term.teaching_weeks < min_weeks)

    def _search_is_below_min_weeks(self, operator, value):
        min_weeks = self._get_min_teaching_weeks()
        if (operator == "=" and value) or (operator == "!=" and not value):
            return [("teaching_weeks", "<", min_weeks)]
        return [("teaching_weeks", ">=", min_weeks)]

    @api.model_create_multi
    def create(self, vals_list):
        if not can_maintain_closed_year_records(self.env):
            semester_ids = [vals.get("semester_id") for vals in vals_list if vals.get("semester_id")]
            if semester_ids:
                semesters = self.env["university.semester"].browse(semester_ids).exists()
                if any(s.academic_year_id.state in ("closed", "archived") for s in semesters):
                    raise UserError("Cannot create department terms in a closed or archived academic year.")
        return super().create(vals_list)

    @api.depends("date_start", "date_end")
    def _compute_teaching_weeks(self):
        for term in self:
            if not term.date_start or not term.date_end:
                term.teaching_weeks = 0.0
                continue
            days = (term.date_end - term.date_start).days + 1
            term.teaching_weeks = round(days / 7.0, 1)

    @api.depends("date_start", "date_end")
    def _compute_state(self):
        today = fields.Date.context_today(self)
        for term in self:
            if not term.date_start or not term.date_end or today < term.date_start:
                term.state = "planned"
            elif today > term.date_end:
                term.state = "ended"
            else:
                term.state = "running"

    @api.constrains("semester_id", "date_start", "date_end")
    def _check_dates_within_semester(self):
        for term in self:
            semester = term.semester_id
            if not semester or not term.date_start or not term.date_end:
                continue
            if not semester.date_start or not semester.date_end:
                raise ValidationError(
                    "Department term dates require a semester with start and end dates."
                )
            if (
                term.date_start < semester.date_start
                or term.date_end > semester.date_end
            ):
                raise ValidationError(
                    "Department term dates must fall within the selected semester dates."
                )

    @api.constrains(
        "registration_start", "registration_end", "date_start", "date_end",
        "add_drop_deadline", "add_drop_start", "add_drop_end",
        "withdraw_deadline", "exam_start", "exam_end", "grade_deadline",
    )
    def _check_milestones(self):
        for term in self:
            if term.registration_start and term.registration_end \
                    and term.registration_end < term.registration_start:
                raise ValidationError(
                    "Registration end must be on or after registration start."
                )
            if term.registration_start and term.date_start \
                    and term.date_start < term.registration_start:
                raise ValidationError(
                    "Class start date cannot be before registration start."
                )

            if term.add_drop_deadline and term.date_start and term.date_end:
                if term.add_drop_deadline < term.date_start or term.add_drop_deadline > term.date_end:
                    raise ValidationError(
                        "Add/drop deadline must fall within term class dates."
                    )
            if term.withdraw_deadline and term.date_start and term.date_end:
                if term.withdraw_deadline < term.date_start or term.withdraw_deadline > term.date_end:
                    raise ValidationError(
                        "Withdraw deadline must fall within term class dates."
                    )

            if term.exam_start and term.exam_end \
                    and term.exam_end < term.exam_start:
                raise ValidationError(
                    "Exam end date must be on or after exam start date."
                )
            if term.exam_end and term.grade_deadline \
                    and term.grade_deadline < term.exam_end:
                raise ValidationError(
                    "Grade deadline must be on or after exam end date."
                )
            elif term.grade_deadline and term.date_end \
                    and term.grade_deadline < term.date_end:
                raise ValidationError(
                    "Grade deadline cannot be before the term end date."
                )

            if term.add_drop_start and term.add_drop_end \
                    and term.add_drop_end < term.add_drop_start:
                raise ValidationError(
                    "Add/drop end must be on or after add/drop start."
                )
            if term.registration_end and term.add_drop_start \
                    and term.add_drop_start < term.registration_end:
                raise ValidationError("Add/drop cannot start before registration ends.")

    def write(self, vals):
        if not can_maintain_closed_year_records(self.env):
            if any(term.academic_year_id.state in ("closed", "archived") for term in self):
                raise UserError("Department terms of a closed or archived academic year are read-only and cannot be modified.")

        changing_dates = {"date_start", "date_end"} & set(vals)
        old_values = {
            term.id: (term.date_start, term.date_end) for term in self
        } if changing_dates else {}
        if "date_end" in vals:
            new_end = fields.Date.to_date(vals["date_end"])
            today = fields.Date.context_today(self)
            for term in self:
                if new_end and term.date_end and new_end > term.date_end \
                        and today >= term.date_start \
                        and not (vals.get("change_reason") or term.change_reason):
                    raise ValidationError(
                        "A reason is required when extending a started term."
                    )

        result = super().write(vals)
        if changing_dates:
            for term in self:
                old_start, old_end = old_values[term.id]
                reason = (". Reason: %s" % term.change_reason) \
                    if term.change_reason else ""
                term.message_post(body=(
                    "Schedule changed by %s: start %s -> %s; end %s -> %s%s"
                    % (
                        self.env.user.display_name,
                        old_start or "-", term.date_start or "-",
                        old_end or "-", term.date_end or "-", reason,
                    )
                ))
        return result

    def unlink(self):
        if not can_maintain_closed_year_records(self.env):
            if any(term.academic_year_id.state in ("closed", "archived") for term in self):
                raise UserError("Cannot delete department terms of a closed or archived academic year.")
        return super().unlink()

    def is_registration_open(self, today=None):
        self.ensure_one()
        today = today or fields.Date.context_today(self)
        return bool(
            self.registration_start and self.registration_end
            and self.registration_start <= today <= self.registration_end
        )

    def is_add_drop_open(self, today=None):
        self.ensure_one()
        today = today or fields.Date.context_today(self)
        if self.add_drop_deadline and self.date_start:
            return bool(self.date_start <= today <= self.add_drop_deadline)
        return bool(
            self.add_drop_start and self.add_drop_end
            and self.add_drop_start <= today <= self.add_drop_end
        )

    @api.model
    def action_ending_soon(self):
        today = fields.Date.context_today(self)
        return {
            "type": "ir.actions.act_window",
            "name": "Ending Soon",
            "res_model": self._name,
            "view_mode": "list,form",
            "domain": [
                ("date_end", ">=", today),
                ("date_end", "<=", today + timedelta(days=14)),
            ],
        }

    @api.model
    def _cron_update_state(self):
        terms = self.search([])
        terms._compute_state()
        return True

    @api.model
    def _cron_create_deadline_activities(self):
        today = fields.Date.context_today(self)
        activity_type = self.env.ref(
            "mail.mail_activity_data_todo", raise_if_not_found=False
        )
        if not activity_type:
            return True
        model_id = self.env["ir.model"]._get_id(self._name)
        for term in self.search([]):
            user = term.department_id.head_id.user_id
            if not user:
                continue
            for event_name in ("registration_end", "date_end", "grade_deadline"):
                event_date = getattr(term, event_name)
                if not event_date or event_date - today != timedelta(days=7):
                    continue
                summary = "Department term %s: %s" % (term.id, event_name)
                if self.env["mail.activity"].search_count([
                    ("res_model_id", "=", model_id),
                    ("res_id", "=", term.id),
                    ("user_id", "=", user.id),
                    ("summary", "=", summary),
                ]):
                    continue
                self.env["mail.activity"].create({
                    "activity_type_id": activity_type.id,
                    "res_model_id": model_id,
                    "res_id": term.id,
                    "user_id": user.id,
                    "summary": summary,
                    "note": "Deadline: %s" % event_date,
                    "date_deadline": today,
                })
        return True

    @api.model
    def _cron_daily_maintenance(self):
        self._cron_update_state()
        self._cron_create_deadline_activities()
        return True
