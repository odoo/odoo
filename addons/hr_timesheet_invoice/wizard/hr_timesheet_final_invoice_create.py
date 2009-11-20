# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import wizard
import pooler
import time
from tools.translate import _

#
# Create an final invoice based on selected timesheet lines
#

#
# TODO: check unit of measure !!!
#
class final_invoice_create(wizard.interface):
    def _get_defaults(self, cr, uid, data, context):
        return {}

    def _do_create(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        mod_obj = pool.get('ir.model.data') 
        result = mod_obj._get_id(cr, uid, 'account', 'view_account_invoice_filter')
        res = mod_obj.read(cr, uid, result, ['res_id'])
        analytic_account_obj = pool.get('account.analytic.account')
        res_partner_obj = pool.get('res.partner')
        account_payment_term_obj = pool.get('account.payment.term')

        account_ids = data['ids']
        invoices = []
        for account in analytic_account_obj.browse(cr, uid, account_ids, context):
            partner = account.partner_id
            amount_total=0.0
            if (not partner) or not (account.pricelist_id):
                raise wizard.except_wizard(_('Analytic account incomplete'),
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
                'name': time.strftime('%D')+' - '+account.name,
                'partner_id': account.partner_id.id,
                'address_contact_id': pool.get('res.partner').address_get(cr, uid, [account.partner_id.id], adr_pref=['contact'])['contact'],
                'address_invoice_id': pool.get('res.partner').address_get(cr, uid, [account.partner_id.id], adr_pref=['invoice'])['invoice'],
                'payment_term': partner.property_payment_term.id or False,
                'account_id': partner.property_account_receivable.id,
                'currency_id': account.pricelist_id.currency_id.id,
                'date_due': date_due,
                'fiscal_position': account.partner_id.property_account_position.id
            }
            last_invoice = pool.get('account.invoice').create(cr, uid, curr_invoice)
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
                product = pool.get('product.product').browse(cr, uid, product_id, context2)

                if product:
                    taxes = product.taxes_id
                else:
                    taxes = []

                tax = pool.get('account.fiscal.position').map_tax(cr, uid, account.partner_id.property_account_position, taxes)
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
                pool.get('account.invoice.line').create(cr, uid, curr_line)

            if not data['form']['balance_product']:
                raise wizard.except_wizard(_('Balance product needed'), _('Please fill a Balance product in the wizard'))
            product = pool.get('product.product').browse(cr, uid, data['form']['balance_product'], context2)

            taxes = product.taxes_id
            tax = pool.get('account.fiscal.position').map_tax(cr, uid, account.partner_id.property_account_position, taxes)
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
            pool.get('account.invoice.line').create(cr, uid, curr_line)
            if account.amount_max < amount_total:
                pool.get('account.invoice').write(cr, uid, [last_invoice], {'type': 'out_refund',})
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


    _create_form = """<?xml version="1.0"?>
    <form title="Final invoice for analytic account">
        <separator string="Do you want details for each line of the invoices ?" colspan="4"/>
        <field name="date"/>
        <field name="time"/>
        <field name="name"/>
        <field name="price"/>
        <separator string="Invoice Balance amount" colspan="4"/>
        <field name="balance_product" required="1"/>
    </form>"""

    _create_fields = {
        'date': {'string':'Date', 'type':'boolean', 'help':"Display date in the history of works"},
        'time': {'string':'Time spent', 'type':'boolean', 'help':"Display time in the history of works"},
        'name': {'string':'Name of entry', 'type':'boolean', 'help':"Display detail of work in the invoice line."},
        'price': {'string':'Cost', 'type':'boolean', 'help':"Display cost of the item you reinvoice"},
        'balance_product': {'string':'Balance product', 'type': 'many2one', 'relation':'product.product', 'help':"The product that will be used to invoice the remaining amount."},
    }

    states = {
        'init' : {
            'actions' : [_get_defaults],
            'result' : {'type':'form', 'arch':_create_form, 'fields':_create_fields, 'state': [('end','Cancel'),('create','Create invoices')]},
        },
        'create' : {
            'actions' : [],
            'result' : {'type':'action', 'action':_do_create, 'state':'end'},
        },
    }
final_invoice_create('hr.timesheet.final.invoice.create')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

