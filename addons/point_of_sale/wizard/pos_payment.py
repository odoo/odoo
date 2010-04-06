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

import netsvc
from osv import osv,fields
from tools.translate import _
import pos_box_entries
import time
from decimal import Decimal
from tools.translate import _
import pos_receipt

class pos_make_payment(osv.osv_memory):
    _name = 'pos.make.payment'
    _description = 'Point of Sale Payment'
    
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
        res = super(pos_make_payment, self).default_get(cr, uid, fields, context=context)
        record_id = context and context.get('active_id',False)  
        j_obj = self.pool.get('account.journal')
        company_id = self.pool.get('res.users').browse(cr,uid,uid).company_id.id
        journal = j_obj.search(cr, uid, [('type', '=', 'cash'), ('company_id', '=', company_id)])
        
        if journal:
            journal = journal[0]
        else:
            journal = None
        wf_service = netsvc.LocalService("workflow")

        order_obj=self.pool.get('pos.order')
        order = order_obj.browse(cr, uid, record_id, context)
        #get amount to pay
        amount = order.amount_total - order.amount_paid
        if amount <= 0.0:
            context.update({'flag': True})
            order_obj.action_paid(cr, uid, [record_id], context)
        elif order.amount_paid > 0.0:
            order_obj.write(cr, uid, [record_id], {'state': 'advance'})
        invoice_wanted_checked = False
    
        current_date = time.strftime('%Y-%m-%d')
            
        if 'journal' in fields:
            res.update({'journal':journal})         
        if 'amount' in fields:
            res.update({'amount':amount})   
        if 'invoice_wanted' in fields:
            res.update({'invoice_wanted':invoice_wanted_checked})               
        if 'payment_date' in fields:
            res.update({'payment_date':current_date})
        if 'payment_name'  in fields: 
            res.update({'payment_name':'Payment'})    
        return res
        
    def view_init(self, cr, uid, fields_list, context=None):
        res = super(pos_make_payment, self).view_init(cr, uid, fields_list, context=context)
        record_id = context and context.get('active_id', False) or False        
        order = self.pool.get('pos.order').browse(cr, uid, record_id)
        if not order.lines:
                raise osv.except_osv('Error!','No order lines defined for this sale ')
        True
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        """ 
             Changes the view dynamically
        
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param context: A standard dictionary 
             
             @return: New arch of view.
        
        """
        record_id = context and context.get('record_id', False) or False        
        res = super(pos_make_payment, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
        if record_id:
            order = self.pool.get('pos.order').browse(cr, uid, record_id)
            amount = order.amount_total - order.amount_paid
            if amount==0.0:
                res['arch'] = """ <form string="Make Payment" colspan="4">
                                <group col="2" colspan="2">
                                    <label string="Do you want to print the Receipt?" colspan="4"/>
                                    <separator colspan="4"/>
                                    <button icon="gtk-cancel" special="cancel" string="No" readonly="0"/>
                                    <button name="print_report" string="Print Receipt" type="object" icon="gtk-print"/>
                                </group>
                            </form>
                        """
        return res

    def check(self, cr, uid, ids, context=None):
        
        """Check the order:
        if the order is not paid: continue payment,
        if the order is paid print invoice (if wanted) or ticket.
        """
        record_id = context and context.get('active_id',False)      
        order_obj = self.pool.get('pos.order')
        jrnl_obj = self.pool.get('account.journal')        
        order = order_obj.browse(cr, uid, record_id, context)
        amount = order.amount_total - order.amount_paid
        data =  self.read(cr, uid, ids)[0]

        # Todo need to check ...
        if amount !=0.0:
            invoice_wanted = data['invoice_wanted']
            jrnl_used=False
            if data.get('journal',False):
                jrnl_used=jrnl_obj.browse(cr,uid,data['journal'])
            order_obj.write(cr, uid, [record_id], {'invoice_wanted': invoice_wanted})
            order_obj.add_payment(cr, uid, record_id, data, context=context)            
        
        if amount<=0.0:
            context.update({'flag':True})
            order_obj.action_paid(cr,uid,[record_id],context)
        if order_obj.test_paid(cr, uid, [record_id]):
            if order.partner_id and order.invoice_wanted:
                return self.create_invoice(cr,uid,ids,context)
            else:
                order_obj.write(cr, uid, [record_id],{'state':'paid'})                            
                return self.print_report(cr, uid, ids, context)  
        if order.amount_paid > 0.0:
            self.pool.get('pos.order').write(cr, uid, [record_id],{'state':'advance'})
            return self.print_report(cr, uid, ids, context)            
        return {}

    
    def create_invoice(self, cr, uid, ids, context):
        wf_service = netsvc.LocalService("workflow")
        record_ids = context and context.get('active_ids',False)      
        for i in record_ids:
            wf_service.trg_validate(uid, 'pos.order', i, 'invoice', cr)
        datas = {'ids' : context.get('active_ids', [])}        
        return { 
                'type' : 'ir.actions.report.xml',
                'report_name':'pos.invoice',
                'datas' : datas,               
        }            
                    
    def print_report(self, cr, uid, ids, context=None):
        if not context:
            context={}
        """ 
         @summary: To get the date and print the report           
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary 
         @return : retrun report
        """        
        datas = {'ids' : context.get('active_ids',[])}
        res =  {}        
        datas['form'] = res

        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'pos.receipt',
            'datas': datas,
       }

    _columns = {
        'journal':fields.selection(pos_box_entries.get_journal, "Journal",required=True),
        'product_id': fields.many2one('product.product', "Acompte"),
        'amount':fields.float('Amount', digits=(16,2) ,required= True),
        'payment_name': fields.char('Payment name', size=32, required=True),
        'payment_date': fields.date('Payment date', required=True),
        'is_acc': fields.boolean('Accompte'),
        'invoice_wanted': fields.boolean('Invoice'),
        'num_sale':fields.char('Num.File', size=32),
    }
    
pos_make_payment()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

