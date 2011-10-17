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
import time
import tools

class auction_pay_buy(osv.osv_memory):
    _name = "auction.pay.buy"
    _description = "Pay buy"
    _columns= {
       'amount': fields.float('Amount', digits= (16, 2), help="Amount For First Bank Statement"), 
       'buyer_id':fields.many2one('res.partner', 'Buyer'), 
       'statement_id1':fields.many2one('account.bank.statement', 'Statement', required=True, help="First Bank Statement For Buyer"), 
       'amount2': fields.float('Amount', digits= (16, 2), help="Amount For Second Bank Statement"), 
       'statement_id2':fields.many2one('account.bank.statement', 'Statement', help="Second Bank Statement For Buyer"), 
       'amount3': fields.float('Amount', digits = (16, 2), help="Amount For Third Bank Statement"), 
       'statement_id3':fields.many2one('account.bank.statement', 'Statement', help="Third Bank Statement For Buyer"), 
       'total': fields.float('Total Amount', digits = (16, 2), readonly =True), 
    }
    
    def default_get(self, cr, uid, fields, context=None):
        """ 
         To get default values for the object.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param fields: List of fields for which we want default values 
         @param context: A standard dictionary 
         @return: A dictionary which of fields with values. 
        """        
        if context is None:
            context={}
        res = super(auction_pay_buy, self).default_get(cr, uid, fields, context=context)
        auction_lots_obj= self.pool.get('auction.lots')       
        for lot in auction_lots_obj.browse(cr, uid, context.get('active_ids', []), context=context):
            if 'amount' in fields:
                res.update({'amount': lot.buyer_price})                
            if 'buyer_id' in fields:
                res.update({'buyer_id': lot.ach_uid and lot.ach_uid.id or False})                        
            if 'total' in fields:
                res.update({'total': lot.buyer_price})     
        return res
    
    def pay_and_reconcile(self, cr, uid, ids, context=None):
        """
        Pay and Reconcile
        @param cr: the current row, from the database cursor.
        @param uid: the current user’s ID for security checks.
        @param ids: the ID or list of IDs
        @param context: A standard dictionary 
        @return: 
        """        
        if context is None: context = {}
        lot_obj = self.pool.get('auction.lots')
        bank_statement_line_obj = self.pool.get('account.bank.statement.line')
        
        for datas in self.read(cr, uid, ids, context=context):
            if not abs(datas['total'] - (datas['amount'] + datas['amount2'] + datas['amount3'])) <0.01:
                rest = datas['total'] - (datas['amount'] + datas['amount2'] + datas['amount3'])
                raise osv.except_osv(_('Payment aborted !'), _('You should pay all the total: "%.2f" are missing to accomplish the payment.') %(round(rest, 2)))
    
            lots = lot_obj.browse(cr, uid, context.get('active_ids', []), context=context)
            for lot in lots:
                if datas['buyer_id']:
                    if isinstance(datas['buyer_id'], tuple):
                        datas['buyer_id'] = datas['buyer_id'][0]
                    lot_obj.write(cr, uid, [lot.id], {'ach_uid': datas['buyer_id']})
                if not lot.auction_id:
                    raise osv.except_osv(_('Error!'), _('No auction date for "%s": Please set one.') % (lot.name))
                lot_obj.write(cr, uid, [lot.id], {'is_ok':True})
            for st, stamount in [('statement_id1', 'amount'), ('statement_id2', 'amount2'), ('statement_id3', 'amount3')]:
                if isinstance(datas[st], tuple):
                        datas[st] = datas[st][0]
                if datas[st]:
                    new_id = bank_statement_line_obj.create(cr, uid, {
                        'name':'Buyer:'+ str(lot.ach_login or '')+', auction:'+ lots[0].auction_id.name, 
                        'date': time.strftime('%Y-%m-%d'), 
                        'partner_id': datas['buyer_id'] or False, 
                        'type':'customer', 
                        'statement_id': datas[st], 
                        'account_id': lot.auction_id.acc_income.id, 
                        'amount': datas[stamount]
                        })
                    for lot in lots:
                        lot_obj.write(cr, uid, [lot.id], {'statement_id':[(4, new_id)]})
            return {'type': 'ir.actions.act_window_close'}
auction_pay_buy()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

