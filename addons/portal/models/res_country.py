# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ResCountry(models.Model):
    _inherit = "res.country"

    def _get_address_format_fields_mapping(self):
        """Return mapping of `res.country` 'address_format' fields to `res.partner` fields that
        have to be set on the address page.
        """
        fields_mapping = {
            "state_name": "state_id",
            "state_code": "state_id",
            "country_name": "country_id",
        }
        if self._enforce_city_choice():
            fields_mapping["city"] = "city_id"

        return fields_mapping

    def _get_cities_data(self, state_id=False):
        if not self:
            return []

        self.ensure_one()
        domain = [("country_id", "=", self.id)]
        if state_id:
            domain.append(("state_id", "in", [state_id, False]))

        return self.env["res.city"].sudo().search_read(
            domain=domain,
            fields=self._get_cities_fields_to_fetch(),
            load='',  # we only want the ids of relational fields
        )

    @api.model
    def _get_cities_fields_to_fetch(self):
        return ["id", "name", "zipcode", "state_id"]

    def _is_zip_before_city(self, default_address_fields=[]):
        if not self or self.zip_applicability == "not_applicable":
            return False

        address_fields = default_address_fields or self.get_address_fields()
        if not address_fields or "zip" not in address_fields:
            return False

        return address_fields.index("zip") < address_fields.index(
            self._get_partner_city_field()
        )

    def _get_partner_city_field(self):
        """Return city field based on `_enforce_city_choice`."""
        if self._enforce_city_choice():
            return "city_id"
        return "city"

    def _enforce_city_choice(self):
        if not self:
            return False

        # Only enabled on frontend for those countries for now
        # Feature has to be adapted to be more generic and less blocking
        # before being enabled for other countries
        if self.code not in ["BR", "CL", "PE", "CO", "TW"]:
            return False

        self.ensure_one()
        return self.enforce_cities and bool(
            self.env["res.city"].sudo().search_count([("country_id", "=", self.id)], limit=1)
        )
