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
        rec_id = context and context.get('active_id', False)
        res = {}
        price = self.pool.get('product.product').browse(cr, uid, rec_id)
        res['new_price'] = price.standard_price
        return res
    
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
        prod_obj = self.pool.get('product.template')
        location_obj = self.pool.get('stock.location')
        lot_obj = self.pool.get('stock.report.prodlots')
        move_obj = self.pool.get('account.move')
        move_line_obj = self.pool.get('account.move.line')
        data_obj = self.pool.get('ir.model.data')
        
        res = self.read(cr, uid, ids[0], ['new_price'])
        new_price = res.get('new_price',[])
        data = prod_obj.browse(cr, uid, rec_id)
        diff = data.standard_price - new_price
        prod_obj.write(cr, uid, rec_id, {'standard_price': new_price})
        
        loc_ids = location_obj.search(cr, uid, [('account_id','<>',False),('usage','=','internal')])
        lot_ids = lot_obj.search(cr, uid, [('location_id', 'in', loc_ids),('product_id','=',rec_id)])
        qty = 0
        debit = 0.0
        credit = 0.0
        stock_input_acc = data.property_stock_account_input.id or data.categ_id.property_stock_account_input_categ.id
        stock_output_acc = data.property_stock_account_output.id or data.categ_id.property_stock_account_output_categ.id
            
        for lots in lot_obj.browse(cr, uid, lot_ids):
            qty += lots.name
        
        if stock_input_acc and stock_output_acc and lot_ids:
            move_id = move_obj.create(cr, uid, {'journal_id': data.categ_id.property_stock_journal.id})
            if diff > 0:
                credit = qty * diff
                move_line_obj.create(cr, uid, {
                                'name': data.name,
                                'account_id': stock_input_acc,
                                'credit': credit,
                                'move_id': move_id
                                })
                for lots in lot_obj.browse(cr, uid, lot_ids):
                    credit = lots.name * diff
                    move_line_obj.create(cr, uid, {
                                    'name': 'Expense',
                                    'account_id': lots.location_id.account_id.id,
                                    'debit': credit,
                                    'move_id': move_id
                                    })
            elif diff < 0:
                debit = qty * -diff
                move_line_obj.create(cr, uid, {
                                'name': data.name,
                                'account_id': stock_output_acc,
                                'debit': debit,
                                'move_id': move_id
                                })
                for lots in lot_obj.browse(cr, uid, lot_ids):
                    debit = lots.name * -diff
                    move_line_obj.create(cr, uid, {
                                    'name': 'Income',
                                    'account_id': lots.location_id.account_id.id,
                                    'credit': debit,
                                    'move_id': move_id
                                    })
            else:
                raise osv.except_osv(_('Warning!'),_('No Change in Price.'))
        else:
            raise osv.except_osv(_('Warning!'),_('No Accounts are defined for ' 
                        'this product on its location.\nCan\'t create Move.'))
        
        id2 = data_obj._get_id(cr, uid, 'account', 'view_move_tree')
        id3 = data_obj._get_id(cr, uid, 'account', 'view_move_form')
        
        if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id
        if id3:
            id3 = data_obj.browse(cr, uid, id3, context=context).res_id
        
        return {
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'res_id' : move_id,
                'views': [(id3,'form'),(id2,'tree')],
                'type': 'ir.actions.act_window',
        }

change_standard_price()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
