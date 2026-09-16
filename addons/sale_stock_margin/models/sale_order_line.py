from odoo import api, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.depends("move_ids", "move_ids.value", "move_ids.picking_id.state")
    def _compute_purchase_price(self):
        line_ids_to_pass = set()
        for line in self:
            product = line.product_id.with_company(line.company_id)
            if not line.has_valued_move_ids():
                line_ids_to_pass.add(line.id)
            elif (
                line.product_id
                and line.product_id.categ_id
                and line.product_id.categ_id.property_cost_method != "standard"
            ):
                qty_from_delivery = line.qty_transferred
                price_unit_from_delivery = (
                    line.move_ids.filtered(
                        lambda m: m.state == "done"
                    )._get_sale_line_price_unit()
                    if qty_from_delivery > 0
                    else 0
                )
                if qty_from_delivery <= 0:
                    purch_price = product.standard_price
                else:
                    qty_from_std_price = max(line.product_qty - qty_from_delivery, 0)
                    purch_price = (
                        qty_from_delivery * price_unit_from_delivery
                        + qty_from_std_price * product.standard_price
                    ) / (qty_from_delivery + qty_from_std_price)
                purch_price_uom = line.product_id.uom_id._get_price_in_unit(
                    purch_price, line.product_uom_id
                )
                _debug.logic(
                    "line_cost",
                    line=line,
                    by="weighted_delivery_and_standard",
                    delivered=qty_from_delivery,
                    cost=purch_price,
                )
                line.purchase_price = line._convert_to_sol_currency(
                    purch_price_uom,
                    product.cost_currency_id,
                )
            elif not line.product_qty and line.qty_transferred:
                line_ids_to_pass.add(line.id)
        return super(
            SaleOrderLine, self.browse(line_ids_to_pass)
        )._compute_purchase_price()
