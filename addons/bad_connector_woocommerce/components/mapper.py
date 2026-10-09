import json

from odoo.addons.component.core import AbstractComponent
from odoo.addons.connector.components.mapper import mapping


class WooImporttMapper(AbstractComponent):
    """Base Importer Mapper for woocommerce"""

    _name = "woo.import.mapper"
    _inherit = ["connector.woo.base", "base.import.mapper"]
    _usage = "import.mapper"

    @mapping
    def backend_id(self, record):
        """Return backend."""
        return {"backend_id": self.backend_record.id}

    @mapping
    def woo_data(self, record):
        """Return woo data."""
        return {"woo_data": json.dumps(record, indent=2)}


class WooExportMapper(AbstractComponent):
    """Base Exporter Mapper for woocommerce"""

    _name = "woo.export.mapper"
    _inherit = ["connector.woo.base", "base.export.mapper"]
    _usage = "export.mapper"
