import logging

from odoo import _

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create
from odoo.addons.connector.exception import MappingError

_logger = logging.getLogger(__name__)


class WooProductTagBatchImporter(Component):
    """Batch Importer for the WooCommerce Product Tag"""

    _name = "woo.product.tag.batch.importer"
    _inherit = "woo.delayed.batch.importer"
    _apply_on = "woo.product.tag"


class WooProductTagImporter(Component):
    """Importer of WooCommerce Product Tag"""

    _name = "woo.product.tag.importer"
    _inherit = "woo.importer"
    _apply_on = "woo.product.tag"


class WooProductTagImportMapper(Component):
    """Importer Mapper for the WooCommerce Product Tag"""

    _name = "woo.product.tag.import.mapper"
    _inherit = "woo.import.mapper"
    _apply_on = ["woo.product.tag"]

    @only_create
    @mapping
    def odoo_id(self, record):
        """Creating odoo id"""
        tag = record.get("name")
        if not tag:
            raise MappingError(
                _("Tag Name doesn't exist for %s !!!") % record.get("id")
            )
        product_tag = self.env["product.tag"].search([("name", "=", tag)], limit=1)
        if not product_tag:
            return {}
        return {"odoo_id": product_tag.id}

    @mapping
    def name(self, record):
        """Mapping for Name"""
        name = record.get("name")
        if not name:
            raise MappingError(
                _("Tag Name doesn't exist for %s !!!") % record.get("id")
            )
        return {"name": name}

    @mapping
    def slug(self, record):
        """Mapping for Slug"""
        slug = record.get("slug")
        return {"slug": slug} if slug else {}

    @mapping
    def description(self, record):
        """Mapping for Description"""
        description = record.get("description")
        return {"description": description} if description else {}
