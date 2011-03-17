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

import time

from osv import osv, fields
from tools.translate import _

#
# Create an final invoice based on selected timesheet lines
#

#
# TODO: check unit of measure !!!
#
class final_invoice_create(osv.osv_memory):
    _name = 'hr.timesheet.invoice.create.final'
    _description = 'Create invoice from timesheet final'
    _columns = {
        'date': fields.boolean('Date', help='Display date in the history of works'),
        'time': fields.boolean('Time spent', help='Display time in the history of works'),
        'name': fields.boolean('Name of entry', help='Display detail of work in the invoice line.'),
        'price': fields.boolean('Cost', help='Display cost of the item you reinvoice'),
        'balance_product': fields.many2one('product.product', 'Balance product', help='The product that will be used to invoice the remaining amount'),
                }

    def do_create(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        analytic_account_obj = self.pool.get('account.analytic.account')
        res_partner_obj = self.pool.get('res.partner')
        account_payment_term_obj = self.pool.get('account.payment.term')
        invoice_obj = self.pool.get('account.invoice')
        product_obj = self.pool.get('product.product')
        fiscal_pos_obj = self.pool.get('account.fiscal.position')
        invoice_line_obj = self.pool.get('account.invoice.line')
        invoices = []

        if context is None:
            context = {}
        result = mod_obj._get_id(cr, uid, 'account', 'view_account_invoice_filter')
        res = mod_obj.read(cr, uid, result, ['res_id'], context=context)

        data = self.browse(cr, uid, ids, context=context)[0]
        balance_product = data.balance_product.id

        account_ids = 'active_ids' in context and context['active_ids'] or []

        for account in analytic_account_obj.browse(cr, uid, account_ids, context=context):
            partner = account.partner_id
            amount_total=0.0
            if (not partner) or not (account.pricelist_id):
                raise osv.except_osv(_('Analytic account incomplete'),
                        _('Please fill in the partner and pricelist field '
                        'in the analytic account:\n%s') % (account.name,))

            date_due = False
            if partner.property_payment_term:
                pterm_list= account_payment_term_obj.compute(cr, uid,
                        partner.property_payment_term.id, value=1,
                        date_ref=time.strftime('%Y-%m-%d'))
                if pterm_list:
                    pterm_list = [line[0] for line in pterm_list]
                    pterm_list.sort()
                    date_due = pterm_list[-1]

            curr_invoice = {
                'name': time.strftime('%d/%m/%Y')+' - '+account.name,
                'partner_id': account.partner_id.id,
                'address_contact_id': res_partner_obj.address_get(cr, uid, [account.partner_id.id], adr_pref=['contact'])['contact'],
                'address_invoice_id': res_partner_obj.address_get(cr, uid, [account.partner_id.id], adr_pref=['invoice'])['invoice'],
                'payment_term': partner.property_payment_term.id or False,
                'account_id': partner.property_account_receivable.id,
                'currency_id': account.pricelist_id.currency_id.id,
                'date_due': date_due,
                'fiscal_position': account.partner_id.property_account_position.id
            }
            last_invoice = invoice_obj.create(cr, uid, curr_invoice, context=context)
            invoices.append(last_invoice)

            context2=context.copy()
            context2['lang'] = partner.lang
            cr.execute("SELECT product_id, to_invoice, sum(unit_amount) " \
                    "FROM account_analytic_line as line " \
                    "WHERE account_id = %s " \
                        "AND to_invoice IS NOT NULL " \
                    "GROUP BY product_id, to_invoice", (account.id,))

            cr.execute("""SELECT
                    line.product_id,
                    sum(line.amount),
                    line.general_account_id,
                    line.product_uom_id,
                    move_line.ref
                FROM
                    account_analytic_line as line
                    LEFT JOIN account_move_line as move_line on (line.move_id=move_line.id)
                    LEFT JOIN account_analytic_journal as journal on (line.journal_id=journal.id)
                WHERE
                    line.account_id = %s AND
                    line.move_id IS NOT NULL AND
                    journal.type = 'sale'
                GROUP BY
                    line.product_id,
                    line.general_account_id,
                    line.product_uom_id,
                    move_line.ref""", (account.id,))
            for product_id, amount, account_id, product_uom_id, ref in cr.fetchall():
                product = product_obj.browse(cr, uid, product_id, context2)

                if product:
                    taxes = product.taxes_id
                else:
                    taxes = []

                tax = fiscal_pos_obj.map_tax(cr, uid, account.partner_id.property_account_position, taxes)
                curr_line = {
                    'price_unit': -amount,
                    'quantity': 1.0,
                    'discount': 0.0,
                    'invoice_line_tax_id': [(6,0,tax)],
                    'invoice_id': last_invoice,
                    'name': ref or '' +(product and ' - '+product.name or ''),
                    'product_id': product_id,
                    'uos_id': product_uom_id,
                    'account_id': account_id,
                    'account_analytic_id': account.id
                }
                invoice_line_obj.create(cr, uid, curr_line, context=context)

            if not balance_product:
                raise osv.except_osv(_('Balance product needed'), _('Please fill a Balance product in the wizard'))
            product = product_obj.browse(cr, uid, balance_product, context=context2)
            taxes = product.taxes_id
            tax = fiscal_pos_obj.map_tax(cr, uid, account.partner_id.property_account_position, taxes)
            account_id = product.product_tmpl_id.property_account_income.id or product.categ_id.property_account_income_categ.id
            curr_line = {
                'price_unit': account.amount_max - amount_total,
                'quantity': 1.0,
                'discount': 0.0,
                'invoice_line_tax_id': [(6,0,tax)],
                'invoice_id': last_invoice,
                'name': product.name,
                'product_id': product.id,
                'uos_id': product.uom_id.id,
                'account_id': account_id,
                'account_analytic_id': account.id
            }
            invoice_line_obj.create(cr, uid, curr_line, context=context)
            if account.amount_max < amount_total:
                invoice_obj.write(cr, uid, [last_invoice], {'type': 'out_refund',}, context=context)
            cr.execute('update account_analytic_line set invoice_id=%s where invoice_id is null and account_id=%s', (last_invoice, account.id))

        return {
            'domain': "[('id','in', ["+','.join(map(str,invoices))+"])]",
            'name': 'Invoices',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'view_id': False,
            'context': "{'type':'out_invoice'}",
            'type': 'ir.actions.act_window',
            'search_view_id': res['res_id']
                }

final_invoice_create()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
