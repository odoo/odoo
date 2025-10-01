# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _get_kit_lines_price_ratio(self):
        """ This method returns the ratio of the price of the kit component lines.
        It calculates the price ratio based on either the total list price of the kit or
        based on component quantities if the total price is unavailable. """
        kit_lines = {}
        boms = self.move_id.bom_line_id.bom_id
        for bom in boms:
            total_list_price = sum(bom.bom_line_ids.mapped("product_id.list_price"))
            if total_list_price:
                kit_lines.update({
                    line: (line.product_id.list_price / total_list_price) * (
                        1 / line.product_uom_id._compute_quantity(line.product_qty, line.product_id.uom_id)
                    ) for line in bom.bom_line_ids
                })
            else:
                bom_components_total_qty = sum(bom.bom_line_ids.mapped("product_qty"))
                kit_lines.update({
                    line: (line.product_qty / bom_components_total_qty) * (1 / line.product_qty)
                    for line in bom.bom_line_ids
                })
        return kit_lines

    def _compute_sale_price(self):
        kit_lines = self.filtered(lambda move_line: move_line.move_id.bom_line_id.bom_id.type == 'phantom')
        if kit_lines:
            sale_orders = kit_lines.picking_id.sale_id
            line_global_discounts = sale_orders._get_line_global_discount()
            kit_line_price_ratio = kit_lines._get_kit_lines_price_ratio()
            for move_line in kit_lines:
                sale_line = move_line.move_id.sale_line_id
                discount = line_global_discounts.get(sale_line.id, 0)
                sale_unit_price = sale_line.price_reduce_taxinc - discount
                unit_price = sale_unit_price * kit_line_price_ratio[move_line.move_id.bom_line_id]
                qty = move_line.product_uom_id._compute_quantity(move_line.quantity, move_line.product_id.uom_id)
                move_line.sale_price = unit_price * qty
        super(StockMoveLine, self - kit_lines)._compute_sale_price()
