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
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

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
        move_obj = self.pool.get('stock.move')
        for wiz_qty in self.browse(cr, uid, ids, context=context):
            prod = prod_obj.browse(cr, uid, record_id, context=context)
            prod_obj.write(cr, uid, [prod.id], {'product_qty': wiz_qty.product_qty})
            prod_obj.action_compute(cr, uid, [prod.id])

            for move in prod.move_lines:
                bom_point = prod.bom_id
                bom_id = prod.bom_id.id
                if not bom_point:
                    bom_id = bom_obj._bom_find(cr, uid, product_id=prod.product_id.id, context=context)
                    if not bom_id:
                        raise osv.except_osv(_('Error!'), _("Cannot find bill of material for this product."))
                    prod_obj.write(cr, uid, [prod.id], {'bom_id': bom_id})
                    bom_point = bom_obj.browse(cr, uid, [bom_id])[0]

                if not bom_id:
                    raise osv.except_osv(_('Error!'), _("Cannot find bill of material for this product."))

                factor = prod.product_qty * prod.product_uom.factor / bom_point.product_uom.factor
                product_details, workcenter_details = \
                    bom_obj._bom_explode(cr, uid, bom_point, prod.product_id, factor / bom_point.product_qty, [], context=context)
                for r in product_details:
                    if r['product_id'] == move.product_id.id:
                        move_obj.write(cr, uid, [move.id], {'product_uom_qty': r['product_qty']})
            if prod.move_prod_id:
                move_obj.write(cr, uid, [prod.move_prod_id.id], {'product_uom_qty' :  wiz_qty.product_qty})
            self._update_product_to_produce(cr, uid, prod, wiz_qty.product_qty, context=context)
        return {}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
