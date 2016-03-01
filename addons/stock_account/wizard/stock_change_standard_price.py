# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

class change_standard_price(osv.osv_memory):
    _name = "stock.change.standard.price"
    _description = "Change Standard Price"
    _columns = {
        'new_price': fields.float('Price', required=True, digits_compute=dp.get_precision('Product Price'),
            help="If cost price is increased, stock variation account will be debited "
            "and stock output account will be credited with the value = (difference of amount * quantity available).\n"
            "If cost price is decreased, stock variation account will be creadited and stock input account will be debited."),
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
        if context.get("active_model") == 'product.product':
            product_pool = self.pool.get('product.product')
        else:
            product_pool = self.pool.get('product.template')
        product_obj = product_pool.browse(cr, uid, context.get('active_id', False))

        res = super(change_standard_price, self).default_get(cr, uid, fields, context=context)

        price = product_obj.standard_price

        if 'new_price' in fields:
            res.update({'new_price': price})
        return res

    def change_price(self, cr, uid, ids, context=None):
        """ Changes the Standard Price of Product.
            And creates an account move accordingly.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        @return:
        """
        if context is None:
            context = {}
        rec_id = context.get('active_id', False)
        assert rec_id, _('Active ID is not set in Context.')
        new_price = self.browse(cr, uid, ids, context=context)[0].new_price
        if context.get("active_model") == 'product.template':
            prod_obj = self.pool.get('product.template')
            rec_ids = prod_obj.browse(cr, uid, rec_id, context=context).product_variant_ids.mapped('id')
        else:
            rec_ids = [rec_id]
        prod_obj = self.pool.get('product.product')
        prod_obj.do_change_standard_price(cr, uid, rec_ids, new_price, context)
        return {'type': 'ir.actions.act_window_close'}
