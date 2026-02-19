import logging

from odoo import _

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.connector.exception import MappingError

# pylint: disable=W7950

_logger = logging.getLogger(__name__)


class WooResPartnerBatchImporter(Component):
    """Batch Importer for WooCommerce Partners"""

    _name = "woo.res.partner.batch.importer"
    _inherit = "woo.delayed.batch.importer"
    _apply_on = "woo.res.partner"


class WooResPartnerImportMapper(Component):
    """Impoter Mapper for the WooCommerce Partner"""

    _name = "woo.res.partner.import.mapper"
    _inherit = "woo.import.mapper"
    _apply_on = "woo.res.partner"

    @mapping
    def name(self, record):
        """
        Mapping for Name (Set name base on the combination of firstname and lastname
        if firstname or lastname else it will take username)
        """
        first_name = record.get("first_name", "")
        last_name = record.get("last_name", "")
        username = record.get("username", "")
        name = f"{first_name} {last_name}" if first_name or last_name else username
        if not name:
            raise MappingError(_("Username not found!"))
        return {"name": name.strip()}

    @mapping
    def firstname(self, record):
        """Mapping for firstname"""
        return (
            {"firstname": record.get("first_name")} if record.get("first_name") else {}
        )

    @mapping
    def lastname(self, record):
        """Mapping for lastname"""
        return {"lastname": record.get("last_name")} if record.get("last_name") else {}

    @mapping
    def email(self, record):
        """Mapping for Email"""
        email = record.get("email")
        if not email:
            raise MappingError(_("No Email found in Response"))
        return {"email": email}

    def _get_field_value(self, record, field_name):
        """Get the value of a field from a record."""
        billing = record.get("billing")
        shipping = record.get("shipping")
        if any(billing.values()):
            return billing.get(field_name)
        elif any(shipping.values()):
            return shipping.get(field_name)
        return None

    @mapping
    def country_id(self, record):
        """Mapping for country_id"""
        woo_country = self._get_field_value(record, "country")
        if woo_country:
            country = self.env["res.country"].search(
                [("code", "=", woo_country)], limit=1
            )
            return {"country_id": country.id} if country else {}
        return {}

    @mapping
    def state_id(self, record):
        """Mapping for state_id"""
        woo_state = self._get_field_value(record, "state")
        woo_country = self._get_field_value(record, "country")
        if woo_state and woo_country:
            country_record = self.env["res.country"].search(
                [("code", "=", woo_country)], limit=1
            )
            state = self.env["res.country.state"].search(
                [("code", "=", woo_state), ("country_id", "=", country_record.id)],
                limit=1,
            )
            return {"state_id": state.id} if state else {}
        return {}

    @mapping
    def street(self, record):
        """Mapping for street"""
        woo_address = self._get_field_value(record, "address_1")
        return {"street": woo_address} if woo_address else {}

    @mapping
    def street2(self, record):
        """Mapping for street2"""
        woo_address2 = self._get_field_value(record, "address_2")
        return {"street2": woo_address2} if woo_address2 else {}

    @mapping
    def zip(self, record):
        """Mapping for zip"""
        woo_zip = self._get_field_value(record, "zip")
        return {"zip": woo_zip} if woo_zip else {}

    @mapping
    def city(self, record):
        """Mapping for city"""
        woo_city = self._get_field_value(record, "city")
        return {"city": woo_city} if woo_city else {}

    @mapping
    def addresses(self, record):
        """Mapping for Invoice and Shipping Addresses"""
        woo_res_partner = self.env["res.partner"]
        child_data = woo_res_partner.create_get_children(
            record, record.get("id"), self.backend_record
        )
        return (
            {"child_ids": [(0, 0, child_added) for child_added in child_data]}
            if child_data
            else {}
        )


class WooResPartnerImporter(Component):
    """Importer the WooCommerce Partner"""

    _name = "woo.res.partner.importer"
    _inherit = "woo.importer"
    _apply_on = "woo.res.partner"
