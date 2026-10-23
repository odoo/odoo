# Copyright 2017-2020 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MisBudgetItemAbstract(models.AbstractModel):
    _name = "mis.budget.item.abstract"
    _description = "MIS Budget Item (Abstract Base Class)"

    budget_id = fields.Many2one(
        comodel_name="mis.budget.abstract",
        string="Budget",
        required=True,
        ondelete="cascade",
        index=True,
    )
    budget_date_from = fields.Date(
        related="budget_id.date_from", readonly=True, string="Budget Date From"
    )
    budget_date_to = fields.Date(
        related="budget_id.date_to", readonly=True, string="Budget Date To"
    )
    date_range_id = fields.Many2one(
        comodel_name="date.range",
        domain="[('date_start', '>=', budget_date_from),"
        " ('date_end', '<=', budget_date_to)]",
        string="Date range",
    )
    date_from = fields.Date(required=True, string="From")
    date_to = fields.Date(required=True, string="To")

    @api.onchange("date_range_id")
    def _onchange_date_range(self):
        for rec in self:
            if rec.date_range_id:
                rec.date_from = rec.date_range_id.date_start
                rec.date_to = rec.date_range_id.date_end

    @api.onchange("date_from", "date_to")
    def _onchange_dates(self):
        for rec in self:
            if rec.date_range_id:
                if (
                    rec.date_from != rec.date_range_id.date_start
                    or rec.date_to != rec.date_range_id.date_end
                ):
                    rec.date_range_id = False

    def _prepare_overlap_domain(self):
        """Prepare a domain to check for overlapping budget items."""
        self.ensure_one()
        domain = [
            ("id", "!=", self.id),
            ("budget_id", "=", self.budget_id.id),
            ("date_from", "<=", self.date_to),
            ("date_to", ">=", self.date_from),
        ]
        return domain

    def _check_dates(self):
        for rec in self:
            # date_from <= date_to
            if rec.date_from > rec.date_to:
                raise ValidationError(
                    _("%s start date must not be after end date") % (rec.display_name,)
                )
            # within budget dates
            if rec.date_from < rec.budget_date_from or rec.date_to > rec.budget_date_to:
                raise ValidationError(
                    _(
                        "%(rec_name)s is not within budget %(budget_name)s date range.",
                        rec_name=rec.display_name,
                        budget_name=rec.budget_id.display_name,
                    )
                )
            # overlaps
            domain = rec._prepare_overlap_domain()
            res = self.search(domain, limit=1)
            if res:
                raise ValidationError(
                    _(
                        "%(rec_name)s overlaps %(res_name)s in budget %(budget_name)s",
                        rec_name=rec.display_name,
                        res_name=res.display_name,
                        budget_name=rec.budget_id.display_name,
                    )
                )
