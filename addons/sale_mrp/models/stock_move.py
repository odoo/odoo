from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_sale_kit(self):
        order_line = self.sale_line_id
        if len(order_line) != 1 or self.product_id == order_line.product_id:
            return order_line, self.env["mrp.bom"]
        alive = order_line.move_ids.filtered(lambda move: move.state != "cancel")
        if self.product_id != alive.product_id:
            return order_line, self.env["mrp.bom"]
        product = order_line.product_id.with_company(order_line.company_id)
        bom = self.env["mrp.bom"]._get_bom_by_product(
            product, company_id=order_line.company_id.id, bom_type="phantom"
        )[product]
        return order_line, bom

    def _get_sale_line_price_unit(self):
        order_line = self.sale_line_id
        if len(order_line) == 1 and self.product_id != order_line.product_id:
            product = order_line.product_id.with_company(order_line.company_id)
            kit_bom = self.env["mrp.bom"]._get_bom_by_product(
                product, company_id=order_line.company_id.id, bom_type="phantom"
            )[product]
            if kit_bom:
                _debug.logic("sale_line_price_unit", move=self, by="kit_bom")
                return self._get_kit_price_unit(
                    product, kit_bom, order_line.qty_transferred
                )
        return super()._get_sale_line_price_unit()

    def _get_cogs_price_unit(self, quantity=0):
        order_line, kit_bom = self._get_sale_kit()
        if kit_bom:
            _debug.logic("cogs_price_unit", move=self, by="kit_bom", bom=kit_bom)
            return self._get_kit_cogs_price_unit(
                order_line.product_id.with_company(order_line.company_id),
                kit_bom,
                quantity,
            )
        return super()._get_cogs_price_unit(quantity)

    def _get_kit_cogs_price_unit(self, product, kit_bom, quantity):
        component_qty, kit_qty = kit_bom._get_kit_component_qty(product)
        if product.uom_id.is_zero(kit_qty):
            return 0
        total_price = sum(
            super(StockMove, valuated_moves)._get_cogs_price_unit(quantity)
            * component_qty[component]
            for component, valuated_moves in self.grouped("product_id").items()
            if component.is_storable
        )
        return total_price / kit_qty
