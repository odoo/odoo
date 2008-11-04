# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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

import time
import netsvc
from osv import fields, osv
import ir

class account_invoice(osv.osv):
    def _amount_untaxed(self, cr, uid, ids, name, args, context={}):
        res = {}
        for invoice in self.browse(cr,uid,ids):
            if invoice.price_type == 'tax_included':
                res[invoice.id] = reduce( lambda x, y: x+y.price_subtotal, invoice.invoice_line,0)
            else:
                res[invoice.id] = super(account_invoice, self)._amount_untaxed(cr, uid, [invoice.id], name, args, context)[invoice.id]
        return res

    def _amount_tax(self, cr, uid, ids, name, args, context={}):
        res = {}
        for invoice in self.browse(cr,uid,ids):
            if invoice.price_type == 'tax_included':
                res[invoice.id] = reduce( lambda x, y: x+y.amount, invoice.tax_line,0)
            else:
                res[invoice.id] = super(account_invoice, self)._amount_tax(cr, uid, [invoice.id], name, args, context)[invoice.id]
        return res

    def _amount_total(self, cr, uid, ids, name, args, context={}):
        res = {}
        for invoice in self.browse(cr,uid,ids):
            if invoice.price_type == 'tax_included':
                res[invoice.id]= invoice.amount_untaxed + invoice.amount_tax
            else:
                res[invoice.id] = super(account_invoice, self)._amount_total(cr, uid, [invoice.id], name, args, context)[invoice.id]
        return res

    _inherit = "account.invoice"
    _columns = {
        'price_type': fields.selection([('tax_included','Tax included'),
                                        ('tax_excluded','Tax excluded')],
                                        'Price method', required=True, readonly=True,
                                        states={'draft':[('readonly',False)]}),
        'amount_untaxed': fields.function(_amount_untaxed, digits=(16,2), method=True,string='Untaxed Amount'),
        'amount_tax': fields.function(_amount_tax, method=True, string='Tax', store=True),
        'amount_total': fields.function(_amount_total, method=True, string='Total', store=True),
    }
    _defaults = {
        'price_type': lambda *a: 'tax_excluded',
    }
account_invoice()

