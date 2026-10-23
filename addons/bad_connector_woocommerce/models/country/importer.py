from odoo import _

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create
from odoo.addons.connector.exception import MappingError

# pylint: disable=W7950


class WooResCountryBatchImporter(Component):
    """Batch Importer for WooCommerce Country"""

    _name = "woo.res.country.batch.importer"
    _inherit = "woo.delayed.batch.importer"
    _apply_on = "woo.res.country"


class WooResCountryImportMapper(Component):
    """Impoter Mapper for the WooCommerce Country"""

    _name = "woo.res.country.import.mapper"
    _inherit = "woo.import.mapper"
    _apply_on = "woo.res.country"

    direct = [("code", "external_id")]

    def get_country(self, country_code):
        """Retrieve the country record based on the country code."""
        country = self.env["res.country"].search([("code", "=", country_code)], limit=1)
        return country

    @only_create
    @mapping
    def odoo_id(self, record):
        """Creating odoo id"""
        country = self.get_country(record.get("code"))
        if not country:
            return {}
        return {"odoo_id": country.id}

    @mapping
    def name(self, record):
        """Mapping for Name"""
        country_name = record.get("name")
        if self.get_country(record.get("code")):
            return {}
        if not country_name:
            raise MappingError(_("Country Name not found!"))
        return {"name": country_name}

    @mapping
    def code(self, record):
        """Mapping for Code"""
        country_code = record.get("code")
        if self.get_country(country_code):
            return {}
        return {"code": country_code} if country_code else {}

    @mapping
    def state_ids(self, record):
        """Mapper for state_ids"""
        state_ids = []
        states = record.get("states", [])
        if not states:
            return {}
        country_code = record.get("code")
        country_record = self.env["res.country"].search(
            [("code", "=", country_code)], limit=1
        )
        for state in states:
            state_code = state.get("code")
            state_record = self.env["res.country.state"].search(
                [
                    ("code", "=", state_code),
                    ("country_id.code", "=", country_code),
                ],
                limit=1,
            )
            if not state_record:
                state_vals = {
                    "name": state.get("name"),
                    "code": state_code,
                    "country_id": country_record.id,
                }
                state_record = self.env["res.country.state"].create(state_vals)
            state_ids.append((4, state_record.id, 0))
        return {"state_ids": state_ids} if state_ids else {}


class WooResCountryImporter(Component):
    """Importer the WooCommerce Country"""

    _name = "woo.res.country.importer"
    _inherit = "woo.importer"
    _apply_on = "woo.res.country"
