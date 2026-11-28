from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class UniversityYearRolloverWizard(models.TransientModel):
    _name = "university.year.rollover.wizard"
    _description = "Academic Year Rollover"

    source_year_id = fields.Many2one(
        "university.academic.year",
        string="Source Academic Year",
        required=True,
        readonly=True,
    )
    new_year_name = fields.Char(string="New Academic Year", required=True)
    new_year_start_date = fields.Date(string="New Start Date", required=True)

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        source = self.env["university.academic.year"].browse(
            self.env.context.get("active_id")
        ).exists()
        if source:
            values.setdefault("source_year_id", source.id)
            values.setdefault("new_year_name", source.name)
            values.setdefault("new_year_start_date", source.date_start)
        return values

    def action_rollover(self):
        self.ensure_one()
        source = self.source_year_id
        if not source:
            raise UserError("Select a source academic year.")
        if source.state not in ("running", "closed"):
            raise ValidationError(
                "Rollover is available only for running or closed academic years."
            )
        if self.env["university.academic.year"].search_count(
            [("name", "=", self.new_year_name), ("id", "!=", source.id)]
        ):
            raise ValidationError(
                "An academic year with this name already exists."
            )
        delta = self.new_year_start_date - source.date_start

        def shifted(value):
            return value + delta if value else False

        new_year = self.env["university.academic.year"].create({
            "name": self.new_year_name,
            "date_start": shifted(source.date_start),
            "date_end": shifted(source.date_end),
            "current": False,
            "active": True,
            "state": "draft",
        })

        for semester in source.with_context(active_test=False).semester_ids:
            new_semester = self.env["university.semester"].create({
                "name": semester.name,
                "academic_year_id": new_year.id,
                "semester_type": semester.semester_type,
                "date_start": shifted(semester.date_start),
                "date_end": shifted(semester.date_end),
                "active": semester.active,
            })
            for term in semester.with_context(active_test=False).department_term_ids:
                self.env["university.department.term"].create({
                    "semester_id": new_semester.id,
                    "department_id": term.department_id.id,
                    "date_start": shifted(term.date_start),
                    "date_end": shifted(term.date_end),
                    "registration_start": shifted(term.registration_start),
                    "registration_end": shifted(term.registration_end),
                    "add_drop_start": shifted(term.add_drop_start),
                    "add_drop_end": shifted(term.add_drop_end),
                    "grade_deadline": shifted(term.grade_deadline),
                })

        for holiday in source.with_context(active_test=False).holiday_ids:
            self.env["university.holiday"].create({
                "name": holiday.name,
                "date_start": shifted(holiday.date_start),
                "date_end": shifted(holiday.date_end),
                "academic_year_id": new_year.id,
                "faculty_id": holiday.faculty_id.id,
            })

        return {
            "type": "ir.actions.act_window",
            "res_model": "university.academic.year",
            "view_mode": "form",
            "res_id": new_year.id,
            "target": "current",
        }
