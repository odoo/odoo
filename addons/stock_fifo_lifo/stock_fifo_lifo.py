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


#@TODO Should not this be product template?
class product_product (osv.osv):
    _name = "product.product"
    _inherit = "product.product"
    _columns = {
        'cost_method': fields.property('', type='selection', view_load=True, selection = [('standard','Standard Price'), ('average','Average Price'), 
                                                                                          ('fifo', 'FIFO price'), ('lifo', 'LIFO price')],
            help="""Standard Price: The cost price is manually updated at the end of a specific period (usually every year).
                Average Price: The cost price is recomputed at each incoming shipment.
                FIFO: When cost is calculated the FIFO way.
                LIFO: When cost is calculated the LIFO way. """, 
            string="Costing Method"),
    }


    def get_stock_matchings_fifolifo(self, cr, uid, ids, qty, fifo, context=None):
        '''
            This method returns a list of tuples for which the stock moves are working fifo/lifo
            This should be called for only one product at a time
            -> might still need to add UoM
        '''
        assert len(ids) == 1, 'Only the fifolifo stock moves of one product can be calculated at a time.'
        product = self.browse(cr, uid, ids, context=context)[0]
        move_obj = self.pool.get('stock.move')

        if fifo:
            move_ids = move_obj.search(cr, uid, [('qty_remaining', '>', 0), ('state', '=', 'done'), 
                                             ('type', '=', 'in'), ('product_id', '=', product.id)], 
                                       order = 'date', context=context)
        else: 
            move_ids = move_obj.search(cr, uid, [('qty_remaining', '>', 0), ('state', '=', 'done'), 
                                             ('type', '=', 'in'), ('product_id', '=', product.id)], 
                                       order = 'date desc', context=context)
        tuples = []
        qty_to_go = qty
        for move in move_obj.browse(cr, uid, move_ids, context=context):
            # @TODO convert UoM for product quantities?
            product_qty = move.product_qty
            if qty_to_go - product_qty >= 0: 
                tuples.append((move.id, product_qty, move.price_unit),)
                qty_to_go -= product_qty
            else:
                tuples.append((move.id, qty_to_go, move.price_unit),)
                qty_to_go = 0
                break
        return tuples

class stock_move(osv.osv):
    _inherit = 'stock.move'
    _columns = {'qty_remaining': fields.float("Remaining"),
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


    #@TODO overwrite method for price_computation
    def price_computation(self, cr, uid, ids, partial_datas, context=None):
        super(stock_move, self).price_computation(cr, uid, ids, partial_datas, context=context)
        product_obj = self.pool.get('product.product')
        matching_obj = self.pool.get('stock.move.matching')
        
        #Find stock moves working in fifo/lifo price -> find stock moves out
        for move in self.browse(cr, uid, ids, context=context):
            product = product_obj.browse(cr, uid, move.product_id.id, context=context)

            #Check we are using the right company
            company_id = move.company_id.id
            ctx = context.copy()
            user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
            if company_id != user.company_id.id:
                ctx['force_company'] = move.company_id.id
                product = product_obj.browse(cr, uid, move.product_id.id, context=ctx)
            cost_method = product.cost_method
            product_price = move.price_unit
            #Still need to see how to handle UoM + check quantity from the partial datas
            product_qty = move.product_qty
            
            if move.picking_id.type == 'out' and cost_method in ['fifo', 'lifo']:
                if not move.move_returned_from:
                    tuples = product_obj.get_stock_matchings_fifolifo(cr, uid, [product.id], product_qty, cost_method == 'fifo', context=context)
                    for match in tuples: 
                        matchvals = {'move_in_id': match[0], 'qty': match[1], 'price_unit': match[2], 
                                     'move_out_id': move.id}
                        match_id = matching_obj.create(cr, uid, matchvals, context=context)
                        move_in = self.browse(cr, uid, match[0], context=context)
                        self.write(cr, uid, match[0], { 'qty_remaining': move_in.qty_remaining - match[1]}, context=context)
                else:
                    #We should find something to do when a stock matching is linked to the returned move already
                    if move.move_returned_from.matching_ids_in:
                        pass
        return True

class stock_move_matching(osv.osv):
    _name = "stock.move.matching"
    _description = "Stock move matchings"
    _columns = {
        'move_in_id': fields.many2one('stock.move', 'Stock move in', required=True),
        'move_out_id': fields.many2one('stock.move', 'Stock move out', required=True),
        'qty': fields.integer('Quantity', required=True), 
        'price_unit':fields.related('move_in_id', 'price_unit', string="Unit price", type="float"),
    }

