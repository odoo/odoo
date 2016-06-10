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

from openerp.osv import osv
from openerp.tools.translate import _


class purchase_line_invoice(osv.osv_memory):

    """ To create invoice for purchase order line"""

    _name = 'purchase.order.line_invoice'
    _description = 'Purchase Order Line Make Invoice'

    def _make_invoice_by_partner(self, cr, uid, partner, orders, lines_ids, context=None):
        """
            create a new invoice for one supplier
            @param cr : Cursor
            @param uid : Id of current user
            @param partner : The object partner
            @param orders : The set of orders to add in the invoice
            @param lines : The list of line's id
        """
        purchase_obj = self.pool.get('purchase.order')
        account_jrnl_obj = self.pool.get('account.journal')
        invoice_obj = self.pool.get('account.invoice')
        name = orders and orders[0].name or ''
        journal_id = account_jrnl_obj\
            .search(cr, uid, [('type', '=', 'purchase')], context=None)
        journal_id = journal_id and journal_id[0] or False
        a = partner.property_account_payable.id
        inv = {
            'name': name,
            'origin': name,
            'type': 'in_invoice',
            'journal_id': journal_id,
            'reference': partner.ref,
            'account_id': a,
            'partner_id': partner.id,
            'invoice_line': [(6, 0, lines_ids)],
            'currency_id': orders[0].currency_id.id,
            'comment': " \n".join([order.notes for order in orders if order.notes]),
            'payment_term': orders[0].payment_term_id.id,
            'fiscal_position': partner.property_account_position.id
        }
        inv_id = invoice_obj.create(cr, uid, inv, context=context)
        purchase_obj.write(cr, uid, [order.id for order in orders], {'invoice_ids': [(4, inv_id)]}, context=context)
        return inv_id

    def makeInvoices(self, cr, uid, ids, context=None):

        """
             To get Purchase Order line and create Invoice
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param context: A standard dictionary
             @return : retrun view of Invoice
        """

        if context is None:
            context={}

        record_ids =  context.get('active_ids',[])
        if record_ids:
            res = False
            invoices = {}
            purchase_obj = self.pool.get('purchase.order')
            purchase_line_obj = self.pool.get('purchase.order.line')
            invoice_line_obj = self.pool.get('account.invoice.line')

            for line in purchase_line_obj.browse(cr, uid, record_ids, context=context):
                if (not line.invoiced) and (line.state not in ('draft', 'cancel')):
                    if not line.partner_id.id in invoices:
                        invoices[line.partner_id.id] = []
                    acc_id = purchase_obj._choose_account_from_po_line(cr, uid, line, context=context)
                    inv_line_data = purchase_obj._prepare_inv_line(cr, uid, acc_id, line, context=context)
                    inv_line_data.update({'origin': line.order_id.name})
                    inv_id = invoice_line_obj.create(cr, uid, inv_line_data, context=context)
                    purchase_line_obj.write(cr, uid, [line.id], {'invoiced': True, 'invoice_lines': [(4, inv_id)]})
                    invoices[line.partner_id.id].append((line,inv_id))

            res = []
            for result in invoices.values():
                il = map(lambda x: x[1], result)
                orders = list(set(map(lambda x : x[0].order_id, result)))

                res.append(self._make_invoice_by_partner(cr, uid, orders[0].partner_id, orders, il, context=context))

        return {
            'domain': "[('id','in', ["+','.join(map(str,res))+"])]",
            'name': _('Supplier Invoices'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'view_id': False,
            'context': "{'type':'in_invoice', 'journal_type': 'purchase'}",
            'type': 'ir.actions.act_window'
        }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

