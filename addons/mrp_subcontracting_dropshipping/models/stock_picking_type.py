from odoo import models


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    def _is_default_location_suitable(self, location, partner_usage):
        if self.code == "dropship" and partner_usage == "customer":
            if location.is_subcontract():
                return True
        return super()._is_default_location_suitable(location, partner_usage)
