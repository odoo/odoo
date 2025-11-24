# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    pickup_delivery_method_id = fields.Many2one(
        "delivery.carrier",
        help="The delivery method that generated this pickup point.",
        ondelete="cascade",
    )

    @api.model
    def _address_from_json(self, json_location_data, parent_id, pickup_delivery_method_id=False):
        """Search for an existing address with the same data as the one in json_location_data
        and the same parent_id. If no address is found, creates a new one.

        :param dict json_location_data: The JSON-formatted pickup location address.
        :param res.partner parent_id: The parent partner of the address to create.
        :param int pickup_delivery_method_id: The id of the related pickup delivery method.
        :return: The existing or newly created address.
        :rtype: res.partner
        """
        if not json_location_data:
            return self
        name = json_location_data.get("name") or parent_id.name
        street = json_location_data["street"]
        city = json_location_data["city"]
        zip_code = json_location_data["zip_code"]
        country_code = json_location_data["country_code"]
        country = self.env["res.country"].search([("code", "=", country_code)]).id
        state = (
            self
            .env["res.country.state"]
            .search([("code", "=", json_location_data["state"]), ("country_id", "=", country)])
            .id
            if (json_location_data.get("state") and country)
            else None
        )
        email = parent_id.email
        phone = parent_id.phone

        domain = [
            ("street", "=", street),
            ("city", "=", city),
            ("state_id", "=", state),
            ("country_id", "=", country),
            ("type", "=", "delivery"),
            ("parent_id", "=", parent_id.id),
            ("pickup_delivery_method_id", "=", pickup_delivery_method_id),
        ]
        existing_partner = self.with_context(active_test=False).search(domain, limit=1)
        if existing_partner:
            # Update partner's data
            existing_partner.write({"email": email, "phone": phone})
            return existing_partner
        return self.create({
            "parent_id": parent_id.id,
            "type": "delivery",
            "name": name,
            "street": street,
            "city": city,
            "state_id": state,
            "zip": zip_code,
            "country_id": country,
            "email": email,
            "phone": phone,
            "pickup_delivery_method_id": pickup_delivery_method_id,
            "pickup_location_data": json_location_data,
            "active": False,
        })
