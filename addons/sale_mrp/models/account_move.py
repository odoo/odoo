# -*- coding: utf-8 -*-
from odoo import models


class AccountMoveLine(models.Model):
    # TDE FIXME: what is this code ??
    _inherit = "account.move.line"

    def _stock_account_get_anglo_saxon_price_unit(self):
        price_unit = super(AccountMoveLine, self)._stock_account_get_anglo_saxon_price_unit()
        # in case of anglo saxon with a product configured as invoiced based on delivery, with perpetual
        # valuation and real price costing method, we must find the real price for the cost of good sold
        if self.product_id.invoice_policy == "delivery":
            for s_line in self.sale_line_ids:
                # qtys already invoiced
                qty_done = sum([x.product_uom_id._compute_quantity(x.quantity, x.product_id.uom_id) for x in s_line.invoice_lines if x.move_id.state == 'posted'])
                quantity = self.product_uom_id._compute_quantity(self.quantity, self.product_id.uom_id)
                # Put moves in fixed order by date executed
                moves = s_line.move_ids.sorted(lambda x: x.date)
                # Go through all the moves and do nothing until you get to qty_done
                # Beyond qty_done we need to calculate the average of the price_unit
                # on the moves we encounter.
                bom = s_line.product_id.product_tmpl_id.bom_ids and s_line.product_id.product_tmpl_id.bom_ids[0]
                if bom.type == 'phantom':
                    average_price_unit = 0
                    components = s_line._get_bom_component_qty(bom)
                    for product_id in components:
                        factor = components[product_id]['qty']
                        prod_moves = [m for m in moves if m.product_id.id == product_id]
                        prod_qty_done = factor * qty_done
                        prod_quantity = factor * quantity
                        average_price_unit += factor * self._compute_average_price(prod_qty_done, prod_quantity, prod_moves)
                    price_unit = average_price_unit or price_unit
                    price_unit = self.product_id.uom_id._compute_price(price_unit, self.product_uom_id)
        return price_unit
