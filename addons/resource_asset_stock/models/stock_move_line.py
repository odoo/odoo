from odoo import models

from odoo.addons.resource_asset.models.resource_asset import SKIP_IDENTITY_CHECK


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def _create_production_lots(self):
        return super(
            StockMoveLine, self.with_context(**{SKIP_IDENTITY_CHECK: True})
        )._create_production_lots()