class account_invoice_line(osv.osv):
    _inherit = "account.invoice.line"
    def _amount_line(self, cr, uid, ids, name, args, context={}):
        """
        Return the subtotal excluding taxes with respect to price_type.
        """
        res = {}
        tax_obj = self.pool.get('account.tax')
        res = super(account_invoice_line, self)._amount_line(cr, uid, ids, name, args, context)
        res2 = res.copy()
        for line in self.browse(cr, uid, ids):
            if not line.quantity:
                res[line.id] = 0.0
                continue
            if line.invoice_id and line.invoice_id.price_type == 'tax_included':
                product_taxes = None
                if line.product_id:
                    if line.invoice_id.type in ('out_invoice', 'out_refund'):
                        product_taxes = line.product_id.taxes_id
                    else:
                        product_taxes = line.product_id.supplier_taxes_id
                if product_taxes:
                    for tax in tax_obj.compute_inv(cr, uid, product_taxes, res[line.id]/line.quantity, line.quantity):
                        res[line.id] = res[line.id] - round(tax['amount'], 2)
                else:
                    for tax in tax_obj.compute_inv(cr, uid,line.invoice_line_tax_id, res[line.id]/line.quantity, line.quantity):
                        res[line.id] = res[line.id] - round(tax['amount'], 2)
            if name == 'price_subtotal_incl' and line.invoice_id and line.invoice_id.price_type == 'tax_included':
                prod_taxe_ids = None
                line_taxe_ids = None
                if product_taxes:
                    prod_taxe_ids = [ t.id for t in product_taxes ]
                    prod_taxe_ids.sort()
                    line_taxe_ids = [ t.id for t in line.invoice_line_tax_id ]
                    line_taxe_ids.sort()
                if product_taxes and prod_taxe_ids == line_taxe_ids:
                    res[line.id] = res2[line.id]
                elif not line.product_id:
                    res[line.id] = res2[line.id]
                else:
                    for tax in tax_obj.compute(cr, uid, line.invoice_line_tax_id, res[line.id]/line.quantity, line.quantity):
                        res[line.id] = res[line.id] + tax['amount']
            res[line.id]= round(res[line.id], 2)
        return res

    def _price_unit_default(self, cr, uid, context={}):
        if 'check_total' in context:
            t = context['check_total']
            if context.get('price_type', False) == 'tax_included':
                for l in context.get('invoice_line', {}):
                    if len(l) >= 3 and l[2]:
                        p = l[2].get('price_unit', 0) * (1-l[2].get('discount', 0)/100.0)
                        t = t - (p * l[2].get('quantity'))
                return t
            return super(account_invoice_line, self)._price_unit_default(cr, uid, context)
        return 0

    _columns = {
        'price_subtotal': fields.function(_amount_line, method=True, string='Subtotal w/o tax', store=True),
        'price_subtotal_incl': fields.function(_amount_line, method=True, string='Subtotal'),
    }

    _defaults = {
        'price_unit': _price_unit_default,
    }

    def move_line_get_item(self, cr, uid, line, context={}):
        return {
                'type':'src',
                'name':line.name,
                'price_unit':line.price_subtotal / line.quantity,
                'quantity':line.quantity,
                'price':line.price_subtotal,
                'account_id':line.account_id.id,
                'product_id': line.product_id.id,
                'uos_id':line.uos_id.id,
                'account_analytic_id':line.account_analytic_id.id,
            }

    def product_id_change_unit_price_inv(self, cr, uid, tax_id, price_unit, qty, address_invoice_id, product, partner_id, context={}):
        if context.get('price_type', False) == 'tax_included':
            return {'price_unit': price_unit,'invoice_line_tax_id': tax_id}
        else:
            return super(account_invoice_line, self).product_id_change_unit_price_inv(cr, uid, tax_id, price_unit, qty, address_invoice_id, product, partner_id, context=context)

    def product_id_change(self, cr, uid, ids, product, uom, qty=0, name='', type='out_invoice', partner_id=False, price_unit=False, address_invoice_id=False, price_type='tax_excluded', context={}):
        context.update({'price_type': price_type})
        return super(account_invoice_line, self).product_id_change(cr, uid, ids, product, uom, qty, name, type, partner_id, price_unit, address_invoice_id, context=context)
account_invoice_line()

class account_invoice_tax(osv.osv):
    _inherit = "account.invoice.tax"

    def compute(self, cr, uid, invoice_id):
        tax_grouped = {}
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        inv = self.pool.get('account.invoice').browse(cr, uid, invoice_id)
        cur = inv.currency_id

        if inv.price_type=='tax_excluded':
            return super(account_invoice_tax,self).compute(cr, uid, invoice_id)

        for line in inv.invoice_line:
            for tax in tax_obj.compute_inv(cr, uid, line.invoice_line_tax_id, (line.price_unit * (1-(line.discount or 0.0)/100.0)), line.quantity, inv.address_invoice_id.id, line.product_id, inv.partner_id):
                val={}
                val['invoice_id'] = inv.id
                val['name'] = tax['name']
                val['amount'] = cur_obj.round(cr, uid, cur, tax['amount'])
                val['manual'] = False
                val['sequence'] = tax['sequence']
                val['base'] = tax['price_unit'] * line['quantity']

                if inv.type in ('out_invoice','in_invoice'):
                    val['base_code_id'] = tax['base_code_id']
                    val['tax_code_id'] = tax['tax_code_id']
                    val['base_amount'] = val['base'] * tax['base_sign']
                    val['tax_amount'] = val['amount'] * tax['tax_sign']
                    val['account_id'] = tax['account_collected_id'] or line.account_id.id
                else:
                    val['base_code_id'] = tax['ref_base_code_id']
                    val['tax_code_id'] = tax['ref_tax_code_id']
                    val['base_amount'] = val['base'] * tax['ref_base_sign']
                    val['tax_amount'] = val['amount'] * tax['ref_tax_sign']
                    val['account_id'] = tax['account_paid_id'] or line.account_id.id

                key = (val['tax_code_id'], val['base_code_id'], val['account_id'])
                if not key in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += val['base']
                    tax_grouped[key]['base_amount'] += val['base_amount']
                    tax_grouped[key]['tax_amount'] += val['tax_amount']

        return tax_grouped
account_invoice_tax()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

