# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, _
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp


class mrp_product_produce_line(osv.osv_memory):
    _name="mrp.product.produce.line"
    _description = "Product Produce Consume lines"

    _columns = {
        'product_id': fields.many2one('product.product', string='Product'),
        'product_qty': fields.float('Quantity (in default UoM)', digits_compute=dp.get_precision('Product Unit of Measure')),
        'lot_id': fields.many2one('stock.production.lot', string='Lot'),
        'produce_id': fields.many2one('mrp.product.produce', string="Produce"),
    }

class mrp_product_produce(osv.osv_memory):
    _name = "mrp.product.produce"
    _description = "Product Produce"

    _columns = {
        'product_id': fields.many2one('product.product', type='many2one'),
        'product_qty': fields.float('Select Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'mode': fields.selection([('consume_produce', 'Consume & Produce'),
                                  ('consume', 'Consume Only')], 'Mode', required=True,
                                  help="'Consume only' mode will only consume the products with the quantity selected.\n"
                                        "'Consume & Produce' mode will consume as well as produce the products with the quantity selected "
                                        "and it will finish the production order when total ordered quantities are produced."),
        'lot_id': fields.many2one('stock.production.lot', 'Lot'), #Should only be visible when it is consume and produce mode
        'consume_lines': fields.one2many('mrp.product.produce.line', 'produce_id', 'Products Consumed'),
        'tracking': fields.related('product_id', 'tracking', type='selection',
                                   selection=[('serial', 'By Unique Serial Number'), ('lot', 'By Lots'), ('none', 'No Tracking')]),
    }

    def on_change_qty(self, cr, uid, ids, product_qty, consume_lines, context=None):
        """ 
            When changing the quantity of products to be produced it will 
            recalculate the number of raw materials needed according
            to the scheduled products and the already consumed/produced products
            It will return the consume lines needed for the products to be produced
            which the user can still adapt
        """
        prod_obj = self.pool.get("mrp.production")
        uom_obj = self.pool.get("product.uom")
        production = prod_obj.browse(cr, uid, context['active_id'], context=context)
        consume_lines = []
        new_consume_lines = []
        if product_qty > 0.0:
            product_uom_qty = uom_obj._compute_qty(cr, uid, production.product_uom.id, product_qty, production.product_id.uom_id.id)
            consume_lines = prod_obj._calculate_qty(cr, uid, production, product_qty=product_uom_qty, context=context)
        
        for consume in consume_lines:
            new_consume_lines.append([0, False, consume])
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
                    done += move.product_uom_qty # As uom of produced products and production order should correspond
        return prod.product_qty - done

    def _get_product_id(self, cr, uid, context=None):
        """ To obtain product id
        @return: id
        """
        prod=False
        if context and context.get("active_id"):
            prod = self.pool.get('mrp.production').browse(cr, uid,
                                    context['active_id'], context=context)
        return prod and prod.product_id.id or False
    
    def _get_track(self, cr, uid, context=None):
        prod = self._get_product_id(cr, uid, context=context)
        prod_obj = self.pool.get("product.product")
        return prod and prod_obj.browse(cr, uid, prod, context=context).tracking or 'none'

    _defaults = {
         'product_qty': _get_product_qty,
         'mode': lambda *x: 'consume_produce',
         'product_id': _get_product_id,
         'tracking': _get_track,
    }

    def do_produce(self, cr, uid, ids, context=None):
        production_id = context.get('active_id', False)
        assert production_id, "Production Id should be specified in context as a Active ID."
        data = self.browse(cr, uid, ids[0], context=context)
        self.pool.get('mrp.production').action_produce(cr, uid, production_id,
                            data.product_qty, data.mode, data, context=context)
        return {}

    @api.onchange('consume_lines')
    def _onchange_consume_lines(self):
        '''
        The purpose of the method is to warn the user if we plan to consume more than one unit of
        a product with unique serial number.
        '''
        for product in self.consume_lines.mapped('product_id'):
            if product.tracking != 'serial':
                continue

            qty_by_lot = {}
            lines = self.consume_lines.filtered(lambda r: r.product_id == product)
            for line in lines:
                qty_by_lot.setdefault(line.lot_id, 0.0)
                qty_by_lot[line.lot_id] += line.product_qty

                if qty_by_lot[line.lot_id] > 1.0:
                    warning_mess = {
                        'title': _('Issue with lot quantity!'),
                        'message' : _('You plan to consume more than 1.00 unit of product %s with unique lot number %s') % \
                            (product.name, line.lot_id.name)
                    }
                    return {'warning': warning_mess}
