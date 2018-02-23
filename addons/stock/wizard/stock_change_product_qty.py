# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp import tools
from openerp.exceptions import UserError, AccessError


class stock_change_product_qty(osv.osv_memory):
    _name = "stock.change.product.qty"
    _description = "Change Product Quantity"

    _columns = {
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'product_tmpl_id': fields.many2one('product.template', 'Template', required=True),
        'product_variant_count': fields.related('product_tmpl_id', 'product_variant_count', type='integer', string='Variant Number'),
        'new_quantity': fields.float('New Quantity on Hand', digits_compute=dp.get_precision('Product Unit of Measure'), required=True, help='This quantity is expressed in the Default Unit of Measure of the product.'),
        'lot_id': fields.many2one('stock.production.lot', 'Serial Number', domain="[('product_id','=',product_id)]"),
        'location_id': fields.many2one('stock.location', 'Location', required=True, domain="[('usage', '=', 'internal')]"),
    }
    _defaults = {
        'new_quantity': 1,
        'product_id': lambda self, cr, uid, ctx: ctx and ctx.get('active_id', False) or False
    }

    def default_get(self, cr, uid, fields, context):
        res = super(stock_change_product_qty, self).default_get(cr, uid, fields, context=context)

        if context.get('active_model') == 'product.template':
            product_ids = self.pool.get('product.product').search(cr, uid, [('product_tmpl_id', '=', context.get('active_id'))], context=context)
            if product_ids:
                res['product_id'] = product_ids[0]

        if 'location_id' in fields:
            location_id = res.get('location_id', False)
            if not location_id:
                try:
                    model, location_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'stock', 'stock_location_stock')
                except (AccessError):
                    pass
            if location_id:
                try:
                    self.pool.get('stock.location').check_access_rule(cr, uid, [location_id], 'read', context=context)
                except (AccessError):
                   location_id = False
            res['location_id'] = location_id
        return res

    def create(self, cr, uid, values, context=None):
        if values.get('product_id'):
            values.update(self.onchange_product_id(cr, uid, None, values['product_id'], context=context)['value'])
        return super(stock_change_product_qty, self).create(cr, uid, values, context=context)

    def _prepare_inventory_line(self, cr, uid, inventory_id, data, context=None):

        product = data.product_id.with_context(location=data.location_id.id, lot_id=data.lot_id.id)
        th_qty = product.qty_available

        res = {
               'inventory_id': inventory_id,
               'product_qty': data.new_quantity,
               'location_id': data.location_id.id,
               'product_id': data.product_id.id,
               'product_uom_id': data.product_id.uom_id.id,
               'theoretical_qty': th_qty,
               'prod_lot_id': data.lot_id.id,
        }

        return res

    def onchange_product_id(self, cr, uid, ids, prod_id, context=None):
        product = self.pool.get('product.product').browse(cr, uid, prod_id)
        return {'value': {
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_variant_count': product.product_tmpl_id.product_variant_count
        }}

    def change_product_qty(self, cr, uid, ids, context=None):
        """ Changes the Product Quantity by making a Physical Inventory. """
        if context is None:
            context = {}

        inventory_obj = self.pool.get('stock.inventory')
        inventory_line_obj = self.pool.get('stock.inventory.line')

        for data in self.browse(cr, uid, ids, context=context):
            if data.new_quantity < 0:
                raise UserError(_('Quantity cannot be negative.'))
            ctx = context.copy()
            ctx['location'] = data.location_id.id
            ctx['lot_id'] = data.lot_id.id
            if data.product_id.id and data.lot_id.id:
                filter = 'none'
            elif data.product_id.id:
                filter = 'product'
            else:
                filter = 'none'
            inventory_id = inventory_obj.create(cr, uid, {
                'name': _('INV: %s') % tools.ustr(data.product_id.name),
                'filter': filter,
                'product_id': data.product_id.id,
                'location_id': data.location_id.id,
                'lot_id': data.lot_id.id}, context=context)

            line_data = self._prepare_inventory_line(cr, uid, inventory_id, data, context=context)

            inventory_line_obj.create(cr, uid, line_data, context=context)
            inventory_obj.action_done(cr, uid, [inventory_id], context=context)
        return {}

    def onchange_location_id(self, cr, uid, ids, location_id, product_id, context=None):
        if location_id:
            qty_wh = 0.0
            qty = self.pool.get('product.product')._product_available(cr, uid, [product_id], context=dict(context or {}, location=location_id, compute_child=False))
            if product_id in qty:
                qty_wh = qty[product_id]['qty_available']
            return { 'value': { 'new_quantity': qty_wh } }
