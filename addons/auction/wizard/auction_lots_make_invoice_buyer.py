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
import netsvc
import pooler
import time
import tools
import wizard

class auction_lots_make_invoice_buyer(osv.osv_memory):
    
    def _value_amount(self, cr, uid, context={}):
        """
        For Amount default value
        @return:default auction lots amount value in amount fields. 
        """
        lots= self.pool.get('auction.lots').browse(cr, uid, context['active_ids'])
        amount_total=0.0
        for lot in lots:
            amount_total+=lot.buyer_price
        return amount_total
        
    def _value_object(self, cr, uid, context={}):
        """
        For object default value.
        @return:length of id  in Object field.
        """
        object = len(context['active_ids'])
        return object
    
    def _value_buyer_id(self, cr, uid, context={}):
        """
        For default buyer id value
        @return:auction lots buyer id in buyer id field.
        """
        lots= self.pool.get('auction.lots').browse(cr, uid, context['active_ids'])
        for lot in lots:
            buyer=lot and lot.ach_uid.id or False
        return buyer  

    def _makeInvoices(self, cr, uid, ids, context):
        """
        Create an invoice for selected lots (IDS) to BUYER_ID .
        @param cr: the current row, from the database cursor.
        @param uid: the current user’s ID for security checks.
        @param ids: List of Auction lots make invoice buyer’s IDs
        @return: dictionary of  account invoice form.
        """    
        newinv = []
        for data in self.read(cr, uid, ids):
            
            order_obj = self.pool.get('auction.lots')
            mod_obj = self.pool.get('ir.model.data') 
            result = mod_obj._get_id(cr, uid, 'account', 'view_account_invoice_filter')
            id = mod_obj.read(cr, uid, result, ['res_id'])
            lots = order_obj.browse(cr, uid, context['active_ids'])
            invoice_number = data['number']
            for lot in lots:
                up_auction = self.pool.get('auction.lots').write(cr, uid, [lot.id], {'ach_uid':data['buyer_id']})
            ids = order_obj.lots_invoice(cr, uid, context['active_ids'], context, data['number'])
            cr.commit()
            return  {
                'domain': "[('id','in', ["+','.join(map(str, ids))+"])]", 
                'name': 'Buyer invoices', 
                'view_type': 'form', 
                'view_mode': 'tree,form', 
                'res_model': 'account.invoice', 
                'view_id': False, 
                'context': "{'type':'in_refund'}", 
                'type': 'ir.actions.act_window', 
                'search_view_id': id['res_id']         
            }
            
    _name = "auction.lots.make.invoice.buyer"
    _description = "Make invoice buyer "
    _columns= {
               'amount': fields.float('Invoiced Amount', required =True, readonly=True), 
               'objects':fields.integer('# of objects', required =True, readonly=True), 
               'number':fields.char('Invoice Number', size=64), 
               'buyer_id':fields.many2one('res.partner', 'Buyer', required=True), 
               }
    _defaults={
               'amount':_value_amount,
               'objects':_value_object,
               'number':lambda *a: False,
               'buyer_id':_value_buyer_id
               
               }

auction_lots_make_invoice_buyer()
