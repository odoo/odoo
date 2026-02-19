import logging

from odoo import _

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.connector.exception import MappingError

# pylint: disable=W7950

_logger = logging.getLogger(__name__)


class WooSettingsBatchImporter(Component):
    """Batch Importer the WooCommerce Settings"""

    _name = "woo.settings.batch.importer"
    _inherit = "woo.delayed.batch.importer"
    _apply_on = "woo.settings"


class WooSettingsImportMapper(Component):
    """Impoter Mapper for the WooCommerce Settings"""

    _name = "woo.settings.import.mapper"
    _inherit = "woo.import.mapper"
    _apply_on = "woo.settings"

    @mapping
    def name(self, record):
        """Mapping for Name"""
        name = record.get("label")
        if not name:
            raise MappingError(_("Settings Name doesn't exist please check !!!"))
        return {"name": name}

    @mapping
    def woo_type(self, record):
        """Mapping for Type"""
        return {"woo_type": record.get("type")} if record.get("type") else {}

    @mapping
    def default(self, record):
        """Mapping for default"""
        return {"default": record.get("default")} if record.get("default") else {}

    @mapping
    def value(self, record):
        """Mapping for value"""
        return {"value": record.get("value")} if record.get("value") else {}


class WooSettingsImporter(Component):
    """Importer the WooCommerce Settings"""

    _name = "woo.settings.importer"
    _inherit = "woo.importer"
    _apply_on = "woo.settings"

    def _after_import(self, binding, **kwargs):
        """Inherit Method: inherit method to import remote child"""
        result = super(WooSettingsImporter, self)._after_import(binding, **kwargs)
        if binding.external_id == "woocommerce_prices_include_tax":
            include_tax = True if binding.value == "yes" else False
            binding.backend_id.write({"include_tax": include_tax})

        if binding.external_id == "woocommerce_manage_stock":
            stock_manage = True if binding.value == "yes" else False
            binding.write({"stock_update": stock_manage})
            binding.backend_id.write({"update_stock_inventory": stock_manage})

        if binding.external_id == "woocommerce_currency":
            currency = self.env["res.currency"].search(
                [("name", "=", binding.value)], limit=1
            )
            if not currency:
                raise MappingError(
                    _(
                        "'%s' currency not found, ensure that currency is active!!!"
                        % binding.value
                    )
                )
            binding.backend_id.write({"currency_id": currency.id})

        if binding.external_id == "woocommerce_weight_unit":
            weight_uom = self.env["uom.uom"].search(
                [("name", "=", binding.value)], limit=1
            )
            binding.backend_id.write({"weight_uom_id": weight_uom.id})

        if binding.external_id == "woocommerce_dimension_unit":
            dimension_uom = self.env["uom.uom"].search(
                [("name", "=", binding.value)], limit=1
            )
            binding.backend_id.write({"dimension_uom_id": dimension_uom.id})
        return result
