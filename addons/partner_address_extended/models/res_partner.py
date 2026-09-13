from odoo import api, fields, models, tools


class ResPartner(models.Model):
    _inherit = "res.partner"

    street_name = fields.Char(
        compute="_compute_street_data",
        inverse="_inverse_street_data",
        store=True,
    )
    street_number = fields.Char(
        string="House",
        compute="_compute_street_data",
        inverse="_inverse_street_data",
        store=True,
    )
    street_number2 = fields.Char(
        string="Door",
        compute="_compute_street_data",
        inverse="_inverse_street_data",
        store=True,
    )

    city_id = fields.Many2one(
        comodel_name="res.city",
        string="City ID",
    )
    country_enforce_cities = fields.Boolean(related="country_id.enforce_cities")

    @api.model
    def _address_fields(self):
        return super()._address_fields() + ["city_id"]

    def _inverse_street_data(self):
        """update self.street based on street_name, street_number and street_number2"""
        for partner in self:
            street = " ".join(
                part for part in (partner.street_name, partner.street_number) if part
            )
            if partner.street_number2:
                street = (
                    f"{street} - {partner.street_number2}"
                    if street
                    else partner.street_number2
                )
            partner.street = street

    @api.depends("street")
    def _compute_street_data(self):
        """Split the street value into its sub-fields when `street` changes."""
        for partner in self:
            partner.update(tools.street_split(partner.street))

    def _get_street_split(self):
        self.check_singleton()
        return {
            "street_name": self.street_name,
            "street_number": self.street_number,
            "street_number2": self.street_number2,
        }

    @api.onchange("city_id")
    def _onchange_city_id(self):
        if self.city_id:
            self.city = self.city_id.name
            self.zip = self.city_id.zipcode
            self.state_id = self.city_id.state_id
        else:
            self.city = False
            self.zip = False
            self.state_id = False

    @api.onchange("country_id")
    def _onchange_country_id(self):
        super()._onchange_country_id()
        if self.country_id and self.country_id != self.city_id.country_id:
            self.city_id = False
            self.city = False
            self.zip = False
            self.state_id = False
