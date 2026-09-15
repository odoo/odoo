from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_description(self):
        if self.purchase_line_id and self.purchase_line_id.order_id.dest_address_id:
            _debug.logic(
                "move_description_from_dropship_address",
                move=self,
                address=self.purchase_line_id.order_id.dest_address_id,
            )
            product = self.product_id.with_context(
                lang=self.purchase_line_id.order_id.dest_address_id.lang
                or self._get_lang()
            )
            return product._get_description(self.picking_type_id)
        return super()._get_description()
