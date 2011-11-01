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

from osv import fields, osv
from tools.translate import _


class product_product(osv.osv):
    _inherit = "product.product"    

    def get_product_accounts(self, cr, uid, product_id, context=None):
        """ To get the stock input account, stock output account and stock journal related to product.
        @param product_id: product id            
        @return: dictionary which contains information regarding stock input account, stock output account and stock journal
        """
        product_obj = self.pool.get('product.product').browse(cr, uid, product_id, False)
        res = super(product_product,self).get_product_accounts(cr, uid, product_id, context=context)
        stock_input_acc = product_obj.property_stock_account_input and product_obj.property_stock_account_input.id or False 
        if not stock_input_acc:
            stock_input_acc = product_obj.categ_id.property_stock_account_input_categ and product_obj.categ_id.property_stock_account_input_categ.id or False
        
        stock_output_acc = product_obj.property_stock_account_output and product_obj.property_stock_account_output.id or False
        if not stock_output_acc:
            stock_output_acc = product_obj.categ_id.property_stock_account_output_categ and product_obj.categ_id.property_stock_account_output_categ.id or False

        journal_id = product_obj.categ_id.property_stock_journal and product_obj.categ_id.property_stock_journal.id or False
        
        res.update({'stock_account_input': stock_input_acc})
        res.update({'stock_account_output': stock_output_acc})
        res.update({'stock_journal': journal_id})  
        
        return res
    

    _columns = {
        "bom_ids": fields.one2many('mrp.bom', 'product_id','Bill of Materials'),
    }
    
#    Removed do_change_standard_price for the fix of lp:747056

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({
            'bom_ids': []
        })
        return super(product_product, self).copy(cr, uid, id, default, context=context)


product_product()
