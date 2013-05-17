# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import tools
from openerp.osv import osv, fields


#TODO: remove this module and put everything in existing core modules (purchase, stock, product...)
class product_product (osv.osv):
    _name = "product.product"
    _inherit = "product.product"


    def get_stock_matchings_fifolifo(self, cr, uid, ids, qty, fifo, product_uom_id = False, currency_id = False, context=None):
        '''
            This method returns a list of tuples with quantities from stock in moves
            These are the quantities that would go out theoretically according to the fifo or lifo method if qty needs to go out
            (move_in_id, qty in uom of move out, price (converted to move out), qty in uom of move in
            This should be called for only one product at a time
            UoMs and currencies from the corresponding moves are converted towards that given in the params
            It is good to use force_company in the header
        '''
        assert len(ids) == 1, _('Only the fifolifo stock matchings of one product can be calculated at a time.')
        uom_obj = self.pool.get('product.uom')
        currency_obj = self.pool.get('res.currency')
        
        product = self.browse(cr, uid, ids, context=context)[0]
        move_obj = self.pool.get('stock.move')

        if not product_uom_id: 
            product_uom_id = product.uom_id.id
        
        if 'force_company' in context:
            company_id = context['force_company']
        else:
            #Would be better not to have to go here
            company_id = product.company_id.id

        if not currency_id:
            currency_id = self.pool.get('res.company').browse(cr, uid, company_id, context=context).currency_id.id
        if fifo:
            move_in_ids = move_obj.search(cr, uid, [('company_id','=', company_id), ('qty_remaining', '>', 0), ('state', '=', 'done'), 
                                             ('location_id.usage', '!=', 'internal'), ('location_dest_id.usage', '=', 'internal'), ('product_id', '=', product.id)], 
                                       order = 'date', context=context)
        else: 
            move_in_ids = move_obj.search(cr, uid, [('company_id','=', company_id), ('qty_remaining', '>', 0), ('state', '=', 'done'), 
                                             ('location_id.usage', '!=', 'internal'), ('location_dest_id.usage', '=', 'internal'), ('product_id', '=', product.id)], 
                                       order = 'date desc', context=context)

        tuples = []
        qty_to_go = qty
        for move in move_obj.browse(cr, uid, move_in_ids, context=context):
            #Convert to UoM of product each time
            uom_from = move.product_uom.id
            qty_from = move.qty_remaining
            product_qty = uom_obj._compute_qty(cr, uid, uom_from, qty_from, product_uom_id)
            #Convert currency from in move currency id to out move currency
            if move.price_currency_id and (move.price_currency_id.id != currency_id):
                new_price = currency_obj.compute(cr, uid, move.price_currency_id.id, currency_id, 
                                                 move.price_unit, round=False)
            else:
                new_price = move.price_unit
            new_price = uom_obj._compute_price(cr, uid, uom_from, new_price,
                            product_uom_id)
            if qty_to_go - product_qty >= 0: 
                tuples.append((move.id, product_qty, new_price, qty_from),)
                qty_to_go -= product_qty
            else:
                tuples.append((move.id, qty_to_go, new_price, qty_from * qty_to_go / product_qty),)
                break
        return tuples

class stock_move(osv.osv):
    _inherit = 'stock.move'
    _columns = {'qty_remaining': fields.float("Remaining Qty"),
                'matching_ids_in': fields.one2many('stock.move.matching', 'move_in_id'),
                'matching_ids_out':fields.one2many('stock.move.matching', 'move_out_id'),
                }
    
    def create(self, cr, uid, vals, context=None):
        if 'product_qty' in vals:
            vals['qty_remaining'] = vals['product_qty']
        res = super(stock_move, self).create(cr, uid, vals, context=context)
        return res

    def write(self, cr, uid, ids, vals, context=None):
        if 'product_qty' in vals:
            vals['qty_remaining'] = vals['product_qty']
        res = super(stock_move, self).write(cr, uid, ids, vals, context=context)
        return res


class stock_move_matching(osv.osv):
    _name = "stock.move.matching"
    _description = "Stock move matchings"
    _columns = {
        'move_in_id': fields.many2one('stock.move', 'Stock move in', required=True),
        'move_out_id': fields.many2one('stock.move', 'Stock move out', required=True),
        'qty': fields.float('Quantity', required=True), 
        'price_unit':fields.related('move_in_id', 'price_unit', string="Unit price", type="float"),
        'price_unit_out': fields.float('Unit price out') 
    }

