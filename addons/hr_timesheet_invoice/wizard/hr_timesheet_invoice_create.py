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

## Create an invoice based on selected timesheet lines
#

#
# TODO: check unit of measure !!!
#
class hr_timesheet_invoice_create(osv.osv_memory):

    _name = 'hr.timesheet.invoice.create'
    _description = 'Create invoice from timesheet'
    _columns = {
        'accounts': fields.many2many('account.analytic.account', 'invoice_id', 'account_id', 'Analytic Accounts', required=True),
        'date': fields.boolean('Date', help='The real date of each work will be displayed on the invoice'),
        'time': fields.boolean('Time spent', help='The time of each work done will be displayed on the invoice'),
        'name': fields.boolean('Name of entry', help='The detail of each work done will be displayed on the invoice'),
        'price': fields.boolean('Cost', help='The cost of each work done will be displayed on the invoice. You probably don\'t want to check this'),
        'product': fields.many2one('product.product', 'Product', help='Complete this field only if you want to force to use a specific product. Keep empty to use the real product that comes from the cost.'),
                }

    def _get_accounts(self, cr, uid, context=None):
        if context is None:
            context = {}
        if not len(context['active_ids']):
            return {}
        #Checking whether the analytic line is invoiced or not
        analytic_line_obj = self.pool.get('account.analytic.line').browse(cr, uid, context['active_ids'], context)
        for obj_acc in analytic_line_obj:
            if obj_acc.invoice_id and obj_acc.invoice_id.state !='cancel':
                raise osv.except_osv(_('Warning'),_('The analytic entry "%s" is already invoiced!')%(obj_acc.name,))

        cr.execute("SELECT distinct(account_id) from account_analytic_line where id =ANY(%s)",(context['active_ids'],))
        account_ids = cr.fetchall()
        return [x[0] for x in account_ids]

    _defaults = {
         'accounts': _get_accounts
                 }

    def do_create(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        analytic_account_obj = self.pool.get('account.analytic.account')
        res_partner_obj = self.pool.get('res.partner')
        account_payment_term_obj = self.pool.get('account.payment.term')
        invoices = []

        result = mod_obj._get_id(cr, uid, 'account', 'view_account_invoice_filter')
        res = mod_obj.read(cr, uid, result, ['res_id'])

        data = self.read(cr, uid, ids, [], context)[0]
        account_ids = data['accounts']
        for account in analytic_account_obj.browse(cr, uid, account_ids, context):
            partner = account.partner_id
            if (not partner) or not (account.pricelist_id):
                raise osv.except_osv(_('Analytic Account incomplete'),
                        _('Please fill in the Associate Partner and Sale Pricelist fields in the Analytic Account:\n%s') % (account.name,))

            if not partner.address:
                raise osv.except_osv(_('Partner incomplete'),
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
            last_invoice = self.pool.get('account.invoice').create(cr, uid, curr_invoice)
            invoices.append(last_invoice)

            context2=context.copy()
            context2['lang'] = partner.lang
            cr.execute("SELECT product_id, to_invoice, sum(unit_amount) " \
                    "FROM account_analytic_line as line " \
                    "WHERE account_id = %s " \
                        "AND id =ANY(%s) AND to_invoice IS NOT NULL " \
                    "GROUP BY product_id,to_invoice", (account.id,context['active_ids'],))

            for product_id,factor_id,qty in cr.fetchall():
                product = pool.get('product.product').browse(cr, uid, product_id, context2)
                if not product:
                    raise osv.except_osv(_('Error'), _('At least one line has no product !'))
                factor_name = ''
                factor = pool.get('hr_timesheet_invoice.factor').browse(cr, uid, factor_id, context2)

                if not data['product']:
                    if factor.customer_name:
                        factor_name = product.name+' - '+factor.customer_name
                    else:
                        factor_name = product.name
                else:
                    factor_name = pool.get('product.product').name_get(cr, uid, [data['product']], context=context)[0][1]

                if account.pricelist_id:
                    pl = account.pricelist_id.id
                    price = pool.get('product.pricelist').price_get(cr,uid,[pl], data['product'] or product_id, qty or 1.0, account.partner_id.id)[pl]
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
                    'product_id': data['product'] or product_id,
                    'invoice_line_tax_id': [(6,0,tax)],
                    'uos_id': product.uom_id.id,
                    'account_id': account_id,
                    'account_analytic_id': account.id,
                }

                #
                # Compute for lines
                #
                cr.execute("SELECT * FROM account_analytic_line WHERE account_id = %s and id = ANY (%s) AND product_id=%s and to_invoice=%s", (account.id, data['ids'], product_id, factor_id))

                line_ids = cr.dictfetchall()
                note = []
                for line in line_ids:
                    # set invoice_line_note
                    details = []
                    if data['date']:
                        details.append(line['date'])
                    if data['time']:
                        if line['product_uom_id']:
                            details.append("%s %s" % (line['unit_amount'], pool.get('product.uom').browse(cr, uid, [line['product_uom_id']])[0].name))
                        else:
                            details.append("%s" % (line['unit_amount'], ))
                    if data['name']:
                        details.append(line['name'])
                    #if data['price']:
                    #   details.append(abs(line['amount']))
                    note.append(u' - '.join(map(lambda x: unicode(x) or '',details)))

                curr_line['note'] = "\n".join(map(lambda x: unicode(x) or '',note))
                pool.get('account.invoice.line').create(cr, uid, curr_line)
                cr.execute("update account_analytic_line set invoice_id=%s WHERE account_id = %s and id =ANY(%s)" ,(last_invoice, account.id,data['ids']))

        self.pool.get('account.invoice').button_reset_taxes(cr, uid, [last_invoice], context)

        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

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
#            'type': 'ir.actions.act_window',
#            'search_view_id': res['res_id']
#        }


hr_timesheet_invoice_create()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

