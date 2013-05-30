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


#TODO: remove this FILE and put everything in existing core modules (purchase, stock, product...)
class product_product (osv.osv):
    _name = "product.product"
    _inherit = "product.product"

    def _compute_and_set_avg_price(self, cr, uid, prod, company_id, context=None):
        """
        This method is called when we modify the cost method of a product 'prod' from something to 'average'. At that time, we
        will compute and set the current average price on the product.

        :param prod: browse_record(product.product)
        :param company_id: ID of the company to consider
        """
        move_obj = self.pool.get("stock.move")
        uom_obj = self.pool.get("product.uom")
        qty = 0.0
        total_price = 0.0
        #search all outgoing stock moves and count the total cost and total quantity
        mov_ids = move_obj.search(cr, uid, [('product_id', '=', prod.id), ('company_id', '=', company_id), ('state', '=', 'done'), ('location_dest_id.usage', '=', 'internal'), ('location_id.usage', '!=', 'internal')], context=context)
        for move in move_obj.browse(cr, uid, mov_ids, context=context):
            total_price += move.product_qty * move.price_unit
            qty += uom_obj._compute_qty(cr, uid, move.product_uom.id, move.product_qty, prod.uom_id.id, round=False)
        if qty > 0.0:
            self.write(cr, uid, [prod.id], {'standard_price': total_price / qty}, context=context)

    def _update_moves_set_avg_price(self, cr, uid, prod, company_id, context=None):
        """
        This method is called when we modify the cost method of a product 'prod' from average to something else. At that time, we
        will set the current average price on all the stock moves with a positive remaining quantity.

        :param prod: browse_record(product.product)
        :param company_id: ID of the company to consider
        """
        move_obj = self.pool.get("stock.move")
        uom_obj = self.pool.get("product.uom")
        mov_ids = move_obj.search(cr, uid, [('product_id', '=', prod.id), ('company_id', '=', company_id), ('state', '=', 'done'), ('qty_remaining', '>', 0.0)], context=context)
        for move in move_obj.browse(cr, uid, mov_ids, context=context):
            #convert the average price of the product into the stock move uom
            new_price = uom_obj._compute_price(cr, uid, move.product_uom.id, prod.standard_price, prod.uom_id.id)
            move_obj.write(cr, uid, [move.id], {'price_unit': new_price}, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        #If we changed the cost method of the product, we may need to do some operation on stock moves or on the product itself
        if "cost_method" in vals:
            company_id = context.get('force_company', self.pool.get("res.users").browse(cr, uid, uid, context=context).company_id.id)
            for prod in self.browse(cr, uid, ids, context=context):
                if prod.cost_method == 'average' and vals['cost_method'] != 'average':
                    #If we are changing the cost_method from 'average' to something else, we need to store the current average price
                    #on all the done stock move that have a remaining quantity to be matched (mostly incomming stock moves but it may
                    #include OUT stock moves as well if the stock went into negative) because their further valuation needs to be done
                    #using this price.
                    self._update_moves_set_avg_price(cr, uid, prod, company_id, context=context)
                elif vals["cost_method"] == 'average' and prod.cost_method != 'average':
                    #If we are changing the cost_method from anything to 'average', we need to compute the current average price 
                    #and set it on the product as standard_price.
                    self._compute_and_set_avg_price(cr, uid, prod, company_id, context=context)
        return super(product_product, self).write(cr, uid, ids, vals, context=context)
    
    def get_stock_matchings_fifolifo(self, cr, uid, ids, qty, fifo, product_uom_id=False, currency_id=False, context=None):
        #TODO: document the parameters (what is fifo? what's its type and is it used for?)...
        #TODO: check if possible to refactore and to split this big method into several smaller
        '''
        This method returns a list of tuples with quantities from stock in moves
        These are the quantities that would go out theoretically according to the fifo or lifo method if qty needs to go out
        (move_in_id, qty in uom of move out, price (converted to move out), qty in uom of move in
        This should be called for only one product at a time
        UoMs and currencies from the corresponding moves are converted towards that given in the params
        It is good to use force_company in the context
        '''
        assert len(ids) == 1, 'Only the fifolifo stock matchings of one product can be calculated at a time.'
        if context is None:
            context = {}
        uom_obj = self.pool.get('product.uom')
        move_obj = self.pool.get('stock.move')
        currency_obj = self.pool.get('res.currency')
        
        product = self.browse(cr, uid, ids, context=context)[0]
        if not product_uom_id: 
            product_uom_id = product.uom_id.id
        company_id = context.get('force_company', product.company_id.id)

        if not currency_id:
            currency_id = self.pool.get('res.company').browse(cr, uid, company_id, context=context).currency_id.id
        if fifo:
            order = 'date, id'
        else: 
            order = 'date desc, id desc' #id also for yml tests
        move_in_ids = move_obj.search(cr, uid, [('company_id', '=', company_id), 
                                                ('qty_remaining', '>', 0.0), 
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
            product_qty = uom_obj._compute_qty(cr, uid, uom_from, qty_from, product_uom_id, round=False)
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
    _inherit = 'stock.move'
    
    def _get_moves_from_matchings(self, cr, uid, ids, context=None):
        #TOCHECK: self == match_obj ?
        match_obj = self.pool.get("stock.move.matching")
        res = set()
        for match in match_obj.browse(cr, uid, ids, context=context):
            res.add(match.move_out_id.id)
            res.add(match.move_in_id.id)
        return list(res)

    def _get_qty_remaining (self, cr, uid, ids, field_names, arg, context=None):
        '''
        This function calculates how much of the stock move that still needs to be matched
        '''
        match_obj = self.pool.get("stock.move.matching")
        uom_obj = self.pool.get("product.uom")
        res = {}
        for move in self.browse(cr, uid, ids, context=context):
            qty = move.product_qty
            if move.location_id.usage != 'internal' and move.location_dest_id.usage == 'internal':
                # for incomming moves, the remaining quantity is the quantity what hasn't been matched yet with outgoing moves
                matches = match_obj.search(cr, uid, [('move_in_id', '=', move.id)], context=context)
                for match in match_obj.browse(cr, uid, matches, context=context):
                    qty -= uom_obj._compute_qty(cr, uid, match.move_out_id.product_uom.id, match.qty, move.product_uom.id, round=False)
            elif move.location_id.usage == 'internal' and move.location_dest_id.usage != 'internal':
                # for outgoing moves, we need to compute the remaining quantity to manage the negative stocks.
                # We do that in the same way that for incomming moves.
                matches = match_obj.search(cr, uid, [('move_out_id', '=', move.id)], context=context)
                for match in match_obj.browse(cr, uid, matches, context=context):
                    # we don't need to call uom_obj.compute() as the qty on the matching is already in the uom of the out move
                    qty -= match.qty
            else:
                # we don't use remaining quantity on internal moves (no matching are created)
                qty = 0
            res[move.id] = qty
        return res

    _columns = {'qty_remaining': fields.function(_get_qty_remaining, type="float", string="Remaining quantity to be matched", 
                                                 store = {'stock.move.matching': (_get_moves_from_matchings, ['qty', 'move_in_id', 'move_out_id'], 10),
                                                          'stock.move':  (lambda self, cr, uid, ids, ctx: ids, ['product_qty', 'product_uom', 'location_id', 'location_dest_id'], 10)}),
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
        move_in_ids = []
        #TOCHECK : self == move_obj i think
        move_obj = self.pool.get("stock.move")
        for move in move_obj.browse(cr, uid, ids, context=context):
            if move.location_id.usage != 'internal' and move.location_dest_id.usage == 'internal':
                move_in_ids.append(move.id)
        return self.pool.get("stock.move.matching").search(cr, uid, [('move_in_id', 'in', move_in_ids)], context=context)

    _columns = {
        'move_in_id': fields.many2one('stock.move', 'Stock move in', required=True),
        'move_out_id': fields.many2one('stock.move', 'Stock move out', required=True),
        'qty': fields.float('Quantity in UoM of out', required=True), 
        'price_unit':fields.related('move_in_id', 'price_unit', string="Unit price", type="float"),
        'price_unit_out': fields.function(_get_unit_price_out, type="float", string="Price in UoM of out move", 
                                                 store = {'stock.move': (_get_matches, ['price_unit', 'product_uom'], 10), 
                                                          'stock.move.matching': (lambda self, cr, uid, ids, ctx: ids, ['move_in_id', 'qty', 'move_out_id'], 10)},), 
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
