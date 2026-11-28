from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class UniversityEnrollment(models.Model):
    _inherit = "university.enrollment"

    has_book = fields.Boolean(
        string="Has Book",
        default=False,
        help="Indicates whether the enrolled student already has the required textbook for this course.",
        tracking=True,
    )
    book_status = fields.Selection(
        [
            ("no_book", "No Book"),
            ("has_book", "Has Book"),
        ],
        string="Book Status",
        compute="_compute_book_status",
        store=True,
    )

    @api.depends("has_book")
    def _compute_book_status(self):
        for rec in self:
            rec.book_status = "has_book" if rec.has_book else "no_book"

    def action_toggle_has_book(self):
        for rec in self:
            rec.has_book = not rec.has_book
        return True

    @api.constrains("student_id", "class_section_id", "status", "enrollment_date")
    def _check_enrollment_deadline_closed(self):
        if self.env.context.get("bypass_enrollment_deadline"):
            return
        for rec in self:
            section = rec.class_section_id or rec.section_id
            if not section or not section.enroll_deadline:
                continue
            if rec.status not in ("draft", "enrolled", "to_approve"):
                continue

            today = fields.Date.context_today(rec)
            if section.enroll_deadline < today or section.enroll_closed:
                raise ValidationError(
                    _(
                        "Enrollment for class section '%(section)s' is closed "
                        "(deadline %(deadline)s). New enrollments are not allowed."
                    )
                    % {
                        "section": section.display_name,
                        "deadline": section.enroll_deadline,
                    }
                )
