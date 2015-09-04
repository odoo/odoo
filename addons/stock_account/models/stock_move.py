# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class StockMove(models.Model):
    _inherit = "stock.move"

    @api.multi
    def action_done(self):
        self.product_price_update_before_done()
        res = super(StockMove, self).action_done()
        self.product_price_update_after_done()
        return res

    def _store_average_cost_price(self):
        for move in self:
            if any([q.qty <= 0 for q in move.quant_ids]) or move.product_qty == 0:
                #if there is a negative quant, the standard price shouldn't be updated
                continue
            #Note: here we can't store a quant.cost directly as we may have moved out 2 units (1 unit to 5€ and 1 unit to 7€) and in case of a product return of 1 unit, we can't know which of the 2 costs has to be used (5€ or 7€?). So at that time, thanks to the average valuation price we are storing we will valuate it at 6€
            average_valuation_price = 0.0
            for quant in move.quant_ids:
                average_valuation_price += quant.qty * quant.cost
            average_valuation_price = average_valuation_price / move.product_qty
            # Write the standard price, as SUPERUSER_ID because a warehouse manager may not have the right to write on products
            move.product_id.sudo().with_context(force_company=self.company_id.id).write({'standard_price': average_valuation_price})
            move.price_unit = average_valuation_price

    def product_price_update_before_done(self):
        tmpl_dict = {}
        for move in self.filtered(lambda m: m.location_id.usage == 'supplier' and m.product_id.cost_method == 'average'):
            #adapt standard price on incomming moves if the product cost_method is 'average'
            product = move.product_id
            product_avail = product.qty_available + tmpl_dict.setdefault(product.id, 0)
            if product_avail <= 0:
                new_std_price = move.price_unit
            else:
                # Get the standard price
                amount_unit = product.standard_price
                new_std_price = ((amount_unit * product_avail) + (move.price_unit * move.product_qty)) / (product_avail + move.product_qty)
            tmpl_dict[product.id] += move.product_qty
            # Write the standard price, as SUPERUSER_ID because a warehouse manager may not have the right to write on products
            product.sudo().with_context(force_company=move.company_id.id).write({'standard_price': new_std_price})

    def product_price_update_after_done(self):
        '''
        This method adapts the price on the product when necessary
        '''
        #adapt standard price on outgoing moves if the product cost_method is 'real', so that a return
        #or an inventory loss is made using the last value used for an outgoing valuation.
        #store the average price of the move on the move and product form
        self.filtered(lambda m: m.product_id.cost_method == 'real' and m.location_dest_id.usage != 'internal')._store_average_cost_price()
