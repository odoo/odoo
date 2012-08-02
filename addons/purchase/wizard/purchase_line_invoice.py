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

from osv import osv
from tools.translate import _


class purchase_line_invoice(osv.osv_memory):

    """ To create invoice for purchase order line"""

    _name = 'purchase.order.line_invoice'
    _description = 'Purchase Order Line Make Invoice'

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
            invoice_obj=self.pool.get('account.invoice')
            purchase_line_obj=self.pool.get('purchase.order.line')
            property_obj=self.pool.get('ir.property')
            account_fiscal_obj=self.pool.get('account.fiscal.position')
            invoice_line_obj=self.pool.get('account.invoice.line')
            account_jrnl_obj=self.pool.get('account.journal')

            def multiple_order_invoice_notes(orders):
                notes = ""
                for order in orders:
                    notes += "%s \n" % order.notes
                return notes



            def make_invoice_by_partner(partner, orders, lines_ids):
                """
                    create a new invoice for one supplier
                    @param partner : The object partner
                    @param orders : The set of orders to add in the invoice
                    @param lines : The list of line's id
                """
                name = orders and orders[0].name or ''
                journal_id = account_jrnl_obj.search(cr, uid, [('type', '=', 'purchase')], context=None)
                journal_id = journal_id and journal_id[0] or False
                a = partner.property_account_payable.id
                inv = {
                    'name': name,
                    'origin': name,
                    'type': 'in_invoice',
                    'journal_id':journal_id,
                    'reference' : partner.ref,
                    'account_id': a,
                    'partner_id': partner.id,
                    'invoice_line': [(6,0,lines_ids)],
                    'currency_id' : orders[0].pricelist_id.currency_id.id,
                    'comment': multiple_order_invoice_notes(orders),
                    'payment_term': orders[0].payment_term.id,
                    'fiscal_position': partner.property_account_position.id
                }
                inv_id = invoice_obj.create(cr, uid, inv)
                for order in orders:
                    order.write({'invoice_ids': [(4, inv_id)]})
                return inv_id

            for line in purchase_line_obj.browse(cr,uid,record_ids):
                if (not line.invoiced) and (line.state not in ('draft','cancel')):
                    if not line.partner_id.id in invoices:
                        invoices[line.partner_id.id] = []
                    if line.product_id:
                        a = line.product_id.product_tmpl_id.property_account_expense.id
                        if not a:
                            a = line.product_id.categ_id.property_account_expense_categ.id
                        if not a:
                            raise osv.except_osv(_('Error !'),
                                    _('There is no expense account defined ' \
                                            'for this product: "%s" (id:%d)') % \
                                            (line.product_id.name, line.product_id.id,))
                    else:
                        a = property_obj.get(cr, uid,
                                'property_account_expense_categ', 'product.category',
                                context=context).id
                    fpos = line.order_id.fiscal_position or False
                    a = account_fiscal_obj.map_account(cr, uid, fpos, a)
                    inv_id = invoice_line_obj.create(cr, uid, {
                        'name': line.name,
                        'origin': line.order_id.name,
                        'account_id': a,
                        'price_unit': line.price_unit,
                        'quantity': line.product_qty,
                        'uos_id': line.product_uom.id,
                        'product_id': line.product_id.id or False,
                        'invoice_line_tax_id': [(6, 0, [x.id for x in line.taxes_id])],
                        'account_analytic_id': line.account_analytic_id and line.account_analytic_id.id or False,
                    })
                    purchase_line_obj.write(cr, uid, [line.id], {'invoiced': True, 'invoice_lines': [(4, inv_id)]})
                    invoices[line.partner_id.id].append((line,inv_id))

            res = []
            for result in invoices.values():
                il = map(lambda x: x[1], result)
                orders = list(set(map(lambda x : x[0].order_id, result)))

                res.append(make_invoice_by_partner(orders[0].partner_id, orders, il))

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
purchase_line_invoice()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

