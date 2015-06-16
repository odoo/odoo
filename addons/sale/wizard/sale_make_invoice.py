# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import UserError

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
            raise UserError(_('You cannot create invoice when sales order is not confirmed.'))
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
                raise UserError(_("You shouldn't manually invoice the following sale order %s") % (sale_order.name))

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
