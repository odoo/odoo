from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccountFiscalYear(models.Model):
    _name = "account.fiscal.year"
    _description = "Fiscal Year"
    _order = "date_from desc"

    name = fields.Char(required=True)
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    active = fields.Boolean(default=True)

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for fiscal_year in self:
            if fiscal_year.date_from and fiscal_year.date_to and fiscal_year.date_from >= fiscal_year.date_to:
                raise ValidationError("Fiscal year start date must be before end date.")

    @api.constrains("date_from", "date_to", "company_id")
    def _check_overlapping(self):
        for fiscal_year in self:
            if not fiscal_year.date_from or not fiscal_year.date_to or not fiscal_year.company_id:
                continue
            overlapping_domain = [
                ("id", "!=", fiscal_year.id),
                ("company_id", "=", fiscal_year.company_id.id),
                ("date_from", "<=", fiscal_year.date_to),
                ("date_to", ">=", fiscal_year.date_from),
            ]
            if self.search_count(overlapping_domain):
                raise ValidationError(
                    "Fiscal years cannot overlap for the same company."
                )

    @api.model
    def find_daterange_fy(self, dt):
        date_value = fields.Date.to_date(dt) if dt else fields.Date.context_today(self)
        return self.search(
            [
                ("company_id", "=", self.env.company.id),
                ("date_from", "<=", date_value),
                ("date_to", ">=", date_value),
                ("active", "=", True),
            ],
            order="date_from desc",
            limit=1,
        )

