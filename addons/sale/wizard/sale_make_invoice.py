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
        'grouped': fields.boolean('Group Invoices', help='Check the box to group invoices for same customer'),
        'invoice_date': fields.date('Invoice Date'),
    }
    _defaults = {
        'grouped': False,
        'invoice_date': fields.date.context_today,
    }

    def resolve_order_ids_from_context(self, cr, uid, context=None):
        if context is None:
            context = {}
        
        active_model = context.get('active_model')
        order_obj = self.pool.get(active_model)
        active_ids = context.get('active_ids')
        line_ids = []
        order_ids = []
        if active_model == 'sale.order.line':
            line_ids = active_ids
            for line in order_obj.browse(cr, uid, line_ids, context=context):
                if line.order_id.id not in order_ids:
                    order_ids.append(line.order_id.id)
        elif active_model == 'sale.order':
            order_ids = active_ids
        return order_ids, line_ids
    
    def _check_order_lines_before_invoice_create(self, cr, uid, ids, grouped=False, line_ids=None, context=None):
        partner_ids = []
        order_obj = self.pool.get('sale.order')
        order_line_obj = self.pool.get('sale.order.line')

        if line_ids:
            for order_line in order_line_obj.browse(cr, uid, line_ids, context=context):
                if order_line.invoiced:
                    raise osv.except_osv(_('Warning!'), _("You can not invoice already invoiced Sales Order %s") % (order_line.order_id.name))

        for order in order_obj.browse(cr, uid, ids, context=context):
            if order.state == 'draft':
                raise osv.except_osv(_('Warning!'), _('You cannot create invoice when sales order is not confirmed.'))
            if grouped:
                if not partner_ids:
                    partner_ids.append(order.partner_id.id)
                else:
                    if order.partner_id.id not in(partner_ids):
                        raise osv.except_osv(_('Warning!'), _('You cannot group invoices which have different customers.'))
        return True
    
    def make_invoices(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        sale_order_obj = self.pool.get('sale.order')
        if context is None:
            context = {}
        data = self.read(cr, uid, ids)[0]
        order_ids, line_ids = self.resolve_order_ids_from_context(cr, uid, context=context)
        sale_order_obj._check_order_before_invoice_create(cr, uid, order_ids, grouped=data['grouped'], line_ids=line_ids, context=context)
        invoice_ids = sale_order_obj.action_invoice_create(cr, uid, order_ids, data['grouped'], states=None, date_invoice=data['invoice_date'], line_ids=line_ids, context=context)
        result = mod_obj.get_object_reference(cr, uid, 'account', 'action_invoice_tree1')
        view_id = result and result[1] or False
        result = act_obj.read(cr, uid, [view_id], context=context)[0]
        if not isinstance(invoice_ids, (list)):
            view_ids = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')
            view_id = view_ids and view_ids[1] or False
            result['res_id'] = invoice_ids
            result.update(views=[(view_id, 'form'), (False, 'tree')])
        else:
            result['domain'] = "[('id','in', [" + ','.join(map(str, invoice_ids)) + "])]"
        return result


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
