# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv
from openerp import SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)


class stock_move(osv.osv):
    _inherit = "stock.move"

    def action_done(self, cr, uid, ids, context=None):
        self.product_price_update_before_done(cr, uid, ids, context=context)
        res = super(stock_move, self).action_done(cr, uid, ids, context=context)
        self.product_price_update_after_done(cr, uid, ids, context=context)
        return res

    def _store_average_cost_price(self, cr, uid, move, context=None):
        ''' move is a browe record '''
        product_obj = self.pool.get('product.product')
        if any([q.qty <= 0 for q in move.quant_ids]) or move.product_qty == 0:
            #if there is a negative quant, the standard price shouldn't be updated
            return
        #Note: here we can't store a quant.cost directly as we may have moved out 2 units (1 unit to 5€ and 1 unit to 7€) and in case of a product return of 1 unit, we can't know which of the 2 costs has to be used (5€ or 7€?). So at that time, thanks to the average valuation price we are storing we will valuate it at 6€
        average_valuation_price = 0.0
        for q in move.quant_ids:
            average_valuation_price += q.qty * q.cost
        average_valuation_price = average_valuation_price / move.product_qty
        # Write the standard price, as SUPERUSER_ID because a warehouse manager may not have the right to write on products
        ctx = dict(context or {}, force_company=move.company_id.id)
        product_obj.write(cr, SUPERUSER_ID, [move.product_id.id], {'standard_price': average_valuation_price}, context=ctx)
        self.write(cr, uid, [move.id], {'price_unit': average_valuation_price}, context=context)

    def product_price_update_before_done(self, cr, uid, ids, context=None):
        product_obj = self.pool.get('product.product')
        tmpl_dict = {}
        for move in self.browse(cr, uid, ids, context=context):
            #adapt standard price on incomming moves if the product cost_method is 'average'
            if (move.location_id.usage == 'supplier') and (move.product_id.cost_method == 'average'):
                product = move.product_id
                product_id = move.product_id.id
                qty_available = move.product_id.qty_available
                if tmpl_dict.get(product_id):
                    product_avail = qty_available + tmpl_dict[product_id]
                else:
                    tmpl_dict[product_id] = 0
                    product_avail = qty_available
                if product_avail <= 0:
                    new_std_price = move.price_unit
                else:
                    # Get the standard price
                    amount_unit = product.standard_price
                    new_std_price = ((amount_unit * product_avail) + (move.price_unit * move.product_qty)) / (product_avail + move.product_qty)
                tmpl_dict[product_id] += move.product_qty
                # Write the standard price, as SUPERUSER_ID because a warehouse manager may not have the right to write on products
                ctx = dict(context or {}, force_company=move.company_id.id)
                product_obj.write(cr, SUPERUSER_ID, [product.id], {'standard_price': new_std_price}, context=ctx)

    def product_price_update_after_done(self, cr, uid, ids, context=None):
        '''
        This method adapts the price on the product when necessary
        '''
        for move in self.browse(cr, uid, ids, context=context):
            #adapt standard price on outgoing moves if the product cost_method is 'real', so that a return
            #or an inventory loss is made using the last value used for an outgoing valuation.
            if move.product_id.cost_method == 'real' and move.location_dest_id.usage != 'internal':
                #store the average price of the move on the move and product form
                self._store_average_cost_price(cr, uid, move, context=context)
