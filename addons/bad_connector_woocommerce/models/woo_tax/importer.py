import logging

from odoo import _, api

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create
from odoo.addons.connector.exception import MappingError

# pylint: disable=W7950

_logger = logging.getLogger(__name__)


class WooTaxBatchImporter(Component):
    """Batch Importer for WooCommerce Tax"""

    _name = "woo.tax.batch.importer"
    _inherit = "woo.delayed.batch.importer"
    _apply_on = "woo.tax"


class WooTaxImportMapper(Component):
    """Impoter Mapper for the WooCommerce Tax"""

    _name = "woo.tax.import.mapper"
    _inherit = "woo.import.mapper"
    _apply_on = "woo.tax"

    @api.model
    def get_tax(self, rate):
        """
        Get a tax record based on the given rate,company_id and type_tax_use.
        """
        company = self.backend_record.company_id
        search_conditions = [
            ("amount", "=", rate),
            ("type_tax_use", "in", ["sale", "none"]),
            ("company_id", "=", company.id),
        ]
        tax = self.env["account.tax"].search(search_conditions, limit=1)
        return tax

    @only_create
    @mapping
    def odoo_id(self, record):
        """Mapping for odoo_id"""
        tax = self.get_tax(record.get("rate"))
        if not tax:
            return {}
        return {"odoo_id": tax.id}

    @mapping
    def name(self, record):
        """Mapping for name of tax"""
        name = record.get("name")
        rate_to_float = float(record.get("rate"))
        rate = round(rate_to_float, 2)
        if not name:
            raise MappingError(_("No Tax Name found in Response"))
        return {"name": f"{name} {rate}%"}

    @mapping
    def woo_amount(self, record):
        """Mapping for woo_amount"""
        return {"woo_amount": record.get("rate")} if record.get("rate") else {}

    @mapping
    def woo_rate(self, record):
        """Mapping for woo_rate"""
        return {"woo_rate": record.get("rate")} if record.get("rate") else {}

    @mapping
    def woo_tax_name(self, record):
        """Mapping for woo_tax_name"""
        return {"woo_tax_name": record.get("name")} if record.get("name") else {}

    @mapping
    def priority(self, record):
        """Mapping for priority"""
        return {"priority": record.get("priority")} if record.get("priority") else {}

    @mapping
    def shipping(self, record):
        """Mapping for shipping"""
        return {"shipping": record.get("shipping")} if record.get("shipping") else {}

    @mapping
    def woo_class(self, record):
        """Mapping for woo_class"""
        return {"woo_class": record.get("class")} if record.get("class") else {}

    @mapping
    def compound(self, record):
        """Mapping for compound"""
        return {"compound": record.get("compound")} if record.get("compound") else {}

    @mapping
    def country(self, record):
        """Mapping for country"""
        return {"country": record.get("country")} if record.get("country") else {}

    @mapping
    def state(self, record):
        """Mapping for state"""
        return {"state": record.get("state")} if record.get("state") else {}

    @mapping
    def city(self, record):
        """Mapping for city"""
        return {"city": record.get("city")} if record.get("city") else {}

    @mapping
    def cities(self, record):
        """Mapping for Cities"""
        cities_list = record.get("cities", [])
        cities = [city for city in cities_list]
        return {"cities": ", ".join(cities)} if cities else {}

    @mapping
    def postcodes(self, record):
        """Mapping for postcodes"""
        postcode_list = record.get("postcodes", [])
        postcodes = [postcode for postcode in postcode_list]
        return {"postcodes": ", ".join(postcodes)} if postcodes else {}

    @mapping
    def postcode(self, record):
        """Mapping for postcode"""
        return {"postcode": record.get("postcode")} if record.get("postcode") else {}


class WooTaxImporter(Component):
    """Importer the WooCommerce Tax"""

    _name = "woo.tax.importer"
    _inherit = "woo.importer"
    _apply_on = "woo.tax"
