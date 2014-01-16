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

from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp


class mrp_product_produce_line(osv.osv_memory):
    _name="mrp.product.produce.line"
    _description = "Product Produce Consume lines"

    _columns = {
        'product_id': fields.many2one('product.product', 'Product'), 
        'product_qty': fields.float('Quantity'), 
        'lot_id': fields.many2one('stock.production.lot', 'Lot'), 
        'produce_id': fields.many2one('mrp.product.produce')
        }

class mrp_product_produce(osv.osv_memory):
    _name = "mrp.product.produce"
    _description = "Product Produce"

    _columns = {
        'product_qty': fields.float('Select Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'mode': fields.selection([('consume_produce', 'Consume & Produce'),
                                  ('consume', 'Consume Only')], 'Mode', required=True,
                                  help="'Consume only' mode will only consume the products with the quantity selected.\n"
                                        "'Consume & Produce' mode will consume as well as produce the products with the quantity selected "
                                        "and it will finish the production order when total ordered quantities are produced."),
        'lot_id': fields.many2one('stock.production.lot', 'Lot'), #Should only be visible when it is consume and produce mode
        'consume_lines': fields.one2many('mrp.product.produce.line', 'produce_id', 'Products Consumed'),
    }
    
    
    def on_change_qty(self, cr, uid, ids, product_qty, consume_lines, context=None):
        """ Will calculate number of products based on 
        """
        prod_obj = self.pool.get("mrp.production")
        production = prod_obj.browse(cr, uid, context['active_id'], context=context)
        
        produced_qty = 0
        for produced_product in production.move_created_ids2:
            if (produced_product.scrapped) or (produced_product.product_id.id != production.product_id.id):
                continue
            produced_qty += produced_product.product_qty
        
        
        #Calculate consume lines
        consumed_data = {}
        for consumed in production.move_lines2:
            if consumed.scrapped:
                continue
            if not consumed_data.get(consumed.product_id.id, False):
                consumed_data[consumed.product_id.id] = 0
            consumed_data[consumed.product_id.id] += consumed.product_qty
        
        print "Consumed data", consumed_data

        new_consume_lines = []
        
        # Find product qty to be consumed and consume it
        for scheduled in production.product_lines:

            # total qty of consumed product we need after this consumption
            total_consume = ((product_qty + produced_qty) * scheduled.product_qty / production.product_qty)

            # qty available for consume and produce
            qty_avail = scheduled.product_qty - consumed_data.get(scheduled.product_id.id, 0.0)

            if qty_avail <= 0.0:
                # there will be nothing to consume for this raw material
                continue

            qty = total_consume - consumed_data.get(scheduled.product_id.id, 0.0)
            dict_new = {'product_id': scheduled.product_id.id, 'product_qty': qty}
            new_consume_lines.append([0, False, dict_new])
        
        return {'value': {'consume_lines': new_consume_lines}}


    def _get_product_qty(self, cr, uid, context=None):
        """ To obtain product quantity
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param context: A standard dictionary
        @return: Quantity
        """
        if context is None:
            context = {}
        prod = self.pool.get('mrp.production').browse(cr, uid,
                                context['active_id'], context=context)
        done = 0.0
        for move in prod.move_created_ids2:
            if move.product_id == prod.product_id:
                if not move.scrapped:
                    done += move.product_qty
        return (prod.product_qty - done) or prod.product_qty

    _defaults = {
         'product_qty': _get_product_qty,
         'mode': lambda *x: 'consume_produce'
    }

    def do_produce(self, cr, uid, ids, context=None):
        production_id = context.get('active_id', False)
        assert production_id, "Production Id should be specified in context as a Active ID."
        data = self.browse(cr, uid, ids[0], context=context)
        self.pool.get('mrp.production').action_produce(cr, uid, production_id,
                            data.product_qty, data.mode, data, context=context)
        return {}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
