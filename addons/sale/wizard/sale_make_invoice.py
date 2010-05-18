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
from service import web_services
from tools.translate import _
import ir
import netsvc

class sale_make_invoice(osv.osv_memory):
    _name = "sale.make.invoice"
    _description = "Sale Make Invoice"
    _columns = {
        'grouped': fields.boolean('Group the invoices'),
        'invoice_date':fields.date('Invoice Date'),
    }
    _default = {
        'grouped' : lambda *a: False
    }

    def make_invoices(self, cr, uid, ids, context={}):
        order_obj = self.pool.get('sale.order')
        newinv = []
        data=self.read(cr,uid,ids)[0]
        order_obj.action_invoice_create(cr, uid, context.get(('active_ids'),[]), data['grouped'],date_inv = data['invoice_date'])
        for id in context.get(('active_ids'),[]):
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(uid, 'sale.order', id, 'manual_invoice', cr)
            
        for o in order_obj.browse(cr, uid, context.get(('active_ids'),[]), context):
            for i in o.invoice_ids:
                newinv.append(i.id)
        
        mod_obj =self.pool.get('ir.model.data')
        result = mod_obj._get_id(cr, uid, 'account', 'view_account_invoice_filter')
        
        id = mod_obj.read(cr, uid, result, ['res_id'])                
        return {
            'domain': "[('id','in', ["+','.join(map(str,newinv))+"])]",
            'name': 'Invoices',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'view_id': False,
            'context': "{'type':'out_refund'}",
            'type': 'ir.actions.act_window',
            'search_view_id': id['id']                
        }

sale_make_invoice()        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

