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

class change_standard_price(osv.osv_memory):
    _name = "stock.change.standard.price"
    _description = "Change Standard Price"
    _columns = {
        'new_price': fields.float('Price', required=True, digits_compute=dp.get_precision('Product Price'),
                                  help="If cost price is increased, stock variation account will be debited "
                                        "and stock output account will be credited with the value = (difference of amount * quantity available).\n"
                                        "If cost price is decreased, stock variation account will be creadited and stock input account will be debited."),
        'stock_account_input':fields.many2one('account.account', 'Stock Input Account'),
        'stock_account_output':fields.many2one('account.account', 'Stock Output Account'),
        'stock_journal':fields.many2one('account.journal', 'Stock journal', required=True),
        'enable_stock_in_out_acc':fields.boolean('Enable Related Account',),
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
        product_pool = self.pool.get('product.product')
        product_obj = product_pool.browse(cr, uid, context.get('active_id', False))
        res = super(change_standard_price, self).default_get(cr, uid, fields, context=context)

        accounts = product_pool.get_product_accounts(cr, uid, context.get('active_id', False), context={})

        price = product_obj.standard_price

        if 'new_price' in fields:
            res.update({'new_price': price})
        if 'stock_account_input' in fields:
            res.update({'stock_account_input': accounts['stock_account_input']})
        if 'stock_account_output' in fields:
            res.update({'stock_account_output': accounts['stock_account_output']})
        if 'stock_journal' in fields:
            res.update({'stock_journal': accounts['stock_journal']})
        if 'enable_stock_in_out_acc' in fields:
            res.update({'enable_stock_in_out_acc': True})

        return res

    # onchange_price function is not used anywhere 
    def onchange_price(self, cr, uid, ids, new_price, context=None):
        """ Sets stock input and output account according to the difference
            of old price and new price.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param new_price: Changed price
        @param context: A standard dictionary
        @return: Dictionary of values
        """
        if context is None:
            context = {}
        product_obj = self.pool.get('product.product').browse(cr, uid, context.get('active_id', False), context=context)
        price = product_obj.standard_price
        diff = price - new_price
        if diff > 0 :
            return {'value' : {'enable_stock_in_out_acc':True}}
        else :
            return {'value' : {'enable_stock_in_out_acc':False}}

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
        rec_id = context and context.get('active_id', False)
        assert rec_id, _('Active ID is not set in Context.')
        prod_obj = self.pool.get('product.product')
        res = self.browse(cr, uid, ids, context=context)
        datas = {
            'new_price' : res[0].new_price,
            'stock_output_account' : res[0].stock_account_output.id,
            'stock_input_account' : res[0].stock_account_input.id,
            'stock_journal' : res[0].stock_journal.id
        }
        prod_obj.do_change_standard_price(cr, uid, [rec_id], datas, context)
        return {'type': 'ir.actions.act_window_close'}

change_standard_price()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
