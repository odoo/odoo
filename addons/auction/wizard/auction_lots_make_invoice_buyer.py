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

class auction_lots_make_invoice_buyer(osv.osv_memory):
    """Make Invoice for Buyer"""
    
    _name = "auction.lots.make.invoice.buyer"
    _description = __doc__
    _columns= {
       'amount': fields.float('Invoiced Amount', required =True, readonly=True, help="Buyer Price"), 
       'objects':fields.integer('# of objects', required =True, readonly=True), 
       'number':fields.char('Invoice Number', size=64), 
       'buyer_id':fields.many2one('res.partner', 'Buyer', required=True), 
    }
    _defaults={
       'number': lambda *a: False,
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
        res = super(auction_lots_make_invoice_buyer, self).default_get(cr, uid, fields, context=context)
        lots_obj=self.pool.get('auction.lots')
        for lot in lots_obj.browse(cr, uid, context.get('active_ids', []), context=context):
            if 'amount' in fields:
                res.update({'amount': lot.buyer_price})                
            if 'buyer_id' in fields:
                res.update({'buyer_id': lot.ach_uid and lot.ach_uid.id or False})                        
            if 'objects' in fields:
                res.update({'objects': len(context.get('active_ids', []))})   
        return res

    def makeInvoices(self, cr, uid, ids, context=None):
        """
        Create an invoice for selected lots (IDS) to BUYER_ID .
        @param cr: the current row, from the database cursor.
        @param uid: the current user’s ID for security checks.
        @param ids: List of Auction lots make invoice buyer’s IDs
        @return: dictionary of  account invoice form.
        """    
        order_obj = self.pool.get('auction.lots')
        mod_obj = self.pool.get('ir.model.data') 
        result = mod_obj._get_id(cr, uid, 'account', 'view_account_invoice_filter')
        id = mod_obj.read(cr, uid, result, ['res_id'])
        lots = order_obj.browse(cr, uid, context.get('active_ids', []), context=context)
        for current in self.browse(cr, uid, ids, context=context):
            invoice_number = current.number
            for lot in lots:
                up_auction = order_obj.write(cr, uid, [lot.id], {'ach_uid': current.buyer_id.id})
            lots_ids = order_obj.lots_invoice(cr, uid, context.get('active_ids', []), context, current.number)
            return  {
                'domain': "[('id','in', ["+','.join(map(str, lots_ids))+"])]", 
                'name': 'Buyer invoices', 
                'view_type': 'form', 
                'view_mode': 'tree,form', 
                'res_model': 'account.invoice', 
                'view_id': False, 
                'context': "{'type':'in_refund'}", 
                'type': 'ir.actions.act_window', 
                'search_view_id': id['res_id']         
            }

auction_lots_make_invoice_buyer()
