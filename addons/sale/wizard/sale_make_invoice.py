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

class sale_make_invoice(osv.osv_memory):
    _name = "sale.make.invoice"
    _description = "Sales Make Invoice"
    _columns = {
        'grouped': fields.boolean('Group the invoices', help='Check the box to group the invoices for the same customers'),
        'invoice_date': fields.date('Invoice Date'),
    }
    _defaults = {
        'grouped': False
    }

    def view_init(self, cr, uid, fields_list, context=None):
        if context is None:
            context = {}
        record_id = context and context.get('active_id', False)
        order = self.pool.get('sale.order').browse(cr, uid, record_id, context=context)
        if order.state == 'draft':
            raise osv.except_osv(_('Warning !'),'You cannot create invoice when sales order is not confirmed.')
        return False

    def make_invoices(self, cr, uid, ids, context=None):
        order_obj = self.pool.get('sale.order')
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        newinv = []
        if context is None:
            context = {}
        data = self.read(cr, uid, ids)[0]
        order_obj.action_invoice_create(cr, uid, context.get(('active_ids'), []), data['grouped'], date_inv = data['invoice_date'])
        wf_service = netsvc.LocalService("workflow")
        for id in context.get(('active_ids'), []):
            wf_service.trg_validate(uid, 'sale.order', id, 'manual_invoice', cr)

        for o in order_obj.browse(cr, uid, context.get(('active_ids'), []), context=context):
            for i in o.invoice_ids:
                newinv.append(i.id)

        result = mod_obj.get_object_reference(cr, uid, 'account', 'action_invoice_tree1')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        result['domain'] = "[('id','in', ["+','.join(map(str,newinv))+"])]"

        return result

sale_make_invoice()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: