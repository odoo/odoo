# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import wizard
import pooler
import time
from tools.translate import _

#
# Create an invoice based on selected timesheet lines
#

#
# TODO: check unit of measure !!!
#
class invoice_create(wizard.interface):
    def _get_accounts(self, cr, uid, data, context):
        if not len(data['ids']):
            return {}
        #Checking whether the analytic line is invoiced or not
        pool = pooler.get_pool(cr.dbname)
        analytic_line_obj = pool.get('account.analytic.line').browse(cr, uid, data['ids'], context)
        for obj_acc in analytic_line_obj:
            if obj_acc.invoice_id and obj_acc.invoice_id.state !='cancel':
                raise wizard.except_wizard(_('Warning'),_('The analytic entry "%s" is already invoiced!')%(obj_acc.name,))
        
        cr.execute("SELECT distinct(account_id) from account_analytic_line where id IN %s", (tuple(data['ids']),))
        account_ids = cr.fetchall()
        return {'accounts': [x[0] for x in account_ids]}

    def _do_create(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        analytic_account_obj = pool.get('account.analytic.account')
        res_partner_obj = pool.get('res.partner')
        account_payment_term_obj = pool.get('account.payment.term')

        account_ids = data['form']['accounts'][0][2]
        invoices = []
        for account in analytic_account_obj.browse(cr, uid, account_ids, context):
            partner = account.partner_id
            if (not partner) or not (account.pricelist_id):
                raise wizard.except_wizard(_('Analytic Account incomplete'),
                        _('Please fill in the Associate Partner and Sale Pricelist fields in the Analytic Account:\n%s') % (account.name,))

            if not partner.address:
                raise wizard.except_wizard(_('Partner incomplete'),
                        _('Please fill in the Address field in the Partner: %s.') % (partner.name,))

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
                'address_contact_id': res_partner_obj.address_get(cr, uid,
                    [account.partner_id.id], adr_pref=['contact'])['contact'],
                'address_invoice_id': res_partner_obj.address_get(cr, uid,
                    [account.partner_id.id], adr_pref=['invoice'])['invoice'],
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
                        "AND id IN %s " \
                        "AND to_invoice IS NOT NULL " \
                    "GROUP BY product_id,to_invoice",
                       (account.id, tuple(data['ids'])))

            for product_id,factor_id,qty in cr.fetchall():
                product = pool.get('product.product').browse(cr, uid, product_id, context2)
                if not product:
                    raise wizard.except_wizard(_('Error'), _('At least one line has no product !'))
                factor_name = ''
                factor = pool.get('hr_timesheet_invoice.factor').browse(cr, uid, factor_id, context2)
                
                if not data['form']['product']:
                    if factor.customer_name:
                        factor_name = product.name+' - '+factor.customer_name
                    else:
                        factor_name = product.name
                else:
                    factor_name = pool.get('product.product').name_get(cr, uid, [data['form']['product']], context=context)[0][1]
                            
                if account.pricelist_id:
                    pl = account.pricelist_id.id
                    price = pool.get('product.pricelist').price_get(cr,uid,[pl], data['form']['product'] or product_id, qty or 1.0, account.partner_id.id)[pl]
                else:
                    price = 0.0

                taxes = product.taxes_id
                tax = pool.get('account.fiscal.position').map_tax(cr, uid, account.partner_id.property_account_position, taxes)
                account_id = product.product_tmpl_id.property_account_income.id or product.categ_id.property_account_income_categ.id

                curr_line = {
                    'price_unit': price,
                    'quantity': qty,
                    'discount':factor.factor,
                    'invoice_line_tax_id': [(6,0,tax )],
                    'invoice_id': last_invoice,
                    'name': factor_name,
                    'product_id': data['form']['product'] or product_id,
                    'invoice_line_tax_id': [(6,0,tax)],
                    'uos_id': product.uom_id.id,
                    'account_id': account_id,
                    'account_analytic_id': account.id,
                }
                
                #
                # Compute for lines
                #
                cr.execute("SELECT * "  # TODO optimize this
                           "  FROM account_analytic_line"
                           " WHERE account_id=%s"
                           "   AND id IN %s"
                           "   AND product_id=%s"
                           "   AND to_invoice=%s"
                           " ORDER BY account_analytic_line.date",
                           (account.id, tuple(data['ids']), product_id, factor_id))
                line_ids = cr.dictfetchall()
                note = []
                for line in line_ids:
                    # set invoice_line_note
                    details = []
                    if data['form']['date']:
                        details.append(line['date'])
                    if data['form']['time']:
                        if line['product_uom_id']:
                            details.append("%s %s" % (line['unit_amount'], pool.get('product.uom').browse(cr, uid, [line['product_uom_id']],context2)[0].name))
                        else:
                            details.append("%s" % (line['unit_amount'], ))
                    if data['form']['name']:
                        details.append(line['name'])
                    #if data['form']['price']:
                    #   details.append(abs(line['amount']))
                    note.append(' - '.join(map(lambda x: x or '',details)))

                curr_line['note'] = "\n".join(map(lambda x: x or '',note))
                pool.get('account.invoice.line').create(cr, uid, curr_line)
                cr.execute("UPDATE account_analytic_line SET invoice_id=%s "\
                           "WHERE account_id = %s AND id IN %s",
                           (last_invoice,account.id, tuple(data['ids'])))
                
        pool.get('account.invoice').button_reset_taxes(cr, uid, [last_invoice], context)
        
        mod_obj = pooler.get_pool(cr.dbname).get('ir.model.data')
        act_obj = pooler.get_pool(cr.dbname).get('ir.actions.act_window')
        
        mod_id = mod_obj.search(cr, uid, [('name', '=', 'action_invoice_tree1')])[0]
        res_id = mod_obj.read(cr, uid, mod_id, ['res_id'])['res_id']
        act_win = act_obj.read(cr, uid, res_id, [])
        act_win['domain'] = [('id','in',invoices),('type','=','out_invoice')]
        act_win['name'] = _('Invoices')
        return act_win
        
