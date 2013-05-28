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


    #Need to change stock moves/product when changing cost method
    def write(self, cr, uid, ids, vals, context=None):
        if "cost_method" in vals:
            move_obj = self.pool.get("stock.move")
            uom_obj = self.pool.get("product.uom")
            prod_obj = self.pool.get("product.product")
            #TODO Need force_company in context?
            if 'force_company' not in context:
                company_id = self.pool.get("res.users").browse(cr, uid, uid, context=context).company_id.id
            else:
                company_id = context['force_company']
            for prod in self.browse(cr, uid, ids, context=context):
                if prod.cost_method == 'average':
                    mov_ids = move_obj.search(cr, uid, [('product_id', '=', prod.id), ('company_id', '=', company_id), ('state', '=', 'done'), ('qty_remaining', '>', 0.0)], context=context)
                    #TODO Need to convert to all prices to UoM of stock move
                    for move in move_obj.browse(cr, uid, mov_ids, context=context):
                        new_price = uom_obj._compute_price(cr, uid, move.product_uom.id, prod.standard_price, prod.uom_id.id)
                        move_obj.write(cr, uid, [move.id], {'price_unit': new_price}, context=context)
                #We need to recalculate the average on all products from all stock moves in
                if vals["cost_method"] == 'average':
                    #Search all done in moves
                    mov_ids = move_obj.search(cr, uid, [('product_id', '=', prod.id), ('company_id', '=', company_id), ('state', '=', 'done'), ('location_dest_id.usage', '=', 'internal'), 
                                                        ('location_id.usage', '!=', 'internal')], context=context)
                    qty = 0.0
                    total_price = 0.0
                    for move in move_obj.browse(cr, uid, mov_ids, context=context):
                        total_price += move.product_qty * move.price_unit
                        qty += uom_obj._compute_qty(cr, uid, move.product_uom.id, move.product_qty, prod.uom_id.id)
                    if qty > 0.0:
                        prod_obj.write(cr, uid, [prod.id], {'standard_price': total_price / qty}, context=context)
        res = super(product_product, self).write(cr, uid, ids, vals, context=context)
        return res
    
    def get_stock_matchings_fifolifo(self, cr, uid, ids, qty, fifo, product_uom_id = False, currency_id = False, context=None):
        '''
            This method returns a list of tuples with quantities from stock in moves
            These are the quantities that would go out theoretically according to the fifo or lifo method if qty needs to go out
            (move_in_id, qty in uom of move out, price (converted to move out), qty in uom of move in
            This should be called for only one product at a time
            UoMs and currencies from the corresponding moves are converted towards that given in the params
            It is good to use force_company in the context
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
            order = 'date, id'
        else: 
            order = 'date desc, id'
        move_in_ids = move_obj.search(cr, uid, [('qty_remaining', '>', 0.0), 
                                                ('state', '=', 'done'), 
                                                ('location_id.usage', '!=', 'internal'), 
                                                ('location_dest_id.usage', '=', 'internal'), 
                                                ('product_id', '=', product.id)], 
                                       order = order, context=context)
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
            new_price = uom_obj._compute_price(cr, uid, uom_from, new_price, product_uom_id)
            if qty_to_go - product_qty >= 0: 
                tuples.append((move.id, product_qty, new_price, qty_from),)
                qty_to_go -= product_qty
            else:
                tuples.append((move.id, qty_to_go, new_price, qty_from * qty_to_go / product_qty),)
                break
        return tuples

class stock_move(osv.osv):
    
    def _get_moves(self, cr, uid, ids, context=None):
        res = []
        #search_dom = ['|', '&', ('location_id.usage','=', 'internal'), ('location_dest_id.usage','!=', 'internal'), '&', ('location_id.usage', '=')]
        #res_ids = self.search(cr, uid, [], context=context)
        for move in self.browse(cr, uid, ids, context=context):
            move_inorout = move.location_id and move.location_dest_id
            move_inorout = move_inorout and ((move.location_id.usage == 'internal' and move.location_dest_id.usage != 'internal') or (move.location_id.usage != 'internal' and move.location_dest_id.usage == 'internal' ))
            if move_inorout:
                res.append(move.id)
        return res


    def _get_moves_from_matchings(self, cr, uid, ids, context=None):
        match_obj = self.pool.get("stock.move.matching")
        res = {}
        for match in match_obj.browse(cr, uid, ids, context=context):
            if match.move_out_id.id not in res:
                res[match.move_out_id.id] = True
            if match.move_in_id.id not in res:
                res[match.move_in_id.id] = True
        return res.keys()

    def _get_qty_remaining (self, cr, uid, ids, field_names, arg, context=None):
        '''
        This function calculates how much of the stock move that still needs to be matched
        '''
        match_obj = self.pool.get("stock.move.matching")
        uom_obj = self.pool.get("product.uom")
        res = {}
        for move in self.browse(cr, uid, ids, context=context):
            move_out = move.location_id.usage == 'internal' and move.location_dest_id.usage != 'internal'
            move_in = move.location_id.usage != 'internal' and move.location_dest_id.usage == 'internal'
            if move_in:
                #Search all matchings
                matches = match_obj.search(cr, uid, [('move_in_id', '=', move.id)], context=context)
                qty = move.product_qty
                for match in match_obj.browse(cr, uid, matches, context=context):
                    qty -= uom_obj._compute_qty(cr, uid, match.move_out_id.product_uom.id, match.qty, move.product_uom.id)
                res[move.id] = qty
            elif move_out:
                #Search all matchings, but from the out side
                matches = match_obj.search(cr, uid, [('move_out_id', '=', move.id)], context=context)
                qty = move.product_qty
                for match in match_obj.browse(cr, uid, matches, context=context):
                    qty -= match.qty
                res[move.id] = qty
        return res
    _inherit = 'stock.move'
    _columns = {'qty_remaining': fields.function(_get_qty_remaining, type="float", string="Remaining quantity to be matched", 
                                                 store = {'stock.move.matching': (_get_moves_from_matchings, ['qty', 'move_in_id', 'move_out_id'], 10),
                                                          'stock.move':  (_get_moves, ['product_qty', 'product_uom', 'location_id', 'location_dest_id', 'company_id'], 10)}), #locations and company_id not necessary?
                'matching_ids_in': fields.one2many('stock.move.matching', 'move_in_id'),
                'matching_ids_out':fields.one2many('stock.move.matching', 'move_out_id'),
                }


class stock_move_matching(osv.osv):
    _name = "stock.move.matching"
    _description = "Stock move matchings"
    
    
    def _get_unit_price_out (self, cr, uid, ids, field_names, arg, context=None):
        res = {}
        uom_obj = self.pool.get("product.uom")
        for match in self.browse(cr, uid, ids, context=context):
            res[match.id] = uom_obj._compute_price(cr, uid, match.move_in_id.product_uom.id, match.price_unit, match.move_out_id.product_uom.id)
        return res

    def _get_matches(self, cr, uid, ids, context=None):
        res = []
        move_obj = self.pool.get("stock.move")
        for move in move_obj.browse(cr, uid, ids, context=context):
            move_in = move.location_id and move.location_dest_id and move.location_id.usage != 'internal' and move.location_dest_id.usage == 'internal'
            if move_in:
                matches = self.pool.get("stock.move.matching").search(cr, uid, [('move_in_id', '=', move.id)], context=context)
                res += matches
        return res

    def _get_selfmatches(self, cr, uid, ids, context=None):
        return ids


    _columns = {
        'move_in_id': fields.many2one('stock.move', 'Stock move in', required=True),
        'move_out_id': fields.many2one('stock.move', 'Stock move out', required=True),
        'qty': fields.float('Quantity in UoM of out', required=True), 
        'price_unit':fields.related('move_in_id', 'price_unit', string="Unit price", type="float"),
        'price_unit_out': fields.function(_get_unit_price_out, type="float", string="Price in UoM of out move", 
                                                 store = {'stock.move':  (_get_matches, ['price_unit', 'product_uom'], 10), 
                                                          'stock.move.matching': (_get_selfmatches, ['move_in_id', 'qty', 'move_out_id'], 10)},), 
    }
    

