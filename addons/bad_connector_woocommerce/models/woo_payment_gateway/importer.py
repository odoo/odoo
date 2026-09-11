import logging

from odoo import _

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.connector.exception import MappingError

# pylint: disable=W7950

_logger = logging.getLogger(__name__)


class WooPaymentGatewayBatchImporter(Component):
    """Batch Importer the WooCommerce Payment Gateway"""

    _name = "woo.payment.gateway.batch.importer"
    _inherit = "woo.delayed.batch.importer"
    _apply_on = "woo.payment.gateway"


class WooPaymentGatewqayImportMapper(Component):
    """Impoter Mapper for the WooCommerce Payment Gateway"""

    _name = "woo.payment.gateway.import.mapper"
    _inherit = "woo.import.mapper"
    _apply_on = "woo.payment.gateway"

    @mapping
    def name(self, record):
        """Mapping for Name"""
        title = record.get("title")
        if not title:
            raise MappingError(
                _(
                    "Payment Gateway for '%s' doesn't exist please check !!!"
                    % record.get("id")
                )
            )
        return {"name": title}

    @mapping
    def slug(self, record):
        """Mapping product Slug"""
        description = record.get("description")
        return {"slug": description} if description else {}

    @mapping
    def enable(self, record):
        """Mapping for enable"""
        return {"enable": record.get("enabled", False)}

    @mapping
    def description(self, record):
        """Mapping for Description"""
        method_description = record.get("method_description")
        return {"description": method_description} if method_description else {}


class WooPaymentGatewayImporter(Component):
    """Importer the WooCommerce Payment Gateway"""

    _name = "woo.payment.gateway.importer"
    _inherit = "woo.importer"
    _apply_on = "woo.payment.gateway"
