# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
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
        if not data['ids']:
            return {}
        account = pooler.get_pool(cr.dbname).get('account.analytic.account').browse(cr, uid, data['ids'], context)[0]
        return {'use_amount_max': bool(account.amount_max)}

    def _do_create(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
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
            }
            last_invoice = pool.get('account.invoice').create(cr, uid, curr_invoice)
            invoices.append(last_invoice)

            context2=context.copy()
            context2['lang'] = partner.lang
            cr.execute("SELECT product_id, to_invoice, sum(unit_amount) " \
                    "FROM account_analytic_line as line " \
                    "WHERE account_id = %d " \
                        "AND to_invoice IS NOT NULL " \
                    "GROUP BY product_id, to_invoice", (account.id,))
            for product_id,factor_id,qty in cr.fetchall():
                product = pool.get('product.product').browse(cr, uid, product_id, context2)
                factor_name = ''
                factor = pool.get('hr_timesheet_invoice.factor').browse(cr, uid, factor_id, context2)
                if factor.customer_name:
                    factor_name = product.name+' - '+factor.customer_name
                else:
                    factor_name = product.name
                if account.pricelist_id:
                    pl = account.pricelist_id.id
                    price = pool.get('product.pricelist').price_get(cr,uid,[pl], product_id, qty or 1.0, account.partner_id.id)[pl]
                else:
                    price = 0.0

                taxes = product.taxes_id
                tax = self.pool.get('account.fiscal.position').map_tax(cr, uid, account.partner_id, taxes)
                account_id = product.product_tmpl_id.property_account_income.id or product.categ_id.property_account_income_categ.id

                curr_line = {
                    'price_unit': price,
                    'quantity': qty,
                    'discount':factor.factor,
                    'invoice_line_tax_id': [(6,0,tax )],
                    'invoice_id': last_invoice,
                    'name': factor_name,
                    'product_id': product_id,
                    'uos_id': product.uom_id.id,
                    'account_id': account_id,
                    'account_analytic_id': account.id,
                }

                amount_total += round((price * ( 1.0 - (factor.factor or 0.0)/100.0)), 2) * qty

                #
                # Compute for lines
                #
                cr.execute("SELECT * FROM account_analytic_line WHERE account_id = %d AND product_id=%d and to_invoice=%d" % (account.id, product_id, factor_id))
                line_ids = cr.dictfetchall()
                note = []
                for line in line_ids:
                    # set invoice_line_note
                    details = []
                    if data['form']['date']:
                        details.append(line['date'])
                    if data['form']['time']:
                        details.append("%s %s" % (line['unit_amount'], pool.get('product.uom').browse(cr, uid, [line['product_uom_id']])[0].name))
                    if data['form']['name']:
                        details.append(line['name'])
                    #if data['form']['price']:
                    #   details.append(abs(line['amount']))
                    note.append(' - '.join(map(str,details)))

                curr_line['note'] = "\n".join(map(str,note))
                pool.get('account.invoice.line').create(cr, uid, curr_line)
                cr.execute("update account_analytic_line set invoice_id=%d WHERE account_id = %d and invoice_id is null" % (last_invoice,account.id,))

            cr.execute("SELECT line.product_id, sum(line.amount), line.account_id, line.product_uom_id, move_line.ref FROM account_analytic_line as line, account_move_line as move_line WHERE line.account_id = %d AND line.move_id IS NOT NULL AND move_line.id = line.move_id GROUP BY line.product_id, line.account_id, line.product_uom_id, move_line.ref" % (account.id))
            for product_id, amount, account_id, product_uom_id, ref in cr.fetchall():
                product = pool.get('product.product').browse(cr, uid, product_id, context2)

                if product:
                    taxes = product.taxes_id
                else:
                    taxes = []

                tax = self.pool.get('account.fiscal.position').map_tax(cr, uid, account.partner_id, taxes)
                curr_line = {
                    'price_unit': -amount,
                    'quantity': 1.0,
                    'discount': 0.0,
                    'invoice_line_tax_id': [(6,0,tax)],
                    'invoice_id': last_invoice,
                    'name': ref+(product and ' - '+product.name or ''),
                    'product_id': product_id,
                    'uos_id': product_uom_id,
                    'account_id': account_id,
                }
                pool.get('account.invoice.line').create(cr, uid, curr_line)

            if data['form']['use_amount_max']:
                if abs(account.amount_max - amount_total) > data['form']['balance_amount'] :
                    if not data['form']['balance_product']:
                        raise wizard.except_wizard(_('Balance product needed'), _('Please fill a Balance product in the wizard'))
                    product = pool.get('product.product').browse(cr, uid, data['form']['balance_product'], context2)

                    taxes = product.taxes_id
                    tax = self.pool.get('account.fiscal.position').map_tax(cr, uid, account.partner_id, taxes)
                    account_id = product.product_tmpl_id.property_account_income.id or product.categ_id.property_account_income_categ.id

                    curr_line = {
                        'price_unit': account.amount_max - amount_total,
                        'quantity': 1.0,
                        'discount': 0.0,
                        'invoice_line_tax_id': [(6,0,tax)],
                        'invoice_id': last_invoice,
                        'name': product.name,
                        'product_id': product_id,
                        'uos_id': product.uom_id.id,
                        'account_id': account_id,
                    }
                    pool.get('account.invoice.line').create(cr, uid, curr_line)
                    if account.amount_max < amount_total:
                        pool.get('account.invoice').write(cr, uid, [last_invoice], {'type': 'out_refund',})

        return {
            'domain': "[('id','in', ["+','.join(map(str,invoices))+"])]",
            'name': 'Invoices',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'view_id': False,
            'context': "{'type':'out_invoice'}",
            'type': 'ir.actions.act_window'
        }


    _create_form = """<?xml version="1.0"?>
    <form title="Final invoice for analytic account">
        <separator string="Do you want details for each line of the invoices ?" colspan="4"/>
        <field name="date"/>
        <field name="time"/>
        <field name="name"/>
        <field name="price"/>
        <separator string="Invoice Balance amount" colspan="4"/>
        <field name="use_amount_max"/>
        <field name="balance_amount"/>
        <field name="balance_product"/>
    </form>"""

    _create_fields = {
        'date': {'string':'Date', 'type':'boolean'},
        'time': {'string':'Time spent', 'type':'boolean'},
        'name': {'string':'Name of entry', 'type':'boolean'},
        'price': {'string':'Cost', 'type':'boolean'},
        'use_amount_max': {'string':'Use Max. Invoice Price', 'type':'boolean'},
        'balance_amount': {'string':'Balance amount', 'type': 'float'},
        'balance_product': {'string':'Balance product', 'type': 'many2one', 'relation':'product.product'},
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

