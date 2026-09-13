from odoo import api, fields, models


class ResCountry(models.Model):
    _inherit = "res.country"

    has_foreign_fiscal_position = fields.Boolean(
        compute="_compute_has_foreign_fiscal_position"
    )  # Caching technical field

    @api.depends_context("company")
    def _compute_has_foreign_fiscal_position(self):
        countries_with_foreign_vat = {
            country
            for [country] in self.env["account.fiscal.position"]._read_group(
                [
                    *self._check_company_domain(self.env.company),
                    ("foreign_vat", "!=", False),
                    ("country_id", "in", self.ids),
                ],
                ["country_id"],
            )
        }
        for country in self:
            country.has_foreign_fiscal_position = country in countries_with_foreign_vat
