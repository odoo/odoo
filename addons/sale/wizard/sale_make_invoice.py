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

class sale_make_invoice(osv.osv_memory):
    _name = "sale.make.invoice"
    _description = "Sales Make Invoice"
    _columns = {
        'grouped': fields.boolean('Group the invoices', help='Check the box to group the invoices for the same customers'),
        'invoice_date': fields.date('Invoice Date'),
    }
    _defaults = {
        'grouped': False,
        'invoice_date': fields.date.context_today,
    }

    def view_init(self, cr, uid, fields_list, context=None):
        if context is None:
            context = {}
        record_id = context and context.get('active_id', False)
        order = self.pool.get('sale.order').browse(cr, uid, record_id, context=context)
        if order.state == 'draft':
            raise osv.except_osv(_('Warning!'), _('You cannot create invoice when sales order is not confirmed.'))
        return False

    def make_invoices(self, cr, uid, ids, context=None):
        order_obj = self.pool.get('sale.order')
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        newinv = []
        if context is None:
            context = {}
        data = self.read(cr, uid, ids)[0]
        for sale_order in order_obj.browse(cr, uid, context.get(('active_ids'), []), context=context):
            if sale_order.state != 'manual':
                raise osv.except_osv(_('Warning!'), _("You shouldn't manually invoice the following sale order %s") % (sale_order.name))

        order_obj.action_invoice_create(cr, uid, context.get(('active_ids'), []), data['grouped'], date_invoice=data['invoice_date'])
        orders = order_obj.browse(cr, uid, context.get(('active_ids'), []), context=context)
        for o in orders:
            for i in o.invoice_ids:
                newinv.append(i.id)
        # Dummy call to workflow, will not create another invoice but bind the new invoice to the subflow
        order_obj.signal_workflow(cr, uid, [o.id for o in orders if o.order_policy == 'manual'], 'manual_invoice')
        result = mod_obj.get_object_reference(cr, uid, 'account', 'action_invoice_tree1')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        result['domain'] = "[('id','in', [" + ','.join(map(str, newinv)) + "])]"

        return result


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
