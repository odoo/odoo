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

from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp import workflow

class sale_order_line_make_invoice(osv.osv_memory):
    _name = "sale.order.line.make.invoice"
    _description = "Sale OrderLine Make_invoice"
    
    def make_invoices(self, cr, uid, ids, context=None):
        """
             To make invoices.

             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param ids: the ID or list of IDs
             @param context: A standard dictionary

             @return: A dictionary which of fields with values.

        """
        if context is None: context = {}
        res = False
        invoices = {}

    #TODO: merge with sale.py/make_invoice
        def make_invoice(order, lines):
            """
                 To make invoices.

                 @param order:
                 @param lines:

                 @return:

            """
            a = order.partner_id.property_account_receivable.id
            if order.partner_id and order.partner_id.property_payment_term.id:
                pay_term = order.partner_id.property_payment_term.id
            else:
                pay_term = False
            inv = {
                'name': order.client_order_ref or '',
                'origin': order.name,
                'type': 'out_invoice',
                'reference': "P%dSO%d" % (order.partner_id.id, order.id),
                'account_id': a,
                'partner_id': order.partner_invoice_id.id,
                'invoice_line': [(6, 0, lines)],
                'currency_id' : order.pricelist_id.currency_id.id,
                'comment': order.note,
                'payment_term': pay_term,
                'fiscal_position': order.fiscal_position.id or order.partner_id.property_account_position.id,
                'user_id': order.user_id and order.user_id.id or False,
                'company_id': order.company_id and order.company_id.id or False,
                'date_invoice': fields.date.today(),
            }
            inv_id = self.pool.get('account.invoice').create(cr, uid, inv)
            return inv_id

        sales_order_line_obj = self.pool.get('sale.order.line')
        sales_order_obj = self.pool.get('sale.order')
        for line in sales_order_line_obj.browse(cr, uid, context.get('active_ids', []), context=context):
            if (not line.invoiced) and (line.state not in ('draft', 'cancel')):
                if not line.order_id in invoices:
                    invoices[line.order_id] = []
                line_id = sales_order_line_obj.invoice_line_create(cr, uid, [line.id])
                for lid in line_id:
                    invoices[line.order_id].append(lid)
        if not invoices:
            raise osv.except_osv(_('Warning!'), _('Invoice cannot be created for this Sales Order Line due to one of the following reasons:\n' 
            '1.The state of this sales order line is either "draft" or "cancel"!\n2.The Sales Order Line is Invoiced!'))
        new_invoice_ids = []
        for order, il in invoices.items():
            new_invoice_id = make_invoice(order, il)
            cr.execute('INSERT INTO sale_order_invoice_rel \
                    (order_id,invoice_id) values (%s,%s)', (order.id, new_invoice_id))
            sales_order_obj.invalidate_cache(cr, uid, ['invoice_ids'], [order.id], context=context)
            new_invoice_ids.append(new_invoice_id)
            flag = True
            sales_order_obj.message_post(cr, uid, [order.id], body=_("Invoice created"), context=context)
            data_sale = sales_order_obj.browse(cr, uid, order.id, context=context)
            for line in data_sale.order_line:
                if not line.invoiced:
                    flag = False
                    break
            if flag:
                workflow.trg_validate(uid, 'sale.order', order.id, 'manual_invoice', cr)

        res = {'type': 'ir.actions.act_window_close'}
        if context.get('open_invoices', False):
            res = self.open_invoices( cr, uid, ids, new_invoice_ids, context=context)
        return res

    def open_invoices(self, cr, uid, ids, invoice_ids, context=None):
        """ open a view on one of the given invoice_ids """
        ir_model_data = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        action_res = ir_model_data.get_object_reference(cr, uid, 'account', 'action_invoice_tree1')
        action_id = action_res and action_res[1] or False
        res = act_obj.read(cr, uid, [action_id], context=context)[0]
        domain = eval(res['domain'])
        domain.append(('id', 'in', invoice_ids))
        res['domain'] = str(domain)
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
