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

class change_standard_price(osv.osv_memory):
    _name = "stock.change.standard.price"
    _description = "Change Standard Price"
    _columns = {
            'new_price': fields.float('Price', required=True),
            'stock_account_input':fields.many2one('account.account', 'Stock Input Account'),
            'stock_account_output':fields.many2one('account.account', 'Stock Output Account'),
            'stock_journal':fields.many2one('account.journal', 'Stock journal', required=True),            
            'enable_stock_in_out_acc':fields.boolean('Enable Related Account',),
    }
    
    def default_get(self, cr, uid, fields, context):
        """ 
         To get default values for the object.
        
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param fields: List of fields for which we want default values 
         @param context: A standard dictionary 
         
         @return: A dictionary which of fields with values. 
        
        """ 
        product_obj = self.pool.get('product.product').browse(cr, uid, context.get('active_id', False))
        res = super(change_standard_price, self).default_get(cr, uid, fields, context=context)   
        
        stock_input_acc = product_obj.property_stock_account_input and product_obj.property_stock_account_input.id or False 
        if not stock_input_acc:
            stock_input_acc = product_obj.categ_id.property_stock_account_input_categ and product_obj.categ_id.property_stock_account_input_categ.id or False
        
        stock_output_acc = product_obj.property_stock_account_output and product_obj.property_stock_account_output.id or False
        if not stock_output_acc:
            stock_output_acc = product_obj.categ_id.property_stock_account_output_categ and product_obj.categ_id.property_stock_account_output_categ.id or False

        price = product_obj.standard_price
        journal_id = product_obj.categ_id.property_stock_journal and product_obj.categ_id.property_stock_journal.id or False
        
        if 'new_price' in fields:
            res.update({'new_price': price})
        if 'stock_account_input' in fields:
            res.update({'stock_account_input': stock_input_acc})         
        if 'stock_account_output' in fields:
            res.update({'stock_account_output': stock_output_acc})         
        if 'stock_journal' in fields:
            res.update({'stock_journal': journal_id})  
        if 'enable_stock_in_out_acc' in fields:
            res.update({'enable_stock_in_out_acc': True})              
                 
                     
        return res
    
    def onchange_price(self, cr, uid, ids, new_price, context = {}):
        product_obj = self.pool.get('product.product').browse(cr, uid, context.get('active_id', False))
        price = product_obj.standard_price
        diff = price - new_price
        if diff > 0 : 
            return {'value' : {'enable_stock_in_out_acc':False}}
        else :
            return {'value' : {'enable_stock_in_out_acc':True}}
        
    def change_price(self, cr, uid, ids, context):
        """ 
             Changes the Standard Price of Product. 
             And creates an account move accordingly.
            
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param ids: List of IDs selected 
             @param context: A standard dictionary 
             
             @return:  
        
        """
        rec_id = context and context.get('active_id', False)
        assert rec_id, _('Active ID is not set in Context')
        prod_obj = self.pool.get('product.product')
        location_obj = self.pool.get('stock.location')
        lot_obj = self.pool.get('stock.report.prodlots')
        move_obj = self.pool.get('account.move')
        move_line_obj = self.pool.get('account.move.line')
        data_obj = self.pool.get('ir.model.data')
        
        res = self.browse(cr, uid, ids)
        
        loc_ids = location_obj.search(cr, uid, [('account_id','<>',False),('usage','=','internal')])
        
        new_price = res[0].new_price
        stock_output_acc = res[0].stock_account_output.id
        stock_input_acc = res[0].stock_account_input.id
        journal_id = res[0].stock_journal.id

        move_ids = []
        for location in location_obj.browse(cr, uid, loc_ids):
            c = context.copy()
            c.update({'location': location.id})
            c.update({'compute_child': False})
            
            product = prod_obj.browse(cr, uid, rec_id, context=c)
            qty = product.qty_available
            diff = product.standard_price - new_price                        
            assert diff, _("Could not find any difference between standard price and new price!")
            if qty:
                location_account = location.account_id and location.account_id.id or False
                company_id = location.company_id and location.company_id.id or False                
                assert location_account, _('Inventory Account is not specified for Location: %s' % (location.name))
                assert company_id, _('Company is not specified in Location')
                move_id = move_obj.create(cr, uid, {
                            'journal_id': journal_id, 
                            'company_id': company_id
                            }) 
                
                move_ids.append(move_id)
                if diff > 0:    
                    amount_diff = qty * diff        
                    move_line_obj.create(cr, uid, {
                                'name': product.name,
                                'account_id': stock_input_acc,
                                'debit': amount_diff,
                                'move_id': move_id,
                                })
                    move_line_obj.create(cr, uid, {
                                'name': location.name,
                                'account_id': location_account,
                                'credit': amount_diff,
                                'move_id': move_id
                                })
                elif diff < 0: 
                    amount_diff = qty * -diff
                    move_line_obj.create(cr, uid, {
                                'name': product.name,
                                'account_id': stock_output_acc,
                                'credit': amount_diff,
                                'move_id': move_id
                                })
                    move_line_obj.create(cr, uid, {
                                'name': location.name,
                                'account_id': location_account,
                                'debit': amount_diff,
                                'move_id': move_id
                                })                   
            
        prod_obj.write(cr, uid, rec_id, {'standard_price': new_price})

        return {  }

change_standard_price()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