#        return {
#            'domain': "[('id','in', ["+','.join(map(str,invoices))+"])]",
#            'name': _('Invoices'),
#            'view_type': 'form',
#            'view_mode': 'tree,form',
#            'res_model': 'account.invoice',
#            'view_id': False,
#            'context': "{'type':'out_invoice'}",
#            'type': 'ir.actions.act_window'
#        }


    _create_form = """<?xml version="1.0"?>
    <form string="Invoice on analytic entries">
        <notebook>
        <page string="Invoicing Data">
            <separator string="Do you want to show details of work in invoice ?" colspan="4"/>
            <field name="date"/>
            <field name="time"/>
            <field name="name"/>
            <field name="price"/>
            <separator string="Force to use a specific product" colspan="4"/>
            <field name="product"/>
        </page>
        <page string="Filter on Accounts" groups="base.group_extended">
            <separator string="Choose accounts you want to invoice" colspan="4"/>
            <field name="accounts" colspan="4" nolabel="1"/>
        </page>
        </notebook>
    </form>"""

    _create_fields = {
        'accounts': {'string':'Analytic Accounts', 'type':'many2many', 'required':'true', 'relation':'account.analytic.account'},
        'date': {'string':'Date', 'type':'boolean', 'help':'The real date of each work will be displayed on the invoice'},
        'time': {'string':'Time spent', 'type':'boolean', 'help':'The time of each work done will be displayed on the invoice'},
        'name': {'string':'Name of entry', 'type':'boolean', 'help':'The detail of each work done will be displayed on the invoice'},
        'price': {'string':'Cost', 'type':'boolean', 'help':'The cost of each work done will be displayed on the invoice. You probably don\'t want to check this.'},
        'product': {'string':'Product', 'type':'many2one', 'relation': 'product.product', 'help':"Complete this field only if you want to force to use a specific product. Keep empty to use the real product that comes from the cost."},
    }

    states = {
        'init' : {
            'actions' : [_get_accounts],
            'result' : {'type':'form', 'arch':_create_form, 'fields':_create_fields, 'state': [('end','Cancel'),('create','Create Invoices')]},
        },
        'create' : {
            'actions' : [],
            'result' : {'type':'action', 'action':_do_create, 'state':'end'},
        },
    }
invoice_create('hr.timesheet.invoice.create')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

