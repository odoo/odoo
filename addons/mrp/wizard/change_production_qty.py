# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError

class change_production_qty(osv.osv_memory):
    _name = 'change.production.qty'
    _description = 'Change Quantity of Products'

    _columns = {
        'product_qty': fields.float('Product Qty', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
    }

    def default_get(self, cr, uid, fields, context=None):
        """ To get default values for the object.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param fields: List of fields for which we want default values
        @param context: A standard dictionary
        @return: A dictionary which of fields with values.
        """
        if context is None:
            context = {}
        res = super(change_production_qty, self).default_get(cr, uid, fields, context=context)
        prod_obj = self.pool.get('mrp.production')
        prod = prod_obj.browse(cr, uid, context.get('active_id'), context=context)
        if 'product_qty' in fields:
            res.update({'product_qty': prod.product_qty})
        return res

    def _update_product_to_produce(self, cr, uid, prod, qty, context=None):
        move_lines_obj = self.pool.get('stock.move')
        for m in prod.move_created_ids:
            move_lines_obj.write(cr, uid, [m.id], {'product_uom_qty': qty})

    def change_prod_qty(self, cr, uid, ids, context=None):
        """
        Changes the Quantity of Product.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        @return:
        """
        record_id = context and context.get('active_id',False)
        assert record_id, _('Active Id not found')
        prod_obj = self.pool.get('mrp.production')
        bom_obj = self.pool.get('mrp.bom')
        production_line_obj = self.pool['mrp.production.product.line']
        move_obj = self.pool.get('stock.move')
        for wiz_qty in self.browse(cr, uid, ids, context=context):
            prod = prod_obj.browse(cr, uid, record_id, context=context)
            prod_obj.write(cr, uid, [prod.id], {'product_qty': wiz_qty.product_qty})

            bom_point = prod.bom_id

            factor = prod.product_qty * prod.product_uom.factor / bom_point.product_uom.factor
            product_details, workcenter_details = \
                    bom_obj._bom_explode(cr, uid, bom_point, prod.product_id, factor / bom_point.product_qty, [], context=context)

            for move in product_details:
                product_line = prod.product_lines.filtered(lambda x: x.product_id.id == move['product_id'])
                move_line = prod.move_lines.filtered(lambda x: x.product_id.id == move['product_id'])
                production_line_obj.write(cr, uid, product_line.id, {'product_qty': move['product_qty']}, context=context)
                move_obj.write(cr, uid, move_line.id, {'product_uom_qty': move['product_qty']}, context=context)

            if prod.move_prod_id:
                move_obj.write(cr, uid, [prod.move_prod_id.id], {'product_uom_qty' :  wiz_qty.product_qty})
            self._update_product_to_produce(cr, uid, prod, wiz_qty.product_qty, context=context)
        return {}
