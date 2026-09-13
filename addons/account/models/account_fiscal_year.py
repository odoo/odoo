from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountFiscalYear(models.Model):
    _name = "account.fiscal.year"
    _description = "Fiscal Year"

    name = fields.Char(required=True)
    date_from = fields.Date(
        string="Start Date",
        required=True,
        help="Start Date, included in the fiscal year.",
    )
    date_to = fields.Date(
        string="End Date",
        required=True,
        help="Ending Date, included in the fiscal year.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        required=True,
    )

    @api.constrains("date_from", "date_to", "company_id")
    @_debug.perf.timed
    def _check_dates(self):
        others_by_company = self.search(
            [("company_id", "in", self.company_id.ids)]
        ).grouped("company_id")
        for fy in self:
            date_from = fy.date_from
            date_to = fy.date_to
            if date_to < date_from:
                _debug.logic(
                    "fiscal_year_rejected", fiscal_year=fy, reason="inverted_dates"
                )
                raise ValidationError(
                    _("The ending date must not be prior to the starting date.")
                )
            if fy.company_id.parent_id:
                _debug.logic(
                    "fiscal_year_rejected", fiscal_year=fy, reason="child_company"
                )
                raise ValidationError(
                    _("You cannot have a fiscal year on a child company.")
                )

            overlapping = any(
                other != fy
                and other.date_from <= fy.date_to
                and other.date_to >= fy.date_from
                for other in others_by_company.get(fy.company_id, self.browse())
            )
            if overlapping:
                _debug.logic("fiscal_year_rejected", fiscal_year=fy, reason="overlap")
                raise ValidationError(
                    _(
                        "You can not have an overlap between two fiscal years, please correct the start and/or end dates of your fiscal years."
                    )
                )
