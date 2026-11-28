from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from ..academic.academic_lock import can_maintain_closed_year_records


class UniversityHoliday(models.Model):
    _name = "university.holiday"
    _description = "University Holiday"
    _order = "date_start, name"

    name = fields.Char(string="Holiday", required=True)
    date_start = fields.Date(string="Start Date", required=True)
    date_end = fields.Date(string="End Date", required=True)
    academic_year_id = fields.Many2one(
        "university.academic.year",
        string="Academic Year",
        required=True,
        ondelete="cascade",
        index=True,
    )
    faculty_id = fields.Many2one(
        "university.faculty",
        string="Faculty",
        help="Leave empty for a university-wide holiday.",
        index=True,
    )

    _valid_date_range = models.Constraint(
        "CHECK (date_end >= date_start)",
        "Holiday end date must be on or after the start date.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        if not can_maintain_closed_year_records(self.env):
            year_ids = [vals.get("academic_year_id") for vals in vals_list if vals.get("academic_year_id")]
            if year_ids:
                years = self.env["university.academic.year"].browse(year_ids).exists()
                if any(year.state in ("closed", "archived") for year in years):
                    raise UserError("Holidays cannot be created in a closed or archived academic year.")
        return super().create(vals_list)

    def write(self, vals):
        if not can_maintain_closed_year_records(self.env):
            if any(holiday.academic_year_id.state in ("closed", "archived") for holiday in self):
                raise UserError("Holidays of a closed or archived academic year cannot be modified.")
        return super().write(vals)

    def unlink(self):
        if not can_maintain_closed_year_records(self.env):
            if any(holiday.academic_year_id.state in ("closed", "archived") for holiday in self):
                raise UserError("Holidays of a closed or archived academic year cannot be deleted.")
        return super().unlink()

    @api.constrains("date_start", "date_end", "academic_year_id")
    def _check_dates_within_year(self):
        for holiday in self:
            year = holiday.academic_year_id
            if not year or not holiday.date_start or not holiday.date_end:
                continue
            if holiday.date_start < year.date_start or holiday.date_end > year.date_end:
                raise ValidationError(
                    "Holiday dates must fall within the selected academic year."
                )
