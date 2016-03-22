# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp



class stock_move_scrap(osv.osv_memory):
    _name = "stock.move.scrap"
    _description = "Scrap Products"

    _columns = {
        'product_id': fields.many2one('product.product', 'Product', required=True, select=True),
        'product_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True),
        'location_id': fields.many2one('stock.location', 'Location', required=True),
        'restrict_lot_id': fields.many2one('stock.production.lot', 'Lot'),
    }

    _defaults = {
        'location_id': lambda *x: False
    }

    def default_get(self, cr, uid, fields, context=None):
        """ Get default values
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param fields: List of fields for default value
        @param context: A standard dictionary
        @return: default values of fields
        """
        if context is None:
            context = {}
        res = super(stock_move_scrap, self).default_get(cr, uid, fields, context=context)
        move = self.pool.get('stock.move').browse(cr, uid, context['active_id'], context=context)

        location_obj = self.pool.get('stock.location')
        scrap_location_id = location_obj.search(cr, uid, [('scrap_location','=',True)])

        if 'product_id' in fields:
            res.update({'product_id': move.product_id.id})
        if 'product_uom' in fields:
            res.update({'product_uom': move.product_uom.id})
        if 'location_id' in fields:
            if scrap_location_id:
                res.update({'location_id': scrap_location_id[0]})
            else:
                res.update({'location_id': False})
        return res

    def move_scrap(self, cr, uid, ids, context=None):
        """ To move scrapped products
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: the ID or list of IDs if we want more than one
        @param context: A standard dictionary
        @return:
        """
        if context is None:
            context = {}
        move_obj = self.pool.get('stock.move')
        move_ids = context['active_ids']
        for data in self.browse(cr, uid, ids):
            move_obj.action_scrap(cr, uid, move_ids,
                             data.product_qty, data.location_id.id, restrict_lot_id=data.restrict_lot_id.id,
                             context=context)
        if context.get('active_id'):
            move = self.pool.get('stock.move').browse(cr, uid, context['active_id'], context=context)
            if move.picking_id:
                return {
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'stock.picking',
                    'type': 'ir.actions.act_window',
                    'res_id': move.picking_id.id,
                    'context': context
                }
        return {'type': 'ir.actions.act_window_close'}
