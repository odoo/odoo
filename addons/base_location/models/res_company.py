# Copyright 2016 Nicolas Bessi, Camptocamp SA
# Copyright 2018 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    # In order to keep the same logic used in Odoo, fields must be computed
    # and inversed, not related. This way we can ensure that it works
    # correctly on changes and that inconsistencies cannot happen.
    # When you make the fields related, the constrains added in res.partner
    # will fail, because when you change the city_id in the company, you are
    # effectively changing it in the partner. The constrains on the partner
    # are evaluated before the inverse methods update the other fields (city,
    # etc..) so we need them to ensure consistency.
    # As a conclusion, address fields are very related to each other.
    # Either you make them all related to the partner in company, or you
    # don't for all of them. Mixing both approaches produces inconsistencies.

    city_id = fields.Many2one(
        "res.city",
        compute="_compute_address",
        inverse="_inverse_city_id",
        string="City ID",
    )
    zip_id = fields.Many2one(
        "res.city.zip",
        string="ZIP Location",
        compute="_compute_address",
        inverse="_inverse_zip_id",
        help="Use the city name or the zip code to search the location",
    )
    country_enforce_cities = fields.Boolean(
        related="partner_id.country_id.enforce_cities"
    )

    def _get_company_address_field_names(self):
        """Add to the list of field to populate in _compute_address the new
        ZIP field + the city that is not handled at company level in
        `base_address_extended`.
        """
        res = super()._get_company_address_field_names()
        res += ["city_id", "zip_id"]
        return res

    def _inverse_city_id(self):
        for company in self.with_context(skip_check_zip=True):
            company.partner_id.city_id = company.city_id

    def _inverse_zip_id(self):
        for company in self.with_context(skip_check_zip=True):
            company.partner_id.zip_id = company.zip_id

    def _inverse_state(self):
        self = self.with_context(skip_check_zip=True)
        return super(ResCompany, self)._inverse_state()

    def _inverse_country(self):
        self = self.with_context(skip_check_zip=True)
        return super(ResCompany, self)._inverse_country()

    @api.onchange("zip_id")
    def _onchange_zip_id(self):
        if self.zip_id:
            self.update(
                {
                    "zip": self.zip_id.name,
                    "city_id": self.zip_id.city_id,
                    "city": self.zip_id.city_id.name,
                    "country_id": self.zip_id.city_id.country_id,
                    "state_id": self.zip_id.city_id.state_id,
                }
            )

    @api.onchange("state_id")
    def _onchange_state_id(self):
        if self.state_id.country_id:
            self.country_id = self.state_id.country_id.id
