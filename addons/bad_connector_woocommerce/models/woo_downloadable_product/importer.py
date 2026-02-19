import logging

from odoo import _

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.connector.exception import MappingError

_logger = logging.getLogger(__name__)


class WooDownloadableProductImportMapper(Component):
    _name = "woo.downloadable.product.import.mapper"
    _inherit = "woo.import.mapper"
    _apply_on = "woo.downloadable.product"

    direct = [("id", "external_id")]

    @mapping
    def name(self, record):
        """Map name"""
        name = record.get("name")
        if not name:
            raise MappingError(_("File must consist name"))
        return {"name": name}

    @mapping
    def url(self, record):
        """Map file"""
        url = record.get("file")
        return {"url": url} if url else {}
