import logging

from odoo import _

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.connector.exception import MappingError

_logger = logging.getLogger(__name__)


class WooDeliveryCarrierBatchImporter(Component):
    """Batch Importer the WooCommerce Delivery Method"""

    _name = "woo.delivery.carrier.batch.importer"
    _inherit = "woo.delayed.batch.importer"
    _apply_on = "woo.delivery.carrier"


class WooDeliveryCarrierImporter(Component):
    """Importer of WooCommerce Delivery Method"""

    _name = "woo.delivery.carrier.importer"
    _inherit = "woo.importer"
    _apply_on = "woo.delivery.carrier"


class WooDeliveryCarrierImportMapper(Component):
    """Importer Mapper for the WooCommerce Delivery carrier"""

    _name = "woo.delivery.carrier.import.mapper"
    _inherit = "woo.import.mapper"
    _apply_on = "woo.delivery.carrier"

    direct = [
        ("id", "external_id"),
        ("title", "name"),
        ("description", "description"),
    ]

    @mapping
    def product_id(self, record):
        product_id = self.backend_record.default_carrier_product_id
        if not product_id:
            raise MappingError(
                _("The default carrier product must be set on the backend")
            )
        return {"product_id": product_id.id}
