import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping

_logger = logging.getLogger(__name__)


class WooProductProductExporterMapper(Component):
    _name = "woo.product.product.export.mapper"
    _inherit = "woo.export.mapper"
    _apply_on = "woo.product.product"

    @mapping
    def stock_quantity(self, record):
        """Mapping for stock_quantity"""
        return {"stock_quantity": record.woo_bind_ids[0].woo_product_qty}

    @mapping
    def template_external_id(self, record):
        """Mapping for template_external_id"""
        tmpl_external = record.product_tmpl_id.woo_bind_ids
        return (
            {"template_external_id": tmpl_external[0].external_id}
            if tmpl_external
            else {}
        )


class ProductInventoryExporter(Component):
    _name = "woo.product.product.exporter"
    _inherit = "woo.exporter"
    _apply_on = ["woo.product.product"]
