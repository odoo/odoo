import logging

from odoo import _

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.connector.exception import MappingError

# pylint: disable=W7950

_logger = logging.getLogger(__name__)


class WooProductAttributeBatchImporter(Component):
    """Batch Importer the WooCommerce Product Attribute"""

    _name = "woo.product.attribute.batch.importer"
    _inherit = "woo.delayed.batch.importer"
    _apply_on = "woo.product.attribute"


class WooProductAttributeImportMapper(Component):
    """Impoter Mapper for the WooCommerce Product Attribute"""

    _name = "woo.product.attribute.import.mapper"
    _inherit = "woo.import.mapper"
    _apply_on = "woo.product.attribute"

    @mapping
    def name(self, record):
        """Mapping for Name"""
        name = record.get("name")
        if not name:
            raise MappingError(_("Attribute Name doesn't exist please check !!!"))
        return {"name": name}

    @mapping
    def has_archives(self, record):
        """Mapping product Has Archives"""
        return {"has_archives": record.get("has_archives")}


class WooProductAttributeImporter(Component):
    """Importer the WooCommerce Product"""

    _name = "woo.product.attribute.importer"
    _inherit = "woo.importer"
    _apply_on = "woo.product.attribute"

    def _after_import(self, binding, **kwargs):
        """Inherit Method: inherit method to import remote child"""
        # TODO: Pass context for delay
        binding.sync_attribute_values_from_woo()
        return super(WooProductAttributeImporter, self)._after_import(binding, **kwargs)

    def _must_skip(self, **kwargs):
        """Skipped Records which have not_real set to be True."""
        binding = self._get_binding()
        if binding and binding.not_real:
            return _("This Attribute is exclusively assigned to a specific product.")
        return super(WooProductAttributeImporter, self)._must_skip(**kwargs)
