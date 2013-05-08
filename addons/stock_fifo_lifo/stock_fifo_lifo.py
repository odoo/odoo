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
#TODO: remove this module and put everything in existing core modules (purchase, stock, product...)
class product_product (osv.osv):
    _name = "product.product"
    _inherit = "product.product"
#     _columns = {
#         'cost_method': fields.property('', type='selection', view_load=True, selection = [('standard','Standard Price'), ('average','Average Price'), 
#                                                                                           ('fifo', 'FIFO price'), ('lifo', 'LIFO price')],
#             help="""Standard Price: The cost price is manually updated at the end of a specific period (usually every year).
#                 Average Price: The cost price is recomputed at each incoming shipment.
#                 FIFO: When cost is calculated the FIFO way.
#                 LIFO: When cost is calculated the LIFO way. """, 
#             string="Costing Method"),
#     }


    def get_stock_matchings_fifolifo(self, cr, uid, ids, qty, fifo, product_uom_id = False, currency_id = False, context=None):
        '''
            This method returns a list of tuples with quantities from stock in moves
            These are the quantities that would go out theoretically according to the fifo or lifo method if qty needs to go out
            (move_in_id, qty in uom of move out, price (converted to move out), qty in uom of move in
            This should be called for only one product at a time
            UoMs and currencies from the corresponding moves are converted towards that given in the params
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
                                             ('type', '=', 'in'), ('product_id', '=', product.id)], 
                                       order = 'date', context=context)
        else: 
            move_in_ids = move_obj.search(cr, uid, [('company_id','=', company_id), ('qty_remaining', '>', 0), ('state', '=', 'done'), 
                                             ('type', '=', 'in'), ('product_id', '=', product.id)], 
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


    #Overwrites method for FIFO computation
    def price_computation(self, cr, uid, ids, partial_datas, context=None):
        super(stock_move, self).price_computation(cr, uid, ids, partial_datas, context=context)
        product_obj = self.pool.get('product.product')
        matching_obj = self.pool.get('stock.move.matching')
        currency_obj = self.pool.get('res.currency')
        uom_obj = self.pool.get('product.uom')
        
        #Find stock moves working in fifo/lifo price -> find stock moves out
        for move in self.browse(cr, uid, ids, context=context):
            partial_data = partial_datas.get('move%s'%(move.id), {})
            product_qty = partial_data.get('product_qty',0.0)
            product_uom = partial_data.get('product_uom',False)
            product_price = partial_data.get('product_price',0.0)
            product_currency = partial_data.get('product_currency',False)
            product = product_obj.browse(cr, uid, move.product_id.id, context=context)

            #Check we are using the right company
            company_id = move.company_id.id
            ctx = context.copy()
            user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
            if company_id != user.company_id.id:
                ctx['force_company'] = company_id
                product = product_obj.browse(cr, uid, move.product_id.id, context=ctx)
            cost_method = product.cost_method
            uom_id = product.uom_id.id
            if move.picking_id.type == 'out' and cost_method in ['fifo', 'lifo']:
                #This price has to be put as the new standard price for the product, but needs to be converted to product UoM and currency
                #convert uom of qty

                product_uom_qty = uom_obj._compute_qty(cr, uid, product_uom, product_qty, uom_id)

                #get_stock_matchings will convert to currency and UoM of this stock move
                tuples = product_obj.get_stock_matchings_fifolifo(cr, uid, [product.id], product_qty, cost_method == 'fifo', 
                                                                  product_uom, move.company_id.currency_id.id, context=context) #Always currency of the company
                price_amount = 0.0
                amount = 0.0
                move_currency_id = move.company_id.currency_id.id
                ctx['currency_id'] = move_currency_id
                for match in tuples: 
                    matchvals = {'move_in_id': match[0], 'qty': match[1], 
                                 'move_out_id': move.id, 'price_unit_out': match[2]}
                    match_id = matching_obj.create(cr, uid, matchvals, context=context)
                    move_in = self.browse(cr, uid, match[0], context=context)
                    #Reduce remaining quantity
                    self.write(cr, uid, match[0], { 'qty_remaining': move_in.qty_remaining - match[3]}, context=context)
                    price_amount += match[1] * match[2]
                    amount += match[1]
                if product.qty_available >= product_uom_qty:
                    self.write(cr, uid, move.id, {'price_unit': price_amount / amount}, context=context)
                else:
                    self.write(cr, uid, move.id, {'price_unit': price_amount / amount}, context=context)
                

                #convert price, no need of UoM conversion as it is the total price
                currency_id = move.company_id.currency_id.id
                currency_from = move.price_currency_id
                if move.price_currency_id and (move.price_currency_id.id != currency_id): 
                    new_price = currency_obj.compute(cr, uid, move.price_currency_id, currency_id, 
                                                 price_amount)
                else:
                    new_price = price_amount
                #new_price does not depend on qty as it is the total amount => no conversion needed for uom 
                product_obj.write(cr, uid, product.id, {'standard_price': new_price / product_uom_qty}, context=ctx)
            # When the move is products returned to supplier or return products from customer, 
            # it should be treated as a normal in or out, so for every in
            elif cost_method in ['fifo', 'lifo']:  
                #The currency in the stock move should be the currency of the company
                if product_price > 0.0:
                    if product_currency != move.company_id.currency_id.id:
                        new_price = currency_obj.compute(cr, uid, product_currency, move.company_id.currency_id.id, 
                                                     product_price, round=False)
                    else:
                        new_price = product_price
                else: 
                    if product_uom != uom_id:
                        new_price = uom_obj._compute_price(cr, uid, uom_id, new_price,
                            product_uom)
                    else:
                        new_price = product.standard_price
                self.write(cr, uid, [move.id],
                            {'price_unit': new_price,
                             'price_currency_id': move.company_id.currency_id.id})
        return True

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

